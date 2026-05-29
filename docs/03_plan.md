# Plan

## Decision

**Repurpose `user-data-platform/` into a runnable external-agent sample for Hushh.**

Three deliverables for Manish, in priority order:

### 1. A one-page "principles" note (`docs/04_principles.md`)
A short artifact that says, in our own words:
- The four non-negotiables we now see in Hushh (BYOK, ciphertext-only, capability tokens, scoped consent).
- How our v0 thinking aligned and where it didn't.
- The smallest contribution boundary we can occupy without duplicating shipped work.

This answers Manish's *"core system + design principles + proposed solutions."*

### 2. A runnable sample agent (`samples/external-agent/`)
The smallest possible "personal agent" that uses Hushh from the outside:
- Reads `HUSHH_DEVELOPER_TOKEN` from env.
- `GET /api/v1/user-scopes/{user_id}` to discover scopes for a user.
- `POST /api/v1/request-consent` for `attr.financial.*` (or similar).
- Polls `GET /api/v1/consent-status` until approved.
- `POST /api/v1/scoped-export` to get encrypted ciphertext + wrapped key.
- Client-side X25519 unwrap + AES decrypt.
- Calls an LLM with the decrypted scope-data and answers a question.
- One-command bring-up: `docker compose up`. README in <60 lines.

This answers Manish's *"extreme ease of use with a few samples"* and *"fastest / cheapest personal agent service."*

### 3. A Claude Desktop config snippet (`samples/claude-desktop/`)
A `claude_desktop_config.json` pointing at `https://api.uat.hushh.ai/mcp/?token=…`, with a short README showing how to ask Claude *"summarize my Hushh financial scope"* and watch it execute with consent.

This is the **visceral demo** — "Claude reading your data, with consent." On-brand and fast.

## What we are *not* doing

- Not opening a PR to `consent-protocol/`. That subtree is under heavy PR-train governance; touching it without context risks failing their review SOP.
- Not building a parallel data store, parallel consent table, parallel Kafka pipeline. They exist already and we'd violate AGENTS.md.
- Not promising functionality we haven't verified end-to-end against the live UAT endpoint.

## Where the work lives

- **For now:** stays in `user-data-platform/` (this repo) under `samples/`. Old scaffold gets deleted as part of the repurpose.
- **Once it works end-to-end:** offer to PR it into `hushh-research` at `samples/external-agent/`. Decision to merge is theirs. If they prefer it as a standalone `hushh-labs/hushh-agent-sample` repo, that's fine too.

## What we need from Manish before we can finish

1. **The original problem statement.** His email references *"the problem statement I had given"* — we have no record of it. Best to ask rather than guess.
2. **A `HUSHH_DEVELOPER_TOKEN`** issued at `https://uat.kai.hushh.ai/developers` (or shared from his team). Without it, the sample can be shape-only — fillable when the token arrives.
3. **A preference on landing surface:** PR into `hushh-research` vs. standalone repo vs. just a workspace link.

## What goes in the email to Manish

A short reply, ~12 lines, that:
- Acknowledges the prior conversation and his direction.
- States honestly: *"I started from first principles. Then I read the upstream repo and saw most of what I'd designed already shipped. So I sequenced around the existing trust contract."*
- Links three artifacts: (a) the principles note, (b) the runnable sample (link to repo or a recorded run), (c) the Claude Desktop demo.
- Asks the three questions above.
- Offers the Claude Code session link as the workspace.

## Implementation sequence

1. Delete obsolete scaffolding in `user-data-platform/` (services, schema, docker-compose). Keep this `docs/` folder.
2. Write `docs/04_principles.md` (one page).
3. Build `samples/external-agent/` in shape-only mode (mockable HTTP client). README + Dockerfile.
4. Build `samples/claude-desktop/` config + README.
5. When a developer token is available: end-to-end run against `api.uat.hushh.ai`, capture transcript in `samples/external-agent/RUN.md`.
6. Revise `docs/MANISH_RESPONSE.md` against this new reality.
7. Push to a clean branch in `atishay-kasliwal/user-data-platform`, share link with Manish.
