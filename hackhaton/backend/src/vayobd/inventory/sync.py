"""Inventory sync (T015, R2, FR-027).

`git fetch && git reset --hard origin/<branch>` shelled via subprocess.
Refresh failure preserves the previously cached copy on disk; the meta
file gains `last_refresh_attempted_at` + `consecutive_failed_refreshes`
so the SPA can render the FR-027 banner once the failure count crosses
the configured threshold.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from vayobd.logging import get_logger

log = get_logger(__name__)

GIT_TIMEOUT_SECONDS = 60


class InventorySyncError(RuntimeError):
    """Raised when the local checkout cannot be refreshed."""


@dataclass(frozen=True)
class SyncResult:
    last_refreshed_at: datetime
    last_refresh_attempted_at: datetime
    consecutive_failed_refreshes: int  # Always 0 on success.
    source_revision: str
    host_count: int  # Caller fills this after re-loading.


@dataclass(frozen=True)
class FailureRecord:
    """Returned in lieu of SyncResult when a refresh attempt fails but the
    local cache is preserved. Used by the scheduler to update on-disk
    meta tracking and to drive the exp-backoff schedule.
    """

    last_refresh_attempted_at: datetime
    consecutive_failed_refreshes: int
    error: str


async def _run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        "git",
        *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=GIT_TIMEOUT_SECONDS)
    except TimeoutError as exc:
        proc.kill()
        await proc.wait()
        raise InventorySyncError(f"git {args[0]} timed out") from exc
    return (
        proc.returncode if proc.returncode is not None else -1,
        stdout.decode("utf-8", errors="replace"),
        stderr.decode("utf-8", errors="replace"),
    )


async def sync_inventory(*, inventory_path: Path, branch: str, meta_path: Path) -> SyncResult:
    """Refresh the local checkout. Raises InventorySyncError on failure.

    The previously cached copy is left untouched on failure (the helper bails
    before mutating the working tree if `git fetch` fails). On success the
    failure counter is reset to zero on disk via `_write_meta_success`.
    """
    if not inventory_path.exists():
        raise InventorySyncError(
            f"inventory checkout missing at {inventory_path}; clone it first or set "
            f"VAYOBD_INVENTORY_PATH to an existing checkout"
        )
    if not (inventory_path / ".git").exists():
        raise InventorySyncError(f"{inventory_path} is not a git checkout")

    fetch_rc, _, fetch_err = await _run_git(["fetch", "origin", branch], inventory_path)
    if fetch_rc != 0:
        raise InventorySyncError(f"git fetch failed: {fetch_err.strip()}")

    reset_rc, _, reset_err = await _run_git(
        ["reset", "--hard", f"origin/{branch}"], inventory_path
    )
    if reset_rc != 0:
        raise InventorySyncError(f"git reset failed: {reset_err.strip()}")

    rev_rc, rev_out, _ = await _run_git(["rev-parse", "--short", "HEAD"], inventory_path)
    revision = rev_out.strip() if rev_rc == 0 else "unknown"

    now = datetime.now(UTC)
    _write_meta_success(meta_path, last_refreshed_at=now, source_revision=revision)

    log.info(
        "inventory_synced",
        path=str(inventory_path),
        branch=branch,
        revision=revision,
    )
    return SyncResult(
        last_refreshed_at=now,
        last_refresh_attempted_at=now,
        consecutive_failed_refreshes=0,
        source_revision=revision,
        host_count=0,  # Loader re-enumerates and updates this; carried for API meta.
    )


# --- Meta file I/O -----------------------------------------------------------


def _read_meta(meta_path: Path) -> dict[str, object]:
    if not meta_path.exists():
        return {}
    try:
        with meta_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("meta_read_failed", path=str(meta_path), error=str(exc))
        return {}
    return data if isinstance(data, dict) else {}


def _write_meta(meta_path: Path, payload: dict[str, object]) -> None:
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = meta_path.with_suffix(meta_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, default=str)
    tmp.replace(meta_path)


def _write_meta_success(
    meta_path: Path,
    *,
    last_refreshed_at: datetime,
    source_revision: str,
) -> None:
    """Write meta after a successful refresh — counter resets to 0."""
    payload = {
        "last_refreshed_at": last_refreshed_at.isoformat(),
        "last_refresh_attempted_at": last_refreshed_at.isoformat(),
        "source_revision": source_revision,
        "consecutive_failed_refreshes": 0,
    }
    _write_meta(meta_path, payload)


def record_failure(meta_path: Path, *, attempted_at: datetime) -> FailureRecord:
    """Increment the failure counter and update the attempted-at timestamp.

    Preserves `last_refreshed_at` and `source_revision` from any prior
    successful refresh, since the cache itself is untouched (FR-027).
    """
    existing = _read_meta(meta_path)
    prior_count_raw = existing.get("consecutive_failed_refreshes", 0)
    try:
        prior_count = int(prior_count_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        prior_count = 0
    new_count = prior_count + 1
    payload: dict[str, object] = {
        "last_refreshed_at": existing.get("last_refreshed_at"),
        "last_refresh_attempted_at": attempted_at.isoformat(),
        "source_revision": existing.get("source_revision", "unknown"),
        "consecutive_failed_refreshes": new_count,
    }
    if payload["last_refreshed_at"] is None:
        # First-ever attempt failed before any successful refresh; surface
        # the attempted-at as the freshness timestamp so the SPA isn't
        # rendering an empty cell.
        payload["last_refreshed_at"] = attempted_at.isoformat()
    _write_meta(meta_path, payload)
    return FailureRecord(
        last_refresh_attempted_at=attempted_at,
        consecutive_failed_refreshes=new_count,
        error="inventory_refresh_failed",
    )
