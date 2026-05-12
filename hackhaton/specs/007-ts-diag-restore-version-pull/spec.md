# Feature Specification: Restore TS_diag entry, host-side version pull, drop API check battery, readability tweaks

**Feature Branch**: `007-ts-diag-restore-version-pull`
**Created**: 2026-05-11
**Status**: Draft
**Input**: User description: "Ok at some point the TS_diag got removed from the webpage interface, we wnat it back. Then the versions of vDrive,vREECU and SEC, should be pulled from host and confirmed with manifest just as in the rust-cli. We should remove the api checks from the host. Implement any tweaks to make the UX easier to read."

## Clarifications

### Session 2026-05-11

- Q: Does the engine subcommand for reading vDrive / vREECU / SEC versions already exist, or does this feature need to add a new one? → A: Already exists — `ree-debug-cli` (Report subcommand) already produces the version values as part of its JSON output. The backend extracts the version-bearing fields from the existing engine output; no rust changes are required in this feature. The work is backend wiring + frontend rendering only.
- Q: When one of the three version fields resolves but another fails (e.g., vDrive OK but SEC times out), what does the response look like? → A: Per-field availability. Each of the three version fields carries its own verdict — including a per-field `unavailable` state with a one-line plain-language reason. Response-level `source` is a summary: `"live"` if at least one field resolved, `"unavailable"` only if all three failed. The page renders each cell against its own state, never collapsing the whole surface to an unavailable banner just because one field couldn't be read.
- Q: How long should the host-version response be cached, and how does the operator force a fresh pull? → A: Short per-host TTL (60 s) with an explicit refresh button on the page. Within the TTL, repeat visits to the same host serve the cached response instantly. The refresh button bypasses the TTL and triggers a fresh engine invocation. The cell-level timestamp ("as of HH:MM:SS") is visible so the operator can see how fresh the data is. After a TTL miss, the page transparently re-pulls on next mount.
- Q: What does each version cell render while the engine invocation is in flight (first mount, after refresh, after TTL miss)? → A: Em-dash with spinner. Each cell renders `—` plus a small spinner during the in-flight window. Once the response lands, the cell flips atomically to its final state (live value + verdict + timestamp, or `unavailable` with the one-line reason). The spinner is the operator-visible distinction between "loading" and "unavailable"; the post-load steady states are unambiguous.
- Q: Where on the page should the restored "Live diagnostic" (TS_diag) entry point appear — global header, main-page primary action, or both? → A: Both. The button appears in the global `AppHeader` (reachable from any sub-page mid-debugging) AND on the main page next to the primary action (prominent on landing). Both renderings honour the 004 Developer-mode gate identically: hidden when Developer mode is off; visible when on. Clicking either lands on the same /live surface.

## User Scenarios & Testing *(mandatory)*

The web app currently sits in an awkward intermediate state during the
006 pivot:

- **TS_diag (the live CAN diagnostic surface from 004) is no longer
  reachable from the main webpage.** The route still exists, but the
  entry-point button vanished — the operator has no way to launch a
  live session without typing a URL.
- **The host-detail page shows `vdrive_manifest`, `vreecu_version`, and
  `sec_version` as em-dashes.** The backend returns
  `source: "placeholder"` and the engine subcommand that would actually
  read those values off the testbed (the way the rust CLI's
  `vdrive_release_drift_check` already does over SSH) is not wired.
- **The legacy "API checks" battery (a sequence of HTTP/Peplink/REECU
  health checks served as a `runs` endpoint) is mid-removal but still
  partially referenced** — leaving dead surfaces and stale wiring on
  the host-side API.
- **The pages that survived the pivot are harder to scan than they
  should be** — wide single-column lists, weak status colours, version
  drift not visually surfaced when actual ≠ manifest.

This feature is a focused tweak round that closes those four gaps so
the SPA is internally consistent again: a developer can launch
TS_diag from the main page in one click, can see real vDrive/vREECU/SEC
versions cross-checked against the manifest on the host-detail page,
no longer sees any vestige of the API-check battery, and finds both
surfaces visually easier to read.

