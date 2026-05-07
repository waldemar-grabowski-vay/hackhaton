---
description: "Task breakdown for Real Diagnostic Engine via ree-debug-tui (feature 002-real-executor)"
---

# Tasks: Real Diagnostic Engine via ree-debug-tui

**Input**: Design documents from `specs/002-real-executor/`
**Prerequisites**: `plan.md`, `spec.md` (clarified 2026-05-07), `research.md`, `data-model.md`, `contracts/{engine-cli,http-api}.md`, `quickstart.md`

**Tests**: Targeted only — Rust workspace `cargo test`, backend pytest unit + integration, frontend Playwright smoke. Constitution-mandated minimum, not full TDD.

**Organization**: Tasks are grouped by user story (US1, US2, US3 from `spec.md`). Each story phase is independently testable per the spec's "Independent Test" sections.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel — different files, no dependencies on incomplete tasks.
- **[Story]**: User-story phases only — `[US1]`, `[US2]`, `[US3]`.
- File paths are repository-relative; the project root for code is `hackhaton/`.

## Path Conventions (per `plan.md`)

- Engine workspace: `hackhaton/engine/{ree-debug-engine,ree-debug-tui,ree-debug-cli}/...`
- Backend: `hackhaton/backend/src/vayobd/...` and `hackhaton/backend/tests/...`
- Frontend: `hackhaton/frontend/src/...` and `hackhaton/frontend/tests/...`
- Specs: `hackhaton/specs/002-real-executor/...`
- Source repo we're porting from: `~/GitHub/ree-debug-tui` (read-only reference)

---

## Phase 1: Setup (Engine Workspace Skeleton)

**Purpose**: Stand up the empty Cargo workspace and the three crates so CI can build green before any Rust diagnostic code is moved. Each crate has a stub that compiles; nothing yet does real work.

- [ ] T001 Create the Cargo workspace at `hackhaton/engine/Cargo.toml` declaring `members = ["ree-debug-engine", "ree-debug-tui", "ree-debug-cli"]` plus the `[profile.release] lto = "thin"; strip = true` settings carried over from `~/GitHub/ree-debug-tui/Cargo.toml`
- [ ] T002 [P] Create `hackhaton/engine/ree-debug-engine/Cargo.toml` (library crate, `[lib] name = "ree_debug_engine"`) plus a stub `hackhaton/engine/ree-debug-engine/src/lib.rs` that exposes a placeholder `pub async fn run_checks(...) -> Result<EngineReport, EngineError>` returning a hardcoded empty report — enough to compile against
- [ ] T003 [P] Create `hackhaton/engine/ree-debug-tui/Cargo.toml` (binary crate, `[[bin]] name = "ree-debug-tui"`) depending on `ree-debug-engine` plus a stub `hackhaton/engine/ree-debug-tui/src/main.rs` that prints "stub" and exits 0
- [ ] T004 [P] Create `hackhaton/engine/ree-debug-cli/Cargo.toml` (binary crate, `[[bin]] name = "ree-debug-cli"`) depending on `ree-debug-engine`, `clap`, `serde_json`, `tokio`, plus a stub `hackhaton/engine/ree-debug-cli/src/main.rs` that prints `{"schema":"ree-debug-engine","version":"<sha>","checks":[]}` and exits 0
- [ ] T005 [P] Add `hackhaton/engine/ree-debug-cli/build.rs` that resolves the workspace git SHA via `git rev-parse --short HEAD` and writes it into a `cargo:rustc-env=REE_DEBUG_VERSION=<sha>` directive (used by `--version` per FR-003a)
- [ ] T006 Verify workspace bootstrap: `cd hackhaton/engine && cargo build --release --workspace && cargo test --workspace` are both green; commit the skeleton before any port work

**Checkpoint**: Engine workspace builds and tests cleanly with stub implementations. CI is green; nothing user-visible has changed yet.

---

## Phase 2: Foundational (Cross-Story Plumbing)

**Purpose**: Establish the data-model extensions, settings persistence layer, and removal of retired 001 surfaces. **No user-story work begins until this phase is complete.**

