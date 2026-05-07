# Data Model — Remote Host Diagnostics

Pydantic v2 models on the backend; matching Zod schemas on the frontend
under `frontend/src/api/schemas.ts`. Field names are snake_case at the API
boundary (Python convention); the frontend converts to camelCase only
inside React components if helpful.

---

## HostId

Type: `str` (regex-validated). Stable identifier for a host, derived from
the YAML filename in `ree-vehicle-configs` with the `.yaml` suffix
stripped.

- Examples: `ve-de-apollo`, `ts-de-ber-zeus`.
- Pattern: `^(ve|ts)-de(-[a-z0-9-]+)+$` (DE-only in v1 per
  Clarification 2026-05-07).
- Used as a path-safe slug; never contains VIN or PII.

## Country

Enum: `"de"`. Derived from segment 2 of the host filename. v1 hosts with
any other country segment (e.g., `us`, `be`) are filtered out at load
time and never reach the API (FR-001b). The Country wizard step in the
SPA renders an additional disabled-only "United States — Coming soon"
tile as a static UI affordance; that tile does not correspond to any
data on the wire (see `contracts/http-api.md`).

## HostType

Enum: `"vehicle" | "telestation"`. Derived from segment 1 of the host
filename (`ve-` → vehicle, `ts-` → telestation).

## City

Type: `str | null`. Derived from segment 3 of the host filename **only**
for telestations (e.g., `ts-de-ber-zeus` → `"ber"`; rendered to operator
as `"Berlin"` via the `strings.ts` city table). For vehicles, always
`null`. Constraint enforced by FR-001a: vehicles have no city.

## Host

The picker-facing record for one selectable host. Returned inside `Inventory`.

| Field | Type | Source / notes |
|---|---|---|
| `id` | `HostId` | Filename slug. |
| `display_name` | `str` | Human-friendly label shown in the picker. Derived from the last filename segment (`apollo`, `01001`, `zeus`); the frontend may pretty-print it (e.g., `Apollo`, `Vehicle 01001`). |
| `host_class` | `str` | `"vehicle"` or `"telestation"`; equal to `type` today, but kept distinct so a future host class (e.g., a different vehicle generation with a different check catalog) doesn't reshape the API. |
| `type` | `HostType` | Picker step 2 grouping. |
| `country` | `Country` | Picker step 1 grouping. |
| `city` | `City` | Picker step 3 grouping (telestation only). |
| `address` | `str` | Reachability address used by the executor. Server-internal; **never returned to the frontend**. |
| `source_file` | `str` | Repo-relative path inside `ree-vehicle-configs`. Server-internal; surfaced to operator only via Developer mode raw_detail when relevant. |

Validation rules:
- `city is None` ⇔ `type == "vehicle"`.
- `country` is one of the v1 in-scope set; out-of-scope hosts are dropped at load time, not filtered at request time.

## InventoryMeta

| Field | Type | Notes |
|---|---|---|
| `last_refreshed_at` | `datetime` (ISO 8601 UTC) | Most recent **successful** `git fetch + reset` timestamp. Surfaced by `GET /api/inventory` for FR-018. |
| `last_refresh_attempted_at` | `datetime \| null` | Most recent refresh **attempt** timestamp, success or failure. Distinct from `last_refreshed_at` so the frontend can tell that a retry happened recently even if it failed. |
| `consecutive_failed_refreshes` | `int` | Count of consecutive refresh failures since the last successful refresh. Zero on success. The frontend renders the FR-027 warning banner once this crosses the configurable threshold (default 3). |
| `source_revision` | `str` | Short SHA of the cached checkout's HEAD. |
| `host_count` | `int` | Number of in-scope hosts after country filtering. |

## Inventory

The full payload returned by `GET /api/inventory`.

| Field | Type | Notes |
|---|---|---|
| `meta` | `InventoryMeta` | |
| `hosts` | `list[Host]` | All in-scope hosts. The frontend wizard groups them; the backend does not pre-group. |

The frontend derives wizard steps locally:
- Step 1 (Country): in v1, exactly two tiles are rendered — **Germany**
  (selectable; comes from the unique `host.country` value `"de"`) and
  **United States** (rendered as a disabled "Coming soon" affordance
  with no backing data; see Clarification 2026-05-07 in `spec.md`).
  Selecting the US tile is a no-op and does not advance the wizard.
