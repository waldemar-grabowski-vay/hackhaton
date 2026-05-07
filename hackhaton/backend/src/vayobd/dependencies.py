"""FastAPI dependency providers that need a singleton lifetime.

The `Executor` is the production-relevant choice. v1 of 002 ships
two:
- `FixtureExecutor` (dev / CI / demo) — canned per-host YAML.
- `ReeCliExecutor` (production default, T034 / FR-001 / FR-003) —
  shells out to `engine/target/release/ree-debug-cli` for real
  diagnostic output against a reachable testbed.

Selection is driven by `VAYOBD_EXECUTOR` (`fixture | ree`).
"""

from __future__ import annotations

import shutil
from functools import lru_cache
from pathlib import Path

from fastapi import Depends

from vayobd.checks.executor import Executor, FixtureExecutor
from vayobd.checks.ree_cli import ReeCliConfig, ReeCliExecutor
from vayobd.config import ExecutorMode, Settings, get_settings


def _default_fixtures_dir() -> Path:
    # backend/src/vayobd/dependencies.py → backend/tests/fixtures/runs
    return Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "runs"


def _default_ree_cli_bin() -> Path | None:
    """FR-003 resolution order:
    1. explicit override (handled by caller),
    2. relative path `engine/target/release/ree-debug-cli` from the repo root,
    3. `$PATH` lookup of `ree-debug-cli`.
    """
    # backend/src/vayobd/dependencies.py → engine/target/release/ree-debug-cli
    repo_root = Path(__file__).resolve().parents[3]
    candidate = repo_root / "engine" / "target" / "release" / "ree-debug-cli"
    if candidate.is_file():
        return candidate
    found = shutil.which("ree-debug-cli")
    if found:
        return Path(found)
    return None


def _resolve_ree_cli_bin(settings: Settings) -> Path | None:
    if settings.ree_cli_bin is not None:
        return settings.ree_cli_bin
    return _default_ree_cli_bin()


@lru_cache(maxsize=1)
def _build_executor(
    *,
    mode: ExecutorMode,
    fixtures_dir: Path,
    inventory_path: Path,
    run_timeout_seconds: float,
    ree_cli_bin: Path | None,
) -> Executor:
    if mode is ExecutorMode.FIXTURE:
        return FixtureExecutor(fixtures_dir=fixtures_dir)
    if mode is ExecutorMode.REE:
        if ree_cli_bin is None:
            raise RuntimeError(
                "VAYOBD_EXECUTOR=ree but no ree-debug-cli binary found. "
                "Run `cargo build --release --workspace` from `engine/`, "
                "or set VAYOBD_REE_CLI_BIN to an explicit path."
            )
        return ReeCliExecutor(
            config=ReeCliConfig(binary=ree_cli_bin, inventory_path=inventory_path),
            run_timeout_seconds=run_timeout_seconds,
        )
    raise RuntimeError(f"unknown executor mode: {mode!r}")


def get_executor(settings: Settings = Depends(get_settings)) -> Executor:
    fixtures_dir = settings.fixtures_dir or _default_fixtures_dir()
    return _build_executor(
        mode=settings.executor,
        fixtures_dir=fixtures_dir,
        inventory_path=settings.inventory_path,
        run_timeout_seconds=settings.run_timeout_seconds,
        ree_cli_bin=_resolve_ree_cli_bin(settings),
    )
