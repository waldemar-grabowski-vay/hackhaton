"""Inventory sync (T015, R2).

`git fetch && git reset --hard origin/<branch>` shelled via subprocess.
Refresh failure preserves the previously cached copy on disk.
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
    source_revision: str
    host_count: int  # Caller fills this after re-loading.


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
    before mutating the working tree if `git fetch` fails).
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

    last_refreshed_at = datetime.now(UTC)
    _write_meta(meta_path, last_refreshed_at=last_refreshed_at, source_revision=revision)

    log.info(
        "inventory_synced",
        path=str(inventory_path),
        branch=branch,
        revision=revision,
    )
    return SyncResult(
        last_refreshed_at=last_refreshed_at,
        source_revision=revision,
        host_count=0,  # Loader re-enumerates and updates this; carried for API meta.
    )


def _write_meta(meta_path: Path, *, last_refreshed_at: datetime, source_revision: str) -> None:
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_refreshed_at": last_refreshed_at.isoformat(),
        "source_revision": source_revision,
    }
    tmp = meta_path.with_suffix(meta_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
    tmp.replace(meta_path)
