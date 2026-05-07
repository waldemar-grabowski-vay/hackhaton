"""Application settings — env-driven.

Phase 2 (T012, T016): SSH executor mode and the periodic-refresh
backoff knobs from 001 are gone. Phase 3 (T036) re-introduces a
`ree` ExecutorMode wired to the in-monorepo `ree-debug-cli` binary.

The operator's persisted inventory path lives in
`~/.config/vayobd/settings.toml` (see `settings_file.py`); this
config module owns process-level env settings only.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutorMode(StrEnum):
    FIXTURE = "fixture"
    REE = "ree"  # production default — shells out to engine/target/release/ree-debug-cli
    HYBRID = "hybrid"  # demo — fixture first, falls through to ree when no fixture exists


def _default_inventory_path() -> Path:
    return Path.home() / ".cache" / "vayobd" / "ree-vehicle-configs"


def _default_runs_dir() -> Path:
    return Path.home() / ".cache" / "vayobd" / "runs"


def _default_meta_path() -> Path:
    return Path.home() / ".cache" / "vayobd" / "inventory.meta.json"


def _default_ree_reecu_path() -> Path:
    return Path.home() / "GitHub" / "ree-reecu"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VAYOBD_", env_file=".env", extra="ignore")

    # Inventory — env-only override; the operator-facing path comes from
    # `~/.config/vayobd/settings.toml` via `settings_file.py` in Phase 2 / 3.
    inventory_path: Path = Field(default_factory=_default_inventory_path)
    inventory_meta_path: Path = Field(default_factory=_default_meta_path)

    # Run cache (per-(operator, host) JSON, FR-026 carry-forward).
    runs_dir: Path = Field(default_factory=_default_runs_dir)

    # Executor selection.
    executor: ExecutorMode = ExecutorMode.FIXTURE
    fixtures_dir: Path | None = None  # Defaults under backend/tests/fixtures/runs
    ree_cli_bin: Path | None = None  # Override; falls back to repo-relative engine/target/release/ree-debug-cli + $PATH

    # API
    run_timeout_seconds: float = 30.0  # FR-008 / 001 FR-025
    static_dir: Path | None = None  # Production-built SPA mounted here when set

    # 004 — Live diagnostic surface (Developer mode only).
    developer_mode: bool = False
    ree_reecu_path: Path = Field(default_factory=_default_ree_reecu_path)
    dbc_path: Path | None = None  # When None, dbc_decoder uses find_dbc() glob fallback under ree_reecu_path


def get_settings() -> Settings:
    """One source of truth. Use as a FastAPI dependency."""
    return Settings()
