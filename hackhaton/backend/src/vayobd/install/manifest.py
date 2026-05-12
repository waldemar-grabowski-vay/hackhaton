"""Loader for the required-repos manifest shipped at /usr/share/vayobd/manifest.toml.

Schema documented in specs/006-deb-package-distribution/contracts/manifest.md.
This is the FR-006 single source of truth for which private repos VayOBD needs.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from vayobd.logging import get_logger

log = get_logger(__name__)

_SUPPORTED_MANIFEST_VERSION = 1
_REPO_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")


class ManifestError(Exception):
    """Base for every manifest-loading failure."""


class ManifestVersionError(ManifestError):
    """`manifest_version` is not understood by this VayOBD."""


class ManifestPathError(ManifestError):
    """A `target_path` resolves outside `$HOME` — refused for safety."""


class ManifestSchemaError(ManifestError):
    """Required field missing, regex mismatch, or other shape violation."""


class RepoEntry(BaseModel):
    """One row in the manifest's `[[repo]]` array.

    Contract: see specs/006-deb-package-distribution/contracts/manifest.md.
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    id: str
    url: str
    target_path: Path
    branch: str | None = None
    sparse_paths: list[str] = Field(default_factory=list)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if not _REPO_ID_RE.match(value):
            raise ManifestSchemaError(
                f"repo.id {value!r} must match {_REPO_ID_RE.pattern}"
            )
        return value

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        if not value or not value.strip():
            raise ManifestSchemaError("repo.url must be a non-empty string")
        return value.strip()

    @field_validator("sparse_paths")
    @classmethod
    def _validate_sparse_paths(cls, value: list[str]) -> list[str]:
        for entry in value:
            if entry.startswith("/"):
                raise ManifestSchemaError(
                    f"sparse_paths entry {entry!r} must be relative, not absolute"
                )
            if ".." in Path(entry).parts:
                raise ManifestSchemaError(
                    f"sparse_paths entry {entry!r} must not contain '..' segments"
                )
        return value

    def resolved_target(self) -> Path:
        """Absolute target_path with `~` and env vars expanded."""
        return Path(str(self.target_path)).expanduser().resolve()

    def ensure_under_home(self) -> None:
        """Raise ManifestPathError if the resolved target_path is not inside $HOME."""
        home = Path.home().resolve()
        target = self.resolved_target()
        try:
            target.relative_to(home)
        except ValueError as exc:
            raise ManifestPathError(
                f"repo.id={self.id!r} target_path resolves to {target!s}, "
                f"which is not under {home!s}"
            ) from exc


class Manifest(BaseModel):
    """Top-level manifest object."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    manifest_version: int
    repo: list[RepoEntry]

    @field_validator("repo")
    @classmethod
    def _validate_repo_unique_nonempty(cls, value: list[RepoEntry]) -> list[RepoEntry]:
        if not value:
            raise ManifestSchemaError("manifest must contain at least one [[repo]]")
        seen: set[str] = set()
        for entry in value:
            if entry.id in seen:
                raise ManifestSchemaError(f"duplicate repo.id {entry.id!r}")
            seen.add(entry.id)
        return value


def load_manifest(path: Path) -> Manifest:
    """Read and validate the manifest at `path`.

    Raises:
        ManifestSchemaError: file missing, malformed TOML, missing required field,
            invalid `id`, duplicate `id`, empty `[[repo]]` list, bad sparse_paths.
        ManifestVersionError: `manifest_version` not equal to the supported version.
        ManifestPathError: any `target_path` resolves outside `$HOME`.
    """
    if not path.is_file():
        log.warning("manifest_missing", path=str(path))
        raise ManifestSchemaError(f"manifest file not found at {path!s}")

    try:
        with path.open("rb") as fh:
            raw: dict[str, Any] = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        log.warning("manifest_unparseable", path=str(path), error=str(exc))
        raise ManifestSchemaError(f"could not parse {path!s}: {exc}") from exc

    version = raw.get("manifest_version")
    if version != _SUPPORTED_MANIFEST_VERSION:
        log.warning("manifest_version_unsupported", path=str(path), version=version)
        raise ManifestVersionError(
            f"manifest_version {version!r} is not supported "
            f"(this VayOBD speaks v{_SUPPORTED_MANIFEST_VERSION})"
        )

    try:
        manifest = Manifest.model_validate(raw)
    except ManifestError:
        raise
    except Exception as exc:  # pydantic ValidationError, etc.
        log.warning("manifest_schema_invalid", path=str(path), error=str(exc))
        raise ManifestSchemaError(str(exc)) from exc

    # FR-006 safety: every target_path must resolve under $HOME.
    for entry in manifest.repo:
        entry.ensure_under_home()

    log.info(
        "manifest_loaded",
        path=str(path),
        version=manifest.manifest_version,
        repos=[r.id for r in manifest.repo],
    )
    return manifest
