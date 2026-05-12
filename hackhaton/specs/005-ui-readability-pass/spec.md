# Feature Specification: UI Readability Pass

**Feature Branch**: `005-ui-readability-pass`
**Created**: 2026-05-07
**Status**: Draft
**Input**: User description: "So I would love to work on the UI, make it more
readable and clearer."

## User Scenarios & Testing *(mandatory)*

The 004 Live diagnostic surface shipped end-to-end on 2026-05-07 and was
exercised against a real testbed. The smoke session surfaced a list of
small-but-real UX issues: connection failures display technical reason
codes (`ssh_failed`, `host_out_of_scope`) instead of plain-language
context; the signal table renders 200+ rows as a flat list with no
visual grouping; backend health (errq / DBC loaded vs degraded) sits in
a corner box that's easy to miss; channel and pause states aren't
visually distinct enough at a glance. None of these are functional
bugs — the surface works — but together they make the page harder to
read than it needs to be.

This feature is a focused **readability and clarity pass** on the SPA,
prioritising the Live diagnostic surface (where today's gaps are most
visible) and applying the same principles to the existing one-shot
diagnostic flow where the same patterns appear. The scope is **visual
hierarchy, copy, and state communication** — not new features, not new
backend behaviour, not redesign of the navigation or branding.

### User Story 1 - Plain-language connection states (Priority: P1)

