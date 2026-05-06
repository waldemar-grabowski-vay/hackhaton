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
    run_timeout_seconds: float = 25.0
    static_dir: Path | None = None  # Production-built SPA mounted here when set


def get_settings() -> Settings:
    """One source of truth. Use as a FastAPI dependency."""
    return Settings()
