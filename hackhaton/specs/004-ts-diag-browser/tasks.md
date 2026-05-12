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

- [X] T021 [P] [US1] Implement `backend/src/vayobd/live/candump_runner.py` — `CandumpRunner` class wrapping `asyncio.create_subprocess_exec` against the operator's local `ssh`, with `lines()` async iterator yielding `(stream, line)` tuples (stdout + stderr surfaced separately so FR-006 can quote the first stderr line) and SIGTERM-grace-SIGKILL `terminate()`. Per Q2, uses the system `ssh` binary so credentials live in `~/.ssh/`. Parser handles both classic and CAN-FD candump line forms, with redacted command logging per FR-021
- [X] T022 [P] [US1] Implement `backend/src/vayobd/live/session.py` — `LiveDiagnosticSession` per data-model.md §1 with `connecting/connected/lost/closed` state, the bounded outbound queue (newest-wins on overflow), 100 ms coalescing window for `signal_update`, 10 s no-frame stall detection, errq aggregator + state tracker fed inline (US2 envelope diff also wired). The orchestrator drives four tasks (drain / emit / inbound / outbound) via `asyncio.wait(FIRST_COMPLETED)` so a single failure tears the whole session down cleanly
- [X] T023 [US1] Implement `backend/src/vayobd/live/ws_router.py` — FastAPI `APIRouter` at `/api/live/{host_id}/ws` performs the four-stage handshake (X-Vay-User header → developer_mode_check query → settings.developer_mode → inventory lookup), uses the `1008` close codes from `contracts/websocket.md`, and accepts + delegates to `session.run()` on the happy path. Operator slug is normalised before logging
- [X] T024 [US1] `live_router` is included in `create_app` after the inventory + runs routers; `/live` HTTP routes resolve unchanged
- [X] T025 [P] [US1] Implement `frontend/src/pages/LiveDiagnostic/useLiveSession.ts` — `useLiveSession()` opens the WebSocket with `developer_mode_check=1`, parses envelopes through `parseServerEnvelope`, accumulates signals (`Map<name::channel, DecodedSignal>`), errq diffs, and a 500-line raw-frame ring (FR-014). Exposes `connect/disconnect/send` and synthesises a `lost` state from close codes 1008/1011/4000/4001 when the server hasn't already pushed one
- [X] T026 [P] [US1] Implement `frontend/src/pages/LiveDiagnostic/HostPicker.tsx` — host-only picker fed by `/api/inventory`, persists last selection in `localStorage` (`vayobd.live.hostSelection`), optional `user@`/`port` overrides under "Show advanced", explicit copy clarifying that no SSH credentials are collected. TS hosts sort first since the desktop tool is TS-only
- [X] T027 [P] [US1] Implement `frontend/src/pages/LiveDiagnostic/StatePanel.tsx` — table sorted by (channel, name), capped at 500 rows. Filter input owns its own debounced state and dispatches `set_filter` upstream after 150 ms, while *also* applying client-side filtering so stale rows don't linger when the filter narrows
- [X] T028 [US1] Implement `frontend/src/pages/LiveDiagnostic/LiveDiagnosticPage.tsx` — surface state machine (`idle → connecting → connected → lost`), HostPicker for idle, status header + StatePanel for connected, lost-banner with Reconnect button quoting the first line of ssh stderr. Multi-panel + tabs are deferred to US2
- [X] T029 [US1] `/live` route is registered in `frontend/src/App.tsx` and the page itself redirects to `/` when `/api/health.live_diagnostic.enabled` is false
- [X] T030 [P] [US1] Backend integration test `backend/tests/integration/test_live_websocket.py` — covers all four handshake-failure paths (missing X-Vay-User, missing developer_mode_check, settings.developer_mode=false, unknown host) and the happy path through the `ready` + `status:connecting` envelopes. The full pipeline (real ssh subprocess) is exercised via the manual quickstart since CI has no testbed access; tests were green at 23 passing
- [~] T031 [P] [US1] Frontend test `frontend/src/pages/LiveDiagnostic/__tests__/useLiveSession.test.ts` — **deferred**: the frontend uses Playwright for e2e and has no Vitest toolchain installed. Adding Vitest + jsdom + React Testing Library was scoped out of this implementation pass. The backend integration test (T030) covers the WebSocket envelope contract end-to-end; the hook is exercised via the manual smoke (T032). Track as a follow-up if a Vitest toolchain lands
- [ ] T032 [US1] Manual smoke test against `ts-de-ber-00005`: start backend on port 8002, frontend on 5173 with Developer mode on; click Live diagnostic; pick host; click Connect; verify decoded signals stream within 10 s (matches the SC-001 budget); verify a deliberately wrong hostname (`ts-de-nope-12345`) surfaces the first line of `ssh` stderr per FR-006 — **operator-run**: requires SSH access to a real testbed and is therefore out of scope for the implementation pass

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

