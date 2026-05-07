"""Inventory loader (T037 / FR-001b / FR-013, FR-013a / Clarification 2026-05-07).

Reads the **combined** `org/vay/inventory.yaml` file from the
operator's local `ree-vehicle-configs` clone — the file
`ree-debug-tui` has always read. Replaces 001's
`org/*/{vehicles,telestations}/*.yaml` walker.

Inventory shape (Ansible-style):

```yaml
all:
  children:
    telestations:
      hosts:
        ts-de-ber-zeus:
          ansible_host: 192.168.60.2
        ts-de-ber-00005:
          ansible_host: ...
    vehicles:
      hosts:
        ve-de-apollo:
          ansible_host: 10.0.1.5
```

Each nested host name doubles as the `Host.id`. Country / type / city
are derived from the host id regex per 001's rules; non-DE rows are
dropped at load time.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

import yaml

from vayobd.logging import get_logger
from vayobd.models import Country, Host, HostType, Inventory, InventoryMeta

log = get_logger(__name__)

_INVENTORY_REL_PATH = Path("org") / "vay" / "inventory.yaml"

_HOST_ID_RE = re.compile(r"^(ve|ts)-(de)(?:-([a-z0-9]+))?(?:-([a-z0-9-]+))?$")
_GROUP_TO_TYPE: dict[str, HostType] = {
    "telestations": HostType.TELESTATION,
    "vehicles": HostType.VEHICLE,
}
_IN_SCOPE_COUNTRIES: dict[str, Country] = {"de": Country.DE}


def _resolve_inventory_yaml(inventory_path: Path) -> Path:
    """Treat `inventory_path` as the operator's clone root (per the spec
    + the CLI binary's `--inventory` semantics) and append the canonical
    relative path. If `inventory_path` is itself the YAML file (legacy
    callers / tests), return it as-is.
    """
    if inventory_path.is_file() and inventory_path.suffix in (".yaml", ".yml"):
        return inventory_path
    return inventory_path / _INVENTORY_REL_PATH


def _parse_host_id(host_id: str) -> tuple[HostType, Country, str | None] | None:
    """Return (type, country, city_or_None) or None when out-of-scope.

    Vehicles: `ve-de-<rest>` — no city.
    Telestations: `ts-de-<city>-<rest>` — third segment is the city code.
    Anything else (non-DE country, malformed) is filtered out.
    """
    m = _HOST_ID_RE.match(host_id)
    if not m:
        return None
    prefix, country_code, third, _rest = m.groups()
    country = _IN_SCOPE_COUNTRIES.get(country_code)
    if country is None:
        return None
    host_type = HostType.VEHICLE if prefix == "ve" else HostType.TELESTATION
    if host_type is HostType.VEHICLE:
        return host_type, country, None
    # telestation requires a city segment
    if not third:
        return None
    return host_type, country, third


def load_hosts(inventory_path: Path) -> list[Host]:
    """Walk the Ansible-style inventory file and return every in-scope Host."""
    yaml_path = _resolve_inventory_yaml(inventory_path)
    if not yaml_path.is_file():
        log.warning("inventory_yaml_missing", path=str(yaml_path))
        return []

    try:
        with yaml_path.open("r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as exc:
        log.warning("inventory_yaml_unparseable", path=str(yaml_path), error=str(exc))
        return []

    if not isinstance(doc, dict):
        return []
    children = (doc.get("all") or {}).get("children") or {}
    if not isinstance(children, dict):
        return []

    hosts: list[Host] = []
    source_repr = str(yaml_path.relative_to(inventory_path)) if yaml_path != inventory_path else str(yaml_path)
    for group_name, group in children.items():
        host_type_from_group = _GROUP_TO_TYPE.get(str(group_name))
        if host_type_from_group is None:
            continue
        if not isinstance(group, dict):
            continue
        host_block = group.get("hosts") or {}
        if not isinstance(host_block, dict):
            continue

        for raw_id, info in host_block.items():
            host_id = str(raw_id)
            parsed = _parse_host_id(host_id)
            if parsed is None:
                continue
            host_type, country, city = parsed
            # Cross-check the group declaration matches the id-derived type.
            # If they disagree (e.g., a `ve-…` host nested under telestations),
            # trust the id and drop the row — Ansible inventories are not
            # immune to typos.
            if host_type != host_type_from_group:
                log.warning(
                    "inventory_host_group_mismatch",
                    host_id=host_id,
                    group=group_name,
                    derived_type=host_type.value,
                )
                continue
            address: str | None = None
            if isinstance(info, dict):
                ah = info.get("ansible_host")
                if isinstance(ah, str) and ah.strip():
                    address = ah.strip()
            display_name = host_id.split("-", 2)[-1] if host_type is HostType.VEHICLE else host_id.split("-")[-1]
            hosts.append(
                Host(
                    id=host_id,
                    display_name=display_name,
                    host_class=host_type.value,
                    type=host_type,
                    country=country,
                    city=city,
                    address=address,
                    source_file=source_repr,
                )
            )
    hosts.sort(key=lambda h: (h.type.value, h.id))
    return hosts


def load_inventory(inventory_path: Path, _meta_path: Path | None = None) -> Inventory | None:
    """Compose the full Inventory payload, or None if the local copy is missing.

    Returns None when:
    - inventory_path doesn't exist on disk, OR
    - the resolved YAML file contains zero in-scope hosts.

    The caller (`api/inventory.py`) translates None into HTTP 503
    (`inventory_unavailable`).
    """
    if not inventory_path.exists():
        log.warning("inventory_path_missing", path=str(inventory_path))
        return None
    hosts = load_hosts(inventory_path)
    if not hosts:
        log.warning("inventory_empty", path=str(inventory_path))
        return None
    # 002 / FR-013a — no caching layer; freshness IS "now" by definition.
    meta = InventoryMeta(
        last_read_at=datetime.now(UTC),
        source_path=str(inventory_path),
        host_count=len(hosts),
    )
    return Inventory(meta=meta, hosts=hosts)
