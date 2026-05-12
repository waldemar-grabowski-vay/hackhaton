# Engine-output Mapping Contract — `EngineReport.checks` → `HostVersions`

**Owner**: `backend/src/vayobd/api/host_versions.py` (the parser
specifically, isolated as a pure function for testability).
**Engine source**: `engine/ree-debug-engine/src/checks/reecu.rs`
(`vdrive_release_drift_check`, `compose_version_summary`).
**Phase**: 007 — locks in the name-match parser introduced in
research §1.

This file is the single source of truth for **which `CheckEntry`
rows the backend extracts and which verdict each one yields**. When
the engine renames a row, this file MUST be updated in the same PR
that lands the engine change; the integration test
`test_host_versions_endpoint.py` is the canary.

---

## Engine report shape (reminder)

```rust
pub struct EngineReport {
    pub schema: String,
    pub version: String,
    pub host_id: String,
    pub host_type: HostType,           // Vehicle | Telestation
    pub started_at: String,
    pub completed_at: String,
    pub outcome: RunOutcome,           // Complete | Partial | Unreachable | Timeout
    pub checks: Vec<CheckEntry>,
}

pub struct CheckEntry {
    pub id: String,
    pub name: String,                  // ← we match on this
    pub status: CheckStatus,           // Pass | Warn | Fail
    pub raw_detail: Option<String>,
    pub duration_ms: u64,
}
```

The backend deserialises this via Pydantic; matching is by
case-insensitive substring on `name`.

---

## Row-to-field map

For each target field, the backend scans `EngineReport.checks` and
takes the **first matching** row (engine emits each category once
per host so duplicates aren't expected; first-match keeps the parser
deterministic if duplicates ever appear).

### `vdrive_manifest`

| Match condition | Substring in `CheckEntry.name` |
|---|---|
| Primary | `vDrive package vs manifest` |
| Fallback | `ree-drive-` |

The fallback handles the engine wording variant where the row name
embeds the package id (`ree-drive-telestation` / `ree-drive-vehicle`)
instead of the abstract category. If neither matches, verdict is
`unavailable` with `reason: "host didn't report vDrive version"`.

### `vreecu_version`

| Match condition | Substring in `CheckEntry.name` |
|---|---|
| Primary | `Aurix` |
| Fallback | `REECU firmware` |

Engine names this `Aurix firmware …` today (see
`engine/ree-debug-engine/src/checks/reecu.rs:758-760`). The
fallback covers a likely future renaming.

### `sec_version`

| Match condition | Substring in `CheckEntry.name` |
|---|---|
| Primary | `SEC version` |
| Fallback | `Gateway firmware` |

Engine names this `SEC <build-type> <X.Y.Z>` today via
`compose_version_summary` with `gw_build_type` (`engine/.../reecu.rs:761-763`).

VE-host caveat: if the planned-row list does NOT include a SEC row
for vehicle hosts (engine's current rust-side planning), the field
collapses to `unavailable` with `reason: "SEC version not
applicable to vehicle hosts"`. This is a known engine asymmetry,
not a bug.

---

## Verdict derivation

For each matched row, the verdict is derived from `CheckEntry.status`
combined with substring detection on `CheckEntry.name`:

```text
status   name contains                              → verdict
─────────────────────────────────────────────────────────────────
Pass    "matches manifest"                         → match
Warn    "manifest expects" OR "≠ manifest"         → drift
Warn    "no manifest available"                    → no-manifest
Fail    (any)                                      → unavailable
Warn    (none of the above; rare)                  → no-manifest
                                                     (defensive default; engine
                                                      emits Warn for benign
                                                      version oddities)
```

When no row matches the target field at all, the result is
`unavailable` with the "didn't report" reason.

---

## Value extraction

The `value` and `expected` strings come from parsing
`CheckEntry.name` itself, because the engine already embeds them in
the summary text:

| Engine `name` example | Parsed `value` | Parsed `expected` |
|---|---|---|
| `vDrive package vs manifest: R12.3.0 (matches manifest)` | `R12.3.0` | — |
| `vDrive package vs manifest: R12.3.0 (manifest expects R12.4.0)` | `R12.3.0` | `R12.4.0` |
| `vDrive package vs manifest: R12.3.0 (sha abcd1234 matches manifest)` | `R12.3.0` | — |
| `Aurix firmware: 8.5.3 (matches manifest)` | `8.5.3` | — |
| `SEC version: 6.1.0 (manifest expects 6.2.0)` | `6.1.0` | `6.2.0` |

Parser rules:

1. Split `name` on the first `:` — left side is the field label
   (discarded once we've matched), right side is the value-plus-tail.
2. Take everything up to the first `(` — that's `value` (trimmed).
3. The parenthesised tail (if present) is searched for `expects <X>`
   or `manifest <X>`; the first capture group becomes `expected`.

If parsing fails (no `:`, malformed `(...)` tail), the field is
emitted with `value = name.strip()`, `verdict = match`, and a
backend log warning. Falling through to `match` rather than
`unavailable` follows the engine's intent — `status: Pass` means
"this is fine"; a parsing weirdness shouldn't downgrade the
operator's view.

---

## Reason extraction (verdict `unavailable` only)

The `reason` string for an unavailable field follows the table in
`research.md` § 4. Implementation note: the matching is done
**after** the row has been classified as `unavailable` — the
backend never composes a reason for a non-unavailable verdict.

---

## Test fixture invariants

`backend/tests/fixtures/engine_reports/ts_host_full.json` MUST
contain at least one row matching each of the three primary
substring patterns (`vDrive package vs manifest`, `Aurix`,
`SEC version`) AND MUST exhibit all four verdicts across the three
fields (specifically: drift on vDrive, match on vREECU, unavailable
on SEC). If the engine renames a row such that the primary substring
fails, the fixture MUST be regenerated and this contract updated in
the same PR.

A second fixture `ve_host_full.json` covers the vehicle-host
asymmetry: VE planned rows include vDrive (VE flavour) and Aurix,
but no SEC row — the parser must yield SEC as `unavailable` with
the "not applicable" reason.
