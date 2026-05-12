# Phase 1 Data Model — Restore host check battery, fix Live Diagnostic regression

**Date**: 2026-05-11
**Status**: complete

This file captures the shapes 008 touches — both the wire shape
(the unified `HostDetailResponse` the page consumes) and the
internal types feeding it. Models marked **(restored)** are
recovered verbatim from the pre-007 working tree via the
`git checkout HEAD --` in US1; only the composition layer is new.

---

## 1. `ItemStatus` (restored)

```python
class ItemStatus(StrEnum):
    WORKING = "working"
    WARNING = "warning"
    ERROR = "error"
```

Source of truth: pre-007 `backend/src/vayobd/models.py:60-63`.
Restored unchanged.

---

## 2. `CheckCategory` (restored)

```python
class CheckCategory(StrEnum):
    COMMUNICATION = "communication"
    HARDWARE      = "hardware"
    CONFIGURATION = "configuration"
    SOFTWARE      = "software"
    CALIBRATION   = "calibration"
```

Source of truth: pre-007 `backend/src/vayobd/models.py:42-…`.
Five-category palette from 002 / FR-006. Used by the restored
`ResultGroup` to colour-band the rows.

---

## 3. `DiagnosticItem` (restored)

```python
class DiagnosticItem(BaseModel):
    id: str                              # stable per host class
    name_key: str                        # i18n path into strings.ts
    description_key: str | None = None
    category: CheckCategory
    status: ItemStatus
    recommended_action_key: str | None = None  # required for WARNING/ERROR
    raw_detail: str | None = None        # always populated server-side
```

Source of truth: pre-007 `backend/src/vayobd/models.py:125-…`.
Restored unchanged. Model-validator enforces FR-004b (warning /
error rows MUST carry a `recommended_action_key`).

---

## 4. `RunOutcome` (restored)

```python
class RunOutcome(StrEnum):
    COMPLETE     = "complete"
    PARTIAL      = "partial"
    UNREACHABLE  = "unreachable"
    TIMEOUT      = "timeout"
```

Restored unchanged. Drives which of the restored state components
(`RunningState`, `PartialRunState`, `UnreachableState`, the
completion-with-errors hero) the page renders.

---

## 5. `DiagnosticRun` (restored)

```python
class DiagnosticRun(BaseModel):
    host_id: str
    started_at: datetime
    completed_at: datetime
    outcome: RunOutcome
    items: list[DiagnosticItem]
```

Restored unchanged. The shape `POST /api/runs` returns and the
restored `RunResultPage` consumes.

---

## 6. `VersionVerdict`, `VersionField`, `HostVersions` (007, kept)

Unchanged from 007's `data-model.md` §1–§3. The version card
continues to render off these. 008 does NOT redefine them.

Brief recap:

```python
class VersionVerdict(StrEnum):
    MATCH = "match"
    DRIFT = "drift"
    NO_MANIFEST = "no-manifest"
    UNAVAILABLE = "unavailable"

class VersionField(BaseModel):
    value: str | None
    verdict: VersionVerdict
    expected: str | None     # populated only on DRIFT
    reason: str | None       # populated only on UNAVAILABLE
    as_of: datetime
    # invariants enforced by model_validator (see 007 data-model.md § 2)

class HostVersions(BaseModel):
    vdrive_manifest: VersionField
    vreecu_version:  VersionField
    sec_version:     VersionField
```

---

## 7. `HostDetailResponse` (new in 008 — composition layer)

The unified wire shape the host-detail page consumes. This is the
post-008 wire format for `GET /api/host/{id}/versions`.

```python
class HostDetailResponse(BaseModel):
    host: Host
    versions: HostVersions          # 007's version card
    run: DiagnosticRun | None       # restored check battery; None while in flight
    source: Literal["live", "unavailable"]
```

Fields:

- **`host`**: the inventory Host record. Unchanged from 007.
- **`versions`**: the three-cell version card payload from 007.
  Populated by the unified collector — vDrive from `ree-debug-cli`,
  vREECU + SEC from the REECU one-shot capture.
