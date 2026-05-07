# Feature Specification: Real Diagnostic Engine via ree-debug-tui

**Feature Branch**: `002-real-executor`
**Created**: 2026-05-07
**Status**: Draft
**Input**: User description: "Replace the fixture/SSH executor stack with ree-debug-tui as the v1 diagnostic engine for VayOBD. Add a `report --json` subcommand to ree-debug-tui, surface every check it runs in the web app, retire the per-file inventory walker in favour of `org/vay/inventory.yaml` whose path is captured from the operator on first launch and persisted."

## Clarifications

### Session 2026-05-07

- Q: FR-006 — what category set does Operator mode use to label items in the result view? → A: Five plain-language categories — **Communication, Hardware, Configuration, Software, Calibration**. Software covers vDrive manifest drift, firmware/gateware version drift, container status; Calibration covers SAS calibration and the GNSS yaw-rate watchdog.
- Q: How does `ree-debug-tui`'s `Warn` status map onto the web app's two-status `DiagnosticItem` shape? → A: Add a third status `warning` end-to-end. Mapping: `Pass → working`, `Warn → warning`, `Fail → error`. `warning` items render in the "Needs attention" group alongside `error` items, but with a visually subordinate amber tint distinct from the red `error` tint. Plain-language descriptions and recommended next actions still apply.
- Q: When `ree-debug-tui` is missing or its `report --json` subcommand is unavailable, what should the app do? → A: **Hard-fail**, never silently fall back. With `VAYOBD_EXECUTOR=ree` (production default), every `POST /api/runs` returns the `engine_unavailable` / `engine_incompatible` banner and the CTA stays disabled until the engine is installed/upgraded. Demos / CI explicitly opt into fixtures with `VAYOBD_EXECUTOR=fixture`. Auto-fallback is not allowed — the silent "operator thought they were running real diagnostics but got fixtures" failure mode is the specifically forbidden case.
- Q: When does the backend re-read `org/vay/inventory.yaml`? → A: **Per request.** Every `GET /api/inventory` re-reads and re-parses the file from the configured path. The cache + periodic git-fetch + manual refresh button + exp-backoff banner from `001-host-diagnostics` (FR-016 — FR-019, FR-027) are retired along with the walker; the operator's `git pull` + browser tab refresh is the v1 update flow.
- Q: Bolt `report --json` onto the existing `ree-debug-tui` binary, or restructure the Rust into a clean engine-library-plus-frontends layout? → A: **Clean refactor inside this monorepo.** Three Cargo crates under a new `engine/` workspace at the repo root: `ree-debug-engine` (library — every probe, every parser, returns structured Rust types, no I/O concerns), `ree-debug-tui` (binary — thin ratatui frontend), `ree-debug-cli` (binary — thin JSON-emitting frontend the Python backend shells out to). The existing `~/GitHub/ree-debug-tui` repo is the **source we port from**; after porting it is historical. JSON contract versioning collapses to "the binary and the Python backend ship from the same git SHA" — no separate `schema_version` field needed in v1.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Run a real diagnostic against a real testbed (Priority: P1)

The operator opens the web app, walks the existing wizard
(Country → Type → optional City → Host → Continue → Run check), and
gets back a result view that reflects the **actual state of the
testbed**, not a fixture. Every check `ree-debug-tui` already runs in
its terminal UI — SSH reachability, DNS resolver, vDrive package vs
manifest drift, REECU container status, CAN buses up, APP_CAN traffic
rate, the XCP active probe (CAN ID `0x790` request → `0x791` response),
REECU heartbeat, SAS calibration, GNSS yaw-rate watchdog, lobby
polling-loop detector, ROS-node liveness, USB inventory, plus the
TS- and VE-specific CAN decoders — appears in the **Working** or
**Needs attention** group with a plain-language operator-facing name
and (for errors) a recommended next action. Developer mode reveals
the raw probe output for each item.

**Why this priority**: This is the entire point of `002-real-executor`.
Without it, VayOBD stays a fixture demo and operators can't actually
diagnose anything. It is also the smallest viable slice — once it
works, the team can throw away the SSH-stub and move on.

**Independent Test**: With a real testbed reachable on the network,
pick that host in the wizard, click **Run check**, and confirm the
result view enumerates every item the same `ree-debug-tui` instance
would show in its TUI for the same host (status counts match,
operator-visible names match the catalog).

**Acceptance Scenarios**:

