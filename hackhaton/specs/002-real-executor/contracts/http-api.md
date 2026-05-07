# HTTP API Contract — Delta from `001-host-diagnostics`

This document captures *only* the differences from
`specs/001-host-diagnostics/contracts/http-api.md`. Anything not
listed here is unchanged. The 001 contract for `POST /api/runs`,
`GET /api/inventory`, the auth / `X-Vay-User` header rule, the
problem+JSON envelope shape, and the strings.ts `message_key` story
all carry forward verbatim.

---

## Removed routes

`POST /api/inventory/refresh` — gone. The cache layer it served is
retired (FR-013a; per-request inventory re-read).

---

## Modified routes

### `GET /api/inventory`

Same 200 / 503 shape as 001, but the `meta` block is **slimmed**
(FR-013a — no caching means no refresh-attempted timestamps and no
failure counter):

```json
{
  "meta": {
    "last_read_at": "2026-05-07T12:13:14.000Z",
    "source_path": "/home/operator/GitHub/ree-vehicle-configs",
    "host_count": 5
  },
  "hosts": [ /* unchanged from 001 */ ]
}
```

503 response unchanged in shape but reuses the FR-019 envelope. The
exp-backoff banner state from 001's `consecutive_failed_refreshes`
field is gone. Frontend's `InventoryRefreshBanner` component is
deleted in lockstep (plan.md project structure).

### `POST /api/runs`

Path, request body, and 200/4xx/5xx shapes carry forward from 001
verbatim. Two changes:

1. **Response item `status` enum extended**: `working | warning |
   error` (FR-004a). 001 callers that hard-coded "exactly two
   values" need updating. The frontend Zod schema in
   `data-model.md` Layer 3 is the source of truth.
2. **Response item `category` enum extended**: `communication |
   hardware | configuration | software | calibration` (FR-006).

### Stable error codes (additions)

001's existing codes (`run_in_progress`, `unknown_host`,
`inventory_unavailable`, `inventory_refresh_failed`,
`missing_operator_identity`, `invalid_operator_identity`) carry
forward. New codes for FR-007 + FR-009:

| Error code | HTTP | When | `message_key` |
|---|---|---|---|
| `engine_unavailable` | 503 | `ree-debug-cli` binary cannot be located via the FR-003 resolution order (missing/unbuilt). Remediation copy includes `cargo build --release --workspace` from `engine/`. | `engine.unavailable.body` |
| `engine_incompatible` | 503 | The binary is present and `--version` runs, but produces a SHA the backend doesn't recognise (typically: stale binary from an older workspace SHA), or `--version` exits non-zero / fails to parse. Remediation copy: rebuild the engine. | `engine.incompatible.body` |
| `inventory_unconfigured` | 200 (NOT an error per se) | The settings file is missing or `[inventory]` is unset on the operator's machine. The SPA renders the setup card. | `settings.inventory_unconfigured.body` |
| `path_missing` | 422 | Setup-card validation: the path the operator entered does not exist on disk. | `settings.path_missing.body` |
| `path_not_a_directory` | 422 | Setup-card validation: path exists but isn't a directory. | `settings.path_not_a_directory.body` |
| `inventory_yaml_missing` | 422 | Setup-card validation: directory exists but lacks `org/vay/inventory.yaml`. | `settings.inventory_yaml_missing.body` |
| `inventory_yaml_unparseable` | 422 | Setup-card validation: file exists but isn't valid YAML or doesn't match the expected shape. | `settings.inventory_yaml_unparseable.body` |
| `inventory_yaml_empty` | 422 | Setup-card validation: file parsed but contains zero in-scope hosts. | `settings.inventory_yaml_empty.body` |

The `inventory_unconfigured` "code" is unusual — it surfaces in a
**200** body from `GET /api/settings/inventory-path` (see new route
below), not as an error. The SPA reads the body to decide whether
to show the wizard or the setup card.

---

## New routes

### `GET /api/settings/inventory-path`

Read the operator's persisted settings + the engine mode the
backend booted with. The SPA calls this at startup before anything
else.

**Response 200**

```json
{
  "inventory": {
    "path": "/home/operator/GitHub/ree-vehicle-configs"
  },
  "engine_mode": "live"
}
```

When no settings file exists (or the persisted path no longer
validates per R5), `inventory` is `null`:

```json
{
  "inventory": null,
  "engine_mode": "live"
}
```

The SPA renders the `InventorySetupCard` whenever `inventory ===
null`, regardless of `engine_mode`.

`engine_mode` is `"live"` when `VAYOBD_EXECUTOR=ree` (the production
default) and the engine binary self-check succeeded; `"fixture"`
when `VAYOBD_EXECUTOR=fixture`. The SPA renders the
`EngineModeBadge` accordingly (FR-007's visibility rule).

### `POST /api/settings/inventory-path`

Persist a new inventory path. Validates per R5; failures return one
of the `path_*` / `inventory_*` 422 codes from the table above with
the `meta` echo (the offending path) so the setup card can surface
the right error inline.

**Request body**

```json
{ "path": "/home/operator/GitHub/ree-vehicle-configs" }
```

**Response 200**

```json
{
  "inventory": {
    "path": "/home/operator/GitHub/ree-vehicle-configs"
  },
  "engine_mode": "live"
}
```

**Response 422** — validation failed:

```json
{
  "error": "inventory_yaml_missing",
  "message_key": "settings.inventory_yaml_missing.body",
  "meta": {
    "path": "/home/operator/Wrong/Path"
  }
}
```

The backend MUST validate synchronously (R5) and MUST NOT touch
disk after a 422 — the prior settings remain in place.

---

## Authentication header

Carries forward from 001: `X-Vay-User` is required on every API
endpoint that produces or persists run-shaped data
(`POST /api/runs`, the run audit log). The new settings endpoints
also require it — settings are tied to the OS user owning the
FastAPI process, but the FR-026 per-operator audit / persistence
contract still applies (so we know *who* set the path, even if the
path itself is one-per-machine).

---

## Caching headers

Same as 001: `Cache-Control: no-store` on every endpoint above.
`GET /api/inventory` re-reads the YAML per request (FR-013a) — no
intermediary should cache it.

---

## Versioning

The `/api` prefix is unversioned for v1 of this feature, matching
001. Breaking schema changes (e.g., a 4th `status` value) require a
follow-up amendment to this file plus a coordinated frontend update;
out-of-band consumers are not supported.
