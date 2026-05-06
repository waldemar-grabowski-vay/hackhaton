"""T036 — inventory loader filters out non-Germany hosts and derives metadata."""

from __future__ import annotations

from pathlib import Path

from vayobd.inventory.loader import load_hosts


def test_loader_returns_germany_fleet_only(synthetic_inventory: Path) -> None:
    hosts = load_hosts(synthetic_inventory)
    ids = {h.id for h in hosts}

    # Belgium (FR-001b) is filtered out.
    assert "ve-be-bxl" not in ids
    assert "ts-be-bxl-foo" not in ids
    assert ids == {"ve-de-apollo", "ve-de-loki", "ve-de-thor", "ts-de-ber-zeus"}


def test_loader_restricts_telestations_to_berlin(synthetic_inventory: Path) -> None:
    telestations = [h for h in load_hosts(synthetic_inventory) if h.type.value == "telestation"]
    cities = {h.city for h in telestations}
    assert cities == {"ber"}
    ids = {h.id for h in telestations}
    assert "ts-de-ham-poseidon" not in ids


def test_loader_derives_country_type_city(synthetic_inventory: Path) -> None:
    hosts = {h.id: h for h in load_hosts(synthetic_inventory)}

    apollo = hosts["ve-de-apollo"]
    assert apollo.country.value == "de"
    assert apollo.type.value == "vehicle"
    assert apollo.city is None  # vehicles have no city
    assert apollo.host_class == "vehicle"
    assert apollo.address == "10.0.1.5"

    zeus = hosts["ts-de-ber-zeus"]
    assert zeus.country.value == "de"
    assert zeus.type.value == "telestation"
    assert zeus.city == "ber"
    assert zeus.host_class == "telestation"


def test_loader_returns_empty_when_org_missing(tmp_path: Path) -> None:
    assert load_hosts(tmp_path) == []
