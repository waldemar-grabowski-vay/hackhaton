"""Executor interface + implementations.

T012 (Phase 2): `SshExecutor` from 001 is retired. `FixtureExecutor`
stays for dev / CI / demo. Phase 3 (US1 T036) adds `ReeCliExecutor` —
the production-default executor that shells out to `ree-debug-cli`
from the in-monorepo Rust workspace under `engine/`.

`ItemResult` is the per-item shape the executor returns; the runner
joins that against `CheckSpec` to build a full `DiagnosticItem`.
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
    # Human-readable label, set when the executor has a better name than
    # the catalog (e.g., the ree-debug-engine's planned-row name). The
    # runner uses this verbatim in the fallback path (T039 catalog rebuild
    # will replace the fallback with proper i18n keys).
    display_name: str | None = None


@dataclass(frozen=True)
class ExecutorResult:
    """What an executor produces for one host run.

    The runner converts this (plus the static catalog) into a `DiagnosticRun`.
    """

    outcome: RunOutcome
    items: list[ItemResult] = field(default_factory=list)
    offline_reason: str | None = None


class Executor(ABC):
    @abstractmethod
    async def run(self, host: Host) -> ExecutorResult:  # pragma: no cover - interface
        ...


# --- Fixture executor -------------------------------------------------------


class HybridExecutor(Executor):
    """Demo-mode wrapper: try the fixture first; if no fixture exists for
    `host.id`, delegate to the real engine.

    This lets a single backend run both the demo flow (fixture-backed
    hosts like `ve-de-thor` showing the new repair-guide UI) AND the
    live flow (real `ts-de-ber-00005` reachable via SSH) simultaneously.
    """

    def __init__(self, *, fixtures: "FixtureExecutor", live: Executor) -> None:
        self._fixtures = fixtures
        self._live = live

    async def run(self, host: Host) -> ExecutorResult:
        path = self._fixtures._dir / f"{host.id}.yaml"  # noqa: SLF001
        if path.is_file():
            log.info("hybrid_fixture_hit", host_id=host.id)
            return await self._fixtures.run(host)
        log.info("hybrid_fallthrough_to_live", host_id=host.id)
        return await self._live.run(host)


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
            return ExecutorResult(outcome=RunOutcome.UNREACHABLE, items=[], offline_reason="network_unreachable")

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

        offline_reason: str | None = data.get("offline_reason") or None
        if isinstance(offline_reason, str):
            offline_reason = offline_reason.strip() or None

        items_raw = data.get("items") or []
        items: list[ItemResult] = []
        if outcome in (RunOutcome.UNREACHABLE, RunOutcome.TIMEOUT):
            return ExecutorResult(outcome=outcome, items=[], offline_reason=offline_reason)

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
