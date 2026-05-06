# Feature Specification: Remote Host Diagnostics

**Feature Branch**: `001-host-diagnostics`
**Created**: 2026-05-06
**Status**: Draft
**Input**: User description: "The user should be able to debug an remote host, via an web app. He doesn't need to know what is happening underneath. With use of the app, he should get list of items that are working as intened. But as well the ones with errors. The errors will have a variety of inputs. Such as CAN, missing USB devices, configs."

## Clarifications

### Session 2026-05-06

- Q: Display language for v1 (English-only / EN+DE bilingual / region-aware DE↔US)? → A: English-only.
- Q: Host picker UX shape (flat grouped list vs. step-by-step wizard, and step ordering)? → A: Step-by-step wizard — Country → Type of host → (City step only if Type = Telestation) → Host. Inventory is small enough that no in-app search is required for v1.
- Q: Behaviour when the inventory source is unavailable (single blocking message / partial best-effort / cached fallback)? → A: Local cached copy on the operator's machine is the runtime source of truth. It is refreshed periodically and can also be pulled manually. Live access to the central source is not required while the app is in use; only a missing local copy (e.g., first-time install) blocks the wizard.
- Q: Should v1 expose underlying technical detail per item (operator-only / per-item raw expand for everyone / dual-mode)? → A: Two modes — **Operator** (default, no raw output) and **Developer** (per-item expand reveals raw underlying output: CAN trace, exit codes, file paths, parser messages). Switched via a **manual toggle in the app header**; default on first load is Operator. Same routes and data in both modes; only the affordances differ.
- Q: What can the operator do during an in-progress run (wait only / cancel / cancel + background)? → A: **Wait only.** No cancel control, no background-run pattern in v1. The operator observes progress (FR-009) until completion, timeout, or failure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run a check and see what is broken (Priority: P1)

A non-technical operator opens the web app and picks the remote host
they want to check via a short step-by-step wizard:
**Country → Type of host → (City, only when Telestation) → Host**.
They then start a diagnostic run. After a short wait, they see a
single screen showing the **exact, complete list of items that were
checked**, split into two clearly labelled groups:

- **Working** — items confirmed healthy on that host, listed by name.
- **Needs attention** — items in error, each listed by name with a
  plain-language description of the problem and a recommended next action.

Every item that the diagnostic covers for this host is shown in one of the
two groups, so the operator can confirm exactly what was inspected — not
only what failed. Aggregate "all good" messages alone are not sufficient;
the individual item names are always visible.

**Why this priority**: This is the entire point of the feature. Without it
the tool delivers no value. It is also the smallest viable slice that an
operator can use to answer "is this host ready or not?" — and "did you
actually check X?" — in the field.

**Independent Test**: Open the app, pick a host, click "Run check". The
acceptance criterion is that the operator — with no prior briefing — can
correctly say within 5 seconds (a) whether the host is fully working,
partially working, or unusable, and (b) name at least three specific items
that the diagnostic just inspected.

**Acceptance Scenarios**:

1. **Given** the host is reachable and fully healthy, **When** the operator
   runs a check, **Then** the result shows a non-empty "Working" group that
   enumerates every item that was checked by name, an empty "Needs
   attention" group, and an explicit "All checks passed" indicator.
2. **Given** the host has at least one failing check (for example a missing
   USB device), **When** the operator runs a check, **Then** that item
   appears in "Needs attention" with a plain-language description and a
   recommended next action, and every other item that was checked appears
   in "Working" by name.
3. **Given** the host is reachable, **When** the operator runs a check,
   **Then** the union of items shown in "Working" and "Needs attention"
   equals the full set of items the diagnostic covers for that host's
   class — no checked item is hidden from the result.
4. **Given** the host is unreachable, **When** the operator runs a check,
   **Then** the result is a single clear message stating the host could not
   be reached, **not** a list of individual item errors.

---

### User Story 2 - Re-check after a fix (Priority: P2)

After taking the recommended next step on an errored item (for example
re-seating a USB device or correcting a config value), the operator can
re-run the same check on the same host with one click and see the result
view refresh.

**Why this priority**: Verifying a fix is the natural follow-up to seeing an
error. Without an in-app re-check the operator has to leave the app or
guess, which breaks the simplicity-first promise. It is a small extension on
top of P1, not a new flow.

**Independent Test**: After completing a P1 run with at least one error,
correct the underlying issue out-of-band, then click "Run check again". The
previously errored item now appears in "Working".

**Acceptance Scenarios**:

1. **Given** a previous run showed a USB device missing, **When** the device
   is reconnected and the operator re-runs the check, **Then** the new
   result shows that item under "Working".
