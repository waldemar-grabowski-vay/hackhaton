"""GET /api/host/{host_id}/versions — host-detail surface.

Reads three deployed versions off a host (vDrive manifest, vREECU,
SEC) via the rust engine's existing `ree-debug-cli report` path,
maps the engine's per-check rows to per-field `VersionField`
records with `match` / `drift` / `no-manifest` / `unavailable`
verdicts, and serves the result with a 60 s per-host TTL cache plus
an `?fresh=true` override.

See:
- spec.md       — `/specs/007-ts-diag-restore-version-pull/spec.md`
- data-model.md — wire shapes (VersionVerdict, VersionField, …)
- contracts/http-api.md       — endpoint surface, caching, errors
- contracts/engine-mapping.md — CheckEntry → version-field rules
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator

from vayobd.api.auth import current_operator
from vayobd.api.errors import ApiError
from vayobd.checks.executor import Executor
from vayobd.checks.runner import RunInProgressError, execute_run
from vayobd.config import Settings, get_settings
from vayobd.dependencies import _resolve_ree_cli_bin, get_executor
from vayobd._internal.version_cache import VersionCache
from vayobd.inventory.loader import load_inventory
from vayobd.logging import get_logger
from vayobd.models import (
    DiagnosticRun,
    EngineCheckEntry,
    EngineReport,
    EngineStatus,
    Host,
    RunOutcome,
)

log = get_logger(__name__)

router = APIRouter(tags=["host-versions"])

# Wall-clock cap on a single engine invocation. Matches contracts/http-api.md
# "Engine invocation" — SC-002 allows 10s, this gives 5s headroom.
ENGINE_TIMEOUT_SECONDS = 15.0

# Module-level singleton — single-user desktop deployment. Tests inject
# their own cache via `set_cache_for_tests`.
_cache: VersionCache[HostVersionsResponse] = None  # type: ignore[assignment]


def _get_cache() -> VersionCache[HostVersionsResponse]:
    global _cache
    if _cache is None:
        _cache = VersionCache[HostVersionsResponse]()
    return _cache


def set_cache_for_tests(cache: VersionCache[HostVersionsResponse]) -> None:
    """Override the module-level cache. Tests only."""
    global _cache
    _cache = cache


# --- Wire models ------------------------------------------------------------


class VersionVerdict(StrEnum):
    """Per-field comparison outcome against the bundled manifest."""

    MATCH = "match"
    DRIFT = "drift"
    NO_MANIFEST = "no-manifest"
    UNAVAILABLE = "unavailable"


class VersionField(BaseModel):
    """One of the three deployed versions on a host, with verdict + context."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    value: str | None = Field(
        default=None,
        description=(
            "Live version string read from the host (e.g. 'R12.3.0'). "
            "None when verdict is 'unavailable'."
        ),
    )
    verdict: VersionVerdict
    expected: str | None = Field(
        default=None,
        description="Manifest's expected value when verdict is 'drift'. None otherwise.",
    )
    reason: str | None = Field(
        default=None,
        description=(
            "Plain-language explanation when verdict is 'unavailable'. "
            "None for non-unavailable verdicts."
        ),
    )
    as_of: datetime = Field(
        description="Timestamp this value was read from the host (FR-019).",
    )

    @model_validator(mode="after")
    def _check_invariants(self) -> VersionField:
        if self.verdict == VersionVerdict.MATCH:
            if self.value is None or self.expected is not None or self.reason is not None:
                raise ValueError("match: value required; expected/reason must be null")
        elif self.verdict == VersionVerdict.DRIFT:
            if self.value is None or self.expected is None or self.reason is not None:
                raise ValueError("drift: value + expected required; reason must be null")
        elif self.verdict == VersionVerdict.NO_MANIFEST:
            if self.value is None or self.expected is not None or self.reason is not None:
                raise ValueError("no-manifest: value required; expected/reason must be null")
        elif self.verdict == VersionVerdict.UNAVAILABLE:
            if self.value is not None or self.expected is not None or self.reason is None:
                raise ValueError("unavailable: reason required; value/expected must be null")
        return self


