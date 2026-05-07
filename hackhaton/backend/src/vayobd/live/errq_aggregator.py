"""ERRQ byte aggregator (T007).

Ported from `TS_diagnostic_tool/errq_aggregator.py` with one adjustment:
`_BYTE_SIG_RE` is a class-level constant on `ErrqAggregator` so it can be
overridden by tests.

Reads `TS_Ch[AB]_ERRQ_Byte01..64` signals out of decoded frames and
stitches them back into a 64-byte buffer per channel. The buffer is
handed off to the `ErrqStateTracker` which manages the Active/Passive
lifecycle.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

_FULL_SIG_NAMES = ("TS_ChA_ERRQ", "TS_ChB_ERRQ")


@dataclass
class _ChannelBuffer:
    bytes_: bytearray = field(default_factory=lambda: bytearray(64))

    def set(self, idx: int, value: int) -> None:
        if 0 <= idx < len(self.bytes_):
            self.bytes_[idx] = value & 0xFF

    def snapshot(self) -> bytes:
        return bytes(self.bytes_)


class ErrqAggregator:
    """Pure aggregator: ingests signals, exposes per-channel snapshots.

    Lifecycle (active/passive) is owned by `ErrqStateTracker` — this class
    only assembles bytes.
    """

    BYTE_SIG_RE = re.compile(
        r"^.*TS_Ch(?P<ch>[AB])_ERRQ_Byte(?P<idx>\d{1,3})\s*$",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        self._channels: dict[str, _ChannelBuffer] = {
            "A": _ChannelBuffer(),
            "B": _ChannelBuffer(),
        }

    def ingest(self, signals: dict[str, object]) -> set[str]:
        """Update buffers from a frame's decoded signals.

        Returns the set of channels touched ("A"/"B") so the caller knows
        whose snapshot to grab.
        """
        if not signals:
            return set()
        touched: set[str] = set()

        # Path 1: per-byte signals (TS_Ch[AB]_ERRQ_ByteNN).
        for name, value in signals.items():
            m = self.BYTE_SIG_RE.match(str(name))
            if not m:
                continue
            ch = m.group("ch").upper()
            idx_one_based = int(m.group("idx"))
            idx = idx_one_based - 1 if idx_one_based >= 1 else idx_one_based
            try:
                ival = int(value)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                continue
            self._channels[ch].set(idx, ival)
            touched.add(ch)

        # Path 2: a single bytes-like signal carrying the whole array.
        for full_name in _FULL_SIG_NAMES:
            if full_name in signals:
                ch = "A" if "ChA" in full_name else "B"
                value = signals[full_name]
                if isinstance(value, (bytes, bytearray)):
                    buf = self._channels[ch]
                    for i, b in enumerate(value[: len(buf.bytes_)]):
                        buf.set(i, int(b))
                    touched.add(ch)
        return touched

    def snapshot(self, channel: str) -> bytes:
        return self._channels[channel].snapshot()

    def reset(self) -> None:
        for ch in self._channels.values():
            ch.bytes_ = bytearray(64)
