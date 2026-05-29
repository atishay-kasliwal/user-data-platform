# Draft response to Manish

Drafted 2026-05-29 in response to his check-in email while he's traveling in Paris / Abu Dhabi.

---

Hey Manish,

Hope Paris is going well. Quick update.

**What I did first.** I designed a v0 "always-on user data platform"
from first principles, ended up at a universal Postgres + JSONB table
with a consent table, Redis hot-read path, and Kafka backbone.

**Then I read the upstream `hushh-research` repo.** Most of what I'd
designed already ships there in stronger form — Capability Tokens
with VAULT_OWNER + scoped + dev-token hierarchy, BYOK with
client-side PBKDF2, ciphertext-only `pkm_blobs` and segmented PKM,
the `/api/v1` developer surface, the hosted MCP server, and Agent
Kai. Three of my v0's four moves directly contradicted the
non-negotiables in your `AGENTS.md` (server stored plaintext, no key
boundary, scope-as-row instead of scope-as-token). So I stopped
building a parallel path and sequenced around the existing trust
contract instead.

**What I shipped this week, in this repo:**

1. A one-page **principles note** — the four invariants of the trust
   contract in plain language, aligned with what
   `consent-protocol/docs/reference/consent-protocol.md` already
   encodes. Written so a new developer can answer "what does this
   platform promise the user?" in one sitting.
2. A runnable **external-agent sample** — the smallest FastAPI
   personal agent that does the full developer flow: discover scope
   → request consent → poll → encrypted scoped export → client-side
   X25519 ECDH + AES-256-GCM decrypt → answer. Mock mode runs without
   a token (verified locally, full decrypt path exercises the
   documented wire shape). Live mode flips with one env var.
3. A **Claude Desktop demo** — six-line `claude_desktop_config.json`
   that points Claude at the public MCP endpoint. The visceral
   version of the invariants: ask Claude, get a push on your phone,
   approve, watch Claude answer with consented data the server never
   read in plaintext.

This is the "extreme ease of use with a few samples" surface you
asked for. There is no end-to-end external-developer sample in
`hushh-research` today — that was the real gap.

**Repo + workspace:**
- Code: https://github.com/atishay-kasliwal/user-data-platform
- Branch with this week's work: `samples/external-agent`
- Claude Code session driving the work: [will share in reply]

**Three questions before I land it in your research repo:**

1. Do you want this PR'd into `hushh-research` as
   `samples/external-agent/` and `samples/claude-desktop/`, or kept
   as a standalone `hushh-labs/hushh-agent-sample` you can point
   developers at independently?
2. Can your team issue me a `HUSHH_DEVELOPER_TOKEN` in UAT (or point
   me at someone with a vault I can read for testing)? Live mode is
   ready; only env is missing.
3. You mentioned the problem statement you'd given me — could you
   resend it? I want to make sure the principles note maps to it
   directly rather than paraphrasing.

Happy to hop on a call when you're back, or keep going async — I'm
making progress every day. Will not push to `consent-protocol/`
without alignment with Kushal; his recent revamp (PR #615) is on my
radar.

Best,
Atishay