- **`run`**: the restored `DiagnosticRun`. `items` includes every
  non-REECU check from the restored catalog (Peplink, network,
  cameras, WAKE, config validity, etc.). REECU-derived items do
  NOT appear here (they're already in `versions` per FR-011).
  `None` while the collector is in flight; the SPA renders the
  restored `RunningState` while `run is None`.
- **`source`**: response-level summary, same semantics as 007 —
  `"live"` if any field resolved, `"unavailable"` only if every
  source failed.

The page composition:

```text
┌─ Host header                                ─┐
│  display name + host id                       │
└───────────────────────────────────────────────┘
┌─ Version card (007)                          ─┐
│  source pill + refresh button                 │
│  vDrive  [verdict pill] [as-of]               │
│  vREECU  [verdict pill] [as-of]               │
│  SEC     [verdict pill] [as-of]               │
└───────────────────────────────────────────────┘
┌─ Result groups (restored)                    ─┐
│  Result hero (RunOutcome-aware)               │
│  Working      (n items)        [collapsible]  │
│  Needs attention (n items)     [collapsible]  │
│  → row: name + status pill + raw detail       │
│  → row: name + WAKE diagram + repair guide CTA│
│  → …                                          │
└───────────────────────────────────────────────┘
```

---

## 8. `CacheEntry` / `VersionCache[HostDetailResponse]` (007, type parameter changed)

The existing cache from 007's `_internal/version_cache.py` is
generic. The type parameter at the import site in
`host_versions.py` changes from `HostVersionsResponse` to
`HostDetailResponse`. The cache module itself is unchanged.

TTL stays at 60 seconds per Clarification Q4. Re-visit within the
TTL serves the whole unified response (version card + restored
items) instantly. `?fresh=true` invalidates the entry and re-runs
both pipelines in parallel.

---

## 9. State transitions

The unified page renders one of these post-load steady states,
chosen by `HostDetailResponse.run.outcome`:

```text
                         ┌─ COMPLETE      → "Working" + "Needs attention" groups
                         │
   run is non-null ──────┼─ PARTIAL       → PartialRunState above the groups
                         │
                         ├─ UNREACHABLE   → UnreachableState (no groups)
                         │
                         └─ TIMEOUT       → TimeoutState (no groups)

   run is null        ────► RunningState (the version card still resolves; can be done independently)
```

The version card has its own state machine (007 §6) — `loading
→ match / drift / no-manifest / unavailable` per cell — and
renders independently of the run state. The two surfaces share a
common loading state when the page first mounts (em-dash + spinner
on both); when one pipeline lands, that surface flips first
without waiting for the other.

---

## 10. Persistence

The restored `runs.py` continues to persist runs to
`backend/.cache/vayobd/runs/<operator-slug>/<host-id>.json` (the
pre-007 location, via `vayobd.inventory.runs_cache.write_run`).
The TTL cache in 008 sits in front of that — cached responses
serve without writing a new run record. Run records are still
written for fresh captures so the operator can compare run history
on a later iteration (out of scope for 008; the persistence remains
in case future features want it).

---

## 11. Compatibility with prior wire shape

The post-007 shape was:

```jsonc
{
  "host":     { ... },
  "versions": { vdrive_manifest: VersionField, vreecu_version: …, sec_version: … },
  "source":   "live" | "unavailable"
}
```

The post-008 shape is the same plus a top-level `run: DiagnosticRun | null`
field. Adding a nullable field is backward-compatible at the JSON
level — old clients that only read the three known fields still
work. The SPA's Zod schema in `frontend/src/api/hostVersions.ts`
adds the optional field; no breaking-change framing needed.

---

## 12. Engine fixture and test invariants

`backend/tests/fixtures/engine_reports/ts_host_full.json` and
`ve_host_full.json` (added in 007) remain useful for the version-card
parser tests, but they're now insufficient for the unified
collector — they don't carry the non-REECU check rows the restored
battery needs. New fixtures:

- `backend/tests/fixtures/runs/ts_host_complete.json` — restored
  from `git checkout HEAD --`. Pre-007 fixture covering the full
  catalog for a TS host.
- `backend/tests/fixtures/runs/ve_host_complete.json` — same for
  a VE host.

The unit test `test_host_versions_collector.py` is extended to
assert (a) REECU rows from the engine fixture get routed into
`versions`, not `run.items` (FR-011), and (b) every non-REECU row
in the engine fixture appears in `run.items` exactly once.
