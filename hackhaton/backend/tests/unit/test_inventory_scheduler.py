"""T083 — exponential-backoff scheduler (FR-027 / R2).

The scheduler doubles its sleep on each consecutive refresh failure
(base × multiplier^(failures-1), capped at the ceiling) and resets to
the configured cadence on the next successful refresh. A separate
on-disk counter (`record_failure`) drives the SPA's banner
visibility.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vayobd.inventory import scheduler as scheduler_mod
from vayobd.inventory.scheduler import _next_backoff, run_periodic_refresh
from vayobd.inventory.sync import InventorySyncError, record_failure


# --- Pure backoff function ---------------------------------------------------


def test_backoff_first_failure_returns_base() -> None:
    assert _next_backoff(1, base=30.0, multiplier=2.0, ceiling=300.0) == 30.0


def test_backoff_doubles_each_consecutive_failure() -> None:
    assert _next_backoff(2, base=30.0, multiplier=2.0, ceiling=600.0) == 60.0
    assert _next_backoff(3, base=30.0, multiplier=2.0, ceiling=600.0) == 120.0
    assert _next_backoff(4, base=30.0, multiplier=2.0, ceiling=600.0) == 240.0


def test_backoff_capped_at_ceiling() -> None:
    # 30 * 2^9 = 15360, well above the 5-min ceiling.
    assert _next_backoff(10, base=30.0, multiplier=2.0, ceiling=300.0) == 300.0


def test_backoff_zero_or_negative_returns_base() -> None:
    assert _next_backoff(0, base=30.0, multiplier=2.0, ceiling=300.0) == 30.0
    assert _next_backoff(-3, base=30.0, multiplier=2.0, ceiling=300.0) == 30.0


# --- On-disk failure counter (record_failure) -------------------------------


def test_record_failure_starts_counter_at_one(tmp_path: Path) -> None:
    meta_path = tmp_path / "inventory.meta.json"
    rec = record_failure(meta_path, attempted_at=datetime.now(UTC))
    assert rec.consecutive_failed_refreshes == 1
    raw = json.loads(meta_path.read_text())
    assert raw["consecutive_failed_refreshes"] == 1


def test_record_failure_increments_existing_counter(tmp_path: Path) -> None:
    meta_path = tmp_path / "inventory.meta.json"
    record_failure(meta_path, attempted_at=datetime.now(UTC))
    record_failure(meta_path, attempted_at=datetime.now(UTC))
    rec = record_failure(meta_path, attempted_at=datetime.now(UTC))
    assert rec.consecutive_failed_refreshes == 3


def test_record_failure_preserves_last_refreshed_at(tmp_path: Path) -> None:
    meta_path = tmp_path / "inventory.meta.json"
    success_ts = "2026-05-07T12:00:00+00:00"
    meta_path.write_text(
        json.dumps(
            {
                "last_refreshed_at": success_ts,
                "last_refresh_attempted_at": success_ts,
                "consecutive_failed_refreshes": 0,
                "source_revision": "abc1234",
            }
        )
    )

    record_failure(meta_path, attempted_at=datetime.now(UTC))

    raw = json.loads(meta_path.read_text())
    assert raw["last_refreshed_at"] == success_ts  # untouched
    assert raw["consecutive_failed_refreshes"] == 1
    assert raw["last_refresh_attempted_at"] != success_ts  # updated


# --- Scheduler loop (failure → backoff → success → reset) -------------------


def test_scheduler_resets_counter_and_cadence_after_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two failures then a success: the third sleep MUST be the configured
    cadence, not a backoff value. The on-disk counter resets to 0.
    """
    meta_path = tmp_path / "inventory.meta.json"
    inventory_path = tmp_path / "checkout"
    inventory_path.mkdir()
    (inventory_path / ".git").mkdir()

    # Sequence the sync calls: fail, fail, succeed, then cancel.
    call_count = {"n": 0}

    async def fake_sync(*, inventory_path, branch, meta_path):
        call_count["n"] += 1
        if call_count["n"] <= 2:
            raise InventorySyncError(f"simulated failure {call_count['n']}")
        # Success: write a successful meta file ourselves (the real sync does this).
        meta_path.write_text(
            json.dumps(
                {
                    "last_refreshed_at": datetime.now(UTC).isoformat(),
                    "last_refresh_attempted_at": datetime.now(UTC).isoformat(),
                    "consecutive_failed_refreshes": 0,
                    "source_revision": "succ",
                }
            )
        )
        from vayobd.inventory.sync import SyncResult

        now = datetime.now(UTC)
        return SyncResult(
            last_refreshed_at=now,
            last_refresh_attempted_at=now,
            consecutive_failed_refreshes=0,
            source_revision="succ",
            host_count=0,
        )

    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        # Cancel the loop after the third sleep so the test ends deterministically.
        if len(sleeps) >= 3:
            raise asyncio.CancelledError()

    monkeypatch.setattr(scheduler_mod, "sync_inventory", fake_sync)
    monkeypatch.setattr(scheduler_mod.asyncio, "sleep", fake_sleep)

    asyncio.run(
        run_periodic_refresh(
            inventory_path=inventory_path,
            branch="main",
            meta_path=meta_path,
            interval_seconds=30 * 60,  # 30 min cadence
            backoff_base_seconds=30.0,
            backoff_multiplier=2.0,
            backoff_ceiling_seconds=5 * 60.0,
        )
    )

    # Sleeps: failure 1 → 30 s; failure 2 → 60 s; success → 30 min.
    assert sleeps == [30.0, 60.0, 30 * 60]

    # On-disk counter should be 0 after the success (the success branch
    # writes the meta file with consecutive_failed_refreshes: 0).
    raw = json.loads(meta_path.read_text())
    assert raw["consecutive_failed_refreshes"] == 0
