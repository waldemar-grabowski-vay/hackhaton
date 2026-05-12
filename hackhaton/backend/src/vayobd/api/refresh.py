"""Refresh API — POST /api/refresh + GET /api/refresh/status.

Contract: specs/006-deb-package-distribution/contracts/http-api.md (US3 / FR-008).
Background task driven by `vayobd.install.clone.clone_all(..., mode="fetch")`,
the same code path `vayobd refresh` uses. Module-level `asyncio.Lock` guarantees
at most one refresh runs at a time.
"""

from __future__ import annotations

import threading
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from vayobd.api.auth import current_operator
from vayobd.api.errors import ApiError
from vayobd.config import get_settings
from vayobd.install.clone import CloneAllResult, clone_all
from vayobd.install.credentials import probe_credentials
from vayobd.install.manifest import ManifestError, load_manifest
from vayobd.install.state import ManifestState, load_state, save_state_atomic
from vayobd.logging import get_logger

log = get_logger(__name__)

router = APIRouter(tags=["refresh"])

# Module-level singleton — single-user desktop app, at most one refresh in flight.
# Use a threading.Lock + worker thread (not an asyncio task) so the background
# work is decoupled from the request's event loop: under TestClient and under
# uvicorn alike, the refresh continues until completion no matter which event
# loop is currently active.
_refresh_lock = threading.Lock()
_current_refresh: dict[str, Any] | None = None
_last_result: CloneAllResult | None = None


def _state_to_status_payload(state: ManifestState, *, running_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Render `state` into the `/api/refresh/status` response body."""
    now = datetime.now(UTC)
    stalest = state.stalest_age(now)
    body: dict[str, Any] = {
        "state": "running" if running_meta else "idle",
        "stalest_age_seconds": int(stalest.total_seconds()) if stalest else None,
        "repos": [
            {
                "id": repo_id,
                "last_synced_at": rs.last_synced_at.isoformat() if rs.last_synced_at else None,
                "last_outcome": rs.last_outcome,
                "resolved_revision": rs.resolved_revision,
            }
            for repo_id, rs in state.repo.items()
        ],
    }
    if running_meta:
        body.update(running_meta)
    if state.last_refresh_outcome is not None:
        body["last_refresh_outcome"] = state.last_refresh_outcome
        body["last_refresh_at"] = state.last_refresh_at.isoformat() if state.last_refresh_at else None
    return body


def _run_refresh(refresh_id: str) -> None:
    """Background worker (runs in a daemon thread).

    Performs the manifest-driven fetch and writes the resulting state to disk.
    Sync function on purpose — see the threading.Lock comment above.
    """
    global _last_result, _current_refresh
    try:
        settings = get_settings()
        try:
            manifest = load_manifest(settings.manifest_path)
        except ManifestError as exc:
            log.warning("refresh_manifest_error", error=str(exc))
            return

        state = load_state()
        probe = probe_credentials()
        if probe.all_failed:
            # Mark the state as auth-failed without touching any repo.
            state.last_refresh_outcome = "credentials_failed"
            state.last_refresh_at = datetime.now(UTC).replace(microsecond=0)
            save_state_atomic(state)
            return

        result = clone_all(
            manifest, state, mode="fetch", credential_surface=probe.winner
        )
        save_state_atomic(state)
        _last_result = result
    except Exception as exc:  # pragma: no cover — never silently die
        log.exception("refresh_worker_crashed", error=str(exc))
    finally:
        _current_refresh = None


@router.post("/refresh")
def post_refresh(
    _operator: object = Depends(current_operator),
) -> JSONResponse:
    """FR-008 / contracts/http-api.md POST /api/refresh."""
    global _current_refresh
    if _current_refresh is not None or _refresh_lock.locked():
        # Already running — return 409 with the existing refresh's id.
        in_flight = _current_refresh or {}
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "refresh_in_progress",
                "message_key": "refresh.already_running",
                **in_flight,
            },
        )

    # Pre-flight credential probe so we can return 503 synchronously rather
    # than starting a background task that's guaranteed to fail.
    probe = probe_credentials()
    if probe.all_failed:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": "credentials_failed",
                "message_key": "refresh.credentials_failed",
                "tried": [
                    {"surface": s.surface, "outcome": s.detail} for s in probe.surfaces
                ],
                "suggestions": [
                    "Add your SSH key to GitHub and run `ssh-add`",
                    "Run `gh auth login`",
                ],
            },
        )

    refresh_id = f"r-{uuid.uuid4().hex[:24]}"
    started_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    _current_refresh = {"refresh_id": refresh_id, "started_at": started_at}

    def _runner() -> None:
        with _refresh_lock:
            _run_refresh(refresh_id)

    threading.Thread(target=_runner, name=f"vayobd-refresh-{refresh_id}", daemon=True).start()

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"refresh_id": refresh_id, "started_at": started_at},
    )


@router.get("/refresh/status")
def get_refresh_status(
    _operator: object = Depends(current_operator),
) -> dict[str, Any]:
    """FR-010 source-of-truth — the UI polls this for the staleness banner."""
    state = load_state()
    running_meta = None
    if _current_refresh is not None:
        running_meta = {
            **_current_refresh,
            "current_repo": None,  # finer-grained tracking deferred; UI handles None
            "completed": [],
        }
    return _state_to_status_payload(state, running_meta=running_meta)


# Internal helper exported for tests.
def _reset_refresh_state_for_tests() -> None:
    global _current_refresh, _last_result
    _current_refresh = None
    _last_result = None
