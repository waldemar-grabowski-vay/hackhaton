"""Reader/writer for ~/.cache/vayobd/manifest-state.toml.

Survives apt remove / upgrade (per FR-011 / FR-012). Schema in
specs/006-deb-package-distribution/data-model.md § 2. Writes are atomic
(tmp file + os.replace) so a crash mid-write can never produce a partial state file.
"""

from __future__ import annotations

import os
import tempfile
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from vayobd.logging import get_logger

log = get_logger(__name__)

CredentialSurface = Literal["ssh", "gh", "credential-helper"]
RepoOutcome = Literal["ok", "network-error", "auth-error", "conflict"]


def default_state_path() -> Path:
    """Return the canonical state-file location for the invoking user.

    Resolved on every call so tests (and operators using `HOME=...`) see the
    current home directory rather than a cached value from import time.
    """
    return Path.home() / ".cache" / "vayobd" / "manifest-state.toml"


class RepoState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    last_synced_at: datetime | None = None
    last_attempted_at: datetime | None = None
    resolved_revision: str | None = None
    last_outcome: RepoOutcome = "ok"


class ManifestState(BaseModel):
    model_config = ConfigDict(extra="ignore")

    last_credential_probe: datetime | None = None
    credential_surface_used: CredentialSurface | None = None
    repo: dict[str, RepoState] = Field(default_factory=dict)
    last_refresh_outcome: (
        Literal["partial_failure", "credentials_failed", "network_error", "conflict"] | None
    ) = None
    last_refresh_at: datetime | None = None

    @property
    def is_first_run(self) -> bool:
        """True iff no repo has ever been successfully synced."""
        return not any(s.last_synced_at for s in self.repo.values())

    def stalest_age(self, now: datetime | None = None) -> timedelta | None:
        """Max age across all repos (used by the in-app staleness banner, FR-010)."""
        if now is None:
            now = datetime.now(UTC)
        ages = [
            now - s.last_synced_at
            for s in self.repo.values()
            if s.last_synced_at is not None
        ]
        if not ages:
            return None
        return max(ages)


def load_state(path: Path | None = None) -> ManifestState:
    """Load the manifest state, returning an empty state if the file is absent.

    The "file absent" case is the first-run trigger; callers test `is_first_run`.
    """
    target = path or default_state_path()
    if not target.is_file():
        return ManifestState()
    try:
        with target.open("rb") as fh:
            raw: dict[str, Any] = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("state_unparseable_resetting", path=str(target), error=str(exc))
        return ManifestState()
    return ManifestState.model_validate(raw)


def save_state_atomic(state: ManifestState, path: Path | None = None) -> Path:
    """Write `state` to `path` atomically (tmp + os.replace)."""
    target = path or default_state_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = _render_toml(state)
    # NamedTemporaryFile in the same dir guarantees os.replace stays on one filesystem.
    fd, tmp_name = tempfile.mkstemp(
        prefix=".manifest-state-", suffix=".tmp", dir=target.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        # Includes KeyboardInterrupt — leave no stray tmp file behind.
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise
    return target


def _render_toml(state: ManifestState) -> str:
    """Render `state` to TOML text.

    We hand-write the TOML (rather than depending on `tomli-w`) to keep the
    runtime dependency surface small — Python ships `tomllib` for reading
    but not writing as of 3.11+, and the schema here is tiny.
    """
    lines: list[str] = []
    if state.last_credential_probe is not None:
        lines.append(f"last_credential_probe = {_fmt_dt(state.last_credential_probe)}")
    if state.credential_surface_used is not None:
        lines.append(f'credential_surface_used = "{state.credential_surface_used}"')
    if state.last_refresh_outcome is not None:
        lines.append(f'last_refresh_outcome = "{state.last_refresh_outcome}"')
    if state.last_refresh_at is not None:
        lines.append(f"last_refresh_at = {_fmt_dt(state.last_refresh_at)}")

    for repo_id, repo_state in state.repo.items():
        lines.append("")
        lines.append(f"[repo.{repo_id}]")
        if repo_state.last_synced_at is not None:
            lines.append(f"last_synced_at = {_fmt_dt(repo_state.last_synced_at)}")
        if repo_state.last_attempted_at is not None:
            lines.append(f"last_attempted_at = {_fmt_dt(repo_state.last_attempted_at)}")
        if repo_state.resolved_revision is not None:
            lines.append(f'resolved_revision = "{repo_state.resolved_revision}"')
        lines.append(f'last_outcome = "{repo_state.last_outcome}"')

    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _fmt_dt(value: datetime) -> str:
    """TOML date-time literal (RFC 3339) for an aware UTC datetime."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    # TOML offset-date-time: 2026-05-11T09:42:48Z
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
