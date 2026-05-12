# Data Model — VayOBD .deb package

**Date**: 2026-05-11
**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)

This feature adds two new files to the user's filesystem and one new Pydantic settings field. No databases, no schemas, no migrations. All state is per-user and lives under `~/.cache/vayobd/` (per FR-011 / FR-012, so package upgrade/remove never touches it).

---

## 1. Required-repos manifest (read-only, shipped in the `.deb`)

**Location in package**: `/usr/share/vayobd/manifest.toml`
**Location after install**: same (read-only, owned by root, mode `0644`).
**Loaded by**: `backend/src/vayobd/install/manifest.py` on every `vayobd run` startup and at the start of every refresh.

### Schema (TOML)

```toml
# /usr/share/vayobd/manifest.toml — Required-repos manifest
# FR-006: single source of truth for every repo VayOBD needs to clone on first run
# and refresh. An upstream rename is a one-line change here.

manifest_version = 1   # bumped only on incompatible schema changes

[[repo]]
id          = "ree-vehicle-configs"
url         = "git@github.com:Reemote/ree-vehicle-configs.git"
target_path = "~/.cache/vayobd/ree-vehicle-configs"
branch      = "main"          # optional; defaults to remote HEAD
# sparse_paths = []           # optional; if set, sparse-checkout these dirs only

[[repo]]
id          = "ree-reecu"
url         = "git@github.com:Reemote/ree-reecu.git"
target_path = "~/GitHub/ree-reecu"   # matches existing config.py default
branch      = "main"
# Only the errq + dbcs subtrees are actually needed; sparse-checkout to save disk.
sparse_paths = ["platform/tools/errq", "ve/6_tools/CANoe_G4/dbcs", "ve/6_tools/CANoe_G4/dbcs/Env.dbc"]
```

### Python representation (Pydantic)

```python
# backend/src/vayobd/install/manifest.py
class RepoEntry(BaseModel):
    id: str                       # short, slug-style; used as the key in manifest-state.toml
    url: str                      # canonical clone URL (SSH form by default)
    target_path: Path             # may contain ~; resolved with expanduser() before use
    branch: str | None = None     # None ⇒ remote HEAD
    sparse_paths: list[str] = []  # empty ⇒ full clone

class Manifest(BaseModel):
    manifest_version: int         # currently always 1
    repo: list[RepoEntry]
```

### Validation rules

