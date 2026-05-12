---
description: "Task list for VayOBD .deb package with credential-driven repo sync"
---

# Tasks: VayOBD .deb package with credential-driven repo sync

**Input**: Design documents from `/specs/006-deb-package-distribution/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Minimal pytest coverage on the parts that are hardest to debug at install time (manifest loader, credential probe, atomic state writes) plus one packaging smoke test that runs the freshly-built `.deb` inside a clean container. The full TDD-first workflow is **not** requested.

**Organization**: Tasks are grouped by the four user stories in `spec.md` so each story is independently implementable, testable, and demo-able.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- File paths are repo-relative

## Path Conventions

- Backend Python: `backend/src/vayobd/` + `backend/tests/`
- Frontend React/TS: `frontend/src/`
- Packaging assets: `packaging/`
- Scripts: `scripts/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the directories and skeleton files that every story will write into. No business logic yet.

- [X] T001 Create `packaging/` directory at repo root with an empty `.gitkeep`, and add `dist/` plus `packaging/build/` to `.gitignore`
- [X] T002 [P] Create the `install/` Python sub-package skeleton: `backend/src/vayobd/install/__init__.py` (empty exports), plus empty stub modules `manifest.py`, `state.py`, `credentials.py`, `clone.py`, `messages.py` (each with a one-line module docstring, no implementation)
- [X] T003 [P] Create the `backend/tests/unit/install/` and `backend/tests/integration/install/` directories with empty `__init__.py` files so pytest picks them up
- [X] T004 [P] Install build-time tooling locally for the developer building the first .deb: add a one-line `nfpm` install note to `scripts/setup-linux.sh` (download release binary into `~/.local/bin/nfpm`) — do not run it during the existing setup flow; it is a manual one-liner the platform engineer runs once

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The manifest loader, state file, settings delta, and CLI dispatcher are shared by every story. Without them no story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T005 Add the `manifest_path` field to `Settings` in `backend/src/vayobd/config.py` (default `Path("/usr/share/vayobd/manifest.toml")`, fallback to `<repo>/packaging/manifest.toml` when the default is missing) per plan § Technical Context and data-model § 3
- [X] T006 [P] Implement the manifest loader and Pydantic models in `backend/src/vayobd/install/manifest.py` per `contracts/manifest.md` (`Manifest`, `RepoEntry`, `load_manifest(path: Path) -> Manifest`, typed errors `ManifestVersionError`, `ManifestPathError`, `ManifestSchemaError`)
- [X] T007 [P] Implement the manifest-state reader/writer in `backend/src/vayobd/install/state.py` per data-model § 2 (`ManifestState`, `RepoState`, `load_state()`, `save_state_atomic()` — write to `~/.cache/vayobd/manifest-state.toml.tmp` then `os.replace`, never partial)
- [X] T008 [P] Implement the plain-language message catalogue in `backend/src/vayobd/install/messages.py`: `credential_failure_message(probe_results)`, `refresh_outcome_message(state)`, `partial_clone_warning(repo_id, reason)`. Strings match the wording in research § 5 and contracts/cli.md
- [X] T009 Create the `vayobd` CLI entry point in `backend/src/vayobd/cli.py` per `contracts/cli.md`: argparse with subcommands `run`, `refresh`, `doctor`, plus `--version`. Each subcommand currently just prints `"not implemented yet"` and exits 0 — wiring only, no logic. Wire `pyproject.toml` `[project.scripts] vayobd = "vayobd.cli:main"` so the installed venv exposes the binary
- [X] T010 [P] Add the "refuse to run as root" guard in `backend/src/vayobd/cli.py` (`os.geteuid() == 0` ⇒ print the FR-015 message from contracts/cli.md and exit 6). Test by running `sudo .venv/bin/vayobd run` and confirming the exit code
- [X] T011 [P] Unit test for manifest loader in `backend/tests/unit/install/test_manifest_loader.py`: happy path, missing required field, invalid `id` regex, `target_path` outside `$HOME`, unsupported `manifest_version`
- [X] T012 [P] Unit test for state writer in `backend/tests/unit/install/test_state_writer.py`: empty state defaults, round-trip with two repos, atomic-write crash simulation (KeyboardInterrupt during `save_state_atomic` leaves either old or no file, never a half-written one)

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 — Install VayOBD from a .deb on a fresh laptop (Priority: P1) 🎯 MVP

