"""
DBC loading + per-frame decoding using `cantools`.

The loader picks the most recently modified .dbc that matches one of the
configured globs under REPO_ROOT. Decoding is wrapped in a try/except so
unknown IDs or bad payloads never bubble up to the UI thread.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import cantools
from cantools.database import Database
from cantools.database.can.message import Message

from config import DBC_GLOB_PATTERNS, ERROR_MESSAGE_HINTS, PRIMARY_DBC, REPO_ROOT, TS_STATE_SIGNALS

log = logging.getLogger(__name__)


@dataclass
class DecodedFrame:
    ts: float
    bus: str
    can_id: int
    ext: bool
    message_name: str | None
    signals: dict[str, object] = field(default_factory=dict)
    is_error_message: bool = False
    state_signals: dict[str, object] = field(default_factory=dict)
    raw: bytes = b""

    @property
    def hex_id(self) -> str:
        return f"{self.can_id:08X}" if self.ext else f"{self.can_id:03X}"


def find_dbc(repo_root: Path = REPO_ROOT, patterns: Iterable[str] = DBC_GLOB_PATTERNS) -> Path | None:
    """Find the TS APP DBC.

    Prefers the explicit `PRIMARY_DBC` if it exists; otherwise falls back
    to the most recently modified glob match under repo_root.
    """
    if PRIMARY_DBC.is_file():
        return PRIMARY_DBC
    if not repo_root.exists():
        log.warning("Repo root does not exist: %s", repo_root)
        return None
    candidates: list[Path] = []
    for pat in patterns:
        candidates.extend(repo_root.glob(pat))
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


class DbcDecoder:
    def __init__(self, dbc_path: Path | None = None):
        self.dbc_path: Path | None = None
        self.db: Database | None = None
        self.state_signal_set = {s.lower() for s in TS_STATE_SIGNALS}
        if dbc_path is not None:
            self.load(dbc_path)

    # ---- load ----
    def load(self, path: Path) -> None:
        log.info("Loading DBC: %s", path)
        self.db = cantools.database.load_file(str(path))
        self.dbc_path = Path(path)

    def autoload(self) -> Path | None:
        path = find_dbc()
        if path:
            self.load(path)
        return path

    def all_signal_names(self) -> list[str]:
        """Every signal name across every message — used by the signal picker."""
        if not self.db:
            return []
        names: set[str] = set()
        for msg in self.db.messages:
            for sig in msg.signals:
                names.add(sig.name)
        return sorted(names)

    # ---- decode ----
    def decode(self, ts: float, bus: str, can_id: int, ext: bool, data: bytes) -> DecodedFrame:
        out = DecodedFrame(ts=ts, bus=bus, can_id=can_id, ext=ext, message_name=None, raw=data)
        if not self.db:
            return out
        try:
            msg: Message = self.db.get_message_by_frame_id(can_id)
        except KeyError:
            return out
        out.message_name = msg.name
        try:
            decoded = self.db.decode_message(can_id, data)
        except Exception as exc:  # noqa: BLE001
            log.debug("decode failed for %s/%s: %s", msg.name, data.hex(), exc)
            return out
        if isinstance(decoded, dict):
            out.signals = dict(decoded)
            # Categorize.
            mname = msg.name.lower()
            if any(h in mname for h in ERROR_MESSAGE_HINTS):
                out.is_error_message = True
            for sig_name, value in decoded.items():
                if sig_name.lower() in self.state_signal_set:
                    out.state_signals[sig_name] = value
                lname = sig_name.lower()
                if any(h in lname for h in ERROR_MESSAGE_HINTS):
                    out.is_error_message = True
        return out
