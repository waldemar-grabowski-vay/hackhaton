"""FastAPI dependency providers that need a singleton lifetime.

Currently just the `Executor` — chosen at startup based on
`settings.executor`. Kept in its own module so test code can override it
with `app.dependency_overrides[get_executor] = ...` cleanly.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from vayobd.checks.executor import Executor, FixtureExecutor, SshExecutor
from vayobd.config import ExecutorMode, Settings, get_settings


def _default_fixtures_dir() -> Path:
    # backend/src/vayobd/dependencies.py → backend/tests/fixtures/runs
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "runs"


@lru_cache(maxsize=1)
def _build_executor(
    *,
    mode: ExecutorMode,
    fixtures_dir: Path,
    ssh_key: Path | None,
    known_hosts: Path | None,
) -> Executor:
    if mode is ExecutorMode.SSH:
        if ssh_key is None or known_hosts is None:
            raise RuntimeError(
                "VAYOBD_EXECUTOR=ssh requires VAYOBD_SSH_KEY and VAYOBD_SSH_KNOWN_HOSTS"
            )
        return SshExecutor(ssh_key=ssh_key, known_hosts=known_hosts)
    return FixtureExecutor(fixtures_dir=fixtures_dir)


def get_executor(settings: Settings = Depends(get_settings)) -> Executor:
    fixtures_dir = settings.fixtures_dir or _default_fixtures_dir()
    return _build_executor(
        mode=settings.executor,
        fixtures_dir=fixtures_dir,
        ssh_key=settings.ssh_key,
        known_hosts=settings.ssh_known_hosts,
    )
