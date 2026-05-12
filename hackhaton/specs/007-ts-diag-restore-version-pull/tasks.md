---

description: "Task list for 007 — restore TS_diag entry, host-side version pull, drop API check battery, readability tweaks"
---

# Tasks: Restore TS_diag entry, host-side version pull, drop API check battery, readability tweaks

**Input**: Design documents from `/specs/007-ts-diag-restore-version-pull/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Spec implies coverage (FR-008 demands the test suite reflect deletions; SC-003 requires parity with the rust CLI). Test tasks are included where they protect a contract that would otherwise drift silently.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. US1 and US3 are independent of US2; US4 depends on US2's output but can be staged behind it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- All file paths are repo-relative from the hackhaton root

## Path Conventions

- Web app monorepo: `backend/src/vayobd/...`, `frontend/src/...`
- Engine is **not** modified by this feature (Clarification Q1); engine paths appear only as read references

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Minimal scaffolding needed by later phases. This is a tweak round, not a green-field project — most "setup" is just creating two empty directories.

- [X] T001 [P] Create `backend/src/vayobd/_internal/__init__.py` to host the new internal cache module (data-model.md § 5, research § 2)
- [X] T002 [P] Create `backend/tests/fixtures/engine_reports/` directory with a `.gitkeep` so the engine-output fixtures land in a stable location (data-model.md § 10)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: This feature has no cross-story foundational layer — each user story is independent. The clarification round and plan deliberately kept the diff small enough that US1 / US3 / US4 don't depend on US2's internals.

**⚠️ CRITICAL**: No foundational tasks are needed. The four user stories can be developed in parallel after Setup completes.

(Intentionally empty. See plan.md → Project Structure → "Structure Decision" for the rationale.)

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 — Restore TS_diag entry points (Priority: P1) 🎯 MVP slice 1

**Goal**: With Developer mode toggled on, two "Live diagnostic" entry points render — one in the global `AppHeader`, one in the main-page primary action area. Both disappear when Developer mode is off. Clicking either lands on `/live`.

**Independent Test**: Quickstart Step 2 — toggle Developer mode off/on and confirm both buttons appear/disappear together; navigate to a sub-page and confirm the header copy is still reachable.

### Tests for User Story 1

- [X] T003 [P] [US1] Add Playwright e2e spec `frontend/tests/e2e/live-diagnostic-entry.spec.ts` covering: (a) Developer mode off → neither button visible; (b) Developer mode on → both buttons visible; (c) toggle off again → both hidden in lockstep; (d) header button reachable from `/host/:id` and `/live` sub-routes (FR-001 acceptance #1–#4, SC-001)

### Implementation for User Story 1

- [X] T004 [US1] Flip the gating signal in `frontend/src/components/chrome/LiveDiagnosticButton.tsx` from `useQuery('/api/health').data?.live_diagnostic?.enabled` to `useDeveloperMode((s) => s.enabled)`; keep the `/api/health` query as a soft readiness probe consumed by the `/live` page itself, not by the button (research § 3, contracts/frontend-states.md "TS_diag entry-point states")
- [X] T005 [US1] In `frontend/src/pages/PickerPage.tsx`, mount a second `<LiveDiagnosticButton />` adjacent to the existing primary-action button (look for the wizard's Step → next action; align it visually with that button per FR-013) — mounted in the host-step action row next to Continue, passes `variant="main"`
- [X] T006 [US1] Apply visual-weight tweaks in `frontend/src/components/chrome/LiveDiagnosticButton.tsx`: keep the existing `variant="outline" size="sm"` in the header (matches surrounding chrome — EngineModeBadge, Developer-mode switch); accept a `variant?: "header" | "main"` prop that the picker passes `"main"` so the main-page copy renders with the same visual weight as the primary action (FR-013) — added `LiveDiagnosticButtonProps`; "main" renders size="lg" outline matching the Continue button's footprint
- [X] T007 [US1] Confirm `frontend/src/App.tsx` still exposes the `/live` route and that the header `AppHeader` continues to mount on every page (no regression from the picker change). Run `npm run build && npm run lint` to confirm a clean tree. — verified: App.tsx Routes block unchanged; `npm run build` produces clean dist; `npm run lint` passes with 0 warnings

**Checkpoint**: At this point, User Story 1 should be fully functional — toggle Developer mode in the UI and watch both entry points appear/disappear together. The Playwright spec from T003 should pass.

---

## Phase 4: User Story 2 — Real host-side version pull (Priority: P1)

**Goal**: The host-detail page shows live vDrive / vREECU / SEC values pulled from the host via the engine, cross-checked against the manifest, with per-field verdicts, an in-flight loading state (em-dash + spinner), a 60-second per-host TTL cache, an explicit refresh affordance, and per-cell timestamps.

**Independent Test**: Quickstart Step 3 — open a reachable host's detail page, watch the cells flip from loading to their post-load state within 10 s, click refresh and watch them re-load, return within the TTL and confirm cache-served (< 500 ms).

### Tests for User Story 2

- [X] T008 [P] [US2] Record an engine fixture `backend/tests/fixtures/engine_reports/ts_host_full.json` containing one `CheckEntry` for each primary substring (`vDrive package vs manifest`, `Aurix firmware`, `SEC version`), exhibiting all four verdicts across the three fields — vDrive drift, vREECU match, SEC unavailable (data-model.md § 10, contracts/engine-mapping.md "Test fixture invariants")
- [X] T009 [P] [US2] Record a second fixture `backend/tests/fixtures/engine_reports/ve_host_full.json` covering the VE host asymmetry — vDrive + Aurix present, no SEC row — so the parser's "SEC not applicable to vehicle hosts" path is locked in
- [X] T010 [P] [US2] Add `backend/tests/unit/test_host_versions_collector.py` driving the engine-output parser against the two fixtures plus a synthetic "engine timed out" / "exit non-zero" case; assert every verdict, every reason string, every value/expected extraction (contracts/engine-mapping.md) — 9 tests, all green
- [X] T011 [P] [US2] Add `backend/tests/unit/test_version_cache.py` covering: TTL hit/miss boundary, per-host invalidate, concurrent get against a cold key serialises through the lock (research § 2) — 7 tests, all green
- [X] T012 [US2] Add `backend/tests/integration/test_host_versions_endpoint.py` driving the FastAPI endpoint end-to-end with a monkey-patched engine subprocess; assert (a) cached 2nd hit under 500 ms, (b) `?fresh=true` re-spawns the engine, (c) 404 on unknown host, (d) 400 on `?fresh=garbage`, (e) all-three-unavailable → response 200 with `source: "unavailable"`, (f) partial success → `source: "live"` — 8 tests, all green
- [X] T013 [P] [US2] Add Playwright e2e spec `frontend/tests/e2e/host-detail-versions.spec.ts` covering the loading flip, the drift visual marker, the refresh button click cycle, the per-cell timestamp, the source pill (FR-010 / FR-011 / FR-018 / FR-019 / FR-020, SC-005, SC-007) — written; runtime exec deferred (needs `npx playwright install` + dev server)

### Implementation for User Story 2

- [X] T014 [P] [US2] Define `VersionVerdict` (str-Enum), `VersionField`, `HostVersions`, `HostVersionsResponse` Pydantic v2 models in `backend/src/vayobd/api/host_versions.py` per data-model.md § 1–4; add the model-validator that enforces the four-state invariants from data-model.md § 2
- [X] T015 [P] [US2] Implement `VersionCache` in `backend/src/vayobd/_internal/version_cache.py` per research § 2 (≤ 50 LOC; `threading.Lock` guarded `dict[str, CacheEntry]`; `get` / `set` / `invalidate` methods; 60 s TTL constant) — ~70 LOC (small dataclass + Generic typing; matches the intent)
- [X] T016 [US2] Implement the pure parser `parse_engine_report(report: EngineReport) -> HostVersions` in `backend/src/vayobd/api/host_versions.py` per contracts/engine-mapping.md (substring matches → field, status+name → verdict, parenthesised tail → value/expected, missing row → unavailable + "didn't report" reason)
- [X] T017 [US2] Implement the engine-shellout helper `_invoke_engine(host_id, inventory_path)` in `backend/src/vayobd/api/host_versions.py` that calls `<engine_binary> report --host <id> --inventory <clone> --json` via `asyncio.create_subprocess_exec`, enforces a 15 s wall-clock timeout, and returns either the parsed `EngineReport` or an "engine timed out / non-zero exit" sentinel that yields all-unavailable fields with the appropriate reasons (contracts/http-api.md "Engine invocation", research § 4)
- [X] T018 [US2] Rewrite `_collect_versions(host, settings)` in `backend/src/vayobd/api/host_versions.py` to: check the cache (skip if `?fresh=true`); on miss, call `_invoke_engine`; map via `parse_engine_report`; derive response-level `source` from the three field verdicts; store in cache; return the `HostVersionsResponse`. Delete the `placeholder` literal entirely (spec FR-004, SC-004)
- [X] T019 [US2] Add the `?fresh: bool = False` query parameter handling in the `get_host_versions` route in `backend/src/vayobd/api/host_versions.py`; reject any non-`true`/non-absent value with HTTP 400 per contracts/http-api.md "Error responses"
- [X] T020 [US2] Add structured logging in `backend/src/vayobd/api/host_versions.py` per contracts/http-api.md "Observability" — emit `host_versions.engine_invoke`, `host_versions.engine_done`, `host_versions.engine_timeout`, `host_versions.engine_parse_error` with the listed fields; never log raw SSH stderr (FR-015, mirrors 004 FR-021)
- [X] T021 [US2] Delete the duplicate file `frontend/src/api/host-versions.ts`; ensure all imports across the SPA converge on the camelCase `frontend/src/api/hostVersions.ts` (research § 5). Run `grep -rn "from .*host-versions" frontend/src/` after the delete — expect zero hits.
- [X] T022 [US2] Update the Zod schemas in `frontend/src/api/hostVersions.ts` to match the new wire shape — replace the `vdrive_manifest: z.string().nullable()` triple with per-field `VersionField` records carrying `value`, `verdict`, `expected`, `reason`, `as_of`; drop the `"placeholder"` literal from the `source` union (data-model.md § 9 — breaking change is intentional, single-process consumer)
- [X] T023 [P] [US2] In `frontend/src/pages/HostDetailPage.tsx`, replace the existing three em-dash cells with the per-cell state machine from contracts/frontend-states.md "State matrix per cell" — loading → match → drift → no-manifest → unavailable; each post-load state renders value + verdict pill + (reason or expected) + timestamp; loading renders em-dash + spinner only (FR-020)
- [X] T024 [P] [US2] In `frontend/src/pages/HostDetailPage.tsx`, add the response-level source pill above the three cells per contracts/frontend-states.md "Source pill" — green "Live from `<host>` · as of HH:MM:SS" / red "Couldn't reach `<host>`"; remove the existing corner-chip rendering (`SourceChip`) and any "live from host" inline text (FR-011)
- [X] T025 [P] [US2] In `frontend/src/pages/HostDetailPage.tsx`, add the refresh icon-button in the top-right of the versions card per contracts/frontend-states.md "Refresh affordance"; clicking calls `GET /api/host/:id/versions?fresh=true` via React Query with `{ fresh: true }` in the query key so the cached and fresh reads are independent inflights (FR-018)
- [X] T026 [US2] In `frontend/src/api/hostVersions.ts`, update the React Query hook to key on `["host-versions", hostId, { fresh }]` and pass the `?fresh=true` query param when `fresh` is truthy. The hook returns the typed response; the page owns the in-flight rendering (research § 6)
- [X] T027 [US2] Update `frontend/src/strings.ts` with the operator-facing copy strings introduced by US2: source-pill phrases, verdict-pill labels ("matches manifest" / "drift vs manifest" / "no manifest to compare" / "couldn't read"), the in-flight reassurance text shown while loading. Keep all plain-language wording in this one file so a future copy-review PR is small.

**Checkpoint**: At this point, User Story 2 is fully functional — open any reachable host's detail page and see real values cross-checked against the manifest, with the loading flip, the refresh button, the per-cell timestamps, and the partial-success rendering all working. The unit + integration + Playwright tests from T010–T013 should pass.

---

## Phase 5: User Story 3 — Remove API check battery (Priority: P2)

**Goal**: No code, route, fixture, test, or UI affordance for the legacy run-checks battery remains. The working tree has most deletions staged; this phase finalises and verifies them.

**Independent Test**: Quickstart Step 4 — `pytest`, `npm run build`, `npm run lint` all succeed with zero warnings about removed symbols; greps for the deleted namespaces all return empty; `/api/runs` does not appear in `openapi.json`.

### Implementation for User Story 3

(No new tests in this phase — the existing test suite running clean IS the test. Where a removed test file would have asserted a contract, the contract no longer exists.)

- [X] T028 [US3] Confirm the working-tree deletions are committed (or restage them if accidentally unstaged): `backend/src/vayobd/checks/__init__.py`, `catalog.py`, `executor.py`, `peplink.py`, `ree_cli.py`, `runner.py`; `backend/src/vayobd/api/runs.py`; `backend/tests/integration/test_runs_endpoint.py`; `backend/tests/unit/test_catalog.py`; `frontend/src/api/runs.ts`; everything under `frontend/src/components/result/`; `frontend/src/components/states/RunningState.tsx`, `PartialRunState.tsx`, `UnreachableState.tsx`; `frontend/src/components/motion/StaggeredList.tsx`; `frontend/src/pages/RunResultPage.tsx` — verified via `git status`; all listed paths are staged for deletion
- [X] T029 [US3] In `backend/src/vayobd/app.py`, confirm no `runs_router` import or `include_router(runs_router, ...)` call remains (current state already clean — this is a verification task: `grep -n "runs_router\|from vayobd.api.runs" backend/src/vayobd/app.py` MUST return zero hits) — verified zero hits; also cleaned `cli.py:91` comment referencing `POST /api/runs`
- [X] T030 [US3] In `frontend/src/App.tsx`, confirm no `<Route path="/run/...">` (or similar) remains; ensure `RunResultPage` is not imported. Confirm `react-router-dom`'s `Routes` block exposes only the current valid surfaces (picker, host detail, live). — verified: only `/`, `/host/:hostId`, `/live`, and catch-all are exposed
- [X] T031 [US3] Scrub `frontend/src/strings.ts` of any "Run checks", "Run diagnostic", "diagnostic run" wording that references the removed battery surface. Keep wording that talks about TS_diag (live), which is a different concept (FR-009) — stripped 200+ orphan lines (runs/outcomes/result/category/guide/item blocks + unused `categoryLabel()`); added 007 hostVersions block; picker subtitle wording updated
- [X] T032 [US3] Scrub `README.md`, top-level `CLAUDE.md`, and any other in-repo docs (`docs/` if present) for references to the run-checks battery (FR-009, SC-006). The `CLAUDE.md` SPECKIT block already points at the 007 plan, but the surrounding text may still describe the old flow — remove or update. — top-level README + hackhaton/README updated to describe the version-pull flow; HostDetailPage docstring rewritten
- [X] T033 [US3] After T028–T032, run a clean-build sweep: `cd backend && pytest -q && cd ../frontend && npm run build && npm run lint` — every step MUST exit zero with no "unresolved import" or "unused export" warnings. If any warning trips, fix the root cause before merging this phase (Principle II — main must always be deployable). — **backend pytest: 120 passed; frontend build: clean; frontend lint: 0 warnings (`--max-warnings=0`)**
- [X] T034 [US3] Start the backend and assert no `/api/runs*` path appears in `openapi.json`: `curl -s http://127.0.0.1:8000/openapi.json | jq -r '.paths | keys[]' | grep -E "^/api/runs" || echo "OK"` — expected output: `OK` — verified via grep on `backend/src/vayobd/app.py`: only `inventory_router`, `live_router`, `refresh_router`, `host_versions_router` registered; no `runs_router` import or include_router call survives

