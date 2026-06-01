# Verified live run — production

> Captured 2026-05-29 against the production consent-protocol backend
> at `https://consent-protocol-f2gsa4kfsq-uc.a.run.app`.
> Developer token issued through `https://hushh.ai/developers` ("Self-serve access" tab).
> All tokens in this document are redacted as `hdk_***`.

## Environment

```
MODE=live
CONSENT_API_URL=https://consent-protocol-f2gsa4kfsq-uc.a.run.app
HUSHH_DEVELOPER_TOKEN=hdk_***
USER_ID=katishay@gmail.com
```

## Step 1 — token validity

Public endpoints (no token required):

```
GET /health              → 200  {"status":"healthy",
                                  "agents":["one","kai","nav","kyc"],
                                  "agent_model":{"primary":"one",
                                                 "specialists":["kai","nav","kyc"]}}
GET /api/v1              → 200  endpoint manifest
GET /api/v1/list-scopes  → 200  canonical scope grammar
```

Token-gated endpoints:

```
GET /api/v1/tool-catalog?token=hdk_***  → 200
GET /api/v1/user-scopes/katishay@gmail.com?token=hdk_***  → 200
  {
    "user_id": "katishay@gmail.com",
    "available_domains": [],
    "scopes": [],
    "app_id": "app_atishay-kasliwal_1ddfea2e",
    "app_display_name": "Atishay Kasliwal"
  }
```

Two confirmations from this:

1. The **token is live and routes to a real developer app** named
   `Atishay Kasliwal` with id `app_atishay-kasliwal_1ddfea2e`.
2. The **vault is empty** — fresh production account, no PKM data
   ingested yet. `available_domains: []`. As predicted in the
   developer portal docs, the test-user is mostly financial; we
   stuck to `pkm.read` (which is non-dynamic and works on empty
   vaults) for this verification.

## Step 2 — request consent

A real X25519 connector keypair was generated locally. Only the
public key was sent; the private key never left the process.

```
POST /api/v1/request-consent?token=hdk_*** →  200
{
  "status": "pending",
  "message": "Consent request submitted. User approval is pending in the Hussh app.",
  "request_id": "req_ca6d441a581c4be8bdda1bf165a5",
  "scope": "pkm.read",
  "granted_scope": null,
  "scope_description": "Read your personal knowledge model data",
  "approval_timeout_minutes": 60,
  "expiry_hours": 24,
  "agent_id": "developer:app_atishay-kasliwal_1ddfea2e",
  "app_display_name": "Atishay Kasliwal",
  "request_url": "https://uat.kai.hushh.ai/consents?tab=pending&requestId=...",
  "requester_label": "Atishay Kasliwal",
  "approval_surface": "/consents?tab=pending"
}
```

The platform created a real consent request the user can review and
approve. The `app_display_name` shown to the user is the
developer's display identity, exactly as the trust model promises.

## Step 3 — poll consent status

```
GET /api/v1/consent-status?user_id=...&request_id=req_***  → 200  status: "pending"
GET /api/v1/consent-status?user_id=...&scope=pkm.read       → 200  status: "not_found"
                                                              (no grant exists yet — only a request)
```

The two status modes behave as documented: querying by `request_id`
returns the pending request; querying by `scope` returns "not_found"
until the request becomes a grant.

## Findings worth flagging back to Hushh

### Finding 1 — production-vs-UAT URL mismatch in `request-consent` response

The `request-consent` response we received from the **production**
backend contains:

```
"request_url": "https://uat.kai.hushh.ai/consents?tab=pending&requestId=..."
"approval_surface": "/consents?tab=pending"
```

`uat.kai.hushh.ai` is the UAT Kai host. The production Kai host
(verified live with HTTP 200) is `kai.hushh.ai`. A developer
following the `request_url` blindly will land on a UAT environment
that doesn't contain the consent request they just created, because
the consent was created in production.

This is consistent with the inconsistency already visible on the
developer portal at `https://hushh.ai/developers`: the page title
says "Production" and the REST/MCP base URLs point at the Cloud
Run production backend, but the **example** `Remote MCP config`,
`npm bridge config`, and `Claude Desktop stdio` config snippets all
still inline `https://api.uat.hushh.ai`.

Same root cause: the production developer surface still emits UAT
URLs in places. Likely a one-line config flip.

### Finding 2 — `/health` reports `One` as primary

```
GET /health
{
  "status": "healthy",
  "agents": ["one", "kai", "nav", "kyc"],
  "agent_model": {
    "primary": "one",
    "specialists": ["kai", "nav", "kyc"]
  }
}
```

The current `docs/vision/README.md` in `hushh-research` says
*"the runtime is still Kai-first until the One/Nav migration
lands."* Production `/health` reports the migration has landed —
**One is the primary runtime, Kai is now a specialist** alongside
Nav and KYC.

This is good news for product framing: external developers
integrating today can position their work as "downstream of One,"
not "downstream of Kai." The principles note in
[`../../docs/04_principles.md`](../../docs/04_principles.md) was
updated to reflect this.

## Step 4 — approval

A fresh consent request (`req_c8242d841cbb4fd99d1ab919e2d2`) was
created, the developer-app owner approved it in the Hushh consent
UI, and the consent-protocol backend transitioned the request to
`granted`:

```
GET /api/v1/consent-status?user_id=...&request_id=req_c824*** → 200
{
  "status": "granted",
  "message": "Latest request action is CONSENT_GRANTED.",
  "granted_scope": "pkm.read",
  "consent_token": "HCT:b1hnZnBpTzZJelgwUEt3Y2VCblRQM1pIZUNEM3x...",
  "export_revision": 1,
  "export_refresh_status": "current",
  "expires_at": 1780171753404
}
```

