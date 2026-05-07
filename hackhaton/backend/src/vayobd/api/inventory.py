"""Inventory API.

`GET /api/inventory` reads `org/vay/inventory.yaml` from the
operator-configured local checkout per request (FR-013a — no
caching). The 001 cache + sync layer (FR-016 — FR-019, FR-027) is
retired along with the per-folder walker; the operator's `git pull`
+ browser tab refresh is the v1 update flow.

The `POST /api/inventory/refresh` route from 001 is retired in this
feature.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from vayobd.api.errors import ApiError
from vayobd.config import Settings, get_settings
from vayobd.inventory.loader import load_inventory
from vayobd.logging import get_logger
from vayobd.models import Inventory

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