2. **Given** a previous run showed a configuration error, **When** the
   operator re-runs the check without changing anything, **Then** the same
   error is still reported (the result reflects the live state, not a
   cached one).

---

### User Story 3 - Understand when and what was checked (Priority: P3)

The operator can see the timestamp of the last check on the result screen
and can confirm at a glance which host was checked. Each item is labelled
with a plain-language category (for example "Communication", "Hardware",
"Configuration") so the operator has a sense of what kind of problem they
are looking at, without needing to know what CAN, USB, or config files are.

**Why this priority**: This builds confidence that the displayed result is
fresh and is for the right host. It is comfort and trust rather than
core function, so it is the lowest priority.

**Acceptance Scenarios**:

1. **Given** a completed run, **When** the operator looks at the result,
   **Then** the host identifier and the run timestamp are visible without
   scrolling.
2. **Given** a completed run with mixed errors, **When** the operator looks
   at the "Needs attention" group, **Then** each item shows a category label
   they can understand without prior technical knowledge.

---

### Edge Cases

- **Host unreachable**: The result MUST be a single user-facing message
  ("Host could not be reached"), not a list of fabricated item-level
  errors.
- **Check times out partway**: The result MUST be marked as partial and
  indicate which kinds of checks did not complete, so the operator does not
  mistake an incomplete run for a clean bill of health.
- **Same error repeated multiple times** (for example three identical config
  problems): The result SHOULD group or otherwise present these so the
  operator is not overwhelmed by duplicate noise.
- **Underlying tooling produces an unhelpful raw error** (stack trace,
  numeric code): The Operator view MUST hide it. The same raw output is
  surfaced through the per-item expand control in Developer mode (see
  FR-020 – FR-023); it MUST NOT appear in Operator mode under any
  condition.
- **Operator triggers a second check while one is already running on the
  same host**: The system MUST not start two concurrent runs against the
  same host; the second click is either ignored or queued, with feedback to
  the operator.
- **Host newly provisioned with no expected USB devices recorded yet**: The
  diagnostic MUST behave deterministically — either declare the host
  unsupported or fall back to a documented baseline check set, not silently
  return an empty pass.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST let the operator pick the remote host to diagnose
  from a pre-registered inventory. The inventory is sourced from the
  team's existing `ree-vehicle-configs` configuration repository; free-form
  host identifier entry MUST NOT be supported in v1.
- **FR-001a**: The host picker MUST be presented as a step-by-step wizard
  with the following ordered steps:
  1. **Country** — the operator picks **Germany** or **United States**.
  2. **Type of host** — the operator picks **Vehicle** or **Telestation**.
  3. **City** — only when Type is **Telestation**. The operator picks
     from the cities present in the chosen country (for example Berlin
     for DE; Las Vegas, Lincoln, Nuq for US — exact set is whatever the
     inventory currently contains). When Type is **Vehicle**, this step
     MUST be skipped entirely; vehicles are not associated with a city.
  4. **Host** — the operator picks the specific host from the list
     filtered by the prior steps.
  At each step the operator MUST be able to go back to the previous step
  without losing earlier selections.
- **FR-001b**: Country and (for telestations) city MUST be derived
  deterministically from the host file-name prefix in
  `ree-vehicle-configs`: `ve-de-*` / `ts-de-*` → Germany,
  `ve-us-*` / `ts-us-*` → United States; for telestations the third
  segment of the file name is the city code (e.g., `ts-de-ber-*` → Berlin,
  `ts-us-las-*` → Las Vegas). Hosts whose country prefix is neither `de`
  nor `us` (e.g., `ve-be-*`, `ts-be-*`) are out of scope for the v1
  picker and MUST NOT appear at any step.
- **FR-001c**: The picker MUST NOT require an in-app search or type-ahead
  filter in v1. Each wizard step MUST display the available choices as a
  single visible list/group; if the list grows beyond what fits on one
  screen, simple scrolling is acceptable.
- **FR-002**: System MUST start a diagnostic run on the chosen host in
  response to an explicit operator action; runs MUST NOT start automatically
  in v1.
- **FR-003**: System MUST present results as two clearly distinguished
  groups in a single view: items confirmed working and items requiring
  attention. Every item that the diagnostic covers for the chosen host
  MUST appear by name in exactly one of the two groups; aggregate-only
  summaries (for example "all good") without item names are not
  acceptable.
- **FR-004**: For every item displayed, system MUST show a plain-language
  name and a short plain-language status description; raw error codes,
  stack traces, and developer-only output MUST NOT appear in the primary
  view.
