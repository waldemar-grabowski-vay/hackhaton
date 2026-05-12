# Implementation Plan: Restore host check battery, fix Live Diagnostic regression, keep version pull surface

**Branch**: `008-restore-host-checks-fix-live` | **Date**: 2026-05-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-restore-host-checks-fix-live/spec.md`

## Summary

Regression-recovery round on top of 007. Three concrete pieces:

1. **`git checkout HEAD --` the deletions** that 007 introduced (per Clarification Q3). The pre-007 working tree at commit `01d3979` still contains every file 007 staged-for-delete — backend `checks/` package, `/api/runs.py`, the result-page React components (`CategoryBadge`, `ResultGroup`, `ResultHero`, `DiagnosticItemRow`, `RepairGuideSheet`, `HarnessDiagram`, `TelestationDiagram`, `RunningState`, `PartialRunState`, `UnreachableState`, `StaggeredList`), `RunResultPage`, plus the matching tests. Restoration is mechanical; the only file that needs hand-merging is `frontend/src/strings.ts` (007 kept the new `hostVersions` block; 008 needs to re-introduce the `runs / outcomes / result / category / guide / item` blocks alongside it).
2. **Diagnose + fix Live Diagnostic** (per Clarification Q2's deferred-diagnosis answer). The most likely root cause based on observed evidence is the SPA-mount path: the user's `vayobd` command resolves to the pyenv-installed editable build (a leftover from the 007 test pass) which doesn't set `VAYOBD_STATIC_DIR`, so the SPA is never mounted at `/` and every page (including `/live`) returns 404. Secondary causes worth checking during the spike: the DBC glob pattern preferring `Env.dbc` over `application_protocol.dbc` on this user's `ree-reecu` clone layout, and a possible `strings.ts` reference orphaned by 007's scrub that the Live Diagnostic page hits. The plan calls for a focused 30-minute spike against the .deb-installed runtime before scoping the fix.
3. **Wire the REECU pipeline as a one-shot capture** (per Clarification Q4). The host-detail backend opens a brief candump+DBC session per host (3–5 s wall-clock), extracts vREECU / SEC / ERRQ fields, caches the response under 007's 60 s TTL, then routes the values into 007's existing version card AND the restored check battery. The non-REECU rows (vDrive, Peplink, network, etc.) keep coming from `ree-debug-cli report` per Clarification Q1.

The diff revives ~22 deleted files (or ~2.5k LoC of restored code), adds two thin coordination layers (a new REECU-capture path that reuses `vayobd.live.session`, and a unified `HostDetailPage` layout composing the version card above the restored result page), preserves every 007 improvement (per-field verdicts, TTL cache, refresh button, dual TS_diag entry points, plain-language copy), and ships with no rust-side change.

## Technical Context

**Language/Version**: Python 3.12 (bundled python-build-standalone in the .deb); TypeScript 5.6 + React 18.3 (existing SPA); Rust 1.75+ (engine — no changes here, same as 007).
**Primary Dependencies**: FastAPI / uvicorn / Pydantic (backend, unchanged); `cantools` + `asyncssh` (already used by `vayobd.live.session`); existing `ree-debug-cli` binary on PATH; React Router + @tanstack/react-query (SPA, unchanged); shadcn/ui primitives the restored result page already relies on.
**Storage**: Same as 007 — in-memory per-process TTL cache for host detail responses (now keyed by host_id, carrying the combined REECU + non-REECU + version response). No new disk artefacts.
**Testing**: pytest for the new REECU-capture wiring + the unified host-detail collector; restored unit tests (`test_catalog.py`) come back via git checkout; restored `test_runs_endpoint.py` comes back via git checkout; Playwright e2e for the combined host-detail page + the Live Diagnostic happy path after the spike-driven fix.
**Target Platform**: Same as 007 — Ubuntu 24.04+ (and any glibc-based amd64 Linux via the bundled-python .deb).
**Project Type**: web-service + SPA in the existing monorepo.
**Performance Goals**: SC-001 (versions + checks rendered within 10 s on a reachable host, 95% of attempts); SC-002 (LD reaches decoded-signal state within 10 s or surfaces a plain-language error within 5 s, 100% of attempts); SC-005 (007's cache-served re-visit <500 ms holds — extended to the unified response); SC-006 (operator can scan the page in <3 s and distinguish versions from checks from repair-guide entry points).
**Constraints**:
  - **Web app standards loopback-HTTP exception** — inherited from 006 / 007, no new constraint.
  - **No rust-side change** — Clarification Q1 locks the engine as a black box; if a rust change turns out to be needed during implementation, that's a separate spec.
  - **No new packaging change** — the bundled-Python .deb work from the recent fix carries forward unchanged.
  - **Restoration via `git checkout`, not re-implementation** — Clarification Q3 binds us to mechanical recovery + hand-merged strings only.
  - **REECU capture is one-shot, 3–5 s per page mount** — Clarification Q4; no long-lived background sessions, no live streaming on the host-detail page.
**Scale/Scope**: Single-user desktop; ≤ a few hosts in flight per session; the in-scope German fleet (tens of hosts) is the TTL-cache audience. No multi-tenant or horizontal-scaling considerations.

## Constitution Check

*Gates evaluated against `.specify/memory/constitution.md` v1.0.0. Re-checked after Phase 1.*

| Gate | Status | Evidence |
|------|--------|----------|
| **I. Simplicity First (NON-NEGOTIABLE)** | ✅ Pass | The largest part of US1 is a mechanical revert (`git checkout HEAD --` per deleted path) — no new abstractions introduced. The new REECU-capture path reuses `vayobd.live.session` rather than introducing a new SSH/decode pipeline. The cache is the same `VersionCache` 007 added, extended in-place to hold a richer response. No new packages, no new tables, no DI rework. |
| **II. Ship Fast** | ✅ Pass | The plan is staged so US1 (mechanical revert) can land alone in a small PR before US2's spike-driven fix is even started. Even the most complex story (US4 — REECU pipeline) is a thin wrapper around existing code. Every user story is independently testable per the spec's Independent Test sections. |
| **III. Non-Technical User UX (NON-NEGOTIABLE)** | ⚠️ Engineering-audience scope — passes intent | Same disposition as 007: the operator audience is internal Vay engineers; the restored battery uses 005's plain-language copy conventions verbatim (since we're reverting to the state 005 already landed); the new REECU-capture loading state reuses 007's em-dash + spinner pattern. No new operator-facing copy is invented for 008 except where strings.ts needs hand-merging — and the merge target is 005's wording, which Principle III already approved. |
| **Web App Standards — HTTPS** | ⚠️ Inherited exception | Loopback-only HTTP; no change from 006 / 007. |
| **Web App Standards — browsers, responsive, privacy** | ✅ Pass | No new external scripts or network calls. The REECU one-shot capture is a backend → host SSH call, no new client-side traffic. The combined layout uses `flex-col md:flex-row` patterns already in the SPA. |
| **Development Workflow — demo always working** | ✅ Pass | Each US lands as an independently shippable increment. The revert is staged for US1 alone; LD fix is US2; layout composition is US3. The demo state never regresses because 008 only ADDS what 007 over-removed, never removes anything 007 kept. |

**Result**: All gates pass with one inherited HTTPS exception (Complexity Tracking below). No new exceptions.

## Project Structure

### Documentation (this feature)

```text
specs/008-restore-host-checks-fix-live/
├── plan.md              # This file
├── spec.md              # Feature spec (clarified 2026-05-11; 5 questions resolved)
├── research.md          # Phase 0 — LD failure-mode spike findings, restoration mechanics, REECU capture pattern, strings.ts merge strategy
├── data-model.md        # Phase 1 — HostDetail wire shape (versions + REECU rows + non-REECU rows), CheckResult restored from pre-007
├── contracts/
│   ├── http-api.md      # Unified GET /api/host/{id}/versions response shape; existing /api/runs/* endpoints restored
│   ├── reecu-pipeline.md  # One-shot REECU capture: capture window, signal extraction, error semantics
│   └── strings-merge.md   # Hand-merge guide for frontend/src/strings.ts (which blocks to restore from HEAD; which to keep from 007)
├── quickstart.md        # Acceptance walkthrough: revert lands → restored battery works → LD works → unified page renders
└── checklists/
    └── requirements.md  # Spec-quality checklist (already exists, all pass)
