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


# --- FR-011: REECU-owned rows belong to the version card, not run.items ----


def _diagnostic_item(id_: str, category: str = "software") -> "DiagnosticItem":
    from vayobd.models import CheckCategory, DiagnosticItem, ItemStatus

    return DiagnosticItem(
        id=id_,
        name_key=f"item.{id_}.name",
        category=CheckCategory(category),
        status=ItemStatus.WORKING,
        raw_detail="ok",
    )


def _run_with_items(item_ids: list[str]) -> "DiagnosticRun":
    from vayobd.models import DiagnosticRun, RunOutcome

    return DiagnosticRun(
        host_id="ts-de-ber-zeus",
        started_at=_now(),
        completed_at=_now(),
        outcome=RunOutcome.COMPLETE,
        items=[_diagnostic_item(i) for i in item_ids],
    )


def test_filter_reecu_owned_items_drops_version_card_rows() -> None:
    """FR-011: REECU/vDrive/SEC rows MUST NOT appear in run.items
    (they're already on the version card)."""
    from vayobd.api.host_versions import _filter_reecu_owned_items

    run = _run_with_items(
        [
            # version-card-owned (engine ids — should be filtered)
            "vdrive_package_vs_manifest",
            "aurix_mcu_firmware",
            "sec_fpga_gateware",
            "ts_sec_version",
            "reecu_firmware_check",
            # genuine check-battery items (should remain)
            "peplink_cellular_reachable",
            "main_can_bus_reachable",
            "telestation_config_valid",
            "expected_input_devices_connected",
        ]
    )
    kept = _filter_reecu_owned_items(run).items
    kept_ids = {item.id for item in kept}

    # version-card-owned rows are filtered out
    assert "vdrive_package_vs_manifest" not in kept_ids
    assert "aurix_mcu_firmware" not in kept_ids
    assert "sec_fpga_gateware" not in kept_ids
    assert "ts_sec_version" not in kept_ids
    assert "reecu_firmware_check" not in kept_ids
    # genuine check-battery rows survive
    assert "peplink_cellular_reachable" in kept_ids
    assert "main_can_bus_reachable" in kept_ids
    assert "telestation_config_valid" in kept_ids
    assert "expected_input_devices_connected" in kept_ids


def test_filter_drops_cloud_reeapis_noise() -> None:
    """Cloud-side reeapis.com probes are low-signal on isolated testbeds
    and should not appear in run.items."""
    from vayobd.api.host_versions import _filter_reecu_owned_items

    run = _run_with_items(
        [
            "api_prod_reeapis_com",
            "lobby_prod_reeapis_com",
            "tdms_prod_reeapis_com",
            "cloud_telemetry_prod_reeapis_com",
            "main_can_bus_reachable",  # a real check; must survive
        ]
    )
    kept_ids = {item.id for item in _filter_reecu_owned_items(run).items}

    assert kept_ids == {"main_can_bus_reachable"}


def test_filter_is_idempotent() -> None:
    """Running the filter twice produces the same result (no oscillation)."""
    from vayobd.api.host_versions import _filter_reecu_owned_items

    run = _run_with_items(
        [
            "vdrive_package_vs_manifest",  # filtered
            "peplink_cellular_reachable",  # kept
        ]
    )
    once = _filter_reecu_owned_items(run)
    twice = _filter_reecu_owned_items(once)
    assert [i.id for i in once.items] == [i.id for i in twice.items]
