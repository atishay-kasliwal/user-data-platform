# user-data-platform

> A runnable client for consent-based, zero-knowledge personal data
> access — an external agent that requests a user's consent, receives
> an encrypted export, and decrypts it **client-side** so the data
> provider's server never sees plaintext.

Built against [Hushh](https://github.com/hushh-labs/hushh-research)'s
public developer API. Demonstrates: applied cryptography (X25519 ECDH +
AES-256-GCM), async API client design, and a security model where
consent is enforced by math, not by a database flag.

## Try it in 30 seconds

```bash
git clone <this-repo> && cd user-data-platform/samples/external-agent
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
MODE=mock LLM_PROVIDER=stub .venv/bin/uvicorn main:app --port 8765
```

```bash
curl -s -X POST http://127.0.0.1:8765/ask \
  -H 'content-type: application/json' \
  -d '{"scope":"attr.financial.*","question":"what were my biggest losers?"}'
```

No account or API key needed — mock mode runs the full flow, including
real decryption, against a synthetic export. See
[`samples/external-agent/RUN.md`](samples/external-agent/RUN.md) for
the verified output.

## The flow

```
discover scope → request consent → poll for approval →
fetch encrypted export → decrypt client-side (X25519 + AES-256-GCM) →
answer the question
```

The connector's private key is generated at process start and never
leaves it. The server holds ciphertext only — it has no ability to
read the data it's transporting, by construction, not by policy.

## What's in this repo

| Path | What it is |
|---|---|
| [`samples/external-agent/`](samples/external-agent/) | FastAPI agent implementing the flow above end-to-end. Mock mode needs nothing; live mode needs a `HUSHH_DEVELOPER_TOKEN`. |
| [`samples/claude-desktop/`](samples/claude-desktop/) | Config snippet wiring the same consented vault into Claude Desktop via MCP. |
| [`docs/`](docs/) | Design notes: findings from the upstream protocol, a gap analysis against an earlier from-scratch design, the four trust invariants, and a 90-day roadmap. Start with [`docs/04_principles.md`](docs/04_principles.md) for the one-page mental model. |

## Verified

- Mock mode: runs locally, no external calls, exercises the full
  decrypt path (ECDH → SHA-256 → AES-GCM unwrap → AES-GCM decrypt)
  against a wire-shape-correct synthetic export —
  [`samples/external-agent/RUN.md`](samples/external-agent/RUN.md).
- Live mode: implemented against the documented `/api/v1` contract;
  requires a `HUSHH_DEVELOPER_TOKEN` from
  `https://uat.kai.hushh.ai/developers` to run against real data — see
  [`samples/external-agent/RUN_LIVE.md`](samples/external-agent/RUN_LIVE.md).

## Background

This started as an original design for an "always-on user data
platform." Once it became clear the same thesis — consent-first, BYOK,
zero-knowledge, scoped capability tokens — already ships in production
at [hushh-labs/hushh-research](https://github.com/hushh-labs/hushh-research),
this repo was repurposed into a downstream client and a plain-language
explanation of that trust model, rather than a competing design. The
reasoning behind that call is in [`docs/02_gap_analysis.md`](docs/02_gap_analysis.md)
and [`docs/03_plan.md`](docs/03_plan.md).

## What this repo is not

- Not a fork or replacement of `hushh-research` — it's a downstream
  consumer.
- Not a proposal to change the consent protocol. That lives upstream
  at [`consent-protocol/docs/reference/consent-protocol.md`](https://github.com/hushh-labs/hushh-research/blob/main/consent-protocol/docs/reference/consent-protocol.md).
- Not a finished product — the smallest readable surface for
  understanding and exercising the platform as an external developer.
