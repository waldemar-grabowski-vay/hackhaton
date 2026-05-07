"""Run orchestrator (T030 / T031 / T032).

- Joins catalog metadata with executor item results to produce DiagnosticItem rows.
- Enforces a per-host_id `asyncio.Lock` so a second concurrent run for the
  same host returns 409 (FR-011).
- Applies a server-side PII scrubber to `raw_detail` before persistence
  (FR-013 / R6).
"""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime

from vayobd.checks.catalog import CheckSpec, catalog_for
from vayobd.checks.executor import Executor, ItemResult
from vayobd.logging import get_logger
from vayobd.models import (
    CheckCategory,
    DiagnosticItem,
    DiagnosticRun,
    Host,
    ItemStatus,
    RunOutcome,
)

log = get_logger(__name__)


class RunInProgressError(RuntimeError):
    """Raised when a run for the same host is already in flight."""


class _LockRegistry:
    """One asyncio.Lock per host_id, lazily created.

    Single asyncio loop = the `if .locked() … async with` pattern is safe
    because no other coroutine runs between the check and the acquire
    request (no awaits in between).
    """

    def __init__(self) -> None:
        self._locks: dict[str, asyncio.Lock] = {}

    def get(self, host_id: str) -> asyncio.Lock:
        lock = self._locks.get(host_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[host_id] = lock
        return lock


_lock_registry = _LockRegistry()


# --- PII scrubber -----------------------------------------------------------

_VIN_RE = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
_MAC_RE = re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b")
_EMAIL_RE = re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b")


def scrub_raw_detail(text: str | None) -> str | None:
    """Mask common PII shapes in raw_detail (FR-013).

    Conservative: VIN-shaped 17-char strings, MAC addresses, email
    addresses. Hostnames and IP addresses are intentionally allowed since
    they're useful debugging signal and aren't operator PII.
    """
    if text is None:
        return None
    out = _VIN_RE.sub("[redacted-vin]", text)
    out = _MAC_RE.sub("[redacted-mac]", out)
    out = _EMAIL_RE.sub("[redacted-email]", out)
    return out


# --- Runner -----------------------------------------------------------------


def _build_item(spec: CheckSpec, result: ItemResult | None) -> DiagnosticItem | None:
    """Combine static spec + executor result into a DiagnosticItem.

    Returns None when there's no result for this spec — the caller treats
    that as a missed item (drives the partial/complete outcome decision).
    """
    if result is None:
        return None
    description_key = (
        spec.description_key_working
        if result.status is ItemStatus.WORKING
        else spec.description_key_error
    )
    # 002 / FR-004b — `warning` items also need a recommended_action_key.
    recommended_action = (
        spec.recommended_action_key
        if result.status in (ItemStatus.ERROR, ItemStatus.WARNING)
        else None
    )
    return DiagnosticItem(
        id=spec.id,
        name_key=spec.name_key,
        description_key=description_key,
        category=spec.category,
        status=result.status,
        recommended_action_key=recommended_action,
        raw_detail=scrub_raw_detail(result.raw_detail),
    )


def _build_item_from_executor_only(result: ItemResult) -> DiagnosticItem:
    """Fallback for engine check ids that don't have a catalog entry yet.

    002 ports ree-debug-engine into the monorepo; the engine produces
    ~37 items per host, but the operator-visible catalog (T039) is a
    follow-up. Until T039 lands, the runner uses this fallback so no
    item is silently dropped — the engine's `display_name` is plumbed
    through as the operator-visible `name_key` (the SPA's `t()` helper
    falls through to the literal value when no strings.ts entry
    matches).
    """
    # Prefer the engine-supplied human label; fall back to a key-shape
    # if absent (which only happens for FixtureExecutor-style results
    # that pre-date the display_name field).
    name_key = result.display_name or f"item.{result.id}.name"
    # Default-bucket placeholder — concrete category lands with the
    # T039 catalog rebuild. Treat unknown checks as Communication for
    # now (the largest engine bucket — better default than e.g. Hardware).
    category = CheckCategory.COMMUNICATION
    description_key = (
        f"item.{result.id}.description.{result.status.value}"
        if not result.display_name
        else None
    )
    recommended_action = (
        f"item.{result.id}.action"
        if result.status in (ItemStatus.ERROR, ItemStatus.WARNING)
        else None
    )
    return DiagnosticItem(
        id=result.id,
        name_key=name_key,
        description_key=description_key,
        category=category,
        status=result.status,
        recommended_action_key=recommended_action,
        raw_detail=scrub_raw_detail(result.raw_detail),
    )


async def execute_run(
    *,
    host: Host,
    executor: Executor,
    timeout_seconds: float,
) -> DiagnosticRun:
    """Acquire the per-host lock, run the executor, build a DiagnosticRun.

    Raises `RunInProgressError` if another run for this host is already
    in flight; the API layer translates this into HTTP 409.
    """
    lock = _lock_registry.get(host.id)
    if lock.locked():
        raise RunInProgressError(host.id)

    started_at = datetime.now(UTC)
    async with lock:
        try:
            executor_result = await asyncio.wait_for(
                executor.run(host), timeout=timeout_seconds
            )
            outcome = executor_result.outcome
            results_by_id = {r.id: r for r in executor_result.items}
        except TimeoutError:
            outcome = RunOutcome.TIMEOUT
            results_by_id = {}

    completed_at = datetime.now(UTC)

    catalog = catalog_for(host.host_class)
    catalog_by_id = {spec.id: spec for spec in catalog}
    items: list[DiagnosticItem] = []
    if outcome not in (RunOutcome.UNREACHABLE, RunOutcome.TIMEOUT):
        seen_ids: set[str] = set()
        # 1) Catalog-known items first, in catalog order. Items the
        #    catalog declares but the executor didn't return are
        #    treated as a partial run.
        catalog_present = 0
        for spec in catalog:
            built = _build_item(spec, results_by_id.get(spec.id))
            if built is not None:
                items.append(built)
                seen_ids.add(built.id)
                catalog_present += 1
        # 2) Engine-emitted items the catalog doesn't know about
        #    (002 / T039 will replace this fallback with proper copy).
        for result in executor_result.items:
            if result.id in seen_ids:
                continue
            items.append(_build_item_from_executor_only(result))
            seen_ids.add(result.id)
        # Reconcile outcome against catalog completeness only.
        if outcome is RunOutcome.COMPLETE and catalog_present != len(catalog):
            outcome = RunOutcome.PARTIAL

    log.info(
        "run_finished",
        host_id=host.id,
        outcome=outcome.value,
        item_count=len(items),
    )

    return DiagnosticRun(
        host_id=host.id,
        started_at=started_at,
        completed_at=completed_at,
        outcome=outcome,
        items=items,
    )
