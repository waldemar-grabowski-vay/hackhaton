"""
Telestation directory.

Pulls the list from the ree-vehicle-configs repo:
    <VEHICLE_CONFIGS_ROOT>/org/vay/telestations/*.yaml

Each YAML looks roughly like:

    # TS-BER-05
    network:
      ts_addresses:
      - 10.1.101.15
      - 10.1.102.15
      - 10.1.103.15
      - 10.1.104.15
    telestation:
      id: "ts-de-ber-00005"
      type: gamma
      system_category: genuine

`ts_addresses` are the four CAN-over-IP NICs. The SSH IP lives on a
separate management subnet:

    Berlin    (ts-de-ber-*) -> 10.1.200.<host>
    Las Vegas (ts-us-las-*) -> 10.128.200.<host>     (assumption — please correct via the JSON override if wrong)
    Other / lab            -> first ts_address (heuristic)

`<host>` is the trailing octet from the first ts_address.

Users can override any computed value by editing
%USERPROFILE%\\.tsdiag\\telestations_overrides.json.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from config import TELESTATIONS_DIR

log = logging.getLogger(__name__)


@dataclass
class Telestation:
    name: str                     # display name, e.g. "TS-BER-05"
    id: str                       # canonical id from yaml, e.g. "ts-de-ber-00005"
    host: str                     # SSH IP (computed or overridden)
    user: str = "wilhelm.leonhardt"
    port: int = 22
    location: str = ""            # "Berlin", "Las Vegas", "Lab"
    system_category: str = ""     # "genuine" / "testbed"
    ts_addresses: list[str] = field(default_factory=list)
    yaml_path: str = ""

    def display(self) -> str:
        bits = [self.name]
        if self.system_category and self.system_category != "genuine":
            bits.append(f"[{self.system_category}]")
        return " ".join(bits)


# ---------------------------------------------------------------------------
# YAML parsing
# ---------------------------------------------------------------------------
def _read_leading_comment(path: Path) -> str:
    """
    Return a short display name from the file's comment lines.

    Most YAMLs put a `# TS-BER-05` (or `# Apollo Telestation`) tag near
    the top — sometimes as the first line, sometimes after `env_vars:`.
    Scan the first ~20 lines for the first comment that looks like a
    name and strip alias parentheticals.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[:20]
    except OSError:
        return ""
    for raw in lines:
        line = raw.strip()
        if not line.startswith("#"):
            continue
        text = line.lstrip("# ").strip()
        # Skip the boilerplate "namespace alias needed for ..." comment
        # and TODO/FIXME chatter.
        if not text or text.lower().startswith(("todo", "fixme", "namespace alias", "workaround", "generic ")):
            continue
        # Trim parenthetical aliases like "TS-BER-02 (former Aphrodite ...)".
        if "(" in text:
            text = text.split("(", 1)[0].strip()
        return text
    return ""


def _location_for(canonical_id: str) -> tuple[str, str]:
    """Return (display_location, location_tag). Tag is one of 'ber','las','lab','other'."""
    cid = canonical_id.lower()
    if cid.startswith("ts-de-ber-"):
        if cid.endswith("lab"):
            return ("Berlin (Lab)", "lab")
        return ("Berlin", "ber")
    if cid.startswith("ts-us-las-"):
        return ("Las Vegas", "las")
    return ("Other", "other")


def _ssh_host_for(location_tag: str, ts_addresses: list[str]) -> str:
    """Compute the management/SSH IP from one of the ts_addresses."""
    if not ts_addresses:
        return ""
    first = ts_addresses[0]
    parts = first.split(".")
    if len(parts) != 4:
        return first
    host_octet = parts[3]
    if location_tag == "ber":
        return f"10.1.200.{host_octet}"
    if location_tag == "las":
        # Assumed mgmt subnet. Override per-station via the JSON file if wrong.
        return f"10.128.200.{host_octet}"
    # Lab / testbed / unknown — use the first ts_address verbatim.
    return first


def _parse_yaml(path: Path) -> Telestation | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        log.exception("telestations: cannot parse %s", path)
        return None
    if not isinstance(data, dict):
        return None

    ts_block = data.get("telestation") or data.get("control_room") or {}
    network_block = data.get("network") or {}
    canonical_id = str(ts_block.get("id") or "").strip()
    if not canonical_id:
        return None

    ts_addresses_raw = network_block.get("ts_addresses") or []
    ts_addresses: list[str] = []
    if isinstance(ts_addresses_raw, list):
        for item in ts_addresses_raw:
            if isinstance(item, str) and item.strip():
                ts_addresses.append(item.strip())

    display_loc, loc_tag = _location_for(canonical_id)
    host = _ssh_host_for(loc_tag, ts_addresses)
    name = _read_leading_comment(path) or canonical_id

    return Telestation(
        name=name,
        id=canonical_id,
        host=host,
        location=display_loc,
        system_category=str(ts_block.get("system_category") or "").strip(),
        ts_addresses=ts_addresses,
        yaml_path=str(path),
    )


# ---------------------------------------------------------------------------
# Per-user overrides
# ---------------------------------------------------------------------------
def _user_config_dir() -> Path:
    base = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(base) / ".tsdiag"


def _overrides_path() -> Path:
    return _user_config_dir() / "telestations_overrides.json"


def _load_overrides() -> dict[str, dict]:
    """Per-id overrides: {"ts-de-ber-00005": {"host": "10.1.200.15", "user": "..."}, ...}"""
    p = _overrides_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        log.exception("telestations: cannot parse overrides %s", p)
        return {}
    return data if isinstance(data, dict) else {}


def _apply_overrides(stations: list[Telestation]) -> list[Telestation]:
    overrides = _load_overrides()
    if not overrides:
        return stations
    for ts in stations:
        if ts.id in overrides:
            ov = overrides[ts.id]
            for field_name in ("name", "host", "user", "location"):
                if field_name in ov and ov[field_name]:
                    setattr(ts, field_name, str(ov[field_name]))
            if "port" in ov:
                try:
                    ts.port = int(ov["port"])
                except (TypeError, ValueError):
                    pass
    return stations


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def load() -> tuple[list[Telestation], Path | None]:
    """Return (stations sorted by location+id, source-dir or None)."""
    if not TELESTATIONS_DIR.is_dir():
        log.warning("telestations: directory missing: %s", TELESTATIONS_DIR)
        return [], None

    stations: list[Telestation] = []
    for path in sorted(TELESTATIONS_DIR.glob("*.yaml")):
        ts = _parse_yaml(path)
        if ts is not None:
            stations.append(ts)

    stations = _apply_overrides(stations)
    # Sort: known locations first (Berlin → Las Vegas → others), then by id.
    location_order = {"Berlin": 0, "Berlin (Lab)": 1, "Las Vegas": 2}
    stations.sort(key=lambda t: (location_order.get(t.location, 99), t.id))

    log.info("telestations: loaded %d stations from %s", len(stations), TELESTATIONS_DIR)
    return stations, TELESTATIONS_DIR


def open_overrides_in_editor() -> Path:
    """Open (or seed then open) the overrides JSON file."""
    p = _overrides_path()
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {
                    "_help": (
                        "Per-station overrides. Key = telestation id. Each value can "
                        "override any of: name, host, user, port, location."
                    ),
                    "ts-de-ber-00005": {"host": "10.1.200.15"},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    if os.name == "nt":
        try:
            os.startfile(str(p))  # type: ignore[attr-defined]
        except OSError:
            pass
    else:
        try:
            import subprocess
            subprocess.Popen(["xdg-open", str(p)])
        except Exception:  # noqa: BLE001
            pass
    return p
