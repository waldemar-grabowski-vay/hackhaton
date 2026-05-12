# Implementation Plan: Restore TS_diag entry, host-side version pull, drop API check battery, readability tweaks

**Branch**: `007-ts-diag-restore-version-pull` | **Date**: 2026-05-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-ts-diag-restore-version-pull/spec.md`

## Summary

A focused tweak round on top of the in-flight 006 pivot. Four threads, all small:

1. **Restore TS_diag entry points.** Fix the latent bug where toggling Developer mode in the UI does not flip the server-side `/api/health.live_diagnostic.enabled` flag the button is gated on; mount a second copy of `LiveDiagnosticButton` in the picker page's primary-action area (header copy already exists). Both renderings appear / disappear together (Clarification Q5).
2. **Real host-side version pull.** Replace the placeholder body of `api/host_versions.py::_collect_versions` with a real `ree-debug-cli report --host <id>` invocation (engine already produces every value we need — Clarification Q1), parse the JSON, map the three relevant `CheckEntry` rows to `vdrive_manifest` / `vreecu_version` / `sec_version`, encode per-field verdict + reason (Clarification Q2), cache the response per-host with a 60 s TTL plus an explicit refresh affordance (Clarification Q3), and render an em-dash + spinner during the in-flight window (Clarification Q4).
3. **Finish removing the API check battery.** The working tree already deletes most of it (`backend/src/vayobd/checks/*`, `frontend/src/components/result/*`, `runs.py`, `runs.ts`, the result-state components, the `RunResultPage`). This round finalises the cleanup — drop the router registration, scrub any remaining imports / strings, confirm no lingering references survive a clean build.
4. **Readability tweaks.** Apply 005's plain-language + scannable principles to the two surviving surfaces (main page, host-detail page) — visually distinguish `match` / `drift` / `no-manifest` / `unavailable` at a glance, hoist the `source` chip out of corner-decoration territory, never show a bare em-dash without an explanation.

The diff is small and stays inside the existing monorepo. No new packages, no new long-running daemons, no new rust crates. The engine and the broader `006` .deb work continue in parallel — this feature only touches `backend/src/vayobd/api/host_versions.py`, a handful of frontend files, the picker page mounting, and a documentation pass.

## Technical Context

**Language/Version**: Python 3.12 (existing backend); TypeScript 5.6 + React 18.3 (existing SPA); Rust 1.75+ (engine — no changes here).
**Primary Dependencies**: FastAPI / uvicorn / Pydantic (backend, unchanged); existing `ree-debug-cli` binary on PATH (engine surface for FR-004 — already invoked elsewhere); React Router + @tanstack/react-query (SPA — already a dependency); `subprocess`/`asyncio.create_subprocess_exec` for the engine shellout (stdlib, no new deps).
**Storage**: In-memory per-process TTL cache for host versions (FR-017); no disk persistence introduced by this feature. `settings.toml` continues to drive `developer_mode` (FR-001 gate).
**Testing**: pytest (existing) for the rewritten `_collect_versions`, the TTL cache, and the engine-output mapper; Playwright e2e for the dual-entry-point visibility check (Developer mode on/off) and the host-detail loading-state flip; frontend Vitest for the per-field cell renderer.
**Target Platform**: Same as 006 — Ubuntu 24.04 LTS local-loopback web app on the operator's machine. Browser support inherits from earlier features (current Chrome / Firefox / Safari / Edge).
**Project Type**: web-service + SPA in the existing monorepo (`backend/`, `frontend/`, `engine/`).
**Performance Goals**: SC-002 (real versions rendered within 10 s on 95 % of attempts), SC-005 (operator can visually distinguish verdict states in < 2 s of glance), SC-007 (cached re-visit < 500 ms — no SSH spawn).
**Constraints**:
  - **Constitution Web App Standards (HTTPS for production).** Same loopback-HTTP exception 006 already accepted; no new constraint introduced. No clear-text traffic leaves the laptop.
  - **No new abstractions.** Per Principle I, the per-field state and TTL cache are added as the smallest possible additions to existing code; no general-purpose caching layer, no DI rework, no new "version source" plugin interface.
  - **No engine-side change.** Clarification Q1 locks the rust engine as a black box for this feature; if a CheckEntry row mapping turns out to need a tweak, that's a follow-up against the engine, not this branch.
  - **Tweak round, not redesign.** The /live surface itself, the inventory loader, the auth shim, and the settings store are unchanged.
**Scale/Scope**: Single-operator desktop; ≤ a few hosts in flight per session. The TTL cache scales to the in-scope German fleet (tens of hosts). No multi-tenant or horizontal scaling considered.

## Constitution Check

*Gates evaluated against `.specify/memory/constitution.md` v1.0.0. Re-checked after Phase 1.*

| Gate | Status | Evidence |
|------|--------|----------|
| **I. Simplicity First (NON-NEGOTIABLE)** | ✅ Pass | Three discrete in-place edits + one delete. No new packages, no caching framework, no plugin interface. The TTL cache is a `dict[str, tuple[datetime, response]]` guarded by a `threading.Lock` (same model as the refresh router in 006). Engine shellout reuses the pattern already in `backend/src/vayobd/dependencies.py`. |
| **II. Ship Fast** | ✅ Pass | All four user stories are independently testable and can land in separate PRs in any order. US3 (delete) can ship immediately — the working tree already does most of it. US1 / US2 are bounded by the dual-entry-point fix and the engine-output mapper respectively, both estimated < 1 day each. No green-field design, no schema migration. |
| **III. Non-Technical User UX (NON-NEGOTIABLE)** | ⚠️ Partial-applicability — passes intent | The host-detail page is operator-facing but the operator audience is **internal Vay engineers** (the same audience the rust CLI serves). The constitution's "non-technical user" framing applies most strongly to the primary public diagnostic flow (which no longer exists — the API check battery was that surface). What this feature ships honours the *spirit* of Principle III: plain-language verdict states (FR-007 reasons, FR-010 visual distinguishability), no bare em-dashes (FR-012), recovery-oriented copy ("couldn't read SEC version — package not installed" rather than dpkg exit codes). Where engineering terminology is unavoidable (vDrive, vREECU, SEC), it remains in the labels — these terms ARE the operator's mental model. |
| **Web App Standards — HTTPS** | ⚠️ Inherited exception | Loopback-only HTTP; no change from the 006 disposition documented in `006/plan.md` Complexity Tracking. |
| **Web App Standards — browsers, responsive, privacy** | ✅ Pass | No new third-party scripts, no new external network calls. The version data flows: host → engine subprocess → backend → loopback HTTP → SPA. Nothing reaches the network. The responsive layout follows the existing card-grid approach already used on the host-detail page; no new layout primitive. |
| **Development Workflow — demo always working** | ✅ Pass | The feature is additive on top of the 006 working tree. US3 finalises deletions that are already in progress; US1/US2/US4 don't break any existing path. If US2's engine call fails for any reason at demo time, the page degrades to the existing em-dash + reason cell — never a 5xx (FR-014). |

**Result**: All gates pass; one inherited HTTPS exception (Complexity Tracking below); one Principle III nuance accepted as engineering-audience-appropriate.

## Project Structure

### Documentation (this feature)

```text
specs/007-ts-diag-restore-version-pull/
├── plan.md              # This file
├── spec.md              # Feature spec (clarified 2026-05-11; 5 questions resolved)
├── research.md          # Phase 0 — engine output mapping, TTL cache, developer-mode gate root cause, per-field reason copy
├── data-model.md        # Phase 1 — HostVersionField shape, cache entry, response wire shape, settings delta
├── contracts/
│   ├── http-api.md      # GET /api/host/{id}/versions response shape (extended); refresh semantics
│   ├── engine-mapping.md  # Which CheckEntry rows in EngineReport map to which version field
│   └── frontend-states.md # Per-cell state machine: loading / live / drift / unavailable / no-manifest
├── quickstart.md        # Developer walkthrough: rebuild, click around, verify each US's acceptance scenarios
└── checklists/
    └── requirements.md  # Spec-quality checklist (already exists, all pass)
```

### Source Code (repository root)

```text
backend/
├── src/vayobd/
│   ├── api/
│   │   ├── host_versions.py       # REWRITTEN — _collect_versions now shells out to ree-debug-cli,
│   │   │                          #             parses JSON, maps to per-field verdicts, applies TTL cache.
│   │   │                          #             HostVersions / HostVersionsResponse shape evolves
│   │   │                          #             (per-field record per Clarification Q2).
│   │   └── (no new module — refresh affordance for host versions reuses /api/host/{id}/versions
│   │        with a ?fresh=true query param; see contracts/http-api.md)
│   ├── app.py                     # MINOR — leave host_versions_router registration as-is;
│   │                              #         confirm the deleted runs_router is NOT re-introduced.
│   └── _internal/version_cache.py # NEW (tiny) — per-process TTL cache module: get / set / invalidate.
│                                  # Single dict + threading.Lock; ~40 LOC. Lives under _internal/
│                                  # because nothing else should import it.
└── tests/
    ├── unit/
    │   ├── test_host_versions_collector.py   # NEW — engine-output mapping, per-field verdict, error paths
    │   └── test_version_cache.py             # NEW — TTL hit/miss, manual invalidate, concurrent get
    └── integration/
        └── test_host_versions_endpoint.py    # NEW — replaces removed test_runs_endpoint.py for coverage

frontend/
├── src/
│   ├── pages/
│   │   ├── HostDetailPage.tsx                # EDIT — per-cell state (loading / live / drift / unavailable),
│   │   │                                     #        refresh button, timestamps, visible source pill,
│   │   │                                     #        FR-010 / FR-011 / FR-019 / FR-020.
│   │   └── PickerPage.tsx                    # EDIT — mount LiveDiagnosticButton in primary-action area.
│   ├── components/chrome/
│   │   └── LiveDiagnosticButton.tsx          # EDIT — switch the gating signal: read from `useDeveloperMode`
│   │                                          #        local store first (UI is authoritative for the toggle);
│   │                                          #        keep /api/health as a soft-fail readiness probe.
│   ├── api/
│   │   ├── hostVersions.ts                   # EDIT — extended schema (per-field record + verdict + reason)
│   │   └── host-versions.ts                  # DELETE — legacy dup file; only one should remain (research §1.5)
│   └── strings.ts                            # EDIT — update verdict copy, remove "Run checks" wording
└── tests/e2e/
    ├── live-diagnostic-entry.spec.ts         # NEW — dual-entry-point visibility w/ developer-mode toggle
    └── host-detail-versions.spec.ts          # NEW — loading flip, drift highlight, refresh button, TTL

# DELETIONS — finalised in US3 (most already staged in working tree):
backend/src/vayobd/checks/                    # delete the entire package
backend/src/vayobd/api/runs.py                # delete (already staged)
backend/tests/unit/test_catalog.py            # delete (already staged)
backend/tests/integration/test_runs_endpoint.py  # delete (already staged)
frontend/src/api/runs.ts                      # delete (already staged)
frontend/src/components/result/               # delete the entire directory (already staged)
frontend/src/components/states/RunningState.tsx       # delete (already staged)
frontend/src/components/states/PartialRunState.tsx    # delete (already staged)
frontend/src/components/states/UnreachableState.tsx   # delete (already staged)
frontend/src/components/motion/StaggeredList.tsx      # delete (already staged)
frontend/src/pages/RunResultPage.tsx          # delete (already staged)
```

**Structure Decision**: Stay inside the existing monorepo with the smallest viable diff. The two new backend modules (`_internal/version_cache.py`, the new tests) live next to their consumers; nothing is hoisted into a shared library. The frontend follows suit — no new "DiagnosticState" abstraction, no new component library entry, just edits to the two pages that own the surfaces. US3 completes a deletion the working tree has already started; the goal is parity at end of US3 between `git diff main..HEAD` and the listed deletion set, with no orphan imports.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Loopback HTTP instead of HTTPS (Web App Standards exception, inherited from 006) | Local-loopback-only traffic continues to be the deployment model; introducing HTTPS would require either a self-signed cert (browser-trust warning on every launch — direct Principle III violation) or user-supplied cert config (forbidden by 006's "no .env editing" stance). | The constitutional intent of the HTTPS rule is "production traffic" — Same 006-research analysis still applies; no new traffic leaves the laptop because of this feature. |
| Two copies of the entry-point button (FR-001 — header + main page) instead of one | Operator workflow needs both prominence on landing AND mid-session reachability (Clarification Q5). A single rendering trades one for the other. | Single-rendering options A and B were both rejected in clarification; this feature's whole point is restoring discoverability, so the doubled rendering is the user-asked-for shape, not gold-plating. The cost is one extra mount and a coupled gate check — both trivial. |
