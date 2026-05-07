# Implementation Plan: TS Diagnostic Tool — Browser Edition

**Branch**: `004-ts-diag-browser` | **Date**: 2026-05-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-ts-diag-browser/spec.md`

## Summary

Port the operator experience of the PyQt6 desktop **TS Diagnostic Tool** (at
`TS_diagnostic_tool/`) into the existing VayOBD web app as a second, parallel
surface — a Developer-mode-only "Live diagnostic" page reachable via an
additional button on the main page. The backend opens a single WebSocket per
live session, shells out to the operator's local `ssh` binary to stream
`candump` from the chosen TS host, decodes incoming CAN frames via
`cantools` against the team's DBC, aggregates the streaming
`TS_Ch[AB]_ERRQ_Byte01..64` signals into 64-byte buffers, decodes active
error bits via the operator's local `~/GitHub/ree-reecu` `errq` model, and
pushes decoded signals + active errors + (optional) raw frames to the
browser. The browser renders a state panel, a REECU error-queue panel, and
optional raw-frames log, with channel toggle, signal-name filter, and
pause/resume/clear controls. The surface is strictly read-only (no testbed
mutation in v1) and never collects, transmits, or stores SSH credentials —
those stay on the operator's machine in `~/.ssh/`.

## Technical Context

**Language/Version**: Python 3.11 (backend, existing); TypeScript 5.6.3 +
React 18.3.1 (frontend, existing). No engine (Rust) changes — this feature
lives entirely in `backend/` and `frontend/`.
**Primary Dependencies**:
- Backend: existing FastAPI/Pydantic/uvicorn stack, **plus**
  - `cantools >= 39` (DBC decoding) — new, runtime
  - `dbcparser` not used (cantools already covers it)
  - The operator's local `~/GitHub/ree-reecu/platform/tools/errq/errq.py`
    is loaded at runtime via `importlib` (mirroring `errq_bridge.py` from
    the desktop tool); no new runtime dep, but the path is configured.
  - System `ssh` binary on the operator's `PATH` (subprocess invocation).
  - `python-can` is **not** used — we read `candump`'s line-protocol stdout
    directly, since that is what `ssh ... candump can0` actually emits.
- Frontend: existing React + Vite + Zod + shadcn/ui + Tailwind. Adds a
  thin WebSocket client (browser-native `WebSocket`, no library).
**Storage**:
- Frontend: browser `localStorage` only (last-selected host id, channel
  preference, raw-log toggle state). Never SSH credentials.
- Backend: ephemeral in-memory session state. No new on-disk persistence.
**Testing**: existing `pytest` for backend, existing `vitest` for frontend.
Add WebSocket integration tests via `httpx.AsyncClient` + FastAPI's
`TestClient.websocket_connect`.
**Target Platform**: operator's local machine (Linux or macOS) running both
the FastAPI backend and a modern browser (Chrome/Firefox/Safari/Edge). The
backend MUST NOT be deployed to a shared server in v1 — see FR-021 + the
"Backend runs locally" assumption.
**Project Type**: web (existing FastAPI + React monorepo).
**Performance Goals** (from spec SC-002, SC-003, SC-005):
- Decoded signal value updates: ≤ 200 ms p95 from frame arrival to render.
- REECU error-queue: appearance ≤ 1 s, removal ≤ 2 s after testbed
  transition.
- Sustained throughput: ≥ 1,000 frames/s without UI degradation.
**Constraints**:
- Read-only surface (FR-020) — no testbed mutation paths in v1.
- No SSH credential collection / persistence (FR-021).
- Backend runs on `localhost` only — `ssh` invocation re-uses operator's
  local `~/.ssh/` (FR-003, FR-022).
- Errq CSVs sourced from configured local clone (default
  `~/GitHub/ree-reecu`, FR-022).
- Developer-mode-gated visibility (FR-001 / FR-002).
- Responsive ≥ 360 px viewport per constitution Web App Standards.
**Scale/Scope**:
- One operator per testbed per browser session is the typical case; FR-019
  permits concurrent operators against the same host (independent ssh
  subprocesses).
- Single TS host per session; switching hosts closes and reopens the
  session.
- The team's TS DBC defines ~200–400 signals; the errq model defines ~220
  errors per channel.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

The constitution defines three NON-NEGOTIABLE principles plus Web App
Standards. Evaluation:

| Principle | Status | Notes |
|---|---|---|
| I. Simplicity First | **PASS** | Single new WebSocket route, single new SPA page, no new database, no new auth, no new infra. Reuses existing FastAPI app + existing React app. The dialogue dramatically simplified by Q2 (system `ssh` instead of paramiko + key paste UI). |
| II. Ship Fast | **PASS** | US1 alone is a viable MVP (live signals end-to-end). US2 (errq) and US3 (filters/log) layer additively. Each user story ships independently. |
| III. Non-Technical User UX | **PASS (with carve-out)** | This surface is *deliberately* gated behind Developer mode (FR-001 / FR-002) and is not part of the primary non-technical flow. The principle binds the primary flow; a Developer-mode-only secondary surface is permitted as long as it does not intrude on the non-technical user's path. The "Live diagnostic" button MUST NOT appear when Developer mode is off (FR-001). Confirmed in Constitution Check Post-Design. |
| Web App Standards | **PASS (with note)** | Browser-only ✅; modern browsers ✅; responsive ≥ 360 px (the live panel uses a tabbed/collapsible layout to fit phones — degraded but operable); HTTPS — backend is `localhost`-only by Q2, so HTTPS does not strictly apply (note recorded); VIN/PII privacy — this surface does not handle VINs. |

No violations require justification. **Complexity Tracking** stays empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-ts-diag-browser/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions + rationale
├── data-model.md        # Phase 1 — entity shapes (Pydantic, Zod, in-mem)
├── quickstart.md        # Phase 1 — how to run + smoke-test the feature
├── contracts/
│   ├── websocket.md     # Phase 1 — WebSocket message contract
│   └── http-api.md      # Phase 1 — REST delta (new endpoints, if any)
├── checklists/
│   └── requirements.md  # Spec quality checklist (already created)
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
hackhaton/
├── backend/                                 # existing FastAPI app
│   └── src/vayobd/
│       ├── app.py                           # MOD: register WebSocket route + Developer-mode setting
│       ├── config.py                        # MOD: add VAYOBD_REE_REECU_PATH (default ~/GitHub/ree-reecu) + VAYOBD_DBC_PATH
│       ├── settings_file.py                 # MOD: surface "developer_mode" + paths in TOML
│       ├── live/                            # NEW: live diagnostic backend module
│       │   ├── __init__.py
│       │   ├── candump_runner.py            # ssh subprocess wrapper, async lines() iterator
│       │   ├── dbc_decoder.py               # cantools wrapper — load DBCs once, decode_frame()
│       │   ├── errq_loader.py               # ports the desktop tool's errq_bridge.py
│       │   ├── errq_aggregator.py           # ports the desktop tool's errq_aggregator.py
│       │   ├── errq_state.py                # active/passive lifecycle, ports errq_state.py
│       │   ├── session.py                   # LiveDiagnosticSession state machine
│       │   └── ws_router.py                 # FastAPI WebSocket route /api/live/{host_id}
│       └── tests/
│           ├── live/
│           │   ├── test_candump_runner.py   # NEW: subprocess + parser unit tests
│           │   ├── test_dbc_decoder.py      # NEW: round-trip with a recorded DBC + frame
│           │   ├── test_errq_aggregator.py  # NEW: ported from desktop tool's tests
│           │   └── test_errq_loader.py      # NEW: degraded-mode contract
│           └── integration/
│               └── test_live_websocket.py   # NEW: TestClient.websocket_connect end-to-end
├── frontend/                                # existing React + Vite app
│   └── src/
│       ├── api/
│       │   └── liveSession.ts               # NEW: WebSocket client + Zod schemas for messages
│       ├── components/
│       │   └── chrome/
│       │       └── LiveDiagnosticButton.tsx # NEW: visible only when developer_mode is on
│       ├── pages/
│       │   └── LiveDiagnostic/              # NEW
│       │       ├── LiveDiagnosticPage.tsx   # page shell + layout
│       │       ├── HostPicker.tsx           # connection dialog (host-only, no creds)
│       │       ├── StatePanel.tsx           # decoded signals table with filter
│       │       ├── ErrqPanel.tsx            # active errors with severity badges
│       │       ├── RawFramesLog.tsx         # ring-buffered raw can-frame log
│       │       ├── ChannelToggle.tsx        # A / B / both
│       │       ├── PlaybackControls.tsx     # pause / resume / clear
│       │       └── useLiveSession.ts        # WebSocket-backed hook
│       ├── settings/
│       │   └── DeveloperModeToggle.tsx      # NEW (or MOD existing settings card)
│       └── strings.ts                       # MOD: copy for new live page
└── TS_diagnostic_tool/                      # unchanged — desktop tool stays alive in parallel
```

**Structure Decision**: The feature lives entirely in the existing
`backend/` and `frontend/` directories — no new top-level project, no new
deploy unit, no new runtime. New code is co-located in a `backend/.../live/`
sub-module (so it can be deleted as a unit if v2 supersedes it) and a
`frontend/.../pages/LiveDiagnostic/` sub-tree. The desktop
`TS_diagnostic_tool/` directory is **not** modified — both surfaces stay
alive per the README's dual-surface story; we port the relevant Python
modules across rather than refactoring the desktop tool.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

(empty — no violations)
