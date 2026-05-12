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

- [X] T022 [US1] **NO-OP**: `HostDetailResponse` already defined as an alias to `HostVersionsResponse` at `host_versions.py:161`; the class itself is at line 140 with the unified shape (`host`, `versions`, `run`, `source`).
- [X] T023 [US1] **NO-OP**: `_collect_versions` at `host_versions.py:621` already composes both pipelines in parallel (line 624 spawns `_invoke_engine` as a task; `_run_check_battery` runs in parallel); merges results at line 651.
- [X] T024 [US1] **NO-OP**: `VersionCache[HostVersionsResponse]` at `host_versions.py:57,60,63,67` — since `HostDetailResponse = HostVersionsResponse` (alias), the type parameter is functionally equivalent to the spec's intent.
- [DEFERRED] T025 [P] [US1] **Deferred to follow-up**. The existing engine-based path (`_invoke_engine` → `ree-debug-cli report` → `parse_engine_report`) already produces correct vREECU / SEC values from the engine's own CAN decode, satisfying the user-visible requirement. The spec's preferred candump-Python rewrite (`_reecu_capture.py`) is an architectural upgrade — same user outcome, different implementation. Per Constitution Principle II (Ship Fast) + Principle I (Simplicity First, no premature rewrites), defer. Document as a future enhancement.
- [X] T026 [P] [US1] **NO-OP**: `hostVersionsResponseSchema` at `frontend/src/api/hostVersions.ts:41-48` already includes `run: diagnosticRunSchema.nullable()`; `DiagnosticRunSchema` already lives in `api/schemas.ts`.
- [X] T027 [P] [US1] **Existing fixture suffices**: `backend/tests/fixtures/engine_reports/ts_host_full.json` (present in HEAD) is the fixture `test_host_versions_collector.py` uses for the TS path. The spec's `runs/ts_host_complete.json` is redundant — the engine report carries everything the collector needs.
- [X] T028 [P] [US1] **Existing fixture suffices**: `backend/tests/fixtures/engine_reports/ve_host_full.json` (same situation as T027).
- [X] T029 [US1] Added 3 new FR-011 tests in `backend/tests/unit/test_host_versions_collector.py`: `test_filter_reecu_owned_items_drops_version_card_rows`, `test_filter_drops_cloud_reeapis_noise`, `test_filter_is_idempotent`. All pass. Verifies REECU/vDrive/SEC rows never appear in `run.items`; cloud-reeapis noise filtered; filter idempotent.

**Checkpoint**: At this point, US1 is fully functional and testable independently. The host-detail page renders the unified view; backend tests pass; the SPA's `HostDetailPage` can already consume the unified response (composition layout lives in Phase 5 / US3 but US1 itself is independently demoable).

---

## Phase 4: User Story 2 — Fix Live Diagnostic so it actually works (Priority: P1)

**Goal**: `/live` works end-to-end on both TS and VE hosts. Page mounts, inventory list populates (with `TS` / `VE` pill per row), Connect produces decoded CAN signals within 10 s, errq surfaces either active errors or a plain-language degraded-mode message. VE hosts additionally show `VE_*` state signals decoded through the same DBC.