- `manifest_version` MUST equal `1`. Older / newer ⇒ `ManifestVersionError` (CLI / API surface as plain-language: "this VayOBD doesn't understand the bundled manifest; reinstall to get a matching version").
- `repo[].id` MUST match `^[a-z][a-z0-9-]*$` and be unique within the file.
- `repo[].url` MUST be a non-empty string; URL scheme validation deferred to `git` (it knows better than we do).
- `repo[].target_path` MUST be under `$HOME` after `expanduser()`. Anything else ⇒ `ManifestPathError` (refuses to clone outside the user's home dir for safety).
- `sparse_paths` MUST be a list of relative POSIX paths; absolute paths or `..` segments ⇒ rejected.

---

## 2. Manifest state (per-user, generated at runtime)

**Location**: `~/.cache/vayobd/manifest-state.toml`
**Owner**: the invoking user (mode `0644`).
**Lifecycle**: created on first successful clone, updated after every refresh, never deleted by `apt remove` / `apt upgrade` (FR-011, FR-012).

### Schema (TOML)

```toml
# ~/.cache/vayobd/manifest-state.toml — generated; do not hand-edit
# Survives apt upgrade / remove. Delete this file to force a full first-run re-clone.

last_credential_probe = "2026-05-11T09:42:31Z"
credential_surface_used = "ssh"   # one of: ssh | gh | credential-helper

[repo.ree-vehicle-configs]
last_synced_at = "2026-05-11T09:42:48Z"
last_attempted_at = "2026-05-11T09:42:48Z"
resolved_revision = "a1b2c3d4e5f6..."
last_outcome = "ok"               # ok | network-error | auth-error | conflict

[repo.ree-reecu]
last_synced_at = "2026-05-11T09:43:12Z"
last_attempted_at = "2026-05-11T09:43:12Z"
resolved_revision = "f0e1d2c3b4a5..."
last_outcome = "ok"
```

### Python representation

```python
# backend/src/vayobd/install/state.py
class RepoState(BaseModel):
    last_synced_at: datetime | None     # None ⇒ never successfully synced
    last_attempted_at: datetime | None
    resolved_revision: str | None       # SHA at last successful sync
    last_outcome: Literal["ok", "network-error", "auth-error", "conflict"]

class ManifestState(BaseModel):
    last_credential_probe: datetime | None
    credential_surface_used: Literal["ssh", "gh", "credential-helper"] | None
    repo: dict[str, RepoState]          # keyed by RepoEntry.id

    @property
    def is_first_run(self) -> bool:
        """True iff no repo has ever been successfully synced."""
        return not any(s.last_synced_at for s in self.repo.values())

    def stalest_age(self, now: datetime) -> timedelta | None:
        """Used by the in-app staleness banner (FR-010)."""
        ...
```

### State transitions

```
                ┌─────────────────┐
                │  first-run      │  manifest-state.toml absent or is_first_run=True
                │  (Story 2)      │
                └────────┬────────┘
                         │ probe credentials
                  ┌──────┴───────┐
                  ▼              ▼
              all fail       one succeeds
                  │              │
       FR-005 message            ▼
       exit non-zero       clone every repo
       (Story 2 AS-3)            │
                          ┌──────┴───────┐
                          ▼              ▼
                       any fails      all succeed
                          │              │
                  rollback partial    write manifest-state
                  state (FR-009)        is_first_run=False
                  show per-repo            │
                  message                  ▼
                                    ┌───────────────┐
                                    │  steady state │
                                    └───────┬───────┘
                                            │ vayobd refresh OR
                                            │ POST /api/refresh
                                            ▼
                                       refresh flow
                                       (re-runs above, but
                                       failures keep last
                                       successful state ⇒
                                       SC-005 / FR-009)
```

---

## 3. Settings deltas (`backend/src/vayobd/config.py`)

The existing `Settings` class gains **one** field. No removed or renamed fields; full backward compat.

```python
# Addition to backend/src/vayobd/config.py
class Settings(BaseSettings):
    # … existing fields unchanged …

    # 006 — Required-repos manifest. Defaults to the shipped path; overridable
    # via VAYOBD_MANIFEST_PATH for tests / dev runs.
    manifest_path: Path = Path("/usr/share/vayobd/manifest.toml")
```

When the file at `manifest_path` is absent (e.g., a dev checkout, no .deb installed), the loader falls back to `packaging/manifest.toml` relative to the repo root. This lets `run-dev.sh` and the existing integration tests work unchanged.

---

## 4. Filesystem layout summary (post-install, post-first-run)

```
/usr/bin/vayobd                      # symlink → /usr/lib/vayobd/bin/vayobd-launcher
/usr/lib/vayobd/                     # owned by the package
├── bin/
│   ├── vayobd-launcher              # shell shim that exec's the venv python
│   └── ree-debug-cli                # pre-built Rust engine
├── venv/                            # relocatable Python venv with backend + deps
└── share/                           # nothing here yet
/usr/share/vayobd/
├── manifest.toml                    # required-repos manifest (FR-006)
└── spa/                             # pre-built frontend (Vite `dist/`)
/usr/share/applications/vayobd.desktop  # desktop launcher

~/.config/vayobd/settings.toml       # user settings (existing, untouched)
~/.cache/vayobd/
├── manifest-state.toml              # generated; per-user; survives reinstall
├── ree-vehicle-configs/             # cloned per manifest
└── ree-reecu/                       # cloned per manifest (sparse)
~/GitHub/ree-reecu                   # only if manifest's target_path points here
```

---

## 5. Entity-to-spec mapping

| Spec entity (`spec.md`) | Implementation |
|---|---|
| Package artefact | `dist/vayobd_<ver>_amd64.deb` produced by `packaging/build.sh` |
| Required-repos manifest | `/usr/share/vayobd/manifest.toml` (section 1) |
| Per-user cache | `~/.cache/vayobd/` + `manifest-state.toml` (section 2) |
| Per-user settings | `~/.config/vayobd/settings.toml` (existing, untouched) |
| Credential surface | Not stored; probed at runtime by `install/credentials.py`. The outcome is recorded in `manifest-state.toml` (`credential_surface_used`) for FR-004a. |
