"""T030 — WebSocket handshake validation tests.

The full session pipeline (candump subprocess + DBC + errq) is too
brittle to fixture in CI. Instead, this file covers the *handshake*
contract from `contracts/websocket.md` end-to-end:

- 1008 unauthorized when X-Vay-User is missing
- 1008 developer_mode_off when the query param or setting is wrong
- 1008 host_out_of_scope for an unknown host
- accept + ready envelope when everything is green

The session itself is exercised through `_drain_lines` / `_emit_loop`
unit tests (TODO: add later) and through the manual quickstart smoke.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from vayobd.app import create_app
from vayobd.config import ExecutorMode, Settings, get_settings


@pytest.fixture
def base_settings(synthetic_inventory: Path, tmp_path: Path) -> Settings:
    return Settings(
        inventory_path=synthetic_inventory,
        inventory_meta_path=tmp_path / "inventory.meta.json",
        runs_dir=tmp_path / "runs",
        executor=ExecutorMode.FIXTURE,
        fixtures_dir=Path(__file__).resolve().parents[1] / "fixtures" / "runs",
        developer_mode=True,
        ree_reecu_path=tmp_path / "ree-reecu-missing",
    )


def _client(settings: Settings) -> TestClient:
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_missing_x_vay_user_is_unauthorized(base_settings: Settings) -> None:
    client = _client(base_settings)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/api/live/ts-de-ber-zeus/ws?developer_mode_check=1",
            headers={},
        ) as ws:
            ws.receive_text()
    assert excinfo.value.code == 1008


def test_developer_mode_check_missing(base_settings: Settings) -> None:
    client = _client(base_settings)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/api/live/ts-de-ber-zeus/ws",
            headers={"X-Vay-User": "alice"},
        ) as ws:
            ws.receive_text()
    assert excinfo.value.code == 1008


def test_developer_mode_off_in_settings(base_settings: Settings) -> None:
    settings = base_settings.model_copy(update={"developer_mode": False})
    client = _client(settings)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/api/live/ts-de-ber-zeus/ws?developer_mode_check=1",
            headers={"X-Vay-User": "alice"},
        ) as ws:
            ws.receive_text()
    assert excinfo.value.code == 1008


def test_host_not_in_inventory(base_settings: Settings) -> None:
    client = _client(base_settings)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(
            "/api/live/ts-de-ber-imaginary/ws?developer_mode_check=1",
            headers={"X-Vay-User": "alice"},
        ) as ws:
            ws.receive_text()
    assert excinfo.value.code == 1008


def test_handshake_emits_ready_and_connecting(base_settings: Settings) -> None:
    """Happy path up to the moment ssh is spawned. The synthetic
    inventory's `ts-de-ber-zeus` resolves to a fake address, so the
    actual ssh subprocess will fail — but the handshake envelopes
    (`ready`, `status:connecting`) MUST land first.
    """
    client = _client(base_settings)
    with client.websocket_connect(
        "/api/live/ts-de-ber-zeus/ws?developer_mode_check=1",
        headers={"X-Vay-User": "alice@vay.io"},
    ) as ws:
        ready = json.loads(ws.receive_text())
        assert ready["kind"] == "ready"
        assert ready["payload"]["host_id"] == "ts-de-ber-zeus"
        assert ready["payload"]["session_id"]

        connecting = json.loads(ws.receive_text())
        assert connecting["kind"] == "status"
        assert connecting["payload"]["state"] == "connecting"
