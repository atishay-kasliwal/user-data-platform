# Gap analysis — `user-data-platform` vs. Hushh

## Side-by-side

| Concern | What we built in `user-data-platform` | What Hushh already ships | Verdict |
|---|---|---|---|
| User store | Postgres `users` table with **plaintext JSONB** columns | `pkm_blobs` — ciphertext-only segments keyed by `(user_id, domain, segment_id)` | **Conflict.** Hushh's non-negotiable #1: server stores ciphertext only. Ours stores plaintext. |
| Consent model | `consent_grants(user_id, grantee_id, scope[], expires_at, revoked_at)` | Cryptographically signed Capability Tokens; VAULT_OWNER + agent-scoped + dev-token hierarchy; PCHP flow | **Conflict.** Theirs is a token protocol; ours is a DB lookup. |
| Read path | Redis cache → Postgres on miss; service reads return plaintext | Client-side decrypt; server only returns ciphertext + wrapped key | **Conflict.** Server-readable cache violates zero-knowledge. |
| Write path | UPS transaction (`UPDATE users` + `INSERT user_history`) | Encrypted segment upsert via `/store-domain`; manifest + scope registry + events | Parallel path. They already do this. |
| Event bus | Kafka, 5 topics, audit consumer to stdout | `pkm_events` append-only table + audit rows + provenance ledger | Parallel path. They already do this. |
| Ingestion | FastAPI `ingestion-service` with per-source normalizers (OAuth, document, partner webhook, location) | Provider orchestration in `consent-protocol/` (Plaid, Gmail, market, etc.) gated by consent | Parallel path. Their version is consent-gated; ours is not. |
| Audit log | Kafka → stdout (S3 in prod) | `pkm_events` + audit tables; export revisions; data-provenance ledger | Parallel path. |
| Agent surface | None — we have no agent layer | Kai (shipped), One (roadmap), Nav (future). Google ADK runtime, A2A delegation, debate engine. | **Missing entirely in our work.** |
| BYOK / key boundary | None | Client-side vault key (PBKDF2 100k); browser memory-only; X25519 export wrap | **Missing entirely in our work.** |
| Mobile parity | None | Tri-flow web + iOS + Android via Capacitor | **Missing.** Out of scope for any sample we'd build. |

## Summary

- Our user-data-platform is **structurally a non-encrypted shadow** of what Hushh already has.
- Of the 4 non-negotiables in their architecture, our design violates 3.
- Of the 7 architecture layers, our work touches layers 2–4 with a *less safe* implementation. We do not touch layers 1, 5, 6, 7 at all.
- We cannot PR `user-data-platform/` into `hushh-research` as a contribution. It would fail the AGENTS.md premise-verification gate as a "parallel path that contradicts shipped contracts."

## What *is* missing (and would be a real contribution)

| Gap | Why it matters | Who'd use it |
|---|---|---|
| **End-to-end external-agent sample** that consumes the public `/api/v1` developer API + `@hushh/mcp` | Manish asked for "extreme ease of use with samples." This is exactly that surface, and the repo has no runnable example. | External developers, demo-able to investors. |
| Claude Desktop / Claude Code config that points at `https://api.uat.hushh.ai/mcp/` so the user can see "Claude reads my consented vault" in 60 seconds | The most viscerally on-brand artifact possible for the company. Nobody has shipped this yet. | Anyone wanting the "wow" moment. |
| A short "principles" writeup that names the trust contract in language compatible with `docs/vision/` | Manish explicitly asked for "core system + design principles." | Internal alignment + Manish's check-in. |

## What we keep from `user-data-platform/`

- FastAPI + Dockerfile scaffolding pattern (works, tested).
- The mental clarity from having designed a v0 ourselves — useful for the principles writeup.

## What we delete or repurpose from `user-data-platform/`

- The Postgres `users` / `user_history` / `consent_grants` tables and their migrations.
- The Redis cache + Kafka topics + audit-logging service.
- The `user-profile-service` (it's a clone of `consent-protocol/` and contradicts its trust model).
- The `ingestion-service` — replace it with a sample agent that *consumes* Hushh's APIs instead of writing into a private store.
