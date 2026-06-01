"""
external-agent — the smallest runnable Hushh personal agent.

Flow per /ask request:
  1. Discover scopes available for the user.
  2. Request consent for the requested scope.
  3. Wait for the user to approve in the Hushh app (mock: returns immediately).
  4. Receive the encrypted scoped export.
  5. Unwrap the export key + decrypt the payload locally.
  6. Hand decrypted context + question to the LLM. Return the answer.

The connector private key is generated at startup and never leaves the
process. The decrypted payload lives only in the request lifetime.
"""

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import hushh

app = FastAPI(title="external-agent", version="0.1.0")


class AskRequest(BaseModel):
    scope: str = "attr.financial.*"
    question: str
    reason: str = "Personal agent answering a user question over their scoped data."


@app.on_event("startup")
async def startup() -> None:
    app.state.connector = hushh.Connector.fresh()
    app.state.client = hushh.HushhClient(
        mode=os.getenv("MODE", "mock"),
        base_url=os.getenv("CONSENT_API_URL", "https://consent-protocol-f2gsa4kfsq-uc.a.run.app"),
        developer_token=os.getenv("HUSHH_DEVELOPER_TOKEN", ""),
        user_id=os.getenv("USER_ID", "mock-user"),
        user_country_iso2=os.getenv("USER_COUNTRY_ISO2") or None,
    )
    if app.state.client.mode == "mock":
        hushh.set_mock_connector(app.state.connector)
    elif not app.state.client.token or not app.state.client.user_id:
        raise RuntimeError(
            "live mode requires HUSHH_DEVELOPER_TOKEN and USER_ID"
        )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": app.state.client.mode}


@app.post("/ask")
async def ask(body: AskRequest) -> dict[str, str]:
    client: hushh.HushhClient = app.state.client
    connector: hushh.Connector = app.state.connector

    available = await client.user_scopes()
    if body.scope not in available and not _scope_covered(body.scope, available):
        raise HTTPException(
            status_code=400,
            detail=f"scope {body.scope!r} not in discovered scopes {available}",
        )

    consent_token = await client.request_consent(body.scope, connector, body.reason)
    await client.wait_for_approval(body.scope)
    export = await client.scoped_export(consent_token, body.scope)

    plaintext = hushh.decrypt_scoped_export(export, connector)
    answer = await hushh.answer(body.question, plaintext)
    return {
        "granted_scope": export.get("granted_scope", body.scope),
        "coverage_kind": export.get("coverage_kind", "exact"),
        "answer": answer,
    }


def _scope_covered(requested: str, available: list[str]) -> bool:
    """A scope is covered if a broader available scope is a prefix."""
    for s in available:
        if s.endswith(".*") and requested.startswith(s[:-1]):
            return True
    return False
