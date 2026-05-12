"""Auth — read the authenticated identity from the upstream proxy header (R4).

The app process trusts `X-Vay-User`. Real authentication happens at the
reverse proxy. The header is required: missing or empty values yield
HTTP 401 (FR-026 / R4 — the operator identity is load-bearing for
per-operator persistence keying, so we refuse to fall back to a
synthetic anonymous identity).

**006 .deb mode** — when VayOBD runs from the .deb on a user's laptop, there
is no reverse proxy. The `vayobd` CLI shim sets `VAYOBD_OPERATOR_USER` to the
OS user (`getpass.getuser()`) before starting uvicorn, and this resolver uses
that env var as a fallback when no `X-Vay-User` header is present. A real
proxy in front of uvicorn still overrides the env var via the header, so the
production R4 contract is unchanged. The env-var fallback only kicks in for
loopback / single-user .deb deployments.
"""

from __future__ import annotations

import os

from fastapi import Header, status

from vayobd.api.errors import ApiError
from vayobd.models import OperatorIdentity


async def current_operator(
    x_vay_user: str | None = Header(default=None, alias="X-Vay-User"),
) -> OperatorIdentity:
    user = (x_vay_user or "").strip()
    if not user:
        # Spec 006 fallback for the .deb. Empty env var ⇒ unchanged 401 behaviour.
        user = (os.environ.get("VAYOBD_OPERATOR_USER") or "").strip()
    if not user:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="missing_operator_identity",
            message_key="errors.unauthenticated",
        )
    try:
        return OperatorIdentity(username=user)
    except ValueError as exc:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="invalid_operator_identity",
            message_key="errors.unauthenticated",
        ) from exc
