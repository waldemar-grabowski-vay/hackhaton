# Feature Specification: VayOBD .deb package with credential-driven repo sync

**Feature Branch**: `006-deb-package-distribution`
**Created**: 2026-05-11
**Status**: Draft
**Input**: User description: "So we would need to prepare it as a .deb package. We want that all necessary repos are being pulled automatically with user credentials on his laptop."

## Clarifications

### Session 2026-05-11

- Q: Which credential surface should the .deb use to authenticate against GitHub for the first-run clone? → A: Auto-detect, in order: existing SSH (working `git@github.com` via `ssh-agent` / `~/.ssh/`), then GitHub CLI (`gh auth`), then the system credential helper (libsecret / gnome-keyring). The first surface that produces a working clone wins; the others are tried only if the prior one fails.
- Q: Which user-facing surface should trigger a refresh of all required repos? → A: Both — a CLI command (primary, used for support and scripting) and an in-app button rendered next to the staleness indicator in the UI. Background auto-refresh is explicitly out of scope for v1.
- Q: Should the .deb include any client-side telemetry / usage reporting? → A: No. v1 ships with zero telemetry. Success metrics (SC-003 in particular) are measured exclusively via support-ticket volume and any in-app feedback channels that already exist; the .deb makes no outbound network calls beyond those required to clone / refresh the dependency repos.
- Q: How will users obtain the `.deb` artefact? → A: Direct download from an internal release / artifact location (e.g., GitHub release attachment or internal artifact store), installed via `sudo apt install ./vayobd_*.deb`. A signed private apt repository is **not** part of v1 and can be added later as a follow-up without breaking anything else.
- Q: Which Ubuntu LTS versions are supported targets? → A: Ubuntu 24.04 LTS and newer (i.e., 24.04 is the supported floor; 26.04 and any future LTS that ship a compatible Python / glibc baseline are also supported). Ubuntu 22.04 is **not** a supported target; users still on 22.04 should upgrade or keep using `scripts/setup-linux.sh`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Install VayOBD from a .deb on a fresh Vay laptop (Priority: P1)

A Vay engineer is handed a new Linux laptop. They double-click (or `sudo apt install ./vayobd_*.deb`) the package they received from the platform team. Within a few minutes — without editing config files, cloning repos by hand, or knowing what "ree-vehicle-configs" or "ree-debug-cli" are — they can open a browser, see the host inventory populated with real Vay vehicles and telestations, and run a diagnostic against a host.

**Why this priority**: This is the entire reason the feature exists. Today, getting VayOBD running on a new machine requires running `scripts/setup-linux.sh`, fixing a stale clone URL, sorting out SSH access to private repos, and editing `.env`. A .deb that does this end-to-end is the smallest unit of value worth shipping.

**Independent Test**: On a clean Ubuntu LTS VM with the engineer's GitHub credentials already configured (per Story 2), install only the .deb, launch `vayobd` from an application launcher or terminal, open the URL it prints, and confirm the inventory loads and at least one fixture-backed diagnostic run completes successfully.

**Acceptance Scenarios**:

1. **Given** a clean Ubuntu LTS laptop with the user's GitHub credentials already authorised, **When** the user installs the .deb and launches VayOBD for the first time, **Then** all required private repos are cloned to standard cache/config locations, the local web app starts, and the inventory list is non-empty.
2. **Given** VayOBD is already installed, **When** the user launches it again, **Then** the app starts without re-cloning anything and serves the previously cached inventory immediately.
3. **Given** VayOBD is installed, **When** the user runs `sudo apt remove vayobd`, **Then** the application binaries and system-level files are removed, and the user is told (in standard `apt` post-removal output or documentation) how to also delete the cached repos and per-user state if they wish.

---

### User Story 2 — First-run credential check with clear guidance (Priority: P1)

A Vay engineer installs the .deb on a laptop that does **not** yet have working GitHub access for Vay's private repositories. On first launch, instead of failing with cryptic "Repository not found" errors hidden in a log file, VayOBD detects the missing credentials, stops before the first clone attempt, and shows a short, actionable message explaining exactly what the user needs to do (e.g., "authorise your GitHub account for the Reemote org") and how to retry.

**Why this priority**: The current setup script silently warns "(no GitHub access yet?)" and continues, leaving a partially-broken install that 503s when the user opens the app — exactly the failure mode we hit when starting the app today. First-run UX is what makes the .deb usable by non-platform engineers.

