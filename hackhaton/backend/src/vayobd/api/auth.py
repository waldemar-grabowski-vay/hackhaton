"""Auth — read the authenticated identity from the upstream proxy header (R4).

The app process trusts `X-Vay-User`. Real authentication happens at the
reverse proxy. If the header is missing in dev, we synthesise an `unknown`
operator so endpoints work locally.
"""

from __future__ import annotations

from fastapi import Header

from vayobd.models import OperatorIdentity

UNKNOWN_OPERATOR = OperatorIdentity(username="unknown")


async def current_operator(
    x_vay_user: str | None = Header(default=None, alias="X-Vay-User"),
) -> OperatorIdentity:
    if not x_vay_user or not x_vay_user.strip():
        return UNKNOWN_OPERATOR
    return OperatorIdentity(username=x_vay_user.strip())