1. **Given** a healthy reachable Germany vehicle, **When** the operator
   runs a check, **Then** every item the diagnostic engine produces
   appears under "Working" by name, the "Needs attention" group is
   empty, and the run timestamp reflects the actual completion time.
2. **Given** a reachable host with at least one failing check (for
   example, the front camera is disconnected), **When** the operator
   runs a check, **Then** that item appears in "Needs attention" with
   a plain-language description and a recommended next action; every
   other item the engine ran appears in "Working".
3. **Given** a reachable host with a soft warning (for example, only
   public DNS resolvers are configured but the host still resolves
   names), **When** the operator runs a check, **Then** that item
   appears in "Needs attention" with `warning` status — visually
   amber and distinct from a red `error` — alongside any `error`
   items, with the same plain-language description + recommended
   next action treatment.
4. **Given** the operator has Developer mode on, **When** they expand
   any item row, **Then** the raw underlying detail captured by the
   engine (CAN trace excerpt, exit code, parser message, raw stderr
   line) is visible — never in Operator mode.
5. **Given** the host is unreachable on the network, **When** the
   operator runs a check, **Then** the result is the single user-facing
   "Host could not be reached" message inherited from
   `001-host-diagnostics` (FR-006) — not a list of fabricated item
   errors.
6. **Given** the underlying engine takes longer than the configured
   ceiling, **When** the timer elapses, **Then** the run is marked as
   timeout (FR-025 carried forward) and partial results, if any, are
   discarded.

---

### User Story 2 — First-launch inventory setup (Priority: P2)

A new operator opens the app for the first time. Because there is no
saved inventory location, the app blocks the wizard with a setup card
that asks for the path to their local `ree-vehicle-configs` clone
(typical: `~/GitHub/ree-vehicle-configs`). The operator pastes or
browses the path, the app validates that the directory contains
`org/vay/inventory.yaml`, persists the path to a config file under the
user's home directory, and unblocks the wizard.

**Why this priority**: Without inventory the wizard can't render. The
operator's first task on a fresh install is therefore inventory setup.
This story makes that one-time interaction friendly — instead of a
hard-coded path that nobody on the team uses, the operator points the
app at their existing checkout once.

**Independent Test**: From a clean state (no
`~/.config/vayobd/settings.toml`), open the app. The setup card is
the first thing the operator sees. After typing a valid path and
confirming, the wizard appears with the expected hosts. Re-launch the
app — the setup card does not reappear.

**Acceptance Scenarios**:

1. **Given** no settings file exists, **When** the operator opens the
   app, **Then** a setup card asks for the inventory path with an
   editable input (pre-filled with the typical default
   `~/GitHub/ree-vehicle-configs`) and a single "Save" action.
2. **Given** the path the operator entered does not exist, **When**
   they click "Save", **Then** the setup card stays visible and shows
   a plain-language error ("That path doesn't exist on your machine").
3. **Given** the path exists but does not contain
   `org/vay/inventory.yaml`, **When** they click "Save", **Then** the
   setup card stays visible with a different plain-language error
   ("That folder is missing `org/vay/inventory.yaml` — is this the
   right repo?").
4. **Given** the path is valid, **When** they click "Save", **Then**
   the path is persisted and the wizard appears immediately without a
   page reload.
5. **Given** a settings file already exists with a valid path, **When**
   the operator opens the app, **Then** the setup card is skipped and
   the wizard appears directly.

---

### User Story 3 — Change the saved inventory location (Priority: P3)

After the initial setup, the operator can change the saved inventory
path — for example, they moved their `ree-vehicle-configs` checkout
to a different folder, or they're sharing the machine with another
user, or the path stops being valid because the folder was renamed.
A persistent affordance in the app (e.g., a small link in the wizard
header next to "Inventory updated…") opens the same setup card,
pre-filled with the current path.

**Why this priority**: It's not on the demo path — most operators
will set the path once and never touch it. But once an operator's
saved path stops being valid, the app must give them a way out
without editing TOML by hand.

**Independent Test**: With a settings file already in place, click
the "Inventory location" affordance, change the path to a different
valid clone, save, and confirm the wizard repopulates from the new
location.

**Acceptance Scenarios**:

1. **Given** the wizard is showing, **When** the operator clicks the
   "Inventory location" affordance, **Then** the setup card opens
   pre-filled with the current path and a Cancel option.
2. **Given** the operator's saved path stops being valid (the folder
   was deleted), **When** they next open the app, **Then** the setup
   card opens automatically with the previous path pre-filled and an
   inline error explaining what's wrong, until they save a valid
   path.

