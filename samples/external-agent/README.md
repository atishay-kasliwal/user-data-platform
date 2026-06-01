# external-agent

> The smallest runnable Hushh personal agent. Reads a user's
> consented vault scope, decrypts it client-side, answers a question.

## What it does

A tiny FastAPI service that asks a question of your data — e.g.
*"summarize my recent portfolio losers"* — by going through the public
Hushh developer flow:

1. `GET  /api/v1/user-scopes/{user_id}` — discover scopes for the user.
2. `POST /api/v1/request-consent` — ask for one scope (e.g. `attr.financial.*`).
3. `GET  /api/v1/consent-status` — poll until the user approves in the Hushh app.
4. `POST /api/v1/scoped-export` — receive ciphertext + wrapped key.
5. **Client-side**: X25519 unwrap → AES-256-GCM decrypt.
6. Hand the plaintext + question to an LLM. Return the answer.

The whole flow is the four invariants in action — see
[`../../docs/04_principles.md`](../../docs/04_principles.md).

## Bring-up

```bash
cp .env.example .env
# fill in HUSHH_DEVELOPER_TOKEN and USER_ID from https://uat.kai.hushh.ai/developers
docker compose up --build
```

Then ask:

```bash
curl -X POST http://localhost:8000/ask \
  -H 'content-type: application/json' \
  -d '{"scope":"attr.financial.*","question":"summarize my recent losers"}'
```

## Modes

| Mode | When to use | How to enable |
|---|---|---|
| **live** | You have a real `HUSHH_DEVELOPER_TOKEN` and the user has a vault in UAT | Set `MODE=live` |
| **mock** | You want to see the flow without a token | Set `MODE=mock` (default). The Hushh API responses are stubbed. Decryption still runs on a synthetic blob. |

`mock` mode lets you read the code, run it, and see the entire shape
end-to-end without an account. `live` mode talks to
`https://api.uat.hushh.ai`.

## Env vars

| Var | Required | Default | Notes |
|---|---|---|---|
| `MODE` | no | `mock` | `mock` or `live` |
| `CONSENT_API_URL` | live only | `https://consent-protocol-f2gsa4kfsq-uc.a.run.app` (prod). Use `https://api.uat.hushh.ai` for UAT. | base URL for `/api/v1` |
| `HUSHH_DEVELOPER_TOKEN` | live only | — | from `/developers` in the Hushh app |
| `USER_ID` | live only | — | Firebase UID, email, or phone (with `USER_COUNTRY_ISO2`) |
| `USER_COUNTRY_ISO2` | live only if `USER_ID` is a phone number | — | e.g. `US` |
| `LLM_PROVIDER` | no | `stub` | `stub`, `anthropic` |
| `ANTHROPIC_API_KEY` | only if `LLM_PROVIDER=anthropic` | — | Claude API key |

## What's intentionally not here

- No retry/backoff library, no observability stack, no auth on the
  agent's own endpoint. This is a sample, not a production service —
  the readable-in-one-sitting property is the point.
- No webhook for consent approval. We poll every 3s up to a timeout.
  Production agents should subscribe to the FCM push channel instead.
- No persistent storage. The decrypted payload lives in memory for the
  request lifetime and is dropped. That matches Hushh's invariant #1.

## Files

```
external-agent/
├── README.md         ← this file
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── main.py           ← FastAPI app + /ask route
└── hushh.py          ← Hushh /api/v1 client + crypto + LLM glue
```
