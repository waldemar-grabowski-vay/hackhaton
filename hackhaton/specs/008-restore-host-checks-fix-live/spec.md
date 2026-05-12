# Feature Specification: Restore host check battery, fix Live Diagnostic regression, keep version pull surface

**Feature Branch**: `008-restore-host-checks-fix-live`
**Created**: 2026-05-11
**Status**: Draft
**Input**: User description: "Big regres, the Live Diagnostic is not working at all. The checks on host are showing only the versions, where all other checks gone?"

## Clarifications

### Session 2026-05-11

- Q: Should the host-detail page get its data from one engine call (shared between version card and check battery) or two parallel calls? → A: Split by data source, not by surface. REECU-derived information (vREECU firmware, SEC version, ERRQ state, any signal already streamable from REECU's CAN bus) MUST come from the Live Diagnostic surface — which already opens a live SSH + candump + DBC-decode session per host. Everything else (vDrive `dpkg-query`, Peplink HTTP probes, network reachability, camera USB enumeration, WAKE line voltage, vehicle / telestation configuration validity) stays in `ree-debug-cli`. If any non-REECU check turns out to be easier to do in Python on the backend than in the Rust engine, the Python rewrite is an acceptable alternative — the engine is the default, Python is the fallback when easier. The host-detail page composes both data streams into one rendered surface; the two sources are independent and may complete at different times.
- Q: What specifically does "Live Diagnostic not working at all" mean — entry-point invisible, page-mount blank, or Connect failing? → A: Defer concrete failure-mode diagnosis to plan-time spike. US2's success criterion is the same end state 004 originally delivered (entry point reachable when Developer mode is on, page mounts with connection dialog + inventory list, Connect against a reachable TS host produces decoded CAN signals within 10 s, errq + DBC degraded states surface plain-language messages per 004 FR-012). The `/speckit-plan` step runs a reproduction spike against the .deb-installed runtime to enumerate concrete failure modes (errq path, DBC selection, strings.ts dangling refs, .deb binary shadowing) and scopes the fix from there. The spec does not prescribe which subset of those is the actual cause.
- Q: How should the deleted check battery be restored — `git checkout` from HEAD, re-implement from spec records, or a hybrid? → A: `git checkout` HEAD. The pre-007 working tree at commit `01d3979` already contains the correct, working code for every deleted file (`backend/src/vayobd/checks/*`, `backend/src/vayobd/api/runs.py`, all the deleted `frontend/src/components/result/*` and `states/*` components, `RunResultPage`, the deleted tests, etc.). Mechanical restore via `git checkout HEAD -- <path>` per file. The `strings.ts` file is the exception — it needs a hand-merge to keep 007's new `hostVersions` block while re-introducing the `runs / outcomes / result / category / guide / item` blocks that 007 stripped. Restoration is implementation work for `/speckit-plan` / `/speckit-tasks`; this clarification just locks in the mechanism.
- Q: How does the host-detail page consume the REECU pipeline (one-shot session, piggyback, long-lived background, or embedded streaming)? → A: One-shot capture per page mount. The host-detail backend opens a Live-Diagnostic-equivalent SSH + candump session for the requested host, captures roughly 3–5 seconds of frames (enough to catch the periodic ERRQ_Byte01..64 cycle and the version-bearing signals), decodes via the TS DBC, extracts the REECU fields, then closes the session. The 60-second TTL cache from 007 amortises repeated visits — a re-mount within the TTL serves the cached REECU + non-REECU response without re-spawning either pipeline. The capture is invisible to the operator; the page renders a loading state (em-dash + spinner, 007's pattern) while it's in flight. If the operator already has a `/live` session open against the same host in another tab, the host-detail capture is an independent SSH spawn — same coexistence pattern 004 already supports.
- Q: Scope of the restored check battery — every pre-007 check, a defined core subset, or scope-at-plan-time? → A: Restore every non-REECU check from the pre-007 catalog: vDrive package drift, Peplink cellular + VPN, network reachability, camera / USB enumeration, WAKE line, vehicle / telestation configuration validity, harness / telestation diagrams, repair guides registered for each failing check. Same coverage the deleted `catalog.py` provided. Pruning to a smaller set, if any check turns out to be dead weight in practice, is a follow-up — not part of 008.

### Session 2026-05-12

- Q: Where do the VE-side errq CSVs come from at runtime? → A: The **same `ree-reecu` clone** the .deb already uses for TS errq, under a VE-specific subpath. The .deb packaging from 006 is unchanged — no new bundle, no second repo. `errq_bridge` (Wilhelm's) gains an additional resolver for the VE subpath (concrete path is a `/speckit-plan` lookup inside the existing clone). If the clone is incomplete or the VE subpath is missing, the panel falls back to the 004 FR-012 degraded-mode message ("errq data unavailable for this host") — same fallback as for missing TS CSVs. This decision keeps spec 008 strictly inside the SPA + backend; it does NOT touch 006's `.deb` packaging surface.
- Q: Should the `/live` inventory / host-picker dialog visually distinguish TS vs VE hosts? → A: Yes — show a small **TS / VE pill** next to each host id. Each row in the inventory list / host-picker dialog renders the host id PLUS a small typed pill (`TS` for telestation, `VE` for vehicle). The pill source is `host.type` (already populated by the inventory loader via the `ve-*` / `ts-*` id prefix). Render-only change; no backend work. Same visual vocabulary the SPA already uses for typed badges elsewhere — slate background for TS, distinct accent for VE (palette pick deferred to `/speckit-plan`, but it MUST follow the 002 sun-theme tokens, not a new colour). Sets operator expectations for what state signals they'll see before they click Connect.
- Q: Should the 008 quickstart acceptance walkthrough explicitly test against BOTH a TS host AND a VE host? → A: Yes — add a VE-host walkthrough step. The quickstart in `specs/008-restore-host-checks-fix-live/quickstart.md` MUST gain a paired step (or sub-step) that runs the same Live Diagnostic + host-detail flow against a reachable VE host. The VE step verifies: (a) the inventory list includes the VE host as selectable; (b) Connect against the VE host streams decoded CAN signals within ten seconds, with the VE-channel state signals (`VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`, `VE_PRND_STATE`) visible in the state panel; (c) the errq panel either shows decoded VE-side errors (when the VE-specific errq CSV source is present) or the plain-language degraded-mode message (when it's not); (d) the host-detail page for the same VE host renders the version card with whatever fields apply for vehicles (the engine's `parse_engine_report(host_type="vehicle", …)` path already produces this) AND the categorised check battery from `catalog_for("vehicle")`. The TS step is unchanged; the VE step is additive. Without this, the developer running the quickstart only exercises TS and risks shipping VE regressions.
- Q: How should the Live Diagnostic errq panel behave when the connected host is a VE (vehicle), given Wilhelm's errq CSVs are TS-specific? → A: Show TS-style errq panel using **VE-specific CSVs**. The Live Diagnostic backend MUST resolve a VE-specific errq CSV path (alongside the existing TS one) when the connected host is a vehicle, and feed those CSVs into the **same** `errq_bridge` / decode pipeline Wilhelm's tool already uses for TS. The errq panel renders identically regardless of host type — only the underlying CSV source switches. The concrete VE errq CSV path inside `ree-reecu` (or wherever the team stages it) is a `/speckit-plan` lookup; the spec records the rule, not the path. If the VE CSV source is missing at runtime, the panel falls back to the 004 FR-012 degraded-mode message ("errq data unavailable for this host") — never a silent empty panel and never fabricated data.
- Q: What scope of Wilhelm's `TS_DIAG_TOOL_V1.9` desktop work should 008 port into the hackhaton web app? → A: Port the VE state signals onto `/live`. The desktop tool's `TS_STATE_SIGNALS` list (despite the name) already includes VE-channel signals — `VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`, `VE_PRND_STATE`, plus any other `VE_*` entries Wilhelm's `TS_diagnostic_tool/config.py` carries. The web app's Live Diagnostic state panel MUST surface those VE-channel signals alongside the TS-channel ones it already shows, using the same DBC-decode code path, same plain-language degraded-mode wording, same loading affordance. The REECU pipeline that the host-detail page consumes (FR-002 / FR-010) MUST ALSO pick up VE signals when the connected host is a vehicle (VE), not just a telestation (TS). Minimal new code: it's a signal-list and host-type pass-through, not a new transport. Out of scope for this Q (deferred): per-channel `errq_aggregator.py`, multi-bus auto-detect across every UP `can*` interface, severity grouping into `IMMEDIATE_PULLOVER / SAFETY / TS_BRAKES / TS_STEERING / ERROR_GROUP / TS_THROTTLE`. Those become follow-up spec material.
- Q: What happens to Ezequiel's `specs/005-ve-harness-repair-guide/` directory (spec.md + `checklists/requirements.md`) during the integration into 008? → A: Pull it into the repo, but rename to the next free slot: **`specs/009-ve-harness-repair-guide/`**. The directory `specs/005-ve-harness-repair-guide/` on Ezequiel's branch is copied verbatim — `spec.md` + `checklists/requirements.md` — into `specs/009-ve-harness-repair-guide/`. The rename avoids colliding with the local `specs/005-ui-readability-pass/`. Inside the renamed `spec.md`, the `**Feature Branch**: ` field is updated to `009-ve-harness-repair-guide` for self-consistency; any inline references to "005" that mean "this feature" are repointed to "009". The 009 spec stays as the rationale doc for why the harness/guide frontend looks the way it does — but the CODE lands as part of 008's implementation, not under a separate 009 branch. The expected reading order for future contributors is: "008 spec describes the integration mechanics; 009 spec describes the design intent of the harness/guide UI 008 absorbed."
- Q: For the OTHER pre-007 deletions (the result / states components, `RunResultPage`, `api/runs.ts`, `api/runs.py`, `backend/src/vayobd/checks/*`, `engine/ree-debug-engine/src/checks/*`), where do they restore from? → A: Split by tier. Ezequiel's branch is primarily a **frontend** contribution; its backend and engine code is **stale** (from before recent pushes) and would silently regress 006/007 work. Restoration rule:
  - **Frontend pre-007 deletions** (`frontend/src/components/result/CategoryBadge.tsx`, `ResultGroup.tsx`, `ResultHero.tsx`, `DiagnosticItemRow.tsx`, `RunResultPage`, the `frontend/src/components/states/{Running,Partial,Unreachable,EmptyInventory}State.tsx`, `frontend/src/api/runs.ts`) → restore from `origin/005-ve-harness-repair-guide`, one consistent frontend source alongside the harness/guide cherry-pick.
  - **Backend pre-007 deletions** (`backend/src/vayobd/checks/{__init__,catalog,executor,peplink,ree_cli,runner}.py`, `backend/src/vayobd/api/runs.py`) → restore from the local pre-007 commit `01d3979`. Do NOT pull from Ezequiel's branch; his snapshot precedes recent backend pushes.
  - **Engine pre-007 deletions** (`engine/ree-debug-engine/src/checks/{cameras,connectivity,decode,mod,reecu,usb}.rs`) → restore from `01d3979` for the same reason; the Rust engine has moved forward since Ezequiel's fork.
- Q: How should the new top-level Repair Guides library surface (Ezequiel's `RepairGuidesPage` + `RepairGuideLibraryDialog` + `guideLibrary.ts` + `App.tsx` route) be scoped in 008? → A: Add as **User Story 5** (P3, discoverable library). The cherry-pick pulls the three new files in; the `App.tsx` route delta from Ezequiel's branch lands; a chrome entry point (header link OR a secondary main-page affordance — `/speckit-plan` picks which) makes the library reachable without going through a failing host check first. The same `RepairGuideSheet` component renders guides whether opened from the library or from the host-detail check battery — one component, two entry points, no divergent code path. The library is NOT Developer-mode-gated; harness and repair knowledge is operator-facing, not developer-facing.
- Q: When cherry-picking from Ezequiel's branch touches a file that 007 also modified (notably `strings.ts`, `connectorLocations.ts`, possibly `guides.ts`), what's the merge precedence? → A: 007 wins, Ezequiel's additions layer on top. The post-007 HEAD file is the merge base. Ezequiel's NEW keys / entries / blocks are layered on top (his +107 strings, +863 `connectorSpecs.ts` entries, +763 `guides.ts` entries, his `connectorLocations.ts` additions). Where the same key / id exists in both, 007's value wins — this preserves the FR-008 / FR-009 commitments. Implementation note: the `strings.ts` hand-merge that `research.md` already calls out for the 2-way (pre-007 HEAD ↔ post-007 HEAD) case now becomes a 3-way hand-merge with Ezequiel's branch as the third input, same precedence rule applied (007 wins on collision; otherwise the union of all three sources). Drives implementation choice toward `git checkout origin/005-ve-harness-repair-guide -- <path>` followed by a hand-reconciliation pass that re-introduces the 007 keys, rather than a clean `git cherry-pick`.
- Q: Where should the integration of Ezequiel's `origin/005-ve-harness-repair-guide` work live relative to spec 008? → A: Cherry-pick UI deltas into 008. 008 still owns "restore checks + fix Live Diagnostic". From `origin/005-ve-harness-repair-guide` we cherry-pick ONLY the frontend deltas: the improved `HarnessDiagram.tsx`, `RepairGuideSheet.tsx`, `TelestationDiagram.tsx`; the new `RepairGuideLibraryDialog.tsx`, `RepairGuidesPage.tsx`, `guideLibrary.ts`; the four new harness assets (`ve-pigtail-f61-harness.jpg`, `ve-reebox-power-cable-harness.jpg`, `ve-vs040815-harness-p1.png`, `ve-vs040815-harness.pdf`); and the additive blocks in `connectorSpecs.ts` (+863), `guides.ts` (+763), `connectorLocations.ts`, and `strings.ts` (+107). This SUPERSEDES the 2026-05-11 "restore from `git checkout HEAD --`" answer for the harness / repair-guide UI surface specifically — those files are now sourced from Ezequiel's branch, not HEAD. The other deleted files split by tier (per the same-session clarification below): frontend pre-007 deletions (the remaining result components like `CategoryBadge`, `ResultGroup`, `ResultHero`, `DiagnosticItemRow`, the `states/*` components, `RunResultPage`, `api/runs.ts`) also come from Ezequiel's branch for source consistency; backend pre-007 deletions (`backend/src/vayobd/checks/*`, `backend/src/vayobd/api/runs.py`) and engine Rust deletions (`engine/ree-debug-engine/src/checks/*`) restore from the local pre-007 commit `01d3979` because his branch's backend/engine snapshot is stale. Ezequiel's BACKEND deletions (`api/host_versions.py`, `_internal/version_cache.py`, `api/refresh.py`, `install/*`) are explicitly NOT honoured — those files stay because FR-008 / FR-009 / FR-015 commit to keeping 007's version-pull surface intact. Wilhelm's `TS_DIAG_TOOL_V1.9` is already an ancestor of the current branch (PR #1, commit `b3e79ff`) — no integration action required.

## User Scenarios & Testing *(mandatory)*

007 (the version-pull tweak round) over-removed. In US3 of 007 the
backend's full check battery (`vayobd.checks.*` — Peplink, REECU API,
ree_cli probes, network reachability, camera/USB enumeration, WAKE
line presence, etc.) and the entire result-rendering surface
(`/api/runs`, `RunResultPage`, `CategoryBadge`, `ResultGroup`,
`ResultHero`, `DiagnosticItemRow`, `RepairGuideSheet`,
`HarnessDiagram`, `TelestationDiagram`, `RunningState`,
`PartialRunState`, `UnreachableState`) were deleted on the
assumption that the version-only host-detail page was the post-pivot
diagnostic surface. The user has now confirmed that assumption was
wrong: those checks are the value, and the version display alone is
not a substitute. Separately, 007 also left the Live Diagnostic
surface (`/live` — the TS_diag port from 004) in a non-working state
the user has reported as "not working at all."

This feature is a regression-recovery round. It restores the host
check battery — Peplink, REECU, network, harness, repair-guide
surfaces — alongside the version-pull display that 007 added, and
diagnoses + fixes whatever broke Live Diagnostic during the 007
work. The end state: the host-detail page shows BOTH the live
versions AND the categorised check results; the Live Diagnostic
page works end-to-end; nothing 007 added (per-field verdict pills,
TTL cache, refresh button, dual TS_diag entry points) is lost.

### User Story 1 - Restore the host check battery on the host-detail page (Priority: P1)

A Vay engineer picks a host through the wizard and lands on the
host-detail page. Today they see only three version cells (vDrive,
vREECU, SEC). Before 007 they saw a categorised result page —
Peplink cellular reachable / not, REECU API responding, network
addresses reachable, camera USB enumeration, WAKE line active,
harness diagram with connector chips, repair-guide sheets — split
into "Working" and "Needs attention" groups. They want those checks
back. The page should show the versions AND the full check battery,
not versions instead of checks.

**Why this priority**: This is the regression the user explicitly
reported and the highest-impact loss from 007. Without these checks
the host-detail page does not deliver the diagnostic value the team
relied on. Restoring them is the irreducible MVP for this round.

**Independent Test**: Pick a reachable TS host. The detail page
must render — within ten seconds of mount — a full check result set:
versions (vDrive / vREECU / SEC) AND a categorised list of pass /
warn / fail items covering Peplink, REECU, network, hardware,
configuration and (where applicable) calibration. Each failed item
must offer a recovery action and, where one is registered, a
repair-guide sheet.

**Acceptance Scenarios**:

1. **Given** the operator opens a host-detail page for a reachable
   testbed, **When** the page resolves, **Then** every check that
   ran in the pre-007 result page renders again, grouped by
   category, with the operator-facing labels and recovery actions
   that existed before 007.
2. **Given** the operator opens a host-detail page where one or
   more checks fail, **When** the page renders, **Then** the failed
   items appear under "Needs attention" with the same red /
   amber tone the pre-007 design used, and a repair-guide button
   opens the relevant sheet (harness diagram, telestation diagram,
   WAKE signal-path, etc.).
3. **Given** the operator opens a host-detail page for a host that
   is unreachable, **When** the engine reports the host down,
   **Then** the page shows the dedicated unreachable state (not a
   bare error) with a clear recovery suggestion (matches 004 / 005
   plain-language policy).
4. **Given** the operator opens a host-detail page for a host the
   engine partially reports on, **When** some checks complete and
   others time out, **Then** the page renders the partial-result
   state — completed items are shown, missing ones are flagged as
   "didn't return" with a Retry action (matches the pre-007
   partial-run handling).
5. **Given** the version-pull data 007 introduced is available,
   **When** the page renders, **Then** the three version cells
   (vDrive / vREECU / SEC) are visible alongside the check
   battery, NOT as a replacement for it — same verdict pills,
   refresh affordance, and TTL caching 007 added remain intact.

---

### User Story 2 - Fix Live Diagnostic so it actually works (Priority: P1)

A developer toggles Developer mode, clicks "Live diagnostic"
(either header or main-page copy), and lands on `/live`. Today the
surface is broken: the user reports "not working at all." Reproducing
locally shows the backend starting in a degraded state
(`live_errq_degraded`, `live_dbc_ready messages=0 source=Env.dbc`)
because the .deb-installed runtime is pointing the live page at the
wrong errq / DBC sources, and the page itself may be hitting a
crash, blank render, or missing-string regression introduced when
007 scrubbed `strings.ts`.

This story diagnoses the actual root cause(s) on the
.deb-installed runtime and fixes Live Diagnostic so the surface
ships in the same working state 004 originally delivered: an
operator can open the page, pick a host from the inventory, click
Connect, and see decoded CAN signals streaming in within ten
seconds.

**Why this priority**: Live Diagnostic is the primary deep-inspection
surface 004 shipped. Letting it stay broken makes 008 a half-finished
recovery. P1 because the user explicitly flagged it; not gated on
US1 because the two surfaces are independent.

**Independent Test**: With Developer mode on (UI switch toggled,
backend `developer_mode` left at default if needed), click the
"Live diagnostic" entry point. Within ten seconds of clicking
Connect against a reachable host — **TS or VE** — decoded CAN
signals appear in the state panel. For a VE host the panel
includes `VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`,
`VE_PRND_STATE`, and any other `VE_*` signal Wilhelm's
`TS_diagnostic_tool/config.py` already lists. The errq panel
either shows active errors OR shows a clear degraded-mode
message (per 004 FR-012) — never a silent blank surface, never
an unhandled exception in the dev console, never a 404 / 5xx
in the network tab.

**Acceptance Scenarios**:

1. **Given** the operator launches Live Diagnostic from either
   entry point, **When** the `/live` route mounts, **Then** the
   page renders its connection dialog and the inventory list
   populates within five seconds — no blank page, no console
   error, no 4xx/5xx on any request.
2. **Given** the operator picks a host (TS or VE) and clicks
   Connect, **When** the backend invokes ssh, **Then** decoded
   CAN signals begin updating in the state panel within ten
   seconds OR a plain-language connection error is surfaced
   with a Retry action (matches 004 FR-006 / 005 FR-001).
3. **Given** the connected host is a VE, **When** the state
   panel populates, **Then** the VE-channel state signals
   (`VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`, `VE_PRND_STATE`,
   and any other `VE_*` entry in Wilhelm's `TS_STATE_SIGNALS`)
   appear alongside the TS-channel ones, decoded through the
   same DBC and rendered through the same state-panel
   component — no separate VE-only surface.
4. **Given** the local `ree-reecu` clone is incomplete (the
   `live_errq_degraded` warning the user is currently seeing),
   **When** the page mounts, **Then** the errq panel shows the
   degraded-mode message from 004 FR-012 — the rest of the
   surface remains functional (decoded signals + raw frames).
5. **Given** Developer mode is off, **When** the operator navigates
   directly to `/live`, **Then** the gate from 004 FR-002 still
   redirects them to the main page (007's UI-toggle change
   preserves this — verify it survived).
6. **Given** any string the Live Diagnostic surface tries to
   render through `strings.ts`, **When** the page renders,
   **Then** no string lookup returns the literal path key
   (a string regression from 007's scrub would surface as
   `wizard.runButton` or similar literal text on the page).

---

### User Story 3 - Unified host-detail layout: versions and checks side by side (Priority: P2)

The two surfaces — the live version card 007 added and the
pre-007 categorised check result — now live together on the host
detail page. They have to compose into one coherent layout, not
look like two pages glued together. Operators need to read the
page top-down: "what version is on this host" first (the new 007
panel), then "what's wrong with this host right now" (the check
battery), then "how do I fix it" (the repair-guide sheets the
failed items link to).

**Why this priority**: P2 because US1 and US2 alone restore the
functional behaviour the user lost. This story is about the
combined visual story being coherent. Without it, the page reads
as two surfaces in one URL.

**Independent Test**: Open a host-detail page where vDrive shows
drift and one check (e.g. Peplink VPN) is failing. The operator
must be able to tell at a glance (under three seconds of looking
at the page) that there are two distinct attention items, see
both without scrolling, and click through to the repair guide for
the failed check without losing sight of the version drift
indicator above it.

**Acceptance Scenarios**:

1. **Given** the host-detail page renders, **When** the operator
   scans it top-down, **Then** the version card (vDrive / vREECU /
   SEC, with verdict pills + source pill + refresh button from
   007) sits at the top, the categorised check results sit below
   it, and the page has a clear visual separation between the
   two sections.
2. **Given** the host-detail page is opened on a phone-sized
   viewport (≥360 px wide), **When** the page renders, **Then**
   both sections stack cleanly without horizontal scrolling
   (matches Constitution Web App Standards).
3. **Given** a check has a registered repair guide, **When** the
   operator clicks the guide button, **Then** the guide sheet
   opens over the page (not as a route change) so the version
   context remains visible to the operator.
4. **Given** a check is still running, **When** the page renders,
   **Then** the version card has already populated (versions
   resolve on a different code path than the check battery) and
   the operator does not have to wait for the slowest check to
   see version drift.

---

### User Story 4 - No regressions to 007's wins (Priority: P2)

The 007 work added: per-field verdict pills, 60-second TTL cache
for host versions, a refresh affordance, per-cell timestamps,
dual TS_diag entry points (header + main page), Developer-mode
toggle driven from the UI, and the removal of every "Run check"
copy string. None of those should regress when US1 puts the
check battery back. The check battery returns; the version-pull
surface stays; the UI hygiene improvements stay.

**Why this priority**: P2 because the worst-case alternative
(restore the pre-007 layout verbatim and lose 007's improvements)
is functional but a step backwards from the latest design. This
story keeps the 007 win surface intact while the regression is
undone.

**Independent Test**: After 008 lands, run the 007 quickstart
acceptance walkthrough (`specs/007-…/quickstart.md`) end-to-end.
Every 007 scenario must still pass: refresh button, TTL cache,
em-dash + spinner during in-flight, dual entry-point visibility,
plain-language error states, no "Run check" wording.

**Acceptance Scenarios**:

1. **Given** the host-detail page renders, **When** the operator
   clicks the refresh button on the version card, **Then** the
   versions re-pull with `?fresh=true` semantics (the 007
   behaviour) AND the check battery either re-runs alongside OR
   keeps its prior result — never silently disappears.
2. **Given** Developer mode is toggled in the UI, **When** the
   operator looks at the main page, **Then** both TS_diag entry
   points (header + main-page primary action) appear / disappear
   together exactly as 007 specified.
3. **Given** the operator reads any user-facing string on any
   surface, **When** they scan the page, **Then** no "Run check" /
   "Run diagnostic" wording reappears (this means the restored
   check battery uses the same plain-language framing 005 / 007
   established — "open the host" instead of "run a check
   against the host").
4. **Given** the host-detail page sources a check from the engine
   that has the same kind of name-match payload 007's
   `parse_engine_report` parses (`vDrive package vs manifest`,
   `Aurix firmware`, `SEC version`), **When** the page renders,
   **Then** those rows are routed to the 007 version card —
   not duplicated in the check battery section — so the
   operator sees each piece of information once.

---

### User Story 5 - Browse the repair guide library independent of host (Priority: P3)

The repair guide catalogue (harness diagrams, connector chips,
step-by-step procedures) today is only reachable from a failing
check on a host-detail page via `RepairGuideSheet`. An operator
preparing for a field visit, or a new engineer trying to learn
the harness layout, has no surface to browse the catalogue
ahead of time. This story adds a top-level "Repair guides"
surface — the `RepairGuidesPage` and `RepairGuideLibraryDialog`
cherry-picked from Ezequiel's branch — so operators can open
the catalogue from the app chrome without needing a failing
host check first.

**Why this priority**: P3 because US1–US4 already deliver the
regression-recovery the user explicitly requested. The library
is additive value. Without it Ezequiel's catalogue improvements
(+863 `connectorSpecs.ts`, +763 `guides.ts`, four new harness
assets) are reachable only via the host-detail sheet — usable,
but suboptimal.

**Independent Test**: From any page, click the "Repair guides"
chrome entry point. The library opens, lists every registered
guide, and each entry opens the same `RepairGuideSheet` the
host-detail surface uses — identical component, identical
data, no divergent code path.

**Acceptance Scenarios**:

1. **Given** an operator is on any page in the SPA,
   **When** they click the "Repair guides" chrome entry point,
   **Then** `RepairGuidesPage` mounts and lists every guide
   registered in `guideLibrary.ts`, grouped sensibly
   (harness / host type — `/speckit-plan` picks the grouping
   key).
2. **Given** the library page is open, **When** the operator
   clicks a guide entry, **Then** the `RepairGuideSheet`
   opens with the harness diagram + step list — same component
   instance and same props shape as when opened from a failing
   host-detail check.
3. **Given** the operator opens the same guide both from the
   library AND from a failing host-detail check, **When** they
   compare the two sheets, **Then** the rendering is identical
   (same connector chips, same step copy, same harness tab
   default) — no divergent code path, no duplicated guide
   definition.
4. **Given** Developer mode is **off**, **When** the operator
   looks at the chrome, **Then** the "Repair guides" entry
   point is visible. The library is operator-facing knowledge,
   not a developer surface — no gating.

---

### Edge Cases

- **Engine binary present but no inventory**: 007's deletion of the
  legacy executor wiring may have left the broader run flow
  without an inventory-resolution path. The restored battery
  must reuse the same inventory loader the existing inventory
  endpoint uses — not introduce a separate one.
- **Strings.ts scrub left a dangling reference**: 007 dropped
  `runs`, `outcomes`, `result`, `category`, `guide`, `item`,
  `categoryLabel()` — if Live Diagnostic or any other surviving
  surface still references those at runtime, the page renders
  literal path keys ("`runs.runButton`") instead of human copy.
  All such references must be repointed at the new copy or
  re-introduced into `strings.ts`.
- **Result components were deleted**: the React components that
  rendered the result page (`CategoryBadge`, `ResultGroup`,
  `ResultHero`, `DiagnosticItemRow`, `RepairGuideSheet`,
  `HarnessDiagram`, `TelestationDiagram`, `RunningState`,
  `PartialRunState`, `UnreachableState`, `StaggeredList`) are
  gone from the working tree. Either restore them from git
  history (`git show HEAD~N:path`) or re-implement them — they
  must come back functionally, including the connector chip
  routing and repair-guide registry.
- **REECU pipeline shares SSH with Live Diagnostic**: per the
  2026-05-11 clarification, REECU-derived values come from the
  same code path Live Diagnostic uses (candump → cantools
  decode). Two backend code paths consuming live REECU data
  must coordinate so opening the host-detail page does not
  fight a Live Diagnostic session the operator already opened
  in another tab (or vice versa). The shared concern is the
  testbed's per-host concurrent-SSH limit and the candump
  subprocess on the testbed; the page's behaviour when a
  session is already in flight is a `/speckit-plan` decision.
- **Live Diagnostic loads with degraded errq / DBC**: 007 didn't
  touch the live page's errq / DBC sourcing. The user sees
  `live_dbc_ready messages=0 source=Env.dbc` which suggests the
  DBC resolver is picking up the wrong file (Env.dbc is a
  legacy file with zero TS_… messages). The page must pick the
  TS application DBC or surface a clear degraded message.
- **.deb-installed runtime points at source-tree paths**: the
  user's 0.0.6 launch showed
  `engine_ready binary=/home/.../engine/target/release/ree-debug-cli`
  even though `/usr/lib/vayobd/bin/ree-debug-cli` exists from
  the .deb — meaning the runtime resolver is finding the
  source-tree binary first (probably via PATH). The launcher
  must prefer the .deb-installed binary when both are present.
- **Ezequiel's branch is forked from a pre-007 base**:
  `origin/005-ve-harness-repair-guide` deletes
  `backend/src/vayobd/api/host_versions.py`,
  `backend/src/vayobd/_internal/version_cache.py`,
  `backend/src/vayobd/api/refresh.py`, and the entire
  `backend/src/vayobd/install/` workflow, and modifies
  `backend/src/vayobd/{app,models,config,settings_file}.py`
  + `live/*` + `models.py` + `tests/conftest.py` against a
  pre-007 base. The integration is a **frontend-only**
  cherry-pick — those backend deletions and modifications
  are NOT carried over. The cherry-pick scripts / git
  commands used during implementation MUST limit their path
  scope to `frontend/**` (plus the assets under
  `frontend/public/`) so 007's backend surface cannot
  regress through this integration path. Backend and engine
  pre-007 restorations come from local commit `01d3979`,
  NOT from Ezequiel's branch, because his backend/engine
  snapshot predates the recent pushes the project depends on.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The host-detail page MUST render the **full** set of
  host checks that existed before 007 — vDrive package drift,
  Peplink (cellular + VPN), network reachability, camera /
  input-device USB enumeration, WAKE line presence, vehicle /
  telestation configuration validity, harness / telestation
  diagrams. REECU-derived items (vREECU firmware, SEC version,
  ERRQ-decoded errors) come from the Live Diagnostic pipeline
  (FR-002) rather than the legacy `vayobd.checks` package, but
  are rendered into the same categorised result surface. Checks
  MUST be grouped by category exactly as before 007 (Working /
  Needs attention groups, the same colour / iconography
  vocabulary 005's UI readability pass landed on).
- **FR-002**: The backend MUST re-expose a route the host-detail
  page consumes to fetch the full per-host check result. The
  route's response carries data sourced from TWO independent
  pipelines:
  1. **REECU pipeline** — REECU firmware, SEC version, ERRQ
     state, and any check whose value the team already extracts
     from CAN signals in the Live Diagnostic surface. The host-
     detail backend consults the same code path Live Diagnostic
     uses (candump over SSH → cantools decode against the TS
     APP DBC → field extraction) rather than re-deriving these
     values via `ree-debug-cli`. Implementation may reuse the
     existing Live Diagnostic session if one is open, or open
     a one-shot decode for a few seconds, whichever the
     `/speckit-plan` step finds simplest. Per the 2026-05-12
     clarification, the pipeline MUST also extract VE-channel
     state signals (`VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`,
     `VE_PRND_STATE`, and any other `VE_*` signal in Wilhelm's
     `TS_diagnostic_tool/config.py` `TS_STATE_SIGNALS` list)
     when the connected host is a vehicle — same DBC, same
     decode path, no separate VE transport.
  2. **Non-REECU pipeline** — vDrive package version
     (dpkg-query), Peplink cellular + VPN (HTTP probes against
     the Peplink router), network reachability (ping / TCP
     connect), camera / input-device USB enumeration, WAKE
     line voltage, vehicle / telestation configuration
     validity. Default: drive via `ree-debug-cli report`. If
     any specific check turns out simpler to rewrite in Python
     on the backend, that is an acceptable per-check
     alternative — the Rust engine is the default, the Python
     rewrite is an opt-in fallback.

  The two pipelines may complete at different times; the page
  renders each as it arrives (see FR-010 for the combined
  loading-state contract).
- **FR-003**: The deleted React rendering components MUST be
  restored — `CategoryBadge`, `ResultGroup`, `ResultHero`,
  `DiagnosticItemRow`, `RepairGuideSheet`, `HarnessDiagram`,
  `TelestationDiagram`, `RunningState`, `PartialRunState`,
  `UnreachableState`, `StaggeredList`, `RunResultPage` (or the
  subset of them that the new host-detail page actually
  composes — whichever is the smallest viable set that delivers
  US1's acceptance scenarios). Per the 2026-05-12 clarifications,
  restoration source is tiered:
  - **Frontend** (harness / repair-guide UI AND the remaining
    result / states components): cherry-pick from
    `origin/005-ve-harness-repair-guide` — improved
    `HarnessDiagram`, `RepairGuideSheet`, `TelestationDiagram`
    plus the new `RepairGuideLibraryDialog`, `RepairGuidesPage`,
    `guideLibrary.ts`, AND the pre-007 `CategoryBadge`,
    `ResultGroup`, `ResultHero`, `DiagnosticItemRow`,
    `RunningState`, `PartialRunState`, `UnreachableState`,
    `EmptyInventoryState`, `RunResultPage`, `frontend/src/api/runs.ts`.
  - **Backend** pre-007 deletions (`backend/src/vayobd/checks/*`,
    `backend/src/vayobd/api/runs.py`) and **engine** Rust
    deletions (`engine/ree-debug-engine/src/checks/*`):
    restore from local pre-007 commit `01d3979` — NOT from
    Ezequiel's branch (his backend / engine snapshot is stale
    relative to recent pushes and would regress 006 / 007 work).
- **FR-004**: The Live Diagnostic page MUST mount, render its
  connection dialog, and populate the inventory list within five
  seconds of navigation, with no console errors, no failed
  requests in the network tab, and no literal `strings.ts` path
  keys visible on the page.
- **FR-005**: A reachable host (TS **or** VE) connected through
  Live Diagnostic MUST stream decoded CAN signals to the state
  panel within ten seconds of clicking Connect (matches 004
  SC-001). For VE hosts, the state panel MUST surface
  `VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`, `VE_PRND_STATE`,
  and any other `VE_*` signal carried by Wilhelm's
  `TS_diagnostic_tool/config.py` `TS_STATE_SIGNALS` list,
  alongside the TS-channel signals — same decoded-frame
  pipeline, same loading affordance, same plain-language
  degraded-mode wording. No separate VE transport / DBC /
  decode path: it is a signal-list pass-through.
- **FR-006**: The Live Diagnostic surface MUST tolerate the
  same degraded states 004 defined — missing errq CSVs, missing
  or stale DBC, ssh failures — with the same plain-language
  recovery copy 005 specified. Tolerance applies identically to
  TS-host and VE-host sessions. For VE hosts, the errq panel
  MUST resolve a **VE-specific errq CSV subpath** inside the
  **same** local `ree-reecu` clone the runtime already uses for
  TS errq (concrete subpath determined at `/speckit-plan` time)
  and feed it into the same `errq_bridge` decode pipeline used
  for TS hosts. The .deb packaging from 006 is NOT modified by
  008 — no new bundle, no second repo. If the VE subpath is
  missing or the clone is incomplete, the panel falls back to
  the 004 FR-012 degraded-mode message ("errq data unavailable
  for this host") — never silent, never fabricated data.
- **FR-007**: The `strings.ts` scrub from 007 MUST be reconciled
  with the restored check battery: every category label, every
  per-item description / action, every repair-guide copy line,
  every Working / Needs attention heading the restored UI uses
  MUST be present in `strings.ts` and rendered through the same
  `t(path)` lookup the rest of the SPA uses. No literal
  `strings.xxx.yyy` path may surface in operator-visible copy.
  Per the 2026-05-12 clarification, the `strings.ts`
  reconciliation is a 3-way hand-merge: post-007 HEAD is the
  base, Ezequiel's +107 lines from `origin/005-ve-harness-repair-guide`
  layer on top, the pre-007 `runs / outcomes / result /
  category / guide / item` blocks restore from `HEAD~N`. On any
  key collision, the post-007 HEAD value wins. The same
  precedence rule applies to `connectorLocations.ts`,
  `connectorSpecs.ts`, and `guides.ts` if 007 also modified them.
- **FR-008**: 007's version card MUST remain functional on the
  host-detail page in its post-007 form: per-field verdict
  pills (`match` / `drift` / `no-manifest` / `unavailable`),
  per-cell "as of" timestamps, source pill at top of card,
  60-second TTL cache, refresh affordance via `?fresh=true`,
  em-dash + spinner during in-flight load.
- **FR-009**: 007's dual TS_diag entry-point behaviour MUST
  remain functional: the in-UI Developer mode toggle continues
  to drive both the header copy AND the main-page primary-action
  copy; both appear / disappear together; the `/live` gate from
  004 FR-002 still redirects when Developer mode is off.
- **FR-010**: The two pipelines from FR-002 MUST run in parallel,
  not serialised. The page MUST render the REECU pipeline's
  output (vREECU + SEC + ERRQ-derived rows) as soon as it
  arrives, and the non-REECU pipeline's output (vDrive +
  Peplink + network + …) as soon as that arrives, without
  one blocking the other. Worst-case page load for each
  pipeline remains within the 004 / 007 budgets (decoded data
  visible within ten seconds).
- **FR-011**: Each datum on the page MUST come from exactly one
  pipeline — no row appears twice. The REECU pipeline owns
  vREECU, SEC, and any other check whose underlying signal is
  readable from CAN; `ree-debug-cli` MUST NOT emit those rows
  into the non-REECU pipeline's response, and the page MUST
  drop them if it ever finds them duplicated.
- **FR-012**: Failed checks in the restored battery MUST surface
  a repair-guide entry where one was registered before 007.
  Clicking the guide button MUST open the guide as a sheet over
  the page (matches the pre-007 RepairGuideSheet behaviour) so
  the operator does not lose context.
- **FR-013**: The unreachable-host state MUST be surfaced as a
  dedicated rendered state, not as a generic error — same shape
  as `UnreachableState` rendered before 007, with a Retry
  affordance.
- **FR-014**: The partial-result state (some checks completed,
  others did not) MUST be surfaced with the completed items
  visible AND a flag on the missing ones — matches the pre-007
  `PartialRunState` rendering.
- **FR-015**: The `.deb` runtime MUST prefer the
  package-installed engine binary
  (`/usr/lib/vayobd/bin/ree-debug-cli`) over any binary that
  happens to be on PATH, so a developer's source-tree binary
  does not silently shadow the installed one during testing.
- **FR-016**: All copy across the restored battery MUST follow
  the 005 plain-language policy — no "Run check" / "Run
  diagnostic" wording (the term itself is what 007 removed and
  005 found friction with). Use action-oriented copy
  ("Check this host", "Show details", etc.) consistent with
  what's already in `strings.ts`.
- **FR-017**: The top-level repair guide library surface
  (`RepairGuidesPage` + `RepairGuideLibraryDialog` +
  `guideLibrary.ts`, cherry-picked from
  `origin/005-ve-harness-repair-guide`) MUST be reachable
  from a chrome entry point (header link or main-page
  secondary action — `/speckit-plan` picks which) on every
  page in the SPA. The entry point MUST NOT be gated by
  Developer mode.
- **FR-018**: A guide opened from the library MUST render
  through the same `RepairGuideSheet` component instance and
  data path as a guide opened from a failing check on the
  host-detail page. There MUST NOT be two parallel guide
  definitions — `guides.ts` is the single source of truth,
  `guideLibrary.ts` is an index over it.
- **FR-019**: The `/live` inventory list / host-picker dialog
  MUST render a typed pill (`TS` / `VE`) next to each host id,
  sourced from `host.type` (already populated by the inventory
  loader). Pill styling follows the 002 sun-theme palette
  tokens; the specific colour mapping for the VE pill is a
  `/speckit-plan` decision but MUST NOT introduce a new
  palette colour.

### Key Entities *(include if feature involves data)*

- **HostReport**: The full per-host engine output — the same
  shape `ree-debug-cli report --host <id> --json` already
  produces. Carries the `EngineReport.checks` array the
  pre-007 backend used to render. The host-detail page consumes
  this once; the version card and the check battery render
  different slices.
- **CheckResult** (restored): One row of the per-host battery —
  category (communication, hardware, configuration, software,
  calibration), status (pass / warn / fail), operator-facing
  name, recovery action, optional repair-guide id. Mirrors
  the pre-007 `DiagnosticItem` shape; restored from the
  deleted `vayobd.checks` package's data model.
- **RepairGuide** (restored): A registered repair guide
  containing the diagram (harness / telestation / WAKE
  signal-path), copy, and debug steps that the
  `RepairGuideSheet` component opened. Restored from
  `frontend/src/guides.ts` (still in the tree as an orphan
  after 007) plus the deleted `RepairGuideSheet` component.
- **VersionField** (007): per-field record on the version card —
  unchanged from 007. Still routed via 007's
  `parse_engine_report` from the same `HostReport`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After 008 lands, **100%** of host-detail page
  loads against a reachable host render BOTH the version card
  AND the categorised check battery — never one without the
  other.
- **SC-002**: After 008 lands, **100%** of attempts to launch
  Live Diagnostic (Developer mode on, host reachable) reach the
  decoded-signal state within ten seconds, OR surface a
  plain-language connection error within five seconds. Zero
  "blank page" or "console error" reports.
- **SC-003**: Every check that existed on the host-detail page
  before 007 — verifiable by reading the deleted catalog.py
  and the deleted strings.ts blocks — appears on the page
  after 008. **Zero** checks are silently lost.
- **SC-004**: Every visible string on every surviving surface
  resolves to operator-facing copy (not a literal path).
  Grepping the rendered DOM for `strings\.` or path-like
  literals (e.g. `runs.runButton`) returns **zero** hits.
- **SC-005**: The 007 version-pull surface remains intact: the
  refresh button works, the 60-second TTL cache holds on
  re-visit (<500 ms cache-served re-render), per-cell
  timestamps render, the source pill is at the top of the
  card. **Zero** of these regress.
- **SC-006**: An operator can, in **under three seconds** of
  glancing at a host-detail page, distinguish (a) what version
  is on the host, (b) what is currently broken on the host,
  and (c) where to click for the repair guide of the most
  prominent failure.
- **SC-007**: The .deb-installed runtime resolves the engine
  binary to `/usr/lib/vayobd/bin/ree-debug-cli`. The source-tree
  binary at `engine/target/release/ree-debug-cli` is no longer
  silently preferred. Verifiable by inspecting the
  `engine_ready binary=…` log line at startup.
- **SC-008**: After 008 lands, **100%** of guides registered in
  `guideLibrary.ts` are reachable from the new chrome entry
  point in **two clicks or fewer** (entry point → guide). The
  same guides, when opened from a failing host-detail check,
  render through the identical `RepairGuideSheet` component
  with byte-identical output for the harness diagram, step
  list, and connector chips.
- **SC-009**: After 008 lands, a Live Diagnostic session
  against a reachable VE host renders **every** `VE_*` state
  signal listed in Wilhelm's
  `TS_diagnostic_tool/config.py` `TS_STATE_SIGNALS` (at minimum
  `VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`, `VE_PRND_STATE`)
  in the state panel within ten seconds of clicking Connect.
  The same session against a TS host renders the TS-channel
  signals unchanged — no regression of US2's TS path while
  adding VE support.

## Assumptions

- The deleted check battery's behaviour was correct at the time
  of deletion. Reverting / restoring it does not require
  redesigning category coverage — what existed in the pre-007
  catalog is the target state.
- The git history for the deleted files is intact and reachable
  via `git show HEAD~N:path` or equivalent. (If history was
  squashed away, the recovery becomes a re-implementation
  against the spec records in `specs/001-…` through
  `specs/006-…`.)
- The engine (`ree-debug-cli report`) already emits every check
  the restored battery needs to render — only the backend's
  exposure of those results was removed. No rust-side changes
  are required for US1; if a row turns out to need rust work,
  that is a follow-up.
- The Live Diagnostic regression is fixable on the frontend +
  backend Python side without touching the engine or the live
  WebSocket transport. If diagnosis turns up a deeper protocol
  issue, the spec needs revision.
- The 007 version-pull behaviour and the wider check battery
  can share one engine invocation per host. If the engine
  call's wall-clock is too long to gate the version card on
  it, the version card can keep its own faster path and the
  check battery streams in over a second call — a
  decision for `/speckit-plan`, not for this spec.
- Operators continue to be Vay engineers — the audience does
  not change between 007 and 008. Plain-language copy
  conventions from 005 / 007 carry forward.
- The .deb shipping model (single artefact, bundled Python from
  python-build-standalone, no system Python dependency) from
  the latest 006 / 007 / .deb-fix work is unchanged. 008 does
  not revisit packaging.
- Desktop TS Diagnostic Tool remains available as a fallback
  for engineers on Windows or for any case Live Diagnostic
  can't address mid-008.
- This is a regression-recovery feature, not a redesign — the
  scope is "put back what 007 over-removed and fix Live
  Diagnostic", not "redesign the diagnostic page from
  scratch."
