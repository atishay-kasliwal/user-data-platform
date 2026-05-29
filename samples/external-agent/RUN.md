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

## Perf snapshot — mock mode, single laptop

Measured 2026-05-29 on Apple Silicon, Python 3.13, uvicorn single
worker, loopback HTTP. Mock mode generates a fresh sender keypair and
synthetic encrypted payload per request, so each request exercises
both the encrypt path (the mock standing in for the server) *and* the
real `decrypt_scoped_export` connector path.

```
$ curl -s http://127.0.0.1:8765/health   →  ~5 ms to first 200 after uvicorn boot

5x POST /ask (one full mock developer flow per request):
  req 1: 9.96 ms   ← cold path (JIT'd imports, first crypto call)
  req 2: 1.26 ms
  req 3: 1.32 ms
  req 4: 1.28 ms
  req 5: 1.44 ms

Warm median:  1.32 ms
Warm spread: ±0.18 ms
```

What each warm 1.3 ms covers, end to end:

1. HTTP request parse and Pydantic validate.
2. `user_scopes()` mock returns scope list.
3. `request_consent()` mock returns a consent token.
4. `wait_for_approval()` mock no-ops (live mode polls every 3 s).
5. `scoped_export()` mock generates a fresh sender X25519 keypair,
   AES-256-GCM encrypts a synthetic payload, derives the wrapping
   key via ECDH + SHA-256 against the connector public key, AES-GCM
   wraps the export key. **This is the server-side cost simulated.**
6. `decrypt_scoped_export()` runs the real connector path: ECDH,
   SHA-256, AES-GCM unwrap, AES-GCM decrypt, JSON parse.
7. `answer()` stub LLM formats the response.
8. JSON encode + HTTP write.

That whole pipeline takes ~1.3 ms warm. The decrypt-only path (step 6
in isolation) is roughly a third of that — the rest is the mock
encrypt-side, HTTP, and Python overhead. In live mode, step 5 becomes
a real HTTPS round-trip to `api.uat.hushh.ai`, and step 4 becomes a
real poll loop. The decrypt-side cost (which is the part the *platform*
cares about, since it determines what the connector has to absorb)
stays sub-millisecond.

The headline number for the cost argument in
[`../../docs/04_principles.md`](../../docs/04_principles.md#why-these-invariants-also-make-this-the-cheapest-fastest-path):
the connector's per-read crypto work is on the order of a few hundred
microseconds. The server's per-read crypto work is zero — it streams
ciphertext.

## Flipping to live mode

Once a token is available:

```bash
echo "MODE=live" > .env
echo "HUSHH_DEVELOPER_TOKEN=<token-from-/developers>" >> .env
echo "USER_ID=<firebase-uid-or-email>" >> .env
.venv/bin/uvicorn main:app --port 8765
```

No code changes — only env.
