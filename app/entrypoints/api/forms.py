"""Secure one-time form endpoints. Token stays in URL fragment until POST body."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse

from app.core.config import get_settings
from app.core.crypto import LocalKeyProvider
from app.core.db import unit_of_work
from app.core.one_time_form_store import consume_form
from app.modules.social.credentials import store_secret

router = APIRouter(prefix="/secure", tags=["secure-forms"])


@router.get("", response_class=HTMLResponse)
async def show_form(response: Response) -> HTMLResponse:
    nonce = secrets.token_urlsafe(18)
    html = (
        '<!doctype html><html lang="en"><meta charset="utf-8"><title>Secure form</title>'
        '<form method="post" action="/secure/consume">'
        '<input type="hidden" name="token" id="token">'
        '<label>Credential <input type="password" name="credential" '
        'autocomplete="off" required maxlength="4096"></label>'
        '<button type="submit">Submit</button></form>'
        f'<script nonce="{nonce}">'
        'document.getElementById("token").value='
        "decodeURIComponent(location.hash.slice(1));"
        'history.replaceState(null,"",location.pathname);</script>'
        "</html>"
    )
    response.headers["Cache-Control"] = "no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        f"default-src 'none'; script-src 'nonce-{nonce}'; form-action 'self'; "
        "base-uri 'none'; frame-ancestors 'none'"
    )
    return HTMLResponse(html, headers=dict(response.headers))


@router.post("/consume")
async def submit_form(
    request: Request,
    token: Annotated[str, Form(min_length=1, max_length=512)],
    credential: Annotated[str, Form(min_length=1, max_length=4096)],
) -> dict[str, str]:
    # Browser form is same-origin only; reject cross-site form posts (S-012).
    origin = request.headers.get("origin")
    expected = get_settings().public_base_url.rstrip("/")
    if not origin or origin.rstrip("/") != expected:
        raise HTTPException(status_code=403, detail="invalid origin")
    async with unit_of_work() as session:
        consumed = await consume_form(session, raw_token=token, purpose="credential_entry")
        if consumed is not None:
            provider = LocalKeyProvider.from_file(get_settings().master_key_file)
            await store_secret(
                session,
                owner_type=consumed.owner_type,
                owner_id=consumed.owner_id,
                plaintext=credential,
                provider=provider,
                auth_type="manual",
            )
    if consumed is None:
        raise HTTPException(status_code=410, detail="This secure link is expired or already used.")
    return {"status": "accepted"}
