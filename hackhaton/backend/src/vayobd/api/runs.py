"""Runs API (T033 / T034).

`POST /api/runs` triggers one synchronous diagnostic; `GET /api/runs/latest`
returns the persisted result.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from vayobd.api.auth import current_operator
from vayobd.api.errors import ApiError
from vayobd.checks.executor import Executor
from vayobd.checks.runner import RunInProgressError, execute_run
from vayobd.config import Settings, get_settings
from vayobd.dependencies import get_executor
from vayobd.inventory.loader import load_inventory
from vayobd.inventory.runs_cache import read_run, write_run
from vayobd.logging import get_logger
from vayobd.models import DiagnosticRun, Host, OperatorIdentity

log = get_logger(__name__)

router = APIRouter(prefix="/api/runs", tags=["runs"])


class RunBody(BaseModel):
    host_id: str = Field(..., min_length=1)


def _find_host(host_id: str, settings: Settings) -> Host | None:
    inv = load_inventory(settings.inventory_path, settings.inventory_meta_path)
    if inv is None:
        return None
    for host in inv.hosts:
        if host.id == host_id:
            return host
    return None


@router.post("", response_model=DiagnosticRun)
async def trigger_run(
    body: RunBody,
    settings: Settings = Depends(get_settings),
    operator: OperatorIdentity = Depends(current_operator),
    executor: Executor = Depends(get_executor),
) -> DiagnosticRun:
    host = _find_host(body.host_id, settings)
    if host is None:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            error="unknown_host",
            message_key="runs.unknown_host.body",
        )

    try:
        run = await execute_run(
            host=host,
            executor=executor,
            timeout_seconds=settings.run_timeout_seconds,
        )
    except RunInProgressError as exc:
        raise ApiError(
            status_code=status.HTTP_409_CONFLICT,
            error="run_in_progress",
            message_key="runs.in_progress.toast",
        ) from exc

    write_run(runs_dir=settings.runs_dir, run=run, triggered_by=operator)
    log.info(
        "run_triggered",
        host_id=host.id,
        outcome=run.outcome.value,
        triggered_by=operator.username,
    )
    return run


@router.get("/latest", response_model=DiagnosticRun)
async def latest_run(
    host_id: str,
    settings: Settings = Depends(get_settings),
) -> DiagnosticRun:
    run = read_run(runs_dir=settings.runs_dir, host_id=host_id)
    if run is None:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            error="no_run_yet",
            message_key="runs.none_yet.body",
        )
    return run