class HostVersions(BaseModel):
    """Envelope of the three per-field records."""

    model_config = ConfigDict(extra="ignore", frozen=True)

    vdrive_manifest: VersionField
    vreecu_version: VersionField
    sec_version: VersionField


class HostVersionsResponse(BaseModel):
    """Wire shape for `GET /api/host/{id}/versions`.

    Post-008: carries both 007's version card AND the restored check
    battery (`run`). The version card is populated from the engine
    fixture rows that 007's `parse_engine_report` already extracts;
    the check battery comes from the legacy `execute_run` path that
    007 over-removed and 008 restored. Rows that go into `versions`
    are filtered out of `run.items` so the operator never sees the
    same fact twice (FR-011).
    """

    model_config = ConfigDict(extra="ignore", frozen=True)

    host: Host
    versions: HostVersions
    run: DiagnosticRun | None = None
    source: Literal["live", "unavailable"]


# Alias for forward compatibility with data-model.md naming.
HostDetailResponse = HostVersionsResponse


# --- Parsing logic ----------------------------------------------------------


# Engine row matching — keyed by the engine's stable `CheckEntry.id`
# values rather than the human-facing `name`. Names have changed over
# engine revisions (see 008 spike — the engine now emits `aurix_mcu_firmware`
# and `sec_fpga_gateware` instead of the older `aurix-firmware` / `sec-version`
# the 007 patterns were written against). Ids are stable.
_VDRIVE_ID_PATTERNS = ("vdrive_package_vs_manifest", "vdrive-package", "ree-drive")
_VREECU_ID_PATTERNS = ("aurix_mcu_firmware", "aurix_firmware", "reecu_firmware")
_SEC_ID_PATTERNS = ("sec_fpga_gateware", "sec_version", "gateway_firmware")


def _find_row(report: EngineReport, id_patterns: tuple[str, ...]) -> EngineCheckEntry | None:
    """Return the first CheckEntry whose id matches any of `id_patterns`.

    Match is case-insensitive substring against `entry.id`. Falls back
    to a name-substring scan if no id match is found — covers older
    engine revisions whose ids were less consistent.
    """
    needles = tuple(p.lower() for p in id_patterns)
    for entry in report.checks:
        lid = entry.id.lower()
        if any(p in lid for p in needles):
            return entry
    # Legacy fallback: scan names with the same needles.
    for entry in report.checks:
        lname = entry.name.lower()
        if any(p.replace("_", " ") in lname for p in needles):
            return entry
    return None


_TAIL_RE = re.compile(r"\(([^()]*)\)")
_EXPECTS_RE = re.compile(r"(?:manifest\s+)?expects\s+([^\s,;…]+)", re.IGNORECASE)
# Engine emits `(sha <actual> ≠ manifest <expected>)` for vDrive drift
# instead of "expects" notation. Match the expected SHA after `≠ manifest`
# (or its ASCII variant `!= manifest`).
_NOT_EQUAL_MANIFEST_RE = re.compile(
    r"(?:≠|!=)\s*manifest\s+([^\s,;]+)", re.IGNORECASE
)


def _split_value_and_tail(text: str) -> tuple[str, str | None]:
    """Split `'<value> (<tail>)'` into (`value`, `tail`).

    The engine writes its summary to `raw_detail` in shapes like:
      - "R 4.1.1 (matches manifest)"            → ("R 4.1.1", "matches manifest")
      - "12.3.0 (manifest expects 12.4.0)"      → ("12.3.0", "manifest expects 12.4.0")
      - "3af76e30 (no manifest available …)"    → ("3af76e30", "no manifest available …")
      - "R 4.1.1"  (no manifest at all)         → ("R 4.1.1", None)
      - "ssh exit Some(255)"  (failure)         → ("ssh exit Some(255)", None) — caller flips to unavailable

    Strips an optional "label:" prefix (legacy engine output may include
    "vDrive package vs manifest: R12.3.0 (matches manifest)").
    """
    head = text
    if ":" in head and not head.startswith("ssh"):
        # Don't split "ssh exit Some(255)" — that ":" isn't a label boundary.
        head = head.split(":", 1)[1]
    head = head.strip()

    tail_match = _TAIL_RE.search(head)
    if tail_match is None:
        return head, None
    value = head[: tail_match.start()].strip()
    tail = tail_match.group(1).strip()
    return value, tail