- [X] T033 [US2] `backend/src/vayobd/live/session.py` already routed decoded ERRQ byte signals through the per-session `ErrqAggregator` and `ErrqStateTracker` as part of T022; this pass extracted `_emit_one_cycle()` from `_emit_loop()` so the diff cadence is unit-testable. Empty diffs are skipped (contract conformance verified by T036)
- [X] T034 [P] [US2] Implemented `frontend/src/pages/LiveDiagnostic/ErrqPanel.tsx` — table sorted by severity then (channel, byte, bit). Severity badges map to the sun-theme palette (`info → secondary`, `warn → warning`, `error/critical → destructive`); empty state shows "No active errors" with a check-shield icon; degraded-mode hint references `VAYOBD_REE_REECU_PATH` so operators know the recovery action
- [X] T035 [US2] `LiveDiagnosticPage.tsx` connected view now renders Tabs on `< md` (Signals + REECU errors) and a `1fr / 280–360px` two-column grid on `md+`. Active-error count surfaces as a destructive pill in the connected-status header. Raw frames stays a US3 follow-up — there is no placeholder tab yet, since the tabset would emit "Raw frames (—)" with no behaviour. Added `frontend/src/components/ui/tabs.tsx` (shadcn wrapper around `@radix-ui/react-tabs`, dep added)
- [X] T036 [P] [US2] Extended `backend/tests/integration/test_live_websocket.py` with two `_emit_one_cycle` tests — appeared/disappeared diff round-trip against the state tracker, plus a no-change-no-envelope assertion that protects the contract's "empty diffs are NOT sent" rule. 25 tests passing
- [~] T037 [P] [US2] Frontend test `frontend/src/pages/LiveDiagnostic/__tests__/ErrqPanel.test.tsx` — **deferred**: same Vitest toolchain gap as T031. ErrqPanel is a pure-render component with the contract pinned by T036's backend test
- [ ] T038 [US2] Manual smoke test against a host known to have ≥ 1 active errq error — **operator-run**: requires SSH access to a real testbed

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

