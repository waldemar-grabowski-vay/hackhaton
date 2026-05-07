"""ERRQ Active/Passive lifecycle tracker (T008).

Ported from `TS_diagnostic_tool/errq_state.py` with one adjustment: the
"clear within 2 s" grace is no longer a hard-coded 2 s — passive entries
are surfaced via `disappeared_keys()` and the caller decides when to
emit them on the wire (so tests can use shorter cadences).

The single source of truth for the error table is `entries.values()`.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

log = logging.getLogger(__name__)

VIRTUAL_CHANNEL = "—"
ESTOP_KEY = (VIRTUAL_CHANNEL, 0, 0, "TS_ESTOP_BUTTON_PRESSED")


@dataclass
class ErrqEntry:
    channel: str
    byte: int
    bit_mask: int  # 1-bit mask, e.g. 0x04
    name: str
    description: str
    severity: str | None
    first_seen: float
    last_active: float
    status: str  # "active" or "passive"
    cleared_at: float | None
    bus: str = ""
    can_id: int = 0
    hex_id: str = ""

    @property
    def bit_index(self) -> int:
        """0-based bit index within the byte (0..7), or -1 if undefined."""
        return self.bit_mask.bit_length() - 1 if self.bit_mask else -1

    def key(self) -> tuple[str, int, int, str]:
        return (self.channel, self.byte, self.bit_mask, self.name)


EntryKey = tuple[str, int, int, str]


class ErrqStateTracker:
    """Owns the (channel, byte, bit, name) -> ErrqEntry table."""

    def __init__(self) -> None:
        self._entries: dict[EntryKey, ErrqEntry] = {}
        # Last buffer per channel — needed for the diff.
        self._prev: dict[str, bytes] = {"A": b"\x00" * 64, "B": b"\x00" * 64}

    @property
    def entries(self) -> dict[EntryKey, ErrqEntry]:
        return self._entries

    def update_buffer(
        self,
        channel: str,
        buffer: bytes,
        ts: float,
        bus: str,
        can_id: int,
        hex_id: str,
        decode_buffer_fn,
    ) -> list[ErrqEntry]:
        """Diff the latest 64-byte buffer against the previous one, keep
        active errors fresh, flip cleared bits to passive.

        `decode_buffer_fn(channel, buffer)` resolves symbolic names — pass
        `errq_loader.ErrqModel.decode_buffer` (or `lambda *_: []` to fall
        back to "ChX byteNN bitN" placeholder names).

        Returns the entries that changed (added or transitioned).
        """
        prev = self._prev.get(channel, b"\x00" * 64)
        cur = buffer + b"\x00" * max(0, 64 - len(buffer))
        prev = prev + b"\x00" * max(0, 64 - len(prev))

        changed_bytes = [i for i in range(64) if cur[i] != prev[i] or cur[i] != 0]
        if not changed_bytes:
            self._prev[channel] = bytes(cur)
            return []

        decoded = decode_buffer_fn(channel, bytes(cur))
        decoded_by_key: dict[tuple[int, int], object] = {
            (getattr(r, "byte", 0), getattr(r, "bit", 0)): r for r in decoded
        }

        changes: list[ErrqEntry] = []

        for i in range(64):
            byte_1based = i + 1
            cur_byte = cur[i]
            prev_byte = prev[i]
            if cur_byte == 0 and prev_byte == 0:
                continue
            for bit in range(8):
                mask = 1 << bit
                cur_bit = bool(cur_byte & mask)
                prev_bit = bool(prev_byte & mask)

                if cur_bit:
                    decoded_entry = decoded_by_key.get((byte_1based, mask))
                    name = (
                        decoded_entry.name  # type: ignore[union-attr]
                        if decoded_entry and getattr(decoded_entry, "name", None)
                        else f"Ch{channel} byte{byte_1based:02d} bit{bit}"
                    )
                    desc = (
                        decoded_entry.description  # type: ignore[union-attr]
                        if decoded_entry and getattr(decoded_entry, "description", None)
                        else name
                    )
                    severity = (
                        decoded_entry.severity  # type: ignore[union-attr]
                        if decoded_entry
                        else None
                    )
                    key: EntryKey = (channel, byte_1based, mask, name)
                    entry = self._entries.get(key)
                    if entry is None:
                        entry = ErrqEntry(
                            channel=channel,
                            byte=byte_1based,
                            bit_mask=mask,
                            name=name,
                            description=desc,
                            severity=severity,
                            first_seen=ts,
                            last_active=ts,
                            status="active",
                            cleared_at=None,
                            bus=bus,
                            can_id=can_id,
                            hex_id=hex_id,
                        )
                        self._entries[key] = entry
                        changes.append(entry)
                    else:
                        new_change = entry.status != "active"
                        entry.status = "active"
                        entry.last_active = ts
                        entry.cleared_at = None
                        if decoded_entry and getattr(decoded_entry, "name", None):
                            entry.name = decoded_entry.name  # type: ignore[union-attr]
                            entry.description = (
                                decoded_entry.description  # type: ignore[union-attr]
                                or decoded_entry.name  # type: ignore[union-attr]
                            )
                            entry.severity = decoded_entry.severity  # type: ignore[union-attr]
                        if new_change:
                            changes.append(entry)
                elif prev_bit and not cur_bit:
                    for k, entry in self._entries.items():
                        if (
                            entry.channel == channel
                            and entry.byte == byte_1based
                            and entry.bit_mask == mask
                            and entry.status == "active"
                        ):
                            entry.status = "passive"
                            entry.cleared_at = ts
                            changes.append(entry)
                            break

        self._prev[channel] = bytes(cur)
        return changes

    def reset(self) -> None:
        self._entries.clear()
        self._prev = {"A": b"\x00" * 64, "B": b"\x00" * 64}

    def values(self) -> Iterable[ErrqEntry]:
        return self._entries.values()