def _verdict_from_entry(entry: EngineCheckEntry, *, missing_reason: str) -> tuple[VersionVerdict, str | None]:
    """Classify the row's verdict + (for unavailable) the operator-facing reason.

    The verdict-bearing phrase lives in `raw_detail` (where the engine puts
    summaries like "R 4.1.1 (matches manifest)"), not in `name` (which is
    the planned-row label like "SEC FPGA gateware").
    """
    haystack = (entry.raw_detail or entry.name).lower()
    if entry.status == EngineStatus.FAIL:
        return VersionVerdict.UNAVAILABLE, _humanise_fail_reason(entry)
    if "matches manifest" in haystack:
        return VersionVerdict.MATCH, None
    if "manifest expects" in haystack or "≠ manifest" in haystack or "!= manifest" in haystack:
        return VersionVerdict.DRIFT, None
    if "no manifest available" in haystack:
        return VersionVerdict.NO_MANIFEST, None
    if entry.status == EngineStatus.PASS:
        # Healthy row with no manifest comparison embedded — treat as match
        # (the engine's "this is fine" intent).
        return VersionVerdict.MATCH, None
    # Warn without a known phrase — log + fall through to no-manifest.
    log.warning(
        "host_versions.unrecognised_warn_row",
        extra={"entry_id": entry.id, "entry_name": entry.name, "raw_detail": entry.raw_detail},
    )
    return VersionVerdict.NO_MANIFEST, None


def _humanise_fail_reason(entry: EngineCheckEntry) -> str:
    """Reduce engine Fail output to one operator-facing line (research § 4)."""
    raw = (entry.raw_detail or "").lower()
    name = entry.name.lower()

    if "ssh error" in raw or "ssh ok but" not in raw and "ssh" in raw and "fail" in raw:
        # Genuine SSH transport failure.
        if "ssh error" in raw:
            return "couldn't reach the host over SSH"
    if "dpkg failed" in raw or "dpkg-query" in raw:
        if "no packages found" in raw or "not installed" in raw:
            if "sec" in name:
                return "SEC package not installed on this host"
            if "vdrive" in name or "ree-drive" in name:
                return "vDrive package not installed on this host"
            return "package not installed on this host"
        return "package query failed on the host"
    if "not installed" in raw:
        return "package not installed on this host"
    if "candump" in raw:
        # SEC + Aurix versions are decoded from CAN frames via candump.
        # If candump fails the engine can't read those versions either.
        if "sec" in name:
            return "couldn't read SEC version — no CAN frames received"
        if "aurix" in name or "reecu" in name:
            return "couldn't read REECU firmware — no CAN frames received"
        return "couldn't read this version — no CAN frames received"
    # Catch-all — short and direct, never raw engine output.
    return "engine couldn't read this version"


def _extract_expected(tail: str | None) -> str | None:
    """Pull `<X>` out of any of the engine's drift-bearing tail forms:
      - `expects <X>` / `manifest expects <X>`     ← compose_version_summary
      - `≠ manifest <X>` / `!= manifest <X>`       ← decide_vdrive_drift (sha ≠ manifest …)
    Returns None when no expected value is parseable.
    """
    if not tail:
        return None
    # Try the explicit "expects" form first (compose_version_summary).
    match = _EXPECTS_RE.search(tail)
    if match:
        return match.group(1).strip().rstrip("…")
    # Fall through to the vDrive drift form (`≠ manifest <prefix>`).
    match = _NOT_EQUAL_MANIFEST_RE.search(tail)
    if match:
        return match.group(1).strip()
    return None


