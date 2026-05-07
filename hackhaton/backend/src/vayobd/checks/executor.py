"""Executor interface + implementations (T026 / T027 / T028, research R1).

`ItemResult` is the per-item shape the executor returns; the runner joins
that against `CheckSpec` to build a full `DiagnosticItem`.

Two executors:
- `FixtureExecutor` — reads canned YAML from `backend/tests/fixtures/runs/`.
- `SshExecutor` — connects via asyncssh + key auth + known_hosts and runs
  one shell probe per catalog item.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from vayobd.checks.catalog import catalog_for
from vayobd.logging import get_logger
from vayobd.models import Host, ItemStatus, RunOutcome

log = get_logger(__name__)


@dataclass(frozen=True)
class ItemResult:
    id: str
    status: ItemStatus
    raw_detail: str | None = None


@dataclass(frozen=True)
class ExecutorResult:
    """What an executor produces for one host run.

    The runner converts this (plus the static catalog) into a `DiagnosticRun`.
    """

    outcome: RunOutcome
    items: list[ItemResult] = field(default_factory=list)


class Executor(ABC):
    @abstractmethod
    async def run(self, host: Host) -> ExecutorResult:  # pragma: no cover - interface
        ...


# --- Fixture executor -------------------------------------------------------


class FixtureExecutor(Executor):
    """Reads `<fixtures_dir>/<host_id>.yaml` and returns the canned result.

    Fixture YAML shape:

        outcome: complete | partial | unreachable | timeout
        delay_seconds: 1.5  # optional, default 0
        items:
          - id: main_can_bus_reachable
            status: working
            raw_detail: "candump can0: 1 frame in 47ms"
          - ...

    Missing fixture file → unreachable outcome with no items, so a host
    that simply has no fixture demos cleanly as "unreachable".
    """

    def __init__(self, fixtures_dir: Path) -> None:
        self._dir = fixtures_dir

    async def run(self, host: Host) -> ExecutorResult:
        path = self._dir / f"{host.id}.yaml"
        if not path.exists():
            log.warning("fixture_missing", host_id=host.id, path=str(path))
            return ExecutorResult(outcome=RunOutcome.UNREACHABLE, items=[])

        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (OSError, yaml.YAMLError) as exc:
            log.error("fixture_parse_failed", host_id=host.id, error=str(exc))
            return ExecutorResult(outcome=RunOutcome.UNREACHABLE, items=[])

        delay = float(data.get("delay_seconds", 0.0) or 0.0)
        if delay > 0:
            await asyncio.sleep(delay)

        outcome_raw = str(data.get("outcome", "complete"))
        try:
            outcome = RunOutcome(outcome_raw)
        except ValueError:
            log.error("fixture_unknown_outcome", host_id=host.id, outcome=outcome_raw)
            outcome = RunOutcome.UNREACHABLE

        items_raw = data.get("items") or []
        items: list[ItemResult] = []
        if outcome in (RunOutcome.UNREACHABLE, RunOutcome.TIMEOUT):
            # Spec: items is empty for these outcomes regardless of fixture.
            return ExecutorResult(outcome=outcome, items=[])

        valid_ids = {spec.id for spec in catalog_for(host.host_class)}
        seen: set[str] = set()
        for raw in items_raw:
            if not isinstance(raw, dict):
                continue
            iid = raw.get("id")
            status_raw = raw.get("status")
            if not isinstance(iid, str) or iid not in valid_ids or iid in seen:
                continue
            try:
                status = ItemStatus(status_raw)
            except ValueError:
                continue
            raw_detail = raw.get("raw_detail")
            if raw_detail is not None and not isinstance(raw_detail, str):
                raw_detail = str(raw_detail)
            items.append(ItemResult(id=iid, status=status, raw_detail=raw_detail))
            seen.add(iid)

        return ExecutorResult(outcome=outcome, items=items)


# --- SSH executor (live) ----------------------------------------------------


class SshExecutor(Executor):
    """asyncssh-based live executor.

    Hackathon-grade: connects per-run, runs each catalog item's probe
    command, classifies non-zero exit as `error`. Per-check timeout +
    overall connection timeout. The exact probe-command-per-id mapping
    intentionally lives here rather than in the catalog so the catalog
    itself stays declarative.

    For v1 the SSH probe set is illustrative — the demo build runs against
    the FixtureExecutor.
    """

    PROBE_TIMEOUT_SECONDS = 4.0
    CONNECT_TIMEOUT_SECONDS = 5.0

    def __init__(self, *, ssh_key: Path, known_hosts: Path) -> None:
        self._ssh_key = ssh_key
        self._known_hosts = known_hosts

    async def run(self, host: Host) -> ExecutorResult:
        try:
            import asyncssh  # imported lazily so dev installs that omit it still work
        except ImportError:  # pragma: no cover
            log.error("asyncssh_missing")
            return ExecutorResult(outcome=RunOutcome.UNREACHABLE)

        if not host.address:
            log.warning("ssh_no_address", host_id=host.id)
            return ExecutorResult(outcome=RunOutcome.UNREACHABLE)

        probes = _ssh_probes_for(host.host_class)
        items: list[ItemResult] = []
        try:
            async with asyncssh.connect(
                host.address,
                client_keys=[str(self._ssh_key)],
                known_hosts=str(self._known_hosts),
                connect_timeout=self.CONNECT_TIMEOUT_SECONDS,
            ) as conn:
                for spec_id, command in probes.items():
                    try:
                        result = await asyncio.wait_for(
                            conn.run(command, check=False),
                            timeout=self.PROBE_TIMEOUT_SECONDS,
                        )
                        status = (
                            ItemStatus.WORKING if result.exit_status == 0 else ItemStatus.ERROR
                        )
                        raw = (result.stdout or "") + (result.stderr or "")
                        items.append(
                            ItemResult(id=spec_id, status=status, raw_detail=raw.strip() or None)
                        )
                    except TimeoutError:
                        items.append(
                            ItemResult(
                                id=spec_id,
                                status=ItemStatus.ERROR,
                                raw_detail=f"probe timed out after {self.PROBE_TIMEOUT_SECONDS}s",
                            )
                        )
            if host.host_class == "vehicle":
                items.extend(await self._run_peplink_checks(conn, host.id))

        except (OSError, Exception) as exc:
            # Any connection-layer failure → unreachable, items = [].
            log.warning("ssh_connect_failed", host_id=host.id, error=str(exc))
            return ExecutorResult(outcome=RunOutcome.UNREACHABLE, items=[])

        # If we connected but didn't get a result for every catalog item it's
        # `partial`. Otherwise `complete`.
        catalog = catalog_for(host.host_class)
        outcome = (
            RunOutcome.COMPLETE
            if {item.id for item in items} == {spec.id for spec in catalog}
            else RunOutcome.PARTIAL
        )
        return ExecutorResult(outcome=outcome, items=items)


    async def _run_peplink_checks(self, conn, host_id: str) -> list[ItemResult]:
        from vayobd.checks import peplink as peplink_mod

        peplink_timeout = self.PROBE_TIMEOUT_SECONDS * 4
        try:
            cellular_ok, vpn_ok, detail = await asyncio.wait_for(
                peplink_mod.run_checks(conn, host_id, self.PROBE_TIMEOUT_SECONDS * 2),
                timeout=peplink_timeout,
            )
        except TimeoutError:
            detail = f"peplink checks timed out after {peplink_timeout}s"
            cellular_ok = vpn_ok = False
        except Exception as exc:
            detail = f"peplink checks failed: {exc}"
            cellular_ok = vpn_ok = False

        return [
            ItemResult(
                id="peplink_cellular_connected",
                status=ItemStatus.WORKING if cellular_ok else ItemStatus.ERROR,
                raw_detail=detail or None,
            ),
            ItemResult(
                id="peplink_vpn_tunnels_established",
                status=ItemStatus.WORKING if vpn_ok else ItemStatus.ERROR,
                raw_detail=detail or None,
            ),
        ]


_VEHICLE_PROBES: dict[str, str] = {
    "main_can_bus_reachable": "candump -n 1 -T 2000 can0 >/dev/null 2>&1",
    "expected_front_camera_connected": "lsusb | grep -q LI_IMX490",
    "expected_left_camera_connected": "lsusb | grep -q LI_IMX490",
    "expected_right_camera_connected": "lsusb | grep -q LI_IMX490",
    "vehicle_integration_config_valid": "test -s /etc/vay/vehicle.yaml",
    "network_addresses_reachable": "ping -c 1 -W 1 8.8.8.8 >/dev/null",
}

_TELESTATION_PROBES: dict[str, str] = {
    "display_surface_reachable": "nc -z -w 2 localhost 5900",
    "expected_input_devices_connected": "ls /dev/input/event* >/dev/null",
    "telestation_config_valid": "test -s /etc/vay/telestation.yaml",
}


def _ssh_probes_for(host_class: str) -> dict[str, str]:
    if host_class == "vehicle":
        return _VEHICLE_PROBES
    if host_class == "telestation":
        return _TELESTATION_PROBES
    raise KeyError(host_class)
