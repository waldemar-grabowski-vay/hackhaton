---
description: "Task breakdown for Remote Host Diagnostics (feature 001-host-diagnostics)"
---

# Tasks: Remote Host Diagnostics

**Input**: Design documents from `specs/001-host-diagnostics/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/http-api.md`, `quickstart.md`

**Tests**: Targeted only — backend unit tests for filter/catalog logic (cheap, high-value) and one Playwright smoke per user story (mandated by the constitution's Development Workflow). No full TDD pyramid; this is a hackathon.

**Organization**: Tasks are grouped by user story (US1, US2, US3 from `spec.md`). Each story phase is independently testable per the spec's "Independent Test" sections.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependencies on incomplete tasks.
- **[Story]**: User-story phases only — `[US1]`, `[US2]`, `[US3]`.
- File paths are repository-relative; the project root for code is `hackhaton/`.

## Path Conventions (per `plan.md`)

- Backend: `hackhaton/backend/src/vayobd/...` and `hackhaton/backend/tests/...`
- Frontend: `hackhaton/frontend/src/...` and `hackhaton/frontend/tests/...`
- Specs: `hackhaton/specs/001-host-diagnostics/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton, build tooling, theme baseline.

- [ ] T001 Create the two-folder layout `hackhaton/backend/` and `hackhaton/frontend/` per `plan.md` § Project Structure
- [ ] T002 [P] Initialize backend Python project at `hackhaton/backend/pyproject.toml` (FastAPI, Uvicorn, Pydantic v2, PyYAML, asyncssh, structlog, pytest, httpx, ruff)
- [ ] T003 [P] Initialize frontend Vite + React + TypeScript app at `hackhaton/frontend/` (`package.json`, `vite.config.ts`, `tsconfig.json`); install Tailwind CSS, Framer Motion, lucide-react, Recharts, TanStack Query, Zod, react-router-dom
- [ ] T004 [P] Configure Tailwind dark-first theme + brand tokens + glass utility classes in `hackhaton/frontend/tailwind.config.ts` and `hackhaton/frontend/src/theme/globals.css`
- [ ] T005 Initialize shadcn/ui in `hackhaton/frontend/` (`components.json`) and generate base primitives (`button`, `card`, `switch`, `dialog`, `tooltip`, `badge`, `toast`) into `hackhaton/frontend/src/components/ui/`
- [ ] T006 [P] Configure ESLint + Prettier in `hackhaton/frontend/` and ruff config in `hackhaton/backend/pyproject.toml`
- [ ] T007 [P] Configure Vite dev proxy `/api → http://localhost:8000` in `hackhaton/frontend/vite.config.ts`
- [ ] T008 Create empty `hackhaton/frontend/src/strings.ts` with namespace stubs (`wizard.*`, `item.*`, `result.*`, `inventory.*`, `runs.*`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cross-story plumbing — types, app shell, inventory cache, error envelope. **No user-story work begins until this phase is complete.**

- [ ] T009 [P] Create backend Pydantic models (`HostId`, `Country`, `HostType`, `City`, `Host`, `InventoryMeta`, `Inventory`, `DiagnosticItem`, `RunOutcome`, `DiagnosticRun`, `OperatorIdentity`) in `hackhaton/backend/src/vayobd/models.py` per `data-model.md`
- [ ] T010 [P] Create frontend Zod schemas mirroring `data-model.md` in `hackhaton/frontend/src/api/schemas.ts`
- [ ] T011 [P] Create backend Settings module (env-driven `VAYOBD_INVENTORY_PATH`, `VAYOBD_EXECUTOR`, `VAYOBD_SSH_KEY`, `VAYOBD_SSH_KNOWN_HOSTS`, refresh cadence) in `hackhaton/backend/src/vayobd/config.py`
- [ ] T012 [P] Configure structlog with JSON renderer in `hackhaton/backend/src/vayobd/logging.py`
- [ ] T013 [P] Implement problem-JSON error envelope and FastAPI exception handlers in `hackhaton/backend/src/vayobd/api/errors.py`
- [ ] T014 [P] Implement inventory loader — read `org/*/{vehicles,telestations}/*.yaml`, derive `country`/`type`/`city`, filter to DE+US (FR-001b) — in `hackhaton/backend/src/vayobd/inventory/loader.py`
- [ ] T015 [P] Implement inventory sync — `git fetch && git reset --hard origin/<branch>` via subprocess with hard timeout, write `inventory.meta.json`, preserve previous on failure (R2) — in `hackhaton/backend/src/vayobd/inventory/sync.py`
- [ ] T016 [P] Implement run-cache filesystem helpers (`runs/<host_id>.json` read/write with `triggered_by` stripping on API responses) in `hackhaton/backend/src/vayobd/inventory/runs_cache.py`
- [ ] T017 Create FastAPI app factory in `hackhaton/backend/src/vayobd/app.py` — mounts inventory + runs routers, mounts built SPA `static/` directory in production, registers exception handlers from T013
- [ ] T018 Implement auth middleware that reads `X-Vay-User` header into `OperatorIdentity` (R4) in `hackhaton/backend/src/vayobd/api/auth.py`
- [ ] T019 Implement asyncio periodic-refresh task started by app factory (FR-016, default 30 min) in `hackhaton/backend/src/vayobd/inventory/scheduler.py`
- [ ] T020 [P] Frontend app shell — `QueryClientProvider`, router routes (`/`, `/host/:hostId`), theme provider, ErrorBoundary — in `hackhaton/frontend/src/App.tsx` and `hackhaton/frontend/src/main.tsx`
- [ ] T021 [P] Frontend `developerMode` store (Zustand or `useSyncExternalStore` over localStorage), default off, broadcast on toggle (FR-021) in `hackhaton/frontend/src/lib/developerMode.ts`
- [ ] T022 [P] Frontend typed fetch wrapper that maps backend problem-JSON to typed errors and Zod-validates responses in `hackhaton/frontend/src/api/client.ts`
- [ ] T023 [P] Frontend `AppHeader` (brand mark + shadcn `Switch` for Developer mode wired to T021) in `hackhaton/frontend/src/components/chrome/AppHeader.tsx`

**Checkpoint**: Backend and frontend run in dev (empty wizard, no data); typed plumbing in place. User-story phases can now start in parallel.

---

## Phase 3: User Story 1 — Run a check and see what is broken (Priority: P1) 🎯 MVP

**Goal**: Operator picks a host through the wizard, runs a diagnostic, and sees a polished result screen with every catalog item by name in either "Working" or "Needs attention". Developer-mode toggle reveals raw output per item without re-fetch.

**Independent Test**: Open the app against a fixture executor, walk Country → Type → (City, telestation only) → Host, click **Run check**, see the result hero with status donut and both groups populated. Toggle Developer mode — per-item expand controls appear. Toggle off — they disappear. The acceptance is satisfied when an unbriefed operator can name three items just inspected and answer "is this host ready?" within 5 seconds.

### Backend — US1

- [ ] T024 [US1] Implement `GET /api/inventory` returning `Inventory` with `meta` (FR-018) in `hackhaton/backend/src/vayobd/api/inventory.py`
- [ ] T025 [US1] Implement `POST /api/inventory/refresh` invoking T015 sync and returning fresh `InventoryMeta` (FR-017) in `hackhaton/backend/src/vayobd/api/inventory.py`
- [ ] T026 [P] [US1] Define `Executor` interface (abstract `async def run(host: Host) -> list[DiagnosticItem]`) in `hackhaton/backend/src/vayobd/checks/executor.py`
- [ ] T027 [P] [US1] Implement `FixtureExecutor` reading `hackhaton/backend/tests/fixtures/runs/<host_id>.yaml` and returning canned items in `hackhaton/backend/src/vayobd/checks/executor.py`
- [ ] T028 [US1] Implement `SshExecutor` using asyncssh + key auth + known-hosts; per-check command timeout in `hackhaton/backend/src/vayobd/checks/executor.py` (depends on T026)
- [ ] T029 [P] [US1] Define check catalog per `research.md` R3 — vehicle items (CAN, cameras, config, network) and telestation items (display surface, input devices, config) — as a `dict[HostClass, list[CheckSpec]]` in `hackhaton/backend/src/vayobd/checks/catalog.py`
- [ ] T030 [US1] Implement `Runner.run(host)` orchestrating T029 catalog through configured T026 executor, classifying into `RunOutcome` (complete / partial / unreachable / timeout) in `hackhaton/backend/src/vayobd/checks/runner.py`
- [ ] T031 [US1] Implement per-`host_id` `asyncio.Lock` registry; second concurrent run returns 409 (FR-011, R5) in `hackhaton/backend/src/vayobd/checks/runner.py`
- [ ] T032 [P] [US1] Server-side PII scrubber over `raw_detail` strings (no VIN, no host segments containing PII) in `hackhaton/backend/src/vayobd/checks/runner.py` (FR-013)
- [ ] T033 [US1] Implement `POST /api/runs` — body `{host_id}`, 25 s hard timeout, persists via T016, returns `DiagnosticRun` — in `hackhaton/backend/src/vayobd/api/runs.py`
- [ ] T034 [US1] Implement `GET /api/runs/latest?host_id=…` returning persisted run or 404 in `hackhaton/backend/src/vayobd/api/runs.py`
- [ ] T035 [P] [US1] Seed `hackhaton/backend/tests/fixtures/runs/` with a healthy host (`ve-de-apollo.yaml`), an errored host (`ve-de-loki.yaml` — missing USB camera), and an unreachable host (`ve-us-01001.yaml`)
- [ ] T036 [P] [US1] Backend unit test: inventory loader filters out `ve-be-*` / `ts-be-*`, derives `country`/`type`/`city` correctly, vehicle has `city is None`, telestation has non-null `city` — in `hackhaton/backend/tests/unit/test_inventory_loader.py`
- [ ] T037 [P] [US1] Backend unit test: catalog wiring — vehicle host produces vehicle catalog items, telestation produces telestation items, item ids are stable across calls — in `hackhaton/backend/tests/unit/test_catalog.py`
- [ ] T038 [P] [US1] Backend integration test: `POST /api/runs` with `FixtureExecutor` for the three seeded fixtures returns the expected `outcome` and item statuses; second concurrent call returns 409 — in `hackhaton/backend/tests/integration/test_runs_endpoint.py`

### Frontend — US1

- [ ] T039 [P] [US1] API hooks `useInventory()` + `useRefreshInventory()` in `hackhaton/frontend/src/api/inventory.ts`
- [ ] T040 [P] [US1] API hooks `useRunCheck(hostId)` + `useLatestRun(hostId)` (handles 409 toast key, 503 empty-inventory branch) in `hackhaton/frontend/src/api/runs.ts`
- [ ] T041 [P] [US1] Framer Motion wrapper `PageTransition` (slide left/right) in `hackhaton/frontend/src/components/motion/PageTransition.tsx`
- [ ] T042 [P] [US1] `StaggeredList` Framer Motion enter animations for result items in `hackhaton/frontend/src/components/motion/StaggeredList.tsx`
- [ ] T043 [P] [US1] Wizard `CountryStep` — Germany / United States tile picker with flag iconography — in `hackhaton/frontend/src/components/wizard/CountryStep.tsx`
- [ ] T044 [P] [US1] Wizard `TypeStep` — Vehicle / Telestation card picker — in `hackhaton/frontend/src/components/wizard/TypeStep.tsx`
- [ ] T045 [P] [US1] Wizard `CityStep` (rendered only when type=telestation; hidden for vehicles per FR-001a) in `hackhaton/frontend/src/components/wizard/CityStep.tsx`
- [ ] T046 [P] [US1] Wizard `HostStep` — host card grid with friendly names + selected highlight — in `hackhaton/frontend/src/components/wizard/HostStep.tsx`
- [ ] T047 [US1] `PickerPage` — wizard state machine wiring T043–T046 with back navigation that preserves earlier choices (FR-001a) — in `hackhaton/frontend/src/pages/PickerPage.tsx`
- [ ] T048 [P] [US1] `EmptyInventoryState` — blocking message + "Update inventory" CTA wired to `useRefreshInventory` (FR-019) — in `hackhaton/frontend/src/components/states/EmptyInventoryState.tsx`
- [ ] T049 [P] [US1] `InventoryFreshness` — last-refreshed timestamp + Update button (FR-018) — in `hackhaton/frontend/src/components/chrome/InventoryFreshness.tsx`
- [ ] T050 [P] [US1] `RunningState` — animated spinner + "Running checks against `<host>`…" copy from `strings.ts` (FR-009) — in `hackhaton/frontend/src/components/states/RunningState.tsx`
- [ ] T051 [P] [US1] `StatusDonut` Recharts component (working vs needs-attention) in `hackhaton/frontend/src/components/charts/StatusDonut.tsx`
- [ ] T052 [P] [US1] `ResultHero` glass card — host display name, run timestamp, donut, pass/fail headline (FR-007) — in `hackhaton/frontend/src/components/result/ResultHero.tsx`
- [ ] T053 [P] [US1] `ResultGroup` container (Working / Needs attention) in `hackhaton/frontend/src/components/result/ResultGroup.tsx`
- [ ] T054 [US1] `DiagnosticItemRow` — plain-language name, category badge, recommended-action paragraph for errors, conditional `raw_detail` expand visible only when `developerMode === true` (FR-022) — in `hackhaton/frontend/src/components/result/DiagnosticItemRow.tsx`
- [ ] T055 [P] [US1] `UnreachableState` — single user-facing message; rendered when `outcome === "unreachable"` (FR-006, edge case) — in `hackhaton/frontend/src/components/states/UnreachableState.tsx`
- [ ] T056 [P] [US1] `PartialRunState` — summary banner that some checks did not complete (FR-006) — in `hackhaton/frontend/src/components/states/PartialRunState.tsx`
- [ ] T057 [US1] `RunResultPage` — pulls `useRunCheck` once on mount, renders `RunningState` then `ResultHero` + two `ResultGroup`s + `DiagnosticItemRow` enumerating every catalog item (FR-003) — in `hackhaton/frontend/src/pages/RunResultPage.tsx`
- [ ] T058 [US1] Populate `hackhaton/frontend/src/strings.ts` with every operator-visible string for v1 (wizard step titles, item names from catalog T029, recommended actions, category labels, error toasts, empty/unreachable messages) (FR-005, FR-014, R6)

### Smoke — US1

- [ ] T059 [US1] Playwright smoke test covering the P1 happy path (open app → Country → Type=Vehicle → Host → Run check → ResultHero with both groups populated → toggle Developer mode → expand a row → toggle off) in `hackhaton/frontend/tests/e2e/p1.spec.ts`

**Checkpoint**: US1 fully functional and demoable end-to-end with the fixture executor. This is the MVP — stop here for first demo.

---

## Phase 4: User Story 2 — Re-check after a fix (Priority: P2)

**Goal**: After acting on a recommended next step, the operator triggers a re-run of the same diagnostic against the same host with one click and sees the result view refresh in place.

**Independent Test**: Run a check that produces at least one error, edit the corresponding fixture file out-of-band to flip the item to working, click **Run check again** on the result page. The errored item now appears under "Working".

- [ ] T060 [US2] Add **Run check again** primary button on `RunResultPage` — calls T040's `useRunCheck` again, shows `RunningState` over the existing layout, replaces result data on success; disables itself while the request is in flight (FR-008, FR-011) — in `hackhaton/frontend/src/pages/RunResultPage.tsx`
- [ ] T061 [US2] Toast on 409 (`runs.in_progress.toast`) using shadcn `useToast`; verify the button stays disabled during the in-flight period — in `hackhaton/frontend/src/pages/RunResultPage.tsx`
- [ ] T062 [US2] Verify run-cache overwrite semantics (most-recent run replaces previous) and add a unit test in `hackhaton/backend/tests/unit/test_runs_cache.py`
- [ ] T063 [US2] Playwright smoke: trigger a run with an errored fixture, swap the fixture to a healthy variant via test helper, click **Run check again**, assert previously errored item is now under "Working" — in `hackhaton/frontend/tests/e2e/p2.spec.ts`

**Checkpoint**: US1 + US2 both work independently; the operator's full "diagnose → fix → verify" loop is closed.

---

## Phase 5: User Story 3 — See exactly what was checked (Priority: P3)

**Goal**: The operator can read off the host identifier, the run timestamp, and a plain-language category label for every item — without scrolling, without external docs.

**Independent Test**: After a successful run, the host display name and timestamp are visible on the result hero on a 360 px viewport without scrolling, and every item row carries a category badge ("Communication" / "Hardware" / "Configuration"). For a fully-healthy host, the operator can read out at least three specific items by name from the result.

- [ ] T064 [US3] Render relative timestamp ("Checked 2 min ago") + host display name prominently on `ResultHero` such that both fit above the fold on a 360 px viewport (FR-007, FR-012) — in `hackhaton/frontend/src/components/result/ResultHero.tsx`
- [ ] T065 [P] [US3] `CategoryBadge` component using shadcn `Badge` with category-specific colour and icon (Communication / Hardware / Configuration) (FR-010) — in `hackhaton/frontend/src/components/result/CategoryBadge.tsx`
- [ ] T066 [US3] Wire `CategoryBadge` into `DiagnosticItemRow` so every row shows its category — in `hackhaton/frontend/src/components/result/DiagnosticItemRow.tsx`
- [ ] T067 [US3] Add category label entries to `hackhaton/frontend/src/strings.ts` (Communication / Hardware / Configuration plain-language labels)
- [ ] T068 [US3] Playwright assertion: for a fully-healthy fixture host, the result enumerates the full catalog by name (no aggregate-only summary) — extends `hackhaton/frontend/tests/e2e/p1.spec.ts` or adds `hackhaton/frontend/tests/e2e/p3.spec.ts` covering SC-007

**Checkpoint**: All three user stories are independently functional. SC-001..SC-008 should be measurable now.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T069 [P] Confetti burst on 100% pass — opt-in via `VITE_FEATURE_CONFETTI=true`, fires from `RunResultPage` on `outcome === "complete"` with empty needs-attention group — in `hackhaton/frontend/src/pages/RunResultPage.tsx`
- [ ] T070 [P] Final theme polish — glass-card variants, accent gradient, focus-visible styles, motion-reduce respect — in `hackhaton/frontend/src/theme/globals.css`
- [ ] T071 [P] Backend lint + type pass: ruff clean, pyright/mypy clean across `hackhaton/backend/`
- [ ] T072 [P] Frontend lint + type pass: `tsc --noEmit` clean and ESLint clean across `hackhaton/frontend/`
- [ ] T073 Manual run-through of `specs/001-host-diagnostics/quickstart.md` §3 happy path and §4 failure paths; record result + screenshots in PR description
- [ ] T074 [P] Manual SC verification — measure SC-001 (60 s for first check), SC-006 (10 s typical), SC-008 (<10 s wizard) and record numbers in PR description
- [ ] T075 Add a one-line `hackhaton/README.md` (or extend existing) pointing newcomers to `specs/001-host-diagnostics/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → no external dependencies, can start immediately.
- **Foundational (Phase 2)** → depends on Setup. **Blocks all user-story phases.**
- **US1 (Phase 3)** → depends on Foundational only. Is the MVP.
- **US2 (Phase 4)** → depends on US1 (re-uses `RunResultPage`, `useRunCheck`, runs cache).
- **US3 (Phase 5)** → depends on US1 (extends `ResultHero` and `DiagnosticItemRow`); independent of US2.
- **Polish (Phase 6)** → depends on whichever stories you intend to ship.

### Within Each Story

- Backend models / executor / catalog can be built in parallel with frontend components — only the `POST /api/runs` integration test (T038) and the Playwright smoke (T059) need both sides done.
- Files touched by multiple tasks (e.g., `RunResultPage.tsx` in T057, T060, T064, T069 and `strings.ts` in T058, T067) MUST run sequentially in the order listed; that's why those tasks are not marked `[P]` even when in different phases.

---

## Parallel Opportunities

### Phase 1 Setup

```text
[P] T002, T003, T004, T006, T007 can all run in parallel after T001.
T005 (shadcn init) waits on T003.
T008 has no dependencies.
```

### Phase 2 Foundational

```text
[P] T009–T016 are independent of each other (different files, no shared state).
T017 depends on T013 (errors) + T014 (loader) + T016 (runs cache).
T018 depends on T017.
T019 depends on T015 (sync).
[P] T020–T023 (frontend foundational) are mutually independent.
```

### Phase 3 US1 — broad parallelism

```text
Backend track:    T024 || T025 || T026 || T027 || T029 || T032 || T035 || T036 || T037
                  T028 → after T026
                  T030 → after T026, T029
                  T031 → after T030
                  T033 → after T030, T016 (cache helpers from Phase 2)
                  T034 → after T033
                  T038 → after T033 + T035

Frontend track:   T039 || T040 || T041 || T042 || T043 || T044 || T045 || T046
                  || T048 || T049 || T050 || T051 || T052 || T053 || T055 || T056
                  T047 → after T043, T044, T045, T046
                  T054 → after T053 (component), T021 (developerMode store)
                  T057 → after T039, T040, T047, T048, T049, T050, T052, T053, T054, T055, T056

T058 strings.ts → after the catalog is finalized (T029) and component shells exist.
T059 Playwright smoke → after T038 (backend reachable) AND T057 (page assembled).
```

### Phase 4 US2

```text
T060 → after T057
T061 → after T060
T062 → after T016 (foundational cache)
T063 → after T060, T061
```

### Phase 5 US3

```text
T064 → after T052
T065 [P] independent
T066 → after T065 + T054
T067 → after T058
T068 → after T066 + T067
```

### Phase 6 Polish

```text
[P] T069, T070, T071, T072, T074 are mutually independent.
T073, T075 are sequential, run last.
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1: Setup
2. Phase 2: Foundational (blocks everything)
3. Phase 3: US1 in full
4. **STOP**, validate quickstart §3 happy path + §4 unreachable + §4 inventory missing
5. Demo

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. + US1 → MVP demo (P1 acceptance scenarios all green)
3. + US2 → Closed-loop diagnose-then-verify demo (P2)
4. + US3 → Trust-and-transparency polish (P3)
5. + Polish → Final demo build with confetti, theme refinements, SC numbers measured

### Parallel Team Strategy (for the hackathon team)

- **Backend track** (one dev): Phase 2 backend tasks → US1 backend (T024–T038)
- **Frontend track** (one dev): Phase 2 frontend tasks → US1 frontend (T039–T058)
- **Glue/integration track** (one dev): Setup, theme, smoke tests, fixtures (T035, T058, T059, T070)
- Once US1 is green, US2 + US3 can each be a half-day for one dev.

---

## Notes

- `[P]` tasks operate on different files with no incomplete-task dependencies.
- Story labels (`[US1]`, `[US2]`, `[US3]`) trace tasks back to spec.md user stories for review.
- Tests are the constitution-mandated minimum: targeted backend unit + integration tests on tricky logic, plus one Playwright smoke per user story for demo-readiness. No full TDD pyramid.
- Commit per task or per logical group; the constitution's mainline-always-deployable rule applies (a broken main MUST be fixed or reverted within the working hour).
- Stop at any checkpoint to validate independently. The MVP at the end of Phase 3 is the smallest demoable thing that delivers the spec's primary value.
