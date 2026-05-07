"""T062 + T085 — run-cache overwrite semantics + per-operator persistence.

Per FR-026 + research R4, persisted runs live under
`runs/<operator-slug>/<host_id>.json`. One operator's runs are
unreachable from another operator's call.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from vayobd.inventory.runs_cache import read_run, write_run
from vayobd.models import (
    CheckCategory,
    DiagnosticItem,
    DiagnosticRun,
    ItemStatus,
    OperatorIdentity,
    RunOutcome,
)


def _run(host_id: str, *, when: datetime, status: ItemStatus) -> DiagnosticRun:
    return DiagnosticRun(
        host_id=host_id,
        started_at=when,
        completed_at=when + timedelta(seconds=2),
        outcome=RunOutcome.COMPLETE,
        items=[
            DiagnosticItem(
                id="main_can_bus_reachable",
                name_key="item.main_can_bus_reachable.name",
                description_key=None,
                category=CheckCategory.COMMUNICATION,
                status=status,
                recommended_action_key=(
                    "item.main_can_bus_reachable.action"
                    if status is ItemStatus.ERROR
                    else None
                ),
                raw_detail="x",
            )
        ],
    )


def test_write_then_read_round_trip(tmp_path: Path) -> None:
    op = OperatorIdentity(username="ops")
    run = _run("ve-de-apollo", when=datetime.now(UTC), status=ItemStatus.WORKING)
    write_run(runs_dir=tmp_path, run=run, triggered_by=op)
    loaded = read_run(runs_dir=tmp_path, host_id="ve-de-apollo", operator=op)
    assert loaded is not None
    assert loaded.host_id == run.host_id
    assert loaded.items[0].status is ItemStatus.WORKING


def test_second_write_overwrites_first(tmp_path: Path) -> None:
    op = OperatorIdentity(username="ops")
    t0 = datetime.now(UTC)
    first = _run("ve-de-apollo", when=t0, status=ItemStatus.ERROR)
    second = _run("ve-de-apollo", when=t0 + timedelta(minutes=5), status=ItemStatus.WORKING)

    write_run(runs_dir=tmp_path, run=first, triggered_by=op)
    write_run(runs_dir=tmp_path, run=second, triggered_by=op)

    loaded = read_run(runs_dir=tmp_path, host_id="ve-de-apollo", operator=op)
    assert loaded is not None
    # Most-recent run replaces previous (US2 / data-model.md).
    assert loaded.items[0].status is ItemStatus.WORKING
    assert loaded.started_at == second.started_at


def test_read_missing_returns_none(tmp_path: Path) -> None:
    op = OperatorIdentity(username="ops")
    assert read_run(runs_dir=tmp_path, host_id="ve-de-apollo", operator=op) is None


def test_triggered_by_persisted_then_stripped_on_read(tmp_path: Path) -> None:
    op = OperatorIdentity(username="audited.user")
    run = _run("ve-de-apollo", when=datetime.now(UTC), status=ItemStatus.WORKING)
    write_run(runs_dir=tmp_path, run=run, triggered_by=op)

    # The persisted file MUST carry triggered_by under the operator's slug dir …
    persisted_path = tmp_path / op.slug / "ve-de-apollo.json"
    raw = json.loads(persisted_path.read_text())
    assert raw["triggered_by"]["username"] == "audited.user"
    assert raw["triggered_by"]["slug"] == op.slug

    # … but read_run strips it before returning.
    loaded = read_run(runs_dir=tmp_path, host_id="ve-de-apollo", operator=op)
    assert loaded is not None
    assert not hasattr(loaded, "triggered_by")


def test_runs_are_scoped_per_operator(tmp_path: Path) -> None:
    """T085 / FR-026 — one operator's runs MUST NOT be visible to another.

    Two operators write a run for the same host. Each must:
      - see only their own run via `read_run(operator=…)`,
      - have a distinct on-disk file under their own slug directory.
    """
    alice = OperatorIdentity(username="alice@vay.io")
    bob = OperatorIdentity(username="bob@vay.io")
    assert alice.slug != bob.slug, "test setup: slugs must differ"

    t0 = datetime.now(UTC)
    alice_run = _run("ve-de-apollo", when=t0, status=ItemStatus.WORKING)
    bob_run = _run("ve-de-apollo", when=t0 + timedelta(minutes=1), status=ItemStatus.ERROR)

    write_run(runs_dir=tmp_path, run=alice_run, triggered_by=alice)
    write_run(runs_dir=tmp_path, run=bob_run, triggered_by=bob)

    # Two distinct files under two distinct operator directories.
    alice_path = tmp_path / alice.slug / "ve-de-apollo.json"
    bob_path = tmp_path / bob.slug / "ve-de-apollo.json"
    assert alice_path.exists()
    assert bob_path.exists()
    assert alice_path != bob_path

    # Each operator only sees their own run.
    alice_loaded = read_run(runs_dir=tmp_path, host_id="ve-de-apollo", operator=alice)
    bob_loaded = read_run(runs_dir=tmp_path, host_id="ve-de-apollo", operator=bob)
    assert alice_loaded is not None
    assert bob_loaded is not None
    assert alice_loaded.items[0].status is ItemStatus.WORKING
    assert bob_loaded.items[0].status is ItemStatus.ERROR

    # And — the kernel of FR-026 — Alice's run is NEVER returned to Bob and vice versa.
    # The path lookup is keyed by operator.slug; if it leaked, the wrong status would surface.
    assert alice_loaded.started_at != bob_loaded.started_at
