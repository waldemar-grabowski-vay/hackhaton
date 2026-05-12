"""Unit tests — per-process version cache (007 FR-017).

TTL boundary, manual invalidate, thread-safety under concurrent get.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from vayobd._internal.version_cache import VersionCache


def _now() -> datetime:
    return datetime(2026, 5, 11, 14, 0, 0, tzinfo=UTC)


def test_set_then_get_returns_response() -> None:
    cache: VersionCache[str] = VersionCache(ttl_seconds=60)
    cache.set("ts-de-ber-00001", "value-a", now=_now())
    assert cache.get("ts-de-ber-00001", now=_now()) == "value-a"


def test_get_miss_returns_none() -> None:
    cache: VersionCache[str] = VersionCache(ttl_seconds=60)
    assert cache.get("never-set", now=_now()) is None


def test_ttl_expiry_returns_none_after_window() -> None:
    cache: VersionCache[str] = VersionCache(ttl_seconds=60)
    set_at = _now()
    cache.set("ts-de-ber-00001", "value-a", now=set_at)
    # 30 s later — still fresh.
    assert cache.get("ts-de-ber-00001", now=set_at + timedelta(seconds=30)) == "value-a"
    # 60 s later — expired.
    assert cache.get("ts-de-ber-00001", now=set_at + timedelta(seconds=60)) is None
    # 61 s later — still expired.
    assert cache.get("ts-de-ber-00001", now=set_at + timedelta(seconds=61)) is None


def test_invalidate_drops_one_host_only() -> None:
    cache: VersionCache[str] = VersionCache(ttl_seconds=60)
    now = _now()
    cache.set("host-a", "v-a", now=now)
    cache.set("host-b", "v-b", now=now)
    cache.invalidate("host-a")
    assert cache.get("host-a", now=now) is None
    assert cache.get("host-b", now=now) == "v-b"


def test_set_overwrites_existing_entry() -> None:
    cache: VersionCache[str] = VersionCache(ttl_seconds=60)
    now = _now()
    cache.set("host-a", "v-1", now=now)
    cache.set("host-a", "v-2", now=now + timedelta(seconds=5))
    assert cache.get("host-a", now=now + timedelta(seconds=10)) == "v-2"


def test_clear_drops_everything() -> None:
    cache: VersionCache[str] = VersionCache(ttl_seconds=60)
    cache.set("a", "x")
    cache.set("b", "y")
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_init_rejects_non_positive_ttl() -> None:
    with pytest.raises(ValueError):
        VersionCache(ttl_seconds=0)
    with pytest.raises(ValueError):
        VersionCache(ttl_seconds=-1)


def test_concurrent_get_set_does_not_corrupt_state() -> None:
    """Lock is held around every mutation — concurrent ops must converge."""
    cache: VersionCache[str] = VersionCache(ttl_seconds=60)
    barrier = threading.Barrier(8)
    results: list[str | None] = []

    def worker(host_id: str, value: str) -> None:
        barrier.wait()
        for _ in range(50):
            cache.set(host_id, value)
            results.append(cache.get(host_id))

    threads = [
        threading.Thread(target=worker, args=(f"host-{i % 4}", f"v-{i}"))
        for i in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # All results should be non-None (something was just written by some thread).
    # Whether it's THIS thread's write or another's depends on interleaving;
    # the assertion is that we never see corrupted state (a non-None getter
    # returns a written value, not garbage).
    assert all(r is not None and r.startswith("v-") for r in results)
