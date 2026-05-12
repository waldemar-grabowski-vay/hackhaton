# Quickstart — building and using the VayOBD `.deb`

**Audience**: platform engineers building the package, plus end users installing it.

## Build the .deb

From a clean checkout:

```bash
./packaging/build.sh
# → dist/vayobd_<version>_amd64.deb
```

`build.sh` does, in order:

1. `cargo build --release` in `engine/` → `engine/target/release/ree-debug-cli`
2. `npm ci && npm run build` in `frontend/` → `frontend/dist/`
3. `uv pip compile` + `uv pip sync` into a relocatable venv at `packaging/build/venv/`
4. Stage everything under `packaging/build/dist/` matching the on-disk layout in `data-model.md` § 4
5. `nfpm package --packager deb -f packaging/nfpm.yaml --target dist/`

Two builds from the same git commit on the same Ubuntu 24.04 image are functionally equivalent: identical version, identical SHA, identical `dpkg-deb -I` summary. Bit-for-bit reproducibility is not promised in v1 (research § 9).

Verify the package:

```bash
dpkg-deb -I dist/vayobd_*.deb       # control fields, Depends, Recommends
dpkg-deb -c dist/vayobd_*.deb       # full file list
```

Run the packaging smoke test (boots a clean `ubuntu:24.04` container, installs the `.deb`, asserts `vayobd --version` and a fixture-mode startup):

```bash
./scripts/package-smoke-test.sh dist/vayobd_*.deb
```

## Install on a clean laptop

```bash
sudo apt install ./vayobd_*.deb
# Pulls in: git, python3 (>= 3.12), libfontconfig1 (engine dep), …
# Recommends: gh
```

`apt remove vayobd` and `apt upgrade` work as you'd expect: package files in `/usr` are replaced/removed; per-user state in `~/.cache/vayobd/` and `~/.config/vayobd/` is preserved (FR-011, FR-012). To fully purge per-user state:

```bash
rm -rf ~/.cache/vayobd ~/.config/vayobd
```

## First-run smoke test

On a fresh laptop with working GitHub access (SSH key, or `gh auth login` done):

```bash
vayobd        # or click the desktop launcher
```

Expected: the credential probe finds your SSH key, both repos clone (~30-60 s on a typical connection), the browser opens `http://127.0.0.1:8000`, and the inventory list is populated. The `manifest-state.toml` now records `credential_surface_used = "ssh"` and per-repo timestamps.

On a fresh laptop **without** GitHub credentials:

```bash
vayobd
# → stderr: VayOBD couldn't read your GitHub credentials.
#           I tried, in order:
#             • SSH (ssh -T git@github.com)        → failed: Permission denied
#             • GitHub CLI (gh auth status)        → not configured
#             • System credential helper           → not configured
#           To fix this, do one of:
#             • Add your SSH key to GitHub and make sure ssh-agent has it loaded, OR
#             • Run `gh auth login` (the GitHub CLI is installed by this package)
#           Then run `vayobd run` again. No data has been changed.
# Exit code: 2
```

`ls ~/.cache/vayobd/` afterwards shows the directory is empty — no partial clones. Run `gh auth login`, re-run `vayobd`, and it now reaches the working state.

## Refresh

CLI:

```bash
vayobd refresh
# ree-vehicle-configs: ok (was a1b2c3d, now f0e1d2c)
# ree-reecu:           ok (was b4a5c6d, now 7e8f9a0)
```

UI: open `http://127.0.0.1:8000`. If any repo is older than 24 h, the StalenessBanner shows above the inventory list with a "Refresh now" button. Clicking it issues `POST /api/refresh`; the button disables, a spinner appears, and the banner updates as each repo completes (driven by `GET /api/refresh/status` polled every 1 s).

## Releasing a new .deb (platform-engineer runbook)

1. **Pick a version.** From `main`, ensure `git status` is clean, then either tag (`git tag -a v0.6.0 -m "..."`) or let `git describe --always --dirty` derive a snapshot version automatically.
2. **Build.** `./packaging/build.sh` produces `dist/vayobd_<version>_amd64.deb` in 30–60 s on a warm cache.
3. **Smoke-test.** `./scripts/package-smoke-test.sh dist/vayobd_<version>_amd64.deb` boots the freshly-installed package inside a clean `ubuntu:24.04` container and asserts `/api/health` returns 200.
4. **Determinism.** Run the build a second time on the same commit. The smoke test, when it sees both `.deb`s in `dist/`, diffs `Version` + `Depends` + `Recommends` between them and warns on drift. Full byte-for-byte reproducibility is intentionally out of scope (research § 9).
5. **Publish.** Upload the `.deb` to the internal release page (GitHub release attachment or your team's artifact store). No private apt repo in v1 — direct download per Clarification Q4.
6. **Announce.** Post the download link plus a one-liner reminder of `sudo apt install ./vayobd_<version>_amd64.deb` and what changed since the previous build.

CI integration is not yet wired in v1 — `./packaging/build.sh` is meant to be runnable from a single command on any platform engineer's laptop. Adding a GitHub Actions job that runs the build + smoke test on tag push is a clean follow-up.

## What's verified by which acceptance scenario

| Acceptance scenario | How to verify it here |
|---|---|
| Story 1, AS-1 (install + first run reaches working app) | `vayobd` on a credentialed clean laptop ⇒ browser shows non-empty inventory |
| Story 1, AS-2 (warm start fast) | `time vayobd` second invocation completes < 2 s before browser opens |
| Story 1, AS-3 (apt remove is clean) | `sudo apt remove vayobd && ls ~/.cache/vayobd/` ⇒ user state still present |
| Story 2, AS-1 (first-run credential failure is actionable) | `vayobd` on a creds-less laptop ⇒ FR-005 message; `ls ~/.cache/vayobd/` ⇒ empty |
| Story 2, AS-2 (fix creds and retry succeeds) | `gh auth login && vayobd` ⇒ reaches AS-1 of Story 1 |
| Story 2, AS-3 (second-repo failure is specific) | Temporarily break the second URL in `manifest.toml` (dev) ⇒ first repo clones, message names the failed repo |
| Story 3, AS-1 (refresh picks up new data) | `vayobd refresh` after upstream push ⇒ inventory reflects new host without restart |
| Story 3, AS-2 (offline refresh keeps last good copy) | Disconnect Wi-Fi, `vayobd refresh` ⇒ state intact, banner says "couldn't refresh — using copy from \<timestamp\>" |
| Story 3, AS-3 (partial failure is recoverable) | Block one URL in `/etc/hosts`, `vayobd refresh` ⇒ exit 5; state file shows mixed outcomes; re-run with hosts restored ⇒ exit 0 |
| Story 4, AS-1 (single build command) | `./packaging/build.sh` from clean checkout ⇒ single `.deb` |
| Story 4, AS-2 (version visible) | `vayobd --version`, `dpkg -s vayobd`, and the app footer all agree |
