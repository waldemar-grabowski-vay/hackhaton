"""T038 / T086 — POST /api/runs against the FixtureExecutor.

Covers:
  - Healthy / errored / unreachable outcome shapes.
  - 404 on unknown host.
  - 409 on concurrent run for the same host (FR-011).
  - 401 on missing X-Vay-User (FR-026 / R4).
  - 30 s hard timeout (FR-025) — exercised with a low `run_timeout_seconds`
    value paired with the slow fixture so the suite stays fast.
  - GET /api/runs/latest is intentionally absent in v1 (FR-028 / R7).
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vayobd.app import create_app
from vayobd.config import ExecutorMode, Settings


def _make_settings(
    *,
    inventory_path: Path,
    runs_dir: Path,
    fixtures_dir: Path,
    run_timeout_seconds: float = 10.0,
) -> Settings:
    return Settings(
        inventory_path=inventory_path,
        inventory_meta_path=runs_dir.parent / "inventory.meta.json",
        runs_dir=runs_dir,
        executor=ExecutorMode.FIXTURE,
        fixtures_dir=fixtures_dir,
        run_timeout_seconds=run_timeout_seconds,
    )


@pytest.fixture
def client(synthetic_inventory: Path, tmp_path: Path) -> TestClient:
    runs_dir = tmp_path / "runs"
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "runs"
    settings = _make_settings(
        inventory_path=synthetic_inventory, runs_dir=runs_dir, fixtures_dir=fixtures_dir
    )
    app = create_app(settings=settings)
    from vayobd.config import get_settings

    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_run_healthy_host_complete_outcome(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post("/api/runs", json={"host_id": "ve-de-apollo"}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["host_id"] == "ve-de-apollo"
    assert body["outcome"] == "complete"
    statuses = {item["id"]: item["status"] for item in body["items"]}
    assert statuses["main_can_bus_reachable"] == "working"
    assert statuses["expected_front_camera_connected"] == "working"


def test_run_errored_host_has_recommended_action(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post("/api/runs", json={"host_id": "ve-de-loki"}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["outcome"] == "complete"
    by_id = {item["id"]: item for item in body["items"]}
    front = by_id["expected_front_camera_connected"]
    assert front["status"] == "error"
    assert front["recommended_action_key"] is not None


def test_run_unreachable_host_returns_empty_items(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post("/api/runs", json={"host_id": "ve-de-no-fixture"}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["outcome"] == "unreachable"
    assert body["items"] == []


def test_run_unknown_host_returns_404(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    resp = client.post(
        "/api/runs", json={"host_id": "ve-de-not-in-inventory"}, headers=auth_headers
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"] == "unknown_host"


def test_run_without_x_vay_user_returns_401(client: TestClient) -> None:
    """FR-026 / R4 — missing operator identity is a hard 401, no anonymous fallback."""
    resp = client.post("/api/runs", json={"host_id": "ve-de-apollo"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "missing_operator_identity"


def test_concurrent_run_for_same_host_returns_409(
    synthetic_inventory: Path, tmp_path: Path
) -> None:
    """Two parallel POST /api/runs for the same host: the second gets 409."""
    runs_dir = tmp_path / "runs"
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "runs"
    settings = _make_settings(
        inventory_path=synthetic_inventory, runs_dir=runs_dir, fixtures_dir=fixtures_dir
    )

    import httpx

    from vayobd.app import create_app
    from vayobd.config import get_settings as _gs

    app = create_app(settings=settings)
    app.dependency_overrides[_gs] = lambda: settings

    headers = {"X-Vay-User": "concurrency.tester@vay.io"}

    async def _go() -> tuple[int, int]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://t") as c:
            t1 = asyncio.create_task(
                c.post("/api/runs", json={"host_id": "ve-de-apollo"}, headers=headers)
            )
            await asyncio.sleep(0)
            t2 = asyncio.create_task(
                c.post("/api/runs", json={"host_id": "ve-de-apollo"}, headers=headers)
            )
            r1, r2 = await asyncio.gather(t1, t2)
            return r1.status_code, r2.status_code

    code1, code2 = asyncio.run(_go())
    assert {code1, code2} == {200, 409}, (code1, code2)


def test_get_latest_endpoint_dropped_in_v1(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    """FR-028 / research R7: no GET /api/runs/latest endpoint exists in v1.

    A request to that path MUST get a 404 from the router (no route),
    not a 200 — the result view is blank-on-entry and the persisted
    record is backend-only in v1.
    """
    resp = client.get(
        "/api/runs/latest",
        params={"host_id": "ve-de-apollo"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_run_exceeding_timeout_returns_timeout_outcome(
    synthetic_inventory: Path, tmp_path: Path, auth_headers: dict[str, str]
) -> None:
    """FR-025 (T086) — exec layer respects `run_timeout_seconds`.

    Pair the slow fixture (`ve-de-saturn-slow.yaml`, sleeps 5 s) with a
    very short timeout to verify the runner cuts the run off and surfaces
    `outcome: timeout` with empty items, without making the suite slow.
    The production default is 30 s; this test exercises the same code path
    with a tighter ceiling so the assertion is fast.
    """
    runs_dir = tmp_path / "runs"
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures" / "runs"
    settings = _make_settings(
        inventory_path=synthetic_inventory,
        runs_dir=runs_dir,
        fixtures_dir=fixtures_dir,
        run_timeout_seconds=0.5,
    )
    app = create_app(settings=settings)
    from vayobd.config import get_settings

    app.dependency_overrides[get_settings] = lambda: settings

    c = TestClient(app)
    resp = c.post(
        "/api/runs",
        json={"host_id": "ve-de-saturn-slow"},
        headers=auth_headers,
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["outcome"] == "timeout"
    assert body["items"] == []
