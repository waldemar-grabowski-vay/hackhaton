# Contract — `manifest.toml`

**Path**: `/usr/share/vayobd/manifest.toml` (installed by the .deb), `packaging/manifest.toml` (source-of-truth in the repo, copied into the package at build time).
**Owner**: VayOBD package; read-only on the user's filesystem.
**Encoding**: UTF-8, TOML 1.0.0.

This is the **single source of truth** (FR-006) for which private GitHub repositories VayOBD requires to function. An upstream rename or repo move is fixed by editing this file, bumping the package version, and re-issuing the `.deb` — no Python code change.

## Top-level keys

| Key | Type | Required | Description |
|---|---|---|---|
| `manifest_version` | integer | yes | Schema version. v1 is the current version. The application MUST refuse to start if it does not recognise this version. |
| `repo` | array of tables | yes | One entry per required repository. MUST contain at least one entry. |

## `[[repo]]` table

| Key | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Stable slug, regex `^[a-z][a-z0-9-]*$`. Used as the key in `manifest-state.toml` and in log/error messages. Renaming an `id` breaks state continuity for already-installed users — avoid. |
| `url` | string | yes | Canonical clone URL. SSH form (`git@github.com:<org>/<repo>.git`) is preferred; HTTPS form works too. The first-run credential probe (research § 3) chooses the auth mechanism at runtime regardless of URL scheme. |
| `target_path` | string | yes | Where to clone the repo on disk, as a path that the user's shell would expand. `~` is supported and resolved at runtime. The resolved absolute path MUST be under `$HOME`; clones outside the user's home directory are refused for safety. |
| `branch` | string | no | Branch to track. Omitted or empty ⇒ track remote HEAD. |
| `sparse_paths` | array of strings | no | If non-empty, enable sparse-checkout and include only these paths. Each entry MUST be a relative POSIX path with no `..` segments. Saves disk on large repos. |

## Example

```toml
manifest_version = 1

[[repo]]
id          = "ree-vehicle-configs"
url         = "git@github.com:Reemote/ree-vehicle-configs.git"
target_path = "~/.cache/vayobd/ree-vehicle-configs"
branch      = "main"

[[repo]]
id          = "ree-reecu"
url         = "git@github.com:Reemote/ree-reecu.git"
target_path = "~/GitHub/ree-reecu"
branch      = "main"
sparse_paths = [
  "platform/tools/errq",
  "ve/6_tools/CANoe_G4/dbcs",
]
```

## Backward / forward compatibility

- **v1 → v2**: future schema changes bump `manifest_version` to 2. The application refuses to start on a manifest whose version it does not know — better than silently misinterpreting fields. Users would see a "reinstall to get a matching VayOBD" message and recover via `apt upgrade`.
- Adding optional keys within v1 is allowed; the loader ignores unknown keys.

## Validation errors

| Error | Cause | User-visible message (plain language) |
|---|---|---|
| `ManifestVersionError` | `manifest_version` is unsupported | "This VayOBD doesn't understand the bundled repo manifest (version N). Reinstall the latest .deb." |
| `ManifestPathError` | A `target_path` resolves outside `$HOME` | "The repo manifest tried to put `<repo id>` outside your home directory. This is a packaging bug — please report it." |
| `ManifestSchemaError` | Missing required field, bad regex, etc. | "The repo manifest is malformed. This is a packaging bug — please report it." |

All three are unrecoverable from the user's perspective and exit non-zero with no partial side effects (FR-005 / FR-009 spirit).
