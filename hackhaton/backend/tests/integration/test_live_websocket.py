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


def test_null_address_host_resolves_to_host_id(base_settings: Settings) -> None:
    """T056 / FR-005 amendment: when the inventory entry exists but has
    no `ansible_host`, the backend MUST fall back to the host_id itself
    as the ssh target rather than rejecting the host. This is the path
    operators rely on for telestations resolved through `~/.ssh/config`
    Host aliases.
    """
    client = _client(base_settings)
    with client.websocket_connect(
        "/api/live/ts-de-ber-noaddr/ws?developer_mode_check=1",
        headers={"X-Vay-User": "alice@vay.io"},
    ) as ws:
        ready = json.loads(ws.receive_text())
        assert ready["kind"] == "ready"
        assert ready["payload"]["host_id"] == "ts-de-ber-noaddr"
        # The session was constructed and `ready` was emitted — that
        # alone proves the handshake didn't close 1008
        # `host_out_of_scope`. The actual ssh target is internal to the
        # session; we can confirm it indirectly via the connecting
        # status that follows.
        connecting = json.loads(ws.receive_text())
        assert connecting["kind"] == "status"
        assert connecting["payload"]["state"] == "connecting"


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


# --------------------------------------------------------------------------
# T036: errq diff envelope emission (US2).
#
# The full pipeline (real ssh subprocess + DBC) is exercised in the manual
# quickstart since CI has no testbed. Here we drive the state tracker
# directly and assert that one cycle of `_emit_one_cycle` produces an
# `errq_update` envelope whose `appeared` / `disappeared` lists are
# correct. This protects the wire contract (`contracts/websocket.md`)
# without smuggling in a fake subprocess.
# --------------------------------------------------------------------------


def _make_session():
    from vayobd.live.session import LiveDiagnosticSession

    # `WebSocket` is only used as the outbound sink, and we don't drain
    # the queue in this test, so a plain `object()` would be enough —
    # but FastAPI's type system wants `WebSocket`. The session never
    # touches `ws` during `_emit_one_cycle`, so a stub class is fine.
    class _StubWS:
        async def send_json(self, *_a, **_k) -> None:  # pragma: no cover
            pass

        async def close(self, *_a, **_k) -> None:  # pragma: no cover
            pass

    return LiveDiagnosticSession(
        websocket=_StubWS(),  # type: ignore[arg-type]
        host_id="ts-de-ber-zeus",
        host_address="192.168.60.2",
        operator_slug="alice",
        errq_model=None,  # degraded mode → placeholder names from state tracker
        dbc_decoder=None,
        server_build="abc123",
    )


def test_emit_cycle_emits_errq_update_on_bit_flip() -> None:
    """Flip a known bit in the channel-A errq buffer. Drive one emit
    cycle. Expect an `errq_update` envelope with `appeared` listing the
    new entry. Then clear the bit, drive another cycle, expect a
    `disappeared` diff for the same key.
    """
    session = _make_session()

    # Buffer with byte 3 (1-based) bit 2 set → mask 0x04. The state
    # tracker uses 1-based byte indexing and bit indices 0..7.
    buf = bytearray(64)
    buf[2] = 0x04  # byte 3 (1-based) → index 2
    session.state_tracker.update_buffer(
        channel="A",
        buffer=bytes(buf),
        ts=1.0,
        bus="can0",
        can_id=0x100,
        hex_id="100",
        decode_buffer_fn=lambda *_: [],
    )

    new_keys = session._emit_one_cycle(active_keys=set())

    # Drain outbound queue.
    items = []
    while not session.outbound.empty():
        items.append(session.outbound.get_nowait())
    errq_envs = [i for i in items if i["kind"] == "errq_update"]
    assert len(errq_envs) == 1
    payload = errq_envs[0]["payload"]
    assert len(payload["appeared"]) == 1
    appeared = payload["appeared"][0]
    assert appeared["channel"] == "A"
    assert appeared["byte"] == 3
    assert appeared["bit"] == 2  # bit_mask 0x04 → index 2
    assert payload["disappeared"] == []
    assert ("A", 3, 2) in new_keys

    # Now clear the bit; the tracker flips it to passive but the active
    # set shrinks to empty, which is what _collect_active_errq returns.
    buf[2] = 0x00
    session.state_tracker.update_buffer(
        channel="A",
        buffer=bytes(buf),
        ts=2.0,
        bus="can0",
        can_id=0x100,
        hex_id="100",
        decode_buffer_fn=lambda *_: [],
    )
    final_keys = session._emit_one_cycle(active_keys=new_keys)

    items = []
    while not session.outbound.empty():
        items.append(session.outbound.get_nowait())
    errq_envs = [i for i in items if i["kind"] == "errq_update"]
    assert len(errq_envs) == 1
    payload = errq_envs[0]["payload"]
    assert payload["appeared"] == []
    assert len(payload["disappeared"]) == 1
    assert payload["disappeared"][0] == {"channel": "A", "byte": 3, "bit": 2}
    assert final_keys == set()


