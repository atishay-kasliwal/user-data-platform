# System Design: Always-On User Data Platform

## Problem Statement

Design a system that **always has access to user information** — meaning authorized services can read any user attribute at any time with low latency, without repeatedly prompting the user for permission.

## Assumptions

1. System is authorized to store and access user information
2. User information includes profile data, documents, location, and metadata
3. "Always has access" means the system must not depend on live fetches from external sources at read time
4. Permission is granted once per service+scope pair and persists until revoked

## Functional Requirements

1. Ingest user information from multiple sources
2. Store user information in a unified profile
3. Authorized services can access user information at any time
4. Maintain full history of all changes
5. Log every read and write
6. Support updates when user information changes

## Non-Functional Requirements

1. High availability (99.99% uptime target)
2. Low latency (p99 read < 50ms)
3. Scalable to millions of users
4. Strong security and privacy controls
5. Compliance and audit support (GDPR, SOC2)
6. Fault tolerance and disaster recovery

---

## Core Philosophy

Rather than a complex microservices mesh, the design reduces to:

> **A universal Postgres table with one row per user and JSONB columns for extensible attributes, with a trust/consent plane, a Redis cache as the hot read path, and Kafka as the event backbone.**

JSONB columns mean new data categories are additive — no schema migrations at scale. Consent is a first-class DB entity, not a config flag. Redis is what services actually read; Postgres is the durable truth.

---

## Data Model

### Primary Table

```sql
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  identity    JSONB NOT NULL,        -- email, phone, biometrics
  profile     JSONB DEFAULT '{}',    -- name, dob, demographics
  documents   JSONB DEFAULT '{}',    -- IDs, passports, certificates
  location    JSONB DEFAULT '{}',    -- current position + history
  meta        JSONB DEFAULT '{}',    -- ingestion source, tags, flags
  created_at  TIMESTAMPTZ DEFAULT now(),
  updated_at  TIMESTAMPTZ DEFAULT now()
);
```

As new data categories emerge, either new keys within an existing JSONB column or a new JSONB column is added — no ALTER TABLE on existing rows.

### Change History (append-only)

```sql
CREATE TABLE user_history (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES users(id),
  field_path  TEXT NOT NULL,          -- e.g., 'profile.name'
  old_value   JSONB,
  new_value   JSONB,
  changed_by  UUID NOT NULL,
  changed_at  TIMESTAMPTZ DEFAULT now()
);
```

### Consent Grants

```sql
CREATE TABLE consent_grants (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES users(id),
  grantee_id  UUID NOT NULL,
  scope       TEXT[] NOT NULL,        -- ['profile.name', 'location.city']
  granted_at  TIMESTAMPTZ DEFAULT now(),
  expires_at  TIMESTAMPTZ,
  revoked_at  TIMESTAMPTZ
);
```

Row-Level Security (RLS) is enforced at the DB layer — services can only query rows and JSONB keys covered by their active consent grants.

---

## Components

### 1. User Profile Service

Source of truth for all user data. Owns reads and writes to the `users` table.

- GET /users/{id}?scope=profile.name,location.city
- PATCH /users/{id} — partial update, field-level
- GET /users/{id}/history — paginated change history
- POST /users/{id}/consent — grant a new scope to a service

Writes are transactional: UPS row update + history insert happen in one DB transaction, then a Kafka event is emitted.

### 2. Ingestion Service

Receives data from external and internal sources, normalizes it to the JSONB schema, deduplicates against current state, and calls User Profile Service to write.

Sources: OAuth providers, document uploads, partner API webhooks, IoT/NFC devices.

### 3. Event Bus (Kafka)

Topics:
- `user.created`
- `user.updated` — field path + old/new values
- `user.accessed` — service + scope + timestamp
- `user.consent_granted`
- `user.consent_revoked`

Consumers: cache invalidation, search index updater, audit log writer.

### 4. Cache (Redis)

Hot read path. All authorized service reads hit Redis first.

- Key: `user:{uuid}:{scope_hash}`
- TTL: 5 min for mutable fields (location), 1 hr for stable fields (profile)
- Invalidation: triggered by `user.updated` Kafka events, not TTL alone

### 5. Audit Logging Service

Kafka consumer that writes every read and write event to an immutable S3 store (Parquet, partitioned by date + user_id). Queryable via Athena for compliance investigations. 7-year retention.

### 6. API Gateway

TLS termination, rate limiting, JWT validation, routing to downstream services. Every request carries `service_id + user_id + requested_scope`.

### 7. Auth & Consent Layer

Before any data is returned:
1. Validate JWT
2. Check `consent_grants` for active grant matching `grantee_id + user_id + scope`
3. If grant exists → serve data
4. If no grant → 403 or trigger one-time consent flow → persist grant → serve data

---

## Read Path (end-to-end)

```
Service → API Gateway (JWT validate) → Auth (consent check)
        → Redis cache hit? → return + audit log
        → cache miss → Postgres query → populate cache → return + audit log
```

## Write Path (end-to-end)

```
Source → Ingestion Service → normalize → dedup check
       → BEGIN TRANSACTION
           UPDATE users SET ...
           INSERT INTO user_history ...
         COMMIT
       → emit user.updated to Kafka
       → [Cache invalidation consumer] delete Redis key
       → [Audit log consumer] write to S3
       → [Search consumer] update Elasticsearch
```

---

## Scaling

| Concern | Solution |
|---|---|
| Storage at scale | Citus (distributed Postgres) shards by user_id hash |
| Read throughput | Redis cluster; reads never touch Postgres for hot profiles |
| Write throughput | Kafka absorbs ingest spikes; async consumers decouple downstream work |
| Global latency | Regional Postgres read replicas + regional Redis clusters |
| Schema evolution | JSONB absorbs new data categories without migrations |
| Day-zero onboarding | Pre-populate rows from identity providers; users claim rows, not sign up |

---

## Security

- Encryption at rest: AES-256 for Postgres, Redis, S3
- Encryption in transit: TLS 1.3, mTLS for internal services
- Field-level encryption: PII fields encrypted with per-user KMS keys before storage
- Data residency: sharding pins EU users to EU shards for GDPR compliance
- Right to erasure: soft-delete + async scrub from cache, search index; audit logs retain tombstone only
