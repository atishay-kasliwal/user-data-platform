# What's in `hushh-research` (upstream)

> Snapshot from reading `github.com/hushh-labs/hushh-research` on 2026-05-29.
> The repo is **not** a research workspace — it's the shipped Hushh product monorepo.

## Project at a glance

- **Name:** Hushh (public brand; legacy code still says "Hushh" / "Hussh" — same thing, mid-rename).
- **Tagline:** *"Consent-first personal data agents — Your data. Your vault. Your agents."*
- **Stack:** Python 3.13 + FastAPI + Google ADK + Supabase backend; Next.js 16 + Capacitor for web/iOS/Android.
- **Standards:** Google A2A (Agent-to-Agent), MCP (Model Context Protocol). Public MCP server at `https://api.uat.hushh.ai/mcp/`.
- **License:** Apache 2.0. npm package: `@hushh/mcp`.

## The trust contract (non-negotiable)

1. The user holds the key boundary (BYOK, PBKDF2 100k client-side derivation).
2. The backend stores **ciphertext only** + metadata. Never plaintext user memory.
3. Scopes (capability tokens) decide what agents may touch.
4. Apps and agents execute only inside granted consent.

## Already shipped

| Piece | Path | Status |
|---|---|---|
| Consent Protocol (signed tokens, VAULT_OWNER, agent-scoped, dev-token, revocation, audit) | `consent-protocol/api/` | Production (Feb 2026) |
| BYOK + zero-knowledge vault (PBKDF2 100k → AES, X25519-AES256-GCM export wrap) | `consent-protocol/`, webapp | Shipped |
| PKM (encrypted segmented blobs, manifests, scope registry, append-only events, revocable safe projections) | `consent-protocol/hushh_mcp/` | Shipped |
| Developer API `/api/v1` (dynamic scope discovery → request consent → poll → encrypted scoped export) | `consent-protocol/api/` | UAT public beta |
| Hosted MCP server (external AI agents read user data with consent) | `api.uat.hushh.ai/mcp/` | UAT live |
| `@hushh/mcp` npm bridge | `packages/hushh-mcp/` | Published |
| Agent Kai (finance specialist; multi-agent debate engine) | `consent-protocol/hushh_mcp/agents/` | Shipped (Kushal revamped via PR #615) |
| Self-serve developer portal at `/developers` | webapp | Live in UAT |

## Token hierarchy (the actual consent model)

| Token | Purpose | TTL |
|---|---|---|
| Firebase ID token | Identity only — used to bootstrap VAULT_OWNER | 1h |
| **VAULT_OWNER token** | Identity + consent + vault unlock; gates **all** data routes | 24h |
| Agent-scoped token | Third-party agent operations | 7d |
| Developer token | External `/api/v1` callers | Self-managed via portal |

Rule they encode: *"signed in" is not consent.* No dev/test bypasses on consent paths.

## Agent ontology (the product)

| Name | Role | Status |
|---|---|---|
| Hushh | Platform, trust model, infra | — |
| **One** | Top-level personal agent (relationship layer: listens, remembers, decides, acts) | Roadmap; runtime still Kai-first |
| **Kai** | Finance specialist (portfolio, market, debate-driven analysis) | Shipped |
| **Nav** | Privacy / consent guardian | Future runtime |

Founder shorthand: **hu_ssh = SSH for humans. Ask. Approve. Audit.**

## 7-layer architecture (canonical)

1. Infrastructure (runtime, deploy, secrets, CI)
2. Core Platform Services (FastAPI domain services)
3. Trust, Identity, Governance (auth, vault unlock, capability tokens, consent, audit)
4. Data + Knowledge (encrypted PKM blobs, workflow DB, caches, provenance)
5. Intelligence + Agent (Kai agents, ADK, operons, debate)
6. Experience (web, iOS, Android, voice, search, action surfaces)
7. Channels (Kai, RIA, MCP, developer API, external hosts)

## Operating constraints we have to respect

From `AGENTS.md` (verbatim, paraphrased):
- *"Do not write as if the project is blank. Hushh already has many shipped contracts."*
- *"If the capability already exists, do not propose a parallel path. Extend or harden the existing contract."*
- *"Smallest acceptable next PR."*
- Premise verification gate: classify every claim as `already_exists`, `partially_exists`, `missing`, `future_state_only`, etc. before responding.
- Multiple AI agents (Claude, Codex, Qwen, Copilot) work in this repo with a formal delegation router.
- PR-train governance is active. Kushal is shipping heavily (`kushaltrivedi/*` branches).

## Volume / velocity context

- Local fork was 598 commits behind upstream main when we synced (2.5 weeks of activity).
- Recent merged work: mobile vault + debate hardening, iOS 1.3.5 release, native UI flow contracts, Kai E2E hardening, PKM event migration replay, RIA streaming.
- Kushal's most recent merge into main: `kushaltrivedi/feat/agent-kai-revamp` (PR #615).

## What's *not* in the repo (the real gap)

- **No runnable external-developer sample agent.** The `@hushh/mcp` README is wire-level only. `hushh-webapp/public/demo-mode/` is just a JSON template for the webapp. There is no end-to-end "external agent that consumes the consent protocol + MCP server" example you can clone and run.
- Onboarding for a developer wanting to *use* Hushh from outside currently requires reading 559 lines of `consent-protocol.md` and figuring it out.