---

### Edge Cases

- **`ree-debug-cli` binary not built yet**: The repo ships the source
  but not pre-built binaries. The app MUST surface a single
  user-facing message ("The diagnostic engine isn't built yet on
  this machine — run `cargo build --release --workspace` from
  `engine/`") and disable the "Run check" CTA — not silently fall
  back to fixtures or stack-trace into the operator's face. Operator
  mode never shows raw "command not found" output
  (Constitution III).
- **`ree-debug-cli` binary present but stale** (built from an older
  workspace SHA than the running Python backend, surfaced via the
  FR-003a startup `--version` mismatch): The app MUST treat this as
  `engine_incompatible` with plain-language framing, pointing the
  operator at "rebuild the engine and try again", rather than
  rendering JSON parser errors from a drifted schema.
- **`ree-debug-cli` writes malformed JSON or exits non-zero**
  (engine crashed mid-run): Outcome is `unreachable` (no fabricated
  items), the run record carries the exit code and stderr tail in the
  audit log only, and the operator sees the standard unreachable
  copy.
- **Engine takes longer than the FR-025 30 s ceiling**: The same
  timeout behaviour as `001-host-diagnostics` — outcome `timeout`,
  empty items, the engine subprocess is sent SIGTERM (then SIGKILL on
  grace expiry) so it doesn't keep an SSH ControlMaster open after
  the request returns.
- **Operator launches the app while their `ree-vehicle-configs`
  checkout is in the middle of a `git pull`**: The path is valid, the
  YAML is parseable; whatever the inventory said at that instant is
  the inventory the wizard sees. The next manual or scheduled refresh
  picks up the rest.
- **Inventory file at the saved path is itself broken** (YAML parse
  error, schema mismatch): The wizard shows the FR-019 blocking
  empty-state with copy adapted to "your inventory file looks
  malformed — re-clone or fix it" and the "Inventory location"
  affordance is highlighted as the recovery path.
- **Operator runs the same check twice in a row**: Each
  `POST /api/runs` is its own `ree-debug-cli` subprocess; there is no
  shared state between runs in v1 (the per-host concurrency lock
  from `001-host-diagnostics` FR-011 still applies). The CLI binary
  re-establishes its own SSH ControlMaster per run.

## Requirements *(mandatory)*

### Functional Requirements

#### Diagnostic engine

- **FR-001**: A new Rust workspace MUST live under `engine/` at the
  monorepo root with three crates (Clarification 2026-05-07):
  - `engine/ree-debug-engine` — library crate. Holds every probe,
    parser, decoder, and inventory loader currently in
    `~/GitHub/ree-debug-tui`. Pure logic — no terminal I/O, no
    `println!`-shaped output, no rendering. Returns structured Rust
    types defined inside the crate.
  - `engine/ree-debug-tui` — binary crate. The terminal UI from the
    historical repo, restructured to call into `ree-debug-engine`
    instead of owning the diagnostic logic. Mutating actions
    (`b` bring up CAN bus, `d` toggle debug-mode sentinel) live
    **only** here; they MUST NOT exist in the engine library.
  - `engine/ree-debug-cli` — binary crate. Thin non-interactive
    frontend. Reads CLI args, calls `ree-debug-engine` against the
    configured inventory + host, serialises the structured results to
    stdout as JSON via `serde_json`, exits. The Python backend shells
    out to this binary.
  The pre-existing `~/GitHub/ree-debug-tui` repo is the **source we
  port from** — once the workspace is populated and tested, the
  external repo is historical and not maintained alongside this one.
- **FR-002**: `ree-debug-cli` MUST expose a `report` subcommand
  invoked as `ree-debug-cli report --host <id> --inventory <path>
  --json` (required args: `--host`, `--inventory`; required flag in
  v1: `--json`). The subcommand runs the full per-host check fan-out,
  serialises the structured engine result to stdout as JSON, and
  exits. The binary MUST also expose a `--version` subcommand the
  backend uses for the FR-003a startup self-check. The `--json` flag
  is required in v1 even though it is the only output format —
  reserving the flag leaves room for a future `--text` mode without
  breaking existing callers.
  Exit codes:
  - `0` — engine produced per-check results (regardless of whether
    individual checks passed or failed; per-check failure is data,
    not engine failure).
  - non-zero — engine-internal failure (inventory unparseable, host
    id not in inventory, SSH layer crashed, etc.). The Python backend
    surfaces these as `engine_unavailable` per FR-007.
  `ree-debug-cli` MUST NOT render any TUI, MUST NOT prompt for
  input, and MUST NOT write anything but the JSON document to
  stdout (logs go to stderr).
- **FR-003**: The Python backend MUST invoke `ree-debug-cli` as a
  child subprocess per `POST /api/runs`, parse the JSON document
  (`serde_json` shape on the Rust side ↔ Pydantic models on the
  Python side), and map each engine check entry into the
  `DiagnosticItem` shape from `001-host-diagnostics` (extended per
  FR-004a). The binary path is resolved in this order: explicit
  `VAYOBD_REE_CLI_BIN` env override; relative path
  `engine/target/release/ree-debug-cli` from the repo root;
  `$PATH` lookup of `ree-debug-cli`. First match wins.
- **FR-003a**: Because the engine library, the CLI binary, and the
  Python backend live in one monorepo and ship from the same git SHA,
  the JSON contract is the workspace's `serde_json` <-> Pydantic
  schema at that SHA — there is no separate `schema_version` field
  to negotiate. The backend's startup self-check MUST verify the
  CLI binary is present and runs the FR-002 invocation against a
  no-op flag (e.g., `--version`) to surface mismatches before the
  first run. Mismatches → `engine_incompatible` per FR-007.
- **FR-004**: Every check `ree-debug-tui` produces MUST be surfaced in
  the result view. Operator mode shows the plain-language name +
  category label per FR-010 from `001-host-diagnostics`; Developer
  mode reveals the raw underlying detail per FR-022 from
  `001-host-diagnostics`. No check is silently dropped from the
  operator-visible result.
- **FR-004a**: The `DiagnosticItem.status` enum MUST be extended to
  three values — `working`, `warning`, `error` — to faithfully carry
  `ree-debug-tui`'s `Pass` / `Warn` / `Fail` outputs (Clarification
  2026-05-07). Mapping is fixed: `Pass → working`, `Warn → warning`,
  `Fail → error`. The two-status enum from
  `001-host-diagnostics` (`working` / `error`) is superseded.
