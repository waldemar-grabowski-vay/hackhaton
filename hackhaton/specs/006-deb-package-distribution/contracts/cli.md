# Contract — `vayobd` CLI

**Installed at**: `/usr/bin/vayobd` (symlink to `/usr/lib/vayobd/bin/vayobd-launcher`).
**Implementation**: `backend/src/vayobd/cli.py` — a thin `argparse` entry point that dispatches to the existing backend / install modules.
**Runs as**: the invoking user. Refuses to run as root with a plain-language message (Constitution Principle III).

This contract is what the spec's user stories rely on for the **CLI surface** of FR-008 and is also the actual binary that the `vayobd.desktop` launcher invokes when the user clicks the app icon.

## Subcommands

### `vayobd run`

Default action; this is what the desktop launcher and `vayobd` (no args) invoke.

**Behaviour**:

1. Load `manifest.toml` (path from `Settings.manifest_path`).
2. Load `manifest-state.toml` (create if absent).
3. **If `is_first_run`**:
   1. Probe credentials (research § 3).
   2. On any failure → print the FR-005 plain-language message to stderr, exit `2`.
   3. On success → clone every repo per the manifest, then continue.
4. Start uvicorn bound to `127.0.0.1` on a free port (default `8000`; configurable via `--port`).
5. Open the user's default browser to the URL (skipped under `--no-browser`).
6. Stream uvicorn output. Ctrl+C ⇒ graceful shutdown.

**Flags**:

| Flag | Default | Effect |
|---|---|---|
| `--port N` | `8000` | uvicorn listen port. If busy, exit `4` with a plain message. |
| `--no-browser` | false | Don't try to open a browser. Useful for SSH / VS Code Remote sessions. |
| `--manifest PATH` | from settings | Override manifest location (dev / test). |

**Exit codes**:

| Code | Meaning |
|---|---|
| 0 | uvicorn exited cleanly (Ctrl+C). |
| 2 | Credential probe failed; FR-005 message printed. |
| 3 | Clone failed; per-repo plain-language message printed. |
| 4 | Port in use or other bind error. |
| 1 | Anything else (unexpected exception; full traceback to `~/.cache/vayobd/last-error.log`, never to stderr — Principle III). |

### `vayobd refresh`

Re-runs the manifest-driven clone/fetch step against every repo in `manifest.toml`, without starting the web UI. This is the CLI half of FR-008.

**Behaviour**:

1. Load manifest + state.
2. Probe credentials (cached probe from `manifest-state.toml` is honoured if < 1 hour old, otherwise re-probed).
3. For each repo: `git fetch` + fast-forward to the manifest's `branch`. If the working tree is dirty (shouldn't happen on a manifest-managed clone), report and skip that repo, do not destroy local changes.
4. Update `manifest-state.toml` atomically (write-tmp + rename) so a crash mid-refresh never leaves a half-written state file (FR-009).
5. Print a single-line summary per repo: `ree-vehicle-configs: ok (was a1b2c3d, now f0e1d2c)`.

**Flags**:

| Flag | Default | Effect |
|---|---|---|
| `--repo ID` | all | Refresh only the named repo (debugging aid). |
| `--quiet` | false | Suppress per-repo lines; print only the overall outcome. |

**Exit codes**:

| Code | Meaning |
|---|---|
| 0 | Every repo refreshed successfully. |
| 5 | At least one repo failed; others may have succeeded. State on disk is consistent (FR-009): each repo is either fully at its old revision or fully at the new one. |
| 2, 3, 4, 1 | Same as `vayobd run`. |

### `vayobd doctor`

Read-only health probe. Prints a single page of diagnostics intended for support engineers to ask the user to paste into a ticket.

**Output (example)**:

```
VayOBD version: 0.6.0 (commit a1b2c3d, built 2026-05-11)
Python:         3.12.3 (system)
Manifest:       /usr/share/vayobd/manifest.toml (version 1, 2 repos)

Credential probe:
  SSH (ssh -T git@github.com):     ✓ authenticated as waldemar-grabowski-vay
  gh auth status:                  not installed
  Git credential helper:           not probed (SSH already worked)

Repos:
  ree-vehicle-configs  ok  last synced 2026-05-11T09:42:48Z  HEAD a1b2c3d
  ree-reecu            ok  last synced 2026-05-11T09:43:12Z  HEAD f0e1d2c

Engine binary: /usr/lib/vayobd/bin/ree-debug-cli (c5b72fa)
errq source:   ~/GitHub/ree-reecu/platform/tools/errq (219 errors, 32 groups)
```

**Exit codes**:

| Code | Meaning |
|---|---|
| 0 | Everything healthy. |
| 1 | At least one anomaly detected; details in the output. Never an unhandled exception. |

### `vayobd --version`

Prints the version line shown by `doctor`, then exits `0`. Satisfies FR-013.

## Refusal: running as root

`vayobd run`, `vayobd refresh`, and `vayobd doctor` all check `os.geteuid()`. If `0`, they exit `6` with:

```
VayOBD must run as your normal user, not as root.
The `.deb` installs system files at install time; running the app
itself as root would put your cached repos in /root and break things
for everyone else on this machine.
```

Justification: FR-015 + Principle III.