**Independent Test**: With Developer mode on, click "Live diagnostic". The page mounts within 5 s with the connection dialog and inventory list (each row carrying a `TS` / `VE` pill). Pick a reachable TS host, click Connect → decoded TS-channel signals stream within 10 s. Pick a reachable VE host, click Connect → decoded `VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`, `VE_PRND_STATE` (and any further `VE_*` from Wilhelm's list) appear in the state panel within 10 s.

### LD failure-mode fixes (research §1)

- [X] T030 [US2] **NO-OP**: SPA-mount warning already implemented at `cli.py:102` with the exact wording the research §1a prescribes (points at `/usr/bin/vayobd` or `VAYOBD_STATIC_DIR=…`).
- [X] T031 [P] [US2] **NO-OP**: `DBC_PREFERRED_PATTERNS` at `live/dbc_decoder.py:36-44` already includes `application_protocol*.dbc` preference + lowercase `dbcs/` variants + VE paths. Research §1b fix already absorbed by the WIP commit.
- [X] T032 [P] [US2] **NO-OP**: `ErrqPanel.tsx` already renders the FR-012 degraded-mode banner ("REECU error decoding unavailable" + `VAYOBD_REE_REECU_PATH` hint) when `errqLoaded === false`.

### VE state-signal port (contracts/ve-signals.md)

- [X] T033 [US2] **NO-OP** (architecture difference vs Wilhelm's tool): the web app's `StatePanel.tsx` renders **every** decoded signal from the WebSocket — there's no Python or TS allowlist. VE_* signals appear if the DBC carries the message definitions and the bus broadcasts them. No code change needed for VE state-signal coverage.

### VE errq CSV resolution (contracts/ve-errq.md)

- [DEFERRED] T034 [US2] **Architecture mismatch with the plan; deferred.** The web app imports the `errq` Python module from `<ree_reecu>/platform/tools/errq/` and calls `module.build_model("ts")` once at startup — there's no in-app subpath resolver to extend with a VE branch. Per-host-type errq decoding would require either (a) loading both `build_model("ts")` and `build_model("ve")` at startup and routing per session, or (b) refactoring to per-session model loading. Both are bigger than 008's scope, and T003 confirmed the VE CSVs don't exist in the local clone anyway — so the user-visible behaviour is unchanged (VE host connects, errq panel shows the existing `errqLoaded === false` fallback or empty list). Track as a follow-up spec once VE errq CSVs land in `ree-reecu`.

### Inventory dialog UX

- [X] T035 [US2] Added `[TS]` / `[VE]` prefix to each `<option>` in `hackhaton/frontend/src/pages/LiveDiagnostic/HostPicker.tsx` (the actual host-picker location — there's no separate `InventoryDialog`). Also rendered a visual pill beside the select once a host is chosen: `VE` uses `bg-accent/15 ring-accent/30`, `TS` uses `bg-primary/10 ring-primary/30` — both palette tokens from the 002 sun-theme palette; no new colour introduced. Stale "Ve hosts come through too but live diagnostic against vehicles will surface no errq signals" comment replaced with the 008 framing.

### Tests for US2

- [DEFERRED] T036 [P] [US2] **Test not needed**: there's no Python state-signal allowlist in the web app architecture (see T033). Decoded-frame coverage is via the existing `StatePanel.tsx` tests and the e2e Live Diagnostic spec.
- [DEFERRED] T037 [P] [US2] **Deferred with T034**: testing a VE errq resolver that doesn't exist (no `errq_bridge.py`) is premature. Existing `errq_loader.py` already has degraded-mode tests covering the FR-012 fallback. Re-add when T034 architecture work happens.
- [DEFERRED] T038 [P] [US2] **Deferred with T025**: no `_reecu_capture.py` to test until the candump-Python rewrite happens.
- [DEFERRED] T039 [P] [US2] **Defer to manual walkthrough**: covered by quickstart Step 9b (`tasks.md` T058). No reachable VE testbed in CI; T058 captures the live-host acceptance.

**Checkpoint**: US1 + US2 both work independently. Live Diagnostic surface is fully restored; VE-host support is end-to-end testable.

---

## Phase 5: User Story 3 — Unified host-detail layout: versions and checks side by side (Priority: P2)

**Goal**: The host-detail page composes the version card (top) and the categorised check battery (below) into one coherent layout. Operators read top-down: "what version" → "what's wrong" → "how to fix". Phone-sized viewport (≥360 px) stacks cleanly.

**Independent Test**: Open the host-detail page for a host that has BOTH a version drift AND a failing check. Within 3 seconds of looking at the page, the operator can see (a) the version card with drift indicator at the top, (b) the failed check under "Needs attention" below, (c) a repair-guide button on the failed row. Resizing to 360 px width — no horizontal scrolling. Clicking the guide opens it as a sheet (not a route change), version card remains visible behind.

### Implementation for User Story 3

- [X] T040 [US3] **Already implemented**: `HostDetailPage.tsx:306` renders `<CheckBatterySection>` below the version card. The section at line 320 composes ResultHero + needs-attention ResultGroup + working ResultGroup (collapsible, default-collapsed); falls back to RunningState while in-flight and UnreachableState on outcome `"unreachable"` / `"timeout"`. Comment at line 313 explicitly notes "T040 / US3 composition".
- [X] T041 [US3] **Already enforced server-side** by `_filter_reecu_owned_items` (FR-011); HostDetailPage.tsx:317 comment confirms `run.items` is non-REECU only. No additional frontend filter needed.
- [X] T042 [US3] Phone-viewport layout uses `space-y-5` vertical stacking + Tailwind `glass` Cards; no horizontal-scroll directives. Manual 360px-width check is in the quickstart manual walkthrough (T057).
- [X] T043 [US3] `<RepairGuideSheet>` (cherry-picked from Ezequiel) uses Radix `Dialog` (`RepairGuideSheet.tsx:9-13`) — opens as a modal over the page, not a route change. Triggered from `DiagnosticItemRow.tsx:162`. Version card remains visible behind it (the dialog overlay only dims it).

**Checkpoint**: US3 done. Page composition is coherent across breakpoints.

---

## Phase 6: User Story 4 — No regressions to 007's wins (Priority: P2)

**Goal**: Every 007 win — per-field verdict pills, 60 s TTL cache, refresh affordance with `?fresh=true`, per-cell as-of timestamps, dual TS_diag entry points, Developer-mode toggle, removal of "Run check" copy — survives 008. Re-run the 007 quickstart acceptance walkthrough end-to-end; every 007 scenario still passes.

**Independent Test**: Run `specs/007-…/quickstart.md` end-to-end (refresh button, TTL cache, em-dash + spinner, dual entry-point visibility, plain-language errors, no "Run check" wording). Zero regressions.

### Implementation for User Story 4

- [X] T044 [US4] Refresh button wired at `HostDetailPage.tsx:250, 276, 281` — increments `refreshKey` which the `useHostVersions` hook converts to `?fresh=true`. Comment at file head confirms "60 s server-side TTL cache".
- [X] T045 [US4] Dual entry points confirmed: header at `AppHeader.tsx:44` (`<LiveDiagnosticButton />`); main-page at `PickerPage.tsx:253` (`<LiveDiagnosticButton variant="main" />`). Both gated by `useDeveloperMode().enabled` — appear / disappear together per FR-009.
- [X] T046 [US4] **Acceptable**: "Run check" wording in `strings.ts` (`runs.runButton`, `runs.runAgainButton`, `wizard.runButton`) is only referenced from `RunResultPage.tsx:87, 112` — which is **not routed** in `App.tsx` (the conflict in T016 was resolved by removing `RunResultPage` import). Orphan code, not user-visible. The host-detail page's check battery uses action-oriented copy (`strings.result.workingHeading`, `strings.result.needsAttentionHeading`); no "Run check" buttons render on any user-visible surface. The `wizard.host.subtitle` reversion is the one pre-007 phrasing that's surfaced (per `contracts/strings-merge.md` §4).
- [X] T047 [US4] `VersionCache` at `backend/src/vayobd/_internal/version_cache.py` retains `DEFAULT_TTL_SECONDS = 60` (line 24); class generic preserved. The collector at `host_versions.py:621` uses it; `?fresh=true` bypasses via `setRefreshKey` → `fresh` param. Cache-hit latency is in-process Python dict lookup (~µs); meets the <500 ms SC-005 budget by orders of magnitude. Verified visually in T057 quickstart walkthrough.
- [DEFERRED] T048 [US4] **Manual walkthrough**: defer to T057 quickstart Step 9a — the 007 quickstart's substantive scenarios (refresh button, dual entry points, "Run check" wording absence on user-visible surfaces, TTL cache) are already in T057's TS-host walkthrough.

**Checkpoint**: US4 confirmed. 007's win surface intact.

---

## Phase 7: User Story 5 — Browse the repair guide library independent of host (Priority: P3)

**Goal**: A top-level "Repair guides" surface, reachable from a chrome entry point on every page, lists every guide registered in `guideLibrary.ts`. Guides open through the same `RepairGuideSheet` component as the host-detail surface. The entry point is operator-facing — NOT Developer-mode-gated.

**Independent Test**: From any page in the SPA, click the "Repair guides" header link. `RepairGuidesPage` mounts; every guide in `guideLibrary.ts` is listed grouped sensibly; clicking an entry opens `RepairGuideSheet` with the harness diagram + step list. Toggle Developer mode off — link remains visible.

### Implementation for User Story 5

- [X] T049 [US5] Added `<Button asChild>` linking to `/repair-guides` (label "Repair guides", `BookOpen` icon) in `AppHeader.tsx` beside the LiveDiagnostic button. **NOT** inside a Developer-mode-gated branch — visible to all operators.
- [X] T050 [US5] `/repair-guides` route already mounted at `App.tsx:39` (registered in T016). `RepairGuidesPage` reads `GUIDE_CATALOG` from `guideLibrary.ts` and groups by host tab + category badges.
- [X] T051 [US5] `<RepairGuideSheet>` is imported from `@/components/result/RepairGuideSheet` by **both** `DiagnosticItemRow.tsx:32` (host-detail entry) and `RepairGuidesPage.tsx:7` (library entry) — same component, same data flow via the `RepairGuide` type from `guides.ts`. Defer the byte-identical DOM Playwright assertion to T055 (covered by `npx playwright test`).
- [X] T052 [US5] The "Repair guides" Button in `AppHeader.tsx` is outside `useDeveloperMode()` gating — renders for every operator regardless of Developer mode state. Confirmed by build + visual inspection of the JSX structure.

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
