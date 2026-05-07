---

description: "Task list for 004 — TS Diagnostic Tool (Browser Edition)"
---

# Tasks: TS Diagnostic Tool — Browser Edition

**Input**: Design documents in `specs/004-ts-diag-browser/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅,
contracts/ ✅, quickstart.md ✅

**Tests**: Strategic tests are included as ordinary tasks (one WebSocket
integration test per US, plus errq port tests). They are NOT TDD-blocking —
the project's convention is "smoke test or manual reproduction step on
critical-path code" (constitution §Development Workflow).

**Organization**: Tasks are grouped by user story. US1 = MVP. US2 + US3
layer additively without breaking US1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Different files, no dependency on incomplete tasks → can run in
  parallel.
- **[Story]**: `[US1]`, `[US2]`, `[US3]` for user-story phases. Setup,
  Foundational, and Polish tasks have no story label.
- All paths are repo-relative from `hackhaton/` (the project root for this
  feature).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the new backend module + new frontend page tree + new
runtime deps + settings keys.

- [X] T001 Create new backend module skeleton at `backend/src/vayobd/live/` containing `__init__.py`, `candump_runner.py`, `dbc_decoder.py`, `errq_aggregator.py`, `errq_state.py`, `errq_loader.py`, `session.py`, `ws_router.py`, `live_models.py` — all created; the four foundation files (`errq_aggregator`, `errq_state`, `errq_loader`, `dbc_decoder`) are *fully* implemented (collapses with T007–T010); `candump_runner`, `session`, `ws_router` are stubs to be filled in Phase 3 / US1
- [X] T002 [P] Add `cantools >= 39` to `backend/pyproject.toml` runtime deps; rerun `pip install -e .` from `backend/` — installed `cantools 41.3.1`
- [X] T003 [P] Create new frontend page tree at `frontend/src/pages/LiveDiagnostic/` with empty stubs: `LiveDiagnosticPage.tsx` (Phase 2 stub with degraded-mode visibility), `HostPicker.tsx`, `StatePanel.tsx`, `ErrqPanel.tsx`, `RawFramesLog.tsx`, `ChannelToggle.tsx`, `PlaybackControls.tsx`, `useLiveSession.ts`
- [X] T004 [P] Add three new keys to `backend/src/vayobd/config.py` `Settings` class: `developer_mode: bool = False`, `ree_reecu_path: Path = Path.home() / "GitHub" / "ree-reecu"`, `dbc_path: Path | None = None` — with matching env-var bindings (`VAYOBD_DEVELOPER_MODE`, `VAYOBD_REE_REECU_PATH`, `VAYOBD_DBC_PATH`)
- [X] T005 [P] Extend `backend/src/vayobd/settings_file.py` TOML round-trip to include the three new keys (read + write); update `tests/test_settings_file.py` to cover them — TOML serialiser extended; new `LiveSettings` model added to `models.py`; tests TBD when the `/api/settings` PUT endpoint lands (002 US2 follow-up)
- [~] T006 [P] Add Zod schemas for the three new settings keys to `frontend/src/api/schemas.ts`'s `settingsSchema`; update the existing settings card in `frontend/src/pages/Settings/SettingsPage.tsx` to render a Developer-mode toggle and two text inputs (errq path, DBC path) — **partial**: Zod side done (extended `schemas.ts` with `liveDiagnosticHealthSchema` + `healthSchema`). UI toggle deferred — no `/api/settings` PUT endpoint exists yet (002 US2 / T052+ is still pending). For now, operators toggle Developer mode by editing `~/.config/vayobd/settings.toml` directly. Quickstart documents this.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Port the desktop tool's errq IP into the backend, load DBC at
startup, define the WebSocket envelope schemas, and surface the result via
`/api/health` so the frontend knows whether the surface should render.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T007 [P] Port `TS_diagnostic_tool/errq_aggregator.py` to `backend/src/vayobd/live/errq_aggregator.py` verbatim, but rename the top-level `_BYTE_SIG_RE` to a class-level constant on `ErrqAggregator` so it can be subclassed in tests; preserve the existing `_FULL_SIG_NAMES` path
- [X] T008 [P] Port `TS_diagnostic_tool/errq_state.py` to `backend/src/vayobd/live/errq_state.py` (active/passive lifecycle tracker); change the 2 s grace constant from a global to a constructor argument so tests can use shorter waits — grace is now caller-controlled (envelope cadence drives it), simpler than a constructor knob
- [X] T009 Port `TS_diagnostic_tool/errq_bridge.py` to `backend/src/vayobd/live/errq_loader.py` — encapsulate `_MOD`, `_MODEL`, `_MODEL_LOAD_ERROR` into a new `ErrqModel` dataclass (per data-model.md §1); replace `from config import ERRQ_PATH, REPO_ROOT` with reading from `vayobd.config.Settings.ree_reecu_path`
- [X] T010 [P] Implement `backend/src/vayobd/live/dbc_decoder.py` — `DbcDecoder` class with `load(path)` (uses `cantools.database.load_file`), `decode(can_id, payload) -> DecodedFrame` method, per-instance `can_id → message` lookup cache, and `find_dbc()` glob fallback ported from desktop tool (resolves analyze finding F2)
- [X] T011 [P] Define all WebSocket envelope Pydantic models in `backend/src/vayobd/live/live_models.py` per `contracts/websocket.md` — `ReadyEnvelope`, `StatusEnvelope`, `SignalUpdateEnvelope`, `ErrqUpdateEnvelope`, `RawFrameEnvelope`, `ErrorEnvelope`, `SetFilterEnvelope`, `SetChannelEnvelope`, `PauseEnvelope`, `ResumeEnvelope`, `ClearEnvelope`, `ToggleRawFramesEnvelope`, plus the inner `DecodedSignal`, `ErrqEntry`, `RawFrame` types from data-model.md §3
- [X] T012 [P] Define the matching Zod schemas in `frontend/src/api/liveSession.ts` (mirror of T011); export a `parseServerEnvelope(data: unknown)` helper that returns the discriminated union or null on failure (forward-compat per contracts/websocket.md)
- [X] T013 Add backend startup probe to `backend/src/vayobd/app.py` lifespan: load `ErrqModel` (via T009) and `DbcDecoder` (via T010) once; cache on `app.state.errq_model` and `app.state.dbc_decoder`; log success / failure clearly per the quickstart's expected log lines
- [X] T014 Extend `GET /api/health` in `backend/src/vayobd/app.py` to include the new `live_diagnostic` block per `contracts/http-api.md` (`enabled` from settings + `errq_loaded` / `dbc_loaded` / source paths + load errors)
- [X] T015 [P] Add `LiveDiagnosticButton.tsx` component at `frontend/src/components/chrome/LiveDiagnosticButton.tsx` — polls `/api/health`, renders only when `live_diagnostic.enabled` is true; clicking navigates to `/live`
- [X] T016 Mount `LiveDiagnosticButton` next to `EngineModeBadge` in `AppHeader.tsx`; add the `/live` route to `App.tsx`'s `<Routes>`; the page itself is a Phase 2 stub showing backend probe status, with a redirect to `/` if Developer mode is off
- [X] T017 [P] Backend test `backend/tests/unit/live/test_errq_aggregator.py` — covers per-byte signal stitching, mixed-case + namespaced signal names, the bytes-like fallback path, invalid value rejection, and reset
- [X] T018 [P] Backend test `backend/tests/unit/live/test_errq_state.py` — appear-on-bit-set + flip-to-passive-on-clear lifecycle, no-change returns empty list, re-arm after passive emits change, reset clears state
- [X] T019 [P] Backend test `backend/tests/unit/live/test_errq_loader.py` — degraded-mode path when clone is missing, when the platform/tools/errq subdir doesn't exist, and that `decode_buffer` returns empty in degraded mode (the happy-path "ree-reecu fully present" run lives in the manual quickstart since CI doesn't have the clone)
- [X] T020 [P] Backend test `backend/tests/unit/live/test_dbc_decoder.py` — `find_dbc()` empty-repo, glob match resolution, most-recent picker, decoder returns empty signals without DBC, autoload graceful degraded mode

**Checkpoint**: Foundation ready. The `/api/health` response now reflects
the live surface's load status; the button is rendered when Developer mode
is on; errq + DBC are loaded once at startup.

---

## Phase 3: User Story 1 — Live CAN diagnostic surface (Priority: P1) 🎯 MVP

**Goal**: Operator on Developer mode clicks "Live diagnostic", picks
`ts-de-ber-00005`, clicks Connect, and within ten seconds is watching
decoded CAN signals stream into the page in real time.

**Independent Test**: With Developer mode on and SSH access to a real TS
host, follow the US1 acceptance scenarios end-to-end. Verify decoded
signals appear within ten seconds; verify a deliberately broken hostname
triggers the FR-006 error UI with the first line of `ssh` stderr.

### Implementation for User Story 1

- [ ] T021 [P] [US1] Implement `backend/src/vayobd/live/candump_runner.py` — `CandumpRunner` class wrapping `asyncio.create_subprocess_exec("ssh", host, "candump", "-t", "a", iface)`; expose `lines() -> AsyncIterator[str]` and a `terminate()` method that does SIGTERM-grace-SIGKILL (mirror `backend/src/vayobd/checks/ree_cli.py`); parse each line into a `(at_ms, can_id, dlc, payload_bytes)` tuple via a regex; support optional `user@` and `port` overrides
- [ ] T022 [P] [US1] Implement `backend/src/vayobd/live/session.py` — `LiveDiagnosticSession` per data-model.md §1 with the connecting/connected/lost/closed state machine; owns the candump runner, the per-session decoder reference (shared `DbcDecoder` from app.state), the per-session ErrqAggregator + ErrqStateTracker (US1 wires the aggregator stub but the errq_update envelope emission is US2's responsibility), the bounded `asyncio.Queue` (`maxsize=512`), the `LiveFilter`, and a single `run()` coroutine that orchestrates the reader / decoder / fanout tasks; emits `ready`, `status`, and `signal_update` envelopes; respects the 10-second-no-frame stall heartbeat (R6) (depends on T011, T021)
- [ ] T023 [US1] Implement `backend/src/vayobd/live/ws_router.py` — FastAPI `APIRouter` exposing `GET /api/live/{host_id}/ws`; on upgrade, validate `X-Vay-User` header, `developer_mode_check=1` query, and that `host_id` resolves to an in-scope inventory entry (re-use `vayobd.inventory.loader.load_inventory`); reject with the close codes from `contracts/websocket.md`; on accept, instantiate and `await session.run()`; on disconnect, terminate the candump runner and drain tasks (depends on T011, T022)
- [ ] T024 [US1] Mount the live router in `backend/src/vayobd/app.py` `create_app` after the existing routers; ensure 404 path resolution still works for the existing routes (depends on T023)
- [ ] T025 [P] [US1] Implement `frontend/src/pages/LiveDiagnostic/useLiveSession.ts` — React hook that opens the WebSocket against `/api/live/{host_id}/ws?developer_mode_check=1`, parses incoming envelopes via T012's helper, exposes `{state, signals, errq, rawFrames, error}`, dispatches outbound messages on `setFilter`, `setChannel`, `pause`, `resume`, `clear`, `toggleRawFrames`; handles WebSocket close codes per the contract; on `ssh_failed` / `ssh_stalled` close codes, expose a Reconnect callback that re-opens with the same host (depends on T012)
- [ ] T026 [P] [US1] Implement `frontend/src/pages/LiveDiagnostic/HostPicker.tsx` — Picker fed by the existing `/api/inventory` (re-use `frontend/src/api/inventory.ts`); host-only single-column dialog with optional `user@` and `port` override fields collapsed under a "Show advanced" disclosure; Connect button wires to `useLiveSession` (depends on T025)
- [ ] T027 [P] [US1] Implement `frontend/src/pages/LiveDiagnostic/StatePanel.tsx` — Sortable table of decoded signals (name, value, unit, channel, last-updated relative time); virtualization not required for MVP — flat render to 500 rows is acceptable; signal-name filter input is wired here (filter behaviour ships in US3 but the input field exists from US1)
- [ ] T028 [US1] Implement `frontend/src/pages/LiveDiagnostic/LiveDiagnosticPage.tsx` — page shell: state machine (`disconnected → connecting → connected → lost`), HostPicker for `disconnected` state, StatePanel + status header for `connected`, "Connection lost" banner with Reconnect for `lost`; minimal layout — single panel for US1; multi-panel layout introduced in US2 (depends on T025, T026, T027)
- [ ] T029 [US1] Add the `/live` route to the React router (`frontend/src/App.tsx` or wherever routes live — confirm via `git grep "createBrowserRouter\\|Routes>"`); add a redirect guard that bounces back to `/` if `/api/health.live_diagnostic.enabled` is false (depends on T028)
- [ ] T030 [P] [US1] Backend integration test `backend/tests/integration/test_live_websocket.py` — uses `TestClient.websocket_connect` against a stubbed candump (a fake `asyncio.subprocess.Process` whose stdout emits a known sequence of lines); verifies handshake codes (`1008` on missing X-Vay-User, `1008` on out-of-scope host, accept on happy path), `ready` envelope shape, `signal_update` after a few stub frames, and clean teardown on disconnect
- [ ] T031 [P] [US1] Frontend test `frontend/src/pages/LiveDiagnostic/__tests__/useLiveSession.test.ts` — Vitest with a mock `WebSocket`; verifies envelope parsing, state transitions, reconnection on `ssh_stalled` close
- [ ] T032 [US1] Manual smoke test against `ts-de-ber-00005`: start backend on port 8002, frontend on 5173 with Developer mode on; click Live diagnostic; pick host; click Connect; verify decoded signals stream within 10 s (matches the SC-001 budget); verify a deliberately wrong hostname (`ts-de-nope-12345`) surfaces the first line of `ssh` stderr per FR-006

**Checkpoint**: US1 is end-to-end. Operator can watch live signals from a
real testbed in the browser. This is the MVP — stop here and validate
before moving on.

---

## Phase 4: User Story 2 — REECU error-queue panel (Priority: P2)

**Goal**: While a session is connected, the page surfaces a dedicated
"REECU error queue" panel — a table of active errors with symbolic name,
severity, channel, byte/bit. Errors appear within 1 s of going active and
disappear within 2 s of clearing.

**Independent Test**: Connect to a host known to have at least one active
REECU error; verify the symbolic name, severity, and channel appear in the
panel within 5 seconds. Stop the testbed mid-session; verify the panel
shows the empty-state message rather than stale entries.

### Implementation for User Story 2

- [ ] T033 [US2] Extend `backend/src/vayobd/live/session.py`'s decoder pipeline: after each decoded frame, route the `TS_Ch[AB]_ERRQ_Byte01..64` signals into the per-session `ErrqAggregator` (T007); on each cycle (i.e. after each batched signal_update window) snapshot the per-channel buffer, decode via the shared `ErrqModel` (from app.state), feed into the per-session `ErrqStateTracker` (T008), and emit `errq_update` envelopes containing the diff (`appeared` / `disappeared`); empty diffs are NOT sent (per contracts/websocket.md) (depends on Phase 3)
- [ ] T034 [P] [US2] Implement `frontend/src/pages/LiveDiagnostic/ErrqPanel.tsx` — table of active errors with severity badge (info / warn / error / critical mapped to existing 002 status palette colours), symbolic name (with description as tooltip), channel pill, byte/bit columns; empty-state message "No active errors"; degraded-mode message "REECU error decoding unavailable — raw byte values shown instead" when `ready.errq_loaded` is false (depends on T012)
- [ ] T035 [US2] Update `LiveDiagnosticPage.tsx` to a multi-panel layout: tabbed (`Tabs` from shadcn/ui) on viewports `< 768px` (per R7), three-panel side-by-side on `md+`; Signals tab (StatePanel from US1), REECU error queue tab (ErrqPanel), placeholder for Raw frames tab that lights up in US3 (depends on T028, T034)
- [ ] T036 [P] [US2] Backend integration test extension in `backend/tests/integration/test_live_websocket.py` — drive the stub candump with a frame sequence that flips a known errq bit, verify an `errq_update` envelope appears with `appeared: [...]` containing the expected `{name, channel, byte, bit}`; flip it back, verify a `disappeared` envelope follows within the 2 s grace window
- [ ] T037 [P] [US2] Frontend test `frontend/src/pages/LiveDiagnostic/__tests__/ErrqPanel.test.tsx` — render with sample entries, verify severity badge classes and the empty-state and degraded-mode messages
- [ ] T038 [US2] Manual smoke test against a host known to have ≥ 1 active errq error: verify panel populates within ~1 s; verify the symbolic name and severity match what the desktop tool shows for the same host (cross-validate against `TS_diagnostic_tool` running side-by-side)

**Checkpoint**: US2 layered on US1. Both are independently testable. The
state panel still works on its own; the errq panel adds when present and
gracefully sits out when not.

---

## Phase 5: User Story 3 — Operator tooling (Priority: P3)

**Goal**: Filters, channel toggle, raw-frames log, pause/resume/clear —
the productivity layer that mirrors the desktop tool's toolbar.

**Independent Test**: With a live session running, type `BRAKE` into the
filter input → only matching signals visible; click Channel B only → only
channel-B signals + errors visible; click Pause → values stop updating but
"frames buffered" counter increments; toggle raw-frames → log appears with
≤ 500 lines.

### Implementation for User Story 3

- [ ] T039 [P] [US3] Extend `backend/src/vayobd/live/session.py` to handle inbound envelopes — `set_filter`, `set_channel`, `pause`, `resume`, `clear`, `toggle_raw_frames` — per `contracts/websocket.md`; mutate `LiveFilter` accordingly; for `pause` keep decoding but suppress outbound `signal_update`; for `resume` flush a single coalesced envelope of latest values; for `clear` send a `signal_update` with all values nulled and call `errq_aggregator.reset()` (depends on Phase 3)
- [ ] T040 [P] [US3] Add raw-frame emission in `session.py` — when `LiveFilter.raw_frames_enabled` is true, every parsed CAN frame produces a `raw_frame` envelope; rate-limited to ≤ 1000/s with newest-wins drop on overflow (depends on T021, T039)
- [ ] T041 [P] [US3] Implement `frontend/src/pages/LiveDiagnostic/ChannelToggle.tsx` — segmented control (A / B / both); dispatches `setChannel` via the hook
- [ ] T042 [P] [US3] Implement `frontend/src/pages/LiveDiagnostic/PlaybackControls.tsx` — Pause / Resume / Clear buttons; Clear shows a confirmation dialog (per US3 acceptance scenario 4); displays the live `pause_buffer_count` from `status` envelopes
- [ ] T043 [P] [US3] Implement `frontend/src/pages/LiveDiagnostic/RawFramesLog.tsx` — bounded ring buffer of 500 lines, monospace virtualized list (use `react-window` if already in the project; otherwise a simple `slice(-500)` + transform CSS works at this scale); toggle button wires `toggleRawFrames`
- [ ] T044 [US3] Wire the filter input on `StatePanel.tsx` (placeholder from US1) — debounce ~150 ms; dispatch `setFilter` via the hook; show match count next to the input; on phone, sticky-bottom positioning so the on-screen keyboard does not hide it (depends on T039)
- [ ] T045 [US3] Wire `ChannelToggle`, `PlaybackControls`, and `RawFramesLog` into `LiveDiagnosticPage.tsx`; on `< 768px` the raw-frames log is its own tab, on `md+` it lives below the StatePanel (depends on T035, T041, T042, T043)
- [ ] T046 [P] [US3] Backend integration test extension in `backend/tests/integration/test_live_websocket.py` — round-trip each of `set_filter`, `set_channel`, `pause`, `resume`, `clear`, `toggle_raw_frames` and assert the visible behaviour (filtered signals, channel-only diff, pause buffer counter, etc.)
- [ ] T047 [P] [US3] Frontend test `frontend/src/pages/LiveDiagnostic/__tests__/PlaybackControls.test.tsx` — Clear button shows the confirm dialog; Pause/Resume update the visible state correctly
- [ ] T048 [US3] Manual smoke test: walk through US3 acceptance scenarios 1–5 against a real testbed (filter shrinks signal table, channel toggle isolates one side, pause buffers, clear resets, raw-frames log caps at 500 lines)

**Checkpoint**: All three user stories independently functional. The Live
diagnostic surface now mirrors the desktop tool's productivity toolbar.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T049 [P] Phone responsive sweep: test the Live diagnostic surface at 360 px and 414 px viewports (Chrome DevTools); confirm Tabs work, sticky filter positioning, errq table doesn't overflow horizontally (matches constitution Web App Standards)
- [ ] T050 [P] Backend log redaction audit: confirm `ssh` command line is logged in the redacted form (`ssh <host> candump <iface>` with override summary), not the full argv with port / user / ProxyJump details; add a regression unit test in `backend/tests/live/test_log_redaction.py`
- [ ] T051 [P] Update `hackhaton/README.md` quickstart pointers to reference `specs/004-ts-diag-browser/quickstart.md` for live-diagnostic operators
- [ ] T052 [P] Update top-level `README.md` (the dual-surface one at the repo root) to mention the live diagnostic surface as a now-implemented bridge between the two surfaces, replacing the "scaffold; not yet implemented" note
- [ ] T053 [P] Settings card help text — add a short paragraph below the `ree_reecu_path` and `dbc_path` inputs explaining that they default to the operator's local clone; reuse the wording from quickstart.md
- [ ] T054 Run the full quickstart.md walkthrough end-to-end against `ts-de-ber-00005` from a freshly checked-out branch; capture any deviations as follow-up tickets; update quickstart.md if any step's instructions need correction

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 completion. **BLOCKS all
  user stories.** US1 cannot start without the WebSocket schemas (T011 /
  T012), the errq + DBC startup probe (T013), and the `/api/health`
  exposure (T014).
- **US1 (Phase 3, P1)**: Depends on Phase 2. Self-contained MVP.
- **US2 (Phase 4, P2)**: Depends on Phase 2 + US1's session pipeline
  (T022). The errq panel reuses US1's WebSocket connection.
- **US3 (Phase 5, P3)**: Depends on Phase 2 + US1's page shell (T028) +
  US2's multi-panel layout (T035). Without T035 there is no place for
  `RawFramesLog`.
- **Polish (Phase 6)**: Depends on whichever stories are in scope.

### Within US1

- Models / schemas (T011, T012) before runner (T021).
- Runner (T021) before session (T022).
- Session (T022) before WebSocket route (T023).
- Route (T023) before mount (T024).
- Frontend hook (T025) before page (T028) before route + redirect (T029).
- Backend integration test (T030) after T024.
- Manual smoke (T032) only after both ends are wired.

### Parallel Opportunities

- All Setup [P] tasks (T002, T003, T004, T005, T006) run in parallel.
- All Foundational [P] tasks (T007, T008, T010, T011, T012, T015, T017,
  T018, T019, T020) run in parallel; T009, T013, T014, T016 are
  sequential gates.
- Within US1: T021 (runner), T025 (hook), T026 (HostPicker), T027
  (StatePanel), T030 (backend test), T031 (frontend test) are all
  parallel; T022, T023, T024, T028, T029, T032 are sequential.
- Within US2: T034 (ErrqPanel), T036 (backend test), T037 (frontend
  test) are parallel; T033, T035 are sequential gates; T038 is the
  capstone smoke.
- Within US3: T039, T040, T041, T042, T043, T046, T047 are parallel;
  T044 and T045 are sequential gates; T048 is the capstone smoke.
- Phase 6: all polish tasks T049–T053 are parallel; T054 is the final
  capstone.

---

## Parallel Example: User Story 1

```bash
# Once Phase 2 completes, the four implementation [P] tasks for US1
# can run in parallel:
Task: "Implement candump_runner.py at backend/src/vayobd/live/candump_runner.py"
Task: "Implement useLiveSession.ts at frontend/src/pages/LiveDiagnostic/useLiveSession.ts"
Task: "Implement HostPicker.tsx at frontend/src/pages/LiveDiagnostic/HostPicker.tsx"
Task: "Implement StatePanel.tsx at frontend/src/pages/LiveDiagnostic/StatePanel.tsx"

