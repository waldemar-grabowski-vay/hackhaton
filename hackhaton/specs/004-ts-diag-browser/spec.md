# Feature Specification: TS Diagnostic Tool — Browser Edition

**Feature Branch**: `004-ts-diag-browser`
**Created**: 2026-05-07
**Status**: Draft
**Input**: User description: "You know the TS_DIAG_TOOL? I want to be able to have
this kind of interface in browser with options that are listed in the tool. It
should be available under additional button."

## Clarifications

### Session 2026-05-07

- Q: Live-stream transport — WebSockets, SSE, or short-poll? → A: WebSockets (one full-duplex connection per live session for stream + control)
- Q: How does SSH authentication work? → A: Backend shells out to the operator's system `ssh` binary on the local machine. No credential dialog — `~/.ssh/config`, keys, agent, ProxyJump are reused as-is. The web app surface is therefore local-only (backend on `localhost`).
- Q: Where does the errq error model come from? → A: Read from the operator's local `ree-reecu` clone at a configured path (default `~/GitHub/ree-reecu`, overridable via a backend setting). Mirrors the desktop tool; live revision; no bundling at build time.

## User Scenarios & Testing *(mandatory)*

The desktop **TS Diagnostic Tool** (PyQt6 Windows app at `TS_diagnostic_tool/`)
is the team's deep-inspection surface for TS hosts: it streams `candump` from a
testbed over SSH, decodes CAN frames against the team's DBC, aggregates the
REECU error-queue (`ERRQ_Byte01..64`) bytes per channel, decodes active error
bits via the local `errq` tool, and presents the result as a live state panel
+ error table + raw log. It also has a connection dialog (host, user, port,
key path, passphrase, password) that pops up automatically on auth failure.

This feature ports that same operator experience into the VayOBD web app as a
**second surface** alongside the existing one-shot Run check flow. It does
**not** replace the existing diagnostic flow (which is for non-technical
operators); it adds a Developer-mode-only "Live diagnostic" entry point for
hardware debuggers and on-call engineers who need real-time visibility into a
testbed's CAN traffic and REECU error state from any browser.

### User Story 1 - Live CAN diagnostic surface (Priority: P1)

A developer or hardware debugger working remotely opens the VayOBD web app on
a laptop or phone, sees an additional **"Live diagnostic"** button on the main
page (visible only when Developer mode is enabled in settings), clicks it, and
lands on a surface that mirrors the desktop tool's layout. They pick a TS host
from the same in-scope inventory the existing flow uses, fill in SSH
credentials in a connection dialog, click Connect, and within seconds see CAN
signals streaming in — a live state panel of decoded values, updating in
real time as frames arrive from the testbed.

**Why this priority**: This is the irreducible MVP for the feature. Without
the surface itself + a working connection + live decoded signals, none of the
other panels (errq, filters, log) have anything to show. Delivering only this
story already gives developers a browser-based replacement for the desktop
tool's primary view and removes the need to be on a Windows machine to debug
a testbed.

**Independent Test**: Enable Developer mode in settings, open the main page,
confirm the "Live diagnostic" button is present, click it, choose a reachable
TS host (e.g., `ts-de-ber-00005`), enter valid SSH credentials, connect, and
verify decoded CAN signals start updating on the page within ten seconds of
clicking Connect.

**Acceptance Scenarios**:

1. **Given** Developer mode is off, **When** the operator opens the main
   page, **Then** the "Live diagnostic" button is not visible.
2. **Given** Developer mode is on, **When** the operator opens the main
   page, **Then** an additional "Live diagnostic" button is rendered next to
   the existing primary action.
3. **Given** the Live diagnostic surface is open and no host has been
   selected, **When** the operator picks a TS host from the inventory and
   clicks Connect, **Then** the backend invokes the operator's local
   `ssh` binary, the page transitions to a connected state, and decoded
   CAN signals start streaming into the state panel within ten seconds.
