# Phase 0 — Research & Decisions

All open `[NEEDS CLARIFICATION]` markers from the spec were resolved in
`/speckit-clarify` (see the `## Clarifications` section of `spec.md`). This
document captures the *implementation-level* research that follows from
those clarifications, plus the dependency / pattern decisions needed before
Phase 1 design.

## R1. Streaming `candump` over `ssh` from the operator's machine

**Decision**: Spawn `ssh <host> candump -t a can0` (or the testbed's
configured CAN interface name) via `asyncio.create_subprocess_exec`,
inheriting the operator's `~/.ssh/` and PATH. Read the child's stdout line by
line on a dedicated `asyncio.Task` and parse each line into a `(timestamp,
can_id, dlc, payload_bytes)` tuple before handing it to the DBC decoder.

**Rationale**:
- Per Q2, the backend must use the operator's local `ssh` rather than
  paramiko or `python-ssh-implementations`. This keeps credentials and
  ProxyJump config entirely on the operator's machine.
- `candump -t a` produces a deterministic line format (`(<ts>) <iface>
  <id>#<hex>`) that's trivial to parse line-by-line — much simpler than
  pulling in `python-can` for live decode.
- `asyncio.create_subprocess_exec` returns process objects with awaitable
  `readline()` and lifecycle hooks (`terminate()`, `kill()`, `wait()`),
  matching what we need for clean disconnect / reconnect.
- We already use `asyncio.create_subprocess_exec` for `ree-debug-cli` in
  002 (`backend/src/vayobd/checks/ree_cli.py`), so the patterns and the
  SIGTERM-grace-SIGKILL teardown are reusable.

**Alternatives considered**:
- `paramiko.SSHClient` with manual `exec_command` — rejected (Q2 explicitly
  ruled out an in-process SSH client; double-managing keys would also
  duplicate what the operator already has in `~/.ssh/`).
- `python-can` with a `socketcan` over SSH bridge — rejected (extra layer
  with no benefit; we don't need the full python-can stack for read-only
  decoding, and bridging socketcan over ssh adds operational burden).
- `subprocess.Popen` (sync) wrapped in a thread — rejected (FastAPI's event
  loop integration with asyncio subprocesses is cleaner, and the
  one-thread-per-session cost would be wasteful at scale).

## R2. WebSocket protocol shape

**Decision**: One WebSocket per live session at
`GET /api/live/{host_id}/ws` (HTTP upgrade). All messages are JSON envelopes
with a discriminated `kind` field. Server → client kinds: `ready`,
`signal_update`, `errq_update`, `raw_frame`, `status` (connecting,
connected, lost), `error`. Client → server kinds: `set_filter`,
`set_channel`, `pause`, `resume`, `clear`, `toggle_raw_frames`.

The full schema lives in `contracts/websocket.md`; this section records the
shape decision.

**Rationale**:
- A single full-duplex channel matches Q1 exactly and avoids splitting
  control flow over a separate REST endpoint.
- A discriminated union is the simplest schema both sides can validate
  with Zod (frontend) and Pydantic (backend) — same pattern we already use
  for the engine JSON contract in 002.
- Batching multiple `signal_update`s into a single envelope keeps the
  per-message overhead manageable at 1 k frames/s without breaking the
  schema.

**Alternatives considered**:
- Two channels (one for stream, one for control) — rejected (extra
  connection state to manage, no benefit; Q1 explicitly chose a single
  channel).
- Binary protocol (e.g., MessagePack or Protobuf) — rejected for v1 (JSON
  is sufficient at our throughput target, debuggable in browser DevTools,
  and matches the existing API style; revisit only if SC-002 / SC-005 are
  missed in load testing).

## R3. DBC decoding library

**Decision**: `cantools >= 39`, loaded once at backend startup against the
configured DBC path (default `~/GitHub/ree-reecu/.../ts.dbc`, overridable
via `VAYOBD_DBC_PATH`). Use `database.decode_message(can_id, payload)` for
each frame; cache the message lookup by `can_id` to avoid the DBC's
arbitration-id-to-message walk on every frame.

**Rationale**:
- The desktop tool already uses cantools (`dbc_handler.py`); preserving the
  same library means decoded values match what operators have been seeing.
- `cantools` is pure Python, well-maintained, and supports the team's DBC
  features (multiplexed signals, factored values, signal groups).
- A pre-warmed cache of `can_id → message` references brings the per-frame
  decode cost to a hashtable lookup + cantools' internal bit-extract,
  which benchmarks at well under 50 µs per frame on commodity hardware —
  comfortably inside the SC-002 200 ms budget.

**Alternatives considered**:
- `cantools` 38.x — rejected (39+ has the multiplexed signal fixes we
  benefit from; new dependency anyway, no upgrade pain).
- Reimplementing the bit-extract in Rust as part of `ree-debug-engine` —
  rejected for v1 (over-engineering for the throughput target; revisit only
  if Python decode shows up as a bottleneck under load).

## R4. Errq model loading

**Decision**: Port the desktop tool's `errq_bridge.py` and `errq_aggregator.py`
verbatim into `backend/src/vayobd/live/{errq_loader,errq_aggregator}.py`
with two adjustments:
1. The configured path comes from the backend's settings file
   (`VAYOBD_REE_REECU_PATH`, default `~/GitHub/ree-reecu`) rather than the
   PyQt6 settings dialog.
2. Module-level globals are encapsulated in a `ErrqModel` dataclass so two
   concurrent live sessions don't race on `_MOD` / `_MODEL` / cache state.