**Independent Test**: On a laptop with no GitHub credentials at all, install the .deb and launch the app. The app must refuse to silently proceed, must tell the user what is missing, and must succeed cleanly the moment the user fixes the credential issue and retries — with no manual cache cleanup needed in between.

**Acceptance Scenarios**:

1. **Given** the user has no working credentials for Vay's private GitHub repos, **When** they launch VayOBD for the first time, **Then** the app surfaces a single, plain-language credential-setup message and exits (or shows a setup screen) without leaving a half-cloned cache.
2. **Given** the user fixes their credentials, **When** they re-launch VayOBD, **Then** the clone proceeds, succeeds, and the app reaches the working state from Story 1.
3. **Given** the user's credentials succeed for the inventory repo but fail for a second required repo, **When** the clone of the second repo fails, **Then** the user sees which specific repo failed and why, not a generic "something went wrong".

---

### User Story 3 — Refresh repos to pick up new vehicles / signal definitions (Priority: P2)

A Vay engineer has been using VayOBD for two weeks. A new telestation has been added to the fleet, and the CAN signal database has been updated. The user wants their local copy to reflect those changes without uninstalling and reinstalling the package.

**Why this priority**: The fleet inventory and the DBC/errq sources change weekly. Without a refresh path, every install drifts into staleness and users invent ad-hoc `git pull` rituals (or worse, file bug reports asking "why is my host missing"). The current setup-script behaviour — clone once at install time — is what got us into the "13 consecutive failed refreshes" state on the demo laptop today.

**Independent Test**: After Story 1 is satisfied, simulate an upstream change in one of the dependency repos. The user invokes the refresh via either the CLI command or the in-app button (both must work) and within a short time the app reflects the upstream change without restarting the laptop or re-running the installer.

**Acceptance Scenarios**:

1. **Given** an installed and working VayOBD, **When** the user triggers the refresh action, **Then** all required repos pull the latest from their default branches and the app reflects the new data on next inventory view.
2. **Given** the user triggers a refresh while offline, **When** the network is unavailable, **Then** the app keeps serving the previously cached data and surfaces a clear "couldn't refresh — using last good copy from \<timestamp\>" indication; nothing is wiped.
3. **Given** a refresh fails midway through (e.g., one repo updates but a second times out), **When** the user retries, **Then** the partial state is reconciled and the user is not left in a broken hybrid state.

---

### User Story 4 — Reproducible package build by the platform team (Priority: P2)

A platform engineer builds the .deb from this repo on a CI runner. The build is deterministic enough that two builds from the same commit produce functionally equivalent packages, and the artefact carries enough metadata (version, build SHA) that a user can answer "what version do I have" without reading source.

**Why this priority**: Without a reproducible build path, "the .deb" is whatever one person had on their laptop last Tuesday. P2 because Stories 1–3 deliver user value first; this story is the operational backbone behind them.

**Independent Test**: Run the documented build command twice on a clean CI environment and confirm both artefacts install cleanly on a fresh Ubuntu LTS VM and report the same version + commit SHA via a documented "show version" surface (CLI flag, in-app footer, or `dpkg -s vayobd`).

**Acceptance Scenarios**:

1. **Given** a clean checkout of this repo, **When** the platform engineer runs the documented build command, **Then** a single `.deb` artefact is produced with a versioned filename and no manual steps required.
2. **Given** an installed package, **When** a user asks "what version is this", **Then** they can find a clear answer via at least one documented surface (CLI, in-app, or `dpkg`).

---

### Edge Cases

