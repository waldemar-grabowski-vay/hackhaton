---

description: "Task list — Restore host check battery, fix Live Diagnostic regression, integrate Wilhelm + Ezequiel"
---

# Tasks: Restore host check battery, fix Live Diagnostic regression, integrate Wilhelm + Ezequiel

**Input**: Design documents from `/specs/008-restore-host-checks-fix-live/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/` (http-api, reecu-pipeline, strings-merge, ezequiel-cherry-pick, ve-signals, ve-errq), `quickstart.md`

**Tests**: Test tasks are included where contracts or `data-model.md` explicitly name fixture / unit / e2e files. They are interleaved with implementation rather than enforced TDD-first — the constitution prioritises Ship Fast (Principle II) and a working demo, not red-green-refactor ceremony.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)
- File paths are **relative to the repo root** (`/home/waldemar-grabowski/GitHub/hackhathon/`)

## Path Conventions

Web app inside the monorepo:

- Backend: `hackhaton/backend/src/vayobd/`
- Frontend: `hackhaton/frontend/src/`
- Engine: `hackhaton/engine/ree-debug-engine/src/`
- Specs / docs: `hackhaton/specs/008-restore-host-checks-fix-live/`
- Desktop reference (read-only): `TS_diagnostic_tool/`

Restoration sources:

- `origin/005-ve-harness-repair-guide` — Ezequiel's branch (frontend tier)
- `01d3979` — local pre-007 commit (backend + engine tiers)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify the branch / clone state required for restoration and lookups. No code edits.

- [X] T001 Verify the working tree is on `008-restore-host-checks-fix-live`. **Result**: branch created from `006-deb-package-distribution` HEAD (commit `ff9eaae`). Surprise — all 21 "deleted" files were present in HEAD (baked in by WIP commit `d69884d`); plan-adapted to merge rather than restore.
- [X] T002 [P] Confirm `ree-reecu` clone path. **Result**: `/home/waldemar-grabowski/GitHub/ree-reecu` per `~/.config/vayobd/settings.toml`.
- [X] T003 [P] Find the VE errq subpath. **Result**: **does not exist** in the current clone (`find $REE_REECU_ROOT/ve -name "*errq*"` returns empty). TS path is `/home/waldemar-grabowski/GitHub/ree-reecu/ts/6_tools/TS_Generators/Errq/ts_errq_cfg_generator/csv/`. VE resolver in T034 bakes in the analogous `/ve/6_tools/VE_Generators/Errq/ve_errq_cfg_generator/csv/` path; **at runtime** the VE branch will exercise FR-012 degraded-mode (per `contracts/ve-errq.md` VE-ERRQ-2/4) until the team populates the VE subpath.
- [X] T004 [P] Grep Wilhelm's VE state-signal list. **Result**: `VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`, `VE_PRND_STATE` (3 signals).
- [X] T005 [P] Verify refs reachable. **Result**: `origin/005-ve-harness-repair-guide` → `e944985`; `01d3979` → `01d3979`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tiered restoration cherry-pick + 3-way merges + route wiring + spec dir rename. Every user story depends on these files existing in the working tree.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. The Tier A / B / C cherry-pick tasks (T006–T011) can run in parallel; the 3-way merge tasks (T012–T015) depend on T006 (`HarnessDiagram` etc. need to be in place before strings.ts is reconciled against them).

### Tier A — Frontend from `origin/005-ve-harness-repair-guide`

- [X] T006 Tier A.1 — improved replacements. **Adapted**: clean checkout would have clobbered HEAD's improvements in `ResultGroup.tsx` (+46 lines: collapsible feature). Instead: small Ezequiel improvements applied to `HarnessDiagram.tsx` and `TelestationDiagram.tsx` via Edit (`?? "board"` fallback), and `RepairGuideSheet.tsx` 3-way merged via `git merge-file` (clean merge, no conflict).
- [X] T007 [P] Tier A.2 — net-new files: 7 files cherry-picked from `origin/005-ve-harness-repair-guide` (3 components + 4 assets). All present.
- [X] T008 [P] Tier A.3 — **NO-OP**: all 11 supposedly-deleted frontend files already exist in HEAD with content matching Ezequiel's branch (CategoryBadge, DiagnosticItemRow, ResultHero, EmptyInventoryState, PartialRunState, RunningState, UnreachableState, StaggeredList, RunResultPage, api/runs.ts byte-identical between HEAD and Ezequiel; `ResultGroup.tsx` HEAD has +46 lines Ezequiel doesn't — kept HEAD per "HEAD wins" rule).