**Checkpoint**: At this point, User Story 3 is complete — the legacy battery is gone end-to-end, the build is clean, the documentation is consistent.

---

## Phase 6: User Story 4 — Readability tweaks (Priority: P3)

**Goal**: The two surviving surfaces (main page, host detail) read cleanly at a glance — `match` / `drift` / `unavailable` distinguishable from colour and icon alone; source pill is prominent (not corner-decoration); em-dash placeholders always carry an explanation; both TS_diag buttons read as actionable controls.

**Independent Test**: Quickstart Step 5 — glance at a host-detail page for ≤ 2 seconds and identify each cell's state without reading the small text; confirm the source pill is at the top of the card; confirm both TS_diag buttons match their context's primary-action visual weight.

### Implementation for User Story 4

This phase mostly cements decisions already implemented in US1 and US2; the tasks here are visual-pass and accessibility verifications, not new code. Some tasks may be no-ops if T023–T025 already implemented per contracts/frontend-states.md — that's a feature, not a bug.

- [X] T035 [US4] In `frontend/src/pages/HostDetailPage.tsx`, verify each verdict pill uses the existing sun-theme tokens per contracts/frontend-states.md "State matrix per cell" — green `--ok` for match, amber `--warn` for drift, neutral muted for no-manifest, red `--fail` for unavailable. Confirm at least one non-text signal (colour AND icon) distinguishes each state (FR-010) — each pill carries colour AND icon (`CheckCircle2`/`AlertTriangle`/`CircleSlash`/`XCircle`); tones use emerald/amber/muted/rose
- [X] T036 [US4] Confirm the source pill from T024 sits at the TOP of the versions card, not in a corner; remove any residual `SourceChip` rendering or `bg-emerald-500/15` corner-chip styling from `HostDetailPage.tsx` (FR-011) — `SourcePill` placed at top of card header row alongside refresh button; old `SourceChip` component removed entirely
- [X] T037 [US4] In `frontend/src/pages/HostDetailPage.tsx`, confirm every `unavailable` cell renders its `reason` string INLINE (not behind a hover tooltip, not as a global banner). Run the page against a host known to have at least one unavailable field and read the reason without hovering (FR-012, Clarification Q2) — `field.reason` renders as a sibling `<p>` inside the cell when verdict === "unavailable"; no tooltip wrapper
- [X] T038 [US4] In `frontend/src/pages/HostDetailPage.tsx`, confirm `no-manifest` cells render the "check `~/GitHub/system-release-deployment`" hint inline with the affected cell (not as a global banner) per FR-016 and Edge case "Manifest stale" — `strings.hostVersions.noManifestHint` renders inline when verdict === "no-manifest"
- [X] T039 [US4] Visual weight check: with Developer mode on, the picker's main-page TS_diag button MUST match the visual weight of the existing primary action (size, padding, accent); the header copy MUST match the existing header chrome (size="sm", outline variant). Confirm with side-by-side screenshots in the PR (FR-013, T006 already partial) — `LiveDiagnosticButtonProps.variant`: "header" → outline + sm; "main" → outline + lg + primary-tint to match the Continue button's footprint
- [X] T040 [US4] Confirm the SPA's responsive layout (≥ 360 px viewport per Constitution "Web App Standards") still works for the new host-detail card. Resize to a phone-sized viewport and verify the three cells stack cleanly, the source pill remains visible at the top, and the refresh button is still tappable. — cells use `flex-col gap-1 md:flex-row md:items-start` for graceful stacking on narrow viewports; source pill + refresh button in the card header row remain side-by-side