- **FR-004b**: The result view MUST render `error` and `warning`
  items both under "Needs attention" — `error` with the existing red
  tint, `warning` with a visually distinct amber tint. The "Working"
  group contains only `working` items. The two acceptance criteria
  on `error` items from `001-host-diagnostics` (plain-language
  description per FR-004; recommended next action per FR-005) MUST
  apply equally to `warning` items.
- **FR-005**: The mapping from `ree-debug-tui`'s per-check identifier
  to the operator-facing `DiagnosticItem` MUST be deterministic and
  reviewable in one place (a check catalog), so a jargon audit
  (Constitution III) can be done by reading one file.
- **FR-006**: The category set used to label items in Operator mode
  MUST be the five plain-language categories — **Communication,
  Hardware, Configuration, Software, Calibration** (Clarification
  2026-05-07). Software covers vDrive manifest drift, firmware /
  gateware version drift, and container status (REECU gateway, ROS
  nodes); Calibration covers SAS calibration and the GNSS yaw-rate
  watchdog. Every item the catalog defines MUST fall into exactly
  one of these five categories. The frontend's `category` enum
  (`api/schemas.ts`) and the `strings.category.*` table MUST be
  extended to match.
- **FR-007**: If `ree-debug-cli` cannot be located via the FR-003
  resolution order, or its `--version` self-check fails, the backend
  MUST fail every run while `VAYOBD_EXECUTOR=ree` (the production
  default) with a stable error code (`engine_unavailable` for
  missing/unbuilt binary, `engine_incompatible` for any other
  startup-check failure) and message_key the SPA can render as a
  plain-language banner. The banner SHOULD include the remediation
  command for the typical case (`cargo build --release --workspace`
  inside `engine/`). The "Run check" CTA MUST be disabled while the
  engine is unavailable. The backend MUST NOT silently fall back to
  `FixtureExecutor` (Clarification 2026-05-07) — falling back is a
  deliberate operator choice, opted into by setting
  `VAYOBD_EXECUTOR=fixture` (mirrors 001's existing env-flag
  selection). The mode the engine is running in MUST be visible to
  the operator (header badge or similar) so a fixture-mode demo is
  never mistaken for a live run.
- **FR-008**: The 30 s hard run timeout (FR-025 from
  `001-host-diagnostics`) MUST apply to the engine subprocess
  end-to-end. On expiry the backend MUST send SIGTERM to the
  subprocess, wait briefly for graceful shutdown, then SIGKILL.

