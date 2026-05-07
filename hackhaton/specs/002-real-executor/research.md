# Phase 0 Research — Real Diagnostic Engine via ree-debug-tui

This document resolves the open implementation questions left by
`spec.md` and `plan.md`, using the format Decision / Rationale /
Alternatives. Six topics, in dependency order.

---

## R1. Cargo workspace layout — what goes in which crate?

**Decision**: Three crates under `engine/`:

```text
engine/
├── Cargo.toml             # [workspace] members = ["ree-debug-engine", "ree-debug-tui", "ree-debug-cli"]
├── ree-debug-engine/      # cdylib? no — rlib library, default target.
├── ree-debug-tui/         # bin = "ree-debug-tui"; depends on ree-debug-engine
└── ree-debug-cli/         # bin = "ree-debug-cli"; depends on ree-debug-engine
```

**`ree-debug-engine` (library) contents**:
- All probe code: `checks/{cameras, connectivity, reecu, usb, decode}`
  ported from `ree-debug-tui/src/checks/*`.
- All glue: `inventory.rs`, `ssh.rs`, `manifest.rs`, `ping.rs`,
  `session_init.rs` ported from `ree-debug-tui/src/*`.
- A new `types.rs` module that defines the *public* serde-derivable
  shapes the binaries consume — the one place we draw the
  library/binary boundary.
- A new `lib.rs` that re-exports a single async entry point:
  `pub async fn run_checks(host_id: &str, inventory_path: &Path) -> Result<EngineReport, EngineError>`.
- **Forbidden**: `println!`, `eprintln!`, anything writing to
  stdout/stderr, anything `std::process::exit`. Rendering and
  process-control belong to the binaries.

**`ree-debug-tui` (binary) contents**:
- `main.rs`, `app.rs`, `repair.rs`, `ui/*` ported from
  `ree-debug-tui/src/{main, app, repair, ui}.rs` — same as before,
  but now they call into `ree_debug_engine::run_checks()` instead of
  owning the diagnostic logic.
- `b` and `d` key handlers (the mutating actions) live here only.
  The engine library never offers a function that mutates host
  state.

**`ree-debug-cli` (binary) contents**:
- A single `main.rs` (~80 lines): clap-derive for the CLI args, one
  `tokio::main` call into the engine, `serde_json::to_writer` to
  stdout, structured exit codes.

**Rationale**:
- Constitution I (Simplicity First): the library/binary split is the
  *minimum* refactor that gives us a TUI and a JSON CLI without
  duplicating diagnostic code. Any tighter coupling means re-writing
  diagnostics; any looser means twin maintenance.
- Forbidding stdout/stderr writes from the engine library means the
  JSON CLI can guarantee its stdout is reserved for the JSON document
  (FR-002 stdout-only requirement).
- Putting mutating actions in the TUI binary only makes
  "the web app is read-only" enforceable at compile time — the engine
  library doesn't expose the mutating functions in its public API,
  so `ree-debug-cli` literally cannot call them.

**Alternatives considered**:
- *Two crates (engine + cli; TUI as a feature flag inside the
  engine)*: rejected — feature-flagging the TUI inside the engine
  library re-introduces stdout writes from the library and breaks
  the FR-002 stdout-purity rule.
- *Four crates (split `engine` further into `engine-types` and
  `engine-runtime`)*: rejected — premature abstraction; the spec
  doesn't ask for an externally-versioned types crate, and we'd add
  a layer of `Cargo.toml` for nothing.
- *Single binary with subcommands (`ree-debug-tui` / `ree-debug-tui
  report`)*: this was the original spec phrasing before the rewrite
  decision. Rejected per the 2026-05-07 clarification — the user
  picked B (clean refactor) precisely to *avoid* the
  subcommand-bolt-on shape.

---

## R2. Porting strategy from `~/GitHub/ree-debug-tui` into `engine/`

**Decision**: Mechanical port, in this order, with each step
landing as a separate commit on `002-real-executor`:

1. **Bootstrap workspace skeleton** — empty `engine/Cargo.toml`
   workspace, three empty crates, each with a stub `lib.rs` /
   `main.rs` that compiles. CI green at this point.
2. **Copy `src/checks/` → `ree-debug-engine/src/checks/`** verbatim.
   Adjust `mod` declarations only. Push.
