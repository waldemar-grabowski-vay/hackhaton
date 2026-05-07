# Implementation Plan: Real Diagnostic Engine via ree-debug-tui

**Branch**: `002-real-executor` | **Date**: 2026-05-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-real-executor/spec.md`

## Summary

Replace the FixtureExecutor-only / SshExecutor-stub diagnostic stack
inherited from `001-host-diagnostics` with a real engine ported from
`~/GitHub/ree-debug-tui` into a new Rust **Cargo workspace under
`engine/` at the monorepo root**, and rewire the FastAPI backend to
shell out to a JSON-emitting CLI binary (`ree-debug-cli`) for every
`POST /api/runs`.

Three Rust crates inside the workspace:
- `ree-debug-engine` (library) — the entire diagnostic surface
  (probes, decoders, inventory loader, SSH ControlMaster fan-out)
  ported from the historical repo. No I/O concerns, no rendering;
  returns structured Rust types via `serde`-derivable structs.
- `ree-debug-tui` (binary) — the existing terminal UI restructured to
  consume `ree-debug-engine`. Mutating actions (`b`/`d`) live here
  only.
- `ree-debug-cli` (binary) — the new non-interactive frontend. Reads
  `--host <id> --inventory <path>`, calls into `ree-debug-engine`,
  serialises the engine result tree to stdout as JSON, exits zero
  on engine completion (irrespective of per-check pass/fail).

Python-side changes (small, mostly contract-driven):
- New `ReeCliExecutor` alongside the retained `FixtureExecutor`;
  `SshExecutor` deleted with no callers.
- `DiagnosticItem.status` extended to `working` / `warning` / `error`
  (FR-004a).
- `CheckCategory` extended to five values (FR-006).
- Inventory loader rewritten: read `org/vay/inventory.yaml` from the
  configured local-checkout path on every `GET /api/inventory`. The
  walker, periodic refresh, exp-backoff banner, and "Update
  inventory" route from 001 are all retired.
- New first-launch setup-card flow (User Stories 2 + 3).
- `engine_unavailable` / `engine_incompatible` error envelope and
  startup `--version` self-check (FR-007 + FR-003a).

Frontend changes:
- New `warning` status rendering in the result view (amber tint,
  under "Needs attention" alongside red `error` items).
- New category badges for `software` and `calibration`.
- New `InventorySetupCard` component and surrounding wiring.
- Existing `InventoryRefreshBanner` retired (no refresh in this
  flow).
- Header "engine mode" badge (`live` vs `fixture` per FR-007's
  visibility rule).

## Technical Context

**Language/Version**:
- Rust 2021 edition, MSRV ≥ 1.74 (matches the existing
  `ree-debug-tui` `ratatui 0.29` / `crossterm 0.28` lower bound and
  `tokio 1.x`).
- Python 3.11+ (Pydantic v2, FastAPI, `asyncio.subprocess` —
  unchanged from 001).
- TypeScript 5.x on Node 20+ (unchanged from 001).

**Primary Dependencies**:
- `engine/` — `tokio`, `ratatui` (TUI binary only), `crossterm` (TUI
  binary only), `serde` + `serde_yaml` (engine), `serde_json` (CLI
  binary only), `anyhow`/`thiserror`, `clap` (CLI binary only). All
  ported from the existing `ree-debug-tui` `Cargo.toml`.
- `backend/` — adds nothing new; uses stdlib `asyncio.subprocess` to
  invoke the CLI binary. (No PyO3, no Rust extension wheels.)
- `frontend/` — no new deps; relies on existing shadcn/Tailwind/Zod.

**Storage**: Same as 001 — local FS only. Adds:
- `engine/target/release/ree-debug-cli` (Cargo build output).
- `~/.config/vayobd/settings.toml` (operator's persisted inventory
  path, FR-009 — FR-012).
The `runs/<operator-slug>/<host_id>.json` cache from 001 stays.

**Testing**:
- Rust: `cargo test --workspace`, plus a small set of golden-output
  fixtures for `ree-debug-cli` (snapshot-style JSON comparison).
- Python: pytest (existing), with a new `test_ree_cli_executor.py`
  exercising the subprocess invocation against a fake CLI binary
  fixture so the suite doesn't depend on network/SSH.
- Frontend: the existing Playwright smoke (`p1.spec.ts`,
  `p2.spec.ts`) extended with a `warning` row assertion and a
  setup-card walkthrough.

**Target Platform**:
- Backend + engine workspace: Linux / macOS. Windows operators run
  inside WSL2 (matches `ree-debug-tui`'s existing constraint —
  OpenSSH ControlMaster is not available on Win32-OpenSSH).
- Frontend: modern Chrome / Firefox / Safari / Edge per the
  Constitution Web App Standards (no change).

**Project Type**: Web application + CLI tooling (a Rust workspace
sits beside the existing `backend/` + `frontend/` roots).

**Performance Goals**: SC-001 — engine run + result render completes
within FR-008's 30 s ceiling for ≥95% of attempts on a healthy
testbed; SC-002 — first-time inventory setup card → wizard appearance
in under 30 s; setup-card validation latency < 500 ms (synchronous
disk reads only, no network).

**Constraints**:
- Engine library MUST stay pure (no `println!`, no `stdout` writes;
  rendering happens in the binary crates).
- `ree-debug-cli` MUST keep stdout reserved for the JSON document;
  logs go to stderr.
- Mutating actions (`b`, `d` keys) MUST live only in the
  `ree-debug-tui` binary. The engine library MUST NOT expose any
  function that mutates host state.
- Engine subprocess respects FR-008's 30 s ceiling end-to-end with
  SIGTERM-then-SIGKILL on expiry.
- All 001 carried-forward constraints (FR-013 PII scrub, FR-026
  per-operator persistence, FR-028 blank-on-entry) MUST remain
  enforced.

**Scale/Scope**: Inherits from 001 — order-of-dozens DE hosts,
single-process FastAPI per operator's machine, single in-flight run
per host. Adds: 20+ checks per host class through the engine (vs.
6/3 today), 3-status × 5-category × ~25-item operator-visible
matrix.

## Constitution Check

*Gates determined from `.specify/memory/constitution.md` v1.0.0. Re-evaluated post-Phase 1 design — see end of this section.*

| Principle / Standard | Evaluation | Status |
|---|---|---|
| **I. Simplicity First** (NON-NEGOTIABLE) | Adding a Rust workspace is a real complexity bump — but it replaces a stub (`SshExecutor`) and a fixture-only happy path with the actual diagnostic IP. The alternative is to port 3 k LOC of working Rust to Python (rejected in clarify), so the workspace is the *simplest* real-engine path. No new persistence layer, no new cross-process IPC beyond stdin/stdout JSON, no PyO3, no Rust extension wheels. The Cargo workspace is a refactor of code that already works, not a greenfield invention. | **PASS** |
| **II. Ship Fast** | `ree-debug-cli` is a thin frontend on a library that already exists; the Cargo refactor is mechanical (move modules, change crate boundaries). FixtureExecutor stays for the demo path. The change can land incrementally: (a) workspace skeleton, (b) library port, (c) CLI binary, (d) Python `ReeCliExecutor`. Each lands with the existing Playwright smoke green via `VAYOBD_EXECUTOR=fixture`, and only the final wire-up (Python ↔ Rust binary) requires the full stack co-running. | **PASS** |
| **III. Non-Technical User UX** (NON-NEGOTIABLE) | The catalog grows from ~9 items to ~25; every new item needs an operator-visible name, category, and (for `error`/`warning`) recommended action. SC-003 (jargon audit on at least 10 distinct error scenarios) gets harder. Mitigation: the catalog table is in `frontend/src/strings.ts` (single PR-reviewable surface, R6 from 001), and the FR-006 5-category palette + FR-004a 3-status enum keeps the operator-visible vocabulary stable. The Rust side never ships English copy. The new `warning` state preserves engineering signal without making "Working" mean "actually working but maybe not". | **PASS** |
| **Web App Standards — Browser-only** | No change. | **PASS** |
| **Web App Standards — Browser support** | No change. | **PASS** |
| **Web App Standards — Responsive ≥360 px** | The setup card and the new amber `warning` row both need to render readably at 360 px — covered in the Phase 1 design and asserted by the existing Playwright viewport. | **PASS** |
| **Web App Standards — HTTPS** | No change. | **PASS** |
| **Web App Standards — No VIN/PII in client logs/analytics/URLs** | The PII scrubber from 001 (`backend/src/vayobd/checks/runner.py::scrub_raw_detail`) MUST run over `raw_detail` produced by the engine before persistence and before the response goes out. Engine library MUST NOT include VIN-shaped strings in raw output. Tested by FR-018 / SC-003. | **PASS (with covering test required)** |
| **Workflow — change review, smoke test on critical path** | Cargo workspace adds a Rust CI step (`cargo test --workspace`). Existing Python pytest + Playwright smoke remain authoritative for the user flow. The Phase 7-style re-alignment pattern from 001 isn't needed — this is a fresh feature on a fresh branch. | **PASS** |
| **Workflow — demo readiness** | Mainline keeps `VAYOBD_EXECUTOR=fixture` as the default in dev/CI. The demo build path is unchanged from 001 (FixtureExecutor, canned YAML). The live engine path is opt-in via `VAYOBD_EXECUTOR=ree`. A failed engine build cannot break the demo. | **PASS** |

**Initial gate result**: PASS. No Complexity Tracking entries needed
— the workspace addition is justified by the rejected alternative
(full Python port) being strictly worse on every Constitution
principle.

**Post-Phase 1 re-evaluation**: PASS. Phase 1 artefacts (engine
workspace structure, JSON contract, settings TOML shape, expanded
catalog) introduce no new persistence engines, no new wire protocols
beyond stdin/stdout JSON, and no abstractions the engine library can
sidestep. The only Constitution-relevant addition is the new
strings.ts entries (~25 new items × 5 categories) — handled by
Constitution III's "single PR-reviewable file" pattern from R6 of
001.

## Project Structure

### Documentation (this feature)

```text
specs/002-real-executor/
├── plan.md              # This file
├── spec.md              # Feature specification (clarified 2026-05-07)
├── research.md          # Phase 0 decisions
├── data-model.md        # Rust types ↔ Pydantic models ↔ Zod schemas
├── contracts/
│   ├── engine-cli.md    # ree-debug-cli CLI + JSON contract
│   └── http-api.md      # Delta from 001's HTTP contract
├── quickstart.md        # Fresh-clone walkthrough — build engine, run app
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks output (next phase)
```

### Source Code (repository root)

The new `engine/` workspace is the headline addition. Backend and
frontend trees are mostly unchanged from 001 — call-outs below are
the diff.

```text
engine/                          # NEW — Rust Cargo workspace
├── Cargo.toml                   # workspace root, members = the three crates
├── ree-debug-engine/            # library crate (no I/O)
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs               # public surface: run_checks(host, inventory) -> EngineReport
│       ├── inventory.rs         # ported from ree-debug-tui/src/inventory.rs
│       ├── ssh.rs               # ported (ControlMaster fan-out, async)
│       ├── checks/
│       │   ├── mod.rs           # ported
│       │   ├── cameras.rs
│       │   ├── connectivity.rs
│       │   ├── decode.rs        # CAN DBC decoders
│       │   ├── reecu.rs
│       │   └── usb.rs
│       ├── manifest.rs          # ported (vDrive manifest drift)
│       ├── ping.rs              # ported (parallel host ping)
│       ├── session_init.rs      # ported
│       └── types.rs             # serde-derivable: Host, Check, Status, Severity, EngineReport
├── ree-debug-tui/               # binary crate
│   ├── Cargo.toml               # depends on ree-debug-engine
│   └── src/
│       ├── main.rs              # ported (entrypoint, signal wiring)
│       ├── app.rs               # ported (state machine; mutating actions live here)
│       ├── repair.rs            # ported (the b/d key paths)
│       └── ui/
│           ├── mod.rs
│           ├── dashboard.rs
│           ├── guides.rs
│           ├── menu.rs
│           └── pick.rs
└── ree-debug-cli/               # binary crate (NEW — no port source)
    ├── Cargo.toml               # depends on ree-debug-engine + clap + serde_json
    └── src/
        └── main.rs              # parse args → call engine → serialise → exit