4. **Given** the operator clicks Connect against a host that the local
   `ssh` cannot reach (unknown host, refused connection, missing key,
   wrong key, ProxyJump failure), **When** the `ssh` subprocess exits
   non-zero, **Then** the page surfaces a plain-language error message
   that includes the exit reason ("Could not reach `<host>`. ssh said:
   `<first line of stderr>`. Check your `~/.ssh/config` and try
   again.") and offers a Retry action with the same host pre-selected.
5. **Given** a live diagnostic session is in progress, **When** the SSH
   connection drops mid-stream, **Then** the page shows a "Connection
   lost" banner with a Reconnect button and stops marking signals as live.

---

### User Story 2 - REECU error-queue panel (Priority: P2)

A developer investigating a flagged testbed wants to see exactly which REECU
errors are currently active, not just decoded raw signals. While a live
diagnostic session is connected, the page surfaces a dedicated "REECU error
queue" panel — a table of active errors with symbolic name, severity (info /
warn / error / critical), channel (A or B), byte and bit position, and a
short description. Errors appear when their bit goes active in the streaming
`ERRQ_Byte01..64` signals; they disappear when the bit clears, just like the
desktop tool's lifecycle behaviour.

**Why this priority**: REECU errq decoding is the highest-value piece of
diagnostic IP the desktop tool has that the existing one-shot SPA flow does
not. Surfacing it gives developers immediate insight into hardware faults
without needing to mentally translate raw byte values. It is layered on top
of US1 (which provides the streaming substrate); without US1's live frames
there is nothing to aggregate.

**Independent Test**: With a live session connected to a host known to have
at least one active REECU error, open the error-queue panel and verify the
expected error symbol (e.g. `TS_FOO_BAR_ERR`) appears with non-empty
description, correct channel, and a severity that is not blank, within five
seconds of connecting.

**Acceptance Scenarios**:

1. **Given** a live session is connected and the testbed has zero active
   REECU errors, **When** the operator views the error-queue panel,
   **Then** the panel shows an empty-state message ("No active errors")
   and not a stale list.
2. **Given** a live session is connected and a REECU error becomes
   active on the testbed, **When** the next `ERRQ_Byte` frame is decoded,
   **Then** within one second the error appears in the panel with
   symbolic name, severity, channel (A or B), and byte/bit position.
3. **Given** a REECU error is shown in the panel, **When** the bit
   clears on the testbed, **Then** within two seconds the entry is
   removed from the panel.
4. **Given** the system is unable to load the local `errq` model
   (e.g. CSV files missing on the server), **When** the operator
   opens the error-queue panel, **Then** the panel shows a clear
   degraded-mode message ("REECU error decoding unavailable — raw byte
   values shown instead") and falls back to displaying the raw 64-byte
   buffer per channel.

---

### User Story 3 - Operator tooling (filters, channels, raw log) (Priority: P3)

While inspecting a live session, a developer wants the same auxiliary
controls the desktop tool offers: pick which channel (A or B) to focus on,
filter the visible signals by name substring, toggle a raw-frames log
showing the underlying CAN frames in hex, and pause / resume / clear the
running stream so they can inspect a snapshot without it scrolling away.
None of these are required to read the decoded data, but together they
make a real debugging session productive.

**Why this priority**: These are quality-of-life controls that mirror the
desktop tool's existing toolbar. They are independently testable (each
control works with mock data) but only meaningful once US1 is in place.
They can ship later without blocking the core value proposition.

**Independent Test**: With a live session running, type a substring in the
signal-name filter and verify the visible signal list shrinks; click the
channel toggle and verify only that channel's signals remain; click Pause
and verify the displayed values stop updating (while the underlying
connection stays live); click Resume and verify they update again.

**Acceptance Scenarios**:

1. **Given** a live session is showing 200+ signals, **When** the operator
   types `BRAKE` into the filter input, **Then** only signals whose name
   contains `BRAKE` (case-insensitive) remain visible, and the count is
   shown next to the filter.
