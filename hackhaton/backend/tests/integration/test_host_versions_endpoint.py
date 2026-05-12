"""Integration tests — `GET /api/host/{host_id}/versions` (007).

Drives the FastAPI endpoint with a monkey-patched engine subprocess
so we can assert end-to-end behaviour (cache, ?fresh=true, 404 on
unknown host, all-unavailable shape) without needing a real
ree-debug-cli binary or a reachable host.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from vayobd._internal.version_cache import VersionCache
from vayobd.api import host_versions as host_versions_module
from vayobd.api.host_versions import HostVersionsResponse
from vayobd.app import create_app
from vayobd.config import ExecutorMode, Settings, get_settings
from vayobd.models import EngineReport
from tests.conftest import AUTH_HEADERS

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "engine_reports"


@pytest.fixture
def fresh_cache() -> VersionCache[HostVersionsResponse]:
    cache: VersionCache[HostVersionsResponse] = VersionCache(ttl_seconds=60)
    host_versions_module.set_cache_for_tests(cache)
    yield cache
    cache.clear()


@pytest.fixture
def client(
    synthetic_inventory: Path, tmp_path: Path, fresh_cache: VersionCache[HostVersionsResponse]
) -> TestClient:
    settings = Settings(
        inventory_path=synthetic_inventory,
        inventory_meta_path=tmp_path / "inventory.meta.json",
        runs_dir=tmp_path / "runs",
        executor=ExecutorMode.FIXTURE,
        # Point ree_cli_bin at a non-existent file so the resolver returns it
        # — our monkeypatched _invoke_engine ignores the path anyway.
        ree_cli_bin=tmp_path / "ree-debug-cli-fake",
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _ts_report() -> EngineReport:
    return EngineReport.model_validate_json((FIXTURE_DIR / "ts_host_full.json").read_text())


def _patch_engine_returns(monkeypatch: pytest.MonkeyPatch, report: EngineReport) -> dict[str, int]:
    """Replace _invoke_engine with a counter-tracking stub returning `report`."""
    counter = {"calls": 0}

    async def fake(host_id: str, settings: Settings) -> EngineReport:
        counter["calls"] += 1
        return report

    monkeypatch.setattr(host_versions_module, "_invoke_engine", fake)
    return counter


def _patch_engine_raises(monkeypatch: pytest.MonkeyPatch, reason: str) -> dict[str, int]:
    counter = {"calls": 0}

    async def fake(host_id: str, settings: Settings) -> EngineReport:
        counter["calls"] += 1
        raise host_versions_module.EngineUnavailable(reason)

    monkeypatch.setattr(host_versions_module, "_invoke_engine", fake)
    return counter


# --- Happy path -------------------------------------------------------------


def test_returns_three_version_fields_and_live_source(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_engine_returns(monkeypatch, _ts_report())

    resp = client.get("/api/host/ts-de-ber-zeus/versions", headers=AUTH_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "live"
    v = body["versions"]
    assert v["vdrive_manifest"]["verdict"] == "drift"
    assert v["vdrive_manifest"]["value"] == "R12.3.0"
    assert v["vdrive_manifest"]["expected"] == "R12.4.0"
    assert v["vreecu_version"]["verdict"] == "match"
    assert v["vreecu_version"]["value"] == "R 8.5.3"  # build_type prefix preserved
    assert v["sec_version"]["verdict"] == "unavailable"
    assert v["sec_version"]["reason"] is not None
    # 008: response now also carries the restored check battery.
    assert body["run"] is not None
    assert body["run"]["host_id"] == "ts-de-ber-zeus"
    assert len(body["run"]["items"]) > 0
    # FR-011 — REECU-owned rows must NOT appear in run.items
    # (they belong to the version card).
    for item in body["run"]["items"]:
        assert not any(p in item["id"].lower() for p in ("vdrive", "ree-drive", "aurix", "sec_version", "sec-version"))


# --- Caching ----------------------------------------------------------------


def test_second_call_within_ttl_serves_cache(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = _patch_engine_returns(monkeypatch, _ts_report())

    r1 = client.get("/api/host/ts-de-ber-zeus/versions", headers=AUTH_HEADERS)
    r2 = client.get("/api/host/ts-de-ber-zeus/versions", headers=AUTH_HEADERS)
    assert r1.status_code == r2.status_code == 200
    assert r1.json() == r2.json()
    assert counter["calls"] == 1  # second hit served from cache


def test_fresh_true_bypasses_cache(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = _patch_engine_returns(monkeypatch, _ts_report())

    client.get("/api/host/ts-de-ber-zeus/versions", headers=AUTH_HEADERS)
    client.get("/api/host/ts-de-ber-zeus/versions?fresh=true", headers=AUTH_HEADERS)
    assert counter["calls"] == 2  # cache busted by ?fresh=true


def test_fresh_other_values_400s(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_engine_returns(monkeypatch, _ts_report())

    resp = client.get(
        "/api/host/ts-de-ber-zeus/versions?fresh=1", headers=AUTH_HEADERS
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "bad_query"


def test_per_host_cache_scoping(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    counter = _patch_engine_returns(monkeypatch, _ts_report())

    client.get("/api/host/ts-de-ber-zeus/versions", headers=AUTH_HEADERS)
    client.get("/api/host/ve-de-apollo/versions", headers=AUTH_HEADERS)
    client.get("/api/host/ts-de-ber-zeus/versions", headers=AUTH_HEADERS)
    # First two are cold (one per host), third is cached.
    assert counter["calls"] == 2


# --- Error paths ------------------------------------------------------------


def test_unknown_host_returns_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_engine_returns(monkeypatch, _ts_report())

    resp = client.get(
        "/api/host/ve-de-does-not-exist/versions", headers=AUTH_HEADERS
    )
    assert resp.status_code == 404
    assert resp.json()["error"] == "host_not_found"


def test_engine_unavailable_yields_200_with_unavailable_versions(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """008 change: the two pipelines are independent (Clarification Q1 +
    FR-010). When the engine fails, the version cells go to unavailable,
    but the restored check battery still runs and feeds `run`. The
    response source is `live` because the page has SOMETHING to show."""
    _patch_engine_raises(monkeypatch, "engine timed out reading versions for this host")

    resp = client.get(
        "/api/host/ts-de-ber-zeus/versions", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200
    body = resp.json()
    # Version cells unavailable (engine failed).
    for field in ("vdrive_manifest", "vreecu_version", "sec_version"):
        assert body["versions"][field]["verdict"] == "unavailable"
        assert body["versions"][field]["value"] is None
        assert body["versions"][field]["reason"] is not None
    # The fixture-mode check battery succeeded in the test client.
    # Source is live (battery has rows even though engine didn't).
    assert body["source"] == "live"
    assert body["run"] is not None
    assert body["run"]["outcome"] == "complete"


def test_missing_auth_header_returns_401(client: TestClient) -> None:
    resp = client.get("/api/host/ts-de-ber-zeus/versions")  # no X-Vay-User
    assert resp.status_code == 401
