# Principles — the smallest set we'd defend

> One page. The trust contract for an "always-on" personal data platform,
> reduced to four invariants. Written *after* reading what Hushh already
> ships, so this is not a fresh proposal — it's an alignment note.

## The question

"Always has access to user information" sounds like a storage question.
It isn't. It's a **trust** question. The interesting design decision is
not *where the data lives* — it's *what holds the user inside the loop*
when their data moves.

Reframed: how do we run agents on personal data such that the user is
always the source of permission, and the platform can prove it?

## Four invariants

The smallest set we'd defend, in plain language:

### 1. The user holds the key boundary
Keys derived on the user's device, never on the server. The server can
hold ciphertext and metadata. It must not be able to read plaintext.
*Why:* anything else makes "consent" performative — a database row the
operator can override. Cryptography is what makes consent honest.

### 2. "Signed in" is not "consented"
Identity (who is acting) and authority (what they may touch) are
separate questions and need separate tokens. A login proves identity.
A capability token proves a specific scope was granted for a specific
window of time. No code path may shortcut from one to the other.
*Why:* every consent-violation incident in industry collapses these
two. Keeping them separate eliminates a whole class of bugs.

### 3. Scope is the unit of consent, not the data category
The user does not grant access to "their data." They grant access to a
**scope** — a named slice, time-bounded, revocable, observable. Scopes
compose; data categories don't.
*Why:* "I let X read my finance data" is unauditable. "I gave X a
read-token for `attr.financial.*` that expires in 24h" is auditable.

### 4. Every consented action leaves a receipt
Every read, every write, every grant, every revocation is logged in
append-only storage the user can inspect. Audit is not a feature — it
is the proof that the other three invariants held.
*Why:* without receipts, the trust contract is a promise. With
receipts, it is a property.

## How these map to Hushh's already-shipped contract

| Invariant | Hushh's implementation |
|---|---|
| 1. Key boundary | BYOK, PBKDF2 (100k iter) client-side; backend stores `pkm_blobs` ciphertext only |
| 2. Identity ≠ consent | Firebase ID token for identity; **VAULT_OWNER** token for consent; bootstrap path is the only crossing point |
| 3. Scope as unit | `attr.{domain}.{path}` grammar; `pkm_scope_registry` + `pkm_manifest_paths`; dynamic per-user scope discovery via `/api/v1/user-scopes` |
| 4. Receipts | `pkm_events` append-only; audit tables; consent grants carry id, expiry, revocation timestamp |

The four invariants are not novel claims about Hushh — they are the
operating principles that the existing protocol enforces. Naming them
this way is useful because it gives external developers a 60-second
mental model before they touch the API.

## Where there is room to add value

Our v0 design (a Postgres + JSONB universal user store) violates three
of these four invariants. We are not going to re-pitch it. The useful
work is downstream of what's already shipped:

- A runnable **external-agent sample** that demonstrates the four
  invariants in code — get token → discover scope → request consent →
  receive ciphertext → decrypt locally → answer. Today the developer
  API has no end-to-end runnable example.
- A **Claude Desktop config** that wires the public MCP endpoint into
  Claude in 60 seconds. This is the most viscerally on-brand artifact
  the platform can ship — "Claude reads your data, with consent" — and
  nobody has built it yet.
- A **public principles note** (this document) that names the four
  invariants in language an external developer can adopt without
  reading 559 lines of `consent-protocol.md`.

## Why these invariants also make this the cheapest, fastest path

The four invariants are usually argued on trust grounds. They also
happen to be the structurally lowest-cost shape for a personal-agent
platform at scale. The argument:

| Invariant | Cost / latency consequence |
|---|---|
| **1. Key boundary on the user** | The server holds ciphertext, so per-user storage is commoditizable cold storage. No PII insurance load, no row-level encryption tax, no "right-to-erasure" infrastructure beyond a delete row. Storage cost converges to bytes-on-disk. |
| **2. Identity ≠ consent** | Capability tokens are signed and stateless. No DB lookup per request to validate a grant — verification is a signature check (microseconds). Compare to row-level security policies that re-evaluate on every read. |
| **3. Scope as the unit** | Reads return only the requested scope's ciphertext + wrapped key. No over-fetching. For LLM-fronted agents, this directly reduces input token count → reduces $/query. The platform never pays compute for "we sent more than we needed." |
| **4. Receipts** | Append-only events are write-once, query-on-demand. No periodic full-table scans, no synchronous logging that adds tail latency to the hot read. Audit becomes a cold archive cost, not a runtime cost. |

The compounding effect: the **server never decrypts**, so the server
runtime can run on cheap stateless compute, scaled per-region, with
zero per-read crypto on the platform's CPU. The connector (the
developer's agent, or the user's device) absorbs that cost — but it
absorbs it for *one user at a time*, where it is negligible. The
platform's marginal cost per read approaches the cost of one network
round-trip plus a signature verification.

That's the structural reason a consent-first platform can be faster
and cheaper than the incumbent ad-tech / data-broker model, not just
safer. The latter pays compute to read every row on every query; the
former pays compute to verify a signature and stream a blob.

This is also why the developer-facing surface needs to be tiny: the
faster a third-party agent can stand up against the platform, the
faster the platform's network effect compounds. The
[`samples/external-agent/`](../samples/external-agent/) in this repo
is a benchmark for "how small can the developer surface be" — it
boots, requests consent, decrypts, and answers in one file of HTTP
and one file of crypto.

## What this is not

- Not a proposal to change the consent protocol.
- Not a claim that the four invariants are original to us.
- Not a substitute for the canonical references in
  `consent-protocol/docs/reference/` — those remain the source of truth.

This note exists so that someone reading it cold can answer "what does
this platform actually promise the user?" in one sitting.