def test_emit_cycle_no_change_no_envelope() -> None:
    """When the active set hasn't changed, no `errq_update` is sent.
    Empty diffs are not on the wire (per contracts/websocket.md).
    """
    session = _make_session()

    buf = bytearray(64)
    buf[5] = 0x01  # byte 6 (1-based), bit 0
    session.state_tracker.update_buffer(
        channel="B",
        buffer=bytes(buf),
        ts=1.0,
        bus="can0",
        can_id=0x101,
        hex_id="101",
        decode_buffer_fn=lambda *_: [],
    )
    keys_after_first = session._emit_one_cycle(active_keys=set())
    # First cycle: appeared envelope.
    assert any(
        i["kind"] == "errq_update"
        for i in _drain(session.outbound)
    )

    # Same buffer again — state tracker does not change, no diff.
    session.state_tracker.update_buffer(
        channel="B",
        buffer=bytes(buf),
        ts=2.0,
        bus="can0",
        can_id=0x101,
        hex_id="101",
        decode_buffer_fn=lambda *_: [],
    )
    keys_after_second = session._emit_one_cycle(active_keys=keys_after_first)
    items = _drain(session.outbound)
    assert not any(i["kind"] == "errq_update" for i in items)
    assert keys_after_second == keys_after_first


def _drain(queue) -> list:
    out = []
    while not queue.empty():
        out.append(queue.get_nowait())
    return out


# --------------------------------------------------------------------------
# T046: client envelope handling (US3) — set_filter, set_channel,
# pause/resume/clear, toggle_raw_frames mutate session state correctly.
# --------------------------------------------------------------------------


def _client_env(kind: str, **payload):
    """Hand-roll the client-side envelope shape (matches Zod). Pydantic
    discriminator picks the right variant based on `kind`.
    """
    return {"kind": kind, "payload": payload}


def test_set_filter_updates_substring() -> None:
    session = _make_session()
    from vayobd.live.session import _validate_client_envelope

    env = _validate_client_envelope(_client_env("set_filter", signal_name_substring="BRAKE"))
    session._apply_client(env)

    assert session.filter.signal_name_substring == "BRAKE"


def test_set_channel_narrows_filter() -> None:
    session = _make_session()
    from vayobd.live.session import _validate_client_envelope

    env = _validate_client_envelope(_client_env("set_channel", channel="A"))
    session._apply_client(env)

    assert session.filter.channel == "A"


def test_pause_then_resume_flushes_coalesced_buffer() -> None:
    """Pausing freezes the outbound flow but keeps decoding. Resume
    flushes a single coalesced signal_update with the latest values.
    """
    from vayobd.live.live_models import DecodedSignal
    from vayobd.live.session import _validate_client_envelope

    session = _make_session()
    session._apply_client(_validate_client_envelope(_client_env("pause")))
    assert session.paused is True

    # Stuff a synthetic signal into the coalesce buffer.
    session.coalesce.merge(
        DecodedSignal(
            name="TS_BrakePedalPosition",
            value=0.42,
            unit=None,
            channel="A",
            can_id=0x100,
            at_ms=1000,
        )
    )

    session._apply_client(_validate_client_envelope(_client_env("resume")))
    assert session.paused is False
    assert session.pause_buffer_count == 0

    items = _drain(session.outbound)
    sig_envs = [i for i in items if i["kind"] == "signal_update"]
    assert len(sig_envs) == 1
    assert sig_envs[0]["payload"]["signals"][0]["name"] == "TS_BrakePedalPosition"


def test_clear_resets_aggregator_state_and_coalesce() -> None:
    """Clear blanks the coalesce buffer + resets the errq aggregator
    and state tracker. The outbound queue is intentionally NOT cleared
    here — pending envelopes already on the wire are the WebSocket's
    responsibility, not the session's.
    """
    from vayobd.live.live_models import DecodedSignal
    from vayobd.live.session import _validate_client_envelope

    session = _make_session()
    session.coalesce.merge(
        DecodedSignal(
            name="TS_X",
            value=1,
            unit=None,
            channel="A",
            can_id=0x100,
            at_ms=1000,
        )
    )
    # Pre-load some errq state.
    buf = bytearray(64)
    buf[0] = 0x01
    session.state_tracker.update_buffer(
        channel="A",
        buffer=bytes(buf),
        ts=1.0,
        bus="can0",
        can_id=0x100,
        hex_id="100",
        decode_buffer_fn=lambda *_: [],
    )
    assert len(session.coalesce.items) == 1
    assert len(list(session.state_tracker.values())) == 1

    session._apply_client(_validate_client_envelope(_client_env("clear")))

    assert session.coalesce.items == {}
    assert list(session.state_tracker.values()) == []


