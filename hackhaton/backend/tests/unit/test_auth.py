"""T084 — auth dependency: 401 on missing/empty/invalid X-Vay-User; slug derivation.

FR-026 / R4 — operator identity is load-bearing for run persistence
keying, so the dependency refuses to fall back to a synthetic anonymous
user. Missing or unsanitisable headers are HTTP 401.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from vayobd.api.auth import current_operator
from vayobd.api.errors import ApiError
from vayobd.app import create_app
from vayobd.models import OperatorIdentity


# --- Slug derivation (model-level) ------------------------------------------


def test_slug_lowercases_and_strips_disallowed_chars() -> None:
    op = OperatorIdentity(username="Alice.O@Vay.IO")
    # Lowercased; '@' is disallowed and replaced with '-'.
    assert op.slug == "alice.o-vay.io"


def test_slug_collapses_runs_of_disallowed_chars() -> None:
    op = OperatorIdentity(username="weird name!!!@@@here")
    # Each contiguous run of disallowed chars becomes a single '-'.
    assert op.slug == "weird-name-here"


def test_slug_strips_leading_and_trailing_punctuation() -> None:
    op = OperatorIdentity(username="...alice...")
    assert op.slug == "alice"


def test_slug_empty_after_sanitisation_raises() -> None:
    """An identity that sanitises to nothing cannot key persistence (FR-026)."""
    with pytest.raises(ValueError):
        OperatorIdentity(username="!!!")


# --- Dependency-level (HTTP) ------------------------------------------------


@pytest.fixture
def client(tmp_path) -> TestClient:
    """A real FastAPI client with no inventory / proxy — we only exercise
    the auth dependency here, so any inventory-bearing endpoint will do.
    """
    from vayobd.config import Settings, get_settings

    settings = Settings(
        inventory_path=tmp_path / "missing-on-purpose",
        inventory_meta_path=tmp_path / "inventory.meta.json",
        runs_dir=tmp_path / "runs",
    )
    app = create_app(settings=settings)
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_missing_header_returns_401(client: TestClient) -> None:
    resp = client.post("/api/runs", json={"host_id": "ve-de-apollo"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "missing_operator_identity"


def test_empty_header_returns_401(client: TestClient) -> None:
    resp = client.post(
        "/api/runs",
        json={"host_id": "ve-de-apollo"},
        headers={"X-Vay-User": "   "},
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "missing_operator_identity"


def test_unsanitisable_header_returns_401(client: TestClient) -> None:
    """A header that produces an empty slug after sanitisation is rejected."""
    resp = client.post(
        "/api/runs",
        json={"host_id": "ve-de-apollo"},
        headers={"X-Vay-User": "!!!"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_operator_identity"


def test_valid_header_resolves_to_operator() -> None:
    """Direct call to the dependency to assert it returns a usable identity."""
    op = asyncio.run(current_operator(x_vay_user="Bob.Person@vay.io"))
    assert isinstance(op, OperatorIdentity)
    assert op.username == "Bob.Person@vay.io"
    assert op.slug == "bob.person-vay.io"


def test_dependency_raises_apierror_for_missing() -> None:
    with pytest.raises(ApiError) as exc:
        asyncio.run(current_operator(x_vay_user=None))
    assert exc.value.status_code == 401
