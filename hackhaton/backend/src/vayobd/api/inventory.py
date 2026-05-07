"""Inventory API (T024 / T025 / T078, FR-027).

`GET /api/inventory` reads the on-disk cache. `POST /api/inventory/refresh`
forces a sync — and on failure embeds the current `meta` block in the
problem+JSON body so the SPA can update its FR-027 banner state without
a follow-up round-trip.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from vayobd.api.errors import ApiError
from vayobd.config import Settings, get_settings
from vayobd.inventory.loader import load_inventory
from vayobd.inventory.sync import (
    InventorySyncError,
    record_failure,
    sync_inventory,
)
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


@router.post("/refresh")
async def refresh_inventory(
    settings: Settings = Depends(get_settings),
):
    try:
        result = await sync_inventory(
            inventory_path=settings.inventory_path,
            branch=settings.inventory_branch,
            meta_path=settings.inventory_meta_path,
        )
    except InventorySyncError as exc:
        log.warning("inventory_refresh_failed", error=str(exc))
        # Update the on-disk failure counter so the periodic scheduler and
        # the SPA see consistent state, then surface the failure-meta block.
        record_failure(settings.inventory_meta_path, attempted_at=datetime.now(UTC))
        inv_after = load_inventory(settings.inventory_path, settings.inventory_meta_path)
        meta_payload = (
            inv_after.meta.model_dump(mode="json")
            if inv_after is not None
            else None
        )
        body = {
            "error": "inventory_refresh_failed",
            "message_key": "inventory.refresh_failed.body",
        }
        if meta_payload is not None:
            body["meta"] = meta_payload
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=body,
            media_type="application/problem+json",
        )

    inv = load_inventory(settings.inventory_path, settings.inventory_meta_path)
    host_count = inv.meta.host_count if inv else 0
    meta = InventoryMeta(
        last_refreshed_at=result.last_refreshed_at,
        last_refresh_attempted_at=result.last_refresh_attempted_at,
        consecutive_failed_refreshes=result.consecutive_failed_refreshes,
        source_revision=result.source_revision,
        host_count=host_count,
    )
    return {"meta": meta.model_dump(mode="json")}
