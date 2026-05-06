"""T062 — run-cache overwrite semantics: most-recent run replaces previous."""

from __future__ import annotations

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
    loaded = read_run(runs_dir=tmp_path, host_id="ve-de-apollo")
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

    loaded = read_run(runs_dir=tmp_path, host_id="ve-de-apollo")
    assert loaded is not None
    # Most-recent run replaces previous (US2 / data-model.md).
    assert loaded.items[0].status is ItemStatus.WORKING
    assert loaded.started_at == second.started_at


def test_read_missing_returns_none(tmp_path: Path) -> None:
    assert read_run(runs_dir=tmp_path, host_id="ve-de-apollo") is None


def test_triggered_by_stripped_from_response(tmp_path: Path) -> None:
    op = OperatorIdentity(username="audited.user")
    run = _run("ve-de-apollo", when=datetime.now(UTC), status=ItemStatus.WORKING)
    write_run(runs_dir=tmp_path, run=run, triggered_by=op)

    # The persisted file MUST carry triggered_by …
    import json

    raw = json.loads((tmp_path / "ve-de-apollo.json").read_text())
    assert raw["triggered_by"] == {"username": "audited.user"}

    # … but read_run strips it before returning to the caller.
    loaded = read_run(runs_dir=tmp_path, host_id="ve-de-apollo")
    assert loaded is not None
    assert not hasattr(loaded, "triggered_by")
