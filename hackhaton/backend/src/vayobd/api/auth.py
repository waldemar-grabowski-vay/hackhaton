"""Auth — read the authenticated identity from the upstream proxy header (R4).

The app process trusts `X-Vay-User`. Real authentication happens at the
reverse proxy. The header is required: missing or empty values yield
HTTP 401 (FR-026 / R4 — the operator identity is load-bearing for
per-operator persistence keying, so we refuse to fall back to a
synthetic anonymous identity).
"""

from __future__ import annotations

from fastapi import Header, status

from vayobd.api.errors import ApiError
from vayobd.models import OperatorIdentity


async def current_operator(
    x_vay_user: str | None = Header(default=None, alias="X-Vay-User"),
) -> OperatorIdentity:
    if x_vay_user is None or not x_vay_user.strip():
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="missing_operator_identity",
            message_key="errors.unauthenticated",
        )
    try:
        return OperatorIdentity(username=x_vay_user.strip())
    except ValueError as exc:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="invalid_operator_identity",
            message_key="errors.unauthenticated",
        ) from exc
