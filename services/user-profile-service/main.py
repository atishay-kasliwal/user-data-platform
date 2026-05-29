"""
User Profile Service — source of truth for all user data.

Read path:  Redis cache → Postgres (on miss)
Write path: Postgres (transactional: row update + history insert) → Kafka event
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg
import redis.asyncio as aioredis
from aiokafka import AIOKafkaProducer
from fastapi import Depends, FastAPI, HTTPException, Header, Query, status
from pydantic import BaseModel, EmailStr

app = FastAPI(title="User Profile Service", version="1.0.0")

# ---------------------------------------------------------------------------
# Config (override via environment variables)
# ---------------------------------------------------------------------------
DB_DSN      = os.getenv("DB_DSN",    "postgresql://platform:platform@postgres:5432/userdata")
REDIS_URL   = os.getenv("REDIS_URL", "redis://redis:6379/0")
KAFKA_BROKERS = os.getenv("KAFKA_BROKERS", "kafka:9092")

# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def startup():
    app.state.db    = await asyncpg.create_pool(DB_DSN, min_size=5, max_size=20)
    app.state.cache = aioredis.from_url(REDIS_URL, decode_responses=True)
    app.state.kafka = AIOKafkaProducer(bootstrap_servers=KAFKA_BROKERS)
    await app.state.kafka.start()

@app.on_event("shutdown")
async def shutdown():
    await app.state.db.close()
    await app.state.cache.aclose()
    await app.state.kafka.stop()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def get_db():
    async with app.state.db.acquire() as conn:
        yield conn

async def emit(topic: str, payload: dict):
    await app.state.kafka.send_and_wait(
        topic,
        json.dumps(payload, default=str).encode()
    )

async def cache_key(user_id: str) -> str:
    return f"user:{user_id}:profile"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class CreateUserRequest(BaseModel):
    email: EmailStr
    phone: str | None = None
    profile: dict[str, Any] = {}

class UpdateUserRequest(BaseModel):
    field_path: str          # e.g., "profile.name"
    value: Any
    changed_by: str          # service or user UUID making the change

class ConsentGrantRequest(BaseModel):
    grantee_id: str
    scope: list[str]         # e.g., ["profile.name", "location.city"]
    expires_at: datetime | None = None

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(body: CreateUserRequest, db=Depends(get_db)):
    user_id = str(uuid.uuid4())
    identity = {"email": body.email}
    if body.phone:
        identity["phone"] = body.phone

    await db.execute(
        """
        INSERT INTO users (id, identity, profile)
        VALUES ($1, $2::jsonb, $3::jsonb)
        """,
        uuid.UUID(user_id),
        json.dumps(identity),
        json.dumps(body.profile),
    )

    await emit("user.created", {"user_id": user_id, "identity": identity})
    return {"id": user_id}


@app.get("/users/{user_id}")
async def get_user(
    user_id: str,
    scope: str = Query(default="", description="Comma-separated field paths to return"),
    x_service_id: str = Header(default=""),
    db=Depends(get_db),
):
    # Check cache first
    ck = await cache_key(user_id)
    cached = await app.state.cache.get(ck)
    if cached:
        row = json.loads(cached)
    else:
        record = await db.fetchrow(
            "SELECT id, identity, profile, documents, location, meta FROM users WHERE id = $1",
            uuid.UUID(user_id),
        )
        if not record:
            raise HTTPException(status_code=404, detail="User not found")
        row = {
            "id": str(record["id"]),
            "identity": record["identity"],
            "profile": record["profile"],
            "documents": record["documents"],
            "location": record["location"],
            "meta": record["meta"],
        }
        await app.state.cache.set(ck, json.dumps(row, default=str), ex=3600)

    await emit("user.accessed", {
        "user_id": user_id,
        "service_id": x_service_id,
        "scope": scope,
        "at": datetime.now(timezone.utc).isoformat(),
    })

    # Filter to requested scope if provided
    if scope:
        fields = [f.strip() for f in scope.split(",")]
        filtered: dict[str, Any] = {"id": row["id"]}
        for field in fields:
            parts = field.split(".", 1)
            top = parts[0]
            if top in row and isinstance(row[top], dict) and len(parts) == 2:
                filtered.setdefault(top, {})[parts[1]] = row[top].get(parts[1])
            elif top in row:
                filtered[top] = row[top]
        return filtered

    return row


@app.patch("/users/{user_id}")
async def update_user(user_id: str, body: UpdateUserRequest, db=Depends(get_db)):
    parts = body.field_path.split(".", 1)
    column = parts[0]
    allowed_columns = {"identity", "profile", "documents", "location", "meta"}
    if column not in allowed_columns:
        raise HTTPException(status_code=400, detail=f"Unknown column: {column}")

    async with db.transaction():
        # Fetch current value for history
        current = await db.fetchval(
            f"SELECT {column} FROM users WHERE id = $1",
            uuid.UUID(user_id),
        )
        if current is None:
            raise HTTPException(status_code=404, detail="User not found")

        old_value = current
        if len(parts) == 2:
            # Nested key update: jsonb_set(column, '{key}', value)
            new_json = json.dumps(body.value)
            await db.execute(
                f"""
                UPDATE users
                SET {column} = jsonb_set({column}, $1, $2::jsonb)
                WHERE id = $3
                """,
                f"{{{parts[1]}}}",
                new_json,
                uuid.UUID(user_id),
            )
        else:
            await db.execute(
                f"UPDATE users SET {column} = $1::jsonb WHERE id = $2",
                json.dumps(body.value),
                uuid.UUID(user_id),
            )

        await db.execute(
            """
            INSERT INTO user_history (user_id, field_path, old_value, new_value, changed_by)
            VALUES ($1, $2, $3::jsonb, $4::jsonb, $5)
            """,
            uuid.UUID(user_id),
            body.field_path,
            json.dumps(old_value),
            json.dumps(body.value),
            uuid.UUID(body.changed_by),
        )

    # Invalidate cache
    await app.state.cache.delete(await cache_key(user_id))

    await emit("user.updated", {
        "user_id": user_id,
        "field_path": body.field_path,
        "changed_by": body.changed_by,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "updated"}


@app.get("/users/{user_id}/history")
async def get_history(
    user_id: str,
    field_path: str | None = Query(default=None),
    limit: int = Query(default=50, le=500),
    db=Depends(get_db),
):
    if field_path:
        rows = await db.fetch(
            """
            SELECT id, field_path, old_value, new_value, changed_by, changed_at
            FROM user_history
            WHERE user_id = $1 AND field_path = $2
            ORDER BY changed_at DESC
            LIMIT $3
            """,
            uuid.UUID(user_id), field_path, limit,
        )
    else:
        rows = await db.fetch(
            """
            SELECT id, field_path, old_value, new_value, changed_by, changed_at
            FROM user_history
            WHERE user_id = $1
            ORDER BY changed_at DESC
            LIMIT $2
            """,
            uuid.UUID(user_id), limit,
        )
    return [dict(r) for r in rows]


@app.post("/users/{user_id}/consent")
async def grant_consent(user_id: str, body: ConsentGrantRequest, db=Depends(get_db)):
    grant_id = str(uuid.uuid4())
    await db.execute(
        """
        INSERT INTO consent_grants (id, user_id, grantee_id, scope, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        uuid.UUID(grant_id),
        uuid.UUID(user_id),
        uuid.UUID(body.grantee_id),
        body.scope,
        body.expires_at,
    )
    await emit("user.consent_granted", {
        "grant_id": grant_id,
        "user_id": user_id,
        "grantee_id": body.grantee_id,
        "scope": body.scope,
    })
    return {"grant_id": grant_id}


@app.delete("/users/{user_id}/consent/{grant_id}")
async def revoke_consent(user_id: str, grant_id: str, db=Depends(get_db)):
    result = await db.execute(
        """
        UPDATE consent_grants SET revoked_at = now()
        WHERE id = $1 AND user_id = $2 AND revoked_at IS NULL
        """,
        uuid.UUID(grant_id), uuid.UUID(user_id),
    )
    if result == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Grant not found or already revoked")

    await emit("user.consent_revoked", {
        "grant_id": grant_id,
        "user_id": user_id,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    return {"status": "revoked"}


@app.get("/health")
async def health():
    return {"status": "ok"}