### Backend models + settings

- [ ] T007 [P] Extend `ItemStatus` enum (add `WARNING`), `CheckCategory` enum (add `SOFTWARE` + `CALIBRATION`), and `DiagnosticItem` validator (require `recommended_action_key` for both `WARNING` and `ERROR` per FR-004b) in `hackhaton/backend/src/vayobd/models.py`
- [ ] T008 [P] Add `EngineStatus` (Pass/Warn/Fail), `EngineCheckEntry`, `EngineReport`, `EngineErrorKind`, `EngineError` Pydantic v2 models in `hackhaton/backend/src/vayobd/models.py` mirroring the Rust types from `data-model.md` Layer 1
- [ ] T009 [P] Add `InventorySettings` (with `_expand_and_validate` `field_validator`) and `AppSettings` Pydantic models in `hackhaton/backend/src/vayobd/models.py` per `data-model.md` Layer 2
- [ ] T010 Implement `hackhaton/backend/src/vayobd/settings_file.py`: read TOML from `${XDG_CONFIG_HOME:-${HOME}/.config}/vayobd/settings.toml` via `tomllib`; write via a small custom serialiser; return `AppSettings` with `inventory=None` when the file is absent
- [ ] T011 Slim `InventoryMeta` in `hackhaton/backend/src/vayobd/models.py`: remove `last_refresh_attempted_at` and `consecutive_failed_refreshes` (FR-013a — caching layer retired); `host_count` + `last_read_at` + `source_path` only

### Backend retirements (delete 001 surfaces no longer used)

- [ ] T012 Delete `SshExecutor` class and its imports from `hackhaton/backend/src/vayobd/checks/executor.py`; `FixtureExecutor` stays (FR-001 — `SshExecutor` retired)
- [ ] T013 [P] Delete `hackhaton/backend/src/vayobd/inventory/sync.py` and `hackhaton/backend/src/vayobd/inventory/scheduler.py`; remove their imports from `hackhaton/backend/src/vayobd/app.py`'s lifespan; **also delete `hackhaton/backend/tests/unit/test_inventory_scheduler.py`** (and any other test file importing from `vayobd.inventory.{sync,scheduler}` — confirmed empty by `grep -rlE 'from vayobd\.inventory\.(sync|scheduler)' backend/tests/` before merging) so pytest collection stays green after the modules are gone
- [ ] T014 [P] Delete the `POST /api/inventory/refresh` route from `hackhaton/backend/src/vayobd/api/inventory.py`; delete the `useRefreshInventory` hook from `hackhaton/frontend/src/api/inventory.ts`
- [ ] T015 [P] Delete `hackhaton/frontend/src/components/chrome/InventoryRefreshBanner.tsx` and remove its import + render site from `hackhaton/frontend/src/pages/PickerPage.tsx`
- [ ] T016 [P] Backend: drop the `consecutive_failed_refreshes`-related settings keys from `hackhaton/backend/src/vayobd/config.py` (`refresh_failure_warning_threshold`, `refresh_backoff_base_seconds`, etc.) and the corresponding test fixtures

### Engine library types

- [ ] T017 [P] Define the public `serde`-derivable types in `hackhaton/engine/ree-debug-engine/src/types.rs` per `data-model.md` Layer 1: `HostType`, `CheckStatus`, `RunOutcome`, `CheckEntry`, `EngineReport`, `EngineErrorKind`, `EngineError`. Add `serde` + `serde_yaml` + `serde_json` derives where shown
- [ ] T018 [P] Re-export the public types from `hackhaton/engine/ree-debug-engine/src/lib.rs` (`pub use types::*;`) so the binaries can `use ree_debug_engine::EngineReport`

### Frontend Zod + delete refresh hooks

