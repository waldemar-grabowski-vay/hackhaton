<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/008-restore-host-checks-fix-live/plan.md`

Companion artefacts in the same directory:
- `spec.md` — feature specification (clarified 2026-05-11; 5 questions resolved: data-source split between REECU pipeline and ree-debug-cli, Live Diagnostic failure-mode diagnosed at plan time, restoration via `git checkout HEAD --`, one-shot REECU capture per page mount, full pre-007 catalog coverage)
- `research.md` — Phase 0 decisions (LD failure-mode spike: SPA mount path is the likely root cause; DBC glob tightening for `application_protocol.dbc`; errq degraded mode surfacing; restoration mechanics; REECU 4-second capture window; strings.ts hand-merge; `VersionCache[HostDetailResponse]` reuse)
- `data-model.md` — restored `DiagnosticItem` / `DiagnosticRun` / `CheckCategory` / `RunOutcome` / `ItemStatus` (from pre-007); new `HostDetailResponse` composition envelope; 007's `VersionField` / `HostVersions` kept verbatim
- `contracts/http-api.md` — unified `GET /api/host/{id}/versions` (versions + restored run); restored `POST /api/runs` and `GET /api/runs/{id}`; caching + error semantics
- `contracts/reecu-pipeline.md` — one-shot REECU capture (4 s window via `vayobd.live.session`, signal extraction, error semantics)
- `contracts/strings-merge.md` — hand-merge guide for `frontend/src/strings.ts` (which blocks restore from HEAD; which to keep from 007)
- `quickstart.md` — 7-step acceptance walkthrough covering all four user stories against a real testbed, with spec scenario ↔ step mapping

Background — earlier features under `specs/001-…` through `specs/007-…` remain
the source of truth for everything 008 builds on. 007 is the immediate
predecessor (and the regression source); 008 restores what 007 over-removed
without sacrificing 007's wins (per-field verdict pills, TTL cache, refresh
button, dual TS_diag entry points, plain-language copy). 004 ships the
TS_diag `/live` surface 008's REECU pipeline reuses for one-shot captures.
005's plain-language / scannable principles carry forward in the restored
result-page wording. 006's .deb (with the bundled-Python python-build-standalone
fix) ships the runtime 008 is acceptance-tested on. The desktop tool whose
UX is being ported is at `TS_diagnostic_tool/`.
<!-- SPECKIT END -->
