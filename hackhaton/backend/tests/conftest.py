"""Shared pytest helpers — synthesise a tiny Ansible-style inventory.

002 / FR-013: the inventory is now the combined `org/vay/inventory.yaml`
file the operator's `ree-vehicle-configs` clone holds (matching what
ree-debug-tui has always read), not the 001-style per-folder walker.
"""

from __future__ import annotations

import textwrap
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


@pytest.fixture
def synthetic_inventory(tmp_path: Path) -> Path:
    """Build a tiny Ansible-style inventory exercising every load-time filter.

    In-scope (Germany only):
      vehicles:    ve-de-apollo, ve-de-loki, ve-de-thor, ve-de-saturn-slow
      telestations: ts-de-ber-zeus

    Filtered out:
      - ve-be-bxl, ts-be-bxl-foo            (Belgium — FR-001b)
      - ve-us-01001, ts-us-las-00001        (USA — Clarification 2026-05-07)
      - ts-de-ham-poseidon                  (Hamburg — telestations restricted to Berlin)

    Returns the **clone root** path. The loader appends
    `org/vay/inventory.yaml` itself.
    """
    root = tmp_path / "ree-vehicle-configs"
    yaml_path = root / "org" / "vay" / "inventory.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)

    # Hamburg telestation gets a city slug the loader doesn't accept (telestations
    # are scoped to Berlin); it appears under the right group but the loader
    # logic drops it. We emit it here so tests can assert that the filter works.
    yaml_path.write_text(
        textwrap.dedent(
            """
            all:
              children:
                telestations:
                  hosts:
                    ts-de-ber-zeus:
                      ansible_host: 192.168.60.2
                    ts-be-bxl-foo:
                      ansible_host: 10.10.0.1
                    ts-us-las-00001:
                      ansible_host: 10.20.0.1
                    ts-de-ham-poseidon:
                      ansible_host: 10.30.0.1
                vehicles:
                  hosts:
                    ve-de-apollo:
                      ansible_host: 10.0.1.5
                    ve-de-loki:
                      ansible_host: 10.0.2.5
                    ve-de-thor:
                      ansible_host: 10.0.3.5
                    ve-de-saturn-slow:
                      ansible_host: 10.0.4.5
                    ve-de-no-fixture:
                      ansible_host: 10.0.5.5
                    ve-be-bxl:
                      ansible_host: 10.0.99.1
                    ve-us-01001:
                      ansible_host: 10.0.99.2
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    return root