```

### Source Code (repository root)

```text
backend/
├── src/vayobd/
│   ├── api/
│   │   ├── host_versions.py       # EDIT — extend 007's collector with a REECU-capture step (one-shot 3-5 s),
│   │   │                          #         merge REECU rows into the unified response, keep the version-card surface intact,
│   │   │                          #         cache under existing VersionCache (TTL 60 s).
│   │   ├── runs.py                # RESTORE — `git checkout HEAD -- backend/src/vayobd/api/runs.py`
│   │   └── (no new module)
│   ├── checks/                    # RESTORE — `git checkout HEAD -- backend/src/vayobd/checks/`
│   │                              # (six files: __init__.py, catalog.py, executor.py, peplink.py, ree_cli.py, runner.py)
│   ├── live/                      # UNCHANGED — session.py exposes the SSH+candump+DBC pipeline the new REECU capture wraps
│   ├── _internal/version_cache.py # MINOR — generic enough as-is; the cached payload type changes; unit tests update
│   └── app.py                     # EDIT — re-register the restored runs_router (single line)
└── tests/
    ├── unit/
    │   ├── test_catalog.py        # RESTORE — `git checkout HEAD --`
    │   ├── test_host_versions_collector.py  # EDIT — extend assertions to cover REECU-row routing
    │   └── test_reecu_capture.py  # NEW — assert one-shot capture extracts vREECU + SEC fields from a recorded DBC fixture
    └── integration/
        ├── test_runs_endpoint.py  # RESTORE — `git checkout HEAD --`
        └── test_host_versions_endpoint.py  # EDIT — extend to cover the unified response (versions + REECU + non-REECU + 60 s TTL)

