"""Run cache — per-(operator, host) JSON persistence (T016, FR-026).

Each operator's runs live under their own slug-derived directory:
`runs/<operator-slug>/<host_id>.json`. One operator's runs are
unreachable from another operator's API surface in v1.

The persisted shape adds a server-internal `triggered_by` field which is
stripped before returning to the SPA.
"""

from __future__ import annotations

import json
from pathlib import Path

from vayobd.logging import get_logger
from vayobd.models import DiagnosticRun, OperatorIdentity

log = get_logger(__name__)


def _operator_dir(runs_dir: Path, operator: OperatorIdentity) -> Path:
    return runs_dir / operator.slug


def _run_path(runs_dir: Path, host_id: str, operator: OperatorIdentity) -> Path:
    return _operator_dir(runs_dir, operator) / f"{host_id}.json"


def write_run(
    *,
    runs_dir: Path,
    run: DiagnosticRun,
    triggered_by: OperatorIdentity,
) -> None:
    """Persist a run under the triggering operator's slug directory."""
    op_dir = _operator_dir(runs_dir, triggered_by)
    op_dir.mkdir(parents=True, exist_ok=True)
    path = _run_path(runs_dir, run.host_id, triggered_by)
    payload = run.model_dump(mode="json")
    payload["triggered_by"] = triggered_by.model_dump()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, default=str)
    tmp.replace(path)
    log.info(
        "run_persisted",
        host_id=run.host_id,
        outcome=run.outcome.value,
        operator_slug=triggered_by.slug,
    )


def read_run(
    *,
    runs_dir: Path,
    host_id: str,
    operator: OperatorIdentity,
) -> DiagnosticRun | None:
    """Return the persisted DiagnosticRun for `(operator, host_id)`, or None.

    Strips the server-internal `triggered_by` field before returning.
    Crucially, an operator's call NEVER surfaces another operator's run —
    the path lookup is scoped to `operator.slug` (FR-026).
    """
    path = _run_path(runs_dir, host_id, operator)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning(
            "run_cache_read_failed",
            host_id=host_id,
            operator_slug=operator.slug,
            error=str(exc),
        )
        return None
    raw.pop("triggered_by", None)
    return DiagnosticRun.model_validate(raw)
