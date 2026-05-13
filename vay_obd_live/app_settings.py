"""
Persistent user settings.

JSON file at %USERPROFILE%\\.tsdiag\\settings.json. Holds the things the
user shouldn't have to re-enter every launch:

  - last_ts_id: canonical id of the last-selected telestation
  - ssh_key_filename: path to the private key the user picked
  - ssh_user: override of the default user, if set
  - remember_ssh: whether the user opted in to remembering the key file

Plain JSON, no schema validation. Future fields are added by adding keys.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class AppSettings:
    last_ts_id: str = ""
    last_ve_id: str = ""
    ssh_key_filename: str = ""
    ssh_user: str = ""
    remember_ssh: bool = True


def _config_path() -> Path:
    base = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(base) / ".tsdiag" / "settings.json"


def load() -> AppSettings:
    p = _config_path()
    if not p.is_file():
        return AppSettings()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        log.exception("settings: cannot parse %s", p)
        return AppSettings()
    if not isinstance(data, dict):
        return AppSettings()
    s = AppSettings()
    for f in fields(s):
        if f.name in data:
            try:
                setattr(s, f.name, type(getattr(s, f.name))(data[f.name]))
            except (TypeError, ValueError):
                pass
    log.info("settings: loaded from %s", p)
    return s


def save(settings: AppSettings) -> Path:
    p = _config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
    log.info("settings: saved to %s", p)
    return p
