<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/008-restore-host-checks-fix-live/plan.md`

Companion artefacts in the same directory:
- `spec.md` — feature specification (clarified across 2026-05-11 and 2026-05-12; 10 questions resolved across two clarification sessions: data-source split, LD failure-mode diagnosis, restoration mechanics, REECU one-shot capture, pre-007 catalog coverage, Ezequiel frontend cherry-pick, 3-way merge precedence, repair-guide library scope, tiered restoration sources, 005→009 spec rename, Wilhelm VE state-signal port, VE errq via same `ree-reecu` clone, dual-host quickstart, TS/VE inventory pill)
- `research.md` — Phase 0 decisions: original §1–§7 (LD failure-mode spike, restoration mechanics, REECU capture window, strings.ts hand-merge, runs router re-registration, VersionCache reuse, session coexistence) + 2026-05-12 §8–§12 (Ezequiel source tier map, library chrome entry point, VE state-signal port, VE errq subpath resolution, 005→009 rename)
- `data-model.md` — restored `DiagnosticItem` / `DiagnosticRun` / `CheckCategory` / `RunOutcome` / `ItemStatus` (pre-007), new `HostDetailResponse`, 007's `VersionField` / `HostVersions` kept; §13 (2026-05-12) covers host-type extensions
- `contracts/http-api.md` — unified `GET /api/host/{id}/versions` (now host-type aware); restored `POST /api/runs` and `GET /api/runs/{id}`
- `contracts/reecu-pipeline.md` — one-shot REECU capture (4 s window via `vayobd.live.session`), §8a covers VE-host signal allowlist + errq resolver pass-through
- `contracts/strings-merge.md` — §1–§8 original 2-way merge; §9 (2026-05-12) extends to 3-way merge (post-007 HEAD ↔ Ezequiel ↔ pre-007 HEAD~N); §9d covers `connectorLocations.ts` / `connectorSpecs.ts` / `guides.ts` companion files
- `contracts/ezequiel-cherry-pick.md` — exact source map: tier A (frontend from `origin/005-ve-harness-repair-guide`), tier B (backend from local `01d3979`), tier C (engine Rust from `01d3979`); tier F lists explicit exclusions
- `contracts/ve-signals.md` — VE state-signal allowlist sourced from Wilhelm's `TS_diagnostic_tool/config.py::TS_STATE_SIGNALS`; host-type-agnostic decode pipeline
- `contracts/ve-errq.md` — VE errq CSV subpath resolution inside the existing `ree-reecu` clone; degraded-mode fallback identical to TS
- `quickstart.md` — 10-step walkthrough (8 in 2026-05-11; +2 in 2026-05-12 for VE-host scenarios and library acceptance); spec scenario ↔ step mapping including SC-008, SC-009, VE-SIG-*, VE-ERRQ-*

Background — earlier features under `specs/001-…` through `specs/007-…` remain
the source of truth for everything 008 builds on. 007 is the immediate
predecessor (and the regression source); 008 restores what 007 over-removed,
absorbs Ezequiel's `origin/005-ve-harness-repair-guide` frontend cherry-pick
(documented under `specs/009-ve-harness-repair-guide/` after rename),
and ports the VE-channel state signals from Wilhelm's already-merged
desktop tool (`TS_diagnostic_tool/`) onto the web app's `/live` surface —
all without sacrificing 007's wins (per-field verdict pills, TTL cache,
refresh button, dual TS_diag entry points, plain-language copy). 004
ships the TS_diag `/live` surface 008's REECU pipeline reuses for one-shot
captures. 005's plain-language / scannable principles carry forward in the
restored result-page wording. 006's .deb (with the bundled-Python
python-build-standalone fix) ships the runtime 008 is acceptance-tested
on — and remains unmodified by 008 (VE errq reads from the same local
`ree-reecu` clone the 006 .deb already expects).
<!-- SPECKIT END -->
