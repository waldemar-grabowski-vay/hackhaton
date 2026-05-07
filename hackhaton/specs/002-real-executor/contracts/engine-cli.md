# `ree-debug-cli` Contract — CLI + JSON

The contract surface between the Python backend and the
`ree-debug-cli` Rust binary. Same git SHA = same contract, per
FR-003a; this file documents what that contract *is* at any given
SHA so the Pydantic models in `data-model.md` and the binary's
`clap` derivation stay in lockstep.

---

## Invocation

```text
ree-debug-cli report --host <HOST_ID> --inventory <PATH> --json
ree-debug-cli --version
ree-debug-cli --help
```

### `report` subcommand

| Arg | Required | Type | Description |
|---|---|---|---|
| `--host <id>` | yes | `HostId` regex `^(ve\|ts)-de(-[a-z0-9-]+)+$` | The host to run the full check fan-out against. |
| `--inventory <path>` | yes | absolute path | Local clone of `ree-vehicle-configs`. Engine reads `<path>/org/vay/inventory.yaml`. |
| `--json` | yes (v1) | flag | Required in v1; reserves stdout for the JSON document. v1 has no other output mode — the flag exists to leave room for `--text` etc. without breaking existing callers. |
| `--ssh-config <path>` | no | path | Override `~/.ssh/config`. Defaults to the engine process owner's home. |
| `--ssh-known-hosts <path>` | no | path | Override `~/.ssh/known_hosts`. |

**Forbidden** (must NOT appear in v1's CLI surface): `--bring-up-bus`,
`--toggle-debug`, anything that would invoke a mutating action. The
mutating-actions assumption from `spec.md` is enforced by the
engine library not exposing those entry points to the CLI binary.

### `--version`

Prints `ree-debug-cli <git-sha>` to stdout, exits 0. Used by the
backend's startup self-check (FR-003a / FR-007). The git SHA is
embedded at build time via `build.rs`.

### `--help`

Prints clap-derived help to stdout, exits 0.

---

## Exit codes

| Code | Meaning | Python interpretation |
|---|---|---|
| `0` | Engine ran the full per-host fan-out and produced an `EngineReport`. Per-check pass/warn/fail is data, not engine failure. | Parse stdout as `EngineReport`; map per FR-004a + R3 / R4. |
| `1` | Generic engine-internal error. JSON `EngineError` written to stderr. | Map to `engine_unavailable` if `kind == InventoryMissing | UnknownHostId`; otherwise `outcome: unreachable` with stderr captured to audit. |
| `2` | Inventory layer failed (missing / unparseable file). JSON `EngineError` on stderr. | Surface to the SPA as `inventory_unavailable` if no `[inventory]` is configured at all; otherwise as `inventory_yaml_unparseable`. |
| `3` | SSH startup layer failed (no key, ControlMaster refused, etc.). JSON `EngineError` on stderr. | Map to `outcome: unreachable` (network/host issue, not engine bug). |
| `64` | CLI argument validation failed (bad `--host` regex, missing flag). Plain-text human-readable message on stderr. | Should never happen in production — backend validates host id before calling. Treat as an `engine_incompatible` (the binary is wired wrong). |
| `>= 128` | UNIX-signal termination (e.g., 143 = SIGTERM, 137 = SIGKILL). | Map to `outcome: timeout` if the backend sent the signal due to FR-008's 30 s ceiling; otherwise `outcome: unreachable`. |

---

## stdout — `EngineReport` JSON shape (success path)

Verbatim from `data-model.md` Layer 1. Example:

```json
{
  "schema": "ree-debug-engine",
  "version": "9697a5e",
  "host_id": "ve-de-apollo",
  "host_type": "vehicle",
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
      "id": "expected_front_camera_connected",
      "status": "Fail",
      "raw_detail": "lsusb: device LI_IMX490 JP2J0208 not present",
      "duration_ms": 12
    },
    {
      "id": "dns_resolver_internal",
      "status": "Warn",
      "raw_detail": "Only public DNS configured; no RFC1918 resolver visible.",
      "duration_ms": 9
    }
  ]
}
```

**Invariants** (engine MUST guarantee, backend MAY assert):
- `schema` is always exactly `"ree-debug-engine"`.
- `version` is always present (build.rs ensures this — the build
  fails if the SHA can't be resolved).
- `host_id` matches the requested `--host`; the engine never
  silently switches host.
- `checks[].id` is unique within the report.
- `checks[].status` is one of exactly `Pass | Warn | Fail`.
- `checks[]` is non-empty when `outcome ∈ {complete, partial}` and
  empty when `outcome ∈ {unreachable, timeout}`.
- All timestamps are UTC ISO 8601 with `Z` suffix.

---

## stderr — `EngineError` JSON shape (failure path)

Engine writes a single line of JSON, then exits non-zero:

```json
{"kind": "unknown_host_id", "message": "host 've-de-not-real' not in inventory at /home/op/.../inventory.yaml"}
```

The Python backend captures stderr, scrubs it for PII via the same
`scrub_raw_detail` helper used for `raw_detail` (FR-018), and stores
it in the run audit log only — never in the SPA response body.

---

## stderr — log lines (informational, success path)

The engine MAY also write log-shaped lines to stderr during a
successful run (e.g., "establishing SSH master to ts-de-ber-zeus"
... "SSH master ready in 213ms"). These MUST be one-line, MUST NOT
be JSON-shaped (so the backend's stderr parser doesn't confuse
informational logs with `EngineError`), and MUST NOT contain VIN /
PII. The backend SHOULD attach these to the audit log on debug
levels and discard them at info+.

The single-line JSON `EngineError` shape is reserved exclusively
for the **last** line on stderr when the binary exits non-zero;
everything earlier is informational.

---

## Process / signal behaviour

- The engine MUST install a SIGTERM handler that tears down the SSH
  ControlMaster cleanly and exits with code 143.
- The engine MUST handle SIGINT (Ctrl-C) the same way (for
  developer convenience when running `ree-debug-cli` by hand).
- The engine MUST NOT touch stdout after the JSON document is
  printed (i.e., one write of the final report, then exit).
- The engine MUST NOT prompt for input (`--host` is required;
  there's no interactive fallback).

---

## Versioning & forward compatibility

- `version` in stdout is the build-time git SHA of the workspace.
- The Python backend's startup self-check runs `ree-debug-cli
  --version` and stores the SHA in the running process's metadata.
  Each persisted `DiagnosticRun` record carries this SHA in its new
  `engine_version` field for audit (data-model.md).
- There is no semver layer in v1 (FR-003a). Breaking schema changes
  bump the workspace's git SHA; the backend's startup check ensures
  the binary in use was built from a SHA the backend recognises.
- *Why no semver*: monorepo collocation. The engine library, the
  CLI binary, and the Python backend live in one repo and ship from
  one SHA. The contract is the SHA. A future split out of the
  monorepo would re-introduce semver.