### User Story 1 - Restore TS_diag entry point on the main page (Priority: P1)

A developer with Developer mode enabled opens the web app and lands on
the main page. They expect to see the "Live diagnostic" (TS_diag) entry
point next to the primary action so they can launch a live CAN session
without remembering or bookmarking `/live`. Today the button is missing
from the rendered page — either it was unmounted, the route lost its
chrome, or the server-side health gate that ungated it is no longer
reporting `live_diagnostic.enabled = true`. This story makes it
visible again under the same rules 004 established (Developer mode on,
server-side gate honoured, no SSH credentials prompted in the UI).

**Why this priority**: TS_diag is the team's primary deep-inspection
surface. Losing the discoverable entry point silently broke an
already-shipped feature — every developer who relies on the surface
has to either know the URL or downgrade to the desktop tool. Restoring
visibility is the smallest unit of value worth shipping in this round.

**Independent Test**: With Developer mode toggled on and the backend
running locally, open the main page and verify the "Live diagnostic"
button is rendered next to the primary action; click it and verify the
existing /live surface loads. With Developer mode off, verify the
button is absent (it has always been a Developer-mode-gated entry per
004 FR-001).

**Acceptance Scenarios**:

1. **Given** Developer mode is on and the backend reports the live
   surface as available, **When** the operator opens the main page,
   **Then** two clearly labelled "Live diagnostic" entry points are
   visible — one in the global header and one next to the
   primary action on the main page — and both are clickable.
2. **Given** Developer mode is off, **When** the operator opens the
   main page, **Then** neither entry point is rendered (matching
   004 FR-001's original gating; the header and main-page
   renderings disappear together).
3. **Given** the operator clicks either entry point, **When** the
   page navigates, **Then** the existing /live surface opens with
   the same connection dialog and inventory behaviour shipped in
   004 (this feature does not redesign the surface — it only
   restores the entry points).
4. **Given** Developer mode is on and the operator has navigated
   away from the main page (e.g., to the host-detail page or to
   /live itself), **When** the operator scans the chrome, **Then**
   the header entry point remains visible and clickable so they
   can launch a new live session without going back to the main
   page first.

---

### User Story 2 - Host-side version pull cross-checked against manifest (Priority: P1)

A developer opens the host-detail page for a TS or VE host. Today the
page shows three em-dashes ("—") for vDrive manifest, vREECU, and SEC
because the backend returns `source: "placeholder"`. The desktop / rust
CLI already has working code that SSHes to the host, runs
`dpkg-query` (and equivalent) for the relevant packages, parses the
version + embedded SHA, and compares it against `vdrive.{telestation,
vehicle}.sw_version` from `release-configs.yaml` — flagging drift as a
warning. This story brings that exact behaviour into the host-detail
surface so the operator sees real values, cross-checked, with the same
drift verdict the CLI would give.

**Why this priority**: This is the primary value proposition of the
host-detail page after the 006 pivot. Without real data, the page is a
shell. The rust engine already knows how to do this work; the gap is
purely a backend wiring + frontend rendering job.

**Independent Test**: On a properly-credentialed laptop with SSH
access to a reachable TS host, open the host-detail page for that
host. Verify each of the three version cells (vDrive manifest, vREECU,
SEC) shows a non-em-dash value sourced from the host within ten
seconds of page load, that the response carries `source: "live"`, and
that the cell is marked as "matches manifest" or "drift vs manifest
<expected>" using the same comparison rule the rust CLI uses
(SHA-prefix match against `vdrive.{telestation,vehicle}.sw_version`).

**Acceptance Scenarios**:

1. **Given** the operator opens a reachable host's detail page,
   **When** the page resolves, **Then** the three version cells each
   render the value that the engine reads from the host (not the
   em-dash placeholder), and the response source is `"live"`.
