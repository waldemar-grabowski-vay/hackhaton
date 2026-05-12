# Phase 0 Research — Restore host check battery, fix Live Diagnostic regression, integrate Wilhelm + Ezequiel

**Date**: 2026-05-11 (sections 1–7) · extended 2026-05-12 (sections 8–12)
**Status**: complete — all NEEDS CLARIFICATION resolved (5-question clarification round 2026-05-11 + 5-question clarification round 2026-05-12 + this document)

This file resolves the plan-level questions that the clarification
round deferred to implementation time. Each section has one decision,
the rationale, and the alternatives considered. The Live Diagnostic
section also documents what the 30-minute reproduction spike turned
up so US2's scope is concrete before tasks are generated.

---

## 1. Live Diagnostic failure-mode spike

**Decision**: Three concrete fixes scoped under US2, in priority order
of likelihood-of-cause as observed on the user's .deb-installed
runtime.

### 1a. SPA mount path — pyenv shim shadowing `/usr/bin/vayobd`

**Observation**: The user's `VAYOBD_EXECUTOR=ree vayobd run` log shows
the backend serving uvicorn at `127.0.0.1:8000` but `GET /` returning
404. The engine path in the log is the source-tree binary
(`/home/.../engine/target/release/ree-debug-cli`), not the .deb's
`/usr/lib/vayobd/bin/ree-debug-cli`. Both signals point at the same
root cause: the `vayobd` command they're running is the pyenv-installed
editable build (`pip install -e ./backend` from the 007 test pass),
which does NOT export the `VAYOBD_STATIC_DIR` env var that the
.deb's `/usr/bin/vayobd` wrapper exports. Without `VAYOBD_STATIC_DIR`,
`app.py` skips the `StaticFiles` mount on `/`, and every page (`/`,
`/host/:id`, `/live`) returns 404.

**Fix**: Detect this case and surface a clear error. Two paths:

1. **Backend-side**: in `vayobd.cli._cmd_run`, if `Settings.static_dir`
   is unset AND there is no source-tree `frontend/dist/index.html`
   reachable, log a loud one-line warning at startup
   pointing the user at either the `/usr/bin/vayobd` wrapper or a
   manual `VAYOBD_STATIC_DIR=…` export. Don't fail startup — uvicorn
   can still serve the API for power users.
2. **Doctor command**: extend `vayobd doctor` to check which `vayobd`
   binary is on the user's `$PATH` and warn when it doesn't match
   `/usr/bin/vayobd`. Surface the warning when `static_dir` is also
   unset.

**Rationale**: The 404 IS the user's "Live Diagnostic not working at
all" — the entire SPA is unmounted, including the entry-point button
and the `/live` route. Fixing this restores the whole SPA, not just
LD. The detect-and-warn approach is more useful than a hard-fail
because the SPA-mount setup is operator-environment, not a bug per se.

**Alternatives considered**:

- *Patch `/usr/bin/vayobd` to forcibly outrank pyenv shims.* Not
  possible — the wrapper is invoked by absolute path or PATH lookup,
  and PATH order is the operator's shell config, not ours.
