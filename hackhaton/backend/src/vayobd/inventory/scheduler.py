"""Periodic inventory refresh (T019, FR-016 + FR-027).

Fires once at startup, then loops on a fixed cadence on success. On
failure switches to **exponential backoff** (base × multiplier, capped
at the ceiling) and increments `consecutive_failed_refreshes` until
the next success resets both. Cancellation-safe.
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
from pathlib import Path

from vayobd.inventory.sync import (
    InventorySyncError,
    record_failure,
    sync_inventory,
)
from vayobd.logging import get_logger

log = get_logger(__name__)


def _next_backoff(
    failures: int,
    *,
    base: float,
    multiplier: float,
    ceiling: float,
) -> float:
    """Return the wait time after `failures` consecutive failures.

    `failures=1` → base; `failures=2` → base*multiplier; …; capped at ceiling.
    """
    if failures <= 0:
        return base
    delay = base * (multiplier ** (failures - 1))
    return min(delay, ceiling)


async def run_periodic_refresh(
    *,
    inventory_path: Path,
    branch: str,
    meta_path: Path,
    interval_seconds: int,
    initial_delay_seconds: float = 0.0,
    backoff_base_seconds: float = 30.0,
    backoff_multiplier: float = 2.0,
    backoff_ceiling_seconds: float = 5 * 60.0,
) -> None:
    """Refresh once immediately, then loop. Cancellation-safe.

    On each iteration:
      - If `sync_inventory` raises `InventorySyncError`, the cached copy
        is preserved (sync bails before mutating it). We bump the meta
        file's `consecutive_failed_refreshes` counter via
        `record_failure` so the SPA can decide when to surface the
        FR-027 banner, and switch to exponential backoff for the next
        sleep.
      - On success, the next sleep returns to the configured cadence.
    """
    if initial_delay_seconds > 0:
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.sleep(initial_delay_seconds)

    consecutive_failures = 0

    while True:
        try:
            await sync_inventory(
                inventory_path=inventory_path,
                branch=branch,
                meta_path=meta_path,
            )
            consecutive_failures = 0
            sleep_for = float(interval_seconds)
        except InventorySyncError as exc:
            consecutive_failures += 1
            failure = record_failure(meta_path, attempted_at=datetime.now(UTC))
            sleep_for = _next_backoff(
                consecutive_failures,
                base=backoff_base_seconds,
                multiplier=backoff_multiplier,
                ceiling=backoff_ceiling_seconds,
            )
            log.warning(
                "inventory_refresh_failed",
                error=str(exc),
                consecutive_failures=failure.consecutive_failed_refreshes,
                next_attempt_in_seconds=sleep_for,
            )
        except Exception as exc:
            consecutive_failures += 1
            record_failure(meta_path, attempted_at=datetime.now(UTC))
            sleep_for = _next_backoff(
                consecutive_failures,
                base=backoff_base_seconds,
                multiplier=backoff_multiplier,
                ceiling=backoff_ceiling_seconds,
            )
            log.error(
                "inventory_refresh_unexpected",
                error=type(exc).__name__,
                message=str(exc),
                consecutive_failures=consecutive_failures,
                next_attempt_in_seconds=sleep_for,
            )

        try:
            await asyncio.sleep(sleep_for)
        except asyncio.CancelledError:
            return