- [ ] T019 [P] Extend `itemStatusSchema` (add `warning`), `checkCategorySchema` (add `software` + `calibration`), and `diagnosticItemSchema` (`recommended_action_key` required for `warning` too) in `hackhaton/frontend/src/api/schemas.ts` per `data-model.md` Layer 3
- [ ] T020 [P] Slim `inventoryMetaSchema` to drop `last_refresh_attempted_at` + `consecutive_failed_refreshes` in `hackhaton/frontend/src/api/schemas.ts`; replace with `last_read_at` + `source_path`
- [ ] T021 [P] Add `inventorySettingsSchema`, `appSettingsSchema`, `settingsErrorSchema` in `hackhaton/frontend/src/api/schemas.ts`

**Checkpoint**: Backend + frontend compile clean with the new model shapes; the workspace stub is in place; the Phase 1 retirement deletes have shed every surface no longer needed. User-story phases can now begin in parallel (engine port + frontend setup-card + Python `ReeCliExecutor` are mostly independent).

---

## Phase 3: User Story 1 — Run a check against a real testbed (Priority: P1) 🎯 MVP

**Goal**: With `VAYOBD_EXECUTOR=ree`, the operator picks a host through the wizard, clicks Run check, and sees real `ree-debug-cli` output rendered as Working / Needs attention groups (warning amber + error red), with every check the engine ran enumerated by name and category.

**Independent Test**: Build the engine workspace, configure a settings.toml pointing at the operator's `ree-vehicle-configs` clone, run the backend with `VAYOBD_EXECUTOR=ree` against a reachable DE testbed, walk the wizard, click Run check. Compare the SPA's rendered checks 1:1 with what `cargo run --release -p ree-debug-tui` shows in the TUI for the same host.

### Engine library port (R2 steps 2–5)

- [ ] T022 [US1] Copy `~/GitHub/ree-debug-tui/src/checks/{cameras,connectivity,decode,reecu,usb,mod}.rs` verbatim into `hackhaton/engine/ree-debug-engine/src/checks/`; adjust `mod` declarations only (no logic edits)
- [ ] T023 [US1] Copy `~/GitHub/ree-debug-tui/src/{inventory,ssh,manifest,ping,session_init}.rs` verbatim into `hackhaton/engine/ree-debug-engine/src/`; adjust `mod` declarations only
- [ ] T024 [US1] Copy `~/GitHub/ree-debug-tui/config/expected_usb.yaml` to `hackhaton/engine/ree-debug-engine/config/expected_usb.yaml`; update the loader path in `hackhaton/engine/ree-debug-engine/src/checks/usb.rs` to use a `CARGO_MANIFEST_DIR`-relative path
- [ ] T025 [US1] Audit ported library files for `println!` / `eprintln!` / `print!` / `dbg!` calls; remove all of them (Constitution: engine library MUST stay pure, no stdout/stderr writes)
- [ ] T026 [US1] Implement the real `ree_debug_engine::run_checks(host_id, inventory_path)` in `hackhaton/engine/ree-debug-engine/src/lib.rs`: orchestrate the existing fan-out logic from `~/GitHub/ree-debug-tui/src/app.rs` (parse host_id → look up in inventory → SSH ControlMaster warm-up → parallel per-category check fan-out → assemble `EngineReport`); replace stub from T002
- [ ] T027 [P] [US1] Add `hackhaton/engine/ree-debug-engine/tests/run_checks_smoke.rs` — golden-output test that calls `run_checks` against a tiny fixture inventory + a fake SSH executor (mocked via trait injection or a test-only feature flag) and asserts the returned `EngineReport` shape

### TUI binary port (R2 step 6)

- [ ] T028 [US1] Move `~/GitHub/ree-debug-tui/src/{main,app,repair}.rs` and `src/ui/{mod,dashboard,guides,menu,pick}.rs` into `hackhaton/engine/ree-debug-tui/src/`; replace any local diagnostic-execution calls with `ree_debug_engine::run_checks(...)`; mutating actions (`b` / `d` keys in `repair.rs`) stay in this binary
- [ ] T029 [P] [US1] Verify TUI binary still builds and runs end-to-end: `cd hackhaton/engine && cargo run --release -p ree-debug-tui` against the operator's real inventory; manual smoke per the historical TUI's behaviour

