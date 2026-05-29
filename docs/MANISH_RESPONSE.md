# Draft response to Manish

Drafted 2026-05-29 in response to his check-in email while he's traveling in Paris / Abu Dhabi.

---

Hey Manish,

Hope Paris is going well. Quick update on where I landed.

**The framing first.** I took your "ask once / remember forever / on
first principles" direction and reduced it to the four invariants the
platform actually has to enforce: user holds the key boundary, identity
is not consent, scope is the unit (not data category), every action
leaves a receipt. That's `hu_ssh` — Ask. Approve. Audit. — in
four lines instead of a deck. Once I named them that way, the cost
story falls out for free: ciphertext-only server is commoditized cold
storage, stateless capability tokens skip the per-request DB lookup,
scope-not-category means agents never over-fetch (so LLM token cost
tracks consent, not catalog), and append-only receipts are a cold
archive cost rather than a hot-path tax. That's the structural reason
this can be the *fastest and cheapest* personal-agent service, not
just the safest — and I wrote it up that way so external developers
read the same story.

**What I built and what I scrapped.** I started by designing a v0
"always-on user data platform" from first principles — universal
Postgres + JSONB, consent table, Redis hot-read path, Kafka backbone.
Then I read `hushh-research` end-to-end. Most of what I'd designed
already ships there in stronger form: Capability Tokens with
VAULT_OWNER + scoped + dev-token hierarchy, client-side PBKDF2 BYOK,
ciphertext-only `pkm_blobs`, the `/api/v1` developer surface, the
hosted MCP server, Agent Kai. Three of my v0's four moves contradicted
the non-negotiables in `AGENTS.md`. So I stopped building a parallel
path. (Side note: production `/health` now reports `One` as the
primary runtime with Kai as a specialist — the migration `docs/vision/`
flagged as future is already live. My work plugs in *below* all of
them as the external developer on-ramp that doesn't exist yet.)

**What I shipped this week:**

1. **A one-page principles note** — `hu_ssh` named as four invariants
   plus the cost/latency argument that falls out of them. Written so
   a new developer can answer *"what does Hussh promise the user, and
   why is it structurally cheap?"* in one sitting, without reading
   559 lines of `consent-protocol.md`.
2. **A runnable external-agent sample** — the smallest FastAPI
   personal agent that does the full developer flow against `/api/v1`:
   discover scope → request consent → poll → encrypted scoped export
   → client-side X25519 ECDH + AES-256-GCM decrypt → answer. Mock
   mode runs without a token (verified locally, full decrypt path
   exercises the documented wire shape). Live flips with one env
   var. Think of it as the smallest possible third-party "One" — what
   an outside developer ships against the platform.
3. **A Claude Desktop demo** — six-line `claude_desktop_config.json`
   that points Claude at the public MCP endpoint. The visceral
   version of `Ask. Approve. Audit.`: ask Claude, get a push on your
   phone, approve, watch Claude answer with consented data the
   server never read in plaintext.

There is no end-to-end external-developer sample in `hushh-research`
today. That was the real gap, and it's where the "few samples with
extreme ease of use" lands cleanly without duplicating shipped work.

**Verified live against production today.** I issued a dev token
through `hushh.ai/developers`, pointed the sample at the production
Cloud Run backend, and ran the full flow: token validation → scope
discovery → consent request → user approval in Kai → status
transition to `granted` with a real signed `HCT:` capability token.
Transcript with redacted tokens lives at
`samples/external-agent/RUN_LIVE.md`. While doing this, the sample
caught **three real bugs in the production developer surface**:

1. The production backend's `request-consent` response emits a
   `request_url` pointing at `uat.kai.hushh.ai` — same UAT/prod
   inline split visible in the example configs on
   `hushh.ai/developers`. A developer following the link blindly
   lands in an environment that doesn't contain their request.
2. `/health` says `One` is primary now, but `docs/vision/README.md`
   still describes the runtime as Kai-first. Docs lag the runtime.
3. **High-severity:** `scoped-export` rejects email/phone user_ids
   that every other `/api/v1` endpoint accepts. There's no
   documented way for a raw `/api/v1` caller to resolve email →
   Firebase UID. This is the loop-closing bug for any external
   developer — you can request and receive consent with an email
   but the *only* call that actually returns data rejects the same
   identifier. Two-line fix on your side (either resolve in
   scoped-export, or expose a resolve-identifier endpoint).

I'd rather discover these for you than not. The sample being the
thing that surfaced them is itself the point — that's what a real
developer on-ramp looks like.

**Workspace + code:**
- Repo: https://github.com/atishay-kasliwal/user-data-platform
- Branch: `samples/external-agent`
- Claude Code session driving the work: [will share in reply]

**One thing I want to flag honestly.** You asked me to check this
into the PR at `hushh-research`. I held off and pushed to my own
fork instead. The reason: your `AGENTS.md` is explicit about not
opening parallel paths against shipped contracts, and Kushal's
agent-revamp train (PR #615 and the open `kushaltrivedi/*` branches)
is actively in motion in the same surface area. Opening a PR there
without first aligning on placement (is this `samples/` in the
monorepo, or a separate `hushh-labs/hushh-agent-sample` you can
point developers at?) seemed worse than asking. I can open the PR
as soon as you say go — happy to default to your call.

**Three things I'd like from you to close the loop:**

1. **Landing surface.** PR into `hushh-research` under
   `samples/external-agent/` + `samples/claude-desktop/`, or carve
   it out as a standalone `hushh-labs/hushh-agent-sample` repo? I
   have a preference for standalone (clean visibility, doesn't add
   to the PR train), but I'll do whichever you want.
2. **`HUSHH_DEVELOPER_TOKEN`** in UAT, or a pointer to someone with
   a vault I can read for testing. Live mode is wired and verified
   in mock; only env is missing.
3. **The original problem statement** — you referenced *"the problem
   statement I had given"* but I don't have it saved. Could you
   resend? Want to make sure the principles note maps cleanly
   instead of paraphrasing.

**Where this goes next.** I sketched a 90-day plan in
`docs/05_roadmap.md` — seven tiles, each shippable on its own. T1 is
"flip mock to live against UAT and capture the wire trace." T4 is
"docs-only PR to `hushh-research` adding the principles + on-ramp,
no `consent-protocol/` changes." T7 is "agent template registry, the
Hushh equivalent of `awesome-mcp-servers`." Mostly waiting on (1) and
(2) above to start sequencing for real.

Happy to hop on a call when you're back, or keep going async. I
won't push to `consent-protocol/` without alignment with Kushal —
his revamp is on my radar.

Best,
Atishay
