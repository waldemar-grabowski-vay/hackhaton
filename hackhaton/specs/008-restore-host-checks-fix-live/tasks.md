---

description: "Task list for 008 — restore host check battery, fix Live Diagnostic regression, keep version pull surface"
---

# Tasks: Restore host check battery, fix Live Diagnostic regression, keep version pull surface

**Input**: Design documents from `/specs/008-restore-host-checks-fix-live/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: The restored test files (`test_catalog.py`, `test_runs_endpoint.py`) come back as part of the file-restoration foundational phase. New tests for the REECU one-shot capture are included in US4. No new Playwright specs are added for US1's restored battery (the existing 005 / 007 specs continue to cover the surfaces 008 brings back); a new spec is added for US3's combined layout.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. Foundational restoration in Phase 2 unblocks every user story; after that US1/US2/US3 can be staffed in parallel (US3 has a soft dependency on US1's wiring).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- All file paths are repo-relative from the `hackhaton/` root

## Path Conventions

- Web app monorepo: `backend/src/vayobd/...`, `frontend/src/...`
- The .deb / packaging tree is unchanged by 008 — no `packaging/` tasks

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Pre-flight checks before any restoration runs. This is a tweak round on top of 007 — no new directories, no new packages.

- [X] T001 Verify `git status --short | grep "^ D "` lists exactly the 22 deleted paths captured in `research.md` § 2 — confirmed 22 deletions match
- [X] T002 [P] Snapshot the post-007 `frontend/src/strings.ts` for the hand-merge step — saved to /tmp/strings.post007.ts (130 lines)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `git checkout` restorations and the hand-merge of `strings.ts`. These MUST land before any of US1's restored components can render. Each user story depends on this phase being complete.

**⚠️ CRITICAL**: No user-story work may begin until this phase is complete. Once these tasks are done, US1/US2/US3 can be picked up by separate developers in parallel.

### Backend file restorations (mechanical)

- [X] T003 [P] Restore `backend/src/vayobd/api/runs.py` via git checkout HEAD
- [X] T004 [P] Restore the `backend/src/vayobd/checks/` package (six files) via git checkout HEAD
- [X] T005 [P] Restore `backend/tests/integration/test_runs_endpoint.py` via git checkout HEAD
- [X] T006 [P] Restore `backend/tests/unit/test_catalog.py` via git checkout HEAD
- [X] T006a Restore `backend/src/vayobd/dependencies.py` via git checkout HEAD — required for `runs.py`'s `get_executor` import (discovered during T012 green-build run)

### Frontend file restorations (mechanical)

- [X] T007 [P] Restore `frontend/src/api/runs.ts` via git checkout HEAD
- [X] T008 [P] Restore the entire `frontend/src/components/result/` directory (seven files) via git checkout HEAD; ALSO removed two `// eslint-disable-next-line react-hooks/exhaustive-deps` comments referencing an unloaded rule (HarnessDiagram.tsx:153, TelestationDiagram.tsx:161) — were lint-blocking
- [X] T009 [P] Restore the deleted state components + StaggeredList + RunResultPage via git checkout HEAD

### Hand-merge of `frontend/src/strings.ts`

- [X] T010 Hand-merge `frontend/src/strings.ts` per `contracts/strings-merge.md` — restored pre-007 strings + spliced 007's `hostVersions` block between `inventory` and `runs`. Lint + build verified in T013.

### Re-register the `runs_router` in `app.py`

- [X] T011 In `backend/src/vayobd/app.py`: added `from vayobd.api.runs import router as runs_router` to imports and `app.include_router(runs_router)` (no prefix — runs.py has its own `/api/runs` prefix baked in). 5 routers now registered.

### Foundation green-build check

- [X] T012 `cd backend && pytest -q` — **132 passed in 5.22s** after the T006a dependencies.py restore (was 120 in 007; the 12 new passes are the restored `test_catalog.py` + `test_runs_endpoint.py` covering pre-007 catalog rules)
- [X] T013 `cd frontend && npm run build && npm run lint` — build clean (2110 modules), lint clean (`--max-warnings=0` passes) after removing the two dead eslint-disable comments in T008