3. **Copy `src/{inventory, ssh, manifest, ping, session_init}.rs`**
   into `ree-debug-engine/src/`. Same — verbatim, only `mod`
   declarations change.
4. **Add `ree-debug-engine/src/types.rs`** — the new public
   serde-derivable types (see R3). The pre-existing internal Rust
   types in `checks/decode.rs` etc. stay private; `types.rs` is the
   library's public face.
5. **Add `ree-debug-engine/src/lib.rs`** — re-exports
   `run_checks(host_id, inventory_path) -> EngineReport`. Internally,
   this is the same orchestration `ree-debug-tui/src/app.rs` does
   today, minus the TUI render loop.
6. **Move `src/{main, app, repair, ui}.rs` → `ree-debug-tui/src/`**.
   Replace any local diagnostic invocations with calls into
   `ree_debug_engine::*`. Mutating handlers stay here.
7. **Write `ree-debug-cli/src/main.rs`** from scratch — clap
   derives, calls `run_checks`, prints JSON.
8. **Verify** with `cargo build --release --workspace` and
   `cargo test --workspace`. The TUI binary should still pass any
   existing smoke tests; the CLI binary runs against a hand-built
   inventory fixture.

**Rationale**:
- Each step lands a green CI build. Constitution II (Ship Fast):
  mainline is always deployable.
- Mechanical "move files, fix imports" reduces the chance of
  introducing diagnostic regressions during the port.
- The engine API surface is small enough (`run_checks`) that the
  TUI binary's adapter logic is one function call away from what it
  does today.

**Alternatives considered**:
- *Big-bang rewrite into the new layout*: rejected — Constitution II
  forbids broken-mainline windows; a multi-step PR with intermediate
  CI greens is the safer landing strategy.
- *Port via PR comments / cherry-picks from the historical repo's
  git log*: rejected — the historical repo isn't a parent of this
  monorepo's git history, and replaying its commits adds noise. A
  squashed import per step is cleaner.

---

## R3. JSON contract — Rust `serde_json` ↔ Python Pydantic shapes

**Decision**: A flat, additive JSON document keyed by stable
engine-internal check identifiers. Concrete shape:

```json
{
  "schema": "ree-debug-engine",
  "version": "<git-sha>",
  "host_id": "ve-de-apollo",
  "started_at": "2026-05-07T12:13:14.000Z",
  "completed_at": "2026-05-07T12:13:21.000Z",
  "outcome": "complete",
  "checks": [
    {
      "id": "main_can_bus_reachable",
      "status": "Pass",
      "raw_detail": "candump can0: 1 frame in 47ms",
      "duration_ms": 47
    },
    {
      "id": "dns_resolver_internal",
      "status": "Warn",
      "raw_detail": "Only public DNS configured; no RFC1918 resolver visible.",
      "duration_ms": 12
    }
  ]
}
```

- Top-level `version` is set at build time from the workspace's git
  SHA via `vergen` or a small `build.rs` (`git rev-parse --short
  HEAD`). The Python backend's startup self-check matches this
  against an expected SHA range stored in `backend/pyproject.toml`
  metadata.
- `outcome` matches the Python-side `RunOutcome` enum from 001:
  `complete | partial | unreachable | timeout`. The CLI binary
  computes `outcome` itself from the per-check distribution + a
  reachability signal from the SSH layer; the Python backend
  trusts what the CLI says.
- `checks[].status` is `Pass | Warn | Fail`, mapped on the Python
  side to `working | warning | error` per FR-004a.
- `checks[].id` is the same stable identifier the engine uses
  internally — the catalog (`backend/src/vayobd/checks/catalog.py`)
  keys off this for operator-visible name + category + recommended
  action.
- `raw_detail` is a free-form string, scrubbed by the Python side
  for VIN/PII per FR-018 before persistence.
- `duration_ms` is informational; not surfaced in the result view
  in v1 but useful for audit logs.

