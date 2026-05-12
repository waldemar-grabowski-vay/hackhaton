"""FastAPI WebSocket route for `/api/live/{host_id}/ws` (T023).

Handshake order:
  1. X-Vay-User header present?            → no: close 1008 unauthorized
  2. developer_mode_check=1 query?         → no: close 1008 developer_mode_off
  3. Settings.developer_mode is True?      → no: close 1008 developer_mode_off
  4. host_id resolves in inventory?        → no: close 1008 host_out_of_scope
  5. Looks good — instantiate session, run.
"""

from __future__ import annotations

import logging
import os
import re
from fastapi import APIRouter, Depends, Query, WebSocket
from fastapi.websockets import WebSocketState

from vayobd.config import Settings, get_settings
from vayobd.inventory.loader import load_inventory
from vayobd.live.session import LiveDiagnosticSession

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/live", tags=["live"])

_SLUG_DISALLOWED_RE = re.compile(r"[^a-z0-9._-]+")


def _operator_slug(username: str) -> str:
    derived = _SLUG_DISALLOWED_RE.sub("-", username.strip().lower()).strip("-_.")
    return derived or "unknown"


@router.websocket("/{host_id}/ws")
async def live_ws(  # noqa: PLR0913 — clarity over cohesion
    websocket: WebSocket,
    host_id: str,
    user: str | None = Query(default=None),
    port: int | None = Query(default=None, ge=1, le=65535),
    developer_mode_check: int | None = Query(default=None),
    settings: Settings = Depends(get_settings),
) -> None:

    # 1. Operator identity.
    # Browsers can't set custom headers on WebSocket upgrades, so the
    # X-Vay-User header that the HTTP shim relies on is missing on every
    # browser-initiated WS connection. Fall back to VAYOBD_OPERATOR_USER
    # (the same env var the .deb's `vayobd` launcher seeds for the HTTP
    # auth shim — see api/auth.py). A real reverse proxy in front of
    # uvicorn can still inject X-Vay-User via subprotocol negotiation;
    # we read both.
    username = websocket.headers.get("x-vay-user", "").strip()
    if not username:
        username = (os.environ.get("VAYOBD_OPERATOR_USER") or "").strip()
    if not username:
        await websocket.close(code=1008, reason="unauthorized")
        return

    # 2 + 3. Developer mode checks
    if developer_mode_check != 1:
        await websocket.close(code=1008, reason="developer_mode_off")
        return
    if not settings.developer_mode:
        await websocket.close(code=1008, reason="developer_mode_off")
        return

    # 4. Host in scope?
    try:
        inventory = load_inventory(settings.inventory_path)
    except Exception as exc:  # noqa: BLE001
        log.warning("live_ws_inventory_unavailable", error=str(exc))
        await websocket.close(code=1011, reason="inventory_unavailable")
        return
    if inventory is None:
        await websocket.close(code=1011, reason="inventory_unavailable")
        return

    host_record = next((h for h in inventory.hosts if h.id == host_id), None)
    if host_record is None:
        await websocket.close(code=1008, reason="host_out_of_scope")
        return
    # When the inventory has no `ansible_host` (typical for telestations
    # that are reachable via the operator's `~/.ssh/config` Host alias),
    # pass the host_id itself to ssh and let the local config resolve
    # it. This mirrors what the desktop tool does.
    ssh_target = host_record.address or host_record.id

    # 5. Accept + run.
    await websocket.accept()
    app_state = websocket.app.state
    session = LiveDiagnosticSession(
        websocket=websocket,
        host_id=host_id,
        host_address=ssh_target,
        operator_slug=_operator_slug(username),
        errq_model=getattr(app_state, "errq_model", None),
        dbc_decoder=getattr(app_state, "dbc_decoder", None),
        server_build=getattr(app_state, "engine_version", None),
        user_override=user,
        port_override=port,
        channel_a_pattern=settings.channel_a_pattern,
        channel_b_pattern=settings.channel_b_pattern,
    )
    log.info(
        "live_ws_open",
        session_id=session.session_id,
        host_id=host_id,
        operator=session.operator_slug,
    )
    try:
        await session.run()
    except Exception as exc:  # noqa: BLE001
        log.exception("live_ws_unhandled", session_id=session.session_id)
        if websocket.client_state != WebSocketState.DISCONNECTED:
            try:
                await websocket.close(code=1011, reason=str(exc)[:120])
            except Exception:  # noqa: BLE001
                pass


