<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:
`specs/004-ts-diag-browser/plan.md`

Companion artefacts in the same directory:
- `spec.md` — feature specification (clarified 2026-05-07; 3 questions resolved)
- `research.md` — Phase 0 decisions (ssh subprocess, WebSocket protocol, cantools DBC, errq port, concurrency, disconnect, phone layout, test strategy)
- `data-model.md` — backend in-memory types + WebSocket envelopes (Pydantic ↔ Zod) + settings deltas
- `contracts/websocket.md` — `/api/live/{host_id}/ws` message contract
- `contracts/http-api.md` — HTTP delta against 002 (new WebSocket route, `/api/health` and `/api/settings` additions)
- `quickstart.md` — fresh-clone walkthrough; live diagnostic + degraded-mode smoke tests

Background — 002 (the Real Executor backbone this builds on) lives at
`specs/002-real-executor/`. 001 (the original MVP) lives at
`specs/001-host-diagnostics/`. The desktop tool whose UX is being ported
is at `TS_diagnostic_tool/` (parallel surface, kept alive).
<!-- SPECKIT END -->
