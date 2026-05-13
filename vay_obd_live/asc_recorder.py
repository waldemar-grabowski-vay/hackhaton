"""
ASC (Vector) recording for live CAN traffic.

Wraps python-can's ASCWriter (which ships with cantools as a transitive
dep) so the app can dump frames to a Vector-compatible .asc log that
opens cleanly in CANalyzer, BusMaster, SavvyCAN, etc.

Usage:
    rec = AscRecorder("dump.asc")
    rec.write(frame)        # frame dict from ssh_can_reader
    ...
    rec.close()
"""
from __future__ import annotations

import logging
from pathlib import Path

import can
from can.io import ASCWriter

log = logging.getLogger(__name__)


# CAN-FD DLC table (DLC value -> data length in bytes). Only DLC 9..15
# differ from the byte count.
_FD_DLC_FOR_LEN = {
    0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8,
    12: 9, 16: 10, 20: 11, 24: 12, 32: 13, 48: 14, 64: 15,
}


def _bus_to_channel(bus_name: str) -> int:
    """Map "can0" -> 1, "can1" -> 2, ..."""
    digits = "".join(c for c in bus_name if c.isdigit())
    try:
        return int(digits) + 1 if digits else 1
    except ValueError:
        return 1


class AscRecorder:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        # ASCWriter accepts a file path; channel "default" lets us mix
        # multiple buses by setting msg.channel per-message.
        self._writer = ASCWriter(str(self.path))
        self._count = 0
        log.info("ASC recording started -> %s", self.path)

    def write(self, frame: dict) -> None:
        """Convert a streamer frame dict into a can.Message and emit it."""
        try:
            data = frame["data"]
            is_fd = bool(frame.get("fd", False))
            flags = int(frame.get("flags", 0))
            # FD flag-nibble bit meanings per Linux SocketCAN:
            #   bit 0 = BRS (Bit Rate Switch)
            #   bit 1 = ESI (Error State Indicator)
            #   bit 2 = (reserved)
            #   bit 3 = (reserved)
            brs = bool(flags & 0x1) if is_fd else False
            esi = bool(flags & 0x2) if is_fd else False

            kwargs = dict(
                timestamp=float(frame["ts"]),
                arbitration_id=int(frame["can_id"]),
                is_extended_id=bool(frame["ext"]),
                data=bytes(data),
                channel=_bus_to_channel(frame.get("bus", "can0")),
            )
            if is_fd:
                kwargs["is_fd"] = True
                kwargs["bitrate_switch"] = brs
                kwargs["error_state_indicator"] = esi
                kwargs["dlc"] = _FD_DLC_FOR_LEN.get(len(data), len(data))
            else:
                kwargs["dlc"] = len(data)

            msg = can.Message(**kwargs)
            self._writer.on_message_received(msg)
            self._count += 1
        except Exception as exc:  # noqa: BLE001
            log.exception("ASC write failed: %s", exc)

    @property
    def count(self) -> int:
        return self._count

    def close(self) -> None:
        try:
            self._writer.stop()
        except Exception:  # noqa: BLE001
            log.exception("ASC writer close failed")
        log.info("ASC recording stopped after %d frames -> %s", self._count, self.path)
