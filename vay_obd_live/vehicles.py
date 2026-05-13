"""
Vehicle directory.

Reads <VEHICLE_CONFIGS_ROOT>/org/vay/vehicles/*.yaml and produces a flat
list for the VE: dropdown.

The YAMLs don't carry a clean "management IP" for SSH; we default
`host` to the first entry in `network.ve_addresses` and let the user
override per-vehicle in %USERPROFILE%\\.tsdiag\\vehicles_overrides.json.

Override format mirrors the telestation overrides:
    {
      "ve-de-00008": {"host": "10.1.250.8", "user": "wilhelm.leonhardt"}
    }
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from config import VEHICLES_DIR

log = logging.getLogger(__name__)


@dataclass
class Vehicle:
    name: str
    id: str
    host: str = ""                # SSH/management IP — first ve_address by default
    user: str = "wilhelm.leonhardt"
    port: int = 22
    description: str = ""
    license_plate: str = ""
    location: str = ""            # "Germany", "USA", "Lab/Fake"
    system_category: str = ""
    ve_addresses: list[str] = field(default_factory=list)
    yaml_path: str = ""

    def display(self) -> str:
        bits = [self.name]
        if self.license_plate:
            bits.append(f"({self.license_plate})")
        return " ".join(bits)


def _location_for(canonical_id: str) -> str:
    cid = canonical_id.lower()
    if cid.startswith("ve-de-"):
        return "Germany"
    if cid.startswith("ve-us-"):
        return "USA"
    if cid.startswith("fakecar"):
        return "Lab"
    return "Other"


def _read_leading_comment(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()[:20]
    except OSError:
        return ""
    for raw in lines:
        line = raw.strip()
        if not line.startswith("#"):
            continue
        text = line.lstrip("# ").strip()
        if not text or text.lower().startswith(("todo", "fixme", "namespace alias", "workaround")):
            continue
        # Strip parenthetical aliases and "...-REECU vehicle" trailers.
        if "(" in text:
            text = text.split("(", 1)[0].strip()
        if " - " in text:
            text = text.split(" - ", 1)[0].strip()
        return text
    return ""


def _parse_yaml(path: Path) -> Vehicle | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        log.exception("vehicles: cannot parse %s", path)
        return None
    if not isinstance(data, dict):
        return None
    veh = data.get("vehicle") or {}
    network = data.get("network") or {}
    canonical_id = str(veh.get("id") or path.stem).strip()
    if not canonical_id:
        return None
    addrs_raw = network.get("ve_addresses") or []
    addrs = [str(a).strip() for a in addrs_raw if isinstance(a, str) and a.strip()]
    # Default SSH host: first ve_address. The vehicle YAML's
    # vehicle.network.ip_address is sometimes set too — use it as a
    # fallback when ve_addresses is empty.
    host = ""
    if addrs:
        host = addrs[0]
    else:
        veh_net = veh.get("network") or {}
        if isinstance(veh_net, dict):
            host = str(veh_net.get("ip_address") or "").strip()

    name = _read_leading_comment(path) or str(veh.get("description") or canonical_id)
    return Vehicle(
        name=name,
        id=canonical_id,
        host=host,
        description=str(veh.get("description") or "").strip(),
        license_plate=str(veh.get("license_plate") or "").strip(),
        location=_location_for(canonical_id),
        system_category=str(veh.get("system_category") or "").strip(),
        ve_addresses=addrs,
        yaml_path=str(path),
    )


def _user_config_dir() -> Path:
    base = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(base) / ".tsdiag"


def _overrides_path() -> Path:
    return _user_config_dir() / "vehicles_overrides.json"


def _load_overrides() -> dict[str, dict]:
    p = _overrides_path()
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        log.exception("vehicles: cannot parse overrides %s", p)
        return {}
    return data if isinstance(data, dict) else {}


def _apply_overrides(vehicles: list[Vehicle]) -> list[Vehicle]:
    overrides = _load_overrides()
    if not overrides:
        return vehicles
    for v in vehicles:
        if v.id in overrides:
            ov = overrides[v.id]
            for fname in ("name", "host", "user", "location"):
                if fname in ov and ov[fname]:
                    setattr(v, fname, str(ov[fname]))
            if "port" in ov:
                try:
                    v.port = int(ov["port"])
                except (TypeError, ValueError):
                    pass
    return vehicles


def open_overrides_in_editor() -> Path:
    """Open (or seed then open) vehicles_overrides.json."""
    p = _overrides_path()
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {
                    "_help": (
                        "Per-vehicle overrides. Key = vehicle id. Each value can "
                        "override any of: name, host, user, port, location."
                    ),
                    "ve-de-00008": {"host": "192.168.140.11"},
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


def load() -> tuple[list[Vehicle], Path | None]:
    """Return (vehicles sorted Germany→USA→others by id, source dir or None)."""
    if not VEHICLES_DIR.is_dir():
        log.warning("vehicles: directory missing: %s", VEHICLES_DIR)
        return [], None
    out: list[Vehicle] = []
    for path in sorted(VEHICLES_DIR.glob("*.yaml")):
        v = _parse_yaml(path)
        if v is not None:
            out.append(v)
    out = _apply_overrides(out)
    location_order = {"Germany": 0, "USA": 1, "Lab": 2}
    out.sort(key=lambda v: (location_order.get(v.location, 99), v.id))
    log.info("vehicles: loaded %d entries from %s", len(out), VEHICLES_DIR)
    return out, VEHICLES_DIR
