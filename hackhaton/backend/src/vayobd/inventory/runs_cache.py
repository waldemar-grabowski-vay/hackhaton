"""Run cache (T016, data-model.md).

Persist most-recent run per host as JSON under VAYOBD_RUNS_DIR. The persisted
shape adds a server-internal `triggered_by` field which is stripped before
returning to the SPA.
"""

from __future__ import annotations

import json
from pathlib import Path

from vayobd.logging import get_logger
from vayobd.models import DiagnosticRun, OperatorIdentity

log = get_logger(__name__)


def _run_path(runs_dir: Path, host_id: str) -> Path:
    return runs_dir / f"{host_id}.json"


def write_run(
    *,
    runs_dir: Path,
    run: DiagnosticRun,
    triggered_by: OperatorIdentity | None = None,
) -> None:
    runs_dir.mkdir(parents=True, exist_ok=True)
    path = _run_path(runs_dir, run.host_id)
    payload = run.model_dump(mode="json")
    if triggered_by is not None:
        payload["triggered_by"] = triggered_by.model_dump()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, default=str)
    tmp.replace(path)
    log.info("run_persisted", host_id=run.host_id, outcome=run.outcome.value)


def read_run(*, runs_dir: Path, host_id: str) -> DiagnosticRun | None:
    """Return the persisted DiagnosticRun for `host_id`, or None if absent.

    Strips the server-internal `triggered_by` field before returning so the
    caller can ship the result straight to the SPA.
    """
    path = _run_path(runs_dir, host_id)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("run_cache_read_failed", host_id=host_id, error=str(exc))
        return None
    raw.pop("triggered_by", None)
    return DiagnosticRun.model_validate(raw)