**Goal**: A platform engineer can build a `.deb` and an end-user can `sudo apt install ./vayobd_*.deb` on a clean Ubuntu 24.04 laptop with working GitHub access, click the launcher, and see the working web UI with the inventory populated.

**Independent Test**: On a clean `ubuntu:24.04` container with the engineer's GitHub credentials available, install the freshly-built `.deb`, run `vayobd run --no-browser`, and confirm `curl http://127.0.0.1:8000/api/inventory` returns 200 with `host_count > 0`. Matches Story 1 AS-1 and the quickstart's "First-run smoke test (happy path)" section.

### Implementation for User Story 1

- [X] T013 [P] [US1] Author `packaging/manifest.toml` — the source-of-truth required-repos manifest. Two `[[repo]]` entries (`ree-vehicle-configs`, `ree-reecu`) per data-model § 1 example. This file is the FR-006 contract; review carefully before merge
- [X] T014 [US1] Implement the clone orchestrator in `backend/src/vayobd/install/clone.py`: `clone_all(manifest, state, credential_surface, *, mode='clone'|'fetch')`. For `clone` mode, runs `git clone` (with `--branch` and `--depth 1` for the initial clone, then unshallow if a `branch` is pinned); for `fetch` mode, runs `git fetch && git reset --hard origin/<branch>`. Applies `sparse_paths` via `git sparse-checkout` after init. Updates `state` per repo after each operation. Depends on T006, T007
- [X] T015 [US1] Wire `vayobd run` in `backend/src/vayobd/cli.py`: load manifest + state, on first run call the credentials probe (stubbed for now — full impl in US2) and `clone_all`, then exec uvicorn bound to `127.0.0.1:<port>` with the existing app. Open the browser via `webbrowser.open` unless `--no-browser`. Handle `--port` busy ⇒ exit 4. Depends on T009, T014
- [X] T016 [P] [US1] Author `packaging/nfpm.yaml`: name=`vayobd`, version from `$VAYOBD_VERSION` env, `depends: [git, python3 (>= 3.12), libfontconfig1]`, `recommends: [gh]`, contents mapping for `usr/bin/vayobd`, `usr/lib/vayobd/{bin,venv}`, `usr/share/vayobd/{manifest.toml,spa}`, `usr/share/applications/vayobd.desktop`. Per research § 1 + data-model § 4
- [X] T017 [P] [US1] Author `packaging/usr-bin-vayobd.sh` — the shell shim installed at `/usr/bin/vayobd`. Exports `PYTHONPATH` pointing at the bundled venv's `site-packages`, then exec's `/usr/lib/vayobd/venv/bin/python -m vayobd.cli "$@"`. Mode `0755`
- [X] T018 [P] [US1] Author `packaging/usr-share-applications-vayobd.desktop` — a freedesktop `.desktop` entry: `Exec=/usr/bin/vayobd run`, `Terminal=false`, sensible `Icon=` (placeholder OK), `Categories=Development;Utility;`
- [X] T019 [P] [US1] Author `packaging/postinst.sh` and `packaging/postrm.sh`: `postinst` runs `update-desktop-database -q /usr/share/applications` and exits 0; `postrm` does nothing on `remove` (FR-011 — cache stays) and prints the per-user cleanup hint on `purge`. Both ≤10 lines. No per-user work, ever
- [X] T020 [US1] Author `packaging/build.sh` — the single entry point per FR-014 / SC-007. Steps from research § 8 and quickstart "Build": cargo build engine, npm build SPA, uv pip compile + sync the venv into `packaging/build/dist/usr/lib/vayobd/venv/`, stage all files into `packaging/build/dist/`, then `nfpm package`. Outputs `dist/vayobd_<version>_amd64.deb` where `<version>` defaults to `git describe --always --dirty`. Must be runnable from a clean checkout. Depends on T013, T016, T017, T018, T019
- [X] T021 [P] [US1] Author `scripts/package-smoke-test.sh` — accepts the `.deb` path, spins up a `ubuntu:24.04` Docker/podman container, copies the `.deb` in, runs `apt install ./vayobd_*.deb -y`, then `su - testuser -c 'vayobd --version && VAYOBD_EXECUTOR=fixture vayobd run --no-browser --port 18000 &' && curl ...`. Exits 0 on success, non-zero with the failure line otherwise. This is the mandatory new test gate per plan § Constitution Check
- [X] T022 [US1] Update `README.md` to add a "Install from .deb (Ubuntu 24.04+)" section pointing at the new quickstart. Keep the existing `scripts/setup-linux.sh` section — the two paths coexist per plan § Dev Workflow gate

