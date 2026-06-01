"""
Hushh /api/v1 client + crypto + LLM glue.

The wire contract this targets:
  GET  /api/v1/user-scopes/{user_id}?token=...
  POST /api/v1/request-consent?token=...
  GET  /api/v1/consent-status?token=...&user_id=...&scope=...
  POST /api/v1/scoped-export?token=...

The encrypted-export response shape, as documented in
consent-protocol/docs/reference/developer-api.md:

  {
    "encrypted_data": "<base64>", "iv": "<base64>", "tag": "<base64>",
    "wrapped_key_bundle": {
      "wrapped_export_key": "<base64>",
      "wrapped_key_iv": "<base64>", "wrapped_key_tag": "<base64>",
      "sender_public_key": "<base64-x25519>",
      "wrapping_alg": "X25519-AES256-GCM",
      "connector_key_id": "...",
    },
    "granted_scope": "...", "expected_scope": "...",
    "coverage_kind": "exact",
    ...
  }

Decryption derives a wrapping key via X25519 ECDH + SHA-256, unwraps the
export key with AES-GCM, then decrypts the payload with the export key.
The private key never leaves this process.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# ---------------------------------------------------------------------------
# Connector keypair — generated once per process. Private key stays here.
# ---------------------------------------------------------------------------

@dataclass
class Connector:
    private_key: X25519PrivateKey
    public_key_b64: str
    key_id: str = "connector-key-1"
    wrapping_alg: str = "X25519-AES256-GCM"

    @classmethod
    def fresh(cls) -> "Connector":
        priv = X25519PrivateKey.generate()
        pub_bytes = priv.public_key().public_bytes_raw()
        return cls(private_key=priv, public_key_b64=_b64(pub_bytes))


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s)


# ---------------------------------------------------------------------------
# Hushh API client — live mode talks to UAT, mock mode returns synthetic data
# ---------------------------------------------------------------------------

class HushhClient:
    def __init__(
        self,
        mode: str,
        base_url: str,
        developer_token: str,
        user_id: str,
        user_country_iso2: str | None,
    ):
        self.mode = mode
        self.base_url = base_url.rstrip("/")
        self.token = developer_token
        self.user_id = user_id
        self.user_country_iso2 = user_country_iso2

    async def user_scopes(self) -> list[str]:
        if self.mode == "mock":
            return ["attr.financial.*", "attr.personal.profile.*"]
        async with self._http() as c:
            r = await c.get(
                f"/api/v1/user-scopes/{self.user_id}",
                params=self._auth_params(),
            )
            r.raise_for_status()
            return r.json().get("scopes", [])

    async def request_consent(
        self, scope: str, connector: Connector, reason: str
    ) -> str:
        """Returns the consent_token (HCT:...) once issued or reused."""
        if self.mode == "mock":
            return "HCT:mock-consent-token"
        body = {
            "user_id": self.user_id,
            "scope": scope,
            "expiry_hours": 24,
            "approval_timeout_minutes": 60,
            "reason": reason,
            "connector_public_key": connector.public_key_b64,
            "connector_key_id": connector.key_id,
            "connector_wrapping_alg": connector.wrapping_alg,
        }
        if self.user_country_iso2:
            body["country_iso2"] = self.user_country_iso2
        async with self._http() as c:
            r = await c.post(
                "/api/v1/request-consent",
                params=self._auth_params(),
                json=body,
            )
            r.raise_for_status()
            data = r.json()
            return data.get("consent_token") or data.get("token")

    async def wait_for_approval(
        self, scope: str, timeout_s: int = 300, poll_interval_s: float = 3.0
    ) -> None:
        if self.mode == "mock":
            return
        deadline = time.monotonic() + timeout_s
        async with self._http() as c:
            while time.monotonic() < deadline:
                r = await c.get(
                    "/api/v1/consent-status",
                    params={
                        **self._auth_params(),
                        "user_id": self.user_id,
                        "scope": scope,
                    },
                )
                r.raise_for_status()
                status = r.json().get("status")
                if status == "approved":
                    return
                if status in {"denied", "expired", "revoked"}:
                    raise RuntimeError(f"consent {status}")
                await asyncio.sleep(poll_interval_s)
        raise TimeoutError("consent approval timed out")

    async def scoped_export(self, consent_token: str, scope: str) -> dict[str, Any]:
        if self.mode == "mock":
            return _mock_scoped_export(scope)
        async with self._http() as c:
            r = await c.post(
                "/api/v1/scoped-export",
                params=self._auth_params(),
                json={
                    "user_id": self.user_id,
                    "consent_token": consent_token,
                    "expected_scope": scope,
                },
            )
            r.raise_for_status()
            return r.json()

    def _auth_params(self) -> dict[str, str]:
        return {"token": self.token}

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=30.0)


# ---------------------------------------------------------------------------
# Decryption — pure-Python, no plaintext touches the wire
# ---------------------------------------------------------------------------

def decrypt_scoped_export(
    export: dict[str, Any], connector: Connector
) -> dict[str, Any]:
    bundle = export["wrapped_key_bundle"]

    sender_pub = X25519PublicKey.from_public_bytes(_unb64(bundle["sender_public_key"]))
    shared_secret = connector.private_key.exchange(sender_pub)
    wrapping_key = hashlib.sha256(shared_secret).digest()

    raw_export_key = AESGCM(wrapping_key).decrypt(
        _unb64(bundle["wrapped_key_iv"]),
        _unb64(bundle["wrapped_export_key"]) + _unb64(bundle["wrapped_key_tag"]),
        None,
    )

    plaintext = AESGCM(raw_export_key).decrypt(
        _unb64(export["iv"]),
        _unb64(export["encrypted_data"]) + _unb64(export["tag"]),
        None,
    )
    return json.loads(plaintext.decode("utf-8"))


# ---------------------------------------------------------------------------
# Mock scoped-export — generates a synthetic ciphertext + wrapped key against
# a fresh ephemeral sender keypair, so the full decrypt path actually runs.
# ---------------------------------------------------------------------------

def _mock_scoped_export(scope: str) -> dict[str, Any]:
    sender = X25519PrivateKey.generate()
    # We don't have the caller's connector here. The mock cheats by deriving
    # the wrapping key with the caller's *public* key, which the caller will
    # rederive via ECDH with this sender's private key. To do this we need
    # the connector's public key — we stash it in a module-level slot.
    connector_pub_bytes = _MOCK_CONNECTOR_PUB.get("bytes")
    if not connector_pub_bytes:
        raise RuntimeError("mock connector public key not set; call set_mock_connector first")
    connector_pub = X25519PublicKey.from_public_bytes(connector_pub_bytes)

    shared_secret = sender.exchange(connector_pub)
    wrapping_key = hashlib.sha256(shared_secret).digest()

    payload = {
        "scope": scope,
        "summary": "synthetic payload for mock mode",
        "items": [
            {"symbol": "AAPL", "pnl": -120.43},
            {"symbol": "NVDA", "pnl": 89.10},
        ],
    }
    plaintext = json.dumps(payload).encode("utf-8")

    export_key = AESGCM.generate_key(bit_length=256)
    payload_iv = os.urandom(12)
    payload_ct_and_tag = AESGCM(export_key).encrypt(payload_iv, plaintext, None)
    payload_ct, payload_tag = payload_ct_and_tag[:-16], payload_ct_and_tag[-16:]

    wrap_iv = os.urandom(12)
    wrapped_ct_and_tag = AESGCM(wrapping_key).encrypt(wrap_iv, export_key, None)
    wrapped_ct, wrap_tag = wrapped_ct_and_tag[:-16], wrapped_ct_and_tag[-16:]

    return {
        "status": "success",
        "user_id": "mock-user",
        "granted_scope": scope,
        "expected_scope": scope,
        "coverage_kind": "exact",
        "encrypted_data": _b64(payload_ct),
        "iv": _b64(payload_iv),
        "tag": _b64(payload_tag),
        "wrapped_key_bundle": {
            "wrapped_export_key": _b64(wrapped_ct),
            "wrapped_key_iv": _b64(wrap_iv),
            "wrapped_key_tag": _b64(wrap_tag),
            "sender_public_key": _b64(sender.public_key().public_bytes_raw()),
            "wrapping_alg": "X25519-AES256-GCM",
            "connector_key_id": "connector-key-1",
        },
        "export_revision": 1,
        "export_generated_at": "2026-05-29T00:00:00Z",
        "export_refresh_status": "current",
    }


_MOCK_CONNECTOR_PUB: dict[str, bytes] = {}


def set_mock_connector(connector: Connector) -> None:
    _MOCK_CONNECTOR_PUB["bytes"] = _unb64(connector.public_key_b64)


# ---------------------------------------------------------------------------
# LLM glue — stub or anthropic
# ---------------------------------------------------------------------------

async def answer(question: str, context: dict[str, Any]) -> str:
    provider = os.getenv("LLM_PROVIDER", "stub")
    if provider == "stub":
        return _stub_answer(question, context)
    if provider == "anthropic":
        return await _anthropic_answer(question, context)
    raise ValueError(f"unknown LLM_PROVIDER: {provider}")


def _stub_answer(question: str, context: dict[str, Any]) -> str:
    return (
        f"[stub LLM] question: {question!r}\n"
        f"[stub LLM] context keys: {list(context.keys())}\n"
        f"[stub LLM] context preview: {json.dumps(context)[:200]}"
    )


async def _anthropic_answer(question: str, context: dict[str, Any]) -> str:
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = await client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        system=(
            "You are a personal-data agent. The user has granted you a scoped "
            "view of their data. Answer the question using only the provided "
            "context. If the context does not cover the question, say so."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Context (decrypted scope payload):\n"
                    f"```json\n{json.dumps(context, indent=2)}\n```\n\n"
                    f"Question: {question}"
                ),
            }
        ],
    )
    return resp.content[0].text