2. **Given** a live session is connected to a host with both channels
   active, **When** the operator selects "Channel B only", **Then** only
   Channel B's signals and Channel B's errq panel are rendered.
3. **Given** the operator clicks Pause, **When** new frames arrive from
   the testbed, **Then** the visible state panel does not update, but the
   "X frames buffered" counter increases; clicking Resume flushes the
   buffer and updates the panel.
4. **Given** the operator clicks "Clear", **When** the action is
   confirmed, **Then** all displayed signals reset to "—" and the errq
   panel is emptied, but the live stream itself continues.
5. **Given** the operator toggles "Raw frames log", **When** new frames
   arrive, **Then** a scrolling log of `<can_id> [<dlc>] <hex>` lines is
   rendered below the state panel and is bounded to the last 500 lines.

---

### Edge Cases

- **Developer mode disabled mid-session**: If an operator turns off
  Developer mode in settings while a live session is open in another tab,
  what happens to the open session? Expected: the existing tab continues
  until the operator navigates away; the button is hidden on next render
  of the main page.
- **Errq model load failure**: The local `errq` tool depends on CSV files
  whose absence (e.g. on a fresh server install) leaves the system unable
  to decode error bits. Expected: surface a clear degraded state in the
  error-queue panel; do not break the rest of the live diagnostic surface.