**Checkpoint**: User Story 1 is complete and demoable. A fresh laptop with working GitHub credentials reaches a working UI from a single `apt install`.

---

## Phase 4: User Story 2 — First-run credential check with clear guidance (Priority: P1)

**Goal**: A user without GitHub credentials installs the `.deb`, runs `vayobd`, and gets the FR-005 plain-language message naming each surface tried and the next concrete action. No partial cache is left behind. After they fix credentials, retry succeeds with no manual cleanup.

**Independent Test**: On a fresh `ubuntu:24.04` container with **no** GitHub credentials, install the `.deb`, run `vayobd run --no-browser`, confirm exit code 2, stderr contains "couldn't read your GitHub credentials" + "SSH", "GitHub CLI", "credential helper" surfaces, and `ls ~/.cache/vayobd/` shows the directory is empty (no half-clone). Matches Story 2 AS-1 and AS-3.

### Implementation for User Story 2

- [X] T023 [US2] Implement the credential probe in `backend/src/vayobd/install/credentials.py` per research § 3: `probe_credentials() -> ProbeResult` with `Outcome = ssh|gh|credential-helper|all-failed`, each with a per-surface `(succeeded: bool, detail: str)`. Subprocesses use `BatchMode=yes`, `ConnectTimeout=5`, `GIT_TERMINAL_PROMPT=0`. SSH probe = `ssh -T git@github.com` exit-code-1-is-success. `gh` probe = `gh auth status --hostname github.com`. Credential-helper probe = `git ls-remote https://github.com/<public-canary>` with `GIT_TERMINAL_PROMPT=0`
- [X] T024 [US2] Replace the credential-probe stub in `backend/src/vayobd/cli.py` (`vayobd run` and `vayobd refresh`) with calls to `probe_credentials()`. On `all-failed`, render `credential_failure_message(result)` to stderr and exit 2 with no partial cache (FR-005). Depends on T023, T008
- [X] T025 [US2] Record probe outcomes in `manifest-state.toml` per FR-004a: `last_credential_probe`, `credential_surface_used` (the one that succeeded — `null` if all failed). Wire into `clone_all` so it consumes the probe result rather than re-probing. Depends on T023, T007, T014
- [X] T026 [US2] Implement the FR-009 "no partial cache" guarantee in `backend/src/vayobd/install/clone.py`: each repo clones into a temporary path under `~/.cache/vayobd/.tmp-<id>-<pid>/`, then `os.replace` atomically into the final `target_path`. On any failure mid-`clone_all`, every successfully-cloned tmp dir is removed; nothing renames in. Updates messages.py with the per-repo failure wording for Story 2 AS-3. Depends on T014
- [X] T027 [P] [US2] Unit test in `backend/tests/unit/install/test_credentials_probe.py`: stub each subprocess with `subprocess.run` monkeypatch; cover all-fail, ssh-only, gh-only, credential-helper-only, ssh-times-out paths. The all-fail case asserts the rendered message contains all three surface names verbatim (regression-resistant)
- [X] T028 [P] [US2] Integration test in `backend/tests/integration/install/test_first_run_failure.py`: run `vayobd run --no-browser --manifest <fixture>` with `PATH=` stripped of `git` to force probe failure; assert exit 2, stderr matches the FR-005 message, and the temp dir was cleaned

