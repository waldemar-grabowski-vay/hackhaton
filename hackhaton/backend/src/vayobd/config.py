"""Application settings — env-driven, with `~/.config/vayobd/settings.toml`
layered on top for any field not explicitly set via env var.

Phase 2 (T012, T016): SSH executor mode and the periodic-refresh
backoff knobs from 001 are gone. Phase 3 (T036) re-introduces a
`ree` ExecutorMode wired to the in-monorepo `ree-debug-cli` binary.
Phase 7 / T057: the `[live]` block of the settings TOML is now merged
into the runtime Settings at startup. Env vars (VAYOBD_*) still take
precedence over TOML values; TOML beats class defaults.
"""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache
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
    """REECU source tree — first-run clone target (per packaging/manifest.toml)."""
    return Path.home() / ".cache" / "vayobd" / "ree-reecu"


def _default_dbc_search_root() -> Path:
    """The DBC repo — separate from ree-reecu by design (004 clarification).
    First-run clone target (per packaging/manifest.toml)."""
    return Path.home() / ".cache" / "vayobd" / "ree-reecu-dbc"


def _default_release_configs_path() -> Path:
    """Release manifest — `release-configs.yaml` listing the expected
    vDrive / vREECU / SEC versions per host kind. First-run clone target
    (per packaging/manifest.toml). Exported to the engine subprocess via
    `RELEASE_CONFIGS_PATH` env var by `host_versions.py::_invoke_engine`."""
    return Path.home() / ".cache" / "vayobd" / "system-release-deployment" / "release-configs.yaml"


def _default_manifest_path() -> Path:
    """Resolve the required-repos manifest (spec 006 / FR-006).

    Production: the `.deb` installs `manifest.toml` at `/usr/share/vayobd/manifest.toml`.
    Dev / source checkouts: fall back to `<repo>/packaging/manifest.toml` so the
    `run-dev.sh` flow keeps working without the .deb installed.
    """
    shipped = Path("/usr/share/vayobd/manifest.toml")
    if shipped.is_file():
        return shipped
    # Repo-relative fallback: this file lives at <repo>/backend/src/vayobd/config.py
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "packaging" / "manifest.toml"


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
    # 008: DBC lives in `ree-reecu-dbc`, a SEPARATE repo from `ree-reecu`
    # (errq CSVs). Default = `~/.cache/vayobd/ree-reecu-dbc/` — first-run
    # clone target. Overridable via `VAYOBD_DBC_SEARCH_ROOT`.
    dbc_search_root: Path = Field(default_factory=_default_dbc_search_root)
    dbc_path: Path | None = None  # When None, dbc_decoder searches under dbc_search_root

    # 009: Release manifest yaml. Default = `~/.cache/vayobd/system-release-deployment/release-configs.yaml`
    # — first-run clone target. The backend passes this to the rust engine
    # via the `RELEASE_CONFIGS_PATH` env var. Overridable via
    # `VAYOBD_RELEASE_CONFIGS_PATH`.
    release_configs_path: Path = Field(default_factory=_default_release_configs_path)

    # FR-026 — operator-configurable channel inference. Each pattern is
    # tested in turn against the decoded signal name (case-insensitive
    # via the `(?i)` inline flag in the defaults). Signals matching
    # neither pattern are classified as `unknown`.
    channel_a_pattern: str = r"(?i)_CHA_|TS_CHA"
    channel_b_pattern: str = r"(?i)_CHB_|TS_CHB"

    # 006 — Required-repos manifest. The .deb installs the canonical copy at
    # `/usr/share/vayobd/manifest.toml`; dev checkouts use `<repo>/packaging/manifest.toml`.
    # Override with `VAYOBD_MANIFEST_PATH` in tests.
    manifest_path: Path = Field(default_factory=_default_manifest_path)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """One source of truth. Use as a FastAPI dependency.

    Precedence (highest first):
      1. Init args (none in this path)
      2. Env vars (`VAYOBD_*`)
      3. `.env` file
      4. `~/.config/vayobd/settings.toml` `[live]` block (Phase 7 / T057)
      5. Class defaults

    The TOML layer is read once and cached. To pick up a settings.toml
    change, restart the backend (matches FR-024's "reloaded at backend
    startup" contract).
    """
    base = Settings()

    # Layer the persisted TOML settings on top of class defaults, but
    # only for fields the operator has not explicitly overridden via
    # `VAYOBD_*` env vars. This keeps env-var-driven runs (CI, ad-hoc)
    # exactly as they were.
    try:
        # Local import to avoid circular dependency at module load.
        from vayobd.settings_file import load_settings as _load_toml

        persisted = _load_toml()
    except Exception:  # noqa: BLE001 — fail-soft; never let TOML break startup
        return base

    live = persisted.live
    overrides: dict[str, object] = {}

    def _take(env_var: str, field: str, value: object) -> None:
        if value is not None and env_var not in os.environ:
            overrides[field] = value

    _take("VAYOBD_DEVELOPER_MODE", "developer_mode", live.developer_mode or None)
    _take("VAYOBD_REE_REECU_PATH", "ree_reecu_path", live.ree_reecu_path)
    _take("VAYOBD_DBC_PATH", "dbc_path", live.dbc_path)
    _take("VAYOBD_CHANNEL_A_PATTERN", "channel_a_pattern", live.channel_a_pattern)
    _take("VAYOBD_CHANNEL_B_PATTERN", "channel_b_pattern", live.channel_b_pattern)

    if persisted.inventory is not None and "VAYOBD_INVENTORY_PATH" not in os.environ:
        overrides["inventory_path"] = persisted.inventory.path

    if not overrides:
        return base
    return base.model_copy(update=overrides)