frontend/
└── src/
    ├── api/
    │   ├── runs.ts                # RESTORE — `git checkout HEAD --`
    │   └── hostVersions.ts        # EDIT — extend the response schema to carry the restored check battery alongside the version cells
    ├── components/
    │   ├── motion/
    │   │   └── StaggeredList.tsx  # RESTORE — `git checkout HEAD --`
    │   ├── result/                # RESTORE — `git checkout HEAD -- frontend/src/components/result/`
    │   │                          # (CategoryBadge, DiagnosticItemRow, HarnessDiagram, RepairGuideSheet,
    │   │                          #  ResultGroup, ResultHero, TelestationDiagram)
    │   └── states/
    │       ├── PartialRunState.tsx     # RESTORE — `git checkout HEAD --`
    │       ├── RunningState.tsx        # RESTORE — `git checkout HEAD --`
    │       └── UnreachableState.tsx    # RESTORE — `git checkout HEAD --`
    ├── pages/
    │   ├── HostDetailPage.tsx     # EDIT — compose 007's version card (kept) + restored result-page sections; route REECU rows from versions, non-REECU into the result groups
    │   ├── RunResultPage.tsx      # RESTORE then merge into HostDetailPage during US3 — defer the merge-vs-keep-separate decision to implementation
    │   └── LiveDiagnostic/        # EDIT during US2 spike — whatever the diagnosis points at (likely DBC selector tightening + SPA-mount note for the .deb wrapper)
    ├── strings.ts                 # HAND-MERGE — keep 007's hostVersions block + restored runs/outcomes/result/category/guide/item blocks
    └── guides.ts                  # UNCHANGED — already in the tree (007 didn't delete it; it became orphan); becomes live again under US1
```

**Structure Decision**: Stay inside the existing monorepo. The revert is mechanical and reversible — any file that turns out to need 007-flavoured updates can be edited in place after the checkout. The single new file (`backend/tests/unit/test_reecu_capture.py`) lives next to its consumer. No new top-level directory; no new package. The frontend gets no new components — every "new" component is something we're restoring from HEAD.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Loopback HTTP instead of HTTPS (Web App Standards exception, inherited from 006) | Local-loopback-only traffic; HTTPS would force a self-signed cert browser-trust warning (Principle III conflict). | Same disposition as 006 and 007 — no new analysis needed. |
| Two pipelines feeding one page (REECU via Live Diagnostic code path; everything else via `ree-debug-cli`) | Clarification Q1 — the team's REECU information already exists as decoded CAN signals; re-deriving it via `ree-debug-cli` over a separate SSH session would duplicate work and re-derive the same fields by a slower path. | Single pipeline (all via `ree-debug-cli`): the rust engine doesn't currently parse REECU CAN frames into a JSON report — it relies on out-of-band signals. Forcing it to would be more work than reusing `vayobd.live.session`. Single pipeline (all via Live Diagnostic): would need to reimplement Peplink HTTP probes, network reachability, `dpkg-query`, etc., inside the live session — far larger scope. The two-pipeline split is the smallest correct shape. |