- **Repo URL drift**: an upstream repo is renamed or moved to a different GitHub org (as `vay/ree-vehicle-configs` → `Reemote/ree-vehicle-configs` did). The .deb must read repo URLs from a single source of truth so a one-line fix in the source repo, plus a refresh, resolves it for every user.
- **Partial connectivity**: the user is on a VPN that reaches GitHub but not the internal mirror, or vice versa. The user must be told which specific dependency couldn't be reached.
- **Shared laptop**: two operators log into the same laptop. Their cached repos may be shared, but per-operator state (selected hosts, recent runs) must not bleed across user accounts.
- **Disk pressure**: the dependency repos can grow large. The package and refresh logic must not silently consume unbounded disk on every refresh.
- **Stale credentials**: the user's credentials were valid at install time but have since expired or been revoked. The next refresh must fail with the same clear, actionable message as the first-run flow, not silently keep serving year-old data with no warning.
- **Apt upgrades**: when a new .deb version is installed via `apt upgrade`, the user's existing cached repos and per-user settings must survive the upgrade unchanged — only the application code is replaced.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST be installable on a supported Ubuntu LTS release via a single `.deb` package using only standard `apt`/`dpkg` workflows, with no manual cloning, virtual-env creation, or `.env` editing required by the user.
- **FR-002**: The package MUST declare all system-level dependencies (e.g., the language runtime needed to execute the bundled application, `git`, anything else needed by first-run clones) so that `apt` installs them automatically and the installer does not need network access to anywhere other than the standard distro mirrors plus the dependency-repo hosts.
- **FR-003**: On first launch, the application MUST automatically clone every private repository it needs to function (at minimum: the vehicle/telestation inventory, the CAN signal database source, and the error-queue catalogue source) into well-known per-user paths, using the credentials the user has already configured on their machine.
- **FR-004**: The application MUST NOT prompt the user for raw secrets (Personal Access Token strings, passwords) inside the app itself. Credentials MUST come from a credential surface the user already manages on their machine. The application MUST try the following surfaces in order until one produces a working clone, and MUST use the first one that succeeds:
   1. The user's existing SSH credentials for GitHub (`ssh-agent` and/or `~/.ssh/` configured such that `git@github.com` resolves and authenticates).
   2. The user's GitHub CLI session, where the application uses `gh`'s configured token (e.g., via `gh auth status` and `gh auth token` or equivalent) to clone over HTTPS.
   3. The user's system credential helper (e.g., libsecret / gnome-keyring) as exposed to `git` via its credential-helper protocol.
- **FR-004a**: The first-run credential check (FR-005) MUST report which of the surfaces in FR-004 was tried and which (if any) succeeded, so that when the user later runs `apt`-level support or reads the in-app credential error, they can see whether SSH was attempted, `gh` was attempted, etc., and which one is actually being used.
- **FR-005**: If every credential surface listed in FR-004 fails to produce a working clone on first run, the application MUST refuse to start the user-facing UI, display a single plain-language message naming each surface that was tried and at least one documented next step (e.g., "set up `gh auth login` or add your SSH key to GitHub"), and exit (or show only a setup screen) with no partial cache left behind.
- **FR-006**: The list of required repositories — with their canonical URLs and target local paths — MUST live in a single, versioned source-of-truth file shipped inside the package, so that an upstream rename (org move, fork, etc.) is a one-line change followed by a refresh, not a code change in every user's clone.
- **FR-007**: After the first successful sync, subsequent launches of the application MUST start in well under the first-launch time (i.e., MUST NOT re-clone or block on network reachability for the standard "open the app and look at inventory" flow).
- **FR-008**: The application MUST provide **both** refresh surfaces, each capable of updating every required repo from its default branch in a single user action:
   1. A CLI command (e.g., `vayobd refresh`) installed alongside the application binary by the .deb. This is the primary surface for support engineers and scripts.
   2. An in-app refresh button rendered next to the staleness indicator from FR-010, so that when a user notices "stale, last sync N days ago" in the UI, they can fix it with one click without leaving the page.

   Both surfaces MUST drive the same underlying refresh logic and MUST produce the same end state (FR-009 consistency guarantees apply to both). Automatic background refresh on launch or on a timer is explicitly out of scope for v1.
- **FR-009**: A refresh that fails partway through MUST leave the user's environment in a consistent, recoverable state — either fully updated, or unchanged from before the refresh — never a mix that produces silently-wrong data.
- **FR-010**: When the application is operating on stale cached data because a refresh failed or never ran, it MUST surface that fact to the user (in the UI, the CLI, or both) with at minimum the timestamp of the last successful sync.
- **FR-011**: Removing the package via `apt remove` MUST cleanly remove the application's system-installed files and MUST NOT delete the user's cached repository clones or per-user settings by default; documentation MUST tell the user how to also purge those if they want a full wipe.
- **FR-012**: Reinstalling or upgrading the package via `apt` MUST preserve the user's existing cached repos and per-user settings; only the application binaries and shared assets are replaced.
- **FR-013**: The package MUST embed enough version metadata that a user (or support engineer) can identify exactly which build is installed via at least one of: a CLI `--version` flag, an in-app footer/about surface, or `dpkg -s vayobd`.
- **FR-014**: The package build process MUST be runnable from a clean checkout of this repository by a single documented command, producing a deterministic-enough artefact that two builds from the same commit are functionally equivalent.
- **FR-015**: The application MUST run as the invoking user (not root) and MUST NOT require root privileges beyond what `apt install` itself requires to place files; first-run clones and refreshes MUST happen in the user's own home/cache directories using the user's own credentials.

### Key Entities *(include if feature involves data)*

