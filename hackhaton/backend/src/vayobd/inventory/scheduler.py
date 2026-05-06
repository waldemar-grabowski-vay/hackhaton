"""Periodic inventory refresh (T019, FR-016).

Fires once at startup, then on a fixed cadence. Failures are logged and the
loop continues.
"""

from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from vayobd.inventory.sync import InventorySyncError, sync_inventory
from vayobd.logging import get_logger

log = get_logger(__name__)


async def run_periodic_refresh(
    *,
    inventory_path: Path,
    branch: str,
    meta_path: Path,
    interval_seconds: int,
    initial_delay_seconds: float = 0.0,
) -> None:
    """Refresh once immediately, then loop. Cancellation-safe."""
    if initial_delay_seconds > 0:
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.sleep(initial_delay_seconds)

    while True:
        try:
            await sync_inventory(
                inventory_path=inventory_path,
                branch=branch,
                meta_path=meta_path,
            )
        except InventorySyncError as exc:
            log.warning("inventory_refresh_failed", error=str(exc))
        except Exception as exc:
            log.error("inventory_refresh_unexpected", error=type(exc).__name__, message=str(exc))

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            return
