"""FastAPI dependency providers that need a singleton lifetime.

Currently just the `Executor`. Phase 2 (T012): `SshExecutor` retired,
only `FixtureExecutor` is wired. Phase 3 (T036) adds the
`ReeCliExecutor` branch (`VAYOBD_EXECUTOR=ree`) — the production
default that shells out to `engine/target/release/ree-debug-cli`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from vayobd.checks.executor import Executor, FixtureExecutor
from vayobd.config import ExecutorMode, Settings, get_settings


def _default_fixtures_dir() -> Path:
    # backend/src/vayobd/dependencies.py → backend/tests/fixtures/runs
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "runs"


@lru_cache(maxsize=1)
def _build_executor(*, mode: ExecutorMode, fixtures_dir: Path) -> Executor:
    if mode is ExecutorMode.FIXTURE:
        return FixtureExecutor(fixtures_dir=fixtures_dir)
    raise RuntimeError(
        f"Executor mode {mode!r} is not yet wired in Phase 2. "
        f"`VAYOBD_EXECUTOR=ree` lands in Phase 3 (US1 task T036)."
    )


def get_executor(settings: Settings = Depends(get_settings)) -> Executor:
    fixtures_dir = settings.fixtures_dir or _default_fixtures_dir()
    return _build_executor(mode=settings.executor, fixtures_dir=fixtures_dir)