- [X] T039 [P] [US3] `backend/src/vayobd/live/session.py` already handles every client envelope kind (`_apply_client` in T022's pipeline build). T046 below pins the contract: `set_filter` updates the substring; `set_channel` narrows the filter; `pause` suspends outbound `signal_update`; `resume` flushes a single coalesced envelope and zeroes `pause_buffer_count`; `clear` empties the coalesce buffer + resets the errq aggregator + state tracker; `toggle_raw_frames` flips the flag
- [X] T040 [P] [US3] Raw-frame emission lives in `session._maybe_enqueue_raw`: when `filter.raw_frames_enabled` is true, every parsed frame produces a `raw_frame` envelope behind a 1-second token bucket capped at `RAW_FRAMES_RATE_LIMIT = 1000`. Overflow is silently dropped (newest-wins via the outbound queue's overflow policy)
- [X] T041 [P] [US3] Implemented `frontend/src/pages/LiveDiagnostic/ChannelToggle.tsx` — three-position radiogroup (Both / Ch A / Ch B), exports the `Channel` type, dispatches `set_channel` via the page-level callback
- [X] T042 [P] [US3] Implemented `frontend/src/pages/LiveDiagnostic/PlaybackControls.tsx` — Pause/Resume toggle, Clear gated behind a `Dialog` confirm (US3 acceptance scenario 4). Surfaces `pause_buffer_count` next to the buttons while paused. Added `DialogFooter` to `frontend/src/components/ui/dialog.tsx` since shadcn's footer wasn't already exported
- [X] T043 [P] [US3] Implemented `frontend/src/pages/LiveDiagnostic/RawFramesLog.tsx` — toggle button, monospace log rendered with stick-to-bottom auto-scroll that yields when the user scrolls up. The hook already enforces the 500-frame ring (FR-014); this component renders the tail without a virtualization lib (modern browsers paint 500 rows comfortably)
- [X] T044 [US3] Filter input was wired in T027 (StatePanel debounces 150 ms then dispatches `set_filter`). This pass added a `channel` prop so the same panel applies client-side channel filtering for instant feedback when the toggle changes
- [X] T045 [US3] `LiveDiagnosticPage.tsx` connected view now mounts ChannelToggle + PlaybackControls in a top-row toolbar, and on phone exposes a third "Raw" tab; on md+ the raw-frames log sits below the side-by-side panels. Channel filtering is mirrored client-side on the visible errq list + the pill counter so the channel toggle has instant effect (US3 acceptance scenario 2)
- [X] T046 [P] [US3] Extended `backend/tests/integration/test_live_websocket.py` with five focused tests covering `set_filter`, `set_channel`, `pause/resume` (verifies the resume flush), `clear` (verifies coalesce + state-tracker reset), and `toggle_raw_frames` (verifies the flag plus a real `raw_frame` envelope). 30 tests passing
- [~] T047 [P] [US3] Frontend test `frontend/src/pages/LiveDiagnostic/__tests__/PlaybackControls.test.tsx` — **deferred**: same Vitest gap as T031/T037. Behaviour is pinned by T046 (server-side) and the component is a thin shadcn Dialog wrapper
- [ ] T048 [US3] Manual smoke walkthrough of US3 acceptance scenarios 1–5 — **operator-run**: needs a real testbed

**Checkpoint**: All three user stories independently functional. The Live
diagnostic surface now mirrors the desktop tool's productivity toolbar.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T049 [P] Phone responsive sweep at 360 px / 414 px in Chrome DevTools — **operator-run**: needs a real browser session against the running dev servers
- [X] T050 [P] Backend log redaction audit — `_redacted_command` now collapses user/port overrides into a single `+overrides` token instead of leaking the values; the regression test at `backend/tests/unit/live/test_log_redaction.py` pins six paths (default form, user-only override, port-only override, both-override, runner-property scrub of the full ssh argv, and the no-marker-when-clean baseline). 36 tests passing
- [X] T051 [P] `hackhaton/README.md` now points at `specs/004-ts-diag-browser/quickstart.md` next to the existing 001 quickstart link
- [X] T052 [P] Top-level `README.md` "How they relate" section rewritten — the live diagnostic surface is described as the implemented bridge under 004; the `003-ts-diagnostic-cherry-picks` "scaffold; not yet implemented" note is gone
- [~] T053 [P] Settings card help text — **deferred**: the SettingsPage UI for `ree_reecu_path` / `dbc_path` doesn't exist yet (T006 noted that the `/api/settings` PUT endpoint hasn't shipped from 002). Operators currently configure these by editing `~/.config/vayobd/settings.toml` directly, which the quickstart already documents. Re-open once the settings round-trip lands
- [ ] T054 Full end-to-end quickstart walkthrough against `ts-de-ber-00005` — **operator-run**: needs SSH + VPN access to a real testbed

---

## Phase 7: Clarification Follow-ups (post-2026-05-07 session)

**Purpose**: Absorb the four new requirements that landed in the
2026-05-07 clarification session (FR-005 amendment, FR-024, FR-025,
FR-026). Two of the four (FR-005 fallback, FR-025 TOFU) were patched
into the code mid-test-session and need ratification tests; two
(FR-024 DBC settings UI, FR-026 channel-inference regex) are new
greenfield work.

**Order**: T055–T056 are quick test-only ratifications and can land
immediately. T057–T060 unblock the FR-024 settings-UI work but depend
on 002's `/api/settings` PUT endpoint shipping first (currently the
blocker called out in T053). T061–T064 implement FR-026 and depend on
the same settings round-trip.