**Rationale**:
- Port-rather-than-rebuild is the minimum-risk path — the desktop tool's
  decode-and-decorate logic is already proven against the team's CSVs.
- Encapsulating the globals is necessary because FR-019 permits concurrent
  live sessions; in the desktop tool this could not happen (single
  process, single QApplication).

**Alternatives considered**:
- Treat the existing `errq_bridge.py` import path as canonical and just
  symlink — rejected (the desktop tool is meant to keep evolving on
  Windows; coupling our import path to its file layout would risk
  surprising regressions).
- Bundle the errq CSVs into the backend pip package — rejected (Q3 chose
  configured-path over bundling for live revision parity).

## R5. Concurrency: how a single FastAPI process handles N sessions

**Decision**: Each WebSocket connection creates one `LiveDiagnosticSession`
that owns:
- one `asyncio.subprocess.Process` (the `ssh ... candump` child)
- one `asyncio.Task` reading stdout
- one `asyncio.Task` running the per-session frame pipeline (decode →
  aggregate → fan out)
- one `asyncio.Queue` of outbound messages (bounded, drops oldest on
  overflow per FR-018)

Sessions do not share state. The errq model is loaded once at startup and
shared read-only.

**Rationale**:
- Asyncio gives us cheap "tasks per session" without the per-thread cost.
- Per-session subprocesses match the desktop tool's behaviour (one
  candump per operator) and satisfy FR-019's no-cross-talk requirement.
- The bounded outbound queue is the simplest way to enforce FR-018 — when
  the browser is slower than the testbed, we drop, we don't queue
  unbounded.

**Alternatives considered**:
- A single shared `candump` per host with fan-out to N subscribers —
  rejected (couples session lifecycles, would require de-duplicating
  state, and the testbed already supports multiple ssh sessions per host
  per the existing 002 traffic model).
- Threads per session — rejected (3× the memory cost for no win at this
  scale).

## R6. Disconnect detection + reconnect

**Decision**:
- The backend declares a session "lost" when the `ssh` child exits or its
  stdout returns EOF, OR when no frame has arrived for 10 s (heartbeat
  threshold). On lost, send a `status: lost` envelope to the client and
  `await proc.wait()`.
- The browser shows the "Connection lost" banner from FR-017 with a
  Reconnect button that opens a new WebSocket against the same host. State
  (filter, channel) is preserved client-side.

**Rationale**:
- Two failure modes (clean ssh exit vs. silent stall) need separate
  detection, since `candump` itself doesn't emit heartbeats.
- 10 s matches FR-017's spec of "detect disconnects within ten seconds".
- Reconnect-as-new-session is simpler than session resumption and matches
  what the desktop tool does on auth failure.

**Alternatives considered**:
- A backend-issued WebSocket ping every 5 s — possible but redundant: the
  WebSocket itself has TCP keepalive; the meaningful signal is "are
  frames still arriving?" which a heartbeat threshold captures.
- Server-side session resumption with replay buffer — rejected (FR-018
  caps the buffer; reconnection that picks up "where we left off" is not
  meaningful for live diagnostic, the operator wants the *current* state).

## R7. Phone viewport responsiveness

**Decision**: Use shadcn/ui's `Tabs` to switch between **Signals**, **Errq**,
and **Raw frames** on viewports below `md` (`< 768 px`); show all three as
side-by-side panels on `md` and above. The connection dialog stays a single
column always. Filter input is sticky-bottom on phones so it doesn't get
hidden by the scrolling signal table.

**Rationale**:
- Constitution's Web App Standards mandate ≥ 360 px usability. A
  three-panel layout doesn't fit there; tabs are the simplest accommodation.
- Existing 002 sun-theme palette already includes Tabs styling, so there is
  no new design surface to bring in.

**Alternatives considered**:
- Hide the developer surface entirely on phones — rejected (operators do
  use phones to read live signals from inside a vehicle; the constitution
  applies).
- Three-panel always with horizontal scroll on phones — rejected (poor
  usability, conflicts with Principle III's "operable without
  documentation" intent).

## R8. Test strategy

**Decision**:
- Backend unit tests for `candump_runner.py`, `dbc_decoder.py`,
  `errq_aggregator.py`, `errq_loader.py` use recorded fixtures under
  `backend/tests/fixtures/live/` (a snippet of `candump` output, a tiny
  one-message DBC, a stub errq model directory).
- One backend integration test uses `TestClient.websocket_connect` to
  drive the WebSocket end-to-end against a fake `candump` process (a
  stub binary that emits known lines).
- Frontend unit tests for the WebSocket Zod schemas + the `useLiveSession`
  hook with a mock WebSocket.
- One frontend Playwright (or Cypress, whichever is already wired)
  end-to-end test: open the page with Developer mode on, mock the
  WebSocket, verify the signal table renders, the filter works, and
  the errq panel populates.

**Rationale**:
- Recorded fixtures keep tests deterministic and avoid needing a real
  testbed in CI.
- The integration WebSocket test is the highest-leverage check — it covers
  the schema, the lifecycle, and the back-pressure (FR-018) in one shot.

**Alternatives considered**:
- Live testbed in CI — rejected (tests must run without network access to
  testbeds, per the existing project's test isolation discipline).
- TDD-first for everything — out of scope for this spec; we follow the
  existing project's style (smoke tests on critical path, polish tests
  later — Constitution §Development Workflow / "Quality gates during the
  hackathon").