def _build_field(
    entry: EngineCheckEntry | None,
    *,
    field_name: str,
    missing_reason: str,
    as_of: datetime,
) -> VersionField:
    if entry is None:
        return VersionField(
            value=None,
            verdict=VersionVerdict.UNAVAILABLE,
            expected=None,
            reason=missing_reason,
            as_of=as_of,
        )

    verdict, fail_reason = _verdict_from_entry(entry, missing_reason=missing_reason)

    if verdict == VersionVerdict.UNAVAILABLE:
        return VersionField(
            value=None,
            verdict=VersionVerdict.UNAVAILABLE,
            expected=None,
            reason=fail_reason or missing_reason,
            as_of=as_of,
        )

    # Parse the value-bearing string. Engine puts the summary in `raw_detail`
    # (e.g. "R 4.1.1 (matches manifest)"); `name` is just the planned-row
    # label ("SEC FPGA gateware"). Fall back to name if raw_detail is empty.
    text_with_value = entry.raw_detail or entry.name
    value, tail = _split_value_and_tail(text_with_value)
    expected = _extract_expected(tail) if verdict == VersionVerdict.DRIFT else None
    # Defensive: drift verdict requires `expected` (model invariant). If the
    # engine emitted a drift signal but in a form we don't yet parse, downgrade
    # to no-manifest so the page still renders the actual value instead of
    # 500-ing. Log the wording so we can extend the patterns.
    if verdict == VersionVerdict.DRIFT and not expected:
        log.warning(
            "host_versions.drift_expected_unparseable",
            extra={
                "entry_id": entry.id,
                "entry_name": entry.name,
                "raw_detail": entry.raw_detail,
                "field": field_name,
            },
        )
        verdict = VersionVerdict.NO_MANIFEST
        expected = None
    return VersionField(
        value=value or None,
        verdict=verdict,
        expected=expected,
        reason=None,
        as_of=as_of,
    )


def parse_engine_report(report: EngineReport, *, as_of: datetime, host_type: str) -> HostVersions:
    """Map an EngineReport to the three per-field version records.

    `host_type` is the inventory-resolved host type (vehicle / telestation);
    drives the "SEC not applicable to vehicle hosts" path per
    contracts/engine-mapping.md.
    """
    vdrive_row = _find_row(report, _VDRIVE_ID_PATTERNS)
    vreecu_row = _find_row(report, _VREECU_ID_PATTERNS)
    sec_row = _find_row(report, _SEC_ID_PATTERNS)

    vdrive = _build_field(
        vdrive_row,
        field_name="vdrive_manifest",
        missing_reason="host didn't report vDrive version",
        as_of=as_of,
    )
    vreecu = _build_field(
        vreecu_row,
        field_name="vreecu_version",
        missing_reason="host didn't report vREECU version",
        as_of=as_of,
    )
    if sec_row is None and host_type == "vehicle":
        sec_missing_reason = "SEC version not applicable to vehicle hosts"
    else:
        sec_missing_reason = "host didn't report SEC version"
    sec = _build_field(
        sec_row,
        field_name="sec_version",
        missing_reason=sec_missing_reason,
        as_of=as_of,
    )

    return HostVersions(vdrive_manifest=vdrive, vreecu_version=vreecu, sec_version=sec)


# --- Engine invocation ------------------------------------------------------