A developer clicks **Connect** on a TS host and the SSH subprocess
fails — wrong host, missing key, key changed, network down. Today the
page surfaces `Reason: ssh_failed` and the literal first line of stderr
in a small monospace block. The developer has to be technical enough to
read SSH error text and know what to do about it. Even as the developer
who *built* this surface, today's testing showed that the technical
reason codes blur together and the right next step ("ssh once manually
to accept the host key") isn't obvious.

This story rewrites every connection state — idle, connecting,
connected, lost — to read as plain English with one suggested next
action when the operator is stuck. The lost-state error block keeps the
raw stderr (it's still the truth) but pairs it with a one-sentence
plain-language summary and a numbered list of likely fixes ranked by
how often they're the answer ("VPN not connected", "host key changed",
"first contact with this host", "your key isn't in the host's
authorized_keys").

**Why this priority**: Connection failures are the single most common
moment a developer hits friction. Even a 20-second improvement per
failure recovery — operator reads the cause, knows the fix, doesn't
have to alt-tab to a terminal — compounds across a typical debugging
session. This is the change with the highest "minutes saved per
operator-day" ratio.

**Independent Test**: With Developer mode on, deliberately connect to
a host whose key isn't in `~/.ssh/known_hosts`. The lost-state banner
must (a) name the failure in plain English ("We couldn't verify
ts-de-ber-XXXXX's identity"), (b) list at least two ranked likely
causes with concrete fix actions, and (c) keep the raw stderr
accessible behind an expand-toggle for power-users.

**Acceptance Scenarios**:

1. **Given** the operator clicks Connect against a host that's down
   (no route to host), **When** the ssh subprocess fails, **Then** the
   lost-state banner reads "We couldn't reach `<host>`" as the primary
   line, "VPN not connected" as the top-ranked likely cause, and the
   raw stderr is one expand-click away (not gone, not hidden).
2. **Given** the operator clicks Connect against a host whose key has
   changed (real MITM signal), **When** ssh fails with `Host key
   verification failed`, **Then** the banner reads "`<host>`'s
   identity has changed since you last connected" as the primary line
   and surfaces the `ssh-keygen -R <host>` recovery command as a
   copyable block (no auto-execute — operator decides).
3. **Given** the operator is in the *connecting* state and 5 seconds
   have passed without a `connected` flip, **When** the page renders,
   **Then** a one-line reassurance ("Still connecting — first SSH
   handshake can take up to 10 s") replaces the bare spinner so the
   operator doesn't think the page is stuck.
4. **Given** the operator is in the *connected* state, **When** the
   page renders, **Then** the host id, session uptime, and
   "frames/sec arrival rate" appear together as one connected-state
   header so the operator can confirm the testbed is genuinely live
   (not a stale connection that hasn't reported in 30 s).

---

### User Story 2 - Scannable signal + error tables (Priority: P2)

A developer chasing a flagged signal — say `TS_BrakePedalPosition` —
opens the Live diagnostic page and tries to find it in the state panel.
Today's flat table of 200+ rows requires either typing the filter
substring (which works but loses context — the operator no longer sees
neighbouring brake-related signals) or scrolling and scanning. Errq
panel rows have the same issue: severity, name, byte/bit are present
but visual hierarchy doesn't pop the high-severity entries to the top.

This story restructures the two tables for **fast visual scanning**:
group signals by CAN message / channel with collapsible group headers,
visually distinguish numeric / boolean / enum values (so a `true/false`
read isn't styled identically to a `0.42` read), highlight rows that
changed within the last 500 ms with a brief flash so the operator
sees what's *moving* even when not filtering, and reorder the errq
panel by severity-then-recency so critical errors are always above the
fold. The filter input becomes sticky-top on desktop (currently sticky
nowhere) so the operator can keep typing while watching the table
shrink.

**Why this priority**: This is the largest readability win once the
operator is already past the connection-state gates from US1. It's
slightly less critical than US1 because it kicks in only after a
working connection; without US1 the operator never reaches it.
Bundling US1 + US2 produces the bulk of the readability improvement.

**Independent Test**: With a live session showing 100+ decoded signals,
the operator must be able to (a) collapse all message groups except
"Brake" with one click, (b) see at a glance which signals updated in
the last second (visual flash that fades), and (c) sort the errq panel
so a synthesised `critical`-severity entry appears strictly above all
`warn` and `info` entries regardless of byte/bit ordering.

**Acceptance Scenarios**:

1. **Given** a live session is showing 200 decoded signals across 12
   CAN messages, **When** the page renders, **Then** signals are
   grouped by message owner with a collapsible header and a count
   badge per group; the channel column moves into the group header
   (so each row doesn't repeat "A" 30 times).
2. **Given** a signal value changes on the testbed, **When** the new
   value lands in the SPA, **Then** the row briefly highlights (≤ 500
   ms fade) so the operator sees what's actually moving — the
   highlight is independent of the filter and never causes layout
   shift.
3. **Given** the errq panel has 8 active errors of mixed severity,
   **When** the panel renders, **Then** entries are ordered
   `critical → error → warn → info`, with severity-coloured row
   borders (not just badge text) so the visual weight matches the
   urgency.
4. **Given** the operator types `BRAKE` in the filter and the visible
   list shrinks, **When** the operator scrolls, **Then** the filter
   input stays visible at the top of the panel (sticky positioning)
   so the operator can keep refining without scrolling back.

---

### User Story 3 - Onboarding clarity for first-run operators (Priority: P3)

A developer who's never opened the Live diagnostic surface lands on
`/live` for the first time. Today they see an empty host picker (or
"Loading hosts…" if inventory is still arriving), no explanation of
what the page will do once they connect, and a small backend-status
box in the corner that uses jargon ("ERRQ: loaded", "DBC: degraded")
without saying what those words mean for them. If they connect and
the surface ends up in degraded mode (no DBC), the page silently
shows raw frames in the state panel without ever explaining why.

This story rewrites every empty / loading / degraded state on the
Live diagnostic surface to read as plain English with **a one-line
"what this means for you" hint**. Backend status moves out of the
corner into a single inline pill at the top of the page that can be
either green ("Ready"), amber ("Limited — DBC missing, raw frames
only"), or red ("Cannot connect"). Each panel gets an empty-state
illustration + one-line explanation when there's no data yet, so the
operator understands what *will* appear once a session is live.

**Why this priority**: This story serves operators who haven't built
muscle memory for the surface — a new hire, an on-call engineer who
uses it once a quarter, a teammate borrowing the page during an
incident. It's lower priority than US1 + US2 because power-users
adapt to terse copy quickly and don't notice the gap. But removing
the gap makes the page genuinely usable on first contact.

**Independent Test**: Open `/live` in a brand-new incognito window
with `localStorage` cleared. With Developer mode on but no
connection yet, the page must communicate (a) what the page is for,
(b) what state the backend is in (errq + DBC ready or degraded), and
(c) what the next action is — all without the operator needing to
read documentation.

**Acceptance Scenarios**:

1. **Given** the operator has never opened the page before
   (`localStorage` empty), **When** they land on `/live`, **Then** an
   above-the-fold paragraph reads "This page streams live CAN traffic
   from a TS testbed via your local SSH. Pick a host below and click
   Connect to start." — no jargon, no acronym without a tooltip.
2. **Given** the backend's DBC failed to load, **When** the operator
   lands on `/live`, **Then** the backend-status pill at the top of
   the page reads "Limited mode — DBC missing, raw frames only" with
   a "Fix this" link that opens the Settings page to the right field.
3. **Given** the operator is connected but no errq errors are active,
   **When** the errq panel renders, **Then** the empty state reads
   "No active errors on this testbed right now. If a REECU error goes
   active, it'll appear here within ~1 s." — not just "No active
   errors" — so the operator understands the panel is *working*, not
   broken.
4. **Given** the operator is connected and signals are streaming,
   **When** they hover over the connected-state header, **Then** a
   tooltip explains what each piece means (session id, uptime,
   arrival rate) — the page is teachable on hover, not just
   parseable for someone who already knows it.

---

### Edge Cases

- **Long host id overflows the connected-state header**: TS hosts have
  short ids (`ts-de-ber-00010`) but vehicle ids can be longer
  (`ve-de-saturn-slow`). The header must truncate with an ellipsis +
  full-text tooltip, not wrap to a second line that pushes content
  down.
- **Errq panel exceeds 50 rows**: The desktop tool can show ~30
  active errors at once on a misconfigured testbed; the panel must
  remain scannable without consuming the whole viewport — either with
  internal scroll or with severity-grouped collapsibles ("…and 22
  more `info` entries").
- **No DBC loaded but operator clicks Connect**: Today the surface
  silently degrades to raw-frames-only with a small status pill. The
  new degraded-mode banner must be larger, named ("Limited mode"),
  and explain *why* the state panel is empty so the operator doesn't
  think the testbed is silent.
- **Operator on a high-DPI mobile viewport**: 360 px width is the
  constitutional minimum. Group headers, sticky filter, and the
  backend-status pill all need to remain legible at 360 px — this is
  a layout test, not just a copy test.
- **Locale**: Today's SPA is English-only. Copy improvements are in
  English; non-English locales remain out of scope (consistent with
  001 / 002 assumptions).
- **Reduced-motion preference**: The row-update flash from US2 must
  honour `prefers-reduced-motion: reduce` (replace the flash with a
  brief outline change so motion-sensitive operators aren't excluded
  from the readability win).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST replace every operator-visible occurrence of
  the SSH / WebSocket reason codes (`ssh_failed`, `ssh_stalled`,
  `host_out_of_scope`, `unauthorized`, `developer_mode_off`,
  `internal_error`) with a plain-English primary line. The original
  reason code MAY remain accessible behind an expand-toggle for
  diagnostic purposes but MUST NOT be the first thing the operator
  reads.
- **FR-002**: System MUST surface, for every connection failure
  classified as `Host key verification failed`, a copyable
  `ssh-keygen -R <host>` recovery command alongside the plain-English
  explanation. The system MUST NOT auto-execute the recovery; the
  operator decides.
- **FR-003**: System MUST replace the bare connecting-state spinner
  with a reassurance line ("Still connecting — first SSH handshake
  can take up to 10 s") whenever the connecting state has lasted ≥ 5
  seconds.
- **FR-004**: System MUST surface, in the connected-state header, the
  host id, session uptime (seconds-resolution), and the rolling
  frames-per-second arrival rate (computed over the last 5 seconds)
  so the operator can confirm the connection is *active* and not
  stale.
- **FR-005**: System MUST group decoded signals by their CAN message
  owner, with a collapsible group header per group showing the
  message name, channel, and signal-count badge. Each group MUST
  retain the operator's collapsed/expanded state across connect /
  disconnect within the same browser tab.
- **FR-006**: System MUST visually distinguish numeric, boolean, and
  enum signal values in the state panel (e.g. typography weight,
  colour, alignment) so the operator can tell value-types at a glance
  without reading every cell.
- **FR-007**: System MUST visually highlight a signal row when its
  value changes — a brief (≤ 500 ms) fade or outline that does NOT
  cause layout shift. The highlight MUST honour
  `prefers-reduced-motion: reduce` by replacing the fade with a
  static outline change.
- **FR-008**: System MUST order REECU error-queue entries strictly by
  severity (`critical → error → warn → info`), with secondary
  ordering by `(channel, byte, bit)`. Severity colour MUST extend to
  the row's left border (not just the badge), so the visual weight
  matches the urgency at scan distance.
- **FR-009**: System MUST keep the signal-name filter input visible
  (sticky positioning) at the top of the state panel on desktop
  (≥ 768 px). On phone (< 768 px) FR-014 of 004 already covers
  sticky-bottom positioning; this requirement does not regress that.
- **FR-010**: System MUST replace the corner backend-status box with a
  single inline pill at the top of the Live diagnostic page. The pill
  has three states: **Ready** (green — errq + DBC both loaded),
  **Limited** (amber — at least one of errq/DBC degraded), **Cannot
  connect** (red — backend unreachable / 503). Each non-green state
  MUST link to the relevant Settings field.
- **FR-011**: System MUST surface a first-run paragraph above the
  host picker on `/live` (visible whenever `localStorage` has no
  prior `vayobd.live.hostSelection`). The paragraph explains in plain
  English what the page does and what to do next.
- **FR-012**: System MUST replace every empty-state message on the
  Live diagnostic surface with a "what this means for you" sentence —
  not just the negation. Empty errq panel reads "No active errors on
  this testbed right now. If a REECU error goes active, it'll appear
  here within ~1 s.", not "No active errors".
- **FR-013**: System MUST provide a tooltip (hover on desktop,
  long-press on touch) on the connected-state header that explains
  what each piece (session id, uptime, fps) means in plain English.
- **FR-014**: System MUST truncate long host ids in the
  connected-state header with an ellipsis + full-text tooltip rather
  than wrapping to a second line that shifts page layout.
- **FR-015**: System MUST collapse the errq panel into severity
  groups when the active-error count exceeds 20, with a default-open
  state for `critical` and `error` and a default-collapsed state for
  `info` and `warn`.
- **FR-016**: System MUST meet WCAG 2.1 AA contrast for every text +
  background pair touched by this pass (severity colours, status
  pills, group headers, empty-state copy).
- **FR-017**: System MUST NOT introduce any new functional behaviour,
  new endpoints, new backend state, or new persisted client state
  beyond what already exists at the start of this feature. Scope is
  **visual hierarchy, copy, and state communication**, not new
  features.

### Key Entities *(out of scope)*

This feature touches presentation only — no new entities. The data
model from 002 / 004 is the source of truth and is not modified.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of operators presented with a connection failure
  can name the likely cause and the next action in **under 10
  seconds** of seeing the lost-state banner, without reading
  documentation. Baseline (today's surface): operators have to read
  the literal stderr line and infer.
- **SC-002**: The signal a developer is hunting (e.g.
  `TS_BrakePedalPosition`) is locatable within **3 seconds** of the
  page rendering — by group-header collapse, by filter, or by
  scrolling — in 95% of attempts. Baseline: ~10 s on today's flat
  table for an operator who doesn't already know where it lives.
- **SC-003**: A first-time operator (no prior session, no prior
  documentation read) can identify whether the page is in **Ready**,
  **Limited**, or **Cannot connect** state in **under 5 seconds** of
  landing on `/live`. Baseline: today's small corner pill is missed
  on first scan.
- **SC-004**: The page remains operable at **360 px viewport width**
  with no horizontal scroll on the primary panels (state, errq, raw
  frames). Constitutional standard preserved.
- **SC-005**: Every text/background pair touched by this pass meets
  **WCAG 2.1 AA contrast** (normal text ≥ 4.5:1; large text ≥ 3:1).
  Verifiable with any automated contrast checker run against the
  built SPA.
- **SC-006**: The pass adds **zero new HTTP endpoints, zero new
  WebSocket envelope kinds, zero new persisted client storage keys**
  — verifiable by code-diff alone.
- **SC-007**: A return operator (one who already knows the surface)
  takes **no longer to complete a typical CAN debug session** after
  this pass than before. The clarity changes are additive — they
  must not slow down power-users.

## Assumptions

- This pass is primarily about the **Live diagnostic surface** (the
  004 page and its supporting components: HostPicker, StatePanel,
  ErrqPanel, RawFramesLog, PlaybackControls, ChannelToggle,
  LiveDiagnosticPage). The same readability principles MAY be
  applied to other SPA surfaces (the 001/002 wizard, the inventory
  page, the Settings page) but those are secondary; if scope is
  pressured the existing surfaces stay as-is.
- The visual design language is the existing **sun-theme palette**
  introduced in 002. Severity colours, status pills, group headers,
  and row highlights all reuse existing palette tokens — no new
  theme, no new colour roles.
- The existing component library (shadcn/ui + Tailwind) is the
  vocabulary for this pass. New shadcn primitives (e.g. an
  `Accordion` for collapsible groups, a `HoverCard` for tooltips)
  MAY be added as dependencies, but no custom design-system work.
- The 004 WebSocket contract is the source of truth for what's on
  the wire; this pass adapts presentation only. Server-side rate
  limiting, coalescing, and envelope shapes are unchanged.
- Operators on a Linux/macOS workstation with `ssh` and a modern
  browser is the target environment. Windows operators continue to
  use the parallel desktop `TS_diagnostic_tool` per the
  dual-surface story in the repo root README.
- English copy only. Localisation remains out of scope (consistent
  with 001 / 002 assumptions).
- Accessibility target is **WCAG 2.1 AA** (existing constitutional
  standard). AAA compliance is out of scope unless cheap to acquire
  alongside an AA fix.
- Manual smoke + Playwright e2e remain the verification path — this
  pass does not introduce a Vitest toolchain (the gap noted in 004
  T031/T037/T047 stays open).
