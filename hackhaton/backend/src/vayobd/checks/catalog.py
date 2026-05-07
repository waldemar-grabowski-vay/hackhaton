"""Diagnostic check catalog (T029, research R3).

A static, code-reviewed map from host class to the ordered list of items
that any run for that host class produces. Item ids are stable so the
"this errored item is now under Working" comparison after a re-run (US2)
is exact.

The catalog lives next to the runner because the parser code that turns a
shell command's output into a DiagnosticItem will live alongside it for
the SshExecutor; the FixtureExecutor reads canned status + raw_detail
from disk and joins them to the catalog by id.
"""

from __future__ import annotations

from dataclasses import dataclass

from vayobd.models import CheckCategory


@dataclass(frozen=True)
class CheckSpec:
    """Static metadata for one item in a host-class catalog.

    The runner combines this with the executor's per-item result
    (`status` + `raw_detail`) to produce a `DiagnosticItem`.
    """

    id: str
    name_key: str
    category: CheckCategory
    description_key_working: str | None = None
    description_key_error: str | None = None
    recommended_action_key: str | None = None  # required when status == error


_VEHICLE_CATALOG: tuple[CheckSpec, ...] = (
    CheckSpec(
        id="main_can_bus_reachable",
        name_key="item.main_can_bus_reachable.name",
        category=CheckCategory.COMMUNICATION,
        description_key_working="item.main_can_bus_reachable.description.working",
        description_key_error="item.main_can_bus_reachable.description.error",
        recommended_action_key="item.main_can_bus_reachable.action",
    ),
    CheckSpec(
        id="expected_front_camera_connected",
        name_key="item.expected_front_camera_connected.name",
        category=CheckCategory.HARDWARE,
        description_key_working="item.front_camera.description.working",
        description_key_error="item.front_camera.description.error",
        recommended_action_key="item.front_camera.action",
    ),
    CheckSpec(
        id="expected_left_camera_connected",
        name_key="item.expected_left_camera_connected.name",
        category=CheckCategory.HARDWARE,
        description_key_working="item.left_camera.description.working",
        description_key_error="item.left_camera.description.error",
        recommended_action_key="item.left_camera.action",
    ),
    CheckSpec(
        id="expected_right_camera_connected",
        name_key="item.expected_right_camera_connected.name",
        category=CheckCategory.HARDWARE,
        description_key_working="item.right_camera.description.working",
        description_key_error="item.right_camera.description.error",
        recommended_action_key="item.right_camera.action",
    ),
    CheckSpec(
        id="vehicle_integration_config_valid",
        name_key="item.vehicle_integration_config_valid.name",
        category=CheckCategory.CONFIGURATION,
        description_key_working="item.vehicle_config.description.working",
        description_key_error="item.vehicle_config.description.error",
        recommended_action_key="item.vehicle_config.action",
    ),
    CheckSpec(
        id="network_addresses_reachable",
        name_key="item.network_addresses_reachable.name",
        category=CheckCategory.COMMUNICATION,
        description_key_working="item.network.description.working",
        description_key_error="item.network.description.error",
        recommended_action_key="item.network.action",
    ),
    CheckSpec(
        id="peplink_cellular_connected",
        name_key="item.peplink_cellular_connected.name",
        category=CheckCategory.COMMUNICATION,
        description_key_working="item.peplink_cellular.description.working",
        description_key_error="item.peplink_cellular.description.error",
        recommended_action_key="item.peplink_cellular.action",
    ),
    CheckSpec(
        id="peplink_vpn_tunnels_established",
        name_key="item.peplink_vpn_tunnels_established.name",
        category=CheckCategory.COMMUNICATION,
        description_key_working="item.peplink_vpn.description.working",
        description_key_error="item.peplink_vpn.description.error",
        recommended_action_key="item.peplink_vpn.action",
    ),
    CheckSpec(
        id="reecu_wake_line_active",
        name_key="item.reecu_wake_line_active.name",
        category=CheckCategory.HARDWARE,
        description_key_working="item.reecu_wake_line.description.working",
        description_key_error="item.reecu_wake_line.description.error",
        recommended_action_key="item.reecu_wake_line.action",
    ),
)

_TELESTATION_CATALOG: tuple[CheckSpec, ...] = (
    CheckSpec(
        id="display_surface_reachable",
        name_key="item.display_surface_reachable.name",
        category=CheckCategory.COMMUNICATION,
        description_key_working="item.display_surface.description.working",
        description_key_error="item.display_surface.description.error",
        recommended_action_key="item.display_surface.action",
    ),
    CheckSpec(
        id="expected_input_devices_connected",
        name_key="item.expected_input_devices_connected.name",
        category=CheckCategory.HARDWARE,
        description_key_working="item.input_devices.description.working",
        description_key_error="item.input_devices.description.error",
        recommended_action_key="item.input_devices.action",
    ),
    CheckSpec(
        id="telestation_config_valid",
        name_key="item.telestation_config_valid.name",
        category=CheckCategory.CONFIGURATION,
        description_key_working="item.telestation_config.description.working",
        description_key_error="item.telestation_config.description.error",
        recommended_action_key="item.telestation_config.action",
    ),
    CheckSpec(
        id="reecu_wake_line_active",
        name_key="item.reecu_wake_line_active.name",
        category=CheckCategory.HARDWARE,
        description_key_working="item.reecu_wake_line.description.working",
        description_key_error="item.reecu_wake_line.description.error",
        recommended_action_key="item.reecu_wake_line.action",
    ),
)


_CATALOG: dict[str, tuple[CheckSpec, ...]] = {
    "vehicle": _VEHICLE_CATALOG,
    "telestation": _TELESTATION_CATALOG,
}


def catalog_for(host_class: str) -> tuple[CheckSpec, ...]:
    """Return the ordered tuple of checks for `host_class`.

    Raises KeyError on unknown classes — caller is expected to have
    validated this against the inventory.
    """
    return _CATALOG[host_class]


def known_host_classes() -> tuple[str, ...]:
    return tuple(_CATALOG.keys())
