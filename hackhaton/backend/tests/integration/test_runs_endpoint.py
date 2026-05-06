"""T038 — POST /api/runs against the FixtureExecutor for the three seeded
fixtures, plus 409 on a concurrent second call.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vayobd.app import create_app
from vayobd.config import ExecutorMode, Settings


def _make_settings(*, inventory_path: Path, runs_dir: Path, fixtures_dir: Path) -> Settings:
    return Settings(
        inventory_path=inventory_path,
        inventory_meta_path=runs_dir.parent / "inventory.meta.json",
        runs_dir=runs_dir,
        executor=ExecutorMode.FIXTURE,
        fixtures_dir=fixtures_dir,
        run_timeout_seconds=10.0,
    )


@pytest.fixture
def client(synthetic_inventory: Path, tmp_path: Path) -> TestClient:
    runs_dir = tmp_path / "runs"
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "runs"
    settings = _make_settings(
        inventory_path=synthetic_inventory, runs_dir=runs_dir, fixtures_dir=fixtures_dir
    )
    app = create_app(settings=settings)
    # Override get_settings so dependents (inventory + runs routers) see ours.
    from vayobd.config import get_settings

    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_run_healthy_host_complete_outcome(client: TestClient) -> None:
    resp = client.post("/api/runs", json={"host_id": "ve-de-apollo"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["host_id"] == "ve-de-apollo"
    assert body["outcome"] == "complete"
    statuses = {item["id"]: item["status"] for item in body["items"]}
    assert statuses["main_can_bus_reachable"] == "working"
    assert statuses["expected_front_camera_connected"] == "working"


def test_run_errored_host_has_recommended_action(client: TestClient) -> None:
    resp = client.post("/api/runs", json={"host_id": "ve-de-loki"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["outcome"] == "complete"
    by_id = {item["id"]: item for item in body["items"]}
    front = by_id["expected_front_camera_connected"]
    assert front["status"] == "error"
    assert front["recommended_action_key"] is not None


def test_run_unreachable_host_returns_empty_items(client: TestClient) -> None:
    resp = client.post("/api/runs", json={"host_id": "ve-de-thor"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["outcome"] == "unreachable"
    assert body["items"] == []


def test_run_unknown_host_returns_404(client: TestClient) -> None:
    resp = client.post("/api/runs", json={"host_id": "ve-de-not-in-inventory"})
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "unknown_host"


def test_concurrent_run_for_same_host_returns_409(
    synthetic_inventory: Path, tmp_path: Path
) -> None:
    """Two parallel POST /api/runs for the same host: the second gets 409."""
    runs_dir = tmp_path / "runs"
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "runs"
    settings = _make_settings(
        inventory_path=synthetic_inventory, runs_dir=runs_dir, fixtures_dir=fixtures_dir
    )

    # Use httpx.AsyncClient against the ASGI app to actually run two requests
    # concurrently inside one event loop (TestClient is sync).
    import httpx

    from vayobd.app import create_app
    from vayobd.config import get_settings as _gs

    app = create_app(settings=settings)
    app.dependency_overrides[_gs] = lambda: settings

    async def _go() -> tuple[int, int]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            t1 = asyncio.create_task(c.post("/api/runs", json={"host_id": "ve-de-apollo"}))
            # Yield once so t1 acquires the lock before t2 checks.
            await asyncio.sleep(0)
            t2 = asyncio.create_task(c.post("/api/runs", json={"host_id": "ve-de-apollo"}))
            r1, r2 = await asyncio.gather(t1, t2)
            return r1.status_code, r2.status_code

    code1, code2 = asyncio.run(_go())
    # Whichever lost the race returns 409. Exactly one 200 and one 409.
    assert {code1, code2} == {200, 409}, (code1, code2)


def test_get_latest_returns_404_when_no_run(client: TestClient) -> None:
    resp = client.get("/api/runs/latest", params={"host_id": "ve-de-apollo"})
    assert resp.status_code == 404
    assert resp.json()["error"] == "no_run_yet"


def test_get_latest_returns_persisted_run(client: TestClient) -> None:
    client.post("/api/runs", json={"host_id": "ve-de-apollo"})
    resp = client.get("/api/runs/latest", params={"host_id": "ve-de-apollo"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["host_id"] == "ve-de-apollo"