2. **Given** the engine resolves a vDrive package version whose
   embedded git SHA prefix-matches the manifest's `sw_version` for
   the corresponding host kind, **When** the cell renders, **Then**
   it shows the version with a "matches manifest" indicator.
3. **Given** the engine resolves a vDrive package version whose
   embedded SHA does NOT match the manifest, **When** the cell
   renders, **Then** it shows the actual version, the expected
   manifest value, and a visible drift indicator that an operator
   can distinguish at a glance from "matches".
4. **Given** the engine cannot reach the host at all (SSH failure,
   host down, missing key), **When** the page renders, **Then** all
   three cells render the `unavailable` state with a one-line
   plain-language reason on each, the response-level `source` is
   `"unavailable"` (all three field verdicts are `unavailable`), and
   the reason is visible on the page (not buried in dev tools).
6. **Given** the engine reaches the host and reads vDrive, but the
   SEC package is not installed on this host, **When** the page
   renders, **Then** the vDrive cell shows its live value with the
   appropriate verdict (`match` / `drift`), the SEC cell shows the
   `unavailable` state with its own one-line reason ("SEC package
   not installed on this host"), and the response-level `source` is
   `"live"` (at least one field resolved). The vDrive cell is NOT
   forced into `unavailable` just because SEC failed.
5. **Given** the manifest itself is missing or unreadable on the
   operator's machine, **When** the page renders, **Then** the cells
   show the live host value with an explicit "no manifest available"
   note rather than silently asserting "match"
   (mirrors the rust CLI's "(no manifest available — check
   ~/GitHub/system-release-deployment)" wording).

---

### User Story 3 - Remove the legacy API check battery (Priority: P2)

The pre-pivot diagnostic flow ran a battery of host checks (Peplink,
REECU API endpoints, ree_cli probes) on each "Run" and rendered a
result page of category-grouped pass/fail rows. The 006 pivot replaces
that with the version-only host-detail surface. The backend `checks/`
module and the `/api/runs` endpoint are mid-removal (the working tree
already deletes most of the files); this story finishes the job so
that no code, route, fixture, or UI affordance for the API-check
battery remains.

**Why this priority**: P2 because Story 2 is what the operator actually
*sees* on the host-detail page; this story is the cleanup that
prevents stale routes / dead components / orphan tests from leaking
into the next release. Shipping Story 2 without finishing Story 3
leaves the backend exposing endpoints that no UI calls and an
inventory of result components nothing imports.

**Independent Test**: Search the codebase for the deleted modules and
the `/api/runs` route. Confirm there are no remaining imports,
references in route registration, frontend hooks or pages, fixture
files, or tests for the old check battery — and that `npm run build`,
`pytest`, and the linter all succeed without warnings about removed
symbols.

**Acceptance Scenarios**:

1. **Given** the working tree after this story lands, **When** the
   backend is started, **Then** the FastAPI app does NOT register a
   `/api/runs` route (or any descendant under it).
2. **Given** the working tree after this story lands, **When** the
   frontend bundle is built, **Then** there is no `runs.ts` API
   client, no result-page components (CategoryBadge, ResultGroup,
   ResultHero, DiagnosticItemRow, RepairGuideSheet, HarnessDiagram,
   TelestationDiagram, RunningState, PartialRunState,
   UnreachableState), and the bundle compiles with no
   "unresolved import" warnings.
3. **Given** the test suite is executed, **When** pytest and the
   frontend tests run, **Then** no test references the old check
   battery (no `test_runs_endpoint.py`, no `test_catalog.py`, no
   fixtures named after the legacy executor) and every remaining
   test passes.
4. **Given** the in-repo documentation, **When** an operator reads
   the quickstart or any user-facing strings, **Then** no surface
   instructs them to "Run checks" against a host — the only diagnostic
   surfaces documented are TS_diag (live) and the host-detail
   version page.

---

### User Story 4 - Readability tweaks across the two surviving surfaces (Priority: P3)

The two surviving surfaces — main page (picker + entry points) and
host-detail page (versions card) — carry over rough edges from the
pivot. Single-column layouts that waste horizontal space, version
drift not visually surfaced when actual ≠ manifest, the "source"
indicator buried as a small chip, em-dash placeholders with no
explanation. This story applies a focused readability pass — same
spirit as 005 — to those two surfaces without redesigning either.

**Why this priority**: P3 because the surfaces are functional without
these tweaks; the gains compound over many sessions but no single one
is blocking. Shipping Story 4 after 1-3 is fine; gating 1-3 on it is
not.

**Independent Test**: Two passes — one with Developer mode on, one
off. On each, navigate from main page to host detail to /live (DM on)
and back. Verify (a) the host-detail version cells visually
distinguish "match", "drift", and "unavailable" at a glance without
having to read the small text; (b) the "source" indicator (live /
placeholder / unavailable) is positioned so an operator scanning the
page top-to-bottom notices it before reaching for the values; (c)
em-dash placeholders carry a one-line plain-language explanation
(matches the 005 spirit of "no silent failures").

**Acceptance Scenarios**:

1. **Given** the host-detail page renders with one cell matching the
   manifest and one cell drifted, **When** the operator scans the
   page, **Then** the two states are immediately distinguishable by
   colour and/or icon — not only by reading the text.
2. **Given** the page renders with `source: "unavailable"`, **When**
   the operator scans the page, **Then** the source indicator is
   visually prominent (not a small grey chip in a corner) and reads
   in plain English ("couldn't reach the host" rather than
   "unavailable").
3. **Given** the main page renders with TS_diag visible (Developer
   mode on), **When** the operator scans the page, **Then** the
   TS_diag entry point reads as an entry-point button (matches the
   existing primary-action visual weight), not as decorative chrome.
4. **Given** the manifest is missing locally, **When** the
   host-detail page renders, **Then** the page surfaces the
   "(no manifest available — check ~/GitHub/system-release-deployment)"
   note inline next to the affected cells (not as a global banner)
   so the operator can attribute the message to the right cell.

---

### Edge Cases

- **Developer mode toggled mid-session**: an operator with Developer
  mode on opens the main page, sees the TS_diag entry point, then
  toggles Developer mode off in another tab. Expected: the entry
  point disappears on next render of the main page (already 004's
  established behaviour — this feature preserves it).
- **Engine binary missing / wrong**: the host-detail page calls into
  the engine to read versions; if `ree-debug-cli` is missing from
  PATH or returns a non-zero exit, the cells must fall through to
  `source: "unavailable"` with a plain-language reason — not a 500
  to the SPA.
- **Manifest stale**: `release-configs.yaml` may be older than the
  vDrive build deployed on the host (engineer pushed a hot-fix
  without a manifest bump). The page must still render — drift is a
  warning, not a hard error.
- **Backend started with no inventory**: opening the host-detail URL
  for a host id the inventory doesn't know about must surface a
  plain-language 404 ("host not found in the current inventory"),
  not a generic 503.
- **TS_diag route still navigable when entry point hidden**: with
  Developer mode off, the route `/live` itself must remain gated
  (matches 004 FR-002 — the redirect, not just the missing button).
  Restoring the entry point does NOT relax that gate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The "Live diagnostic" entry point (the TS_diag launcher
  from 004) MUST be rendered in TWO places, each clearly labelled
  and each obeying the same visibility rules established by 004
  FR-001 (visible only when Developer mode is enabled):
  1. The global `AppHeader` chrome, so the button is reachable from
     any sub-page during a mid-debugging session.
  2. The main page's primary-action area, so the button is
     prominently discoverable on landing.

  Both renderings MUST link to the same `/live` surface and MUST
  appear and disappear together as Developer mode is toggled. If the
  current rendering pipeline silently drops either button when the
  server-side gate fails to report it, this MUST be diagnosed and
  fixed so both reappear under the established conditions.
- **FR-002**: The main page MUST continue to obey 004 FR-002 — direct
  navigation to `/live` with Developer mode off MUST still redirect
  to the main page. This feature restores the entry point only; it
  does not relax the gate.
- **FR-003**: The host-detail page MUST display three version values
  for the selected host — `vdrive_manifest`, `vreecu_version`,
  `sec_version` — sourced from the host itself via the engine, not
  from a placeholder. The values MUST be the same values the rust
  CLI's existing `vdrive_release_drift_check` (and equivalent
  vREECU / SEC code paths) already produce when run from a terminal
  against the same host.
