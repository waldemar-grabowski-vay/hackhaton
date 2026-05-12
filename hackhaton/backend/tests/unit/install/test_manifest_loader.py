"""Unit tests for the required-repos manifest loader (T006)."""

from __future__ import annotations

from pathlib import Path

import pytest

from vayobd.install.manifest import (
    Manifest,
    ManifestPathError,
    ManifestSchemaError,
    ManifestVersionError,
    load_manifest,
)


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_happy_path_two_repos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    manifest_path = _write(
        tmp_path / "manifest.toml",
        f"""
        manifest_version = 1

        [[repo]]
        id = "ree-vehicle-configs"
        url = "git@github.com:Reemote/ree-vehicle-configs.git"
        target_path = "{tmp_path}/.cache/vayobd/ree-vehicle-configs"
        branch = "main"

        [[repo]]
        id = "ree-reecu"
        url = "git@github.com:Reemote/ree-reecu.git"
        target_path = "{tmp_path}/GitHub/ree-reecu"
        sparse_paths = ["platform/tools/errq", "ve/6_tools/CANoe_G4/dbcs"]
        """,
    )

    manifest = load_manifest(manifest_path)
    assert isinstance(manifest, Manifest)
    assert manifest.manifest_version == 1
    assert [r.id for r in manifest.repo] == ["ree-vehicle-configs", "ree-reecu"]
    assert manifest.repo[1].sparse_paths == [
        "platform/tools/errq",
        "ve/6_tools/CANoe_G4/dbcs",
    ]


def test_missing_required_field(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    manifest_path = _write(
        tmp_path / "manifest.toml",
        f"""
        manifest_version = 1

        [[repo]]
        id = "ree-vehicle-configs"
        # url missing
        target_path = "{tmp_path}/x"
        """,
    )
    with pytest.raises(ManifestSchemaError):
        load_manifest(manifest_path)


def test_invalid_id_regex(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    manifest_path = _write(
        tmp_path / "manifest.toml",
        f"""
        manifest_version = 1

        [[repo]]
        id = "Bad_Id"
        url = "git@github.com:Reemote/x.git"
        target_path = "{tmp_path}/x"
        """,
    )
    with pytest.raises(ManifestSchemaError):
        load_manifest(manifest_path)


def test_target_outside_home_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    # /tmp/outside is intentionally outside the synthetic HOME we just set.
    outside = tmp_path.parent / "definitely-not-under-home"
    manifest_path = _write(
        tmp_path / "manifest.toml",
        f"""
        manifest_version = 1

        [[repo]]
        id = "evil"
        url = "git@github.com:Reemote/x.git"
        target_path = "{outside}"
        """,
    )
    with pytest.raises(ManifestPathError):
        load_manifest(manifest_path)


def test_unsupported_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    manifest_path = _write(
        tmp_path / "manifest.toml",
        f"""
        manifest_version = 2

        [[repo]]
        id = "x"
        url = "git@github.com:Reemote/x.git"
        target_path = "{tmp_path}/x"
        """,
    )
    with pytest.raises(ManifestVersionError):
        load_manifest(manifest_path)


def test_empty_repo_list_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    manifest_path = _write(tmp_path / "manifest.toml", "manifest_version = 1\n")
    with pytest.raises(ManifestSchemaError):
        load_manifest(manifest_path)


def test_duplicate_id_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    manifest_path = _write(
        tmp_path / "manifest.toml",
        f"""
        manifest_version = 1

        [[repo]]
        id = "x"
        url = "git@github.com:Reemote/x.git"
        target_path = "{tmp_path}/x"

        [[repo]]
        id = "x"
        url = "git@github.com:Reemote/y.git"
        target_path = "{tmp_path}/y"
        """,
    )
    with pytest.raises(ManifestSchemaError):
        load_manifest(manifest_path)


def test_sparse_paths_reject_dotdot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    manifest_path = _write(
        tmp_path / "manifest.toml",
        f"""
        manifest_version = 1

        [[repo]]
        id = "x"
        url = "git@github.com:Reemote/x.git"
        target_path = "{tmp_path}/x"
        sparse_paths = ["../escape"]
        """,
    )
    with pytest.raises(ManifestSchemaError):
        load_manifest(manifest_path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ManifestSchemaError):
        load_manifest(tmp_path / "does-not-exist.toml")
