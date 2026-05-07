"""Pydantic models — the single source of truth for API payloads.

Field names are snake_case at the API boundary (Python convention). The
frontend mirrors these in `frontend/src/api/schemas.ts` via Zod, and
the Rust engine library mirrors the engine-side shapes in
`engine/ree-debug-engine/src/types.rs`. See
`specs/002-real-executor/data-model.md` for the three-layer story.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

HostId = Annotated[
    str,
    StringConstraints(pattern=r"^(ve|ts)-de(-[a-z0-9-]+)+$"),
]


class Country(StrEnum):
    DE = "de"


class HostType(StrEnum):
    VEHICLE = "vehicle"
    TELESTATION = "telestation"


class CheckCategory(StrEnum):
    """The five-bucket palette pinned by the 2026-05-07 clarify session
    on 002 (FR-006). Operator-mode only — engineering identifiers (XCP,
    SAS, vDrive, …) never reach the SPA verbatim per Constitution III.
    """

    COMMUNICATION = "communication"
    HARDWARE = "hardware"
    CONFIGURATION = "configuration"
    SOFTWARE = "software"  # vDrive drift, firmware/gateware, container status
    CALIBRATION = "calibration"  # SAS calibration, GNSS yaw-rate watchdog


class ItemStatus(StrEnum):
    """Three-status enum from 002's FR-004a. Mirrors the engine's
    `Pass | Warn | Fail` (CheckStatus on the Rust side):
    `Pass → working`, `Warn → warning`, `Fail → error`.
    """

    WORKING = "working"
    WARNING = "warning"
    ERROR = "error"


class RunOutcome(StrEnum):
    """Four outcomes per research R5."""

    COMPLETE = "complete"
    PARTIAL = "partial"
    UNREACHABLE = "unreachable"
    TIMEOUT = "timeout"


_HOST_ID_RE = re.compile(r"^(ve|ts)-de(-[a-z0-9-]+)+$")


class Host(BaseModel):
    """Picker-facing host record. `address` and `source_file` are server-internal
    and stripped before returning to the SPA — see Inventory.to_public()."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Filename slug; HostId pattern.")
    display_name: str
    host_class: str = Field(
        ..., description="Equal to type today; kept distinct for future host classes."
    )
    type: HostType
    country: Country
    city: str | None = None
    address: str | None = Field(default=None, description="Server-internal; not returned to SPA.")
    source_file: str | None = Field(default=None, description="Server-internal; repo-relative path.")

    @model_validator(mode="after")
    def _validate(self) -> Host:
        if not _HOST_ID_RE.match(self.id):
            raise ValueError(f"invalid host id: {self.id!r}")
        if self.type is HostType.VEHICLE and self.city is not None:
            raise ValueError("vehicles must not carry a city")
        if self.type is HostType.TELESTATION and self.city is None:
            raise ValueError("telestations must carry a city")
        return self


class InventoryMeta(BaseModel):
    """Slimmed for 002 (T011 / FR-013a) — the cache + periodic-refresh
    layer is retired, so the 001 freshness fields are gone. The
    inventory is re-read from disk per request; `last_read_at` is
    always 'now'.
    """

    last_read_at: datetime
    source_path: str
    host_count: int


class Inventory(BaseModel):
    """The full payload behind GET /api/inventory."""

    meta: InventoryMeta
    hosts: list[Host]


class DiagnosticItem(BaseModel):
    """One thing that was checked. `raw_detail` is always populated server-side
    so toggling Developer mode never requires a refetch (001 FR-022).

    002 / FR-004b: `warning` items must carry a `recommended_action_key`
    too, not only `error` items.
    """

    id: str = Field(..., description="Stable per host class, e.g. 'main_can_bus_reachable'.")
    name_key: str
    description_key: str | None = None
    category: CheckCategory
    status: ItemStatus
    recommended_action_key: str | None = None
    raw_detail: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> DiagnosticItem:
        if (
            self.status in (ItemStatus.ERROR, ItemStatus.WARNING)
            and self.recommended_action_key is None
        ):
            raise ValueError(
                f"errored/warning item {self.id!r} must have recommended_action_key (FR-004b)"
            )
        return self


_SLUG_DISALLOWED_RE = re.compile(r"[^a-z0-9._-]+")


