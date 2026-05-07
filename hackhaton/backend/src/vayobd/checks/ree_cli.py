"""ReeCliExecutor (T034 / FR-003 / FR-004a / FR-008).

Subprocess wrapper around `engine/target/release/ree-debug-cli` —
the Rust CLI binary that drives the in-monorepo `ree-debug-engine`
library. Selected when `VAYOBD_EXECUTOR=ree`.

Lifecycle (research.md R6):
- Spawn `ree-debug-cli report --host <id> --inventory <path> --json`.
- `asyncio.wait_for(...)` with the configured `run_timeout_seconds`.
- On timeout: SIGTERM, 2 s grace, then SIGKILL. Outcome → TIMEOUT.
- Stderr captured separately; emitted only on non-zero exit (PII-scrubbed).
- Stdout parsed via Pydantic into `EngineReport`; mapped to
  `DiagnosticItem`s (Pass→working / Warn→warning / Fail→error per
  FR-004a).
"""

from __future__ import annotations

import asyncio
import json
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pydantic import ValidationError

from vayobd.checks.executor import Executor, ExecutorResult, ItemResult
from vayobd.logging import get_logger
from vayobd.models import (
    CheckCategory,
    EngineReport,
    EngineStatus,
    Host,
    ItemStatus,
    RunOutcome,
)

log = get_logger(__name__)


_ENGINE_TO_ITEM_STATUS: dict[EngineStatus, ItemStatus] = {
    EngineStatus.PASS: ItemStatus.WORKING,
    EngineStatus.WARN: ItemStatus.WARNING,
    EngineStatus.FAIL: ItemStatus.ERROR,
}


@dataclass(frozen=True)
class ReeCliConfig:
    binary: Path
    inventory_path: Path  # operator's ree-vehicle-configs clone root
    sigterm_grace_seconds: float = 2.0


class ReeCliExecutor(Executor):
    """Production-default executor (002 / FR-001).

    The Python side is intentionally thin: arg construction, signal
    handling, JSON parse, status mapping. All diagnostic logic lives
    in the Rust engine library.
    """

    # 002 catalog rebuild (T039) lands later — until then, items render
    # with their engine-derived id as the operator-visible name. Keep a
    # placeholder mapping from engine check id to a default category so
    # the Pydantic DiagnosticItem validator passes.
    _DEFAULT_CATEGORY: ClassVar[CheckCategory] = CheckCategory.COMMUNICATION

    def __init__(self, config: ReeCliConfig, run_timeout_seconds: float) -> None:
        self._config = config
        self._timeout = run_timeout_seconds

    async def run(self, host: Host) -> ExecutorResult:
        cmd = [
            str(self._config.binary),
            "report",
            "--host",
            host.id,
            "--inventory",
            str(self._config.inventory_path),
            "--json",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except TimeoutError:
            log.warning(
                "ree_cli_timeout",
                host_id=host.id,
                timeout_seconds=self._timeout,
            )
            await self._terminate(proc)
            return ExecutorResult(outcome=RunOutcome.TIMEOUT, items=[])

        exit_code = proc.returncode
        if exit_code != 0:
            log.warning(
                "ree_cli_nonzero_exit",
                host_id=host.id,
                exit_code=exit_code,
                stderr_tail=_tail(stderr),
            )
            return ExecutorResult(outcome=RunOutcome.UNREACHABLE, items=[])

        try:
            payload = json.loads(stdout.decode("utf-8"))
            report = EngineReport.model_validate(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
            log.warning(
                "ree_cli_parse_failed",
                host_id=host.id,
                error=str(exc),
                stdout_tail=_tail(stdout),
            )
            return ExecutorResult(outcome=RunOutcome.UNREACHABLE, items=[])

        if report.host_id != host.id:
            log.warning(
                "ree_cli_host_id_mismatch",
                expected=host.id,
                received=report.host_id,
            )

        items = [
            ItemResult(
                id=entry.id,
                status=_ENGINE_TO_ITEM_STATUS[entry.status],
                raw_detail=entry.raw_detail,
            )
            for entry in report.checks
        ]

        outcome = report.outcome
        return ExecutorResult(outcome=outcome, items=items)

    async def _terminate(self, proc: asyncio.subprocess.Process) -> None:
        """SIGTERM → grace → SIGKILL — research.md R6."""
        if proc.returncode is not None:
            return
        try:
            proc.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(proc.wait(), timeout=self._config.sigterm_grace_seconds)
            return
        except TimeoutError:
            pass
        try:
            proc.kill()
        except ProcessLookupError:
            return
        try:
            await proc.wait()
        except Exception:  # pragma: no cover - defensive
            pass


def _tail(data: bytes, max_chars: int = 500) -> str:
    text = data.decode("utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    return "…" + text[-max_chars:]
