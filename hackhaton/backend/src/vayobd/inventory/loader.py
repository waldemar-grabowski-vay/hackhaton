"""Inventory loader (T014, FR-001b).

Walks `org/*/{vehicles,telestations}/*.yaml` under the configured local
checkout, derives country/type/city deterministically from the filename, and
filters to v1's in-scope set (DE + US). Belgium-region hosts are dropped.

The YAML body is parsed best-effort to discover an `address` (not always
present). Address is server-internal and never reaches the SPA.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import yaml

from vayobd.logging import get_logger
from vayobd.models import Country, Host, HostType, Inventory, InventoryMeta

log = get_logger(__name__)

_FILENAME_RE = re.compile(r"^(ve|ts)-([a-z]{2})(?:-([a-z0-9]+))?(.*?)\.yaml$")
# v1 is restricted to the Germany fleet. Any other country segment is
# filtered out at load time.
_IN_SCOPE_COUNTRIES = {"de": Country.DE}

# Telestations are scoped to Berlin only. Any other city segment is dropped
# at load time.
_IN_SCOPE_TELESTATION_CITIES = frozenset({"ber"})


def _parse_filename(stem_yaml: str) -> tuple[HostType, str, str | None, str] | None:
    """Return (type, country_code, city_or_none, display_name_segment) or None."""
    m = _FILENAME_RE.match(stem_yaml)
    if not m:
        return None
    prefix, country_code, third_segment, rest = m.groups()
    host_type = HostType.VEHICLE if prefix == "ve" else HostType.TELESTATION

    # Vehicles: filename is ve-<country>-<rest>.yaml — third segment doesn't exist
    # in our regex form (it's matched into the rest). Telestations: third segment
    # is the city code (ber, las, lnc, nuq, ...).
    if host_type is HostType.VEHICLE:
        # "ve-de-apollo" → display = "apollo".
        # third_segment captured the first segment of the suffix; restore it.
        display = (third_segment or "") + rest
        display = display.lstrip("-")
        return host_type, country_code, None, display

    # Telestation: ts-<country>-<city>-<rest>
    city = third_segment
    if city is None:
        return None  # malformed telestation filename
    display = rest.lstrip("-")
    return host_type, country_code, city, display


def _try_extract_address(yaml_path: Path) -> str | None:
    try:
        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as exc:
        log.warning("yaml_parse_failed", path=str(yaml_path), error=str(exc))
        return None
    network = data.get("network") if isinstance(data, dict) else None
    if isinstance(network, dict):
        addresses = network.get("ve_addresses")
        if isinstance(addresses, list) and addresses:
            first = addresses[0]
            if isinstance(first, str):
                return first
    return None


def load_hosts(inventory_path: Path) -> list[Host]:
    """Walk the checkout and return every in-scope Host."""
    hosts: list[Host] = []
    org_root = inventory_path / "org"
    if not org_root.exists():
        log.warning("inventory_org_missing", path=str(org_root))
        return hosts

    for org_dir in sorted(org_root.iterdir()):
        if not org_dir.is_dir():
            continue
        for sub in ("vehicles", "telestations"):
            sub_dir = org_dir / sub
            if not sub_dir.is_dir():
                continue
            for yaml_path in sorted(sub_dir.glob("*.yaml")):
                parsed = _parse_filename(yaml_path.name)
                if parsed is None:
                    log.warning("filename_unrecognised", path=str(yaml_path))
                    continue
                host_type, country_code, city, display_segment = parsed
                country_enum = _IN_SCOPE_COUNTRIES.get(country_code)
                if country_enum is None:
                    # FR-001b: drop ve-be-* / ts-be-* etc.
                    continue

                # Telestation city allow-list — Berlin + Las Vegas only.
                if host_type is HostType.TELESTATION and city not in _IN_SCOPE_TELESTATION_CITIES:
                    continue

                host_id = yaml_path.stem
                display = display_segment or host_id
                address = _try_extract_address(yaml_path)
                source_file = str(yaml_path.relative_to(inventory_path))
                hosts.append(
                    Host(
                        id=host_id,
                        display_name=display,
                        host_class=host_type.value,
                        type=host_type,
                        country=country_enum,
                        city=city,
                        address=address,
                        source_file=source_file,
                    )
                )
    return hosts


def load_inventory(inventory_path: Path, meta_path: Path) -> Inventory | None:
    """Compose the full Inventory payload, or None if the local copy is missing.

    Returns None when:
    - inventory_path doesn't exist on disk, OR
    - the org/ subtree contains zero in-scope hosts.

    The caller (api/inventory.py) translates None into HTTP 503 (FR-019).
    """
    if not inventory_path.exists():
        log.warning("inventory_path_missing", path=str(inventory_path))
        return None
    hosts = load_hosts(inventory_path)
    if not hosts:
        log.warning("inventory_empty", path=str(inventory_path))
        return None
    meta = _load_or_synthesise_meta(meta_path, host_count=len(hosts))
    return Inventory(meta=meta, hosts=hosts)


def _load_or_synthesise_meta(meta_path: Path, *, host_count: int) -> InventoryMeta:
    if meta_path.exists():
        try:
            with meta_path.open("r", encoding="utf-8") as f:
                raw = json.load(f)
            return InventoryMeta(
                last_refreshed_at=datetime.fromisoformat(raw["last_refreshed_at"]),
                source_revision=raw.get("source_revision", "unknown"),
                host_count=host_count,
            )
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            log.warning("meta_parse_failed", path=str(meta_path), error=str(exc))

    # Synthesise — first ever boot, no prior meta written yet.
    return InventoryMeta(
        last_refreshed_at=datetime.now(UTC),
        source_revision="unknown",
        host_count=host_count,
    )
