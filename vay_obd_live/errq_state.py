"""
ERRQ + virtual-error state tracker (Active/Passive lifecycle).

For each (channel, byte, bit) bit-mask error we keep:
  * status:      "active" or "passive"
  * first_seen:  timestamp the bit first went high
  * last_active: timestamp the bit was last observed high
  * cleared_at:  timestamp the bit went low (passive transition), or None

The tracker is the single source of truth for the error table — every UI
update walks `entries.values()` and renders accordingly.

A second lane covers *virtual* errors that aren't ERRQ bits but should
appear in the same table — e.g. the TS e-Stop button being pressed.
Virtual entries use a pseudo-channel "—" and a sentinel byte/bit so they
don't collide with real ERRQ keys.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable

log = logging.getLogger(__name__)

VIRTUAL_CHANNEL = "—"
ESTOP_KEY = (VIRTUAL_CHANNEL, 0, 0, "TS_ESTOP_BUTTON_PRESSED")


@dataclass
class ErrqEntry:
    channel: str
    byte: int
    bit_mask: int            # the 1-bit mask, e.g. 0x04
    name: str                # symbolic error id from errq
    description: str         # short explanation (often == name)
    severity: str | None
    first_seen: float
    last_active: float
    status: str              # "active" or "passive"
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


class ErrqStateTracker:
    """Owns the (channel, byte, bit) -> ErrqEntry table."""

    def __init__(self):
        self._entries: dict[tuple[str, int, int, str], ErrqEntry] = {}
        # Last buffer we processed per channel — needed to compute the diff.
        self._prev: dict[str, bytes] = {"A": b"\x00" * 64, "B": b"\x00" * 64}

    @property
    def entries(self) -> dict[tuple[str, int, int, str], ErrqEntry]:
        return self._entries

    # -----------------------------------------------------------------
    # ERRQ buffer ingest
    # -----------------------------------------------------------------
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
        """
        Diff the latest 64-byte buffer against the previous one, keep
        active errors fresh and flip cleared bits to passive.

        Returns the entries that changed (added or transitioned).

        `decode_buffer_fn(channel, buffer)` should be errq_bridge.
        decode_errq_buffer — used to resolve symbolic names lazily.
        """
        prev = self._prev.get(channel, b"\x00" * 64)
        # Pad shorter buffers to 64 bytes so XOR doesn't crash on rare
        # short frames.
        cur = buffer + b"\x00" * max(0, 64 - len(buffer))
        prev = prev + b"\x00" * max(0, 64 - len(prev))

        # Fast diff: only re-decode bytes that changed.
        changed_bytes = [i for i in range(64) if cur[i] != prev[i] or cur[i] != 0]
        # We always need to handle bytes that went non-zero->zero too —
        # the comparison `cur[i] != prev[i]` covers that. The `cur[i] != 0`
        # ensures we re-confirm currently active bits as still active even
        # when nothing changed.

        if not changed_bytes:
            self._prev[channel] = bytes(cur)
            return []

        # Build a quick lookup from errq decode for the current buffer.
        # Each result has byte (1-based) + bit_mask + name + description + severity.
        decoded = decode_buffer_fn(channel, bytes(cur))
        decoded_by_key: dict[tuple[int, int], object] = {
            (r.byte, r.bit): r for r in decoded
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
                    # Active — make sure we have an entry, refresh last_active.
                    decoded_entry = decoded_by_key.get((byte_1based, mask))
                    name = (
                        decoded_entry.name if decoded_entry and decoded_entry.name
                        else f"Ch{channel} byte{byte_1based:02d} bit{bit}"
                    )
                    desc = (
                        decoded_entry.description if decoded_entry and decoded_entry.description
                        else name
                    )
                    severity = decoded_entry.severity if decoded_entry else None
                    key = (channel, byte_1based, mask, name)
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
                        # Refresh metadata in case decode resolved something
                        # that was previously fallback-named.
                        if decoded_entry and decoded_entry.name:
                            entry.name = decoded_entry.name
                            entry.description = decoded_entry.description or decoded_entry.name
                            entry.severity = decoded_entry.severity
                        if new_change:
                            changes.append(entry)
                elif prev_bit and not cur_bit:
                    # Bit cleared — find the matching entry and flip it passive.
                    # We don't know the name, so search by (channel, byte, mask).
                    for key, entry in self._entries.items():
                        if entry.channel == channel and entry.byte == byte_1based and entry.bit_mask == mask:
                            if entry.status == "active":
                                entry.status = "passive"
                                entry.cleared_at = ts
                                changes.append(entry)
                            break

        self._prev[channel] = bytes(cur)
        return changes

    # -----------------------------------------------------------------
    # Virtual errors (e-stop, etc.)
    # -----------------------------------------------------------------
    def set_virtual(
        self,
        key: tuple[str, int, int, str],
        active: bool,
        ts: float,
        description: str = "",
        severity: str | None = "critical",
        bus: str = "",
        can_id: int = 0,
        hex_id: str = "",
    ) -> ErrqEntry | None:
        """
        Mark a virtual error active/passive. Returns the entry if its
        status actually changed (so the UI can update); else None.
        """
        entry = self._entries.get(key)
        if active:
            if entry is None:
                entry = ErrqEntry(
                    channel=key[0],
                    byte=key[1],
                    bit_mask=key[2],
                    name=key[3],
                    description=description or key[3],
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
                return entry
            else:
                changed = entry.status != "active"
                entry.status = "active"
                entry.last_active = ts
                entry.cleared_at = None
                return entry if changed else None
        else:
            if entry is None or entry.status != "active":
                return None
            entry.status = "passive"
            entry.cleared_at = ts
            return entry

    def reset(self) -> None:
        self._entries.clear()
        self._prev = {"A": b"\x00" * 64, "B": b"\x00" * 64}

    def values(self) -> Iterable[ErrqEntry]:
        return self._entries.values()