class EngineUnavailable(Exception):
    """Engine subprocess failed; produces an all-unavailable response."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


async def _invoke_engine(host_id: str, settings: Settings) -> EngineReport:
    """Shell out to `ree-debug-cli report --host <id> --inventory <clone> --json`.

    Raises EngineUnavailable on every non-success path. Never returns
    None and never lets a non-zero exit slip through.
    """
    bin_path = _resolve_ree_cli_bin(settings)
    if bin_path is None:
        raise EngineUnavailable("engine binary (ree-debug-cli) not found on PATH")

    # Inventory file lives at <clone>/org/vay/inventory.yaml; the engine
    # expects the clone root, so climb back up if `inventory_path` already
    # points at the YAML.
    inv = settings.inventory_path
    if inv.is_file() and inv.name == "inventory.yaml":
        clone_root = inv.parent.parent.parent
    else:
        clone_root = inv

    cmd = [
        str(bin_path),
        "report",
        "--host",
        host_id,
        "--inventory",
        str(clone_root),
        "--json",
    ]
    log.info(
        "host_versions.engine_invoke",
        extra={"host_id": host_id, "bin": str(bin_path)},
    )
    # 009: tell the engine where to find the release manifest. The engine
    # falls back to `~/GitHub/system-release-deployment/release-configs.yaml`
    # only when this env var is unset, so vayobd-managed deployments stay
    # decoupled from any user's `~/GitHub/` layout.
    env = dict(os.environ)
    env["RELEASE_CONFIGS_PATH"] = str(settings.release_configs_path)

    start = datetime.now(UTC)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=ENGINE_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            log.warning(
                "host_versions.engine_timeout",
                extra={
                    "host_id": host_id,
                    "duration_ms": int(
                        (datetime.now(UTC) - start).total_seconds() * 1000
                    ),
                },
            )
            raise EngineUnavailable(
                "engine timed out reading versions for this host"
            ) from None
    except FileNotFoundError:
        raise EngineUnavailable("engine binary missing") from None

    duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
    if proc.returncode != 0:
        # Strip stderr to one short line — research § 4 / FR-015 rules out
        # leaking raw stderr to operators or log lines.
        first_err_line = (stderr or b"").decode("utf-8", errors="replace").splitlines()
        summary = first_err_line[0][:200] if first_err_line else ""
        log.warning(
            "host_versions.engine_parse_error",
            extra={
                "host_id": host_id,
                "exit_code": proc.returncode,
                "summary": summary,
                "duration_ms": duration_ms,
            },
        )
        raise EngineUnavailable(
            f"engine exited with code {proc.returncode}"
        )

    try:
        report = EngineReport.model_validate_json(stdout or b"{}")
    except Exception as exc:  # noqa: BLE001 — malformed engine output
        log.warning(
            "host_versions.engine_parse_error",
            extra={"host_id": host_id, "duration_ms": duration_ms, "exc": type(exc).__name__},
        )
        raise EngineUnavailable("engine output was not parseable") from exc

    log.info(
        "host_versions.engine_done",
        extra={
            "host_id": host_id,
            "exit_code": proc.returncode,
            "duration_ms": duration_ms,
            "checks": len(report.checks),
        },
    )
    return report


# --- Collector --------------------------------------------------------------


def _all_unavailable(reason: str, as_of: datetime) -> HostVersions:
    """Build a three-unavailable HostVersions with the same reason on each cell."""
    fld = lambda: VersionField(  # noqa: E731 — small local helper
        value=None,
        verdict=VersionVerdict.UNAVAILABLE,
        expected=None,
        reason=reason,
        as_of=as_of,
    )
    return HostVersions(vdrive_manifest=fld(), vreecu_version=fld(), sec_version=fld())


def _derive_source(versions: HostVersions) -> Literal["live", "unavailable"]:
    verdicts = (
        versions.vdrive_manifest.verdict,
        versions.vreecu_version.verdict,
        versions.sec_version.verdict,
    )
    if all(v == VersionVerdict.UNAVAILABLE for v in verdicts):
        return "unavailable"
    return "live"


# IDs of checks that the engine's `report` subcommand emits which already
# feed 007's version card. Excluded from `run.items` so the operator never
# sees the same fact twice (FR-011). Match by id substring against the
# engine's stable ids (vdrive_package_vs_manifest, aurix_mcu_firmware,
# sec_fpga_gateware, reecu_hardware_rev, ts_sec_state_0x050, …).
_REECU_OWNED_ID_PATTERNS = (
    "vdrive_package_vs_manifest",
    "ree_drive",
    "ree-drive",
    "aurix_mcu_firmware",
    "aurix_firmware",
    "reecu_firmware",
    "sec_fpga_gateware",
    "sec_version",
    "gateway_firmware",
)

# IDs of checks the operator finds low-signal on testbeds — cloud-side
# probes that fail on isolated testbeds without giving the operator any
# diagnostic value about the host itself. Filtered out of `run.items` so
# they don't clutter the "Needs attention" group.
_NOISE_ID_PATTERNS = (
    "api_prod_reeapis_com",
    "lobby_prod_reeapis_com",
    "tdms_prod_reeapis_com",
    "cloud_telemetry_prod_reeapis_com",
)


def _filter_reecu_owned_items(run: DiagnosticRun) -> DiagnosticRun:
    """Drop items the operator should not see in `run.items`:
       - REECU/vDrive/SEC rows (they're already in the version card; FR-011).
       - Cloud-side reeapis.com probes (low-signal on testbeds).
    """
    drop_patterns = _REECU_OWNED_ID_PATTERNS + _NOISE_ID_PATTERNS
    kept = [
        item
        for item in run.items
        if not any(p in item.id.lower() for p in drop_patterns)
    ]
    return run.model_copy(update={"items": kept})


async def _run_check_battery(host: Host, settings: Settings) -> DiagnosticRun | None:
    """Run the restored check battery for `host`.

    Returns a DiagnosticRun on success, None when the battery can't be
    run at all (e.g., no executor available). Per-check failures are
    captured inside the run as `error`/`warning` items — they don't
    surface as None.
    """
    try:
        executor = get_executor(settings)
    except Exception as exc:  # noqa: BLE001 — fail-soft; battery is non-critical
        log.warning("host_versions.executor_unavailable", extra={"host_id": host.id, "exc": str(exc)})
        return None
    try:
        run = await execute_run(
            host=host,
            executor=executor,
            timeout_seconds=settings.run_timeout_seconds,
        )
    except RunInProgressError:
        log.info("host_versions.run_in_progress", extra={"host_id": host.id})
        return None
    return _filter_reecu_owned_items(run)


async def _collect_versions(host: Host, settings: Settings) -> HostVersionsResponse:
    as_of = datetime.now(UTC)
    # Run the two pipelines in parallel — Clarification Q1 + FR-010.
    engine_task = asyncio.create_task(_invoke_engine(host.id, settings))
    battery_task = asyncio.create_task(_run_check_battery(host, settings))

    try:
        report = await engine_task
        versions = parse_engine_report(report, as_of=as_of, host_type=host.type)
        engine_failed = False
    except EngineUnavailable as exc:
        versions = _all_unavailable(exc.reason, as_of)
        engine_failed = True

    # The check battery is independent; await it even if the engine failed.
    try:
        run = await battery_task
    except Exception as exc:  # noqa: BLE001 — battery failure shouldn't break the page
        log.warning("host_versions.battery_failed", extra={"host_id": host.id, "exc": str(exc)})
        run = None

    if engine_failed and run is None:
        source: Literal["live", "unavailable"] = "unavailable"
    else:
        source = _derive_source(versions) if not engine_failed else "live" if run else "unavailable"
        # If the engine failed but the battery succeeded, source is still "live"
        # because the operator has SOMETHING on the page (the check battery rows).
        if run is not None and engine_failed:
            source = "live"

    return HostVersionsResponse(host=host, versions=versions, run=run, source=source)


# --- Route ------------------------------------------------------------------


def _parse_fresh_query(raw: str | None) -> bool:
    if raw is None:
        return False
    if raw == "true":
        return True
    raise ApiError(
        status_code=status.HTTP_400_BAD_REQUEST,
        error="bad_query",
        message_key="host_versions.bad_query",
    )


@router.get("/host/{host_id}/versions")
async def get_host_versions(
    host_id: str,
    fresh: str | None = Query(default=None, description="Pass `true` to bypass the TTL cache."),
    _operator: object = Depends(current_operator),
    settings: Settings = Depends(get_settings),
) -> HostVersionsResponse:
    bypass_cache = _parse_fresh_query(fresh)

    inventory = load_inventory(settings.inventory_path)
    if inventory is None:
        raise ApiError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error="inventory_unavailable",
            message_key="inventory.empty.body",
        )
    host = next((h for h in inventory.hosts if h.id == host_id), None)
    if host is None:
        raise ApiError(
            status_code=status.HTTP_404_NOT_FOUND,
            error="host_not_found",
            message_key="host.not_found",
        )

    cache = _get_cache()
    if bypass_cache:
        cache.invalidate(host_id)
    else:
        cached = cache.get(host_id)
        if cached is not None:
            log.info(
                "host_versions.engine_invoke",
                extra={"host_id": host_id, "fresh": False, "cache_hit": True},
            )
            return cached

    response = await _collect_versions(host, settings)
    cache.set(host_id, response)
    return response