- **DBC missing or out of date**: If no DBC is available on the server, or
  the DBC version does not match the testbed's firmware, decoded signal
  names may be missing or wrong. Expected: a non-blocking warning at the
  top of the surface ("Decoding may be incomplete — DBC missing or
  mismatched") and raw frames continue to be shown.
- **Multiple operators connecting to the same host**: The desktop tool was
  single-user; two operators may now both open Live diagnostic against
  the same testbed. Expected: each session is independent (separate
  `candump` subprocesses on the testbed); no cross-talk.
- **Inventory empty or unavailable**: If the SPA's host inventory is
  empty (e.g. inventory file missing), the host picker in the connection
  dialog must show a clear empty state and not silently break.
- **Slow network**: If frames arrive faster than the browser can render,
  the page must drop frames gracefully (newest wins) rather than
  unbounded buffering.
- **Session left open**: Operators may leave the page open for hours.
  After a long idle period, the surface must either keep the session
  alive or reconnect transparently when the operator returns.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST render an additional "Live diagnostic" entry
  point on the main page, alongside the existing primary action, visible
  only when Developer mode is enabled.
- **FR-002**: System MUST gate the Live diagnostic surface itself behind
  the same Developer-mode setting — direct navigation to its URL by an
  operator with Developer mode disabled MUST redirect to the main page.
- **FR-003**: System MUST present a connection dialog limited to host
  selection — the SPA does NOT collect SSH credentials. The backend MUST
  invoke the operator's local `ssh` binary, which transparently uses the
  operator's existing `~/.ssh/config`, identity files, agent, and
  ProxyJump configuration. Optional one-line "user@" override and
  numeric port override fields MAY be exposed for ad-hoc cases, but
  MUST default to whatever `~/.ssh/config` resolves.
- **FR-004**: Users MUST be able to pick the target host from the same
  in-scope inventory used by the existing diagnostic flow — i.e. only
  Germany hosts are selectable; out-of-scope hosts are filtered out at
  the source.
- **FR-005**: System MUST validate the host selection before attempting
  the SSH session — a missing host or a host outside the in-scope
  inventory MUST produce a field-level error before any subprocess is
  spawned.
- **FR-006**: System MUST surface failures of the spawned `ssh`
  subprocess with a plain-language error that includes the exit code
  and the first line of stderr (so operators can self-diagnose
  unknown-host, permission-denied, ProxyJump, and missing-key
  problems), and MUST keep the host selection so the operator can
  Retry without re-picking.
- **FR-007**: System MUST stream live CAN frames from the connected
  testbed and display decoded signal values in a state panel that
  updates in real time as frames arrive.
- **FR-008**: System MUST decode incoming CAN frames using the team's
  DBC files; signals not covered by the DBC MUST still be visible in
  the optional raw frames log (FR-014) but not in the decoded state
  panel.
- **FR-009**: System MUST aggregate streaming `ERRQ_Byte01..64` signals
  per channel (A and B) into a 64-byte buffer per channel, mirroring the
  desktop tool's aggregator.
- **FR-010**: System MUST decode the per-channel ERRQ buffer using the
  local `errq` tool's model and surface each active error in a dedicated
  REECU error-queue panel with symbolic name, severity, channel, byte,
  and bit position.
- **FR-011**: System MUST remove an error from the panel within two
  seconds of its bit clearing on the testbed, mirroring the desktop
  tool's active/passive lifecycle.
- **FR-012**: System MUST gracefully degrade the error-queue panel when
  the `errq` model cannot be loaded — show a clear degraded-mode message
  and fall back to raw byte values rather than failing the whole surface.
- **FR-013**: System MUST allow the operator to filter the decoded
  state panel by signal-name substring (case-insensitive) and to focus
  on a single channel (A or B) or both.
- **FR-014**: System MUST allow the operator to toggle a raw-frames log
  showing each incoming CAN frame as `<can_id> [<dlc>] <hex>`, capped
  at the last 500 lines.
- **FR-015**: Users MUST be able to pause, resume, and clear the
  visible stream without dropping the underlying SSH session.
- **FR-016**: System MUST remember the operator's last-selected host
  (and the optional user/port overrides, if any) in browser local
  storage so they can reconnect with one click. No SSH credentials are
  ever stored — there are none to store, since `ssh` reads them from
  `~/.ssh/`.
- **FR-017**: System MUST detect and surface SSH disconnects within
  ten seconds with a "Connection lost" banner and a Reconnect action
  that re-uses the last-known credentials.
- **FR-018**: System MUST cap the size of the in-memory frame buffer
  to prevent unbounded memory growth — when frames arrive faster than
  the browser renders, oldest decoded values MUST be dropped (newest
  wins) rather than queued indefinitely.
- **FR-019**: System MUST allow concurrent live sessions from different
  operators against the same testbed; each session MUST be independent
  with no cross-talk.
- **FR-020**: System MUST NOT expose any mutating action on the
  testbed in v1 — the surface is strictly read-only (no setting writes,
  no clear-error commands, no software upload).
- **FR-021**: System MUST NOT collect, transmit, or persist SSH
  credentials — private keys, passphrases, and passwords stay on the
  operator's machine inside `~/.ssh/`, and the backend reaches the
  testbed only by invoking the local `ssh` binary as a subprocess.
  Backend logs MUST NOT capture key contents, agent socket paths, or
  passphrase material if such values ever transit through error output.
- **FR-022**: System MUST load the REECU error model from the
  operator's local `ree-reecu` clone at runtime via a configured
  path (defaulting to `~/GitHub/ree-reecu`, overridable through a
  backend setting). Backend MUST detect a missing or unreadable
  clone at startup and surface the failure clearly through FR-012's
  degraded-mode path; no errq CSVs are bundled with the backend at
  build time.
- **FR-023**: System MUST use a single WebSocket connection per live
  diagnostic session as the transport for both server-push (decoded
  signals, errq updates, raw frames, status events) and client-push
  (pause / resume / clear / channel toggle / filter changes) — control
  messages MUST NOT be split out onto a separate REST endpoint.

### Key Entities *(include if feature involves data)*

- **LiveDiagnosticSession**: Represents one operator's open browser
  session against one testbed. Attributes: operator slug, host id,
  start time, last-frame time, connection state (idle / connecting /
  connected / lost), errq-model state (loaded / degraded), filter and
  channel selections. Lifecycle: created on Connect, kept alive while
  the browser tab is open, torn down on disconnect or navigation away.
- **HostSelection**: The minimal input needed to start a session —
  inventory host id, plus optional ad-hoc user and port overrides that
  default to whatever `~/.ssh/config` resolves. No credential fields.
  Persisted form (FR-016) is browser-local only.
- **DecodedSignal**: One named signal extracted from a decoded CAN
  frame. Attributes: name, value, unit (if known from DBC), channel
  (A / B / unknown), source CAN id, last-updated timestamp.
- **ErrqEntry**: One active error decoded from the per-channel ERRQ
  buffer. Attributes: symbolic name, description, severity (info /
  warn / error / critical), channel, byte (1-based), bit, first-seen
  timestamp, last-seen timestamp.
- **RawFrame**: A pass-through capture of a CAN frame for the optional
  raw log. Attributes: timestamp, can id (hex), dlc, payload (hex).
  Bounded ring buffer (FR-014).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From the moment a developer clicks "Live diagnostic" on
  the main page (Developer mode enabled), they can be looking at
  decoded live signals in **under 30 seconds** assuming the testbed
  is reachable and credentials are correct.
- **SC-002**: A signal value change on the testbed is reflected in
  the decoded state panel **within 200 ms** of the frame arriving on
  the server side, for at least 95% of frames under nominal load.
- **SC-003**: A REECU error becoming active on the testbed appears
  in the error-queue panel **within one second**, and is removed
  **within two seconds** of clearing, for 95% of transitions.
- **SC-004**: 95% of authentication failures are surfaced to the
  operator with a clear, actionable error message in **under five
  seconds** of clicking Connect.
- **SC-005**: The Live diagnostic surface remains responsive — input
  filtering, channel toggle, pause / resume — under sustained
  load of at least 1,000 frames per second from the testbed.
- **SC-006**: 100% of operator actions on the Live diagnostic
  surface are read-only — no v1 control issues a write or mutation
  to the testbed (verifiable from access logs or a security audit).
- **SC-007**: 90% of developers who already use the desktop
  TS Diagnostic Tool can complete a typical CAN debug session
  end-to-end in the browser surface without consulting documentation
  beyond a one-page quickstart.

## Assumptions

- The VayOBD backend runs on the **operator's local machine** (the
  current dev model — backend on `localhost`, frontend on
  `localhost`). This is what makes it acceptable to shell out to the
  operator's local `ssh` binary; the question of running the backend
  on a shared remote server is therefore explicitly out of scope for
  this feature.
