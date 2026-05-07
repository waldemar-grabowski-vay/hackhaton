"""Application settings — env-driven (R2, R4, plan.md)."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutorMode(StrEnum):
    FIXTURE = "fixture"
    SSH = "ssh"


def _default_inventory_path() -> Path:
    return Path.home() / ".cache" / "vayobd" / "ree-vehicle-configs"


def _default_runs_dir() -> Path:
    return Path.home() / ".cache" / "vayobd" / "runs"


def _default_meta_path() -> Path:
    return Path.home() / ".cache" / "vayobd" / "inventory.meta.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VAYOBD_", env_file=".env", extra="ignore")

    # Inventory
    inventory_path: Path = Field(default_factory=_default_inventory_path)
    inventory_branch: str = "main"
    inventory_meta_path: Path = Field(default_factory=_default_meta_path)
    refresh_interval_seconds: int = 30 * 60

    # Run cache
    runs_dir: Path = Field(default_factory=_default_runs_dir)

    # Executor
    executor: ExecutorMode = ExecutorMode.FIXTURE
    ssh_key: Path | None = None
    ssh_known_hosts: Path | None = None
    fixtures_dir: Path | None = None  # Defaults under backend/tests/fixtures/runs

    # API
    run_timeout_seconds: float = 30.0  # FR-025 — hard ceiling per Clarification 2026-05-07
    static_dir: Path | None = None  # Production-built SPA mounted here when set

    # Inventory refresh failure surfacing (FR-027)
    refresh_failure_warning_threshold: int = 3
    refresh_backoff_base_seconds: float = 30.0
    refresh_backoff_multiplier: float = 2.0
    refresh_backoff_ceiling_seconds: float = 5 * 60.0


def get_settings() -> Settings:
    """One source of truth. Use as a FastAPI dependency."""
    return Settings()