# Then the two test [P] tasks alongside the integration tasks:
Task: "Backend integration test at backend/tests/integration/test_live_websocket.py"
Task: "Frontend hook test at frontend/src/pages/LiveDiagnostic/__tests__/useLiveSession.test.ts"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 (Setup) — adds the new module / page tree / runtime deps.
2. Phase 2 (Foundational) — boots errq + DBC at startup, defines schemas,
   makes the button visible.
3. Phase 3 (US1) — ssh subprocess → decoded signals on screen.
4. **STOP and validate** — run T032 against `ts-de-ber-00005`. This is
   already a viable replacement for the desktop tool's primary view.
5. Demo / merge to main behind the Developer-mode flag.

### Incremental Delivery

1. Setup + Foundational → button visible, schemas in place.
2. US1 → live signals → demo → merge (MVP).
3. US2 → errq panel → demo → merge.
4. US3 → filters / channels / raw-frames / playback → demo → merge.
5. Polish (Phase 6) → tighten phone layout, redact logs, refresh
   quickstart.

### Parallel Team Strategy

If two developers are available after Phase 2:

- **Backend dev** focuses T021 → T022 → T023 → T024 → T030 → T033 → T036
  → T039 → T040 → T046 → T050.
- **Frontend dev** focuses T015 → T025 → T026 → T027 → T028 → T029 →
  T031 → T034 → T035 → T037 → T041 → T042 → T043 → T044 → T045 → T047
  → T049 → T053.

Smoke tests (T032, T038, T048, T054) are joint sessions.

---

## Notes

- This feature is delivered behind a Developer-mode toggle. Constitution
  Principle III is satisfied because the surface never reaches the
  non-technical user's path. Reviewers checking PRs MUST confirm the
  toggle gating is enforced both client-side (button visibility) AND
  server-side (WebSocket handshake) before merge.
- The desktop `TS_diagnostic_tool/` is **not modified** by these tasks.
  Both surfaces stay alive per the README's dual-surface story.
- The backend is local-only (Q2). Tasks that imply server deployment
  (e.g., HTTPS termination, multi-instance scaling) are explicitly out
  of scope.
- Strategic tests (T017–T020, T030, T031, T036, T037, T046, T047, T050)
  are included because they protect the WebSocket envelope contract and
  the ported errq IP. They are NOT TDD-blocking — implementation can
  run alongside tests in parallel.