**Rationale**:
- Flat shape (no nested "groups" — those are a frontend rendering
  concern from the catalog's category) keeps the JSON document
  cheap to derive on the Rust side and trivial to validate on the
  Python side.
- Embedding the engine's own status enum (`Pass/Warn/Fail`) and
  doing the mapping in Python keeps the engine library agnostic of
  the Python side's enum — the engine ships the engineering truth,
  the Python catalog ships the operator-visible truth.
- The git-SHA `version` field obviates separate semver versioning
  per the FR-003a clarification.

**Alternatives considered**:
- *MessagePack or CBOR*: rejected — JSON is debuggable at the shell
  (`cat | jq`), the CLI binary is run interactively during dev, and
  parse cost is not a bottleneck for ~25 records per run.
- *NDJSON streaming (one check per line)*: tempting for "live"
  per-item progress in the SPA, but FR-009 inherited from 001 only
  asks for a generic "running" spinner, and the FR-024 wait-only +
  FR-028 blank-on-entry contract means streaming buys nothing the
  spec asks for.
- *Versioned schema field with semver*: rejected per FR-003a — the
  monorepo collocation makes the git SHA the contract.

---

## R4. Status / category mapping — implementation specifics

**Decision (status mapping, FR-004a)**:

| Engine `status` | Python `ItemStatus` | Frontend rendering |
|---|---|---|
| `Pass` | `working` | "Working" group; green check icon |
| `Warn` | `warning` | "Needs attention" group; **amber** tint, icon distinct from error |
| `Fail` | `error` | "Needs attention" group; **red** tint |

`warning` items MUST carry a `recommended_action_key` just like
`error` items (FR-004b's parity rule). The catalog enforces this:
the `CheckSpec` Pydantic model fails validation if a check whose
status maps to `warning` or `error` has no `recommended_action_key`.

**Decision (category set, FR-006)**:

| Category | What goes here |
|---|---|
| `Communication` | SSH reachability; CAN buses up; APP_CAN traffic rate; XCP active probe; REECU heartbeat; lobby polling-loop; ROS-node liveness; Vay private-endpoint DNS resolvability; latency monitors |
| `Hardware` | Cameras (front/left/right); USB inventory; e-Stop channels; brake/accelerator/steering inputs; input devices on telestation |
| `Configuration` | Vehicle integration config valid; telestation config valid; expected USB inventory match; DNS resolver class (warns if only public DNS) |
| `Software` (NEW) | vDrive package vs manifest drift; Aurix MCU firmware; SEC FPGA gateware; REECU hardware rev; REECU gateway container; per-session ROS containers |
| `Calibration` (NEW) | SAS calibration (TS only); GNSS yaw-rate watchdog (VE only) |

The mapping is a Python dict in `backend/src/vayobd/checks/
catalog.py` keyed by engine check id. SC-003's jargon audit checks
the catalog file in one place.

**Rationale**:
- The status mapping is mechanical and lossless; the engine's three
  states project cleanly onto our extended enum.
- The category mapping needed a per-check decision in some cases
  (e.g., DNS resolver lives in `Configuration` because the operator
  fixes it by editing config, not by replacing hardware). The
  mapping table above is the proposed assignment; refinements happen
  during catalog implementation in tasks.md, not here.

**Alternatives considered**:
- *Auto-categorise from check id prefix* (e.g., `dns_*` → Network):
  rejected — too magical, fragile to engine refactors.
- *Per-host-class category override*: rejected — categories don't
  vary by host class, only the per-class catalog membership does.

---

## R5. Settings file — location, format, validation

**Decision**:
- File path: `${XDG_CONFIG_HOME:-${HOME}/.config}/vayobd/settings.toml`.
  Honours XDG; falls back to `~/.config/vayobd/settings.toml` when
  `$XDG_CONFIG_HOME` is unset.
- Format: TOML. Single top-level `[inventory]` table with one
  required key `path = "/abs/or/expanded/path"`.
- Validation flow on every backend start AND on every `POST
  /api/settings/inventory-path`:
  1. Path resolves (expand `~`, normalise to absolute).
  2. Path exists on disk and is a directory.
  3. `<path>/org/vay/inventory.yaml` exists and parses as YAML.
  4. The YAML root contains an iterable that the loader can map onto
     the data-model `Host` shape (at least one host).
- Validation failures return structured error codes the SPA can
  render: `path_missing`, `path_not_a_directory`, `inventory_yaml_missing`,
  `inventory_yaml_unparseable`, `inventory_yaml_empty`. Each maps to
  a `message_key` per Constitution III.
- On first launch (no settings file), the backend serves a 200
  response from `GET /api/settings/inventory-path` with a body
  signalling "not configured" — the SPA renders the setup card.

**Rationale**:
- TOML is Python-stdlib (3.11+ ships `tomllib`), human-editable,
  and the standard for app-level Python config. Avoids YAML for
  user config (YAML is too forgiving — risks of accidental
  multi-document files etc.).
- XDG compliance is one extra `os.environ.get` call and matches
  what `~/.config` means on most operator machines anyway.
- Synchronous validation keeps SC-002 (under-30 s setup) trivially
  achievable — disk reads are microseconds.

**Alternatives considered**:
- *YAML for config* (matches inventory file): rejected — TOML's
  stricter structural rules avoid the "I added a stray colon and
  the app stopped working" class of bug.
- *JSON config*: rejected — TOML is more comment-friendly, and
  Python's `tomllib` is read-only by design (we use a tiny custom
  writer for the persist step, see data-model.md).
- *Env var (`VAYOBD_INVENTORY_PATH`) as the canonical mechanism*:
  rejected — the spec story is "operator picks a path on first
  launch", which only works with persisted state. Env vars stay
  available as an override (`VAYOBD_INVENTORY_PATH` wins over the
  TOML if set), useful for CI / containers.

---

## R6. `ree-debug-cli` invocation lifecycle

**Decision**: The Python `ReeCliExecutor` invokes the CLI binary as
follows:

```python
cmd = [
    str(cli_bin_path),
    "report",
    "--host", host.id,
    "--inventory", str(settings.inventory_path),
    "--json",
]
proc = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
try:
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(), timeout=settings.run_timeout_seconds
    )
except TimeoutError:
    proc.send_signal(signal.SIGTERM)
    await asyncio.sleep(2.0)             # grace
    if proc.returncode is None:
        proc.kill()
        await proc.wait()
    return ExecutorResult(outcome=RunOutcome.TIMEOUT)
```

- Subprocess args are *fixed* — no shell, no glob expansion, no
  user-supplied argv outside `host.id` (which is regex-validated
  against the existing `HostId` pattern).
- `stderr` is captured and surfaced *only* in the audit log on
  non-zero exit (FR-018: it's PII-scrubbed by the same
  `scrub_raw_detail` helper as `raw_detail`).
- On timeout: SIGTERM, grace 2 s, then SIGKILL if still alive. The
  Rust side's tokio runtime catches SIGTERM and tears down its SSH
  ControlMaster cleanly; the SIGKILL fallback is for the
  pathological "engine wedged in a syscall" case.
- Exit code 0 + valid JSON → success path.
- Exit code 0 + malformed JSON → `outcome: unreachable` with a
  banner-worthy log line.
- Exit code != 0 → `outcome: unreachable` with stderr captured to
  audit.
- The first invocation per backend boot is `ree-debug-cli --version`
  (no host arg) for the FR-007 / FR-003a startup self-check;
  failure of that check is what produces `engine_unavailable` /
  `engine_incompatible`.

**Rationale**:
- Plain stdlib `asyncio.subprocess` + `asyncio.wait_for` mirrors
  the existing 001 timeout pattern in `runner.py::execute_run`. No
  new dependency, no shell.
- SIGTERM-then-SIGKILL is the standard pattern for cooperative
  shutdown of a process that owns network resources (SSH
  ControlMaster); aligns with what `tokio` expects for graceful
  shutdown.
- A startup `--version` check catches "binary not built" and
  "binary built from a wildly different SHA" cases before any
  operator-triggered run hits the engine — turning a runtime error
  into a startup error is the right move for SC-004.

**Alternatives considered**:
- *Long-lived engine daemon (gRPC / Unix socket)*: rejected for v1
  — the spec explicitly chose subprocess-per-run (FR-003), and runs
  are bounded at 30 s anyway. Daemon-shaped optimisation is
  measurable but a v2 concern.
- *PyO3 bindings calling `run_checks` directly in-process*:
  rejected per the 2026-05-07 clarify session — adds cross-compile,
  wheel-building, and version-pinning complexity for marginal
  per-call latency gain.

---

## Summary of unresolved items at the end of Phase 0

None. Every implementation question implied by the spec is closed
above. The engine workspace bootstrap, port plan, JSON contract,
status/category mapping, settings file format, and subprocess
lifecycle are all pinned. Phase 1 (data-model.md, contracts/,
quickstart.md) flows directly from these decisions.