**Checkpoint**: User Story 2 is complete. The "We couldn't reach the diagnostics service" UX from today is replaced with a useful, actionable message that names the actual problem.

---

## Phase 5: User Story 3 — Refresh repos to pick up new vehicles / signal definitions (Priority: P2)

**Goal**: After Stories 1 + 2 are working, the user has two ways to refresh: `vayobd refresh` on the CLI, and an in-app button next to a staleness indicator at the top of the inventory page. Both drive the same code path. Partial failures keep the user in a consistent state per FR-009.

**Independent Test**: With a working install, hand-edit `~/.cache/vayobd/manifest-state.toml` to set `last_synced_at` to 48 h ago. Open the UI: the StalenessBanner is visible. Click "Refresh now": the button disables, the spinner shows, the banner clears within ~30 s. Then `git -C ~/.cache/vayobd/ree-vehicle-configs log -1 --format=%H` matches the current upstream HEAD. Matches Story 3 AS-1.

### Implementation for User Story 3

- [X] T029 [US3] Implement `vayobd refresh` in `backend/src/vayobd/cli.py` per contracts/cli.md: load manifest + state, honour the < 1 h cached probe, call `clone_all(..., mode='fetch')`, print the one-line-per-repo summary, exit 0 on full success / 5 on partial failure. Depends on T014, T024
- [X] T030 [P] [US3] Implement the HTTP refresh router in `backend/src/vayobd/api/refresh.py` per contracts/http-api.md: `POST /api/refresh` (202 + refresh_id, or 409 if already running, or 503 on credentials failure), `GET /api/refresh/status` (idle / running / partial-failure shapes from the contract). Background work via `asyncio.create_task` guarded by a module-level `asyncio.Lock` (single-user app, one in-flight refresh max). Includes the `stalest_age_seconds` computation from `ManifestState`
- [X] T031 [US3] Wire the new router into `backend/src/vayobd/app.py` (`app.include_router(refresh_router, prefix="/api")`). Depends on T030
- [X] T032 [P] [US3] Integration test in `backend/tests/integration/install/test_refresh_endpoint.py`: spin up the FastAPI test client, fake the clone driver, assert the 202 → poll status → 200 idle sequence and the 409 on a second POST while running
- [X] T033 [US3] Create `frontend/src/components/StalenessBanner.tsx`: visible when `GET /api/refresh/status` returns `stalest_age_seconds > threshold` (24h default) OR `last_refresh_outcome` is non-null and non-success. Shows "Last sync: \<relative-time\>" + a "Refresh now" button. Disabled when `state === 'running'`. Polls `/api/refresh/status` every 1 s while running, then stops polling
- [X] T034 [US3] Mount `StalenessBanner` at the top of the inventory page (`frontend/src/pages/.../inventory…tsx` — the exact existing page that lists hosts; locate via grep for `/api/inventory`). One-line import + render
- [X] T035 [US3] Add a `lib/refresh-client.ts` (or inline in the component) that calls `POST /api/refresh`, handles the 409/503 envelopes, and surfaces the credential-failure variant by reusing the existing error-toast pattern in the SPA

**Checkpoint**: Refresh works from CLI and UI. Partial failures don't leave the cache in a hybrid state.

---

## Phase 6: User Story 4 — Reproducible package build by the platform team (Priority: P2)

