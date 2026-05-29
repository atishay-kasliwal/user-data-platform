# Verified run — mock mode

> Smoke-tested 2026-05-29 against the local sample, no Docker.

Bring-up:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
MODE=mock LLM_PROVIDER=stub .venv/bin/uvicorn main:app --port 8765
```

Health:

```bash
$ curl -s http://127.0.0.1:8765/health
{"status":"ok","mode":"mock"}
```

Ask:

```bash
$ curl -s -X POST http://127.0.0.1:8765/ask \
    -H 'content-type: application/json' \
    -d '{"scope":"attr.financial.*","question":"what were my biggest losers?"}'
{
  "granted_scope":"attr.financial.*",
  "coverage_kind":"exact",
  "answer":"[stub LLM] question: 'what were my biggest losers?'\n[stub LLM] context keys: ['scope', 'summary', 'items']\n[stub LLM] context preview: {\"scope\": \"attr.financial.*\", \"summary\": \"synthetic payload for mock mode\", \"items\": [{\"symbol\": \"AAPL\", \"pnl\": -120.43}, {\"symbol\": \"NVDA\", \"pnl\": 89.1}]}"
}
```

What this exercised end-to-end:

1. Generated a fresh X25519 connector keypair on startup.
2. Built a wire-shape-correct mock `scoped-export` response: a freshly
   generated sender X25519 keypair, AES-GCM-encrypted payload, wrapped
   export key under the ECDH-derived (`SHA-256(shared_secret)`)
   wrapping key — same algorithm documented in
   [developer-api.md](../../../hushh-research/consent-protocol/docs/reference/developer-api.md#client-side-connector-example).
3. The connector decrypted: ECDH → SHA-256 → AES-GCM unwrap →
   AES-GCM decrypt → JSON parse — confirming the live decryption path
   in `hushh.py:decrypt_scoped_export` matches the wire contract.
4. Stub LLM returned the decrypted context.

What this did *not* exercise (requires a real developer token):

- The actual HTTP calls to `https://api.uat.hushh.ai/api/v1/*`.
- The first-party approval surface (push notification → user taps
  approve in the Hushh app).
- A real Hushh server returning a real wrapped scoped export.

To flip to live mode once a token is available:

```bash
echo "MODE=live" > .env
echo "HUSHH_DEVELOPER_TOKEN=<token-from-/developers>" >> .env
echo "USER_ID=<firebase-uid-or-email>" >> .env
.venv/bin/uvicorn main:app --port 8765
```

No code changes needed — only env.