- The operator's `~/.ssh/config` already has working entries for the
  in-scope testbed hosts (matching how the desktop tool and the
  existing `engine/ree-debug-cli` already reach them). This feature
  does not introduce any SSH config management; it relies on what is
  already on the operator's machine.
- The existing host inventory (`org/vay/inventory.yaml`, FR-014 of
  002) already lists the in-scope Germany hosts; this feature reuses
  that inventory rather than maintaining its own host list.
- The existing X-Vay-User SSO header (from 001) is the operator
  identifier — connection profiles and live-session tracking key off
  the same operator slug used for the run history.
- Developer mode is a per-operator setting accessible through the
  existing settings flow being introduced in 002 US2 (T052+); this
  feature contributes the toggle definition but does not redesign
  the settings surface.
- The team's DBC files for the TS application bus are accessible to
  the backend at a known path; sourcing or updating those DBCs is
  out of scope here (treated as deployment input).
- The desktop tool's `errq` decoding behaviour (severity heuristic,
  active/passive lifecycle, channel A/B aggregation rules) is the
  reference behaviour — divergences MUST be intentional and called
  out, not silent.
- The testbed allows the same operator to open multiple concurrent
  SSH sessions for `candump` streaming; if a hard per-host concurrency
  limit exists at the testbed side, FR-019 may need to be revised.
- This surface is for *active diagnostic work*, not long-term
  monitoring — recording / replay of sessions, alerting on errors,
  and historical trends are out of scope for v1.
- The SPA's existing visual design language (sun-theme palette from
  002) is reused; this feature does not introduce a new theme.
- The desktop TS Diagnostic Tool stays alive in parallel — this
  feature is additive, not a replacement, so operators on Windows
  engineering boxes can keep using the desktop surface during and
  after the port.
