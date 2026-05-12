# Implementation Plan: VayOBD .deb package with credential-driven repo sync

**Branch**: `006-deb-package-distribution` | **Date**: 2026-05-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-deb-package-distribution/spec.md`

## Summary

Ship VayOBD as a single Ubuntu 24.04+ `.deb` that bundles the existing backend (Python + uvicorn), the pre-built frontend SPA, and the pre-built Rust engine (`ree-debug-cli`), plus a thin CLI launcher (`vayobd`) that, on first run as the invoking user, auto-detects the user's GitHub credentials (SSH → `gh auth` → system credential helper), clones every repo named in a versioned manifest into the user's cache, and starts the local web UI. The package is **telemetry-free**, distributed as a direct `.deb` download (no apt repo in v1), and supports a single-action refresh via both `vayobd refresh` and an in-app button next to the staleness indicator the existing UI already needs.

Technical approach: pick the **smallest viable packaging tool** (`nfpm` — single YAML config, no debhelper boilerplate) per Constitution Principle I; do all first-run / credential / clone work in a **plain Python module** invoked by the `vayobd` CLI as the *user* (never as root — maintainer scripts only place static files); express the dependency-repo list as a **single versioned TOML manifest** so an upstream rename is a one-line change (the bug we hit today with `vay/ree-vehicle-configs` → `Reemote/ree-vehicle-configs`); add **one new HTTP endpoint** (`POST /api/refresh`) and a small UI affordance for the in-app refresh button; reuse the existing `~/.cache/vayobd/` and `~/.config/vayobd/` layouts unchanged.

## Technical Context

**Language/Version**: Python 3.12 (matches Ubuntu 24.04 system Python — backend), TypeScript 5.6 + React 18 (existing SPA, no change), Rust 1.75+ (existing `engine/` crate, no change), Bash 5.x (maintainer scripts), nfpm YAML (packaging config).
**Primary Dependencies**: FastAPI / uvicorn / Pydantic (existing backend, unchanged); `git` (Ubuntu system package — declared as a `Depends:` of `vayobd`); GitHub CLI `gh` (declared as `Recommends:` — used if present for the second-tier credential probe, but not required); `nfpm` (build-time only, runs in CI).
**Storage**: filesystem only. Cached repos at `~/.cache/vayobd/ree-vehicle-configs/` and `~/.cache/vayobd/ree-reecu/` (per-user, survives package upgrade/remove per FR-011/FR-012). Settings at `~/.config/vayobd/settings.toml` (existing, unchanged). New: `~/.cache/vayobd/manifest-state.toml` (last-sync timestamps + resolved revisions).
**Testing**: pytest (existing) for the new credential-probe / clone-orchestrator / manifest-parser modules; one new integration test that runs the manifest-driven clone against a local fake-git server; one **packaging smoke test** that installs the freshly-built `.deb` inside a `ubuntu:24.04` container and asserts `vayobd --version` plus a fixture-mode startup work; existing Playwright smoke covers the refresh button via the dev-mode flow.
**Target Platform**: Ubuntu 24.04 LTS and newer (per spec Clarification Q5). Architecture: `amd64` for v1.
**Project Type**: web-service + CLI front-end. Existing monorepo with `backend/`, `frontend/`, `engine/`. This feature adds a new top-level `packaging/` directory and a new `backend/src/vayobd/cli.py` + `backend/src/vayobd/install/` package.
**Performance Goals**: SC-001 (≤10 min from clean laptop to first diagnostic run) — bounded by clone time; SC-005 (≤60 s refresh on typical connection); FR-007 (subsequent launches start under 2 s — no network calls on the warm path).
**Constraints**:
  - **Constitution Web App Standards: HTTPS for production traffic.** This feature serves the UI on `127.0.0.1` (loopback) only, which is explicitly *not* "production traffic" in the constitutional sense — we therefore continue to use plain HTTP on loopback and document this in research. No clear-text traffic ever leaves the laptop.
  - Runs as the invoking user. Maintainer scripts (`postinst` etc.) only install files into `/usr/lib/vayobd/` and `/usr/bin/vayobd`; everything else happens at `vayobd` launch time as the user.
  - No telemetry. The only outbound traffic generated is git clone/fetch to the dependency repos and whatever the existing diagnostic flows already do.
  - No `npm` / `cargo` toolchain required on the user's machine. SPA and engine are pre-built into the `.deb` at build time.
**Scale/Scope**: ~20–50 internal Vay engineers, all on a managed Ubuntu LTS image. Single-user desktop, no horizontal scaling.

## Constitution Check

*Gates evaluated against `.specify/memory/constitution.md` v1.0.0. Re-checked after Phase 1.*

| Gate | Status | Evidence |
|------|--------|----------|
| **I. Simplicity First (NON-NEGOTIABLE)** | ✅ Pass | Picked `nfpm` (single YAML, no debhelper layers) over `dh_make`/`fpm`/Snap. One new HTTP route. One new TOML manifest file. No new long-running daemons, no systemd timers (refresh is user-initiated per Q2). No abstraction for "future apt repo" — direct `.deb` download today (per Q4). Justified in `research.md` § Packaging tool. |
| **II. Ship Fast** | ✅ Pass | MVP path delivers a hand-buildable `.deb` against the current branch on day one; CI wiring is a follow-up. No mandatory test-first detour for non-critical-path code; the packaging smoke test is the only new mandatory gate, and it runs in a single 30 s container job. |
| **III. Non-Technical User UX (NON-NEGOTIABLE)** | ✅ Pass | First-run credential failure message (FR-005) is plain-language and lists each surface tried + the documented next step (research § First-run credential message). In-app refresh button (FR-008) sits next to the existing staleness indicator (FR-010) so the user does not need docs to know how to fix "stale data". `vayobd --help` and `vayobd refresh` print recovery-oriented errors, never tracebacks. |
| **Web App Standards — HTTPS** | ⚠️ Accepted exception | Loopback-only HTTP. Documented in research and tracked under Complexity Tracking below. No production traffic leaves the laptop. |
| **Web App Standards — browsers, responsive, privacy** | ✅ Pass | No change to the existing SPA's browser-support matrix, responsive layout, or VIN-handling rules. New refresh UI is one button + a tooltip — same constraints. |
| **Development Workflow — demo always working** | ✅ Pass | The `.deb` is additive: the existing `scripts/setup-linux.sh` flow continues to work alongside it until the .deb is adopted as the default install path. No mainline-breaking change. |

**Result**: All gates pass with one accepted exception (loopback HTTP). Proceeding to Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/006-deb-package-distribution/
├── plan.md              # This file
├── spec.md              # Feature spec (already exists, clarified 2026-05-11)
├── research.md          # Phase 0 — packaging tool, first-run UX, credential probe, manifest format
├── data-model.md        # Phase 1 — manifest schema, manifest-state.toml, settings deltas
├── contracts/
│   ├── manifest.md      # `manifest.toml` (required-repos manifest) format
│   ├── cli.md           # `vayobd` CLI subcommands (run, refresh, doctor, --version)
│   └── http-api.md      # Delta against 004: POST /api/refresh, GET /api/refresh/status
├── quickstart.md        # Fresh-laptop walkthrough: build → install → first run → refresh
└── checklists/
    └── requirements.md  # Spec-quality checklist (already exists, all pass)
```

