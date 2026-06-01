# 90-day roadmap

> What ships after the sample. Sequenced so each tile multiplies the
> value of the next one. Every tile is scoped so an external developer
> reading it cold knows what they get and what they have to do.

## Guiding question

What would make Hushh the *first* platform a developer reaches for
when they need to build a personal-data agent? The samples in
[`../samples/`](../samples/) prove the on-ramp can be small. The next
90 days is about making the on-ramp *unavoidable*.

## Tiles

### T0 — Sample agent + Claude Desktop demo (shipped)
Already in this repo. Mock mode runs in 60 seconds. Live mode needs
a developer token. Anchors every later tile.

### T1 — Live verification against UAT (days 1–3)
- Plug in the `HUSHH_DEVELOPER_TOKEN`, run the sample end-to-end
  against `api.uat.hushh.ai`.
- Capture the live trace in `samples/external-agent/RUN_LIVE.md`:
  real request/response payloads, real timings, real ciphertext.
- Validate: does `/api/v1/consent-status` use SSE or polling? Is
  there a webhook surface I missed? Update the sample if so.
- Outcome: the sample stops being "shape-only correct" and becomes
  "wire-verified correct."

### T2 — One-line bootstrap for external devs (week 1)
- Single-command `npx @hushh/agent-sample` or `pip install hushh-agent
  && hushh-agent serve` that does what the current sample does, with
  zero clone-and-edit. Drop-in for anyone evaluating the platform in
  five minutes.
- Coordinate with whoever owns `@hushh/mcp` (npm) so the agent sample
  lives next to it in the developer story.
- Outcome: "I've heard about Hushh, what does it look like to build
  on it?" → answer is a one-liner.

### T3 — Third-party "tiny One" reference (weeks 2–3)
- The sample today summarizes one scope. Extend it into a small
  conversational agent that handles multi-turn memory across
  consented scopes (`attr.financial.*` + `attr.personal.profile.*`),
  with explicit consent re-prompts when the conversation drifts.
- Use the same agent ontology language as `docs/vision/`: this is
  what an external developer's "One-shaped" personal agent looks
  like on top of Hushh.
- Outcome: developers see the *shape* of a personal agent they can
  ship next week, not just an API client.

### T4 — Developer on-ramp docs in `hushh-research` (weeks 3–4)
- One docs-only PR to `hushh-research` adding
  `docs/external-developer-onramp.md` — the principles note +
  pointers to the sample + the Claude Desktop config. Zero code
  changes to `consent-protocol/`.
- This is the minimum PR shape that respects `AGENTS.md` while
  making the sample discoverable from the upstream README.
- Outcome: a new developer landing on `hushh-research` finds the
  on-ramp without me having to email them.

### T5 — Cost dashboard (weeks 4–6)
- Instrument the sample to emit OpenTelemetry traces. Build a small
  one-page dashboard (Grafana or hosted) that shows per-request:
  decrypt cost, HTTP cost, LLM token cost, total $/query.
- Publish a short note: *"What does one Hushh agent query cost?"*
  Concrete numbers, no marketing.
- Outcome: the "fastest / cheapest" claim in
  [`04_principles.md`](./04_principles.md) becomes a measurement,
  not a marketing line.

### T6 — Mobile parity sample (weeks 6–8)
- Add an iOS / Android shell (Capacitor) that does the same flow as
  the FastAPI sample — receive the push, approve, decrypt locally,
  show the answer. Aligns with the tri-flow parity rule in
  `project_context_map.md`.
- Outcome: the "personal agent" story is end-to-end visible across
  all three surfaces Hushh already supports.

### T7 — Agent registry sample (weeks 8–12)
- Build a small `agents/` repo: a curated list of external agent
  templates that consume Hushh (finance summary, calendar triage,
  document QA), each one a fork of the base sample.
- Treat it as the Hussh equivalent of the `awesome-mcp-servers` list —
  a public artifact that compounds attention.
- Outcome: developers don't start from zero. They start from a
  template that already speaks Hushh.

## Dependencies

| Tile | Blocked by |
|---|---|
| T1 | `HUSHH_DEVELOPER_TOKEN` (Manish or team) |
| T3 | T1 verified; sync with Kushal on the One ontology timeline |
| T4 | T1 verified; placement decision (samples/ in monorepo vs. standalone repo) |
| T5 | T1 + a tiny budget for hosted observability |
| T6 | Coordination with the mobile lead in `hushh-webapp/` |
| T7 | T2 done so the base template is npm-installable |

## What I'm explicitly not promising

- Changes to `consent-protocol/` itself — Kushal's PR train is moving
  there and any contribution from me belongs after an alignment chat,
  not before.
- A consent UI redesign — Nav is the right owner once that runtime
  surface lands.
- Anything that touches the trust contract. The four invariants are
  the bedrock and my work sits on top of them.

## How to read this

Each tile is a self-contained ship-able artifact. If only the first
three happen, the developer story is already meaningfully better
than what `hushh-research` exposes today. The later tiles are
multipliers, not prerequisites.

The success metric is not "I shipped seven things." It's: *the time
between a developer hearing about Hushh and shipping a working
personal-data agent against it drops from days to one afternoon.*
That number is the lever on the platform's network effect.