### Ratification tests

- [X] T055 [P] FR-025 regression — added two tests at the end of `backend/tests/unit/live/test_log_redaction.py` that monkeypatch `asyncio.create_subprocess_exec` and capture the argv built by `CandumpRunner.start()`. One asserts `StrictHostKeyChecking=accept-new` is present; the other asserts `StrictHostKeyChecking=no` and `UserKnownHostsFile=/dev/null` are NOT present (MITM-bypass guard)
- [X] T056 [P] FR-005 amendment regression — added `ts-de-ber-noaddr` (no `ansible_host`) to the synthetic inventory in `backend/tests/conftest.py`. New test in `test_live_websocket.py` confirms the handshake accepts the host (emits `ready` + `status:connecting` instead of closing 1008). Existing inventory tests updated for the new host count (7→8)

### FR-024 — operator-picked DBC path through Settings UI

**Blocker**: 002's `PUT /api/settings` endpoint must exist before T058
can land. T057 / T060 only need the read side and can ship sooner.

- [X] T057 `get_settings()` now layers `~/.config/vayobd/settings.toml`'s `[live]` block on top of pydantic-settings defaults, with `VAYOBD_*` env vars retaining override precedence (env > TOML > defaults). Cached via `lru_cache`; malformed TOML fails soft to defaults. New unit-test file `backend/tests/unit/test_config.py` pins all four precedence paths (no-file, TOML-overrides-default, env-beats-TOML, malformed-TOML-fallback)
- [ ] T058 Backend `PUT /api/settings` validation in `backend/src/vayobd/api/settings.py` for `dbc_path` and `ree_reecu_path`: file/directory exists, readable, and (for dbc_path) `cantools.database.load_file` parses without error; reject with field-level error on failure. Save round-trips through `settings_file.save_settings()` — **deferred**: depends on 002's `/api/settings` PUT endpoint shipping
- [ ] T059 Backend: on settings save, reload `app.state.dbc_decoder` and `app.state.errq_model` — **deferred**: depends on T058
- [ ] T060 Frontend Settings card with `ree_reecu_path` / `dbc_path` inputs — **deferred**: depends on T058

### FR-026 — operator-configurable channel-inference regex

- [X] T061 [P] Added `channel_a_pattern` / `channel_b_pattern` to `Settings` (`backend/src/vayobd/config.py`) with case-insensitive defaults `(?i)_CHA_|TS_CHA` and `(?i)_CHB_|TS_CHB`. Env-var bindings (`VAYOBD_CHANNEL_A_PATTERN`, `VAYOBD_CHANNEL_B_PATTERN`) inherit from the existing pydantic-settings prefix. TOML round-trip extended in `settings_file.py` and `LiveSettings` in `models.py`
- [X] T062 `LiveDiagnosticSession._infer_channel` is now an instance method using per-session compiled regexes. Patterns are compiled in `__init__` via `_compile_channel_pattern()`, which logs a warning and falls back to the defaults on `re.error` so a typo on the operator side never crashes the session. `ws_router.py` passes `settings.channel_a_pattern` / `channel_b_pattern` through on session construction
- [X] T063 [P] Three new tests in `backend/tests/integration/test_live_websocket.py`: (1) defaults classify the standard `TS_CHA_*` / `TS_CHB_*` convention case-insensitively; (2) custom `^chA_` / `^chB_` patterns take effect and the defaults stop matching; (3) invalid regex (`[unclosed`) falls back to defaults with a `channel_pattern_invalid` warning
- [ ] T064 Frontend regex inputs in the Settings card — **deferred**: depends on T060

**Checkpoint**: All four clarification FRs covered. T055/T056 unblock
on first push. T057–T064 form a coherent settings-round-trip increment
that pairs naturally with the 002 US2 follow-up.

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
- **Clarification follow-ups (Phase 7)**: T055/T056 depend only on the
  current code (live patches). T057–T064 form a settings-round-trip
  increment that depends on 002's `PUT /api/settings` endpoint
  shipping (currently the blocker on T053).

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
