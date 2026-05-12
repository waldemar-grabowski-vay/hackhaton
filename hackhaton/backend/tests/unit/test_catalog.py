"""T037 — catalog wiring: per-class items + stable ids across calls."""

from __future__ import annotations

from vayobd.checks.catalog import catalog_for, known_host_classes


def test_known_host_classes() -> None:
    assert set(known_host_classes()) == {"vehicle", "telestation"}


def test_vehicle_catalog_contains_expected_items() -> None:
    ids = {spec.id for spec in catalog_for("vehicle")}
    assert "main_can_bus_reachable" in ids
    assert "expected_front_camera_connected" in ids
    assert "vehicle_integration_config_valid" in ids
    assert "network_addresses_reachable" in ids
    # No telestation-only items in the vehicle catalog.
    assert "display_surface_reachable" not in ids


def test_telestation_catalog_contains_expected_items() -> None:
    ids = {spec.id for spec in catalog_for("telestation")}
    assert "display_surface_reachable" in ids
    assert "expected_input_devices_connected" in ids
    assert "telestation_config_valid" in ids
    assert "main_can_bus_reachable" in ids


def test_catalog_ids_stable_across_calls() -> None:
    first = [spec.id for spec in catalog_for("vehicle")]
    second = [spec.id for spec in catalog_for("vehicle")]
    assert first == second
