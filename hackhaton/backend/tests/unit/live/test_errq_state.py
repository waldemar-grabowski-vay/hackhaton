"""T018 — ErrqStateTracker active/passive lifecycle tests."""

from __future__ import annotations

from vayobd.live.errq_state import ErrqStateTracker


def _no_decode(_channel: str, _data: bytes) -> list[object]:
    return []


def test_bit_appears_then_clears_marks_passive() -> None:
    tracker = ErrqStateTracker()
    # Byte 3 (1-based), bit 2 = mask 0x04.
    buf = bytearray(64)
    buf[2] = 0x04

    appeared = tracker.update_buffer(
        "A",
        bytes(buf),
        ts=1.0,
        bus="can0",
        can_id=0x123,
        hex_id="123",
        decode_buffer_fn=_no_decode,
    )
    assert len(appeared) == 1
    entry = appeared[0]
    assert entry.channel == "A"
    assert entry.byte == 3
    assert entry.bit_mask == 0x04
    assert entry.status == "active"
    assert entry.cleared_at is None

    # Bit clears on the next buffer.
    cleared = tracker.update_buffer(
        "A",
        bytes(64),
        ts=2.0,
        bus="can0",
        can_id=0x123,
        hex_id="123",
        decode_buffer_fn=_no_decode,
    )
    assert len(cleared) == 1
    assert cleared[0].status == "passive"
    assert cleared[0].cleared_at == 2.0


def test_no_change_returns_empty() -> None:
    tracker = ErrqStateTracker()
    assert tracker.update_buffer(
        "A", bytes(64), ts=0.0, bus="can0", can_id=0, hex_id="000", decode_buffer_fn=_no_decode
    ) == []


def test_re_active_after_passive_emits_change() -> None:
    tracker = ErrqStateTracker()
    buf = bytearray(64)
    buf[0] = 0x01
    tracker.update_buffer("A", bytes(buf), ts=0.0, bus="", can_id=0, hex_id="", decode_buffer_fn=_no_decode)
    tracker.update_buffer("A", bytes(64), ts=1.0, bus="", can_id=0, hex_id="", decode_buffer_fn=_no_decode)
    # Re-arm.
    appeared = tracker.update_buffer(
        "A", bytes(buf), ts=2.0, bus="", can_id=0, hex_id="", decode_buffer_fn=_no_decode
    )
    assert len(appeared) == 1
    assert appeared[0].status == "active"
    assert appeared[0].cleared_at is None


def test_reset_clears_state() -> None:
    tracker = ErrqStateTracker()
    buf = bytearray(64)
    buf[0] = 0x01
    tracker.update_buffer("A", bytes(buf), ts=0.0, bus="", can_id=0, hex_id="", decode_buffer_fn=_no_decode)
    tracker.reset()
    # After reset the bit looks "fresh".
    appeared = tracker.update_buffer(
        "A", bytes(buf), ts=1.0, bus="", can_id=0, hex_id="", decode_buffer_fn=_no_decode
    )
    assert len(appeared) == 1