- **Package artefact**: the distributable `.deb` file. Carries the application code, the manifest of required repos (FR-006), embedded version/build metadata (FR-013), and the desktop-launcher / CLI entry point.
- **Required-repos manifest**: the single source-of-truth file (FR-006) listing each repository the app needs, its canonical URL, its target local path, and any branch / sparse-checkout constraints. Read at first run and at every refresh.
- **Per-user cache**: the operator-owned directory tree (one per Linux user account) holding the cloned dependency repos and the last-sync metadata that drives the staleness indicator (FR-010). Survives package upgrades and uninstalls (FR-011, FR-012).
- **Per-user settings**: any operator-specific configuration the app already maintains (TOML at `~/.config/vayobd/...` or equivalent) — explicitly outside the .deb's purview, preserved across reinstalls.
- **Credential surface**: the user's pre-existing GitHub auth path (SSH key, GitHub CLI session, or system credential helper) — *read* by the app at clone/refresh time but never *managed* by the app (FR-004).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new Vay engineer with a fresh Ubuntu LTS laptop and a working GitHub login can go from "no VayOBD" to "diagnostic run completed against a real host in the UI" in **under 10 minutes**, without reading the source repo.
- **SC-002**: The end-to-end onboarding requires **zero manual `git clone` invocations**, **zero manual edits** to environment files, and **zero hand-curated SSH config** beyond what the engineer already has for their day-to-day work.
- **SC-003**: At least **90%** of first-time installers on a properly-credentialed machine reach a working app on the first attempt, measured via support-ticket volume and any in-app feedback channels already in place. The .deb itself MUST NOT introduce client-side telemetry to gather this signal.
- **SC-004**: When a user is missing GitHub credentials on first run, **100%** of those users see the actionable credential-setup message (FR-005) — never a silent failure, a 503, or an empty inventory with no explanation.
- **SC-005**: A user can pull a freshly-added telestation or signal-database change into their local copy with **a single user action** that completes in **under 60 seconds** on a typical connection, with no app restart required for the inventory to reflect the change.
- **SC-006**: Support load attributable to "I can't get VayOBD to start" or "my host list is empty / wrong" drops **measurably** within one release cycle of the .deb being adopted as the default install path (baseline: the issues we hit today on the demo laptop).
- **SC-007**: A platform engineer can produce a fresh, install-ready `.deb` from a clean checkout with **a single documented command**, and two such builds from the same commit are functionally equivalent (FR-014).

## Assumptions

- The target install audience is **Vay employees with valid GitHub access to the Reemote / Vay GitHub organisations**. Public / external distribution is out of scope.
- The target platform for v1 is **Ubuntu 24.04 LTS and newer** (24.04 is the supported floor; 26.04 and any future LTS that ship a compatible Python / glibc baseline are also supported targets). Ubuntu 22.04 and earlier are explicitly **not** supported by the .deb; users on those releases should upgrade their OS or keep using the existing `scripts/setup-linux.sh` flow. Other Debian-derivative distros may work but are not explicitly tested or supported. Non-Debian distros (Fedora, Arch, macOS, Windows) are out of scope for this feature.
- The user already has a working credential path to GitHub on their machine before installing the .deb. The .deb verifies and guides — it does not create credentials.
- The application's existing executor binary (the compiled `ree-debug-cli`) is shipped **inside** the .deb as a pre-built artefact; the .deb does not require a Rust toolchain on the user's machine. The platform team builds the binary as part of the package build (FR-014).
- The dependency repos (`Reemote/ree-vehicle-configs`, the `ree-reecu` source tree that supplies errq + DBC files) remain accessible via the user's standard GitHub auth. A move to a fully separate artefact registry is out of scope for v1 and can be done later behind the same FR-006 manifest.
- The frontend SPA is **pre-built** into the .deb at package build time; users do not run `npm` or any Node toolchain locally.
- The application listens on a local port (loopback) on the user's machine. Multi-user or networked deployment scenarios are out of scope for this feature.
- "Refresh" (Story 3) is a foreground, user-initiated action in v1. Automatic background refresh is out of scope and can be revisited if support data shows users forget to refresh.
- The .deb is **telemetry-free** in v1. The only outbound network traffic it generates is the git clone / fetch of the dependency repos and whatever the application already does as part of its existing diagnostic flows. Adding usage analytics is a separate, future feature with its own privacy review.
- The .deb does not bundle the dependency repos themselves (only the manifest pointing at them). Repos are pulled on first run, not at package-build time, so users always start from the upstream default-branch tip rather than a months-old snapshot frozen at build time.

