# Draft response to Manish

Drafted 2026-05-29 in response to his check-in email while he's traveling in Paris / Abu Dhabi.

---

Hey Manish,

Hope Paris is going well. Quick update.

**Core principle (after our conversation):** the system reduces to a universal Postgres table — one row per user, JSONB columns for infinitely extensible attributes — with a trust/consent layer on top, Redis as the hot read path, and Kafka as the event bus. No new infrastructure invented, no schema migrations as new categories of personal data show up, and "ask once / remember forever" consent is persisted as a real DB row (not a JWT claim or config flag). Redis is what services actually read; Postgres is durable truth but never the hot path. That's how we deliver low-latency "always has access" at 8B-user scale from day zero.

**Built, tested live, and pushed:** https://github.com/atishay-kasliwal/user-data-platform

- `docs/DESIGN.md` — full design with read/write paths, scaling strategy, security model
- SQL migrations — `users`, `user_history`, `consent_grants` with RLS policies
- Three FastAPI services — Profile (CRUD + history + consent), Ingestion (multi-source normalize + dedup), Audit Logging (Kafka consumer)
- `docker-compose.yml` — full local stack: Postgres, Redis, Kafka, plus PgAdmin and Kafka UI
- End-to-end verified locally: create → cache hit/miss → scoped read → ingest from oauth_profile + location → merged state → history → audit log via Kafka. Summary table in the README.

**Next steps I'd like to take:**

1. Drop me the research repo URL (you mentioned a PR there) and I'll mirror this work into a PR structured the way your team prefers.
2. Happy to add the day-zero "claim" flows we discussed (NFC tag, OAuth-prefilled row, etc.) once we align on which surfaces to ship on first.
3. Short sync with Kushal whenever convenient so I'm not duplicating against Hussh's One architecture.

Using Claude Code as my day-to-day workspace — happy to share session links if useful.

Best,
Atishay
