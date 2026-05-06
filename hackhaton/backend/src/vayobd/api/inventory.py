"""Inventory API (T024 / T025).

`GET /api/inventory` reads the on-disk cache. `POST /api/inventory/refresh`
forces a sync.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from vayobd.api.errors import ApiError
from vayobd.config import Settings, get_settings
from vayobd.inventory.loader import load_inventory
from vayobd.inventory.sync import InventorySyncError, sync_inventory
from vayobd.logging import get_logger
from vayobd.models import Inventory, InventoryMeta

log = get_logger(__name__)

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def _strip_internal_fields(inv: Inventory) -> Inventory:
    """Drop server-internal `address` / `source_file` before response (data-model)."""
    public_hosts = [
        host.model_copy(update={"address": None, "source_file": None})
        for host in inv.hosts
    ]
    return Inventory(meta=inv.meta, hosts=public_hosts)


@router.get("", response_model=Inventory)
async def get_inventory(settings: Settings = Depends(get_settings)) -> Inventory:
    inv = load_inventory(settings.inventory_path, settings.inventory_meta_path)
    if inv is None:
        raise ApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error="inventory_unavailable",
            message_key="inventory.empty.body",
        )
    return _strip_internal_fields(inv)


@router.post("/refresh", response_model=dict)
async def refresh_inventory(
    settings: Settings = Depends(get_settings),
) -> dict[str, InventoryMeta]:
    try:
        result = await sync_inventory(
            inventory_path=settings.inventory_path,
            branch=settings.inventory_branch,
            meta_path=settings.inventory_meta_path,
        )
    except InventorySyncError as exc:
        log.warning("inventory_refresh_failed", error=str(exc))
        raise ApiError(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error="inventory_refresh_failed",
            message_key="inventory.refresh_failed.body",
        ) from exc

    inv = load_inventory(settings.inventory_path, settings.inventory_meta_path)
    host_count = inv.meta.host_count if inv else 0
    meta = InventoryMeta(
        last_refreshed_at=result.last_refreshed_at,
        source_revision=result.source_revision,
        host_count=host_count,
    )
    return {"meta": meta}
