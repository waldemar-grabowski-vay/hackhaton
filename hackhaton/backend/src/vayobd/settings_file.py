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
from vayobd.models import AppSettings, InventorySettings, LiveSettings

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

    raw_dict = raw if isinstance(raw, dict) else {}
    inventory_block = raw_dict.get("inventory")
    inventory_settings: InventorySettings | None = None
    if isinstance(inventory_block, dict):
        candidate = inventory_block.get("path")
        if isinstance(candidate, str) and candidate.strip():
            try:
                inventory_settings = InventorySettings(path=Path(candidate))
            except ValidationError as exc:
                log.warning(
                    "settings_inventory_invalid",
                    path=candidate,
                    errors=[str(e.get("msg", "")) for e in exc.errors()],
                )

    # The live settings are conventionally written under a `[live]` table,
    # but operators routinely drop the section header and put `developer_mode`,
    # `ree_reecu_path`, etc. at the top level. Accept both shapes — fall back
    # to the top level when no `[live]` block exists.
    live_block = raw_dict.get("live")
    if not isinstance(live_block, dict):
        live_block = raw_dict
    live_settings = LiveSettings()
    if isinstance(live_block, dict):
        live_settings = LiveSettings(
            developer_mode=bool(live_block.get("developer_mode", False)),
            ree_reecu_path=Path(live_block["ree_reecu_path"])
            if isinstance(live_block.get("ree_reecu_path"), str) and live_block["ree_reecu_path"].strip()
            else None,
            dbc_path=Path(live_block["dbc_path"])
            if isinstance(live_block.get("dbc_path"), str) and live_block["dbc_path"].strip()
            else None,
            channel_a_pattern=(
                live_block["channel_a_pattern"]
                if isinstance(live_block.get("channel_a_pattern"), str)
                and live_block["channel_a_pattern"].strip()
                else None
            ),
            channel_b_pattern=(
                live_block["channel_b_pattern"]
                if isinstance(live_block.get("channel_b_pattern"), str)
                and live_block["channel_b_pattern"].strip()
                else None
            ),
        )

    return AppSettings(inventory=inventory_settings, live=live_settings)


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


def _quote(raw: str) -> str:
    return raw.replace("\\", "\\\\").replace('"', '\\"')


def _render_toml(settings: AppSettings) -> str:
    parts: list[str] = []
    if settings.inventory is not None:
        parts.append(f'[inventory]\npath = "{_quote(str(settings.inventory.path))}"\n')
    live = settings.live
    has_live_data = (
        live.developer_mode
        or live.ree_reecu_path is not None
        or live.dbc_path is not None
        or live.channel_a_pattern is not None
        or live.channel_b_pattern is not None
    )
    if has_live_data:
        block = ["[live]", f"developer_mode = {'true' if live.developer_mode else 'false'}"]
        if live.ree_reecu_path is not None:
            block.append(f'ree_reecu_path = "{_quote(str(live.ree_reecu_path))}"')
        if live.dbc_path is not None:
            block.append(f'dbc_path = "{_quote(str(live.dbc_path))}"')
        if live.channel_a_pattern is not None:
            block.append(f'channel_a_pattern = "{_quote(live.channel_a_pattern)}"')
        if live.channel_b_pattern is not None:
            block.append(f'channel_b_pattern = "{_quote(live.channel_b_pattern)}"')
        parts.append("\n".join(block) + "\n")
    return "\n".join(parts)