- *Bundle a `vayobd-install` postinst step that removes the
  pyenv-installed editable.* Crosses a boundary (touching the
  operator's pyenv state from a system .deb script) that
  Principle I should not justify.

### 1b. DBC selection bias — `Env.dbc` picked over `application_protocol.dbc`

**Observation**: After fixing 1a, the LD page mounts but the user's
log shows `live_dbc_ready messages=0 source=…/ve/6_tools/CANoe_G4/dbcs/Env.dbc`.
That's a stub / placeholder DBC with zero TS-application signals.
The `find_dbc` glob in `backend/src/vayobd/live/dbc_decoder.py:22-28`
prefers (in order):

```
dbc/application_protocol.dbc
platform/dbc/*.dbc
ts/6_tools/CANoe_G4/DBCs/*.dbc       ← uppercase DBCs/
platform/tools/sec_bindings_generator/ts_*.dbc
**/*.dbc                              ← catch-all
```

The user's `ree-reecu` clone has the TS DBC under `ve/…` with
lowercase `dbcs/`, so patterns 1–4 miss and the catch-all picks the
most-recently-modified `.dbc` — which on their disk is `Env.dbc`.

**Fix**: Tighten the DBC glob list to include case-insensitive variants
and the `ve/…/dbcs/` and `ts/…/dbcs/` paths the team's recent
ree-reecu layout actually uses. Surface the matched path + message
count on the `/live` page so a wrong selection is visible to the
operator before they try to Connect.

**Rationale**: Surfaces the selection failure to the operator
(matches 005's "no silent failures" policy) and makes future DBC
layout shifts easier to debug. Touching only the glob patterns +
the page's status surface is the smallest correct fix.

**Alternatives considered**:

- *Let the operator pick a DBC manually from Settings.* 004 already
  designed this (FR-024) — the operator setting overrides the glob.
  Worth re-checking that the Settings UI exposes it; if not, file as
  a follow-up.

### 1c. errq degraded mode — missing TS CSV files

**Observation**: `errq build_model('ts') failed — missing CSV file:
.../ts/6_tools/TS_Generators/Errq/ts_errq_cfg_generator/csv/Error_Group_List.csv`.
The user's `ree-reecu` clone is incomplete (subset checkout, or
shallow / sparse clone). 004 FR-012 already specified the degraded-
mode behaviour — show a clear message in the errq panel, fall back
to raw byte values. The plumbing for that already exists.

**Fix**: Surface a more prominent in-UI notice (not just a backend
warning log) when errq is degraded. The current message ends up in
the backend log but the page itself may not render anything visible
in the errq panel — that's worth verifying during the spike.

**Rationale**: Same 005 "plain-language degraded states" policy.
This is a UX polish, not a fundamental break — the page can still
function.

**Alternatives considered**:

- *Block the page on errq being loaded.* No — 004 FR-012 explicitly
  allows degraded mode; reversing that would be a regression.
- *Have `vayobd refresh` pull the missing CSVs from the manifest.*
  Already the case if the manifest entry for `ree-reecu` is configured
  correctly. Confirm and document in quickstart.

### 1d. Possible `strings.ts` orphan reference

**Observation**: 007's `strings.ts` scrub removed `runs / outcomes /
result / category / guide / item` blocks. If any surviving code path
(the Live Diagnostic page, `LiveDiagnosticPage.tsx`, its components)
references those blocks via `t()` or direct property access, the
render either crashes or shows literal `runs.foo` path keys on the
page.

**Spike result** (preliminary): a `grep -rn "strings\." frontend/src/pages/LiveDiagnostic/` returned no hits — the LD page reads
operator-facing strings inline, not through `strings.ts`. So this
risk is low; flagged here only because it's the kind of regression
that's easy to introduce. The 008 strings.ts hand-merge (research §4)
restores the deleted blocks so any other consumer recovers too.

---

## 2. Restoration mechanics — `git checkout HEAD --`

**Decision**: One-shot `git checkout HEAD -- <path>` per deleted
path. The full command list is recorded in `quickstart.md` and is
the first task in `tasks.md`. Files restored:

```
backend/src/vayobd/api/runs.py
backend/src/vayobd/checks/__init__.py
backend/src/vayobd/checks/catalog.py
backend/src/vayobd/checks/executor.py
backend/src/vayobd/checks/peplink.py
backend/src/vayobd/checks/ree_cli.py
backend/src/vayobd/checks/runner.py
backend/tests/integration/test_runs_endpoint.py
backend/tests/unit/test_catalog.py
frontend/src/api/runs.ts
frontend/src/components/motion/StaggeredList.tsx
frontend/src/components/result/CategoryBadge.tsx
frontend/src/components/result/DiagnosticItemRow.tsx
frontend/src/components/result/HarnessDiagram.tsx
frontend/src/components/result/RepairGuideSheet.tsx
frontend/src/components/result/ResultGroup.tsx
frontend/src/components/result/ResultHero.tsx
frontend/src/components/result/TelestationDiagram.tsx
frontend/src/components/states/PartialRunState.tsx
frontend/src/components/states/RunningState.tsx
frontend/src/components/states/UnreachableState.tsx
frontend/src/pages/RunResultPage.tsx
```

After the checkout:

- `git status` shows zero deletions remaining (the staged-for-delete
  entries flip to "no change").
- Imports of the restored modules from the surviving files (e.g.
  `vayobd.checks.executor` is imported by `vayobd.dependencies`)
  resolve again.
- The restored test files run again (their fixtures are in
  `backend/tests/fixtures/runs/` which 007 did not touch).

**Rationale**: Clarification Q3 — mechanical revert preserves
exact pre-007 behaviour. Re-implementation against spec records
would risk introducing subtle differences (data shapes, copy
strings, error codes) and turn a one-day job into a multi-day one.

**Caveat — the only non-mechanical part**: `frontend/src/strings.ts`.
007 rewrote this file (kept the new `hostVersions` block, dropped the
`runs / outcomes / result / category / guide / item` blocks, dropped
`categoryLabel()`). A clean `git checkout HEAD --` would lose 007's
new block. The merge is hand-done — see research §4.

**Alternatives considered**:

- *`git revert` of a commit range.* Not applicable — 007's changes
  are uncommitted (working-tree edits and deletions), so there's no
  commit to revert. `git checkout` from HEAD is the equivalent.
- *Stash, checkout pristine HEAD, then re-apply 007's surviving
  edits.* More steps, same outcome; the per-path checkout is
  surgical and easier to review.

---

## 3. REECU one-shot capture — capture window and signal extraction

**Decision**: Backend opens a candump SSH session against the
requested host, captures frames for a fixed wall-clock window of
**4 seconds**, decodes via the existing `vayobd.live.dbc_decoder`
infrastructure, extracts the REECU fields from the latest decoded
values of the relevant signals, then closes the session. The four
fields extracted match the rust engine's existing REECU check
outputs:

| Field on host-detail page | CAN signal(s) decoded |
|---|---|
| `vREECU` (Aurix firmware version) | Latest `TS_FW_VERSION_*` signals (major / minor / patch) — same fields the engine's `compose_version_summary` reads. |
| `SEC version` | Latest `TS_GW_VERSION_*` signals. |
| `SEC state` | Latest `TS_SEC_STATE` (mapped via the engine's `ts_sec_state` table). |
| `ERRQ-decoded errors` | 64-byte `ERRQ_Byte01..64` buffer per channel, decoded via the existing `vayobd.live.errq_decoder`. |

**Window length**: 4 seconds chosen because:

- The slowest REECU broadcast (firmware version triplet) cycles at
  1 Hz, so 4 s catches at least 3 cycles — enough to discard a
  single missed frame without re-trying.
- The ERRQ buffer broadcasts at ~10 Hz, so 4 s catches ~40 frames
  per channel — far above the noise floor.
- Under the 10 s SC-002 budget with ~3 s headroom for SSH setup +
  teardown + transit.

**Empty capture handling**: if 4 s elapse without decoding any
REECU-bearing frame, the field renders as `unavailable` with
reason "host responded but produced no REECU frames in the capture
window" — same shape 007's `VersionField` already supports for
unavailable.

**Rationale**: Clarification Q4 — one-shot capture per page mount,
no long-lived background sessions. 4 seconds is the smallest window
that reliably catches the broadcast. The existing
`vayobd.live.session` code handles the SSH+candump lifecycle
already; the new wrapper is a thin adapter that opens a session,
runs it for N seconds, harvests the decoded state, then closes.

**Alternatives considered**:

- *Variable window — stop early when all four fields have been
  observed.* More code; the savings (~1-2 s on average) don't move
  the user-visible budget. Defer until SC-002 latency becomes a
  problem.
- *Re-use an existing `/live` session if one is open against the
  same host.* Spec edge case lists this as a future option. Defer
  to a follow-up — the one-shot path is independent and works
  whether or not LD is open.

---

## 4. `strings.ts` hand-merge strategy

**Decision**: `git show HEAD:hackhaton/frontend/src/strings.ts` to
get the pre-007 content; carefully merge with the current
working-tree content, keeping:

- **From HEAD** (restored): `wizard.host.subtitle`'s original wording
  ("Each tile is one machine you can run a check against."); the
  `wizard.runButton` key (still referenced in the restored pages);
  the entire `runs`, `outcomes`, `result`, `category`, `guide`, and
  `item` blocks; the `categoryLabel()` function.
- **From working tree** (007 additions): the entire `hostVersions`
  block (cardTitle, refreshButton, sourceLive, sourceUnavailable,
  verdict labels, expectedPrefix, noManifestHint, field labels).

The merged file is then a superset — every string referenced by any
component on the page, from any feature, resolves through
`strings.ts` with no literal path keys leaking to the rendered DOM.

**Rationale**: Strict superset means no consumer regresses. The
"Run check" wording the user explicitly flagged in 007 (and which I
removed because the assumption was the run flow was gone) comes
back because the run flow itself is coming back. The plain-language
adjustments 005 / 007 made stay in place where they apply (the
`hostVersions` block uses 007's "Refresh" / "matches manifest" /
etc. wording).

**Verification step**: after the merge, run
`grep -rn 't("' frontend/src/` and confirm every dot-path used in
a `t("…")` call resolves to a non-undefined string in `strings.ts`.

**Alternatives considered**:

- *Keep 007's slimmed strings file and rewrite the restored pages
  to inline their strings.* Larger diff, harder to review, departs
  from the SPA's "single source of truth" convention.
- *Generate strings.ts from a TOML / JSON source.* Out of scope —
  no team value in restructuring the i18n surface during 008.

---

## 5. `runs_router` re-registration in `app.py`

**Decision**: After `git checkout HEAD -- backend/src/vayobd/api/runs.py`,
add the import + `app.include_router(runs_router)` line back in
`backend/src/vayobd/app.py`. The pre-007 wiring is:

```python
from vayobd.api.runs import router as runs_router
# …
app.include_router(runs_router)
```

This re-exposes `POST /api/runs` and (per the restored
`runs.py`) `GET /api/runs/{run_id}`. The route list reverts to
the pre-007 set + 007's `host_versions_router` (kept) + 007's
`refresh_router` (kept).

**Rationale**: One-line wiring change; no abstraction needed.

**Alternatives considered**:

- *Wait until US3 to re-register, so US1 only restores files
  without changing app.py.* Marginal; saves nothing because US3
  needs this wiring anyway. Doing it in US1 keeps the diff atomic.

---

## 6. `VersionCache` extension for the unified response

**Decision**: Reuse 007's `VersionCache[T]` generic from
`backend/src/vayobd/_internal/version_cache.py`. The type parameter
changes from `HostVersionsResponse` (007's narrow shape) to
`HostDetailResponse` (008's broader shape that adds restored check
results + REECU rows). No code change required in `version_cache.py`
— the generic is already polymorphic. The only edit is the
type parameter at the import site in `host_versions.py`.

**Rationale**: Cleanest possible reuse — the cache was designed
generic for exactly this kind of extension. The 60 s TTL and
per-host key remain the right knobs.

**Verification**: the existing `test_version_cache.py` tests pass
unchanged. The new `test_host_versions_endpoint.py` adjustments
exercise the cache with the richer payload.

**Alternatives considered**:

- *New `HostDetailCache` class.* Duplicates the existing code with
  a different type parameter; violates Principle I.

---

## 7. Coordination with Live Diagnostic sessions

**Decision**: The host-detail page's REECU capture is independent
of any operator-opened `/live` session. Two SSH spawns against the
same testbed coexist exactly as 004 FR-019 already specified ("each
session MUST be independent with no cross-talk").

**Open follow-up (non-blocking for 008)**: if the testbed proves to
have a hard per-host concurrent-SSH limit, the host-detail backend
may want to detect an open `/live` session and piggyback on its
decoded-signal stream rather than opening its own. This is
explicitly out of scope for 008 — 004 already allowed concurrent
sessions and the team has not reported the limit being hit. Track
in `quickstart.md` follow-ups.

**Rationale**: Avoid over-engineering. Independent sessions are
the established 004 contract.

---

## 8. Ezequiel cherry-pick — source map and 3-way merge mechanics

**Decision**: Source restoration files by tier, and resolve the four
3-way-merge files with "post-007 HEAD wins on collision; otherwise
union" precedence.

### 8a. Source tiers

Per the 2026-05-12 clarifications, restoration sources split three ways:

```text
Tier A — Frontend (from origin/005-ve-harness-repair-guide):
  improved (replace HEAD)
    frontend/src/components/result/HarnessDiagram.tsx
    frontend/src/components/result/RepairGuideSheet.tsx
    frontend/src/components/result/TelestationDiagram.tsx
  net-new (add)
    frontend/src/components/chrome/RepairGuideLibraryDialog.tsx
    frontend/src/pages/RepairGuidesPage.tsx
    frontend/src/guideLibrary.ts
  net-new assets (add, under public/)
    frontend/public/ve-pigtail-f61-harness.jpg
    frontend/public/ve-reebox-power-cable-harness.jpg
    frontend/public/ve-vs040815-harness-p1.png
    frontend/public/ve-vs040815-harness.pdf
  pre-007 FE deletions, recovered (add)
    frontend/src/api/runs.ts
    frontend/src/components/result/CategoryBadge.tsx
    frontend/src/components/result/DiagnosticItemRow.tsx
    frontend/src/components/result/ResultGroup.tsx
    frontend/src/components/result/ResultHero.tsx
    frontend/src/components/states/EmptyInventoryState.tsx
    frontend/src/components/states/PartialRunState.tsx
    frontend/src/components/states/RunningState.tsx
    frontend/src/components/states/UnreachableState.tsx
    frontend/src/components/motion/StaggeredList.tsx
    frontend/src/pages/RunResultPage.tsx
  3-way merge (do NOT clobber HEAD; see §8b)
    frontend/src/strings.ts
    frontend/src/connectorLocations.ts
    frontend/src/connectorSpecs.ts
    frontend/src/guides.ts
    frontend/src/App.tsx                       (route registration only)

Tier B — Backend (from local pre-007 commit 01d3979):
  backend/src/vayobd/api/runs.py
  backend/src/vayobd/checks/__init__.py
  backend/src/vayobd/checks/catalog.py
  backend/src/vayobd/checks/executor.py
  backend/src/vayobd/checks/peplink.py
  backend/src/vayobd/checks/ree_cli.py
  backend/src/vayobd/checks/runner.py
  backend/tests/integration/test_runs_endpoint.py
  backend/tests/unit/test_catalog.py

Tier C — Engine (from local pre-007 commit 01d3979):
  engine/ree-debug-engine/src/checks/cameras.rs
  engine/ree-debug-engine/src/checks/connectivity.rs
  engine/ree-debug-engine/src/checks/decode.rs
  engine/ree-debug-engine/src/checks/mod.rs
  engine/ree-debug-engine/src/checks/reecu.rs
  engine/ree-debug-engine/src/checks/usb.rs
```

The full table is exported as `contracts/ezequiel-cherry-pick.md`.

### 8b. 3-way merge files

Four files have legitimate edits in all three sources:

| File | post-007 HEAD owns | Ezequiel adds | Pre-007 restores |
|---|---|---|---|
| `frontend/src/strings.ts` | `hostVersions` block; refresh + dev-mode keys | `+107` keys (harness / guide / library) | `runs / outcomes / result / category / guide / item` blocks; `categoryLabel()` |
| `frontend/src/connectorLocations.ts` | any 007 edits (verify; expected: none) | `+86` lines of VE-side locations | — |
| `frontend/src/connectorSpecs.ts` | any 007 edits (verify; expected: minimal) | `+863` lines of VE connector specs | — |
| `frontend/src/guides.ts` | any 007 edits (verify; expected: none — was orphan) | `+763` lines of guide content | — |

**Merge rule**: post-007 HEAD is the base. Ezequiel's additions are
unioned in. Pre-007 deleted blocks (only `strings.ts` has them) are
unioned in. **On any key collision, post-007 HEAD wins.**

**Implementation choice**: per file, use:

```bash
git checkout origin/005-ve-harness-repair-guide -- <path>
```

then re-introduce the post-007 HEAD blocks by hand-edit. NOT a clean
`git cherry-pick` — Ezequiel's branch has unrelated backend
deletions in the same commits that would corrupt a `cherry-pick`.

**Rationale**: The merge is union-by-default, conflict-resolution
deterministic ("HEAD wins"). One precedence rule covers every case;
no per-file judgement needed beyond verifying the rule applied.

**Alternatives considered**:

- *Resolve conflicts in Ezequiel's favour.* Loses the 007 wins
  FR-008 / FR-009 commit to. Rejected by clarification Q2.
- *Hand-merge per file with named owner in `/speckit-tasks`.* Higher
  ceremony, same outcome. Rejected for cost.

---

## 9. Library chrome entry point — header link (not Developer-mode-gated)

**Decision**: Add a **header** link to `RepairGuidesPage`. The link
lives in `frontend/src/components/chrome/AppHeader.tsx` as a
secondary nav item beside the existing primary actions. It is
**not** Developer-mode-gated — harness and repair knowledge is
operator-facing.

**Placement**:

```text
┌─ AppHeader ─────────────────────────────────────────┐
│  [Vay logo]  [Hosts]  [Repair guides]   …   [Dev▸] │
└──────────────────────────────────────────────────────┘
```

The new "Repair guides" link routes to the `/repair-guides` route
registered in Ezequiel's `App.tsx` delta.

**Rationale**: Header placement is reachable from every page in the
SPA (the constitution Web App Standards already require responsive
layout; header keeps the entry point reachable on phone-sized
viewports too). Operator-facing (not gated) per Q3 of the 2026-05-12
clarification round.

**Alternatives considered**:

- *Main-page secondary action only.* Reachable only from `/`; an
  operator three pages deep into a host-detail flow would have to
  navigate back. Rejected for UX cost.
- *Developer-mode-gated header link.* Conflicts with the
  clarification (Q3) and the constitution Principle III
  (operator-facing knowledge should not be gated).

---

## 10. VE state-signal port from Wilhelm's desktop tool

**Decision**: Lift Wilhelm's `TS_STATE_SIGNALS` allowlist from
`TS_diagnostic_tool/config.py` and merge it into the web app's
state-panel allowlist on `/live`. Specifically, the web app's
`backend/src/vayobd/live/candump_runner.py` (or wherever the
allowlist lives — `/speckit-plan` confirms the exact location at
task time) MUST be extended to include every entry in Wilhelm's
list, with no de-duplication: the web app already includes the
`TS_*` entries; the additions are the `VE_*` entries:

```python
VE_STATE_SIGNALS_ADDED: tuple[str, ...] = (
    "VE_ChA_SSMAN_State",
    "VE_ChB_SSMAN_State",
    "VE_PRND_STATE",
    # …plus any additional VE_* signals in Wilhelm's TS_STATE_SIGNALS
    # — exact list is the verbatim grep result at task time.
)
```

The state-panel decode pipeline is unchanged: `candump → cantools
decode against the TS APP DBC → filter by allowlist`. The TS APP DBC
already carries the VE signals (Wilhelm's config.py and his README
both confirm this — the DBC is the unified application protocol).

### 10a. Host-type routing

The Live Diagnostic backend already knows the host type (the
inventory loader tags `ve-*` IDs as `HostType.VEHICLE`). The
state-panel renderer receives the entire decoded signal stream and
filters by allowlist; the host's type doesn't gate which signals
appear — whichever signals the bus broadcasts, get displayed.

**Rationale**: Mirrors Wilhelm's desktop tool exactly. Zero new
transport. No host-type-specific filter on the decoder side keeps
the code path the same for both host classes; the bus broadcasts
naturally decide which signals are visible.

**Alternatives considered**:

- *Per-host-type allowlist (TS-only on TS hosts, VE-only on VE hosts).*
  Adds gating with no benefit — a VE bus simply does not broadcast
  `TS_*` signals (and vice versa), so the filter falls through
  naturally on the data.
- *Configurable allowlist.* No team value; Principle I says no.

---

## 11. VE errq CSV subpath resolution

**Decision**: `errq_bridge` (the web app's port of Wilhelm's
`errq_bridge.py`) gains a second resolver path for VE-side CSVs
inside the **same** local `ree-reecu` clone the runtime already
uses for TS errq. The TS subpath is unchanged:

```
{ree_reecu_root}/ts/6_tools/TS_Generators/Errq/ts_errq_cfg_generator/csv/
```

The VE subpath is (preliminary, to be confirmed against the actual
clone at task time):

```
{ree_reecu_root}/ve/6_tools/VE_Generators/Errq/ve_errq_cfg_generator/csv/
```

The path is a **lookup**, not a guess: `/speckit-tasks` includes a
short investigative step against the team's `ree-reecu` clone
to confirm the actual VE subpath (the directory may be `ve_errq_*`
or `ve/.../errq/`; the exact spelling is what gets baked in).

### 11a. Fallback semantics

If the VE subpath is missing or the clone is partial, the errq
panel falls back to the 004 FR-012 degraded-mode message — same
fallback as for missing TS CSVs. No fabricated data, no silent
empty panel.

### 11b. .deb packaging unchanged

The 006 `.deb` does NOT bundle either TS or VE errq CSVs — it
expects the operator to have a `ree-reecu` clone locally
(documented in 006's quickstart). 008 does not modify this:
the new VE resolver reads from the same local clone.

**Rationale**: Single source of truth (one `ree-reecu` clone for both
TS and VE errq) keeps the operator's mental model simple — they
have one clone, not two. The .deb stays slim.

**Alternatives considered**:

- *Bundle VE CSVs in the .deb.* Expands 006's packaging surface;
  also requires the .deb build to know where to fetch VE CSVs from
  at build time. Out of 008 scope.
- *Separate `ree-reecu-ve` repo.* Two clones for one feature.
  Rejected for operator cost.
- *Network-fetch VE CSVs at startup.* New external dependency, new
  failure mode. Rejected for risk.

---

## 12. 005 → 009 rename mechanics for Ezequiel's spec dir

**Decision**: Pull Ezequiel's `specs/005-ve-harness-repair-guide/`
directory into the local repo under a new name:
`specs/009-ve-harness-repair-guide/`. The local
`specs/005-ui-readability-pass/` stays untouched.

### 12a. Concrete steps

```bash
# 1. Copy the directory from Ezequiel's branch
git checkout origin/005-ve-harness-repair-guide -- \
  hackhaton/specs/005-ve-harness-repair-guide/

# 2. Move it to the renamed slot
git mv hackhaton/specs/005-ve-harness-repair-guide \
       hackhaton/specs/009-ve-harness-repair-guide

# 3. Inside the renamed spec.md, repoint the metadata
#    - **Feature Branch**: `005-ve-harness-repair-guide` → `009-ve-harness-repair-guide`
#    - any inline references to "005" (self-references) → "009"
# (Note: cross-references to other 005-* features — e.g., to 005's
#  plain-language work in the local repo — stay as 005 since they
#  point at a different feature.)
```

### 12b. Reading order for future contributors

- `specs/008-restore-host-checks-fix-live/spec.md` — what changed,
  how it composed (the integration mechanics + Wilhelm port).
- `specs/009-ve-harness-repair-guide/spec.md` — Ezequiel's design
  rationale for the harness / repair-guide UI 008 absorbed.

The 009 spec is read-only documentation; no code lives under it
(all code is integrated into the hackhaton/ tree via the
cherry-pick).

**Rationale**: Numbering preserves uniqueness (constitution
implicitly assumes feature slots are unique — tooling builds on
the dir name). Documentation is preserved for future readers tracing
back `git blame` on harness files.

**Alternatives considered**:

- *Drop entirely.* Loses design rationale; future contributors
  read code without context. Rejected.
- *Pull as-is, accept double 005.* Breaks the slot-unique
  assumption. Rejected.

---

## Outstanding follow-ups (not blocking this feature)

- **The `/usr/bin/vayobd` wrapper conflicting with pyenv shims** is
  a user-environment issue, not a vayobd bug. The .deb's
  `postinst.sh` could print a one-line warning when it detects a
  pyenv-managed `vayobd` is on PATH, but that's a usability
  improvement, not a 008 deliverable.
- **The `/live` Settings UI for DBC path override** (004 FR-024) —
  worth re-checking that it's still exposed in Settings; file as a
  follow-up if not.
- **REECU pipeline piggybacking on an open `/live` session** —
  optimisation deferred until a concrete latency / per-host SSH
  limit problem appears in practice.
- **Engine `--versions-only` or structured-versions block** — same
  follow-up as 007's research §7 / §1. Still defer.
