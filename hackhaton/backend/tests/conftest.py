"""Shared pytest helpers — synthesise a tiny in-scope + out-of-scope inventory tree."""

from __future__ import annotations

from pathlib import Path

import pytest


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
    # ve-de-thor: in-scope but the run fixture marks it unreachable, so the
    # integration test for the unreachable outcome can hit a real DE host id.
    _write(vehicles / "ve-de-thor.yaml", "")

    # Filtered vehicles
    _write(vehicles / "ve-be-bxl.yaml", "")     # Belgium → FR-001b

    # In-scope telestations (Berlin only)
    _write(telestations / "ts-de-ber-zeus.yaml", "")

    # Filtered telestations
    _write(telestations / "ts-be-bxl-foo.yaml", "")       # Belgium → FR-001b
    _write(telestations / "ts-de-ham-poseidon.yaml", "")  # Hamburg → not Berlin

    return root
