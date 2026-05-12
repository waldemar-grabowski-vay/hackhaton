"""Unit tests — engine-output parser for 007's host-versions endpoint.

Locks in the substring-match rules in `contracts/engine-mapping.md`
against the two recorded engine fixtures plus synthetic edge cases.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vayobd.api.host_versions import (
    VersionVerdict,
    parse_engine_report,
)
from vayobd.models import EngineCheckEntry, EngineReport, EngineStatus

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "engine_reports"


def _load(name: str) -> EngineReport:
    return EngineReport.model_validate_json((FIXTURE_DIR / name).read_text())


def _now() -> datetime:
    return datetime(2026, 5, 11, 14, 5, 0, tzinfo=UTC)


# --- Real fixtures ----------------------------------------------------------


def test_ts_host_drift_match_unavailable_triple() -> None:
    report = _load("ts_host_full.json")
    versions = parse_engine_report(report, as_of=_now(), host_type="telestation")

    assert versions.vdrive_manifest.verdict == VersionVerdict.DRIFT
    assert versions.vdrive_manifest.value == "R12.3.0"
    assert versions.vdrive_manifest.expected == "R12.4.0"
    assert versions.vdrive_manifest.reason is None

    assert versions.vreecu_version.verdict == VersionVerdict.MATCH
    # Engine prefixes the firmware version with the build_type ("R" for
    # release, "D" for debug, …) — value preserves it verbatim.
    assert versions.vreecu_version.value == "R 8.5.3"
    assert versions.vreecu_version.expected is None

    assert versions.sec_version.verdict == VersionVerdict.UNAVAILABLE
    assert versions.sec_version.value is None
    assert versions.sec_version.reason is not None
    assert "SEC" in versions.sec_version.reason or "package" in versions.sec_version.reason


def test_ve_host_match_drift_not_applicable_triple() -> None:
    report = _load("ve_host_full.json")
    versions = parse_engine_report(report, as_of=_now(), host_type="vehicle")

    assert versions.vdrive_manifest.verdict == VersionVerdict.MATCH
    assert versions.vdrive_manifest.value == "R12.4.0"

    assert versions.vreecu_version.verdict == VersionVerdict.DRIFT
    assert versions.vreecu_version.value == "R 8.6.0"  # build_type prefix preserved
    assert versions.vreecu_version.expected == "8.5.3"

    # VE planned-rows omit SEC entirely — should surface as unavailable
    # with the "not applicable to vehicle hosts" reason.
    assert versions.sec_version.verdict == VersionVerdict.UNAVAILABLE
    assert versions.sec_version.reason is not None
    assert "vehicle" in versions.sec_version.reason.lower()


# --- Synthetic edge cases ---------------------------------------------------


def _report(host_type: str = "telestation", checks: list[EngineCheckEntry] | None = None) -> EngineReport:
    """Build a minimal valid EngineReport for verdict-classification tests."""
    return EngineReport.model_validate(
        {
            "schema": "ree-debug-engine",
            "version": "0.0.0+test",
            "host_id": "ts-de-ber-00000",
            "host_type": host_type,
            "started_at": "2026-05-11T14:00:00Z",
            "completed_at": "2026-05-11T14:00:01Z",
            "outcome": "complete",
            "checks": [c.model_dump() for c in (checks or [])],
        }
    )


def _entry(name: str, status: EngineStatus, *, id_: str = "x", raw: str | None = None) -> EngineCheckEntry:
    return EngineCheckEntry(id=id_, name=name, status=status, raw_detail=raw, duration_ms=10)


def test_no_manifest_verdict() -> None:
    report = _report(
        checks=[
            _entry(
                "vDrive package vs manifest",
                EngineStatus.WARN,
                id_="vdrive_package_vs_manifest",
                raw="R12.3.0 (no manifest available — check ~/GitHub/system-release-deployment)",
            ),
        ]
    )
    versions = parse_engine_report(report, as_of=_now(), host_type="telestation")
    assert versions.vdrive_manifest.verdict == VersionVerdict.NO_MANIFEST
    assert versions.vdrive_manifest.value == "R12.3.0"


def test_missing_row_yields_unavailable_with_didnt_report_reason() -> None:
    report = _report(checks=[])  # no rows at all
    versions = parse_engine_report(report, as_of=_now(), host_type="telestation")
    assert versions.vdrive_manifest.verdict == VersionVerdict.UNAVAILABLE
    assert versions.vdrive_manifest.reason == "host didn't report vDrive version"
    assert versions.vreecu_version.verdict == VersionVerdict.UNAVAILABLE
    assert versions.sec_version.verdict == VersionVerdict.UNAVAILABLE


def test_vdrive_not_installed_fail_reason() -> None:
    report = _report(
        checks=[
            _entry(
                "vDrive package vs manifest",
                EngineStatus.FAIL,
                id_="vdrive_package_vs_manifest",
                raw="dpkg-query: no packages found matching ree-drive-telestation",
            ),
        ]
    )
    versions = parse_engine_report(report, as_of=_now(), host_type="telestation")
    assert versions.vdrive_manifest.verdict == VersionVerdict.UNAVAILABLE
    assert versions.vdrive_manifest.reason is not None
    assert "vDrive" in versions.vdrive_manifest.reason or "not installed" in versions.vdrive_manifest.reason


def test_sha_match_pass_is_match() -> None:
    report = _report(
        checks=[
            _entry(
                "vDrive package vs manifest",
                EngineStatus.PASS,
                id_="vdrive_package_vs_manifest",
                raw="R12.4.0 (sha 0xdeadbee matches manifest)",
            ),
        ]
    )
    versions = parse_engine_report(report, as_of=_now(), host_type="telestation")
    assert versions.vdrive_manifest.verdict == VersionVerdict.MATCH
    assert versions.vdrive_manifest.value == "R12.4.0"


def test_verdict_invariant_match_requires_value(monkeypatch) -> None:
    """A match-verdict field MUST have a non-null value (data-model.md § 2)."""
    from pydantic import ValidationError

    from vayobd.api.host_versions import VersionField, VersionVerdict

    with pytest.raises(ValidationError):
        VersionField(value=None, verdict=VersionVerdict.MATCH, as_of=_now())


def test_verdict_invariant_unavailable_requires_reason() -> None:
    from pydantic import ValidationError

    from vayobd.api.host_versions import VersionField, VersionVerdict

    with pytest.raises(ValidationError):
        VersionField(value=None, verdict=VersionVerdict.UNAVAILABLE, reason=None, as_of=_now())