#### Inventory

- **FR-009**: On launch the backend MUST read the operator-configured
  inventory path from a settings file under the user's home (e.g.,
  `~/.config/vayobd/settings.toml`). When that file is absent or the
  configured path no longer points at a valid checkout, the app MUST
  prompt the operator with a setup card before any wizard or run flow
  is reachable.
- **FR-010**: The setup card MUST validate the entered path
  synchronously before saving: the path MUST resolve to a directory
  on disk and that directory MUST contain a parseable
  `org/vay/inventory.yaml`. Validation failures MUST present
  plain-language errors per the User Story 2 acceptance scenarios.
- **FR-011**: The setting MUST persist between launches in a single
  TOML file under the user's home. The file MUST NOT contain any
  secret material (no credentials, tokens, or keys).
- **FR-012**: The wizard MUST expose an "Inventory location"
  affordance that re-opens the setup card pre-filled with the current
  path, so the operator can change it without editing the TOML by
  hand (User Story 3).
- **FR-013**: The combined `org/vay/inventory.yaml` document is the
  v1 source of truth for the host list. The previous
  `org/*/{vehicles,telestations}/*.yaml` walker (FR-001b loader logic
  from `001-host-diagnostics`) is retired.
- **FR-013a**: The backend MUST re-read and re-parse the inventory
  YAML on **every** `GET /api/inventory` request (Clarification
  2026-05-07). No in-memory cache, no periodic refresh task, no
  manual "Update inventory" button, no exp-backoff banner — the
  cache + sync layer from `001-host-diagnostics`
  (FR-016 — FR-019, FR-027) is retired with the walker. The
  operator's `git pull` + browser tab refresh is the v1 update flow.
  YAML parse failures map to the FR-019-style blocking empty-state
  with a "your inventory file looks malformed" message and the
  "Inventory location" affordance highlighted.
- **FR-014**: Inventory parsing MUST honour the same DE-only
  scope (`*-de-*` host IDs) carried forward from
  `001-host-diagnostics`. Hosts whose IDs do not match the DE
  pattern MUST NOT appear in any wizard step.

#### Carried-forward constraints from `001-host-diagnostics`

- **FR-015**: The Operator/Developer mode toggle behaviour
  (FR-020 — FR-023 from `001-host-diagnostics`) is unchanged. The
  Developer-mode raw expand reveals exactly the JSON the engine
  produced for that check.
- **FR-016**: Per-`(operator, host)` backend persistence
  (FR-026 from `001-host-diagnostics`) is unchanged. The persisted
  record adds the engine-version string the run used so an audit can
  tie a stored result back to the engine that produced it.
- **FR-017**: Result view opens blank on host entry
  (FR-028 from `001-host-diagnostics`); the engine subprocess only
  fires after the operator clicks "Run check".
- **FR-018**: PII / VIN MUST NOT appear in URLs, client-side logs, or
  analytics (FR-013 from `001-host-diagnostics`). The same
  server-side scrubber MUST be applied to engine-produced raw output
  before it is persisted or returned to the SPA.

### Key Entities

- **Engine Workspace** (`engine/` at the monorepo root): A Cargo
  workspace containing three crates — the `ree-debug-engine` library
  (diagnostic logic), the `ree-debug-tui` binary (terminal UI), and
  the `ree-debug-cli` binary (JSON-emitting frontend). Built via
  `cargo build --release --workspace` from `engine/`; outputs land
  in `engine/target/release/`.
- **Diagnostic Engine Binary** (`ree-debug-cli`): The compiled JSON
  frontend the Python backend invokes. Discovered via the
  `VAYOBD_REE_CLI_BIN` env override → `engine/target/release/
  ree-debug-cli` relative to the repo root → `$PATH` lookup. Carries
  a workspace-derived version string the backend's startup self-check
  uses for FR-007 compatibility.
- **Engine Report**: The JSON document `ree-debug-cli` prints to
  stdout for one host run. Contains a top-level outcome marker, a
  list of per-check entries (each with an engine-internal identifier,
  status, raw detail, and timing), and the engine version. The
  backend's mapper translates this into a `DiagnosticRun` from
  `001-host-diagnostics`.
- **Engine Check Entry**: One element of `Engine Report.checks`. Has
  a stable identifier (used as the catalog key), a status (one of
  `Pass` / `Warn` / `Fail`, mapped to `working` / `warning` / `error`
  per FR-004a), a free-form raw detail blob, and timing. The catalog
  maps each engine identifier to an operator-visible name + category
  (one of the five from FR-006) + recommended action (required for
  `warning` and `error` items).
