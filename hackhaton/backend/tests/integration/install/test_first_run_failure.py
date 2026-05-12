"""Integration test for the first-run credential-failure flow (T028).

Exercises `vayobd.cli._cmd_run` end-to-end with all credential surfaces
forced to fail. Asserts FR-005 contract:

  - exit code 2,
  - stderr names every probe surface verbatim,
  - no partial cache left behind (the `.cache/vayobd/.tmp-*` tree is gone).
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path

import pytest

from vayobd.cli import build_parser, main
from vayobd.install import credentials as cred_module


def _force_all_creds_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cred_module.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if args[0].endswith("ssh"):
            return subprocess.CompletedProcess(args, 255, "", "Permission denied (publickey).")
        if args[0].endswith("gh"):
            return subprocess.CompletedProcess(args, 1, "", "You are not logged into any GitHub hosts.")
        if args[0].endswith("git"):
            return subprocess.CompletedProcess(args, 128, "", "fatal: could not resolve host: github.com")
        raise AssertionError(f"unexpected subprocess call: {args}")

    monkeypatch.setattr(cred_module.subprocess, "run", fake_run)


def _write_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "manifest.toml"
    manifest.write_text(
        f"""
manifest_version = 1

[[repo]]
id = "ree-vehicle-configs"
url = "git@github.com:Reemote/ree-vehicle-configs.git"
target_path = "{tmp_path}/.cache/vayobd/ree-vehicle-configs"
branch = "main"
""",
        encoding="utf-8",
    )
    return manifest


def test_first_run_no_creds_exits_2_and_renders_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Synthetic HOME so the "is_first_run" check sees no state file and so
    # the .cache scope is contained to tmp_path.
    monkeypatch.setenv("HOME", str(tmp_path))
    _force_all_creds_fail(monkeypatch)

    manifest = _write_manifest(tmp_path)

    exit_code = main(["run", "--no-browser", "--manifest", str(manifest)])
    captured = capsys.readouterr()

    assert exit_code == 2, f"expected exit 2 (FR-005); got {exit_code}. stderr was: {captured.err!r}"

    # FR-005 wording assertions — names every surface and the "no data has been changed" reassurance.
    assert "couldn't read your GitHub credentials" in captured.err
    assert "SSH (ssh -T git@github.com)" in captured.err
    assert "GitHub CLI (gh auth status)" in captured.err
    assert "System credential helper" in captured.err
    assert "No data has been changed." in captured.err

    # Story 2 AS-3: no partial cache.
    cache = tmp_path / ".cache" / "vayobd"
    if cache.exists():
        # Allow the parent dir to exist, but no tmp-* clone staging should remain
        # and no per-repo target dirs should have been created.
        assert not list(cache.glob(".tmp-*")), "first-run failure left a staging dir behind"
        assert not (cache / "ree-vehicle-configs").exists(), "first-run failure left a clone behind"
        # manifest-state.toml should NOT exist (we never reached the post-clone save).
        assert not (cache / "manifest-state.toml").exists(), "manifest-state.toml should not exist after a credential failure"


def test_root_guard_blocks_run(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """FR-015: refuse to run as root."""
    monkeypatch.setattr("os.geteuid", lambda: 0, raising=False)
    exit_code = main(["run"])
    captured = capsys.readouterr()
    assert exit_code == 6
    assert "must run as your normal user" in captured.err


def test_parser_has_run_refresh_doctor() -> None:
    """Smoke-check the argparse contract from contracts/cli.md."""
    parser = build_parser()
    namespaces: dict[str, object] = {}
    for sub in ("run", "refresh", "doctor"):
        namespaces[sub] = parser.parse_args([sub])
    assert namespaces["run"].subcommand == "run"  # type: ignore[attr-defined]
    assert namespaces["refresh"].subcommand == "refresh"  # type: ignore[attr-defined]
    assert namespaces["doctor"].subcommand == "doctor"  # type: ignore[attr-defined]
