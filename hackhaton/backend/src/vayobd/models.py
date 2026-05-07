"""Pydantic models — the single source of truth for API payloads (R6, data-model.md).

Field names are snake_case at the API boundary (Python convention). The frontend
mirrors these in `frontend/src/api/schemas.ts` via Zod.
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

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
    COMMUNICATION = "communication"
    HARDWARE = "hardware"
    CONFIGURATION = "configuration"


class ItemStatus(StrEnum):
    WORKING = "working"
    ERROR = "error"


class RunOutcome(StrEnum):
    """Four outcomes per research R5. Note: spec FR-006 lists three (`timeout`
    is added here as distinct from `unreachable`). HIGH analyze finding I1 —
    spec amendment pending."""

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
    """Inventory freshness summary returned to the SPA.

    `last_refreshed_at` is the most recent **successful** refresh; the
    `*_attempted_at` and `consecutive_failed_refreshes` fields track the
    refresh-failure surfacing required by FR-027 so the SPA can decide
    when to show the persistent banner.
    """

    last_refreshed_at: datetime
    last_refresh_attempted_at: datetime | None = None
    consecutive_failed_refreshes: int = 0
    source_revision: str
    host_count: int


class Inventory(BaseModel):
    """The full payload behind GET /api/inventory."""

    meta: InventoryMeta
    hosts: list[Host]


class DiagnosticItem(BaseModel):
    """One thing that was checked. raw_detail is always populated server-side
    so toggling Developer mode never requires a refetch (FR-022)."""

    id: str = Field(..., description="Stable per host class, e.g. 'main_can_bus_reachable'.")
    name_key: str
    description_key: str | None = None
    category: CheckCategory
    status: ItemStatus
    recommended_action_key: str | None = None
    raw_detail: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> DiagnosticItem:
        if self.status is ItemStatus.ERROR and self.recommended_action_key is None:
            raise ValueError(f"errored item {self.id!r} must have recommended_action_key (FR-005)")
        return self


_SLUG_DISALLOWED_RE = re.compile(r"[^a-z0-9._-]+")


class OperatorIdentity(BaseModel):
    """Pulled from the X-Vay-User reverse-proxy header (R4 + FR-026).

    Load-bearing in v1: `slug` is used as a path segment when persisting
    runs (`runs/<slug>/<host_id>.json`), so it must be sanitised.
    Never returned in API responses — used for structured logging,
    persisted run audit, and per-operator scoping only.
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


# --- Wire payloads / error envelopes -----------------------------------------


class RunRequest(BaseModel):
    host_id: str


class ProblemDetail(BaseModel):
    """problem+JSON error envelope per contracts/http-api.md."""

    error: str
    message_key: str
