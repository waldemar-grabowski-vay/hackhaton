"""Shared pytest helpers — synthesise a tiny in-scope + out-of-scope inventory tree."""

from __future__ import annotations

from pathlib import Path

import pytest

# Default X-Vay-User header for integration tests. Production sets this via
# the SSO-terminating reverse proxy (R4); tests pass it explicitly so the
# strict 401-on-missing behaviour from FR-026 doesn't break the suite.
DEFAULT_TEST_USER = "test.operator@vay.io"
AUTH_HEADERS = {"X-Vay-User": DEFAULT_TEST_USER}


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return dict(AUTH_HEADERS)


def _write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def synthetic_inventory(tmp_path: Path) -> Path:
    """Builds a tiny inventory tree exercising every load-time filter:

      In-scope (Germany fleet only):
        org/apollo/vehicles/{ve-de-apollo,ve-de-loki,ve-de-thor}.yaml
        org/apollo/telestations/{ts-de-ber-zeus}.yaml

      Filtered out:
        - ve-be-bxl, ts-be-bxl-foo   (Belgium — FR-001b)
        - ts-de-ham-poseidon         (Hamburg — telestations restricted to Berlin)

    Returns the inventory_path (root of the checkout).
    """
    root = tmp_path / "ree-vehicle-configs"
    org = root / "org" / "apollo"
    vehicles = org / "vehicles"
    telestations = org / "telestations"

    # In-scope vehicles (Germany only)
    _write(
        vehicles / "ve-de-apollo.yaml",
        "network:\n  ve_addresses:\n    - 10.0.1.5\n",
    )
    _write(vehicles / "ve-de-loki.yaml", "")
    _write(vehicles / "ve-de-thor.yaml", "")
    # ve-de-no-fixture: in-scope host with no corresponding run fixture, so
    # FixtureExecutor returns unreachable — used by the unreachable-outcome test.
    _write(vehicles / "ve-de-no-fixture.yaml", "")
    # ve-de-saturn-slow: in-scope; paired with a sleep-heavy fixture so the
    # FR-025 30 s timeout integration test (T086) has a real host id to
    # POST against.
    _write(vehicles / "ve-de-saturn-slow.yaml", "")

    # Filtered vehicles
    _write(vehicles / "ve-be-bxl.yaml", "")     # Belgium → FR-001b
    _write(vehicles / "ve-us-01001.yaml", "")   # USA → DE-only Clarification 2026-05-07

    # In-scope telestations (Berlin only)
    _write(telestations / "ts-de-ber-zeus.yaml", "")

    # Filtered telestations
    _write(telestations / "ts-be-bxl-foo.yaml", "")       # Belgium → FR-001b
    _write(telestations / "ts-us-las-00001.yaml", "")     # USA → DE-only Clarification 2026-05-07
    _write(telestations / "ts-de-ham-poseidon.yaml", "")  # Hamburg → not Berlin

    return root
