"""T036 — inventory loader filters out non-Germany hosts and derives metadata."""

from __future__ import annotations

from pathlib import Path

from vayobd.inventory.loader import load_hosts


def test_loader_returns_germany_fleet_only(synthetic_inventory: Path) -> None:
    hosts = load_hosts(synthetic_inventory)
    ids = {h.id for h in hosts}

    # Non-Germany regions are filtered out at load time
    # (FR-001b + Clarification 2026-05-07: DE-only).
    assert "ve-be-bxl" not in ids
    assert "ts-be-bxl-foo" not in ids
    assert "ve-us-01001" not in ids
    assert "ts-us-las-00001" not in ids
    # 002 / FR-014: any DE city is in scope, not just Berlin.
    # `ts-de-ham-poseidon` (Hamburg) IS expected to load.
    assert ids == {
        "ve-de-apollo",
        "ve-de-loki",
        "ve-de-thor",
        "ve-de-saturn-slow",
        "ts-de-ber-zeus",
        "ts-de-ham-poseidon",
    }


def test_loader_drops_us_hosts_per_de_only_clarification(synthetic_inventory: Path) -> None:
    """T036 (extended) — `ve-us-*` and `ts-us-*` MUST be dropped at load time.

    United States is represented in the SPA only as a disabled "Coming
    soon" tile (FR-001a step 1, Clarification 2026-05-07); no US data
    crosses the API boundary.
    """
    hosts = load_hosts(synthetic_inventory)
    countries = {h.country.value for h in hosts}
    assert countries == {"de"}


def test_loader_admits_all_de_telestation_cities(synthetic_inventory: Path) -> None:
    """002 / FR-014 relaxes 001's Berlin-only ad-hoc restriction.

    Any DE city is in scope; the loader derives the city from the host
    id's third segment (e.g., `ber` from `ts-de-ber-zeus`, `ham` from
    `ts-de-ham-poseidon`). City filtering happens at the wizard step,
    not at load time.
    """
    telestations = [h for h in load_hosts(synthetic_inventory) if h.type.value == "telestation"]
    cities = {h.city for h in telestations}
    # Both Berlin and Hamburg telestations load.
    assert cities == {"ber", "ham"}
    ids = {h.id for h in telestations}
    assert "ts-de-ber-zeus" in ids
    assert "ts-de-ham-poseidon" in ids
    # Non-DE telestations stay filtered.
    assert "ts-be-bxl-foo" not in ids
    assert "ts-us-las-00001" not in ids


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
