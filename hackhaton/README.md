# VayOBD — Remote Host Diagnostics

A web app that lets a non-technical operator pick a Vay-managed remote host
(vehicle or telestation) and run a fixed set of diagnostics against it,
splitting the result into "Working" and "Needs attention" groups.

For a fresh-clone walkthrough (one-time setup, dev mode, fixture executor,
Playwright smoke), see:

- **[`specs/001-host-diagnostics/quickstart.md`](specs/001-host-diagnostics/quickstart.md)** — primary getting-started doc

Companion artefacts in `specs/001-host-diagnostics/`:

- `spec.md` — feature specification
- `plan.md` — implementation plan and stack
- `tasks.md` — task breakdown and execution order
- `data-model.md` — Pydantic / Zod schemas
- `contracts/http-api.md` — REST contract between SPA and FastAPI