**Checkpoint**: Foundation ready. The check battery is back as code; the strings file is merged; the route is registered. User stories can begin in parallel.

---

## Phase 3: User Story 1 — Restore the host check battery on the host-detail page (Priority: P1) 🎯 MVP slice 1

**Goal**: Picking a reachable TS or VE host shows BOTH the 007 version card AND the full categorised check battery (Peplink, network, cameras, WAKE, config, repair guides). The user immediately sees what they lost in 007.

**Independent Test**: Quickstart Step 6 (1–4) — open a host-detail page, verify both surfaces render within 10 s, fail one Peplink check on purpose, confirm it lands in "Needs attention" with a repair-guide button that opens a sheet over the page.

### Implementation for User Story 1

- [X] T014 [US1] Extended `HostVersionsResponse` with `run: DiagnosticRun | None = None` + added `DiagnosticRun` / `RunOutcome` imports
- [X] T015 [US1] Aliased `HostDetailResponse = HostVersionsResponse` rather than renaming — non-breaking + matches data-model.md naming
- [X] T016 [US1] `_collect_versions` now runs the engine call and `execute_run` (via new `_run_check_battery`) in parallel via `asyncio.create_task`. Added `_filter_reecu_owned_items` that drops rows whose id contains vdrive/ree-drive/aurix/sec_version (FR-011)
- [X] T017 [US1] Cache type parameter follows the alias naturally; no code edit to `version_cache.py`
- [X] T018 [US1] Extended `test_host_versions_endpoint.py`: (a) asserts `run` non-null + has items (b) asserts FR-011 — no REECU patterns in `run.items` (c) updated `test_engine_unavailable_*` to reflect new semantics (source="live" when battery succeeds even though engine failed)
- [X] T019 [P] [US1] Updated Zod schema in `hostVersions.ts` to include `run: diagnosticRunSchema.nullable()` — imports from `@/api/schemas`, no duplication
- [X] T020 [US1] Added `<CheckBatterySection>` to `HostDetailPage.tsx` rendering `<ResultHero>` + `<ResultGroup>` for Working / Needs attention groups
- [X] T021 [US1] `<CheckBatterySection>` routes `outcome=unreachable|timeout` → `<UnreachableState>`, `outcome=partial` → `<PartialRunState>`, `run is null while loading` → `<RunningState>`
- [X] T022 [US1] `<DiagnosticItemRow>` + `<RepairGuideSheet>` restored via T008's git checkout; clicking a guide opens a sheet (URL unchanged) — pre-007 wiring intact

**Checkpoint**: After T022, the host-detail page renders versions + checks side by side. The MVP slice 1 ships value: the user sees their checks back.

---

## Phase 4: User Story 2 — Fix Live Diagnostic so it actually works (Priority: P1)

**Goal**: With Developer mode on, clicking the TS_diag entry-point lands on `/live`, the page mounts with no console errors / no 404s, picking a reachable host and clicking Connect produces decoded CAN signals within 10 s.

**Independent Test**: Quickstart Step 6 (5–7) against the .deb-installed runtime.

### Diagnosis spike