### CLI binary (R2 step 7)

- [ ] T030 [US1] Implement `hackhaton/engine/ree-debug-cli/src/main.rs` per `contracts/engine-cli.md`: clap-derive args (`report --host <id> --inventory <path> --json`, plus `--version`), `tokio::main`, one call into `run_checks`, `serde_json::to_writer(stdout, &report)`, structured exit codes. Reserve stdout for the JSON document; logs go to stderr
- [ ] T031 [US1] Implement the `--version` subcommand: print `ree-debug-cli {REE_DEBUG_VERSION}` to stdout and exit 0 (REE_DEBUG_VERSION wired via T005's `build.rs`)
- [ ] T032 [P] [US1] Add `hackhaton/engine/ree-debug-cli/tests/output_shape.rs` — snapshot test that runs `ree-debug-cli` against a fixture inventory + fake SSH and asserts the stdout JSON validates against `EngineReport` (use `cargo run --bin ree-debug-cli -- --host …` from the test harness)
- [ ] T033 [P] [US1] Add `hackhaton/engine/ree-debug-cli/tests/version_smoke.rs` — `ree-debug-cli --version` exits 0 and prints a non-empty SHA-shaped string

### Backend wiring

- [ ] T034 [US1] Implement `ReeCliExecutor` in `hackhaton/backend/src/vayobd/checks/ree_cli.py`: subprocess spawn of `ree-debug-cli`, JSON parse, status mapping (`Pass`→`working`, `Warn`→`warning`, `Fail`→`error`), category lookup against the catalog (T038), PII scrubbing on `raw_detail`, signal handling per `research.md` R6 (SIGTERM → 2 s grace → SIGKILL on FR-008 timeout)
- [ ] T035 [US1] Backend startup self-check: invoke `ree-debug-cli --version` from the FastAPI lifespan startup hook; cache the SHA in `app.state.engine_version`; surface `engine_unavailable` (binary missing) or `engine_incompatible` (SHA-mismatch from `backend/pyproject.toml` metadata) per FR-007 and `contracts/http-api.md`
- [ ] T036 [US1] Wire `VAYOBD_EXECUTOR=ree` selection into `hackhaton/backend/src/vayobd/dependencies.py`: add a `ReeCliExecutor` branch alongside the existing `FixtureExecutor`; honour `VAYOBD_REE_CLI_BIN` env override + `engine/target/release/ree-debug-cli` repo-relative + `$PATH` resolution per FR-003 and `contracts/engine-cli.md`
- [ ] T037 [US1] Rewrite `hackhaton/backend/src/vayobd/inventory/loader.py` to parse the Ansible-style nested `org/vay/inventory.yaml` (walk `all.children.{vehicles,telestations}.hosts` per `data-model.md`), build the existing `Host` model with `address` from `ansible_host`, `country`/`type`/`city` derived from the host id regex, drop non-`de` rows
- [ ] T038 [US1] Rewrite `hackhaton/backend/src/vayobd/api/inventory.py`: read `<settings.inventory.path>/org/vay/inventory.yaml` per request (FR-013a, no caching), return slimmed `InventoryMeta`; respond 503 with `inventory_unavailable` when settings is missing/invalid (`AppSettings.inventory is None` → SPA shows setup card, see US2)
- [ ] T039 [US1] Implement the check catalog in `hackhaton/backend/src/vayobd/checks/catalog.py`: ~25 entries covering every check id `ree-debug-engine` produces, mapped to `(name_key, category, description_key_pass, description_key_warn, description_key_fail, recommended_action_key, host_classes)`. Categories per `research.md` R4 (the 5-bucket palette). Validate via Pydantic that any check whose engine status can be `Warn`/`Fail` has a non-null `recommended_action_key`
- [ ] T039a [US1] Wire FR-016's `engine_version` audit field: extend `write_run` in `hackhaton/backend/src/vayobd/inventory/runs_cache.py` to accept and persist `engine_version: str | None` (read from `app.state.engine_version` cached during the FR-003a startup self-check), and extend `hackhaton/backend/tests/unit/test_runs_cache.py` to assert the field is written to disk and round-trips on read. Without this task FR-016 ships unimplemented.

### Backend tests

- [ ] T040 [P] [US1] Backend test: `ReeCliExecutor` invokes a fake CLI binary fixture (a tiny shell script under `backend/tests/fixtures/fake-ree-cli.sh` that emits a known-good `EngineReport` JSON to stdout) and produces the expected `DiagnosticRun` shape — in `hackhaton/backend/tests/unit/test_ree_cli_executor.py`
- [ ] T041 [P] [US1] Backend test: 30 s timeout sends SIGTERM then SIGKILL — fake binary that sleeps 60 s, executor configured with `run_timeout_seconds=0.5`, assertion that `outcome=timeout` and the subprocess is reaped — in `hackhaton/backend/tests/unit/test_ree_cli_executor.py`
- [ ] T042 [P] [US1] Backend test: catalog covers every engine check id (test reads a sample `EngineReport` JSON and asserts every `checks[].id` is present in the catalog with a non-null `name_key`) — in `hackhaton/backend/tests/unit/test_catalog.py`
- [ ] T043 [P] [US1] Backend test: PII scrubber removes VIN-shaped strings from engine `raw_detail` before persistence — in `hackhaton/backend/tests/unit/test_runner.py` (extend the existing 001 test)
- [ ] T044 [P] [US1] Backend integration test: `GET /api/inventory` parses Ansible-style YAML + drops non-DE hosts — in `hackhaton/backend/tests/integration/test_inventory_endpoint.py` (rewrite the existing 001 test for the new loader)
- [ ] T045 [P] [US1] Backend integration test: `POST /api/runs` against the fake CLI binary returns the expected `DiagnosticItem[]` with extended status enum (covers Pass/Warn/Fail mapping end-to-end) — extend `hackhaton/backend/tests/integration/test_runs_endpoint.py`

### Frontend

- [ ] T046 [P] [US1] `EngineModeBadge` component in `hackhaton/frontend/src/components/chrome/EngineModeBadge.tsx`: renders `live` (green pill) or `fixture` (amber pill) based on the `engine_mode` field from `GET /api/settings/inventory-path` (T049 in US2)
- [ ] T047 [P] [US1] Extend `DiagnosticItemRow` for `warning` status: amber tint distinct from red `error`, same icon family different colour — in `hackhaton/frontend/src/components/result/DiagnosticItemRow.tsx`
- [ ] T048 [US1] Extend `RunResultPage` to put `warning` items in the "Needs attention" group alongside `error` items, with `working` items in the "Working" group — in `hackhaton/frontend/src/pages/RunResultPage.tsx`
- [ ] T049 [US1] Populate `hackhaton/frontend/src/strings.ts` with: ~25 new item entries (`item.<engine_id>.{name,description.{working,warning,error},action}`) for every check the engine produces; new category labels `category.software` + `category.calibration`; engine-error banners `engine.unavailable.body` + `engine.incompatible.body`; `mode.live.label` + `mode.fixture.label`. Keep existing 001 entries that still apply (Constitution III audit surface)
- [ ] T050 [US1] Wire `EngineModeBadge` into `hackhaton/frontend/src/components/chrome/AppHeader.tsx` (right-aligned beside the Developer-mode switch)

### Smoke

- [ ] T051 [US1] Extend `hackhaton/frontend/tests/e2e/p1.spec.ts` with: an assertion that the `EngineModeBadge` reads `fixture` in the test environment; an assertion that a fixture host with at least one `Warn` status renders an amber row in "Needs attention"

**Checkpoint**: US1 fully functional end-to-end. With `VAYOBD_EXECUTOR=ree` against a reachable testbed, the operator sees real engine output. With `VAYOBD_EXECUTOR=fixture` (CI / demo), the existing fixture flow still works, now with the new 3-status / 5-category palette.

---

## Phase 4: User Story 2 — First-launch inventory setup (Priority: P2)

**Goal**: A new operator sees the `InventorySetupCard` instead of the wizard; pastes the path to their `ree-vehicle-configs` clone; the path is validated synchronously; on success the path is persisted to `~/.config/vayobd/settings.toml` and the wizard appears.

**Independent Test**: From a clean state (`rm ~/.config/vayobd/settings.toml`), open the SPA. The setup card is the first thing visible. Type a valid path → click Save → the wizard appears. Re-launch the backend → the wizard appears directly without the card.

### Backend

- [ ] T052 [US2] Implement `GET /api/settings/inventory-path` in `hackhaton/backend/src/vayobd/api/settings.py`: returns `{inventory: AppSettings.inventory | null, engine_mode: "live" | "fixture"}` per `contracts/http-api.md`
- [ ] T053 [US2] Implement `POST /api/settings/inventory-path` in `hackhaton/backend/src/vayobd/api/settings.py`: validates per R5 (path resolves, is directory, contains parseable `org/vay/inventory.yaml`, non-empty), persists via `settings_file.py`, returns the new state on success or one of the structured 422 codes (`path_not_a_directory`, `inventory_yaml_missing`, `inventory_yaml_unparseable`, `inventory_yaml_empty`) on failure
- [ ] T054 [US2] Register the settings router in `hackhaton/backend/src/vayobd/app.py`'s `create_app` factory
- [ ] T055 [P] [US2] Backend test: `POST /api/settings/inventory-path` round-trip — valid path → 200 + persisted; invalid path → 422 + correct error code; settings file is not touched on 422 — in `hackhaton/backend/tests/integration/test_settings_endpoint.py`

### Frontend

- [ ] T056 [P] [US2] Settings API hooks `useSettings()` + `useSaveSettings()` in `hackhaton/frontend/src/api/settings.ts`: TanStack Query GET/POST with Zod parse
- [ ] T057 [P] [US2] `InventorySetupCard` component in `hackhaton/frontend/src/components/settings/InventorySetupCard.tsx`: input pre-filled with `~/GitHub/ree-vehicle-configs`, Save button, inline error rendering keyed by the structured error code from T053
- [ ] T058 [US2] Update `PickerPage` in `hackhaton/frontend/src/pages/PickerPage.tsx` to gate on settings: when `useSettings().data.inventory === null`, render `<InventorySetupCard />` instead of the wizard; otherwise render the wizard as before
- [ ] T059 [US2] Add the setup-card-related `strings.ts` entries: `settings.inventoryPath.title` / `body` / `placeholder` / `saveButton`; the five validation error message_keys keyed in T053; `settings.inventory_unconfigured.body`
- [ ] T060 [P] [US2] Playwright test: setup-card flow at `hackhaton/frontend/tests/e2e/setup-card.spec.ts` — start with cleared `~/.config/vayobd/`, walk path-paste-save-wizard-appears; also test the three validation error paths (path missing, file missing, file unparseable)

**Checkpoint**: First-launch operator can configure their inventory path without editing TOML. Wizard renders post-setup. US1 still works end-to-end.

---

## Phase 5: User Story 3 — Change saved inventory location (Priority: P3)

**Goal**: After initial setup, the operator can change the saved inventory path via a wizard-header affordance; if the saved path stops being valid (e.g., folder deleted), the setup card auto-opens.

**Independent Test**: With a settings file already in place pointing at clone A, click the "Inventory location" affordance → setup card opens pre-filled with clone A's path → change to clone B's path → Save → wizard repopulates from clone B. Then `mv` clone B aside → re-launch the SPA → setup card auto-opens with B's now-invalid path pre-filled and an inline error.

- [ ] T061 [US3] Add an "Inventory location" link/button in the wizard header (next to `InventoryFreshness`) that opens `InventorySetupCard` in "edit" mode (pre-filled with the current path, Cancel button visible) — in `hackhaton/frontend/src/pages/PickerPage.tsx` + `hackhaton/frontend/src/components/settings/InventorySetupCard.tsx`
- [ ] T062 [US3] Auto-open the setup card when `useSettings().data.inventory !== null` but `GET /api/inventory` returns 503 with `inventory_unavailable` (the saved path stopped being valid) — in `hackhaton/frontend/src/pages/PickerPage.tsx`
- [ ] T063 [P] [US3] Add the affordance string entries: `settings.inventoryLocation.changeLink`, `settings.inventoryLocation.cancelButton` — in `hackhaton/frontend/src/strings.ts`
- [ ] T064 [P] [US3] Playwright test: change-inventory-location flow at `hackhaton/frontend/tests/e2e/change-inventory.spec.ts`; also assert that breaking the saved path mid-session re-opens the setup card on the next API call

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T065 [P] Backend lint + type pass: `ruff check hackhaton/backend/` clean, `pyright` clean across `hackhaton/backend/`
- [ ] T066 [P] Frontend lint + type pass: `npm --prefix hackhaton/frontend run typecheck` clean, `npm --prefix hackhaton/frontend run lint` clean
- [ ] T067 [P] Rust lint + format pass: `cd hackhaton/engine && cargo clippy --workspace --all-targets -- -D warnings` clean, `cargo fmt --workspace --check` clean
- [ ] T068 [P] Verify the engine library is pure: a CI step that greps every file under `hackhaton/engine/ree-debug-engine/src/` for `println!|eprintln!|print!|dbg!` and fails the build if any are found (Constitution: library/binary boundary enforced)
- [ ] T069 [P] Constitution III SC-003 jargon audit: review `hackhaton/frontend/src/strings.ts` against the catalog from T039, confirming zero raw engine identifiers (XCP, GNSS, REECU, SAS, vDrive, etc.) appear in operator-visible copy without a plain-language equivalent — record findings in the PR description
- [ ] T070 [P] Retire obsolete 001 strings now unused: `inventory.refreshFailedToast.*`, `inventory.refreshFailedBanner.*`, `inventory.lastRefreshedPrefix` — in `hackhaton/frontend/src/strings.ts` (after grep confirms no remaining call sites)
- [ ] T071 Manual run-through of `hackhaton/specs/002-real-executor/quickstart.md` §§ 1 — 6: verify the live engine path against a real testbed, the failure paths (binary not built, stale binary, unreachable host, broken inventory), and the fixture-mode demo. Record screenshots + timings in the PR description
- [ ] T072 Update `hackhaton/README.md` to point new contributors at `specs/002-real-executor/quickstart.md` for the engine-aware setup; preserve the 001 quickstart link as historical context

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → no external dependencies. Can start immediately.
- **Foundational (Phase 2)** → depends on Setup. **Blocks all user-story phases.**
- **US1 (Phase 3)** → depends on Foundational only. Is the MVP.
- **US2 (Phase 4)** → depends on Foundational. Backend settings layer (T010 in foundational) feeds US2's endpoints; the SPA setup card is an additional gate the wizard checks. US1's `EngineModeBadge` (T046) consumes the same `GET /api/settings/inventory-path` route as US2 (T052) — that route lands in US2 but its body shape is fixed in `contracts/http-api.md` so US1 can hard-code the badge against the contract while US2 wires the real endpoint.
- **US3 (Phase 5)** → depends on US2 (re-uses `InventorySetupCard` and the settings endpoints).
- **Polish (Phase 6)** → depends on whichever stories you intend to ship.

### Within Each Story

- **Engine port (US1)**: T022 → T023 → T024 → T025 (audit purity) → T026 (real `run_checks`) → T027 (golden test). Sequential because each step touches the engine library's `lib.rs` `mod` declarations.
- **TUI port (US1)**: T028 → T029. Depends on T022–T026 because the TUI binary calls `ree_debug_engine::run_checks`.
- **CLI binary (US1)**: T030 → T031 → T032 / T033. Depends on T026 (real engine entry point) and T005 (build.rs SHA).
- **Backend wiring (US1)**: T034 → T035 → T036. Depends on the CLI binary (T030 — needs a binary to invoke). T037–T039 can run in parallel with the CLI work since they touch backend-only files.
- **Frontend (US1)**: T046–T050 are mostly parallel; T048 depends on T047; T050 depends on T046.
- **Tests (US1)**: T040, T041, T042, T043, T044, T045 are all `[P]` once the corresponding production code lands.

### Parallel Opportunities

#### Phase 1 Setup

```text
T001 must run first (creates the workspace declaration).
[P] T002, T003, T004, T005 are independent — different files, distinct crates.
T006 is the verification step; runs last.
```

#### Phase 2 Foundational

```text
[P] T007 || T008 || T009 || T011 || T012 || T013 || T014 || T015 || T016 || T017 || T018 || T019 || T020 || T021
T010 → after T009 (uses InventorySettings).
```

#### Phase 3 US1 — broad parallelism after the engine library lands

```text
Engine track:    T022 → T023 → T024 → T025 → T026 → T027
TUI track:       T028 → T029                    (after engine track)
CLI track:       T030 → (T031 || T032 || T033)  (after engine track)
Backend track:   (T037 || T038 || T039) || (T034 → T035 → T036)
Frontend track:  T046 || T047 || T049 || T050; T048 → after T047
Test track:      T040–T045 all [P] after their production code

T051 (Playwright extension) → after T034–T036 + T046–T050.
```

#### Phase 4 US2

```text
Backend:  T052 → T053 → T054; T055 [P] after T053.
Frontend: T056 || T057; T058 → after T056 + T057; T059 [P] independent; T060 → after T058.
```

#### Phase 5 US3

```text
T061 → after T057 (re-uses InventorySetupCard); T062 → after T058 (settings gate); T063 [P]; T064 → after T061 + T062.
```

#### Phase 6 Polish

```text
[P] T065, T066, T067, T068, T069, T070 are mutually independent.
T071, T072 sequential, run last.
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1: Setup — empty workspace, three stub crates compile.
2. Phase 2: Foundational — model extensions, settings layer, retirements. CI green via `VAYOBD_EXECUTOR=fixture` (the existing 001 path still works with the extended enums because warning is unused in fixtures).
3. Phase 3: US1 — port the library, write the CLI binary, wire `ReeCliExecutor`, expand the catalog and strings.
4. **STOP, validate** quickstart §§ 3 — 4 happy path against a real testbed and §§ 5 failure paths.
5. Demo.

### Incremental Delivery

1. Setup + Foundational → mainline still demos via fixture; nothing user-visible breaks.
2. + US1 → MVP demo (P1 acceptance scenarios all green; live engine works).
3. + US2 → first-launch friendly (P2). Operator-onboarding story closed.
4. + US3 → operationally complete (P3).
5. + Polish → Constitution III audit, retired-strings cleanup, manual quickstart sweep.

### Parallel Team Strategy (for the hackathon)

- **Rust track** (one engineer): Phase 1 + the engine port + CLI binary (T001 — T033). Lands binaries first so other tracks can mock against the contract.
- **Backend track** (one engineer): Phase 2 backend half + US1 backend wiring (T007 — T016, T034 — T045) + US2/US3 settings (T052 — T055).
- **Frontend track** (one engineer): Phase 2 frontend half + US1 frontend (T019 — T021, T046 — T051) + US2/US3 setup card (T056 — T064).
- **Glue/integration track** (rotating): T006, T035, T071, plus the Playwright + Cargo CI lanes.

---

## Notes

- `[P]` tasks operate on different files with no incomplete-task dependencies.
- Story labels (`[US1]`, `[US2]`, `[US3]`) trace tasks back to spec.md user stories.
- Tests are the constitution-mandated minimum: targeted Rust unit tests + golden snapshot for the engine, backend pytest unit + integration on the load-bearing logic (subprocess invocation, timeout, scrubber, settings round-trip), Playwright smoke per user story for demo readiness. No full TDD pyramid.
- Commit per task or per logical group; the constitution's mainline-always-deployable rule applies.
- Stop at any checkpoint to validate independently. The MVP at the end of Phase 3 is the smallest demoable thing that delivers the spec's primary value (real engine output rendered in the SPA).
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence.