- **FR-004**: The host-detail backend MUST invoke the engine via its
  already-shipping `ree-debug-cli` interface (the existing JSON-emitting
  Report path) and parse the structured output to populate the three
  version fields. No new engine subcommand is added by this feature;
  the rust engine already produces vDrive / vREECU / SEC version
  values and the manifest comparison as part of its per-host report.
  No code path may continue to return `source: "placeholder"` in
  production.
- **FR-005**: For each of the three version values, the response
  MUST include a per-field verdict comparing the live value against
  the bundled manifest using the same rule the rust CLI uses
  (SHA-prefix match for vDrive; appropriate equivalent comparison
  for vREECU and SEC — defined by the rust engine's existing logic,
  not invented here). Allowed per-field verdicts: `match`, `drift`,
  `no-manifest` (manifest unavailable on this machine), `unavailable`
  (this field could not be read on this host — engine timed out,
  package missing, parse error, or other field-specific failure).
  Fields are independent: one cell may be `match` while another is
  `unavailable` in the same response.
- **FR-006**: When any verdict is `drift`, the host-detail page MUST
  render the actual host value and the manifest's expected value
  side-by-side so the operator can see both without expanding a
  tooltip.
- **FR-007**: When a field's verdict is `unavailable`, the response
  MUST carry a one-line plain-language reason for THAT field, and
  the page MUST surface that reason inline with the affected cell
  (e.g., "couldn't read SEC version — package not installed";
  "couldn't reach `<host>` over SSH"). The reason text source is
  the engine's stderr / exit-status / structured-error output
  reduced to a single human-readable line per field, following the
  005 plain-language policy. Two fields with different failure
  modes MUST surface different reasons; never a single shared
  banner.