### Source Code (repository root)

```text
backend/
├── src/vayobd/
│   ├── cli.py                     # NEW — `vayobd` entry point (argparse: run | refresh | doctor)
│   ├── install/                   # NEW — first-run / refresh / credential logic
│   │   ├── __init__.py
│   │   ├── manifest.py            # Loader for the required-repos manifest (TOML → typed objects)
│   │   ├── credentials.py         # Auto-detect SSH → gh → credential helper
│   │   ├── clone.py               # Driver: walks the manifest, clones / fetches as the user
│   │   ├── state.py               # Read/write ~/.cache/vayobd/manifest-state.toml
│   │   └── messages.py            # Plain-language strings for first-run / refresh outcomes
│   ├── api/
│   │   └── refresh.py             # NEW — POST /api/refresh, GET /api/refresh/status
│   ├── app.py                     # Existing — wire the new router
│   └── config.py                  # Existing — add `manifest_path` setting + getter
└── tests/
    ├── unit/install/
    │   ├── test_manifest_loader.py
    │   ├── test_credentials_probe.py
    │   └── test_state_writer.py
    └── integration/
        └── test_refresh_endpoint.py

frontend/
└── src/
    ├── components/StalenessBanner.tsx     # NEW — staleness indicator + refresh button (FR-008/FR-010)
    └── pages/<wherever-inventory-lives>/  # Mount StalenessBanner near the host list

engine/                                    # Unchanged — pre-built artefact pulled into the .deb

packaging/                                 # NEW top-level directory
├── nfpm.yaml                              # Single source of truth for .deb metadata (Depends, etc.)
├── manifest.toml                          # The required-repos manifest shipped inside the .deb
├── usr-bin-vayobd.sh                      # Tiny wrapper installed to /usr/bin/vayobd
├── usr-share-applications-vayobd.desktop  # Desktop launcher entry
├── postinst.sh                            # Maintainer script — symlinks, no per-user work
├── postrm.sh                              # Maintainer script — clean removal per FR-011
└── build.sh                               # `./packaging/build.sh` → ./dist/vayobd_<ver>_amd64.deb

scripts/
├── setup-linux.sh                         # Existing — unchanged; remains the legacy path
└── package-smoke-test.sh                  # NEW — runs the freshly-built .deb in a ubuntu:24.04 container
```

**Structure Decision**: Extend the existing monorepo layout. All packaging assets live under a new `packaging/` directory at the repo root so that `./packaging/build.sh` is the single documented build command (per FR-014 / SC-007). The first-run / credential / clone orchestration lives inside the existing Python backend package (`backend/src/vayobd/install/`) so it shares code, config, logging, and tests with everything else — there is no separate "installer" project to maintain. The `vayobd` CLI is a thin argparse entry point that dispatches to either `uvicorn` (the `run` subcommand) or the `install` package (`refresh`, `doctor`).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Loopback HTTP instead of HTTPS (Web App Standards exception) | Local-loopback-only traffic; introducing a self-signed cert would force every user to click through a browser-trust warning on first launch, directly violating Principle III (non-technical UX) | Self-signed cert: see above. Letting the user provide their own cert: requires config beyond what FR-001 ("no manual .env editing") permits. The constitutional intent of the HTTPS rule is "production traffic" — explicitly clarified in research. |