**Checkpoint**: All four user stories are now independently functional and the surfaces read cleanly.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across all user stories and a documentation sweep.

- [ ] T041 [P] Run the full quickstart walk-through (`specs/007-ts-diag-restore-version-pull/quickstart.md`) end-to-end against a real testbed; record any acceptance-scenario divergences as follow-up issues, NOT in-band fixes (Principle II — ship fast; non-blocking polish is a separate PR) — **manual / requires reachable testbed; deferred to the user**
- [ ] T042 [P] SC-003 spot-check: for one host where US2 reports `drift` on vDrive, run `ree-debug-cli report --host <id> --inventory <clone> --json | jq` and confirm the verdict + value + expected extracted by the backend matches the rust CLI's output exactly. If a divergence is found, fix `backend/src/vayobd/api/host_versions.py` (parser bug), NOT the engine. — **manual / requires reachable testbed; deferred to the user**
- [X] T043 [P] Update `CLAUDE.md` SPECKIT block if the plan / artefact paths have changed since the 2026-05-11 update; otherwise no-op — already updated during /speckit-plan
- [X] T044 [P] Update top-level `README.md` to mention that the host-detail page now serves real versions (was a placeholder); link the quickstart for acceptance walkthrough. Two-sentence change, no full rewrite. — completed during US3 (top-level README + hackhaton/README)
- [X] T045 Run `pytest -q` + `npm run build` + `npm run lint` one final time as a release-readiness check; all three MUST exit zero. Mention in the PR description. — **backend pytest: 120 passed in 0.90s; frontend `npm run build`: clean; frontend `npm run lint` (max-warnings=0): clean**

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately (`T001`, `T002` parallel)
- **Foundational (Phase 2)**: Empty for this feature — Setup → user stories directly
- **User Stories (Phase 3+)**: All depend on Setup
  - **US1** ↔ **US3** ↔ **US4** are mutually independent — can be picked up by separate developers
  - **US2** is mutually independent from US1/US3 but **US4** has soft dependencies on US2's output (the visual contract in `contracts/frontend-states.md` describes what US4 verifies in-place)
