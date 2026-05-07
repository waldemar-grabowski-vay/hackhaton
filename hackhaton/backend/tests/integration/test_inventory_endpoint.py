"""Integration coverage for GET /api/inventory and the 503 empty path."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vayobd.app import create_app
from vayobd.config import ExecutorMode, Settings, get_settings


@pytest.fixture
def client(synthetic_inventory: Path, tmp_path: Path) -> TestClient:
    settings = Settings(
        inventory_path=synthetic_inventory,
        inventory_meta_path=tmp_path / "inventory.meta.json",
        runs_dir=tmp_path / "runs",
        executor=ExecutorMode.FIXTURE,
        fixtures_dir=Path(__file__).resolve().parents[1] / "fixtures" / "runs",
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_inventory_returns_in_scope_hosts(client: TestClient) -> None:
    resp = client.get("/api/inventory")
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["host_count"] == 6
    ids = {h["id"] for h in body["hosts"]}
    assert ids == {
        "ve-de-apollo",
        "ve-de-loki",
        "ve-de-no-fixture",
        "ve-de-thor",
        "ve-de-saturn-slow",
        "ts-de-ber-zeus",
    }
    # Out-of-scope hosts are dropped at load.
    assert "ve-be-bxl" not in ids
    assert "ts-de-ham-poseidon" not in ids
    assert "ve-us-01001" not in ids
    assert "ts-us-las-00001" not in ids
    # Server-internal fields stripped.
    for host in body["hosts"]:
        assert "address" not in host or host["address"] is None
        assert "source_file" not in host or host["source_file"] is None
    # 002 / FR-013a — slimmed meta shape (no caching, no last-refreshed
    # timestamps, no failure counter). The 001 fields are gone.
    meta = body["meta"]
    assert "last_read_at" in meta
    assert "source_path" in meta
    assert "host_count" in meta
    assert meta["host_count"] == 6
    # 001's retired fields are NOT present any more.
    assert "consecutive_failed_refreshes" not in meta
    assert "last_refresh_attempted_at" not in meta
    assert "last_refreshed_at" not in meta
    assert "source_revision" not in meta


def test_inventory_empty_returns_503(tmp_path: Path) -> None:
    settings = Settings(
        inventory_path=tmp_path / "missing",
        inventory_meta_path=tmp_path / "inventory.meta.json",
        runs_dir=tmp_path / "runs",
        executor=ExecutorMode.FIXTURE,
        fixtures_dir=tmp_path / "fixtures",
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    resp = client.get("/api/inventory")
    assert resp.status_code == 503
    assert resp.json()["error"] == "inventory_unavailable"
