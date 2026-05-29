# user-data-platform

> External-agent samples and design notes for [Hushh](https://github.com/hushh-labs/hushh-research).

This repo started as a from-scratch design for an "always-on user
data platform." After reading
[hushh-labs/hushh-research](https://github.com/hushh-labs/hushh-research),
it became clear that the platform thesis (consent-first, BYOK,
zero-knowledge, scoped capability tokens) is already shipped there in
production form. So this repo was repurposed:

- A short **principles note** that names the trust contract in plain
  language: [`docs/04_principles.md`](docs/04_principles.md).
- A runnable **external-agent sample** that consumes the public
  `/api/v1` developer API + decrypts a scoped export client-side:
  [`samples/external-agent/`](samples/external-agent/).
- A 60-second **Claude Desktop demo** that wires the public MCP
  endpoint into Claude: [`samples/claude-desktop/`](samples/claude-desktop/).

## What's in `docs/`

| File | Purpose |
|---|---|
| [`01_hushh_findings.md`](docs/01_hushh_findings.md) | What's in the upstream Hushh repo — stack, trust contract, shipped pieces, token model, agent ontology, layers, operating rules. |
| [`02_gap_analysis.md`](docs/02_gap_analysis.md) | Side-by-side of the original v0 design vs. what Hushh already ships; conflicts and real gaps. |
| [`03_plan.md`](docs/03_plan.md) | Decision, deliverables, sequencing, open questions. |
| [`04_principles.md`](docs/04_principles.md) | The four invariants — one-page mental model. |
| [`MANISH_RESPONSE.md`](docs/MANISH_RESPONSE.md) | Draft reply to Manish referencing the above. |

## What's in `samples/`

| Path | What it is |
|---|---|
| [`external-agent/`](samples/external-agent/) | FastAPI agent that runs the full `/api/v1` flow end-to-end: discover scope → request consent → poll → encrypted export → client-side X25519+AES-GCM decrypt → answer. Mock mode runs without a developer token. |
| [`claude-desktop/`](samples/claude-desktop/) | `claude_desktop_config.json` snippet + README for the visceral "Claude reads my consented vault" demo. |

## Verified end-to-end

- `samples/external-agent/` mock mode runs locally, exercises the
  documented X25519-AES256-GCM decrypt path against a wire-shape
  correct synthetic export — see
  [`samples/external-agent/RUN.md`](samples/external-agent/RUN.md).
- Live mode requires a `HUSHH_DEVELOPER_TOKEN` from
  `https://uat.kai.hushh.ai/developers`. No code changes — env only.

## What this repo is not

- Not a fork or replacement of `hushh-research`. It is a downstream
  consumer.
- Not an attempt to redesign the consent protocol. That document lives
  upstream at
  [`consent-protocol/docs/reference/consent-protocol.md`](https://github.com/hushh-labs/hushh-research/blob/main/consent-protocol/docs/reference/consent-protocol.md).
- Not a finished product. It is the smallest readable surface that
  helps an external developer understand and exercise the platform.