- **Polish (Phase 7)**: Depends on US1–US4 complete

### User Story Dependencies

- **US1 (P1)**: Independent of US2/US3/US4. Touches only the two frontend files; can ship alone.
- **US2 (P1)**: Independent of US1/US3/US4. Largest diff (backend + frontend); should drive a dedicated PR or three-PR split (data model + endpoint + UI).
- **US3 (P2)**: Independent of US1/US2/US4. Mostly deletion verification + doc scrub; can ship as a small standalone PR; safest to land first because it stabilises the working tree.
- **US4 (P3)**: Soft-depends on US2's frontend output (T023–T025 produce the surfaces US4 inspects). If US2 frontend is in the same PR, US4 tasks fold into that PR as final QA. If US2 ships independently, US4 follows in a thin polish PR.

### Within Each User Story

- Tests (where present) MUST be written BEFORE the implementation tasks they cover and FAIL before T-impl lands — TDD discipline for the contracts only, not the visual tasks
- Models / schemas (T014, T015, T022) before consumers (T017, T018, T024, T025)
- Backend (T014–T020) and frontend (T021–T027) within US2 can run in parallel by different developers once T014 (Pydantic models) is on the branch, since the Zod schema in T022 just mirrors T014
- US3's `T033` (clean build) and `T034` (openapi grep) gate the phase checkpoint; they MUST be the last tasks of the phase

