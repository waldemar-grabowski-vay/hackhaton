"""T017 — ErrqAggregator unit tests.

Verifies the ported behaviour from `TS_diagnostic_tool/errq_aggregator.py`:
per-byte signal stitching into the 64-byte buffer, the bytes-like
fallback path, and the channel A/B touch tracking.
"""

from __future__ import annotations

from vayobd.live.errq_aggregator import ErrqAggregator


def test_per_byte_signals_stitch_into_buffer() -> None:
    agg = ErrqAggregator()
    touched = agg.ingest(
        {
            "TS_ChA_ERRQ_Byte01": 0x01,
            "TS_ChA_ERRQ_Byte02": 0x02,
            "TS_ChA_ERRQ_Byte64": 0xFF,
            "Unrelated_Signal": 99,
        }
    )
    assert touched == {"A"}
    snap = agg.snapshot("A")
    assert snap[0] == 0x01
    assert snap[1] == 0x02
    assert snap[63] == 0xFF
    # B untouched.
    assert agg.snapshot("B") == bytes(64)


def test_byte_signals_with_prefix_and_case_match() -> None:
    agg = ErrqAggregator()
    # The desktop tool's regex tolerates leading "MessageName.TS_..." and
    # mixed case — make sure ours does too.
    touched = agg.ingest({"TS_App.TS_chA_ERRQ_Byte05": 0xAA})
    assert touched == {"A"}
    assert agg.snapshot("A")[4] == 0xAA


def test_full_bytes_signal_path() -> None:
    agg = ErrqAggregator()
    payload = bytes([i for i in range(64)])
    touched = agg.ingest({"TS_ChB_ERRQ": payload})
    assert touched == {"B"}
    assert agg.snapshot("B") == payload


def test_invalid_value_skipped() -> None:
    agg = ErrqAggregator()
    touched = agg.ingest({"TS_ChA_ERRQ_Byte01": "not-a-number"})
    assert touched == set()
    assert agg.snapshot("A") == bytes(64)


def test_reset_clears_both_channels() -> None:
    agg = ErrqAggregator()
    agg.ingest({"TS_ChA_ERRQ_Byte01": 0xFF, "TS_ChB_ERRQ_Byte01": 0xFF})
    agg.reset()
    assert agg.snapshot("A") == bytes(64)
    assert agg.snapshot("B") == bytes(64)


def test_empty_signals_returns_empty_set() -> None:
    assert ErrqAggregator().ingest({}) == set()
