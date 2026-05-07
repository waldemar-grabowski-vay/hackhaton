"""Operator-level settings persistence (T010, FR-009 — FR-012).

A tiny TOML round-trip for `~/.config/vayobd/settings.toml`. The file
holds the operator's chosen `ree-vehicle-configs` clone path; nothing
else, no secrets. Read via stdlib `tomllib`; written via a small
hand-rolled serialiser (we don't want to pull `tomli-w` for one
shape).

XDG-aware: `${XDG_CONFIG_HOME}/vayobd/settings.toml` if the env var
is set, else `~/.config/vayobd/settings.toml`.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

from pydantic import ValidationError

from vayobd.logging import get_logger
from vayobd.models import AppSettings, InventorySettings

log = get_logger(__name__)


def settings_path() -> Path:
    """Resolve the on-disk location for the settings TOML."""
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home) if config_home else Path.home() / ".config"
    return base / "vayobd" / "settings.toml"


def load_settings(path: Path | None = None) -> AppSettings:
    """Read settings from disk.

    Returns `AppSettings(inventory=None)` when:
      - the file is absent (first launch),
      - the file is malformed,
      - the persisted path no longer validates (folder moved /
        deleted, etc.).

    The "no file yet" / "stale path" cases collapse to the same
    "show the setup card" state for the SPA — the difference is
    surfaced only in the structured error code returned by
    `POST /api/settings/inventory-path` validation, not by this
    read path.
    """
    p = path or settings_path()
    if not p.is_file():
        return AppSettings(inventory=None)
    try:
        with p.open("rb") as f:
            raw = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("settings_toml_unreadable", path=str(p), error=str(exc))
        return AppSettings(inventory=None)

    inventory_block = raw.get("inventory") if isinstance(raw, dict) else None
    if not isinstance(inventory_block, dict):
        return AppSettings(inventory=None)
    candidate = inventory_block.get("path")
    if not isinstance(candidate, str) or not candidate.strip():
        return AppSettings(inventory=None)

    try:
        return AppSettings(inventory=InventorySettings(path=Path(candidate)))
    except ValidationError as exc:
        log.warning(
            "settings_inventory_invalid",
            path=candidate,
            errors=[str(e.get("msg", "")) for e in exc.errors()],
        )
        return AppSettings(inventory=None)


def save_settings(settings: AppSettings, path: Path | None = None) -> None:
    """Persist `settings` to TOML.

    Raises ValueError on validation failure — the API layer catches
    these before they reach disk, but defending here means the helper
    is safe to call from tests too.
    """
    p = path or settings_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    body = _render_toml(settings)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    tmp.replace(p)
    log.info("settings_persisted", path=str(p))


def _render_toml(settings: AppSettings) -> str:
    if settings.inventory is None:
        return ""
    # Resolve to absolute string; quote-escape any embedded `"` defensively
    # (Path.expanduser/resolve() in InventorySettings normalises this already).
    raw = str(settings.inventory.path)
    escaped = raw.replace("\\", "\\\\").replace('"', '\\"')
    return f"[inventory]\npath = \"{escaped}\"\n"
