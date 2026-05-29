"""
Ingestion Service — receives data from multiple sources, normalizes it,
deduplicates against current state, and forwards writes to the User Profile Service.

Supported source types:
  - oauth_profile  (Google, Apple, etc.)
  - document_upload
  - partner_webhook
  - location_update
"""

import os
from typing import Any, Literal

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="Ingestion Service", version="1.0.0")

UPS_BASE = os.getenv("UPS_BASE_URL", "http://user-profile-service:8000")
SERVICE_ID = os.getenv("SERVICE_ID", "00000000-0000-0000-0000-000000000001")

# ---------------------------------------------------------------------------
# Source-specific normalizers
# Maps raw source payload → {field_path: value} dict
# ---------------------------------------------------------------------------
NORMALIZERS: dict[str, callable] = {
    "oauth_profile": lambda d: {
        "profile.name":        d.get("name"),
        "profile.picture_url": d.get("picture"),
        "identity.email":      d.get("email"),
    },
    "document_upload": lambda d: {
        f"documents.{d['doc_type']}": {
            "url":        d["url"],
            "verified_at": d.get("verified_at"),
        }
    },
    "partner_webhook": lambda d: {
        f"meta.{d['partner']}.{k}": v for k, v in d.get("fields", {}).items()
    },
    "location_update": lambda d: {
        "location.current": {
            "lat":  d["lat"],
            "lng":  d["lng"],
            "at":   d["timestamp"],
        }
    },
}

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class IngestRequest(BaseModel):
    user_id: str
    source: Literal["oauth_profile", "document_upload", "partner_webhook", "location_update"]
    payload: dict[str, Any]

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest(body: IngestRequest):
    normalizer = NORMALIZERS.get(body.source)
    if not normalizer:
        raise HTTPException(status_code=400, detail=f"Unknown source: {body.source}")

    normalized = normalizer(body.payload)
    # Strip None values — don't overwrite existing data with nulls
    normalized = {k: v for k, v in normalized.items() if v is not None}

    if not normalized:
        return {"status": "no_op", "reason": "no non-null fields after normalization"}

    async with httpx.AsyncClient(base_url=UPS_BASE) as client:
        # Fetch current snapshot for dedup
        resp = await client.get(f"/users/{body.user_id}")
        if resp.status_code == 404:
            raise HTTPException(status_code=404, detail="User not found in UPS")
        current = resp.json()

        updates_sent = 0
        for field_path, new_value in normalized.items():
            # Simple dedup: skip if value unchanged
            parts = field_path.split(".", 1)
            current_value = current.get(parts[0], {})
            if len(parts) == 2 and isinstance(current_value, dict):
                current_value = current_value.get(parts[1])
            if current_value == new_value:
                continue

            patch_resp = await client.patch(
                f"/users/{body.user_id}",
                json={
                    "field_path": field_path,
                    "value": new_value,
                    "changed_by": SERVICE_ID,
                },
                headers={"x-service-id": SERVICE_ID},
            )
            if patch_resp.status_code != 200:
                raise HTTPException(
                    status_code=502,
                    detail=f"UPS patch failed for {field_path}: {patch_resp.text}",
                )
            updates_sent += 1

    return {"status": "ok", "fields_updated": updates_sent}


@app.get("/health")
async def health():
    return {"status": "ok"}
