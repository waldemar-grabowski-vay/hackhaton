"""Per-process TTL cache for host-version responses (007 FR-017).

Single-user desktop deployment — one process serving loopback HTTP —
so a `dict[str, CacheEntry]` guarded by a `threading.Lock` is the
smallest viable cache. No Redis, no `lru_cache`, no DI framework.

The cache is owned by `vayobd.api.host_versions` via a module-level
singleton; tests construct their own `VersionCache(ttl_seconds=...)`
to avoid global state.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Generic, TypeVar

T = TypeVar("T")

# 007 / Clarification Q3 — sixty seconds. Operators bouncing between
# hosts feel instant re-visit; a fresh deploy is reflected within at
# most one TTL window without the operator having to do anything.
DEFAULT_TTL_SECONDS = 60


@dataclass(frozen=True, slots=True)
class CacheEntry(Generic[T]):
    cached_at: datetime
    response: T


class VersionCache(Generic[T]):
    """In-memory per-host TTL cache.

    `get` returns `None` when the entry is missing or expired; the
    caller is responsible for re-populating via `set`. `invalidate`
    drops a single host's entry (used by `?fresh=true`).
    """

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._ttl = timedelta(seconds=ttl_seconds)
        self._store: dict[str, CacheEntry[T]] = {}
        self._lock = threading.Lock()

    def get(self, host_id: str, *, now: datetime | None = None) -> T | None:
        ts = now or datetime.now(UTC)
        with self._lock:
            entry = self._store.get(host_id)
            if entry is None:
                return None
            if (ts - entry.cached_at) >= self._ttl:
                # Lazy eviction — keep the implementation tiny.
                self._store.pop(host_id, None)
                return None
            return entry.response

    def set(self, host_id: str, response: T, *, now: datetime | None = None) -> None:
        ts = now or datetime.now(UTC)
        with self._lock:
            self._store[host_id] = CacheEntry(cached_at=ts, response=response)

    def invalidate(self, host_id: str) -> None:
        with self._lock:
            self._store.pop(host_id, None)

    def clear(self) -> None:
        """Tests only — drop every entry."""
        with self._lock:
            self._store.clear()
