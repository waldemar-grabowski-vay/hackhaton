# Implementation Plan: Remote Host Diagnostics

**Branch**: `001-host-diagnostics` | **Date**: 2026-05-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-host-diagnostics/spec.md`

## Summary

A web app lets a non-technical operator pick a Vay-managed remote host
(vehicle or telestation, in DE or US) from a step-by-step wizard, run a
fixed set of diagnostics against it, and read back a plain-language result
split into "Working" and "Needs attention" groups. A header-toggled
Developer mode adds per-item raw output for the people building the
diagnostic app itself. The picker is fed by a local cached copy of the
existing `ree-vehicle-configs` inventory, refreshed periodically and on
demand. Hackathon-grade scope: no DB, no SSO wiring beyond a reverse-proxy
assumption, no background runs, no cancel.

Technical approach: a single Python (FastAPI) backend that owns the
inventory cache and the diagnostic executor, plus a React + TypeScript
SPA served as static assets in production from the same process. Real
host execution is gated behind a small `Executor` interface so the hackathon
demo can run against a stubbed/fixture executor when no live host is
reachable, and switch to the SSH-based executor when one is.

## Technical Context

**Language/Version**: Python 3.11+ (backend); TypeScript 5.x targeting ES2022 (frontend)
**Primary Dependencies**:
  - Backend: FastAPI, Uvicorn, Pydantic v2, PyYAML, asyncssh (executor), structlog
  - Frontend (eye-candy stack, by explicit team direction):
    - React 18 + Vite + TypeScript
    - Tailwind CSS for styling
    - shadcn/ui for accessible, polished primitives (buttons, cards, dialogs, switches)
    - Framer Motion for wizard step transitions and item-level enter/exit animations
    - lucide-react for icon set
    - Recharts (small) for the result-page status donut
    - TanStack Query for server state
    - Zod for runtime payload validation against `frontend/src/api/schemas.ts`
    - Optional, only if cheap: react-confetti or canvas-confetti on a 100% pass result
    - Theme: dark-first (with light mode via Tailwind class strategy), CSS variables for brand accent, glassmorphism on the result-summary hero card
**Storage**: Filesystem only.
  - Inventory cache: a local clone/checkout of `ree-vehicle-configs` at a configured path (default `~/.cache/vayobd/ree-vehicle-configs`).
  - Run results: most-recent run per host as a JSON file under `~/.cache/vayobd/runs/<host_id>.json`. No DB, no historical runs in v1.
**Testing**: pytest + httpx for backend; Vitest + React Testing Library for frontend; one Playwright smoke test for the P1 happy path.
**Target Platform**: Modern browsers (Chrome/Firefox/Safari/Edge current versions) ≥360 px wide; backend runs as a single Uvicorn process behind a reverse proxy in production.
**Project Type**: Web application (Option 2 — frontend + backend, single-process production).
**Performance Goals**:
  - Picker render ≤200 ms after `GET /api/inventory` (data is local).
  - Typical successful diagnostic run completes in ≤10 s (matches SC-006).
  - Inventory refresh ≤30 s end-to-end against a network mirror of the canonical repo.
**Constraints**:
  - Offline-tolerant after first sync (FR-015). The running app MUST NOT make outbound calls to the canonical inventory source on each request.
  - HTTPS in production (constitution Web App Standards) — handled by the reverse proxy, not the app process.
  - No VIN, hostname segments containing PII, or raw stderr in URLs, client-side logs, or analytics events (FR-013).
  - Strict English-only strings in v1 (FR-014). All operator-visible strings live in a single `strings.ts` so a future i18n pass is grep-able.
**Scale/Scope**:
  - ~100 hosts in scope (DE+US vehicles + telestations); ~5–15 diagnostic items per host class.
  - One operator runs one check at a time per host (FR-011); cross-operator concurrency not modelled in v1.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan satisfies it |
|---|---|
| **I. Simplicity First (NON-NEGOTIABLE)** | Single Python process serves both API and built static SPA. No DB. No background queue. No auth wiring inside the app — relies on existing reverse-proxy/SSO. No cancel button, no background runs, no historical runs. Two folders only: `backend/` and `frontend/`. |
| **II. Ship Fast** | Stack chosen for time-to-running, not theoretical purity. Hackathon-friendly defaults (no migrations, no service mesh). The diagnostic executor is interface-gated so a fixture executor can drive the demo independently of live network access. |
| **III. Non-Technical User UX (NON-NEGOTIABLE)** | Operator mode is the default and is the only mode that ships strings to the user; raw output is gated behind FR-021/FR-022 (Developer toggle). All operator-visible copy lives in one file (`frontend/src/strings.ts`) so it can be reviewed for jargon as a single PR diff. Wizard step labels and error messages are pre-written in plain English. |
| **Web App Standards** | Browser SPA, responsive Tailwind layout sized for ≥360 px, HTTPS at the proxy. No native, no IE. Vehicle identifiers stay in request bodies / server-side logs only — never in URL path segments. |
| **Development Workflow** | Critical-path code (picker → run → result) gets one Playwright smoke test in addition to backend integration tests. Mainline always demo-ready: the fixture executor lets `main` produce a working demo even when no test vehicle is reachable. |

**Result: PASS, with one logged deviation under Complexity Tracking.** The
heavyweight UI stack (shadcn/ui + Framer Motion + Recharts) is more than
the simplest viable path Principle I would otherwise mandate, but it is
accepted by explicit team direction in this session. It does not violate
Principle III: Operator-mode strings remain plain English in
`frontend/src/strings.ts` regardless of how richly they are presented.

## Project Structure

### Documentation (this feature)

```text
specs/001-host-diagnostics/
├── plan.md                  # This file
├── research.md              # Phase 0 output
├── data-model.md            # Phase 1 output
├── quickstart.md            # Phase 1 output
├── contracts/
│   └── http-api.md          # REST endpoints exposed to the SPA
└── checklists/
    └── requirements.md      # From /speckit-specify; updated through /speckit-clarify