# --------------------------------------------------------------------------
# T063: channel-inference regex (FR-026).
# --------------------------------------------------------------------------


def test_default_channel_patterns_classify_known_conventions() -> None:
    session = _make_session()
    assert session._infer_channel("TS_CHA_FOO") == "A"
    assert session._infer_channel("TS_CHB_BAR") == "B"
    assert session._infer_channel("FOO_CHA_BAR") == "A"
    assert session._infer_channel("FOO_CHB_BAR") == "B"
    assert session._infer_channel("Random_Signal") == "unknown"
    # Case-insensitive via the (?i) flag in the default.
    assert session._infer_channel("ts_cha_foo") == "A"


def test_custom_channel_patterns_take_effect() -> None:
    """Operator-supplied patterns drive classification; the defaults
    must not leak into a session that overrides them.
    """
    from vayobd.live.session import LiveDiagnosticSession

    class _StubWS:
        async def send_json(self, *_a, **_k) -> None:
            pass

        async def close(self, *_a, **_k) -> None:
            pass

    session = LiveDiagnosticSession(
        websocket=_StubWS(),  # type: ignore[arg-type]
        host_id="ts-de-ber-zeus",
        host_address="ts-de-ber-zeus",
        operator_slug="alice",
        errq_model=None,
        dbc_decoder=None,
        server_build=None,
        channel_a_pattern=r"^chA_",
        channel_b_pattern=r"^chB_",
    )

    assert session._infer_channel("chA_speed") == "A"
    assert session._infer_channel("chB_speed") == "B"
    # Default convention should NOT match under the custom patterns.
    assert session._infer_channel("TS_CHA_FOO") == "unknown"
    assert session._infer_channel("TS_CHB_FOO") == "unknown"


def test_invalid_regex_falls_back_to_defaults(caplog) -> None:
    """An operator typo on a regex MUST NOT crash session
    construction. The session should fall back to the defaults and
    emit a warning log.
    """
    from vayobd.live.session import LiveDiagnosticSession

    class _StubWS:
        async def send_json(self, *_a, **_k) -> None:
            pass

        async def close(self, *_a, **_k) -> None:
            pass

    with caplog.at_level("WARNING", logger="vayobd.live.session"):
        session = LiveDiagnosticSession(
            websocket=_StubWS(),  # type: ignore[arg-type]
            host_id="ts-de-ber-zeus",
            host_address="ts-de-ber-zeus",
            operator_slug="alice",
            errq_model=None,
            dbc_decoder=None,
            server_build=None,
            channel_a_pattern=r"[unclosed",  # invalid: unbalanced bracket
            channel_b_pattern=r"(?P<unclosed",  # invalid: unbalanced group
        )

    # Both invalid patterns should have logged warnings.
    warnings = [r for r in caplog.records if r.levelname == "WARNING"]
    rendered = [r.getMessage() for r in warnings]
    assert any("channel_pattern_invalid" in m for m in rendered), (
        f"expected channel_pattern_invalid warning, got {rendered}"
    )

    # Defaults (TS_CHA / TS_CHB) should now be in effect.
    assert session._infer_channel("TS_CHA_FOO") == "A"
    assert session._infer_channel("TS_CHB_FOO") == "B"


def test_toggle_raw_frames_flips_flag() -> None:
    session = _make_session()
    from vayobd.live.session import _validate_client_envelope

    assert session.filter.raw_frames_enabled is False
    session._apply_client(
        _validate_client_envelope(_client_env("toggle_raw_frames", enabled=True))
    )
    assert session.filter.raw_frames_enabled is True

    # Now feed a parsed frame manually and confirm a raw_frame envelope
    # lands. Using session._maybe_enqueue_raw with a fake frame.
    from vayobd.live.candump_runner import ParsedFrame

    frame = ParsedFrame(
        at_ms=1000,
        bus="can0",
        can_id=0x101,
        ext=False,
        fd=False,
        dlc=2,
        data=b"\x01\x02",
        raw_line="(1.000) can0 101#0102",
    )
    session._maybe_enqueue_raw(frame)
    items = _drain(session.outbound)
    raw_envs = [i for i in items if i["kind"] == "raw_frame"]
    assert len(raw_envs) == 1
    assert raw_envs[0]["payload"]["payload_hex"] == "0102"
    assert raw_envs[0]["payload"]["can_id"] == 0x101