class OperatorIdentity(BaseModel):
    """Pulled from the X-Vay-User reverse-proxy header (R4 + 001 FR-026).

    Load-bearing in v1: `slug` is used as a path segment when persisting
    runs (`runs/<slug>/<host_id>.json`), so it must be sanitised.
    Never returned in API responses.
    """

    model_config = ConfigDict(frozen=True)
    username: str
    slug: str = Field(default="", description="Sanitised lowercased identifier; derived from username if empty.")

    @model_validator(mode="after")
    def _derive_slug(self) -> OperatorIdentity:
        if self.slug:
            return self
        derived = _SLUG_DISALLOWED_RE.sub("-", self.username.strip().lower()).strip("-_.")
        if not derived:
            raise ValueError("operator slug is empty after sanitisation; cannot persist runs (FR-026)")
        # Pydantic frozen models: re-construct with the derived slug.
        object.__setattr__(self, "slug", derived)
        return self


class DiagnosticRun(BaseModel):
    host_id: str
    started_at: datetime
    completed_at: datetime
    outcome: RunOutcome
    items: list[DiagnosticItem]
    offline_reason: str | None = None


# --- 002 engine integration models ------------------------------------------


class EngineStatus(StrEnum):
    """The engine's three statuses, mirrored from the Rust `CheckStatus`
    enum (`engine/ree-debug-engine/src/types.rs`). Mapped to
    `ItemStatus` per FR-004a in `checks/ree_cli.py` (Phase 3, T034).
    """

    PASS = "Pass"
    WARN = "Warn"
    FAIL = "Fail"


class EngineCheckEntry(BaseModel):
    """One element of `EngineReport.checks`. Mirrors the Rust
    `CheckEntry` shape from `data-model.md` Layer 1.

    `name` is the engine's human-readable label for the check (e.g.,
    "SSH reachable"); used verbatim as operator-visible copy when no
    static catalog override exists. `id` is the slugified key used
    for catalog lookup once T039's mapping table is populated.
    """

    id: str
    name: str
    status: EngineStatus
    raw_detail: str | None = None
    duration_ms: int = Field(..., ge=0)


class EngineReport(BaseModel):
    """The JSON document `ree-debug-cli` prints to stdout for one host
    run. Parsed by `ReeCliExecutor` (Phase 3, T034).
    """

    schema_marker: str = Field(alias="schema")
    version: str
    host_id: str
    host_type: HostType
    started_at: datetime
    completed_at: datetime
    outcome: RunOutcome
    checks: list[EngineCheckEntry]

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def _validate(self) -> EngineReport:
        if self.schema_marker != "ree-debug-engine":
            raise ValueError(f"unexpected schema marker {self.schema_marker!r}")
        return self


class EngineErrorKind(StrEnum):
    """Engine-internal failure kinds emitted on stderr when the CLI
    exits non-zero (`contracts/engine-cli.md`).
    """

    INVENTORY_MISSING = "inventory_missing"
    INVENTORY_UNPARSEABLE = "inventory_unparseable"
    UNKNOWN_HOST_ID = "unknown_host_id"
    SSH_STARTUP_FAILED = "ssh_startup_failed"
    INTERNAL = "internal"


class EngineError(BaseModel):
    kind: EngineErrorKind
    message: str


# --- 002 settings models ----------------------------------------------------


class InventorySettings(BaseModel):
    """The persisted inventory path. Lives in `~/.config/vayobd/settings.toml`
    under the `[inventory]` table (FR-009 — FR-012). The path is
    expanded + validated via `_expand_and_validate` so an invalid file
    never ends up persisted.
    """

    path: Path

    @field_validator("path", mode="after")
    @classmethod
    def _expand_and_validate(cls, p: Path) -> Path:
        p = p.expanduser().resolve()
        if not p.exists():
            raise ValueError("path_missing")
        if not p.is_dir():
            raise ValueError("path_not_a_directory")
        if not (p / "org" / "vay" / "inventory.yaml").is_file():
            raise ValueError("inventory_yaml_missing")
        return p


class LiveSettings(BaseModel):
    """004 — Live diagnostic settings. Persisted under `[live]` in the
    settings TOML; absent on disk = Developer mode off, defaults for
    paths.
    """

    developer_mode: bool = False
    ree_reecu_path: Path | None = None
    dbc_path: Path | None = None


class AppSettings(BaseModel):
    """Top-level persisted settings. `inventory is None` means the
    operator hasn't completed first-launch setup yet — the SPA shows
    the setup card (US2).
    """

    inventory: InventorySettings | None = None
    live: LiveSettings = Field(default_factory=LiveSettings)


# --- Wire payloads / error envelopes ----------------------------------------


class RunRequest(BaseModel):
    host_id: str


class ProblemDetail(BaseModel):
    """problem+JSON error envelope per contracts/http-api.md."""

    error: str
    message_key: str