- **FR-005**: For every item in the "Needs attention" group, system MUST
  include a recommended next action stated in plain language and tied to
  what the operator can do (for example "Reconnect the USB device labelled
  X" rather than "errno 19").
- **FR-006**: System MUST distinguish three top-level run outcomes — fully
  reachable and complete, partially complete (some checks could not run),
  and host unreachable — and present each with a different, unambiguous
  user-facing message rather than a generic error list.
- **FR-007**: System MUST display the timestamp at which the run was
  performed and the identifier of the host it ran against, both visible
  without scrolling on a phone-sized viewport.
- **FR-008**: System MUST allow the operator to re-run the same check on
  the same host with a single action without re-entering the host or any
  other parameter.
- **FR-009**: System MUST show clear in-progress feedback while a check is
  running so the operator can tell the app is working, and MUST surface a
  user-facing message if the run takes longer than the expected typical
  duration.
- **FR-010**: System MUST classify each error item with a plain-language
  category label (for example "Communication", "Hardware", "Configuration")
  so the operator gets context without exposure to underlying terms (CAN,
  USB, config files).
- **FR-011**: System MUST prevent two concurrent runs against the same host
  from being initiated by the same operator; further trigger attempts
  during a live run MUST be either no-ops with feedback or queued, never
  silently dropped.
- **FR-012**: System MUST be operable on a phone-sized viewport (≥360 px
  wide), consistent with the project's Web App Standards in the
  constitution.
- **FR-013**: System MUST NOT expose vehicle identifiers (VIN) or any
  personally identifiable data in URLs, client-side logs, or analytics
  events.
- **FR-014**: All operator-visible text — diagnostic item names, category
  labels, status descriptions, recommended next actions, error messages,
  and picker labels — MUST be presented in English in v1. No language
  toggle or region-driven language switching is required for v1.
- **FR-015**: The picker MUST read host data from a local copy of the
  inventory maintained on the operator's machine (or local app instance).
  The running app MUST NOT require live access to the central
  `ree-vehicle-configs` repository to render the wizard or run a check.
- **FR-016**: System MUST refresh the local inventory copy from the
  canonical source on a periodic schedule. The cadence is an
  implementation decision for planning, but MUST be at least once per
  application start.
- **FR-017**: System MUST expose an explicit "Update inventory"
  affordance that the operator can use to force a refresh on demand,
  independent of the periodic schedule.
- **FR-018**: The picker MUST display the timestamp of the most recent
  successful inventory refresh, so the operator can tell how fresh the
  host list is.
- **FR-019**: When the local inventory copy is missing or empty (for
  example, first-time use that has never synced, or a refresh that
  yielded zero in-scope hosts), the picker MUST present a single
  blocking message inviting the operator to run an inventory update
  rather than showing an empty wizard or fabricating content.
- **FR-020**: System MUST present two operator-visible modes — an
  **Operator** mode (default) and a **Developer** mode. The two modes
  MUST share the same routes and the same underlying diagnostic data;
  they differ only in which UI affordances are rendered.
- **FR-021**: System MUST expose a **Developer mode toggle** in the app
  header, accessible from every screen. The default state on initial
  load MUST be Operator mode. The active mode MUST be visibly
  indicated. Toggling MUST NOT trigger a re-run, MUST NOT mutate or
  refresh result data, and MUST be reversible without data loss.
- **FR-022**: When **Developer** mode is active, each Diagnostic Item on
  the result view MUST expose an expand control that reveals the raw
  underlying detail captured for that item (e.g., CAN trace excerpt,
  exit code, device path, parser error message, raw stderr line). When
  **Operator** mode is active, this expand control MUST NOT be present
  and raw underlying detail MUST NOT be visible anywhere in the UI.
- **FR-023**: All Operator-mode requirements (FR-003, FR-004, FR-005,
  FR-010) continue to apply unchanged regardless of whether the
  Developer toggle is currently on or off — Developer mode is purely
  additive and never replaces or rewrites the plain-language primary
  view.
- **FR-024**: Once a diagnostic run has been started, the operator MUST
  wait for it to complete, time out, or fail. v1 MUST NOT expose a
  cancel control and MUST NOT support a background-run pattern (the
  operator cannot navigate away mid-run and reattach to the result
  later). The only operator-controllable interaction during an
  in-progress run is observing the progress feedback required by
  FR-009.

### Key Entities *(include if feature involves data)*

- **Remote Host**: The machine being diagnosed. Has an operator-visible
  identifier (a friendly name), a hidden technical address, a host
  **type** (Vehicle or Telestation), a **country** (Germany or United
  States in v1), and — for telestations only — a **city** derived from
  the file-name segment (e.g., Berlin, Las Vegas, Lincoln, Nuq). Belongs
  to a host class that determines which checks apply. Sourced from
  `ree-vehicle-configs`.
- **Diagnostic Run**: One execution of a check against one host. Has a
  start timestamp, an end timestamp, an overall outcome (complete / partial
  / unreachable), and an ordered list of Diagnostic Items.
- **Diagnostic Item**: A single thing that was checked, for example "main
  CAN bus reachable", "expected USB camera connected", "autonomy config
  valid". Has a plain-language name, a category label visible to the
  operator, a status (working / error), a short description, and — when in
  error — a recommended next action. May also carry **raw underlying
  detail** (CAN trace excerpt, exit code, device path, parser message)
  that is rendered only in Developer mode and never in Operator mode.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator who has never seen the app before can run a
  diagnostic check on a known host and arrive at a correct answer to "is
  this host ready?" in under 60 seconds.
- **SC-002**: 100% of items shown in the "Needs attention" group on the
  primary view include a recommended next action written in plain
  language.
- **SC-003**: A sample audit of the primary view across at least 10 distinct
  error scenarios shows zero raw stack traces, zero numeric error codes,
  and zero developer-internal terms (CAN, USB, errno, etc.) presented
  without a plain-language equivalent.
- **SC-004**: An operator using a phone-sized screen (≥360 px wide) can
  identify whether a host has any errors within 5 seconds of the result
  appearing, without scrolling.
- **SC-005**: When the chosen host is unreachable, the operator sees a
  single clear message stating that fact; they do not see a list of
  individual fabricated item errors.
- **SC-006**: A typical successful run completes and renders results within
  10 seconds on a healthy reachable host on a normal network.
- **SC-007**: For any successful run, 100% of the items the diagnostic
  covers for that host's class appear by name in the result view; an
  operator looking at the screen can read out at least three specific
  items that were inspected without consulting external documentation.
- **SC-008**: Given the friendly identifier of a target host (and, for a
  telestation, its city), an operator can complete the picker wizard
  (Country → Type → optional City → Host) in under 10 seconds.

## Assumptions

- The remote host in scope is a Vay-managed onboard computer or comparable
  dev/test machine. The mention of CAN bus, USB devices, and configuration
  files in the request matches that profile, so the spec is written for
  that case rather than for arbitrary internet hosts.
- Operators are Vay employees accessing the tool on internal
  infrastructure. Authentication and authorization are assumed to be
  handled by existing internal SSO and are out of scope for this
  feature spec.
- The set of diagnostic items checked on a host is fixed per host class in
  v1. There is no user-configurable check list, no plugin model, and no
  per-run check selection.
- The host inventory is read from the existing `ree-vehicle-configs`
  repository (`org/{org}/{vehicles,telestations}/*.yaml`) via a local
  cached copy on the operator's machine, refreshed periodically and on
  demand. The exact sync mechanism (git pull, rsync, packaged tarball,
  etc.) and refresh cadence are implementation decisions for planning.
- Belgium-region hosts (`ve-be-*`, `ts-be-*`) exist in the inventory but
  are out of scope for the v1 picker. Adding a third region grouping is a
  later follow-up, not a v1 requirement.
- "Telestation" and "Vehicle" are treated as distinct host classes; the
  diagnostic check sets for each class may differ. Defining those check
  sets is part of planning, not this spec.
- Only the most recent run per host is retained and displayed. There is no
  historical view, no comparison across runs, and no export in v1.
- One operator runs one check at a time per host. No alerting, no
  background polling, no email/push notifications.
- v1 ships with two operator-visible modes: an **Operator** mode (the
  primary view as designed for non-technical users) and a **Developer**
  mode (per-item raw output expansion for the people building and
  maintaining the diagnostic app itself). Modes are switched by a manual
  toggle in the app header; the default is Operator. There is no
  separate "guides" / docs surface inside the app in v1 — developer
  documentation lives outside the app (project README / docs) until a
  later iteration explicitly adds it.
- The exact mechanism by which the web app reaches the remote host (agent,
  SSH, pre-installed daemon, etc.) is an implementation detail to be
  decided during planning, not in this spec.
- The combined v1 inventory (vehicles + telestations across DE+US) is
  small enough — on the order of dozens to ~100 hosts — that no in-app
  search/type-ahead is needed inside any wizard step. If the inventory
  grows substantially (several hundred hosts in one step), search becomes
  a follow-up requirement.
- The UI ships in English only for v1. German (or any other) localization
  is a deferred follow-up; v1 work does not need to be designed for a
  later locale switch beyond keeping operator-visible strings extractable.