```

### Source Code (repository root, inside `hackhaton/`)

```text
hackhaton/
├── backend/
│   ├── pyproject.toml
│   ├── src/vayobd/
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI factory; mounts API and static SPA
│   │   ├── config.py           # Settings (paths, refresh cadence, executor mode)
│   │   ├── api/
│   │   │   ├── inventory.py    # GET /api/inventory, POST /api/inventory/refresh
│   │   │   └── runs.py         # POST /api/runs, GET /api/runs/latest
│   │   ├── inventory/
│   │   │   ├── loader.py       # Parses ree-vehicle-configs YAMLs into HostInventory
│   │   │   ├── sync.py         # Local-clone refresh (git pull / rsync)
│   │   │   └── filters.py      # DE/US filter; type and city derivation from filename
│   │   ├── checks/
│   │   │   ├── catalog.py      # Per-host-class registry of DiagnosticItem definitions
│   │   │   ├── executor.py     # Executor interface; FixtureExecutor + SshExecutor impls
│   │   │   └── runner.py       # Orchestrates one DiagnosticRun
│   │   └── models.py           # Pydantic models matching data-model.md
│   └── tests/
│       ├── unit/
│       ├── integration/        # Real FastAPI client + temp inventory fixtures
│       └── smoke/              # Playwright entry-point for the P1 path
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── strings.ts          # Single file containing every operator-visible string
│   │   ├── api/                # Typed fetch wrappers + Zod schemas mirroring contracts
│   │   ├── pages/
│   │   │   ├── PickerPage.tsx          # Wizard host (Country → Type → City → Host)
│   │   │   └── RunResultPage.tsx       # Working / Needs attention groups
│   │   ├── components/
│   │   │   ├── ui/                     # shadcn/ui primitives (button, card, switch, dialog, ...)
│   │   │   ├── motion/
│   │   │   │   ├── PageTransition.tsx  # Framer Motion wrapper for wizard step changes
│   │   │   │   └── StaggeredList.tsx   # Per-item enter animation on result groups
│   │   │   ├── charts/
│   │   │   │   └── StatusDonut.tsx     # Recharts donut: working vs needs-attention
│   │   │   ├── wizard/
│   │   │   │   ├── CountryStep.tsx     # DE / US tile picker with flag iconography
│   │   │   │   ├── TypeStep.tsx        # Vehicle / Telestation card picker
│   │   │   │   ├── CityStep.tsx        # Telestation-only city picker
│   │   │   │   └── HostStep.tsx        # Final host list with friendly names
│   │   │   ├── result/
│   │   │   │   ├── ResultHero.tsx      # Glass card: host name, timestamp, donut, pass/fail headline
│   │   │   │   ├── ResultGroup.tsx     # "Working" / "Needs attention" group container
│   │   │   │   └── DiagnosticItemRow.tsx # Item row; raw_detail expand visible only in Developer mode
│   │   │   ├── chrome/
│   │   │   │   ├── AppHeader.tsx       # Brand mark + Developer mode switch (shadcn Switch)
│   │   │   │   └── InventoryFreshness.tsx # FR-018 timestamp + "Update inventory" button
│   │   │   └── states/
│   │   │       ├── RunningState.tsx    # Animated spinner + "Running checks against <host>…"
│   │   │       ├── UnreachableState.tsx
│   │   │       └── EmptyInventoryState.tsx
│   │   ├── theme/
│   │   │   ├── tailwind.config.ts      # Brand palette, dark-first tokens
│   │   │   └── globals.css             # CSS variables, glass utility classes
│   │   └── lib/
│   │       ├── developerMode.ts        # Local-storage backed toggle store (FR-021)
│   │       └── ui.ts                   # cn() helper for shadcn
│   └── tests/
└── CLAUDE.md
```

**Structure Decision**: Web application (Option 2). The two top-level
folders `backend/` and `frontend/` map directly to the two deliverables.
For production, `npm run build` writes the SPA into `backend/src/vayobd/static/`
and FastAPI serves it from there, so the deployable artefact is a single
Python process.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Heavy frontend stack (Tailwind + shadcn/ui + Framer Motion + Recharts + lucide-react) instead of the minimum-viable UI Principle I would mandate | Explicit team direction this session: "do it the most fancy and the best looking way, eyecandy as fuck." Visual polish is treated as a hackathon-demo deliverable, not as accidental complexity. | Flask + Jinja and Streamlit-style options were on the table and explicitly turned down for visual-polish reasons. The deviation is bounded: scope is ~3 screens, all libraries are mainstream, and Operator-mode UX still complies with Principle III (plain language, no jargon, single-file copy review). |