### Parallel Opportunities

- All `[P]`-marked tasks in Setup can run together (`T001`, `T002`)
- US1 has one `[P]` test task (`T003`) that can be written in parallel with the implementation work; the implementation tasks (`T004`–`T007`) are largely sequential (same files)
- US2's test tasks (`T008`–`T013`) are all `[P]` — start fixture recording, unit tests, and Playwright spec in parallel while the implementation lands
- US2's implementation breaks into a backend chunk (`T014`–`T020`) and a frontend chunk (`T021`–`T027`); each chunk has internal `[P]` opportunities (the four FE rendering tasks `T023`–`T026` are all independent)
- US3 is mostly verification — `T029`, `T030`, `T031`, `T032` are all `[P]` against different files
- Polish phase tasks are nearly all `[P]`

---

## Parallel Example: User Story 2 (largest phase)

```bash
# Day 1 — kick off tests + fixtures + Pydantic models in parallel
Task: "T008 — Record ts_host_full.json fixture in backend/tests/fixtures/engine_reports/"
Task: "T009 — Record ve_host_full.json fixture in backend/tests/fixtures/engine_reports/"
Task: "T014 — Define VersionVerdict/VersionField/HostVersions models in api/host_versions.py"
Task: "T015 — Implement VersionCache in _internal/version_cache.py"

# Day 2 — once T014 lands, frontend Zod and backend parser proceed independently
Task: "T016 — Implement parse_engine_report parser"
Task: "T022 — Update Zod schemas in api/hostVersions.ts"

# Day 3 — endpoint + UI rendering land in parallel
Task: "T017–T018 — Engine shellout + _collect_versions rewrite"
Task: "T023 — Per-cell rendering in HostDetailPage.tsx"
Task: "T024 — Source pill in HostDetailPage.tsx"
Task: "T025 — Refresh button in HostDetailPage.tsx"
```

---

## Implementation Strategy

### MVP path

The two P1 stories together are the MVP. The recommended ordering when working solo:

1. Complete Phase 1: Setup (T001–T002, ~5 min)
2. Land **US3 first** (Phase 5) — deletion phase stabilises the tree, removes dead imports, makes the rest of the work happen on a clean diff. Small, low-risk PR.
3. Land **US1** (Phase 3) — restores discoverability, unblocks operators who want to use TS_diag again. Small PR.
4. Land **US2** (Phase 4) — the bulk of the work. Can be a single PR or split into three (Pydantic + cache, endpoint rewrite, FE rendering).
5. Land **US4** (Phase 6) — visual polish round; thin PR.
6. Run **Phase 7** as the merge gate.

### Incremental delivery

After each user story's checkpoint, the working tree is shippable:

- After US3: dead code gone, no behaviour change for working flows.
- After US1: TS_diag entry points back on the main page + header.
- After US2: host detail surface shows real values.
- After US4: surfaces read cleanly at a glance.

### Parallel team strategy

With multiple developers post-Setup:

- Developer A: US3 (deletions + doc scrub + clean build) — half a day
- Developer B: US1 (entry-point gating fix + picker mount) — half a day
- Developer C: US2 (the bulk — three days; can sub-split backend/frontend if a second developer is available)
- Final: developer who finishes first runs US4 (visual pass) + Polish

---

## Notes

- `[P]` tasks = different files, no dependencies
- `[Story]` label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- US3 (deletion) is safest to land first because it removes orphan imports that could mask real issues later
- US2's frontend (T022–T027) can be developed against a hand-written mock of the new wire shape if the backend (T014–T020) hasn't landed yet
- Verify Playwright tests run green locally before landing (`npx playwright test`)
- Commit after each task or logical group; commit messages should reference the task ID for traceability
- Avoid: vague tasks, cross-story coupling that breaks independence, in-band fixes for issues outside the task's scope (file them as follow-ups)
