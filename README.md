# User Data Platform

A system that always has access to user information — built on first principles.

## Core Concept

One universal Postgres table with one row per user and infinitely extensible JSONB columns, layered with a trust/consent control plane, a Redis cache as the primary read path, and Kafka as the event backbone.

```
External Sources → Ingestion Service → Event Bus (Kafka)
                                              ↓
                                   User Profile Store (Postgres)
                                              ↓
                                       Cache (Redis)
                                              ↓
                             API Gateway → Authorized Services
                                              ↓
                                    Audit Logging (S3)
```

## Services

| Service | Description |
|---|---|
| `user-profile-service` | CRUD on the users table; source of truth |
| `ingestion-service` | Multi-source data ingest, normalization, dedup |
| `audit-logging-service` | Immutable R/W log consumer from Kafka |

## Quick Start

```bash
docker-compose up --build
```

Services:
- User Profile Service: http://localhost:8001/docs
- Ingestion Service: http://localhost:8002/docs
- Audit Logging Service: http://localhost:8003/docs
- Kafka UI: http://localhost:8080
- PgAdmin: http://localhost:5050

## Design

See [docs/DESIGN.md](docs/DESIGN.md) for the full system design.

## Schema

See [schema/migrations/](schema/migrations/) for all SQL migrations.
