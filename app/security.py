"""HTTP Basic Auth for the carer-side API surface.

The public endpoints (``GET/POST /enroll/{token}`` and ``/healthz``) stay
open. Everything under ``/v1/*`` requires the admin credentials configured
via ``FARO_ADMIN_USERNAME`` and ``FARO_ADMIN_PASSWORD``.
"""
from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials


_basic = HTTPBasic(realm="Faro (carer)")


def admin_required(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(_basic),
) -> None:
    settings = request.app.state.settings
    if not settings.admin_username or not settings.admin_password:
        # Refuse to authenticate anyone until the operator has configured
        # admin credentials. Fail-closed.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin credentials are not configured on this server.",
        )

    ok_user = secrets.compare_digest(credentials.username, settings.admin_username)
    ok_pass = secrets.compare_digest(credentials.password, settings.admin_password)
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": 'Basic realm="Faro (carer)"'},
        )