- **FR-008**: The legacy API check battery MUST be removed end-to-end
  — backend `checks/` package, `/api/runs` route registration, the
  frontend `api/runs.ts` client, every result-page component listed
  in deletion scope (CategoryBadge, ResultGroup, ResultHero,
  DiagnosticItemRow, RepairGuideSheet, HarnessDiagram,
  TelestationDiagram, RunningState, PartialRunState,
  UnreachableState, StaggeredList), tests under
  `test_runs_endpoint.py` / `test_catalog.py`, and any fixture or
  string referencing the old battery. No import / route / link to
  the removed surface may remain.
- **FR-009**: Existing user-facing strings (English) MUST be updated
  to remove any mention of "Run checks" / "diagnostic run" framed
  as a battery of checks against a host. The host-detail page is the
  only post-pivot diagnostic surface for a static host; TS_diag is
  the only live-stream surface.
- **FR-010**: The host-detail page MUST visually distinguish the
  three verdict states (`match`, `drift`, `unavailable`, plus the
  `no-manifest` qualifier) using colour and/or icon — not only by
  reading the cell text — so an operator scanning the page can
  identify drift at a glance.
- **FR-011**: The "source" indicator on the host-detail page
  (`live` / `unavailable` / and the now-temporary `placeholder`
  during rollout) MUST be positioned and styled so it is visible
  during normal page scanning, and its wording MUST be plain-language
  (no `unavailable` raw enum strings shown to the operator).
- **FR-012**: Em-dash placeholders for missing values in steady
  state (post-response) MUST carry a one-line plain-language
  explanation in the same cell or its immediate label so the
  operator never sees a bare em-dash without context (matches 005's
  "no silent failures" spirit). The in-flight loading state is
  exempt: while the engine invocation is pending, the cell renders
  `—` accompanied by a visible spinner (FR-020), which the operator
  reads as "loading" rather than "unavailable."
