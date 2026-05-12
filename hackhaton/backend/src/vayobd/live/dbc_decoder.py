"""DBC decoder (T010).

Wraps `cantools` with a per-instance `can_id → message` cache so the hot
path is a hashtable lookup + cantools' bit-extract. Also provides the
`find_dbc()` glob fallback that mirrors the desktop tool's
`dbc_handler.find_dbc()` — when no explicit `dbc_path` is configured,
search the operator's `ree-reecu` clone for a usable DBC.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Glob patterns matched relative to the repo root. `find_dbc` returns
# the most-recently-modified file among all matches.
DBC_GLOB_PATTERNS: tuple[str, ...] = (
    "dbc/application_protocol.dbc",
    "platform/dbc/*.dbc",
    "ts/6_tools/CANoe_G4/DBCs/*.dbc",
    "platform/tools/sec_bindings_generator/ts_*.dbc",
    "**/*.dbc",
)

# 008: tightened search — when picking from a noisy ree-reecu clone
# (multiple .dbc files, possibly including the legacy Env.dbc stub
# with zero TS-application signals), prefer `application_protocol*.dbc`
# over anything else. Only fall back to the generic glob if no
# application_protocol DBC exists.
DBC_PREFERRED_PATTERNS: tuple[str, ...] = (
    "dbc/application_protocol.dbc",
    "platform/dbc/application_protocol*.dbc",
    "ts/6_tools/CANoe_G4/DBCs/application_protocol*.dbc",
    "ts/6_tools/CANoe_G4/dbcs/application_protocol*.dbc",
    "ve/6_tools/CANoe_G4/DBCs/application_protocol*.dbc",
    "ve/6_tools/CANoe_G4/dbcs/application_protocol*.dbc",
    "**/application_protocol*.dbc",
)


def find_dbc(
    repo_root: Path,
    patterns: Iterable[str] = DBC_GLOB_PATTERNS,
) -> Path | None:
    """Return the most-recently-modified DBC under `repo_root` that
    matches any of `patterns`, or None when nothing matches.

    008: prefers `application_protocol*.dbc` (via DBC_PREFERRED_PATTERNS)
    when any match. Only falls back to the generic patterns when no
    application_protocol DBC is present. Prevents the legacy `Env.dbc`
    stub from being picked when the application DBC exists in the same
    clone.
    """
    if not repo_root.exists():
        log.warning("dbc: ree-reecu root does not exist: %s", repo_root)
        return None

    # First pass: prefer application_protocol.dbc — these carry the TS
    # signals the live page actually needs.
    preferred: list[Path] = []
    for pat in DBC_PREFERRED_PATTERNS:
        preferred.extend(repo_root.glob(pat))
    if preferred:
        preferred.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return preferred[0]

    # Fall back to the legacy catch-all when no application_protocol DBC
    # is present (covers older clone layouts and the existing tests).
    candidates: list[Path] = []
    for pat in patterns:
        candidates.extend(repo_root.glob(pat))
    if not candidates:
        log.warning("dbc: no .dbc found under %s for patterns %s", repo_root, list(patterns))
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


@dataclass
class DecodedFrame:
    at_ms: int
    bus: str
    can_id: int
    ext: bool
    message_name: str | None
    signals: dict[str, Any] = field(default_factory=dict)
    raw: bytes = b""

    @property
    def hex_id(self) -> str:
        return f"{self.can_id:08X}" if self.ext else f"{self.can_id:03X}"


class DbcDecoder:
    """Per-instance DBC. Lifetime is the FastAPI process — load once on
    startup, share read-only across sessions.

    `decode(can_id, payload)` returns `(message_name, signals)`. When the
    can_id is not in the loaded DBC, signals come back empty so the
    caller can route the frame through the raw-frame log instead (FR-008).
    """

    def __init__(self) -> None:
        self.dbc_path: Path | None = None
        self.db: Any = None
        self._msg_by_id: dict[int, Any] = {}
        self.loaded_at: datetime | None = None
        self.load_error: str | None = None

    @property
    def loaded(self) -> bool:
        return self.db is not None

    def load(self, path: Path) -> None:
        """Load a DBC from disk. Raises on failure — call sites should
        wrap in try/except and fall back to degraded mode.
        """
        # Imported lazily so the backend can boot in environments where
        # cantools failed to install (degraded mode).
        import cantools  # type: ignore[import-not-found]

        log.info("dbc: loading %s", path)
        self.db = cantools.database.load_file(str(path))
        self.dbc_path = Path(path)
        self.loaded_at = datetime.now(timezone.utc)
        self._msg_by_id.clear()
        self.load_error = None

    def autoload(self, dbc_search_root: Path, explicit: Path | None = None) -> bool:
        """Try `explicit` first; fall back to `find_dbc(dbc_search_root)`.

        008: `dbc_search_root` should point at the `ree-reecu-dbc` clone
        (the DBC lives in its own repo, separate from `ree-reecu`).
        Falls through to degraded mode if neither resolves.
        """
        target = explicit
        if target is None:
            target = find_dbc(dbc_search_root)
        if target is None or not target.is_file():
            self.load_error = (
                f"DBC not found — checked explicit={explicit!r} and globs under "
                f"{dbc_search_root} (expected {dbc_search_root}/application_protocol.dbc). "
                f"Run `vayobd refresh` to clone ree-reecu-dbc, or set "
                f"VAYOBD_DBC_PATH=/full/path/to/your.dbc to override."
            )
            log.warning(self.load_error)
            return False
        try:
            self.load(target)
        except Exception as exc:  # noqa: BLE001
            self.load_error = f"DBC load failed for {target}: {exc!r}"
            log.exception(self.load_error)
            return False
        log.info(
            "dbc: loaded from %s — %d messages",
            self.dbc_path,
            len(getattr(self.db, "messages", []) or []),
        )
        return True

    def decode(
        self,
        at_ms: int,
        bus: str,
        can_id: int,
        ext: bool,
        data: bytes,
    ) -> DecodedFrame:
        out = DecodedFrame(at_ms=at_ms, bus=bus, can_id=can_id, ext=ext, message_name=None, raw=data)
        if not self.loaded:
            return out
        msg = self._msg_by_id.get(can_id)
        if msg is None:
            try:
                msg = self.db.get_message_by_frame_id(can_id)  # type: ignore[union-attr]
            except KeyError:
                self._msg_by_id[can_id] = None  # type: ignore[assignment]
                return out
            self._msg_by_id[can_id] = msg
        if msg is None:
            return out
        out.message_name = msg.name
        try:
            decoded = self.db.decode_message(can_id, data)  # type: ignore[union-attr]
        except Exception as exc:  # noqa: BLE001
            log.debug("dbc: decode failed for %s/%s: %s", msg.name, data.hex(), exc)
            return out
        if isinstance(decoded, dict):
            out.signals = dict(decoded)
        return out