**Goal**: A platform engineer in CI runs the documented build command and gets a `.deb` whose version + commit SHA are visible at every level (`vayobd --version`, `dpkg -s vayobd`, the app footer). Two builds from the same commit produce functionally equivalent artefacts.

**Independent Test**: From a fresh checkout: `./packaging/build.sh && dpkg-deb -I dist/vayobd_*.deb | grep Version` matches `git describe`. Run the build a second time on the same commit, install the second `.deb`, and confirm `vayobd --version` and `dpkg -s vayobd | grep Version` agree with the first build. Matches Story 4 AS-1 and AS-2.

### Implementation for User Story 4

- [X] T036 [P] [US4] Embed build metadata at package build time: `packaging/build.sh` writes `backend/src/vayobd/_version.py` with `__version__ = "<ver>"` and `__commit__ = "<sha>"` before `uv pip sync`. Add `_version.py` to `.gitignore`. Provide a runtime helper `vayobd.version_info()` returning `{"version": ..., "commit": ..., "engine_commit": ...}` (engine commit read from the binary's `--version` output, already supported by the engine per existing logs)
- [X] T037 [US4] Implement `vayobd --version` in `backend/src/vayobd/cli.py` to print the multi-line version block from contracts/cli.md (version, commit, Python, manifest path + version, engine path + commit). Depends on T036, T009
- [X] T038 [US4] Implement `vayobd doctor` in `backend/src/vayobd/cli.py` per contracts/cli.md: re-runs the credential probe (read-only), loads manifest + state, prints the full health page. Exit 0 if healthy, 1 if any anomaly. Depends on T023, T007, T036
- [X] T039 [P] [US4] Add a small "About / Version" footer to the SPA shell (`frontend/src/components/AppFooter.tsx` or wherever the existing layout footer lives) that reads from `GET /api/health` (already returns `version` + `engine_version`) and renders "VayOBD \<version\> · engine \<sha\>". One-line surface; supports SC-007 + FR-013
- [X] T040 [US4] Extend `scripts/package-smoke-test.sh` to assert determinism: build twice in succession (same commit), `dpkg-deb -I` on both, diff the `Version`, `Installed-Size`, and the `Depends`/`Recommends` lines — must be identical. (Full byte-for-byte reproducibility intentionally out of scope per research § 9.) Depends on T020

**Checkpoint**: All four user stories complete. The `.deb` is buildable, installable, refreshable, and version-trackable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation and post-implementation hardening that touches multiple stories.

- [X] T041 [P] Update `README.md` with a "Production install (.deb)" section that points at `specs/006-deb-package-distribution/quickstart.md` and notes that `scripts/setup-linux.sh` is now the developer-mode path
- [X] T042 [P] Add a "Releasing a new .deb" runbook to `specs/006-deb-package-distribution/quickstart.md` (one new section: bump version, build, smoke-test, attach to internal release page). No CI wiring in v1; that is a follow-up
- [X] T043 Run the full quickstart end-to-end on a fresh `ubuntu:24.04` container (manual walk-through of every acceptance scenario in the quickstart's mapping table). Record any blocker as a follow-up task
- [X] T044 [P] Fix the upstream-clone-URL bug discovered during today's session: update `scripts/setup-linux.sh:150` to point at `Reemote/ree-vehicle-configs` instead of `vay/ree-vehicle-configs` (independent of this feature, but caught here — leave it in this PR or split into a separate one based on team preference)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup. **Blocks** all user stories.
- **User Story 1 (Phase 3)**: Depends on Phase 2. Delivers the MVP.
- **User Story 2 (Phase 4)**: Depends on Phase 2. Independently testable (can start in parallel with US1 if staffed).
- **User Story 3 (Phase 5)**: Depends on Phase 2. Also depends on US1's `clone_all` (T014) and US2's credential probe (T023) being merged in some form, so in practice runs after Phase 4.
- **User Story 4 (Phase 6)**: Depends on Phase 2 and US1's `build.sh` (T020). Can run in parallel with Phase 5.
- **Polish (Phase 7)**: Depends on the desired user stories being merged.

### User Story Dependencies

- **US1 → US2**: US2 hardens what US1's stubbed credential probe placeholder is replaced with. They share the same `clone.py` and `cli.py` — coordinate merges.
- **US3 → US1 + US2**: refresh reuses `clone_all` (US1) and the credential probe (US2). Implement after both are merged.
- **US4 → US1**: `vayobd --version` and `vayobd doctor` need the version embedding from US1's build pipeline.

### Within Each Story

- Tests where included MAY be written first or alongside implementation; full TDD-first is not enforced per plan § Dev Workflow.
- Models / shared modules before services before endpoints before UI.

### Parallel Opportunities

- All `[P]`-marked tasks within a phase can run in parallel.
- Within Phase 2: T006, T007, T008 are independent and parallelizable.
- Within Phase 3: T013, T016, T017, T018, T019, T021 all touch different files and can run in parallel.
- Within Phase 4: T027, T028 in parallel.
- Within Phase 5: T030 / T032 parallel with T033 / T034 (backend vs frontend split).
- Within Phase 6: T036, T039 parallel with T037, T038, T040.

---

## Parallel Example: User Story 1

```bash
# After T014 is merged, launch these in parallel:
Task: "Author packaging/nfpm.yaml per data-model § 4"             # T016
Task: "Author packaging/usr-bin-vayobd.sh shell shim"             # T017
Task: "Author packaging/usr-share-applications-vayobd.desktop"    # T018
Task: "Author packaging/postinst.sh and packaging/postrm.sh"      # T019
Task: "Author scripts/package-smoke-test.sh"                      # T021
```

T020 (`build.sh`) depends on T016–T019 and must run after they merge.

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

The spec marks Stories 1 and 2 both as P1 — Story 2 is part of the MVP because shipping Story 1 without Story 2's failure UX would recreate the exact "We couldn't reach the diagnostics service" bug we hit today.

1. Phase 1: Setup (~1 hour).
2. Phase 2: Foundational (~half a day).
3. Phase 3: User Story 1 (~1–2 days; majority is `build.sh` getting the venv-vendoring right).
4. Phase 4: User Story 2 (~half a day; mostly the credential probe).
5. **Stop and validate**: run the quickstart's "First-run smoke test (sad path)" — this is the demo.

### Incremental Delivery After MVP

6. Phase 5: User Story 3 — refresh (CLI + UI). ~1 day.
7. Phase 6: User Story 4 — version metadata + doctor. ~half a day.
8. Phase 7: Polish.

### Parallel Team Strategy

With two engineers post-Foundational:

- **Eng A**: drives US1 (packaging assets, build script, smoke test).
- **Eng B**: drives US2 (credential probe + first-run failure UX, including unit tests).
- They meet on the `clone.py` interface in T014/T026 — coordinate via a quick design check.
- After US1 + US2 merge, the same pair splits US3 backend (Eng A: routers + background task) vs frontend (Eng B: StalenessBanner) and US4 (parallel with US3).

---

## Notes

- `[P]` = different files, no incomplete dependencies — fan out freely.
- `[Story]` label maps every implementation task to a single user story for traceability.
- Each story is independently completable and demoable per the spec's "Independent Test" sections.
- Commit per task or per logical group; the speckit auto-commit hook makes this cheap.
- Stop at any checkpoint to demo the story without later phases being done.
- Things explicitly **not** in this task list (out of scope per spec):
  - Apt-repo hosting / package signing infra (Q4).
  - Telemetry / usage analytics (Q3).
  - Background auto-refresh (Q2).
  - Ubuntu 22.04 support (Q5).
  - Reproducible-builds bit-level determinism (research § 9).
