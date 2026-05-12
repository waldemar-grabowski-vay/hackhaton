"""Unit tests for the manifest-state reader/writer (T007)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from vayobd.install.state import (
    ManifestState,
    RepoState,
    load_state,
    save_state_atomic,
)


def test_load_state_missing_file_returns_empty(tmp_path: Path) -> None:
    state = load_state(tmp_path / "missing.toml")
    assert isinstance(state, ManifestState)
    assert state.is_first_run is True
    assert state.repo == {}
    assert state.credential_surface_used is None


def test_round_trip_two_repos(tmp_path: Path) -> None:
    target = tmp_path / "manifest-state.toml"
    now = datetime.now(UTC).replace(microsecond=0)
    original = ManifestState(
        last_credential_probe=now,
        credential_surface_used="ssh",
        repo={
            "ree-vehicle-configs": RepoState(
                last_synced_at=now,
                last_attempted_at=now,
                resolved_revision="a" * 40,
                last_outcome="ok",
            ),
            "ree-reecu": RepoState(
                last_synced_at=now,
                last_attempted_at=now,
                resolved_revision="b" * 40,
                last_outcome="ok",
            ),
        },
    )
    save_state_atomic(original, target)

    reloaded = load_state(target)
    assert reloaded.credential_surface_used == "ssh"
    assert reloaded.last_credential_probe == now
    assert set(reloaded.repo) == {"ree-vehicle-configs", "ree-reecu"}
    assert reloaded.repo["ree-vehicle-configs"].resolved_revision == "a" * 40
    assert reloaded.repo["ree-reecu"].resolved_revision == "b" * 40
    assert reloaded.is_first_run is False


def test_stalest_age_returns_max(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    state = ManifestState(
        repo={
            "fresh": RepoState(last_synced_at=now - timedelta(seconds=30)),
            "stale": RepoState(last_synced_at=now - timedelta(hours=48)),
        }
    )
    age = state.stalest_age(now=now)
    assert age is not None
    assert age.total_seconds() >= 48 * 3600 - 1


def test_stalest_age_none_when_never_synced(tmp_path: Path) -> None:
    state = ManifestState(repo={"x": RepoState()})
    assert state.stalest_age() is None


def test_atomic_write_leaves_no_partial_on_crash(tmp_path: Path) -> None:
    """Simulate a crash during write: file does not exist; tmp does not linger."""
    target = tmp_path / "manifest-state.toml"
    state = ManifestState(credential_surface_used="ssh")

    # Pre-existing file we will fail to overwrite — must remain intact afterwards.
    target.write_text("previous_content = true\n", encoding="utf-8")

    with patch("vayobd.install.state.os.replace", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            save_state_atomic(state, target)

    # Original file unchanged
    assert target.read_text(encoding="utf-8") == "previous_content = true\n"
    # No stray .tmp files in the directory
    assert not list(tmp_path.glob(".manifest-state-*.tmp"))


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "nested" / "manifest-state.toml"
    save_state_atomic(ManifestState(), target)
    assert target.is_file()


def test_render_omits_none_fields(tmp_path: Path) -> None:
    """A near-empty state writes a near-empty TOML, not 'null = ...' lines."""
    target = tmp_path / "manifest-state.toml"
    save_state_atomic(ManifestState(), target)
    body = target.read_text(encoding="utf-8")
    assert "last_credential_probe" not in body
    assert "credential_surface_used" not in body
    assert "null" not in body.lower()


def test_default_state_path_is_under_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    # Re-import to pick up the monkeypatched HOME for the module-level constant.
    # default_state_path() reads Path.home() each call, so it should respect HOME.
    from vayobd.install.state import default_state_path

    p = default_state_path()
    assert str(p).startswith(str(tmp_path))
    assert p.name == "manifest-state.toml"