- Step 2 (Type): unique `host.type` values within the chosen country.
- Step 3 (City): unique `host.city` values within `(country, telestation)`. **Not shown** when type is vehicle.
- Step 4 (Host): hosts matching the chain above.

## DiagnosticItem

One thing that was checked. Returned inside `DiagnosticRun.items`.

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Stable per host class (e.g., `"main_can_bus_reachable"`). Same id appears in every run of the same host class, which is what makes "this errored item now appears in Working" (US2) trivially correct. |
| `name_key` | `str` | String key resolved by `frontend/src/strings.ts` (e.g., `"item.main_can_bus_reachable.name"`). |
| `description_key` | `str | null` | Optional plain-language description key. |
| `category` | `Enum["communication" \| "hardware" \| "configuration"]` | Plain-language label per FR-010; rendered by the frontend. |
| `status` | `Enum["working" \| "error"]` | |
| `recommended_action_key` | `str | null` | Required (non-null) when `status == "error"` (FR-005). |
| `raw_detail` | `str | null` | Underlying technical output (CAN trace excerpt, exit code, parser message). **Always included in the API response** so a Developer-mode toggle on the frontend doesn't require a re-request. The frontend MUST NOT render this field unless Developer mode is active (FR-022). |

Validation rules:
- `status == "error"` ⇒ `recommended_action_key is not None`.
- `raw_detail` is server-trusted; it MUST NOT contain VIN or PII (server-side scrubber in `checks/runner.py`).

## RunOutcome

Enum: `"complete" | "partial" | "unreachable" | "timeout"`. Drives FR-006.

- `complete`: every catalog item ran and produced a status.
- `partial`: at least one item ran but at least one didn't (e.g., SSH succeeded but one check timed out individually).
- `unreachable`: SSH/connection layer never succeeded; no item-level results returned.
- `timeout`: server-side **30 s** hard timeout fired before either category resolved (FR-025).

## DiagnosticRun

The result returned by `POST /api/runs`. Also persisted on disk per
`(operator, host_id)` pair (FR-026); v1 exposes no read endpoint for
the persisted record (FR-028 — see `research.md` R7).

| Field | Type | Notes |
|---|---|---|
| `host_id` | `HostId` | |
| `started_at` | `datetime` | Server clock. |
| `completed_at` | `datetime` | Server clock. Equal to `started_at` for `unreachable` outcomes that fail the connection phase. |
| `outcome` | `RunOutcome` | |
| `items` | `list[DiagnosticItem]` | Empty when `outcome in {"unreachable", "timeout"}`. Populated otherwise. Order is the catalog order for the host class (deterministic). |

State transitions (server-internal):

```text
[idle] ──POST /api/runs──▶ [running] ──ssh ok──▶ [executing items] ──┬─▶ [complete]
                              │                                        ├─▶ [partial]
                              │                                        └─▶ [timeout]
                              └─ssh fails──▶ [unreachable]
```

`[running]` holds the per-`host_id` lock from R5; releasing it transitions
back to `[idle]`. The lock is the only mutable state outside the on-disk
`runs/<host_id>.json` cache.

## OperatorIdentity (server-internal)

Pulled from the `X-Vay-User` proxy header per R4. **Load-bearing**:
this value is used as a path segment when persisting runs (FR-026), so
it must be sanitised before being used in I/O.

| Field | Type | Notes |
|---|---|---|
| `username` | `str` | Raw value from the trusted `X-Vay-User` header. Used in structured logs and the run cache file's `triggered_by` field. Never returned in API responses to avoid leaking identity into client logs. |
| `slug` | `str` (derived) | `username` lowercased and stripped to `[a-z0-9._-]`. Used as the directory segment under `~/.cache/vayobd/runs/`. Must be non-empty after sanitisation; if it is, the request is rejected with HTTP 401. |

## Persistence shapes

- `~/.cache/vayobd/inventory.meta.json` ↔ `InventoryMeta` JSON.
- `~/.cache/vayobd/runs/<operator-slug>/<host_id>.json` ↔ `DiagnosticRun`
  JSON, plus an internal `triggered_by: OperatorIdentity` field stripped
  from API responses. Each operator's directory is independently
  read/writeable; one operator's runs are not visible to another via
  any v1 API surface (FR-026).
- `~/.cache/vayobd/ree-vehicle-configs/` ↔ git checkout (managed by
  `inventory/sync.py`).