backend/                         # delta only
└── src/vayobd/
    ├── checks/
    │   └── ree_cli.py           # NEW — ReeCliExecutor (subprocess + JSON parse)
    ├── settings_file.py         # NEW — read/write ~/.config/vayobd/settings.toml
    ├── api/
    │   ├── inventory.py         # rewritten — reads org/vay/inventory.yaml per request
    │   └── settings.py          # NEW — GET/POST /api/settings/inventory-path
    ├── inventory/
    │   ├── loader.py            # rewritten — single-file YAML, no walker
    │   ├── sync.py              # DELETED — no git fetch any more
    │   └── scheduler.py         # DELETED — no periodic refresh any more
    ├── checks/
    │   └── executor.py          # SshExecutor stub deleted; FixtureExecutor kept
    └── models.py                # extend ItemStatus + CheckCategory enums

frontend/                        # delta only
└── src/
    ├── pages/
    │   └── PickerPage.tsx       # gates wizard on settings; opens setup card if missing
    ├── components/
    │   ├── chrome/
    │   │   ├── InventoryRefreshBanner.tsx  # DELETED
    │   │   ├── EngineModeBadge.tsx         # NEW — "live" vs "fixture" header pill
    │   │   └── InventoryFreshness.tsx      # rewritten — no more last-refreshed timestamp
    │   ├── settings/
    │   │   └── InventorySetupCard.tsx      # NEW
    │   └── result/
    │       └── DiagnosticItemRow.tsx       # extended — amber `warning` tint
    ├── api/
    │   ├── schemas.ts                      # +`warning`, +`software`, +`calibration`
    │   └── settings.ts                     # NEW — settings GET/POST hooks
    └── strings.ts                          # ~25 new item entries; new categories
```

**Structure Decision**: Web application with a sibling Rust workspace
(`engine/`). The three trees (`backend/`, `frontend/`, `engine/`) all
ship from the same git SHA — that's the entire versioning story for
the Rust ↔ Python contract per FR-003a. CI cuts a single artefact
(per-platform tarball) containing the Python wheels + the built
`ree-debug-cli` + the built SPA `dist/`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | Cargo workspace is the simplest path to the spec'd outcome — see Constitution Check above for why the rejected alternative (Python port of 3 k LOC of testbed-specific Rust) is strictly worse against every principle. | |
