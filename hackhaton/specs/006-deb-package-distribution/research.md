# Research — VayOBD .deb package

**Date**: 2026-05-11
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

Phase 0 resolves the open technical questions in `plan.md` § Technical Context before any code or contracts are written. Each subsection is structured as **Decision / Rationale / Alternatives considered** per the workflow.

---

## 1. Packaging tool — `nfpm` vs. `dh_make` / `debhelper` vs. `fpm` vs. Snap

**Decision**: Use [`nfpm`](https://nfpm.goreleaser.com/) (single-file YAML, no debhelper, statically-linked Go binary). One file (`packaging/nfpm.yaml`) describes the package; one command (`nfpm package --packager deb -f packaging/nfpm.yaml`) produces `vayobd_<version>_amd64.deb`.

**Rationale**: Constitution Principle I (Simplicity First) — `nfpm.yaml` is ~30 lines and contains everything we need: name, version, depends/recommends, files (mapping `dist/usr` → `/usr` in the package), maintainer scripts. No `debian/` directory, no `rules` file, no `control` template, no `dh_python3`, no source-package round-trip. Building takes <2 seconds on the developer's laptop, runs identically in CI. Matches FR-014 / SC-007 (single documented command, deterministic enough).

**Alternatives considered**:
- **`dh_make` + `debhelper`** (the canonical Debian Way): rejected — produces ~10 files of boilerplate plus a `debian/changelog` discipline this project doesn't need. Optimised for upstream-to-Debian publication, not for a single internal `.deb`. Violates Principle I.
- **`fpm`**: viable alternative; chose `nfpm` because it is a single static binary (no Ruby toolchain to install) and its YAML config doubles as the source of truth (vs. `fpm`'s long shell-flag invocations). Difference is modest.
- **Snap**: rejected — confined filesystem access fights the spec's "clone into `~/.cache/vayobd`" requirement, requires a snap-store account or sideload dance, and adds a containerised runtime layer that buys nothing for an internal LAN tool.
- **AppImage / Flatpak**: rejected — not `.deb` per the spec, and the user explicitly asked for `apt`-compatible packaging.

---

## 2. Where does first-run work happen — maintainer scripts vs. user-level launcher?

**Decision**: Maintainer scripts (`postinst`, `postrm`) only install **static files** and (on `postinst`) refresh the desktop-launcher cache. **All** first-run work — credential probing, clones, settings-file bootstrap — happens inside `vayobd run` when the user invokes the launcher for the first time, running as the user.

**Rationale**:
- Constitution Principle III (Non-Technical UX): a failed clone during `apt install` would print developer-style errors to a root shell the user never sees, then leave the install in a "succeeded but broken" state — exactly the failure mode Story 2 forbids.
- FR-015: "MUST run as the invoking user". Maintainer scripts run as root and could not access the user's `ssh-agent`, `gh` token, or credential helper anyway.
- FR-011 / FR-012: keeping per-user state out of maintainer scripts means `apt remove` / `apt upgrade` automatically preserve the cache without special-case logic.

**Alternatives considered**:
- Run clones inside `postinst`: rejected as above — wrong user, wrong privileges, wrong UX surface.
- Use a per-user systemd timer that wakes on login: rejected — overkill, harder to debug, and Q2 ruled background refresh out of scope for v1.
- Use a `dpkg-trigger` to mark "first run pending": rejected — over-clever; a sentinel file (`~/.cache/vayobd/manifest-state.toml` absent ⇒ first run) is one line of Python and obvious.

---

## 3. First-run credential probe (FR-004) — implementation

**Decision**: A pure-Python module (`backend/src/vayobd/install/credentials.py`) that, in order:

1. **SSH probe** — runs `ssh -T -o BatchMode=yes -o ConnectTimeout=5 git@github.com`. Exit code 1 (GitHub's "successfully authenticated, but GitHub does not provide shell access") = success. Anything else = move on. Confirmed working in this session: the user authenticated as `waldemar-grabowski-vay` via SSH.
2. **`gh auth` probe** — if `gh` binary present on `$PATH`, runs `gh auth status --hostname github.com 2>&1`. Exit code 0 = success. The clone will use `gh auth token` to populate an HTTPS credential helper for the duration of the run (`GIT_ASKPASS` pointing at a tiny shim, or `git -c credential.helper=...`).
3. **System credential helper probe** — runs `git config --get-all credential.helper` and tries `git ls-remote https://github.com/<known-public-repo>` (e.g., `Reemote/vayobd-public-canary` if we add one — or fall back to any GitHub-hosted repo we can list anonymously) with `GIT_TERMINAL_PROMPT=0`. If git resolves credentials without prompting, the helper is working.

If all three fail, raise a typed error that the CLI / API translates into the FR-005 plain-language message.

**Rationale**: Each probe is fast (<5 s with `ConnectTimeout`), non-interactive (`BatchMode=yes`, `GIT_TERMINAL_PROMPT=0`), and uses only system tools already declared as `Depends`/`Recommends`. The probe outcome is captured in `manifest-state.toml` (FR-004a) for support visibility.

**Alternatives considered**:
- Always try the clone and parse stderr: rejected — slow on failure (the clone itself can block on auth prompts), and error messages from `git` are inconsistent.
- Require the user to pick a credential surface in a setting: rejected — adds a setup question that violates SC-002 ("zero manual edits").
- Use a libgit2 binding (`pygit2`) instead of shelling out to `git`: rejected — adds a compiled dependency for negligible benefit; shelling out to `git` is the standard way and gives us identical auth semantics to whatever the user already has working.

---

## 4. Required-repos manifest format — TOML

**Decision**: A TOML file shipped at `/usr/share/vayobd/manifest.toml`, with schema documented in `contracts/manifest.md`. Loaded once per `vayobd run` startup; cached in memory; re-read on `vayobd refresh`. Fields: array-of-tables `[[repo]]` with `id`, `url`, `target_path`, optional `branch`, optional `sparse_paths`.

**Rationale**: The backend already uses TOML for `~/.config/vayobd/settings.toml`, so the Pydantic/`tomllib` stack is already in place. TOML is human-readable enough that the FR-006 promise ("one-line fix when an upstream renames") is genuinely true — `git diff` on a TOML file is obvious to a non-Python reader.

**Alternatives considered**:
- YAML: rejected on Principle I — adds `PyYAML` for a single file we already have `tomllib` for. (`PyYAML` is already in the venv for the inventory loader, but the manifest is structurally simpler and TOML is just as good.) Actually — the existing inventory loader uses PyYAML, so YAML wouldn't add a dep. Still pick TOML for symmetry with `settings.toml`.
- JSON: rejected — no comments. The manifest will accumulate `# why this repo exists` comments over time.
- Hardcoded Python constant in `clone.py`: rejected — FR-006 explicitly wants the manifest as a separate file so a rename is a one-line PR, not a code change.

---

## 5. First-run credential-failure message (FR-005) — copy

**Decision**: Reuse the established Vay tone (terse, no jargon, "do this, then retry"). Exact draft:

```
VayOBD couldn't read your GitHub credentials.

I tried, in order:
  • SSH (ssh -T git@github.com)         → failed: <reason>
  • GitHub CLI (gh auth status)         → not configured
  • System credential helper            → not configured

To fix this, do one of:
  • Add your SSH key to GitHub and make sure ssh-agent has it loaded, OR
  • Run `gh auth login` (the GitHub CLI is installed by this package)

Then run `vayobd run` again. No data has been changed.
```

Same content is returned by the API (in machine-readable form: `{tried: [...], suggestions: [...]}`) and rendered by both `vayobd run` (stderr) and the future first-run web UI (Story 2 acceptance scenario 1). No `apt install` rerun is needed to retry.

**Rationale**: Constitution Principle III. Names every surface tried (FR-004a) and the next concrete action. Reassures the user nothing was changed (Story 2 AS-3: no partial cache). Uses plain English, never the word "auth backend" or similar.

**Alternatives considered**:
- A pretty TUI / dialog box: rejected — Principle I and "no `npm` toolchain at runtime"; the launcher is a CLI that prints text, and the same text feeds the API.
- Open a browser tab to a setup wizard: rejected — circular; the wizard needs the running app, which the missing credentials block.

---

## 6. In-app refresh button (FR-008) — wiring

**Decision**: One new HTTP endpoint pair (`POST /api/refresh`, `GET /api/refresh/status`) documented in `contracts/http-api.md`. The button lives in a new `StalenessBanner.tsx` component rendered at the top of the inventory page when `manifest-state.toml` says any required repo is older than the threshold (configurable; default 24h). The CLI command `vayobd refresh` calls the same code path directly (no HTTP round-trip).

**Rationale**:
- Single underlying refresh function ⇒ FR-008 / FR-009 "same end state" is enforced by construction, not by parallel implementations.
- Banner is exactly one new component; it consumes a small slice of an existing inventory query result.
- Status endpoint allows the UI to disable the button + show a spinner without polling refresh's HTTP body for completion.

**Alternatives considered**:
- WebSocket for progress streaming: rejected — Principle I; refresh of two repos is a 30 s operation, polling `/api/refresh/status` every 1 s is fine and matches how the 002/004 spec handles similar long ops.
- Make refresh fully async with a server-side queue: rejected — single-user laptop, sequential is simpler and correct.

---

## 7. Loopback HTTP — constitutional exception, with bounded scope

**Decision**: Continue to serve the SPA + API over plain HTTP on `127.0.0.1` only. Document the exception in `plan.md` § Complexity Tracking. Bind explicitly to `127.0.0.1` in uvicorn (never `0.0.0.0`) so that the .deb cannot accidentally expose the API on the laptop's LAN.

**Rationale**: The constitution's HTTPS clause says "Production traffic MUST be served over HTTPS." A loopback-only local tool is not "production traffic" in the spirit of that clause — there is no network path between client and server. Forcing HTTPS would require either (a) a self-signed cert with a per-launch browser-trust warning, directly violating Principle III, or (b) a per-user CA install routine, which violates FR-001 ("no manual configuration"). Both are worse than the status quo.

**Alternatives considered**:
- mkcert + per-user CA install on first run: rejected — installs a CA into the user's trust store as a side effect of installing a diagnostic tool; security-review-rejectable on its face.
- Skip the browser entirely; ship a native Electron-like shell: rejected — explicitly out of scope per Web App Standards ("browser-based only").
- Serve over Unix domain socket: appealing, but browsers can't fetch from a UDS without a helper. Rejected.

---

## 8. Packaging-time vs. install-time vs. first-run-time: what goes where

| Concern | When | Where |
|---|---|---|
| Build Rust engine (`ree-debug-cli`) | Build time (CI / dev laptop running `./packaging/build.sh`) | Output to `engine/target/release/`, copied into `dist/usr/lib/vayobd/bin/` |
| Build SPA (`npm run build`) | Build time | Output to `frontend/dist/`, copied into `dist/usr/share/vayobd/spa/` |
| Bundle Python wheel + venv | Build time | Resolved via `uv pip compile` against the project's `pyproject.toml`, vendored into `dist/usr/lib/vayobd/venv/` (relocatable). System Python 3.12 provides the interpreter. |
| Install `vayobd` shim to `/usr/bin/vayobd` | Install time (`postinst`) | nfpm's `contents:` mapping |
| Refresh desktop database / `update-desktop-database` | Install time (`postinst`) | One line in `postinst.sh` |
| Probe credentials & clone repos | First run as user | `backend/src/vayobd/install/clone.py` |
| Subsequent refreshes | User-initiated | Same module, via `vayobd refresh` or `POST /api/refresh` |

**Rationale**: Each artefact is built once at packaging time so user laptops never need `npm` / `cargo` / `uv`. Per-user work happens as the user. Maintainer scripts contain ≤5 lines each.

**Open follow-up (planning-phase deferred from spec)**: bundling a Python venv vs. relying on `python3-fastapi` style system packages. v1 vendor the venv — system Python on 24.04 is 3.12 (matches our `pyproject.toml` requirement), but the FastAPI/uvicorn versions we depend on are newer than what `apt` ships. Vendoring is ~80 MB of Python wheels; acceptable for an internal tool.

---

## 9. CI / build reproducibility (FR-014, SC-007)

**Decision**: `./packaging/build.sh` is the single documented command. It runs (in order): `cargo build --release` in `engine/`, `npm ci && npm run build` in `frontend/`, `uv pip compile + uv pip sync` into a relocatable venv, then `nfpm package`. The script accepts `--version` (defaults to `git describe --always --dirty`). Two builds from the same commit on the same Ubuntu 24.04 image produce byte-identical `.deb` files modulo build timestamps in the archive; the `version` and `Vcs-Git` (commit SHA) headers are identical, which is what "functionally equivalent" requires.

**Rationale**: Real byte-level reproducible builds would require pinning every wheel's mtime and disabling all timestamp use in `nfpm`. That's a project of its own and SC-007 only asks for "functionally equivalent". The version metadata in `dpkg -s vayobd` and `vayobd --version` is enough to satisfy "what version do I have?" (FR-013).

**Alternatives considered**:
- Full bit-reproducibility with `disorderfs` + `SOURCE_DATE_EPOCH`: rejected for now — disproportionate effort; revisit if the team adopts Reproducible Builds practices project-wide.
