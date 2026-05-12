"""Unit tests for the credential auto-detection probe (T023 / T027)."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from vayobd.install import credentials as cred_module
from vayobd.install.credentials import probe_credentials
from vayobd.install.messages import credential_failure_message


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=["fake"], returncode=returncode, stdout=stdout, stderr=stderr)


def test_ssh_wins_short_circuits_later_probes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cred_module.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        # Should only ever be called for ssh — gh/credential-helper must be skipped.
        assert args[0].endswith("ssh"), f"unexpected probe: {args}"
        return _completed(1, stderr="Hi alice! You've successfully authenticated, but GitHub does not provide shell access.")

    monkeypatch.setattr(cred_module.subprocess, "run", fake_run)

    result = probe_credentials()
    assert result.winner == "ssh"
    assert result.surfaces[0].succeeded is True
    assert result.surfaces[1].succeeded is False
    assert "not tried" in result.surfaces[1].detail
    assert result.surfaces[2].succeeded is False


def test_gh_wins_when_ssh_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cred_module.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if args[0].endswith("ssh"):
            return _completed(255, stderr="Permission denied (publickey).")
        if args[0].endswith("gh"):
            return _completed(0, stdout="Logged in to github.com as alice")
        raise AssertionError(f"credential-helper probe should be skipped, got {args}")

    monkeypatch.setattr(cred_module.subprocess, "run", fake_run)

    result = probe_credentials()
    assert result.winner == "gh"
    assert result.surfaces[0].surface == "ssh" and not result.surfaces[0].succeeded
    assert result.surfaces[1].surface == "gh" and result.surfaces[1].succeeded


def test_credential_helper_wins_when_ssh_and_gh_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cred_module.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if args[0].endswith("ssh"):
            return _completed(255, stderr="Permission denied (publickey).")
        if args[0].endswith("gh"):
            return _completed(1, stderr="You are not logged into any GitHub hosts.")
        if args[0].endswith("git"):
            return _completed(0, stdout="abc123\tHEAD\n")
        raise AssertionError(f"unexpected probe: {args}")

    monkeypatch.setattr(cred_module.subprocess, "run", fake_run)

    result = probe_credentials()
    assert result.winner == "credential-helper"


def test_all_fail_renders_full_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cred_module.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if args[0].endswith("ssh"):
            return _completed(255, stderr="Permission denied (publickey).")
        if args[0].endswith("gh"):
            return _completed(1, stderr="You are not logged into any GitHub hosts.")
        if args[0].endswith("git"):
            return _completed(128, stderr="fatal: could not resolve host: github.com")
        raise AssertionError(f"unexpected probe: {args}")

    monkeypatch.setattr(cred_module.subprocess, "run", fake_run)

    result = probe_credentials()
    assert result.winner is None
    assert result.all_failed is True

    # Spec FR-005: the rendered message MUST name every surface verbatim.
    rendered = credential_failure_message(result)
    assert "SSH (ssh -T git@github.com)" in rendered
    assert "GitHub CLI (gh auth status)" in rendered
    assert "System credential helper" in rendered
    assert "No data has been changed." in rendered


def test_ssh_timeout_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cred_module.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(args, **kwargs):  # type: ignore[no-untyped-def]
        if args[0].endswith("ssh"):
            raise subprocess.TimeoutExpired(cmd=args, timeout=10)
        if args[0].endswith("gh"):
            return _completed(0, stdout="Logged in to github.com as alice")
        raise AssertionError(f"unexpected: {args}")

    monkeypatch.setattr(cred_module.subprocess, "run", fake_run)

    result = probe_credentials()
    assert result.surfaces[0].succeeded is False
    assert "timed out" in result.surfaces[0].detail.lower()
    assert result.winner == "gh"


def test_ssh_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(name: str) -> str | None:
        if name == "ssh":
            return None
        return f"/usr/bin/{name}"

    monkeypatch.setattr(cred_module.shutil, "which", fake_which)
    # gh and credential-helper still need to be probed; mock them to fail too.
    monkeypatch.setattr(
        cred_module.subprocess,
        "run",
        lambda *a, **k: _completed(1, stderr="not authed"),
    )

    result = probe_credentials()
    assert result.surfaces[0].surface == "ssh"
    assert result.surfaces[0].succeeded is False
    assert "not installed" in result.surfaces[0].detail
