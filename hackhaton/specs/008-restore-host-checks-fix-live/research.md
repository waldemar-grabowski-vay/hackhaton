# Phase 0 Research — Restore host check battery, fix Live Diagnostic regression

**Date**: 2026-05-11
**Status**: complete — all NEEDS CLARIFICATION resolved (5-question clarification round 2026-05-11 + this document)

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
