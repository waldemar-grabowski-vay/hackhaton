# Implementation Plan: Restore host check battery, fix Live Diagnostic regression, integrate Wilhelm + Ezequiel

**Branch**: `008-restore-host-checks-fix-live` | **Date**: 2026-05-12 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `specs/008-restore-host-checks-fix-live/spec.md`

## Summary

008 is a regression-recovery + contributor-integration round. It restores
the host check battery that 007 over-removed, fixes the Live Diagnostic
surface that 007 left non-working, and absorbs the two outstanding
contributor streams into one consistent app:

- **Ezequiel's `origin/005-ve-harness-repair-guide`** — frontend-only
  cherry-pick of the improved harness / repair-guide UI, the new
  `RepairGuidesPage` + `RepairGuideLibraryDialog` + `guideLibrary.ts`,
  the four new harness assets, and the additive blocks in
  `connectorSpecs.ts`, `guides.ts`, `connectorLocations.ts`, `strings.ts`.
- **Wilhelm's `TS_DIAG_TOOL_V1.9`** — already an ancestor of HEAD via
  PR #1 (commit `b3e79ff`). 008 ports the VE-channel state signals his
  desktop tool surfaces (`VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`,
  `VE_PRND_STATE`, plus all `VE_*` entries in his `TS_STATE_SIGNALS`)
  onto the hackhaton web app's `/live` Live Diagnostic surface, with
  VE-side errq CSVs resolved from the same `ree-reecu` clone the
  runtime already uses for TS errq.

Technical approach:

1. **Restoration source by tier**: frontend pre-007 deletions come from
   `origin/005-ve-harness-repair-guide` (one consistent FE source);
   backend + engine pre-007 deletions come from the local pre-007 commit
   `01d3979` (his backend/engine snapshot is stale relative to recent
   pushes).