- **FR-020**: While the engine invocation for a host is in flight
  (first mount, post-refresh, or post-TTL re-pull), each of the
  three version cells MUST render `—` plus a visible spinner. Once
  the response lands, every cell MUST flip atomically (within the
  same render) to its final steady state — live value + verdict +
  timestamp for resolved fields, or the `unavailable` plain-language
  reason for unresolved ones — so the operator never sees a
  half-rendered card.
- **FR-013**: The restored "Live diagnostic" entry points MUST each
  read as actionable entry points, not as decorative chrome. The
  main-page rendering MUST match the visual weight of the existing
  primary action on that page; the header rendering MUST match the
  visual weight of other actionable header chrome (e.g., the
  Developer-mode toggle, EngineModeBadge), so neither button is
  visually swallowed by its surroundings.
- **FR-014**: The host-detail page MUST tolerate engine failures
  (binary missing, non-zero exit, malformed output) by returning
  `source: "unavailable"` with a one-line reason, never a 5xx to
  the SPA.
- **FR-015**: The host-detail backend MUST log the engine invocation
  (command, exit code, duration) for support, but MUST NOT log
  raw SSH stderr fragments that could leak agent socket paths or
  key material (mirrors 004 FR-021).
- **FR-016**: When `release-configs.yaml` cannot be read at runtime
  (file missing, parse error), the host-detail response MUST still
  render the live host values with verdict `no-manifest` and a
  visible note pointing the operator at the expected manifest path
  — it MUST NOT fall back to `placeholder` or fail the request.
- **FR-017**: The host-version response MUST be cached per-host with
  a short TTL (60 s). Within the TTL, repeat visits to the same
  host's detail page MUST serve the cached response without
  spawning a new engine invocation. After the TTL expires, the
  next page mount MUST transparently trigger a fresh engine
  invocation. The cache is per-host, not global — a fresh pull for
  host A does not invalidate the cache for host B.
- **FR-018**: The host-detail page MUST render an explicit refresh
  affordance (button or icon) that bypasses the FR-017 TTL and
  triggers a fresh engine invocation for the current host. While
  the refresh is in flight, the page MUST indicate the in-progress
  state so the operator does not double-click. The refresh button
  is always visible — not only when the cache is stale.
- **FR-019**: Each cell on the host-detail version surface MUST
  carry a visible "as of `<time>`" timestamp showing when its
  underlying value was last fetched, so the operator can see at a
  glance whether the data is current or near the TTL boundary.

### Key Entities *(include if feature involves data)*

- **HostVersions** (existing wire shape, extended): each of
  `vdrive_manifest`, `vreecu_version`, `sec_version` becomes a
  per-field record carrying — at minimum — the live value (or null),
  the per-field verdict (`match` / `drift` / `no-manifest` /
  `unavailable`), the expected manifest value when verdict is
  `drift`, and a one-line plain-language reason when verdict is
  `unavailable`. Fields are independent: one may be `match` while
  another is `unavailable` in the same response.
- **HostVersionsResponse** (existing): `host`, `versions`, `source`.
  `source` is a response-level *summary* of the three per-field
  states — `"live"` if at least one field resolved with a non-null
  value, `"unavailable"` only if all three field verdicts are
  `unavailable`. The `"placeholder"` value is removed when FR-004
  lands.
- **Manifest** (existing — supplied by the rust engine's
  `manifest.rs` helpers): the parsed `release-configs.yaml`
  exposing `vdrive_ts` / `vdrive_ve` and the equivalent vREECU / SEC
  expected versions. Read at engine invocation time; not cached
  separately by the backend.
