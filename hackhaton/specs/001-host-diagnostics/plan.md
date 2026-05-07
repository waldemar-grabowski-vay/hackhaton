# Implementation Plan: Remote Host Diagnostics

**Branch**: `001-host-diagnostics` | **Date**: 2026-05-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-host-diagnostics/spec.md`

## Summary

A Vay-internal web app that lets a non-technical operator pick a remote
host (Germany-only in v1) through a short Country → Type → (City) → Host
wizard and run a one-shot diagnostic against it. Results are presented
as two named groups — **Working** and **Needs attention** — with
plain-language item names, categories, and recommended actions. A
header-level Operator/Developer mode toggle reveals raw underlying
output per item without changing routes or refetching.

Technical approach (detailed in `research.md`):

- **Backend**: FastAPI + Pydantic v2 in a single uvicorn process. Two
  interchangeable diagnostic executors (`FixtureExecutor` for dev/demo,
  `SshExecutor` for live hosts) selected by env flag. Per-`(host, operator)`
  JSON cache for persisted runs (FR-026). No database in v1.
- **Frontend**: Vite + React 18 + TypeScript SPA. Zod schemas mirror the
  Pydantic models. Single `strings.ts` module owns every operator-visible
  string (Constitution III + FR-014). The Country wizard step renders
  Germany as selectable and United States as a disabled "Coming soon"
  placeholder (Clarification 2026-05-07).
- **Inventory**: `ree-vehicle-configs` cloned to a local cache; refreshed
  at startup, on demand (FR-017), and on a periodic schedule (FR-016)
  with **exponential backoff** when refreshes fail (FR-027).
- **Auth**: corporate SSO at the upstream reverse proxy; `X-Vay-User`
  header is the operator identity used for run persistence keying.
- **Run lifecycle**: synchronous `POST /api/runs` with a server-side
  **30 s hard timeout** (FR-025). No queueing, no streaming, no cancel
  (FR-024).
- **Result view**: always opens blank on host entry; the operator must
  trigger a fresh run to see results (FR-028). Persisted runs are
  backend-only record-keeping in v1.

## Technical Context

**Language/Version**: Python 3.11+ (backend); TypeScript 5.x on Node 20+ (frontend)
**Primary Dependencies**: FastAPI, Pydantic v2, `asyncssh`, uvicorn (backend); React 18, Vite, Zod, TanStack Query, Playwright (frontend)
**Storage**: Local filesystem cache under `~/.cache/vayobd/` — git checkout of `ree-vehicle-configs`, an `inventory.meta.json`, and a per-operator `runs/<operator>/<host_id>.json` tree. No database.
**Testing**: pytest (backend unit + integration); Vitest (frontend unit); Playwright (E2E smoke against fixture executor)
**Target Platform**: Backend — Linux server (containerised). Frontend — current Chrome / Firefox / Safari / Edge per Constitution Web App Standards.
**Project Type**: Web application — separate `backend/` and `frontend/` directories in a single repo.
**Performance Goals**: SC-006 — typical successful run completes and renders within 10 s. SC-008 — wizard completable in under 10 s. Picker first paint from cache < 500 ms.
**Constraints**: 30 s hard timeout per run (FR-025); ≥360 px viewport (FR-012); no VIN/PII in URLs / client logs / analytics (FR-013, Constitution Web App Standards); offline-tolerant of upstream inventory source (FR-015); per-operator persistence + visibility scope (FR-026).
**Scale/Scope**: Germany-only inventory in v1 — on the order of dozens of hosts. Single-process FastAPI backend. One organisation, internal users.

## Constitution Check

*Gates determined from `.specify/memory/constitution.md` v1.0.0. Re-evaluated post-Phase 1 design — see end of this section.*

| Principle / Standard | Evaluation | Status |
|---|---|---|
| **I. Simplicity First** (NON-NEGOTIABLE) | One backend process, no DB, no message queue, no streaming, no cancel, no plugin model, no roles. Two executors behind a single interface (fixture vs. ssh) is the minimum to demo without a live host. Inventory is a git checkout — same workflow the team already uses manually. | **PASS** |
| **II. Ship Fast** | Fixture executor lets the entire end-to-end flow be demoed without depending on hardware. Mainline deployability is preserved by `VAYOBD_EXECUTOR=fixture` as the default in dev/CI. Quickstart shows a working build in <10 commands from a fresh clone. | **PASS** |
| **III. Non-Technical User UX** (NON-NEGOTIABLE) | Operator-visible strings centralised in `frontend/src/strings.ts` — single PR-reviewable surface for jargon (R6). Every error item carries a `recommended_action_key` (FR-005, enforced as a Pydantic validation rule in `data-model.md`). Defaults: Operator mode on first load (FR-021); blank result view starts with a single clear CTA (FR-028). Raw output (CAN trace, exit codes, stderr) is gated behind the Developer toggle and never appears in Operator mode (FR-022, audited by SC-003). | **PASS** |
| **Web App Standards — Browser-only** | SPA delivered to the browser; backend serves the built `dist/` in production. No native binaries. | **PASS** |
| **Web App Standards — Browser support** | React 18 + Vite output targets modern evergreen browsers. No IE shims. | **PASS** |
| **Web App Standards — Responsive ≥360 px** | FR-012 + SC-004 explicit; covered by the Playwright E2E smoke at the 360 px viewport size. | **PASS** |
| **Web App Standards — HTTPS** | Production deployment behind the SSO-terminating reverse proxy, which already enforces HTTPS. App emits no plaintext-only assumptions. | **PASS** |
| **Web App Standards — No VIN/PII in client logs/analytics/URLs** | FR-013 explicit. Backend never returns `address` or `source_file` to the frontend (`data-model.md`). `host_id` is a path-safe slug derived from filename, not a VIN. The `X-Vay-User` identity is server-side only — never returned in API responses. No client-side analytics in v1. | **PASS** |
| **Workflow — change review, smoke test on critical path** | Playwright E2E covers the P1 happy path + Developer toggle round-trip; documented in `quickstart.md` step 7 and the PR template. | **PASS** |
| **Workflow — demo readiness** | Fixture executor IS the demo path. Mainline keeps `VAYOBD_EXECUTOR=fixture` as default; switching to live SSH is an env flag, not a code change. | **PASS** |

**Initial gate result**: PASS — no Complexity Tracking entries needed.

**Post-Phase 1 re-evaluation**: PASS — the Phase 1 artefacts (data-model
shapes, HTTP contract, quickstart) introduce no new dependencies,
abstractions, or shared-state concerns beyond what the principles already
sanction. The per-operator persistence (FR-026) adds one path-segment of
keying to the on-disk JSON cache; it does not introduce a database, an
auth library, or an authorization model.

## Project Structure

### Documentation (this feature)

```text
specs/001-host-diagnostics/
├── plan.md              # This file
├── spec.md              # Feature specification (with 2026-05-07 clarifications)
├── research.md          # Phase 0 decisions
├── data-model.md        # Pydantic / Zod entity shapes
├── contracts/
│   └── http-api.md      # SPA ↔ FastAPI REST contract
├── quickstart.md        # Fresh-clone walkthrough using FixtureExecutor
├── checklists/          # Spec/plan checklists
└── tasks.md             # /speckit-tasks output (regenerate after this plan)
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml
├── src/vayobd/
│   ├── app.py                  # FastAPI entrypoint, route registration
│   ├── api/
│   │   ├── inventory.py        # GET /api/inventory, POST /api/inventory/refresh
│   │   └── runs.py             # POST /api/runs (synchronous, 30s timeout)
│   ├── auth.py                 # X-Vay-User header dependency
│   ├── checks/
│   │   ├── catalog.py          # HostClass → list[CheckSpec], DE-only catalog
│   │   ├── executor.py         # Executor interface + Fixture + Ssh impls
│   │   └── runner.py           # one run: lock, execute, scrub, persist
│   ├── inventory/
│   │   ├── loader.py           # cached repo → list[Host], filters non-de
│   │   └── sync.py             # startup + scheduled + manual refresh, exp backoff
│   ├── models.py               # Pydantic v2 models (mirrors data-model.md)
│   └── persistence/
│       └── runs.py             # per-(operator, host) JSON cache I/O
└── tests/
    ├── unit/
    ├── integration/            # ASGI tests against a real inventory cache fixture
    ├── e2e_fixtures/           # Per-host canned run YAMLs for FixtureExecutor
    └── fixtures/