### Tier B — Backend from local commit `01d3979`

- [X] T009 [P] **NO-OP**: backend `checks/*` + `api/runs.py` all present in HEAD with the same or improved content vs `01d3979`. Small recent improvements in `catalog.py` (+6 -6), `executor.py` (+6 -2), `runner.py` (+4 -0) — KEPT per "HEAD wins" rule.
- [X] T010 [P] **NO-OP**: `test_runs_endpoint.py` and `test_catalog.py` already exist and match `01d3979` byte-identically. Discovered + fixed one stale assertion in `test_catalog.py`: `main_can_bus_reachable` is now in the telestation catalog (catalog evolved post-`01d3979`); test updated from `not in ids` → `in ids`.

### Tier C — Engine Rust from local commit `01d3979`

- [X] T011 [P] **NO-OP**: all 6 engine Rust check files in HEAD byte-identical to `01d3979`.

### 3-way hand-merges (after T006 lands)

- [X] T012 3-way merge `hackhaton/frontend/src/strings.ts` — merged via `git merge-file` with merge-base `c84f2cf` against `origin/005-ve-harness-repair-guide`. **Clean merge, no conflict**. Build verified the merged file resolves all `t()` calls.
- [X] T013 [P] 3-way merge `hackhaton/frontend/src/connectorLocations.ts` — merged via `git merge-file`. **Clean merge**.
- [X] T014 [P] 3-way merge `hackhaton/frontend/src/connectorSpecs.ts` — merged via `git merge-file`. **Clean merge** (Ezequiel's +814 lines unioned with HEAD's content).
- [X] T015 [P] 3-way merge `hackhaton/frontend/src/guides.ts` — merged via `git merge-file`. **Clean merge** (Ezequiel's +747 lines unioned with HEAD). Removed one unused `CIPG_F_SVG` import revealed by build.

### Route + module wiring

- [X] T016 `App.tsx` merged via `git merge-file` — 1 conflict at imports (HEAD had removed `RunResultPage` import; Ezequiel added `RepairGuidesPage` and kept `RunResultPage`). Resolved per "HEAD wins": kept HEAD's removal of `RunResultPage`, added Ezequiel's `RepairGuidesPage` import. The `/repair-guides` route is registered in the `<Routes>` block.
- [X] T017 **NO-OP**: `runs_router` already included in `app.py:31, 159`.

### Spec dir rename

- [X] T018 Spec dir pulled + renamed: `hackhaton/specs/005-ve-harness-repair-guide/` (from Ezequiel) → `hackhaton/specs/009-ve-harness-repair-guide/`. `**Feature Branch**:` updated to `009-ve-harness-repair-guide` in the renamed `spec.md`.

### Post-restoration verification

- [X] T019 `git status --short | grep "^ D "` returns empty. ✓
- [X] T020 [P] `npm run build && npm run lint` exits zero. ✓ Build emits `dist/` artefacts (1.16 MB JS bundle, gzip 315 kB; below the 500 kB warning threshold for individual assets is informational only). Fixes required during the gate: 3 TS type errors (`UnreachableState.tsx` `||` instead of `??` + `!` non-null on `__default`; `guides.ts` unused `CIPG_F_SVG` import; `RepairGuidesPage.tsx` unused `categoryLabel` import); 2 lint errors (`eslint-disable-next-line react-hooks/exhaustive-deps` referencing an unconfigured rule — removed in both diagram components).
- [X] T021 [P] `pytest backend/ -q` → **132 passed, 1 warning** ✓. One pre-existing stale assertion in `test_catalog.py` fixed (see T010).

**Checkpoint**: Foundation ready — all user story work can now begin.

---

## Phase 3: User Story 1 — Restore the host check battery on the host-detail page (Priority: P1) 🎯 MVP

**Goal**: The host-detail page renders BOTH the 007 version card AND the full pre-007 categorised check battery — vDrive, Peplink, network, hardware, configuration, harness diagrams, repair-guide sheets — within 10 s of mount.

**Independent Test**: Open the host-detail page for a reachable TS host. Within 10 s of landing, both the version card (vDrive / vREECU / SEC with verdict pills + as-of timestamps + source pill + refresh button) AND the categorised check battery (Working / Needs attention groups; failed items show repair-guide buttons) render. The page reads top-down: versions → checks → guides.

### Implementation for User Story 1

- [ ] T022 [US1] Add `HostDetailResponse` model in `hackhaton/backend/src/vayobd/models.py` per `data-model.md` §7 (composes `Host`, `HostVersions`, optional `DiagnosticRun`, `source: Literal["live", "unavailable"]`)
- [ ] T023 [US1] Extend `hackhaton/backend/src/vayobd/api/host_versions.py::_collect_versions` to compose the REECU pipeline + non-REECU pipeline outputs into a unified `HostDetailResponse` (per `data-model.md` §7 + `contracts/http-api.md` §1); rename the response type from `HostVersionsResponse` to `HostDetailResponse` at the FastAPI return-annotation site
- [ ] T024 [US1] Change the `VersionCache[…]` type parameter at the import / instantiation site in `hackhaton/backend/src/vayobd/api/host_versions.py` from `HostVersionsResponse` to `HostDetailResponse` (per `research.md` §6 + `data-model.md` §8 — the generic itself is unchanged)
- [ ] T025 [P] [US1] Create new module `hackhaton/backend/src/vayobd/api/_reecu_capture.py` implementing the 4-second bounded capture wrapper around `vayobd.live.session.LiveSession` (per `contracts/reecu-pipeline.md` §1–§8a — entry point `async def capture_reecu_state(host_id, host_type, settings) -> dict[str, VersionField]`; pass `host_type` through to choose the signal allowlist)
- [ ] T026 [P] [US1] Add Zod schema for `HostDetailResponse` in `hackhaton/frontend/src/api/hostVersions.ts` (extend the existing `HostVersionsResponseSchema` with optional `run: DiagnosticRunSchema | null`; add `DiagnosticRunSchema` mirroring `data-model.md` §5)
- [ ] T027 [P] [US1] Restore / verify fixture `hackhaton/backend/tests/fixtures/runs/ts_host_complete.json` (from `01d3979`; covers full pre-007 catalog for a TS host) — per `data-model.md` §12
- [ ] T028 [P] [US1] Restore / verify fixture `hackhaton/backend/tests/fixtures/runs/ve_host_complete.json` (from `01d3979`; same coverage for a VE host)
- [ ] T029 [US1] Update `hackhaton/backend/tests/unit/test_host_versions_collector.py` (restored by Phase 2) to assert FR-011 — REECU rows are routed into `versions`, NOT `run.items`; every non-REECU row in the engine fixture appears in `run.items` exactly once

**Checkpoint**: At this point, US1 is fully functional and testable independently. The host-detail page renders the unified view; backend tests pass; the SPA's `HostDetailPage` can already consume the unified response (composition layout lives in Phase 5 / US3 but US1 itself is independently demoable).

---

## Phase 4: User Story 2 — Fix Live Diagnostic so it actually works (Priority: P1)

**Goal**: `/live` works end-to-end on both TS and VE hosts. Page mounts, inventory list populates (with `TS` / `VE` pill per row), Connect produces decoded CAN signals within 10 s, errq surfaces either active errors or a plain-language degraded-mode message. VE hosts additionally show `VE_*` state signals decoded through the same DBC.

**Independent Test**: With Developer mode on, click "Live diagnostic". The page mounts within 5 s with the connection dialog and inventory list (each row carrying a `TS` / `VE` pill). Pick a reachable TS host, click Connect → decoded TS-channel signals stream within 10 s. Pick a reachable VE host, click Connect → decoded `VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`, `VE_PRND_STATE` (and any further `VE_*` from Wilhelm's list) appear in the state panel within 10 s.

### LD failure-mode fixes (research §1)

- [ ] T030 [US2] Add SPA-mount detection warning in `hackhaton/backend/src/vayobd/cli.py::_cmd_run`: if `Settings.static_dir` is unset AND there's no reachable source-tree `frontend/dist/index.html`, log a one-line warning at startup pointing the user at `/usr/bin/vayobd` or `VAYOBD_STATIC_DIR=…` (per `research.md` §1a)
- [ ] T031 [P] [US2] Tighten DBC glob patterns in `hackhaton/backend/src/vayobd/live/dbc_decoder.py::find_dbc` to include case-insensitive variants AND `ve/…/dbcs/`, `ts/…/dbcs/` paths; surface the matched DBC path + message count on the `/live` page status surface (per `research.md` §1b)
- [ ] T032 [P] [US2] Surface errq degraded mode prominently in `hackhaton/frontend/src/pages/LiveDiagnosticPage.tsx` (a labelled banner in the errq panel, not just a backend log) per 004 FR-012 wording (per `research.md` §1c)

### VE state-signal port (contracts/ve-signals.md)

- [ ] T033 [US2] Extend the state-panel signal allowlist in `hackhaton/backend/src/vayobd/live/candump_runner.py` (location to confirm at task time; alternative: a `frontend/src/lib/stateSignals.ts` constant) — add every `VE_*` entry from the T004 grep output; verify the existing TS_* entries remain untouched (per `contracts/ve-signals.md`)

### VE errq CSV resolution (contracts/ve-errq.md)

- [ ] T034 [US2] Add the VE errq CSV resolver to `hackhaton/backend/src/vayobd/live/errq_bridge.py`: branch on `host_type` (`HostType.VEHICLE` → VE subpath from T003; otherwise TS subpath unchanged); preserve the 004 FR-012 degraded-mode fallback identically for both branches (per `contracts/ve-errq.md`)

### Inventory dialog UX

- [ ] T035 [US2] Add the `TS` / `VE` pill to each row in `hackhaton/frontend/src/components/live/InventoryDialog.tsx` (location to confirm at task time; alternative: `hackhaton/frontend/src/pages/LiveDiagnosticPage.tsx`'s inventory section) — sourced from `host.type`; pill styling uses the existing 002 sun-theme palette tokens (no new palette colour) (FR-019)

### Tests for US2

- [ ] T036 [P] [US2] Add `hackhaton/backend/tests/unit/test_live_state_filter.py` exercising both TS-host (TS_* visible, VE_* absent) and VE-host (VE_* visible) decoded-frame filtering against a recorded fixture
- [ ] T037 [P] [US2] Add `hackhaton/backend/tests/unit/test_errq_bridge.py` covering: TS-host resolver, VE-host resolver, missing-subpath fallback to 004 FR-012 degraded-mode (per `contracts/ve-errq.md` acceptance contract VE-ERRQ-1..4)
- [ ] T038 [P] [US2] Add `hackhaton/backend/tests/unit/test_reecu_capture.py` driving `capture_reecu_state` against a recorded candump fixture (one TS, one VE); asserts the 4-second window + signal extraction match `contracts/reecu-pipeline.md` §1–§5
- [ ] T039 [P] [US2] Add Playwright spec `hackhaton/frontend/tests/e2e/live-diagnostic-ve.spec.ts` covering VE-host Connect → state panel decode → errq panel render (or degraded-mode fallback) per `contracts/ve-signals.md` and `contracts/ve-errq.md`

**Checkpoint**: US1 + US2 both work independently. Live Diagnostic surface is fully restored; VE-host support is end-to-end testable.

---

## Phase 5: User Story 3 — Unified host-detail layout: versions and checks side by side (Priority: P2)

**Goal**: The host-detail page composes the version card (top) and the categorised check battery (below) into one coherent layout. Operators read top-down: "what version" → "what's wrong" → "how to fix". Phone-sized viewport (≥360 px) stacks cleanly.

**Independent Test**: Open the host-detail page for a host that has BOTH a version drift AND a failing check. Within 3 seconds of looking at the page, the operator can see (a) the version card with drift indicator at the top, (b) the failed check under "Needs attention" below, (c) a repair-guide button on the failed row. Resizing to 360 px width — no horizontal scrolling. Clicking the guide opens it as a sheet (not a route change), version card remains visible behind.

### Implementation for User Story 3

- [ ] T040 [US3] Update `hackhaton/frontend/src/pages/HostDetailPage.tsx` layout per `data-model.md` §7: header → version card (007's components) → restored result groups (ResultHero + ResultGroup pair for Working / Needs attention); RunningState renders below the version card when `data.run` is null
- [ ] T041 [US3] Route REECU rows from `data.versions` to the version card ONLY; route non-REECU rows from `data.run.items` to result groups ONLY (FR-011); add a frontend filter / assert in `HostDetailPage` to drop any duplicates the engine accidentally double-emits
- [ ] T042 [US3] Verify phone-viewport layout (≥360 px wide) — version card and result groups stack vertically with no horizontal scroll (Constitution Web App Standards); fix any Tailwind / shadcn layout issue surfaced
- [ ] T043 [US3] Confirm `<RepairGuideSheet>` opens as a sheet over the page (no route change); the version card remains visible behind it per Ezequiel's improved component

**Checkpoint**: US3 done. Page composition is coherent across breakpoints.

---

## Phase 6: User Story 4 — No regressions to 007's wins (Priority: P2)

**Goal**: Every 007 win — per-field verdict pills, 60 s TTL cache, refresh affordance with `?fresh=true`, per-cell as-of timestamps, dual TS_diag entry points, Developer-mode toggle, removal of "Run check" copy — survives 008. Re-run the 007 quickstart acceptance walkthrough end-to-end; every 007 scenario still passes.

**Independent Test**: Run `specs/007-…/quickstart.md` end-to-end (refresh button, TTL cache, em-dash + spinner, dual entry-point visibility, plain-language errors, no "Run check" wording). Zero regressions.

### Implementation for User Story 4

- [ ] T044 [US4] Verify the version card refresh button on `hackhaton/frontend/src/pages/HostDetailPage.tsx` still re-pulls with `?fresh=true` and the check battery either re-runs alongside OR keeps prior result (never silently disappears) — exercise manually + assert in an existing Playwright spec
- [ ] T045 [US4] Verify the dual TS_diag entry points (header copy + main-page primary action) in `hackhaton/frontend/src/components/chrome/AppHeader.tsx` and `hackhaton/frontend/src/pages/HostPickerPage.tsx` appear / disappear together when Developer mode toggles
- [ ] T046 [US4] Verify the restored battery copy in `hackhaton/frontend/src/strings.ts` uses action-oriented phrasing — no "Run check" / "Run diagnostic" reintroduced anywhere in user-facing UI (FR-016); the `wizard.host.subtitle` reversion is the ONLY pre-007 wording that comes back
- [ ] T047 [US4] Verify the TTL cache serves a <500 ms cache-hit re-render: navigate away and back to the host-detail page within 60 s; confirm no spinner, no engine call, network tab shows the cached response (SC-005)
- [ ] T048 [US4] Run the 007 quickstart end-to-end at `hackhaton/specs/007-ts-diag-restore-version-pull/quickstart.md`; record any deviation in the PR description

**Checkpoint**: US4 confirmed. 007's win surface intact.

---

## Phase 7: User Story 5 — Browse the repair guide library independent of host (Priority: P3)

**Goal**: A top-level "Repair guides" surface, reachable from a chrome entry point on every page, lists every guide registered in `guideLibrary.ts`. Guides open through the same `RepairGuideSheet` component as the host-detail surface. The entry point is operator-facing — NOT Developer-mode-gated.

**Independent Test**: From any page in the SPA, click the "Repair guides" header link. `RepairGuidesPage` mounts; every guide in `guideLibrary.ts` is listed grouped sensibly; clicking an entry opens `RepairGuideSheet` with the harness diagram + step list. Toggle Developer mode off — link remains visible.

### Implementation for User Story 5

- [ ] T049 [US5] Add the "Repair guides" link to `hackhaton/frontend/src/components/chrome/AppHeader.tsx` per `research.md` §9: a secondary nav item beside the existing primary actions, routing to `/repair-guides`; NOT inside any Developer-mode-gated branch
- [ ] T050 [US5] Verify `/repair-guides` route mounts `RepairGuidesPage` (cherry-picked in T007); the page renders every guide registered in `guideLibrary.ts`, grouped sensibly (harness or host type — pick whatever grouping `guideLibrary.ts` exposes)
- [ ] T051 [US5] Verify `<RepairGuideSheet>` opens with IDENTICAL props / output whether triggered from the host-detail surface (US3) or from a library entry (FR-018); a single Playwright assertion comparing the rendered DOM for the same guide from both entry points
- [ ] T052 [US5] Confirm the "Repair guides" link in `AppHeader.tsx` remains visible when Developer mode is OFF (operator-facing knowledge per FR-017 + Constitution Principle III)

**Checkpoint**: All user stories complete and independently testable.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final acceptance, regression sweep, and PR-readiness.

- [ ] T053 [P] Run `cd hackhaton && pytest backend/ -q` — MUST exit zero
- [ ] T054 [P] Run `cd hackhaton/frontend && npm run build && npm run lint` — MUST exit zero
- [ ] T055 [P] Run `cd hackhaton/frontend && npx playwright test` — all e2e specs (including the new `live-diagnostic-ve.spec.ts`) MUST pass
- [ ] T056 SC-004 grep — `cd hackhaton/frontend && npm run build && grep -rE 'strings\.[a-z]+\.' dist/ | head` — MUST return zero hits (no literal path keys in rendered DOM)
- [ ] T057 Manual quickstart 9a (TS-host walkthrough) — run the 9-substep walk-through in `hackhaton/specs/008-restore-host-checks-fix-live/quickstart.md` Step 9a against a reachable TS host; confirm every US1, US2, US3, US4 acceptance criterion
- [ ] T058 Manual quickstart 9b (VE-host walkthrough) — run the 4-substep VE walk-through in `quickstart.md` Step 9b against a reachable VE host; confirm SC-009, VE-SIG-1..4, VE-ERRQ-1..4. If no VE testbed is reachable, document the missing-VE-testbed state in the PR description AND confirm the VE-ERRQ-2 / VE-ERRQ-4 fallback path lit up correctly in T037 (errq degraded-mode message rendered, raw frames + state panel still streaming)
- [ ] T059 Manual quickstart 9c (library walkthrough) — confirm US5 + SC-008 (every guide reachable in ≤2 clicks from entry point)
- [ ] T060 Update the PR description to include: (a) SC-001..SC-009 confirmation table, (b) the VE testbed status (tested live or fallback-only), (c) the VE errq subpath that T003 found (or "missing — degraded mode verified" if absent), (d) the chrome entry-point chosen (header link), (e) the four 3-way merge files' final state with diff stats

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 sequential; T002–T005 parallel after T001. Total: ~5 minutes.
- **Foundational (Phase 2)**: blocks Phases 3–7.
  - T006 (Tier A.1 improved replacements) blocks T012 (strings.ts merge needs the improved components in place to verify imports).
  - T007, T008, T009, T010, T011 — parallel cherry-picks (different files / sources).
  - T012 sequential after T006.
  - T013, T014, T015 parallel after T012 (different files, same merge rule).
  - T016, T017, T018 — parallel after the cherry-picks land.
  - T019, T020, T021 — sequential verification gate after all merges land.
- **Phase 3 (US1)**: depends on Phase 2 (needs `HostDetailResponse` infrastructure, restored backend `checks/` package).
- **Phase 4 (US2)**: depends on Phase 2 AND on T003 / T004 (VE lookups) from Phase 1; no hard dependency on Phase 3.
- **Phase 5 (US3)**: depends on Phase 3 (`HostDetailResponse` must exist) but not on Phase 4.
- **Phase 6 (US4)**: depends on Phases 3 + 4 + 5 (re-runs the 007 walkthrough across all surfaces).
- **Phase 7 (US5)**: depends on Phase 2 only (library files cherry-picked in T007 + route registered in T016).
- **Phase 8 (Polish)**: depends on all desired user stories. T053–T055 parallel; T056 sequential after build; T057–T060 sequential (manual walkthroughs share a testbed).

### User Story Dependencies

- **US1 (P1)** — independent, MVP-shippable on its own (assuming Phase 2 complete).
- **US2 (P1)** — independent of US1; can be implemented in parallel by a second developer once Phase 2 is done.
- **US3 (P2)** — extends US1's data; depends on US1's `HostDetailResponse` being shippable.
- **US4 (P2)** — verification story; runs after US1/US2/US3 land.
- **US5 (P3)** — independent of US1/US2/US3/US4; depends only on Phase 2's cherry-pick + route registration.

### Within Each User Story

- Within US1: T022 (model) → T023 (collector uses model) → T024 (cache type param refers to model); T025/T026/T027/T028 parallel; T029 runs after the collector + fixtures exist.
- Within US2: T030/T031/T032 (LD fixes) parallel with T033/T034 (VE port); T035 (inventory pill) parallel; tests T036/T037/T038/T039 parallel after their target modules exist.
- Within US3: T040 → T041 → T042 → T043 sequential (each builds on the prior layout).
- Within US4: T044/T045/T046/T047 parallel; T048 sequential (final 007 walkthrough).
- Within US5: T049 → T050 → T051 → T052 sequential.

### Parallel Opportunities

- All [P] tasks in Phase 1 (T002–T005).
- Within Phase 2: T006–T011 parallel cherry-picks (different files); T013–T015 parallel merges (after T012).
- Once Phase 2 completes: US1 / US2 / US5 can proceed in parallel (different developers).
- Within US1: 4 parallel implementation tasks (T025, T026, T027, T028).
- Within US2: 8 parallel tasks (4 implementation + 4 test files).
- Within US4: 4 parallel verification tasks (T044, T045, T046, T047).
- Polish: T053, T054, T055 parallel.

---

## Parallel Example: Foundational Phase 2 cherry-picks

```bash
# After T006 lands (HarnessDiagram etc. in place), launch the parallel cherry-picks together:
Task: "Tier A.2 net-new files (T007)"               # frontend/src/components/chrome/RepairGuideLibraryDialog.tsx + 6 others
Task: "Tier A.3 frontend pre-007 deletions (T008)"  # 11 components/states/pages
Task: "Tier B backend checks + runs (T009)"         # 7 backend files
Task: "Tier B backend tests + fixtures (T010)"      # 2 test files + fixtures
Task: "Tier C engine Rust checks (T011)"            # 6 .rs files

# Then after T012 (strings.ts) lands:
Task: "Merge connectorLocations.ts (T013)"
Task: "Merge connectorSpecs.ts (T014)"
Task: "Merge guides.ts (T015)"

# And in parallel with those:
Task: "App.tsx route wiring (T016)"
Task: "app.py include_router (T017)"
Task: "005→009 spec rename (T018)"
```

## Parallel Example: User Story 2 implementation

```bash
# After Phase 2 + T003 + T004 done:
Task: "SPA mount detection (T030)"             # backend/src/vayobd/cli.py
Task: "DBC glob tightening (T031)"             # backend/src/vayobd/live/dbc_decoder.py
Task: "errq degraded UI (T032)"                # frontend/src/pages/LiveDiagnosticPage.tsx
Task: "VE state allowlist (T033)"              # backend/src/vayobd/live/candump_runner.py
Task: "VE errq resolver (T034)"                # backend/src/vayobd/live/errq_bridge.py
Task: "TS/VE pill in inventory (T035)"         # frontend/src/components/live/InventoryDialog.tsx

# Tests in parallel once implementation lands:
Task: "test_live_state_filter.py (T036)"
Task: "test_errq_bridge.py (T037)"
Task: "test_reecu_capture.py (T038)"
Task: "live-diagnostic-ve.spec.ts (T039)"
```

---

## Implementation Strategy

### MVP scope (US1 only)

1. Phase 1 (Setup).
2. Phase 2 (Foundational — tiered restoration, merges, wiring, spec rename, verification).
3. Phase 3 (US1 — `HostDetailResponse` composition).
4. **STOP and VALIDATE**: open the host-detail page for a TS host; both version card AND check battery render. The page reads top-down.
5. Demo-ready as of this point — the regression user reported is resolved.

### Incremental delivery (one PR but staged commits)

1. Setup + Foundational → checkpoint: tree is clean, builds green, tests pass.
2. US1 → checkpoint: host-detail page restored.
3. US2 → checkpoint: Live Diagnostic works on TS + VE, errq panel renders.
4. US3 → checkpoint: unified layout reads top-down on all breakpoints.
5. US4 → checkpoint: 007 walkthrough passes; no regressions.
6. US5 → checkpoint: library reachable from chrome; same guide-sheet UX everywhere.
7. Polish → PR-ready.

### Parallel team strategy

With multiple developers post-Phase 2:

- Dev A: US1 + US3 (host-detail axis).
- Dev B: US2 (Live Diagnostic + VE port).
- Dev C: US5 (library) + US4 (regression sweep at the end).

US1 and US3 share `HostDetailPage.tsx`, so they pair best on one developer. US2 is self-contained (live/ backend + LiveDiagnosticPage). US5 touches only chrome + RepairGuidesPage + verification.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in the same phase.
- [Story] label maps task to specific user story for traceability.
- Each user story is independently completable and testable per the spec's "Independent Test" sections.
- Tests are included where the design docs explicitly name fixture / unit / e2e files; they are not strict TDD-first (per Constitution Principle II "Ship Fast").
- Commit after each task or logical group; the foundational phase is a natural break point.
- Stop at any checkpoint to validate the story increment independently.
- `/usr/bin/vayobd` (the .deb-installed wrapper) is the canonical runtime for the manual walkthroughs; bypassing pyenv shims is implicit (per FR-015 + research §1a).