- **Inventory Settings**: The persisted user-level configuration —
  primarily the inventory path. Lives in a TOML file under the user's
  home; never contains credentials.
- **Inventory File** (`org/vay/inventory.yaml`): The team-maintained
  combined inventory document, owned by `ree-vehicle-configs`. Read
  directly from the operator's local clone rather than via a
  per-folder walker. Supplies the host list the wizard renders.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A run against a healthy reachable Germany testbed
  produces a result view whose item names + statuses match what the
  same `ree-debug-tui` instance shows in its TUI for the same host
  at the same moment, for **100% of the engine's checks**.
- **SC-002**: A first-time operator can complete the inventory setup
  card (paste path, click Save, see the wizard) in **under 30 seconds**
  on a fresh install with the inventory already cloned.
- **SC-003**: A jargon audit of the operator-visible result view
  across at least 10 distinct error scenarios shows zero raw
  identifiers, zero stack traces, and zero engine-internal terms
  (XCP, GNSS, REECU, SAS, vDrive, etc.) presented without a
  plain-language equivalent.
- **SC-004**: When the engine binary is missing, **100% of operators**
  see the dedicated "engine not installed" banner — no operator
  reaches the result view and clicks Run check only to be greeted by
  a stack trace.
- **SC-005**: The retired `SshExecutor` has zero call sites in the
  shipped Python backend (verifiable by grep / dead-code lint), and
  the `engine/` workspace builds and tests cleanly with
  `cargo build --release --workspace && cargo test --workspace`.
- **SC-006**: A single end-to-end run completes within the FR-008 30 s
  ceiling on a healthy reachable testbed for **≥ 95% of attempts**
  (measured over a 10-run sample on one host).

## Assumptions

- Every operator has a local clone of `ree-vehicle-configs`. The app
  does not clone or update the repo on their behalf — the operator
  pulls it the same way they always have.
- The operator builds the `engine/` workspace once on their machine
  (`cargo build --release --workspace` from `engine/` — Rust toolchain
  required, same as ree-debug-tui requires today). The Python backend
  picks up the resulting binary at
  `engine/target/release/ree-debug-cli`. No separate `cargo install`
  step. Failure to build surfaces via FR-007.
- `ree-debug-engine` continues to scope its host list to `*-de-*`
  (Germany only) by porting the existing `src/app.rs` filter into the
  library. The web app's v1 scope inherits this — no extra DE
  filtering is needed beyond what the engine library already does.
- The historical `~/GitHub/ree-debug-tui` repo is the **source we
  port from**. Once the workspace under `engine/` carries the same
  diagnostic IP and the team has switched to using the in-monorepo
  TUI, the external repo is historical; no parallel maintenance.
- Mutating actions (`b` to bring up an XCP bus, `d` to toggle the
  debug-mode sentinel file) live ONLY in the `engine/ree-debug-tui`
  binary and MUST NOT be exposed in `ree-debug-engine` (the library)
  or `ree-debug-cli` (the JSON frontend the web app calls). The web
  app is a read-only diagnostic surface.
- Operating system: Linux or macOS (the platforms `ree-debug-tui`
  already supports). Windows operators run inside WSL2 the same way
  they run the TUI.
- The 30 s FR-025 ceiling is sufficient headroom for the worst
  realistic engine run against one host on the typical Vay network.
  If the engine's full check set genuinely takes longer than 30 s on
  healthy hardware, the ceiling will need a separate clarification —
  this spec does not extend it.
- The catalog (engine-id → operator-visible name / category /
  recommended action) is maintained inside the web app's backend
  alongside `001-host-diagnostics`'s existing catalog. The Rust side
  doesn't ship operator-facing copy.
- Authentication / per-operator persistence (FR-026 from
  `001-host-diagnostics`) is unchanged. The engine subprocess runs
  with the same identity as the FastAPI process, not as the
  triggering operator's OS account; the SSH layer inside the engine
  reads `~/.ssh/config` of the FastAPI process owner. The expected
  deployment is "each operator runs the FastAPI backend on their own
  machine and hits it from their browser at `localhost`" — the same
  desktop-app-shaped model 001's quickstart uses.
- The on-disk run record (`runs/<operator-slug>/<host_id>.json`)
  gains an `engine_version` field; older records without this field
  remain readable for backwards-compat.