frontend/
├── package.json
├── vite.config.ts              # Proxies /api/* to :8000 in dev
├── src/
│   ├── App.tsx
│   ├── api/
│   │   ├── client.ts           # fetch wrapper
│   │   └── schemas.ts          # Zod, mirrors data-model.md
│   ├── components/
│   │   ├── DeveloperToggle.tsx
│   │   ├── ItemRow.tsx
│   │   └── InventoryRefreshBanner.tsx   # FR-027 surfaced after N failures
│   ├── pages/
│   │   ├── Wizard.tsx          # 4-step picker; US tile disabled (FR-001a step 1)
│   │   └── Result.tsx          # Blank-on-entry; CTA → POST /api/runs (FR-028)
│   ├── state/
│   │   └── mode.ts             # Operator/Developer toggle (header-level)
│   └── strings.ts              # All operator-visible English copy (R6)
└── tests/
    ├── unit/
    └── e2e/
        └── happy-path.spec.ts  # Playwright, FixtureExecutor, 360px viewport
```

**Structure Decision**: Web application (Constitution Web App Standards
applies). Backend and frontend are separate top-level directories in the
same repo so the demo can be a single git clone + two `npm`/`pip` commands
per the quickstart. The backend serves the built frontend in production
(single-process serve) and proxies in dev (two-process Vite).

## Complexity Tracking

No Constitution gate requires justification — table intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | | |
