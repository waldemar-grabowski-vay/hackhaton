"""Integration test for POST /api/refresh and GET /api/refresh/status (T032)."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vayobd.api import refresh as refresh_module
from vayobd.api.refresh import _reset_refresh_state_for_tests
from vayobd.app import create_app
from vayobd.config import ExecutorMode, Settings, get_settings
from vayobd.install import credentials as cred_module
from vayobd.install import clone as clone_module
from vayobd.install.clone import CloneAllResult, RepoCloneResult
from vayobd.install.messages import ProbeResult, ProbeSurfaceResult


@pytest.fixture
def manifest_file(tmp_path: Path) -> Path:
    target = tmp_path / "manifest.toml"
    target.write_text(
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
    return target


@pytest.fixture
def client(
    tmp_path: Path,
    manifest_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setenv("HOME", str(tmp_path))
    _reset_refresh_state_for_tests()
    settings = Settings(
        inventory_path=tmp_path,
        inventory_meta_path=tmp_path / "meta.json",
        runs_dir=tmp_path / "runs",
        executor=ExecutorMode.FIXTURE,
        fixtures_dir=Path(__file__).resolve().parents[2] / "fixtures" / "runs",
        manifest_path=manifest_file,
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _fake_probe_ssh_ok() -> ProbeResult:
    return ProbeResult(surfaces=[ProbeSurfaceResult("ssh", True, "authenticated")])


def _fake_probe_all_fail() -> ProbeResult:
    return ProbeResult(
        surfaces=[
            ProbeSurfaceResult("ssh", False, "Permission denied"),
            ProbeSurfaceResult("gh", False, "not installed"),
            ProbeSurfaceResult("credential-helper", False, "not configured"),
        ]
    )


def _fake_clone_all(manifest, state, **kwargs):  # type: ignore[no-untyped-def]
    now = datetime.now(UTC).replace(microsecond=0)
    for repo in manifest.repo:
        rs = state.repo.setdefault(repo.id, clone_module.RepoState())  # type: ignore[attr-defined]
        rs.last_synced_at = now
        rs.last_attempted_at = now
        rs.resolved_revision = "abc1234" + repo.id
        rs.last_outcome = "ok"
    state.last_refresh_at = now
    state.last_refresh_outcome = None
    return CloneAllResult(
        repos=[
            RepoCloneResult(repo.id, "ok", "abc1234" + repo.id, "")
            for repo in manifest.repo
        ]
    )


def test_post_refresh_starts_then_completes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(refresh_module, "probe_credentials", _fake_probe_ssh_ok)
    monkeypatch.setattr(refresh_module, "clone_all", _fake_clone_all)

    resp = client.post(
        "/api/refresh", json={}, headers={"X-Vay-User": "alice@vay.io"}
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["refresh_id"].startswith("r-")
    assert "started_at" in body

    # Status: should be running or already idle (depending on how fast the
    # background task drained). Either way it should not error and the repos
    # array eventually contains our fake repo.
    deadline = time.time() + 2.0
    last_body: dict[str, object] = {}
    while time.time() < deadline:
        st = client.get(
            "/api/refresh/status", headers={"X-Vay-User": "alice@vay.io"}
        )
        assert st.status_code == 200
        last_body = st.json()
        if last_body.get("state") == "idle" and last_body.get("repos"):
            break
        time.sleep(0.05)

    assert last_body.get("state") == "idle", last_body
    repo_ids = {r["id"] for r in last_body.get("repos", [])}
    assert "ree-vehicle-configs" in repo_ids


def test_post_refresh_503_on_credential_failure(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(refresh_module, "probe_credentials", _fake_probe_all_fail)

    resp = client.post(
        "/api/refresh", json={}, headers={"X-Vay-User": "alice@vay.io"}
    )
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"] == "credentials_failed"
    # The 'tried' list MUST name every surface (contracts/http-api.md).
    surfaces = {entry["surface"] for entry in body["tried"]}
    assert surfaces == {"ssh", "gh", "credential-helper"}


def test_post_refresh_returns_409_when_already_running(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(refresh_module, "probe_credentials", _fake_probe_ssh_ok)

    # Slow fake — keeps the global lock held long enough that the second POST sees 409.
    started = threading.Event()
    finish = threading.Event()

    def slow_run_refresh(_refresh_id: str) -> None:
        try:
            started.set()
            finish.wait(timeout=5.0)
        finally:
            refresh_module._current_refresh = None  # type: ignore[attr-defined]

    monkeypatch.setattr(refresh_module, "_run_refresh", slow_run_refresh)

    first = client.post(
        "/api/refresh", json={}, headers={"X-Vay-User": "alice@vay.io"}
    )
    assert first.status_code == 202

    # Wait until the worker has actually entered the slow function so the lock
    # is held when we issue the second POST.
    assert started.wait(timeout=2.0), "background refresh thread never started"

    second = client.post(
        "/api/refresh", json={}, headers={"X-Vay-User": "alice@vay.io"}
    )
    assert second.status_code == 409
    body = second.json()
    assert body["error"] == "refresh_in_progress"

    # Release the slow worker so the lock is freed for the next test.
    finish.set()
    time.sleep(0.05)