2. **3-way hand-merge** for the four shared files
   (`strings.ts`, `connectorLocations.ts`, `connectorSpecs.ts`,
   `guides.ts`): post-007 HEAD is the base, Ezequiel's branch layers
   on top, pre-007 blocks restore from `HEAD~N` for `strings.ts`. On
   any key collision, post-007 HEAD wins (preserves the FR-008 / FR-009
   commitments to 007's version-pull surface).
3. **Live Diagnostic fixes** stay as scoped by the 2026-05-11 research:
   SPA mount path (pyenv shim vs `/usr/bin/vayobd`), DBC glob tightening,
   errq degraded-mode prominence, strings.ts orphan refs.
4. **Host-type-aware Live Diagnostic** uses the existing `host.type`
   inventory tag (already populated for `ve-*` / `ts-*` prefixed IDs).
   The `errq_bridge` gets a VE subpath resolver; the state-panel
   allowlist gains the `VE_*` signal names; the inventory dialog gains
   a `TS` / `VE` pill per row.
5. **Library surface (US5)**: cherry-picked `RepairGuidesPage` +
   `RepairGuideLibraryDialog` + `guideLibrary.ts` land with the
   `App.tsx` route. Chrome entry point chosen in research §8 (header
   link, not Developer-mode-gated). One `RepairGuideSheet` component,
   two entry points, no parallel guide definition.
6. **Spec dir 005 rename**: Ezequiel's `specs/005-ve-harness-repair-guide/`
   is pulled in as `specs/009-ve-harness-repair-guide/` to avoid
   colliding with the local `specs/005-ui-readability-pass/`. Code
   lands as part of 008; 009 is the design-intent doc.

## Technical Context

**Language/Version**:
- Frontend: TypeScript 5.6.3, React 18.3.1
- Backend: Python 3.11+ (FastAPI + Pydantic v2)
- Engine: Rust (ree-debug-engine, edition 2021)
- Desktop reference (TS_diagnostic_tool/): Python 3.11, PyQt6

**Primary Dependencies**:
- Frontend: Tailwind CSS 3.4.13, shadcn/ui (New York, slate baseColor),
  tailwindcss-animate, Zod (for the API schema), React Router 6 (route
  registration for `RepairGuidesPage`), `@tanstack/react-query` (host
  versions fetch + cache).
- Backend: FastAPI, Pydantic v2, paramiko (SSH), cantools (DBC decode),
  python-dateutil. The restored `vayobd.checks.*` package re-imports
  `httpx` (Peplink probes), `subprocess` (ree-debug-cli, ssh).
- Engine: `clap`, `serde_json`, `serde_yaml`, the
  in-tree `engine/ree-debug-engine` workspace.

**Storage**:
- Run records: `backend/.cache/vayobd/runs/<operator-slug>/<host-id>.json`
  (pre-007 location restored).
- Host-versions TTL cache: in-process via `VersionCache[HostDetailResponse]`
  (60 s TTL, per-host key).
- errq CSVs: read from the local `ree-reecu` clone (TS subpath +
  new VE subpath); no app-side persistence.

**Testing**:
- Backend: pytest (`pytest -q`), incl. restored `test_runs_endpoint.py`,
  `test_catalog.py`, new `test_reecu_capture.py`, new
  `test_ve_signals_decode.py`.
- Frontend: `npm run build && npm run lint` plus Playwright specs
  for the `/live` flow (including the new VE-host scenario) and the
  library page.
- Manual: the 8-step quickstart, now incl. dual-host (TS + VE) Live
  Diagnostic walkthrough.

**Target Platform**:
- Web: browser-based SPA (Chrome / Firefox / Safari / Edge current
  versions per Constitution Web App Standards).
- Backend: Linux server, shipped as the 006 `.deb` (`vayobd_0.0.7_amd64.deb`
  for this round). Bundled Python via python-build-standalone; no
  system Python dependency.
- Engine: Linux x86-64 (debian-stable–compatible glibc).
- Desktop reference: Windows (Wilhelm's PyQt6 + Inno Setup), out of
  scope for 008 modifications — only its signal-list / errq pipeline
  is *referenced* by the web port.

**Project Type**: Web application (FastAPI backend + React SPA) with
a companion native engine and a reference desktop tool.

**Performance Goals**:
- Live Diagnostic decoded-signals state within **10 s** of clicking
  Connect (TS or VE) — matches 004 SC-001 and the new SC-009.
- Host-detail page renders BOTH version card AND check battery
  within **10 s** for a cold load; **<500 ms** for a TTL-served
  re-render within 60 s (per SC-005).
- Quickstart end-to-end: dev path under **15 min** for one developer
  on a tested machine (the +5 min vs 2026-05-11 covers the VE step).

**Constraints**:
- No regressions of 007's wins (per FR-008 / FR-009 / FR-015 / FR-016).
- No expansion of the 006 `.deb` packaging surface (FR-006 explicitly
  re-uses the existing `ree-reecu` clone for VE errq).
- Ezequiel's backend / engine code is **not** sourced — only frontend.
- The Constitution's Principle III (Non-Technical User UX) keeps the
  bar for plain-language degraded states across all new VE paths.

**Scale/Scope**:
- Inventory: O(100) hosts (mixed TS + VE) typical; O(1000) tolerated.
- Restored components: ~12 React components, ~7 Python modules,
  ~6 Rust files (per research §2 + the cherry-pick path lists).
- Library catalogue: ~20–40 registered guides initially (count
  matches `guideLibrary.ts` on Ezequiel's branch — exact count is a
  research §8 lookup).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The constitution has three principles. 008 is evaluated against each:

### I. Simplicity First — PASS

- **Cherry-pick over rewrite**: pulling Ezequiel's frontend files
  verbatim (via `git checkout origin/005-ve-harness-repair-guide --`)
  is simpler than re-implementing his harness improvements from his
  spec.
- **Existing host-type infrastructure reused**: the backend already
  has `HostType` enum, `host_class`, `catalog_for(host_class)`, and
  `parse_engine_report(host_type=…)`. VE support is a signal-list
  + CSV-path pass-through, not new architecture.
- **`VersionCache[HostDetailResponse]`**: 007's generic cache is
  reused unchanged — only the type parameter at the import site
  changes (research §6).
- **One `RepairGuideSheet` component, two entry points** (host-detail
  + library): no parallel guide definitions (FR-018).
- **No new clones / packages / repos**: VE errq uses the existing
  `ree-reecu` clone (FR-006); no `ree-reecu-ve` second repo, no
  bundled VE CSVs in the .deb.

The only mild complexity: the 3-way hand-merge across
`strings.ts` / `connectorLocations.ts` / `connectorSpecs.ts` /
`guides.ts`. Justified — these files have legitimate edits from
three sources, and a clean precedence rule ("007 wins on
collision") keeps the merge mechanical, not judgement-heavy.

### II. Ship Fast — PASS

- 008 lands as **one PR** (the user's stated goal: "one consistent
  app"). No multi-PR sequencing.
- The mainline branch remains demo-deployable: nothing in the
  restoration or Wilhelm-port path requires a feature flag; the
  TTL cache + degraded-mode fallbacks keep cold paths safe.
- The .deb path (006) is untouched, so the demo .deb stays current.

### III. Non-Technical User UX — PASS

- All restored copy goes through `strings.ts` (FR-007); no literal
  path keys leak (SC-004).
- Plain-language degraded modes preserved for missing errq CSVs
  (FR-006, TS and VE), missing or stale DBC (research §1b/§1c),
  and unreachable hosts (FR-013).
- The `TS` / `VE` inventory pill (FR-019) tells the operator what
  they're connecting to *before* they click Connect.
- The repair-guide library (US5) is **not** Developer-mode-gated;
  harness/repair knowledge is operator-facing knowledge.
- Action-oriented copy: no "Run check / Run diagnostic" wording
  (FR-016).

**No violations. No Complexity Tracking entries needed.**

## Project Structure

### Documentation (this feature)

```text
specs/008-restore-host-checks-fix-live/
├── plan.md              # This file (/speckit-plan output)
├── research.md          # Phase 0 — extended 2026-05-12 with new sections
├── data-model.md        # Phase 1 — VE host extensions
├── quickstart.md        # Phase 1 — 8-step walkthrough (was 7; +VE step)
├── contracts/
│   ├── http-api.md            # GET /api/host/{id}/versions (unified)
│   ├── reecu-pipeline.md      # One-shot REECU capture (TS + VE)
│   ├── strings-merge.md       # 3-way hand-merge guide
│   ├── ezequiel-cherry-pick.md  # NEW — exact file list, source tier
│   ├── ve-signals.md          # NEW — VE state signal list, decode
│   └── ve-errq.md             # NEW — VE errq CSV subpath resolution
├── checklists/
│   └── requirements.md  # (untouched)
└── tasks.md             # Phase 2 — regenerated by /speckit-tasks
```

### Source Code (repository root: `/home/waldemar-grabowski/GitHub/hackhathon/`)

```text
hackhaton/                            # the SPA + backend (008 work lives here)
├── backend/
│   └── src/vayobd/
│       ├── api/
│       │   ├── host_versions.py      # 007 — extended for HostDetailResponse + VE
│       │   ├── refresh.py            # 007 — kept
│       │   ├── runs.py               # RESTORED from 01d3979
│       │   └── auth.py
│       ├── checks/                   # RESTORED from 01d3979
│       │   ├── catalog.py            # full pre-007 catalog
│       │   ├── executor.py
│       │   ├── peplink.py
│       │   ├── ree_cli.py
│       │   └── runner.py
│       ├── _internal/
│       │   └── version_cache.py      # 007 — generic, kept; new type parameter
│       ├── install/                  # 007 / 006 — kept
│       ├── inventory/                # — kept; already supplies HostType
│       ├── live/                     # 004 / 007 — kept; VE signal + errq
│       │   ├── candump_runner.py     # +VE allowlist
│       │   ├── dbc_decoder.py        # glob tightening (research §1b)
│       │   ├── errq_bridge.py        # +VE CSV resolver
│       │   ├── session.py
│       │   └── ws_router.py
│       └── app.py                    # re-include runs_router
├── frontend/
│   ├── public/                       # +4 harness assets from Ezequiel
│   │   ├── ve-pigtail-f61-harness.jpg
│   │   ├── ve-reebox-power-cable-harness.jpg
│   │   ├── ve-vs040815-harness-p1.png
│   │   └── ve-vs040815-harness.pdf
│   └── src/
│       ├── api/
│       │   ├── runs.ts               # RESTORED from Ezequiel's branch
│       │   └── hostVersions.ts       # 007 — schema gains optional `run`
│       ├── components/
│       │   ├── chrome/
│       │   │   ├── AppHeader.tsx     # +library entry point (research §8)
│       │   │   └── RepairGuideLibraryDialog.tsx  # NEW from Ezequiel
│       │   ├── result/               # FE pre-007 restorations from Ezequiel
│       │   │   ├── CategoryBadge.tsx
│       │   │   ├── DiagnosticItemRow.tsx
│       │   │   ├── HarnessDiagram.tsx       # Ezequiel's improved version
│       │   │   ├── RepairGuideSheet.tsx     # Ezequiel's improved version
│       │   │   ├── ResultGroup.tsx
│       │   │   ├── ResultHero.tsx
│       │   │   └── TelestationDiagram.tsx   # Ezequiel's improved version
│       │   ├── states/               # FE pre-007 restorations from Ezequiel
│       │   │   ├── PartialRunState.tsx
│       │   │   ├── RunningState.tsx
│       │   │   ├── UnreachableState.tsx
│       │   │   └── EmptyInventoryState.tsx
│       │   ├── motion/
│       │   │   └── StaggeredList.tsx
│       │   └── live/
│       │       └── InventoryDialog.tsx        # +TS / VE pill (FR-019)
│       ├── pages/
│       │   ├── HostDetailPage.tsx    # composes version card + check battery
│       │   ├── LiveDiagnosticPage.tsx
│       │   ├── RepairGuidesPage.tsx  # NEW from Ezequiel
│       │   └── RunResultPage.tsx     # RESTORED from Ezequiel's branch
│       ├── connectorLocations.ts     # 3-way merged (research §4)
│       ├── connectorSpecs.ts         # 3-way merged
│       ├── guides.ts                 # 3-way merged
│       ├── guideLibrary.ts           # NEW from Ezequiel
│       ├── strings.ts                # 3-way merged
│       └── App.tsx                   # +/repair-guides route from Ezequiel
├── engine/
│   └── ree-debug-engine/
│       └── src/checks/               # RESTORED from 01d3979
│           ├── cameras.rs
│           ├── connectivity.rs
│           ├── decode.rs
│           ├── mod.rs
│           ├── reecu.rs
│           └── usb.rs
└── specs/
    ├── 008-restore-host-checks-fix-live/  # this feature
    └── 009-ve-harness-repair-guide/       # Ezequiel's spec, renamed from 005-…

TS_diagnostic_tool/                   # repo-root sibling — Wilhelm's desktop tool
                                       # (untouched by 008; reference source for VE signals)
```

**Structure Decision**: Web application with two tiers + reference
desktop tool. The frontend / backend split mirrors the standing
hackhaton layout — 008 doesn't reorganise anything, it restores +
absorbs into the existing structure. The 009 spec directory is a
documentation companion (no code under it); all 008 code lands
inside `hackhaton/`.

## Phase 0 Output

`research.md` was authored on 2026-05-11 (sections 1–7) and extended
on 2026-05-12 (sections 8–12) to absorb the cherry-pick mechanics,
VE state-signal port, VE errq CSV resolution, library entry point,
and 005→009 rename. All `NEEDS CLARIFICATION` items are resolved.

## Phase 1 Output

- `data-model.md` — updated with VE host extensions, host-type
  routing, and the inventory `TS` / `VE` pill source field.
- `contracts/http-api.md` — extended with the host-type behaviour for
  the unified `GET /api/host/{id}/versions` endpoint.
- `contracts/reecu-pipeline.md` — extended for VE-host capture
  (additional signal allowlist; no transport change).
- `contracts/strings-merge.md` — extended to a 3-way merge guide
  (post-007 HEAD ↔ Ezequiel ↔ `HEAD~N` for the deleted blocks).
- `contracts/ezequiel-cherry-pick.md` (new) — file-by-file source
  table (which files come from which source tier).
- `contracts/ve-signals.md` (new) — VE state-signal allowlist and
  decode contract.
- `contracts/ve-errq.md` (new) — VE errq CSV subpath resolution
  contract.
- `quickstart.md` — 8-step walkthrough (added Step 4½: VE-host
  acceptance against the same testbed).

## Complexity Tracking

> No constitution violations. No entries needed.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | _(n/a)_ | _(n/a)_ |