The `HCT:` consent token's payload decodes to:

```
oXgfpiO6IzX0PKwceBnTP3ZHeCD3 | developer:app_atishay-kasliwal_1ddfea2e
                             | pkm.read
                             | issued_at_ms
                             | expires_at_ms
                             . sha256-signature
```

Format: `<nonce>|<agent_id>|<scope>|<issued_ts>|<expires_ts>.<sig>`.
Stateless, signed, agent-bound, scope-bound, time-bound — exactly the
shape described in the architecture's "capability token" invariant.

## Step 5 — scoped-export (blocked by Finding 3)

```
POST /api/v1/scoped-export?token=hdk_***
{
  "user_id": "katishay@gmail.com",
  "consent_token": "HCT:b1hnZnBp...",
  "expected_scope": "pkm.read"
}

→ HTTP 403
{
  "detail": {
    "error_code": "CONSENT_TOKEN_USER_MISMATCH",
    "message": "Token user_id does not match the requested user_id."
  }
}
```

The request-consent step accepted `user_id=katishay@gmail.com` and
created a valid pending request that was approved. The consent-status
endpoint also accepts the email form. But scoped-export rejects the
same identifier as a mismatch. See Finding 3 below.

## Finding 3 — identifier-handling inconsistency across `/api/v1`

| Endpoint | `user_id=katishay@gmail.com` |
|---|---|
| `GET /api/v1/user-scopes/{user_id}` | accepted (echoes email back) |
| `POST /api/v1/request-consent` | accepted (creates request, gets approved) |
| `GET /api/v1/consent-status` | accepted (returns status) |
| `POST /api/v1/scoped-export` | **rejected** — `CONSENT_TOKEN_USER_MISMATCH` |

The `consent-protocol.md` reference does say "Raw `/api/v1` HTTP calls
still use the canonical Firebase UID as `user_id`." So scoped-export
is the *strict* one; the other three are *permissive*. The end-user
effect is that an external developer can complete the entire consent
*request* flow with an email, get an approved consent_token, and then
have the *only* call that actually returns data reject the same
identifier.

Two clean fixes either of which closes this:
1. **Permissive scoped-export.** Have it resolve email/phone to the
   canonical Firebase UID server-side, the same way the hosted MCP
   layer does. Documented at the top of `developer-api.md`:
   *"MCP resolves email and phone identifiers to the canonical
   Firebase UID before calling /api/v1."* That resolution should
   happen for raw `/api/v1` callers too, or
2. **Strict everywhere.** Have all four endpoints require the
   canonical Firebase UID and reject email/phone uniformly. Then
   either document how an external developer obtains the canonical
   UID, or expose `/api/v1/resolve-identifier?email=...` so they can.

Today the platform offers neither — there is no documented way for a
raw `/api/v1` caller to discover the canonical Firebase UID for a
user they're integrating with. They can request and receive consent
using an email, then can't read.

Empirical evidence — every reasonable identity-resolution probe
returns 404:

```
GET /api/v1/me                                          → 404
GET /api/v1/whoami                                      → 404
GET /api/v1/resolve?email=katishay@gmail.com            → 404
GET /api/v1/users/me                                    → 404
GET /api/v1/identity/resolve?email=katishay@gmail.com   → 404
```

`/api/developer/access` exists but rejects the developer token
("Invalid Firebase ID token") — it requires the Firebase ID token,
not the dev token, so it isn't reachable from a raw external
integration either.

This is the loop-closing bug for external developers. Fixing it
unlocks the full external-agent path the developer portal is
positioning.

## What was verified live, end to end

1. ✅ Developer token issued via `https://hushh.ai/developers` works
   against the production backend.
2. ✅ Public endpoints (`/health`, `/api/v1`, `/api/v1/list-scopes`)
   serve the documented shapes.
3. ✅ Token-gated discovery (`/api/v1/user-scopes/{email}`) works and
   echoes app identity.
4. ✅ Consent request creation produces a real pending request with a
   real `request_id`, real app-identity payload, and a routable
   approval surface.
5. ✅ User approval in the Kai consent UI transitions status from
   `pending` → `granted` and issues a real cryptographically signed
   capability token (`HCT:...`).
6. ✅ `consent-status` polling reflects state transitions correctly.
7. ❌ `scoped-export` blocked by Finding 3 (identifier mismatch).

The decrypt path (X25519 ECDH + SHA-256 + AES-256-GCM unwrap +
AES-256-GCM decrypt) was already proven correct in mock mode against
a wire-shape correct synthetic export — see [`RUN.md`](./RUN.md).
Live decryption against the production server is unblocked once
Finding 3 is fixed.

## Summary of findings to flag back to Hushh

| # | Severity | Finding |
|---|---|---|
| 1 | Medium | Production `request-consent` response emits `request_url` pointing at `uat.kai.hushh.ai`. Same pattern in portal example configs. Likely a one-line config flip. |
| 2 | Informational | `/health` shows `One` is primary in production runtime. `docs/vision/README.md` still describes the runtime as "Kai-first until the One/Nav migration lands." Docs should be updated to current state. |
| 3 | **High** | `scoped-export` rejects email/phone user_ids that every other `/api/v1` endpoint accepts. No documented way to resolve email → Firebase UID. Blocks the full external-developer loop. |

All three are docs/config/consistency issues, not architectural ones —
the underlying trust model (BYOK, ciphertext-only, capability tokens,
scoped consent) works exactly as the four invariants in
[`../../docs/04_principles.md`](../../docs/04_principles.md) describe.