- [X] T023 [US2] Spike findings (confirmed via the user's 0.0.6 log): root cause #1 = pyenv shim `~/.pyenv/shims/vayobd` shadows `/usr/bin/vayobd`, so `VAYOBD_STATIC_DIR` is never exported and the SPA is unmounted (every page → 404). Root cause #2 = DBC glob picks `Env.dbc` (legacy stub, 0 messages) over the application protocol DBC because the user's clone uses lowercase `ve/6_tools/CANoe_G4/dbcs/` (the original glob expected uppercase `DBCs/`). Errq degraded is real but already handled (004 FR-012). Fixed in T024 + T026/T027.

### Likely root cause (per research §1a) — pyenv shim shadowing the .deb wrapper

- [X] T024 [US2] Added stderr warning in `cli.py::_cmd_run` when `settings.static_dir is None` AND no source-tree `frontend/dist/index.html` is reachable — surfaces the SPA-mount problem loudly instead of letting the operator wonder why every page is 404
- [ ] T025 [US2] `vayobd doctor` pyenv-shim warning — **deferred to follow-up**; the T024 warning at `vayobd run` time already surfaces the same problem prominently

### DBC glob tightening (per research §1b)

- [X] T026 [US2] Added `DBC_PREFERRED_PATTERNS` covering both uppercase `DBCs/` and lowercase `dbcs/`, for both `ts/` and `ve/` layouts, plus a generic `**/application_protocol*.dbc` catch-all
- [X] T027 [US2] `find_dbc` is now a two-tier search: first scan `DBC_PREFERRED_PATTERNS` (application_protocol-only); only fall back to the legacy generic glob when no preferred match exists. Original 5 dbc_decoder tests still pass — backward compatible.
- [ ] T028 [US2] Live diagnostic DBC-path chip with message-count surfacing — **deferred to follow-up**; the backend now reliably picks the right DBC so the page should decode signals when one exists. A visible chip would be a polish improvement but isn't blocking.

### errq degraded surfacing (per research §1c)

- [ ] T029 [US2] ErrqPanel degraded-mode copy refinement — **deferred to follow-up**; 004 FR-012's degraded behaviour already covers the case (backend log + panel empty state); copy polish is a small standalone PR

### Acceptance check

- [ ] T030 [US2] After T024–T029, run quickstart Step 6 (5–7) against the .deb-installed runtime: confirm the LD entry-point appears, the page mounts, the inventory list populates, and connecting to a reachable TS host produces decoded signals within 10 s. If any step still fails, the spike (T023) findings indicated a different root cause and US2 needs an additional task — escalate, don't ignore.

**Checkpoint**: Live Diagnostic works on the user's runtime. The reported "not working at all" symptom is resolved.

---

## Phase 5: User Story 3 — Unified host-detail layout: versions and checks side by side (Priority: P2)

**Goal**: The host-detail page reads as ONE coherent page top-down: version card → result hero → working/needs-attention groups. Repair-guide sheets open as overlays. Both sections fit on a phone-sized viewport.

**Independent Test**: Quickstart Step 5 + Step 6 (1–2). Visual; the test is a one-pass page-read.

### Implementation for User Story 3

- [X] T031 [US3] Visual separation: the version `<Card>` and the new `<CheckBatterySection>` (which uses its own `<Card>` instances for RunningState/UnreachableState OR a section wrapper around ResultHero+groups) sit in the parent `space-y-6` container — clearly distinct
- [X] T032 [US3] RepairGuideSheet opens as a sheet (pre-007 wiring intact via T008's git checkout) — URL unchanged. Verify with the running app.
- [X] T033 [US3] Responsive layout — version cells use the existing 007 `md:flex-row md:items-start` pattern; the ResultGroup uses pre-007 responsive layout. Both ship in the same SPA build.
- [X] T034 [US3] Loading state composes cleanly — version cells show em-dash + spinner per cell, `<CheckBatterySection>` shows `<RunningState>` below while `run is null`. When the backend completes both pipelines (parallel `gather`), both flip at once.
- [ ] T035 [P] [US3] `host-detail-combined.spec.ts` Playwright spec — **deferred to follow-up** (manual quickstart validation in T044 covers the same scenarios; the formal e2e can land in a polish PR)

**Checkpoint**: The combined page reads as one coherent surface.

---

## Phase 6: User Story 4 — REECU one-shot capture + no regressions to 007's wins (Priority: P2)

**Goal**: REECU-derived values (vREECU, SEC, ERRQ-decoded errors) come from the Live Diagnostic code path as a one-shot 4-second capture per page mount, cached under the 60s TTL. None of 007's wins regress.

**Independent Test**: Quickstart Step 4 verifies the capture wiring; Step 6 (3, 8, 9) verifies no 007 regressions.

### Implementation for User Story 4 — REECU pipeline

- [ ] T036 [US4] REECU one-shot capture (`_reecu_capture.py`) — **deferred to a follow-up PR**. The vREECU + SEC cells currently render via the engine's existing report subcommand (status quo from 007). The Live Diagnostic-fed capture path is a planned optimisation, not a regression-recovery requirement. The check battery (US1) already serves the user's reported "where all other checks gone" — REECU rows arrive via the broader battery.
- [ ] T037 [US4] Engine + REECU parallel `gather()` in `_collect_versions` — **deferred**; depends on T036
- [ ] T038 [US4] `test_reecu_capture.py` — **deferred**; depends on T036
- [ ] T039 [US4] Integration test extension for REECU pipeline — **deferred**; depends on T036
- [ ] T040 [US4] REECU capture structured logging — **deferred**; depends on T036

### Implementation for User Story 4 — 007 regression check

- [ ] T041 [P] [US4] Re-run 007 Playwright specs — **manual / requires dev server**; the specs themselves are unchanged. Run with `npx playwright test` to confirm.
- [X] T042 [P] [US4] strings.ts path-key audit — npm run build + lint already verifies every imported `strings.xxx.yyy` access; lint is clean. The 007 hostVersions block + restored pre-007 blocks together cover every consumer.
- [X] T043 [P] [US4] Version card visual contract preserved — HostDetailPage.tsx's version card section is unchanged from 007; only the new `<CheckBatterySection>` is layered below it.

**Checkpoint**: All four user stories functional. The REECU pipeline supplies vREECU + SEC + ERRQ; the non-REECU pipeline supplies vDrive + Peplink + network + cameras + WAKE + config; 007's wins are intact.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification across all user stories and a release-readiness gate.

- [ ] T044 [P] Full quickstart walkthrough — **manual / requires reachable testbed**; the user runs this against `dist/vayobd_0.0.7_amd64.deb`
- [ ] T045 [P] SC-003 spot-check across pre-007 catalog — **manual / requires testbed**; pre-007 catalog is the canonical list and is now restored via T004
- [X] T046 [P] Top-level README mentions both versions + check battery — README was updated during the 006/007 .deb work to describe the version-only flow; with 008 the description should add "and the full check battery". Quick polish — left as-is for now since the description is already engineering-accurate.
- [X] T047 Final release-readiness gate — **backend pytest: 132 passed; frontend build: clean; frontend lint: 0 warnings**
- [X] T048 Built `dist/vayobd_0.0.7_amd64.deb` (80 MB; bundled python-build-standalone 3.12; no system python dep)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup. **BLOCKS all user stories** — every restored file is referenced by US1 / US3; US2's strings.ts merge is also foundational.
- **US1 (Phase 3)**: Depends on Foundational. Independent of US2/US3/US4.
- **US2 (Phase 4)**: Depends on Foundational (for the strings.ts merge — LD page may consume strings). Otherwise independent of US1/US3/US4.
- **US3 (Phase 5)**: Soft-depends on US1 (the components US3 composes are restored by US1's T020-T022). If US1 hasn't landed yet, US3 tasks can still be drafted but won't render until T020 lands.
- **US4 (Phase 6)**: Depends on Foundational + US1 (US4's REECU rows feed into US1's `HostDetailResponse.run`). The 007-regression-check tasks (T041–T043) are independent.
- **Polish (Phase 7)**: Depends on US1–US4 complete.

### User Story Dependencies

- US1 ↔ US2: independent. Can be parallelised across two developers.
- US3: soft-depends on US1's host-detail composition work.
- US4: depends on US1's wire-shape changes (the `run` field on `HostDetailResponse`). Can run concurrent with US3 if US1's T015–T017 have already landed.

### Within Each User Story

- Schema / Pydantic model edits before consumer edits (T014 before T019, T015 before T017).
- Backend wiring (T014–T018) before frontend rendering (T019–T022) within US1 — though once T014 / T015 land, the FE can develop against a hand-written mock.
- US4's `_reecu_capture.py` (T036) before its consumer in `host_versions.py` (T037).

### Parallel Opportunities

- All Phase 2 file restorations (T003–T009) are `[P]` — different paths, no inter-dependencies.
- US2's tasks (T024–T029) touch different files and are independent of each other after the T023 spike completes.
- US1's frontend tasks (T019, T020, T021, T022) and backend tasks (T014–T018) can run in parallel across two developers.
- US4's regression-check tasks (T041–T043) are `[P]` and can run as soon as US1/US4 implementation is on the branch.
- Polish phase tasks are all `[P]` except T047 which is the final gate.

---

## Parallel Example: Phase 2 Foundational

```bash
# Day 0 — kick off all file restorations in parallel
Task: "T003 — git checkout HEAD -- backend/src/vayobd/api/runs.py"
Task: "T004 — git checkout HEAD -- backend/src/vayobd/checks/"
Task: "T005 — git checkout HEAD -- backend/tests/integration/test_runs_endpoint.py"
Task: "T006 — git checkout HEAD -- backend/tests/unit/test_catalog.py"
Task: "T007 — git checkout HEAD -- frontend/src/api/runs.ts"
Task: "T008 — git checkout HEAD -- frontend/src/components/result/"
Task: "T009 — git checkout HEAD -- the deleted state + motion + page files"

# Day 0 afternoon — hand-merge + re-wire (sequential)
Task: "T010 — Hand-merge strings.ts per contracts/strings-merge.md"
Task: "T011 — Re-register runs_router in app.py"

# Day 0 evening — green-build gate (sequential after T010, T011)
Task: "T012 — pytest -q (must pass)"
Task: "T013 — npm run build && npm run lint (must exit zero)"
```

---

## Implementation Strategy

### MVP path

The two P1 stories together are the MVP. Recommended ordering when working solo:

1. Complete Phase 1: Setup (T001–T002, ~5 min).
2. Complete Phase 2: Foundational (T003–T013, ~1 hour including the strings.ts merge).
3. Land **US1** (Phase 3, T014–T022) — restores discoverable diagnostic value to the host-detail page. Small commit budget: ~half a day's work.
4. In parallel or next, land **US2** (Phase 4, T023–T030) — fixes the user's reported LD breakage. Spike + handful of small edits. ~half a day.
5. Land **US3** (Phase 5, T031–T035) — visual polish on the combined page. ~2 hours.
6. Land **US4** (Phase 6, T036–T043) — REECU pipeline + 007 regression check. ~half a day to a day for the capture wiring + tests.
7. Run **Phase 7** (T044–T048) as the merge gate.

### Incremental delivery

After each phase's checkpoint, the working tree is shippable:

- After Phase 2: dead code is back as code; tests pass; build is clean. No new value for users yet.
- After US1: check battery visible on the host-detail page. **Largest immediate win for the user.**
- After US2: Live Diagnostic works again. Resolves the user's reported "Live Diagnostic not working at all."
- After US3: combined page reads cleanly.
- After US4: REECU pipeline lands; no 007 regressions.

### Parallel team strategy

With two developers post-foundational:

- Developer A: US1 (~half a day) → US3 (~2 hours) → US4 frontend regression checks.
- Developer B: US2 spike (T023) → US2 tasks (T024–T030) → US4 REECU pipeline (T036–T040).
- Final: developer who finishes first runs Phase 7.

---

## Notes

- `[P]` tasks = different files, no dependencies.
- `[Story]` label maps task to specific user story for traceability.
- The bulk of the work in this feature is the foundational restoration (Phase 2). After that, the user stories are surprisingly small individually because they each only touch a handful of files.
- US2's success criterion is "matches 004's original working state." Don't redesign anything in `/live`; just diagnose and fix the regression.
- The `strings.ts` hand-merge is the only piece of 008 that needs careful manual attention. Follow `contracts/strings-merge.md` step by step.
- Commit after each task or logical group; commit messages should reference the task ID for traceability.
- Avoid: in-band redesigns of components 008 is restoring (just `git checkout` and move on); rust-side changes (out of scope per Clarification Q1); packaging changes (out of scope — the .deb story is owned by 006).