- **TS_diag entry point** (existing component): the
  `LiveDiagnosticButton` mounted in the app header. This feature
  ensures it remains rendered under 004's gating rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With Developer mode on, **100%** of operators see
  both "Live diagnostic" entry points (header and main page) within
  one render cycle of the relevant page mounting. With Developer
  mode off, **0%** see either entry point (matches 004's gating
  intent; the two renderings appear and disappear together).
- **SC-002**: When the host-detail page is opened for a reachable
  host, real vDrive / vREECU / SEC versions are displayed within
  **10 seconds** of page mount in at least **95%** of attempts on
  typical SSH conditions. The em-dash placeholder appears only when
  the engine could not produce a value, never as a default render
  state.
- **SC-003**: For every host where the rust CLI reports a vDrive
  drift verdict, the host-detail page reports the same verdict
  (same `match` / `drift` / `no-manifest` outcome) on **100%** of
  spot-checks during acceptance.
- **SC-004**: After this feature lands, **zero** files matching the
  legacy check-battery namespace (`backend/src/vayobd/checks/**`,
  `backend/src/vayobd/api/runs.py`, `frontend/src/api/runs.ts`,
  `frontend/src/components/result/**`, the listed deprecated state
  components) remain in the working tree, and **zero** test
  references to those names remain.
- **SC-005**: An operator can visually distinguish "match" vs
  "drift" vs "unavailable" on the host-detail page in **under two
  seconds** of glancing at the page, without reading the small
  text — verified by a one-pass UI walk-through during acceptance.
- **SC-006**: After this feature lands, the only diagnostic
  surfaces documented in the in-repo quickstart / README are the
  host-detail version page and TS_diag (live). No documentation,
  CLI help, or in-app string references the removed run-checks
  battery.
- **SC-007**: Re-visiting the same host's detail page within the
  TTL window completes in **under 500 ms** (no SSH spawn,
  cache-served). Crossing the TTL boundary re-spawns the engine
  and meets SC-002's 10-second budget on at least 95% of
  attempts.

## Assumptions

- The 004 Live Diagnostic surface (TS_diag) and its server-side
  Developer-mode gate via `/api/health.live_diagnostic.enabled` are
  the established truth. This feature restores discoverability; it
  does not redesign the surface or relax its gate.
- The rust engine (`engine/ree-debug-engine`,
  `engine/ree-debug-cli`) already implements the vDrive drift
  comparison (see `checks/reecu.rs::vdrive_release_drift_check` and
  `manifest.rs::extract_sha` / `normalize_version`) AND already
  exposes the result via its existing CLI interface — confirmed in
  the 2026-05-11 clarification. Equivalent comparisons for vREECU
  and SEC are assumed to exist in the same engine namespace and to
  be carried through the same CLI output path. The backend extracts
  the three version-bearing fields from that output; this feature
  introduces no rust-side code change.
- `release-configs.yaml` continues to live at the path the rust
  engine expects (`~/GitHub/system-release-deployment/...` or
  equivalent). Sourcing or relocating the manifest is out of scope
  here.
- Operators have the same SSH credential surface 004 already relies
  on (`~/.ssh/config`, `ssh-agent`, key files). No new credential
  prompt is introduced by this feature.
- The 006 .deb package work continues in parallel and will eventually
  ship the engine binary alongside the backend. This feature does
  not block on the .deb landing — the backend simply shells out to
  whatever engine binary is on PATH, the same way the rust CLI does.
- The legacy `runs` flow has no production users today (it pre-dated
  the 006 pivot and was never re-exposed after the 004 / 006 work
  began). Removing it does not require a deprecation window.
- The 005 readability principles (plain-language errors, scannable
  layout, no silent failures) carry over verbatim to the two
  surfaces in scope here. This feature does not redesign 005's
  conventions — it applies them to surfaces 005 did not directly
  touch.
- The SPA's existing visual design language (sun-theme palette from
  002) is reused; this feature does not introduce a new theme.
- The desktop TS Diagnostic Tool remains available as a fallback on
  Windows engineering boxes; this feature is additive parity work
  on the web surface, not a desktop replacement.
