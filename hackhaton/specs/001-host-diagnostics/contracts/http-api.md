# HTTP API Contract — Remote Host Diagnostics

The single contract surface between the SPA and FastAPI. Mirrors
`data-model.md`. Keep this file in sync with `frontend/src/api/schemas.ts`
(Zod) and the Pydantic models in `backend/src/vayobd/models.py`.

All endpoints are JSON. All error responses use `application/problem+json`
shape: `{ "error": "<machine_code>", "message_key": "<i18n_key>" }`. No
human English from the backend (R6).

---

## `GET /api/inventory`

Returns the current local-cached inventory plus its freshness metadata.
Used to populate the wizard.

**Response 200**

```json
{
  "meta": {
    "last_refreshed_at": "2026-05-07T14:08:11Z",
    "last_refresh_attempted_at": "2026-05-07T14:08:11Z",
    "consecutive_failed_refreshes": 0,
    "source_revision": "abc1234",
    "host_count": 42
  },
  "hosts": [
    {
      "id": "ve-de-apollo",
      "display_name": "apollo",
      "host_class": "vehicle",
      "type": "vehicle",
      "country": "de",
      "city": null
    },
    {
      "id": "ts-de-ber-zeus",
      "display_name": "zeus",
      "host_class": "telestation",
      "type": "telestation",
      "country": "de",
      "city": "ber"
    }
  ]
}
```

`address` and `source_file` are server-internal and **not returned**.
All `hosts[*].country` values are `"de"` in v1; the wizard's "United
States — Coming soon" tile is a static frontend affordance with no
backing data on the wire.

**Response 503** — local inventory missing or empty (FR-019):

```json
{
  "error": "inventory_unavailable",
  "message_key": "inventory.empty.body"
}
```

The frontend renders the blocking message + "Update inventory" CTA from
`strings.ts` keyed by `message_key`.

---

## `POST /api/inventory/refresh`

Forces an inventory pull on demand (FR-017). Returns once the refresh
completes (success or failure).

**Request body**: empty.

**Response 200**

```json
{
  "meta": {
    "last_refreshed_at": "2026-05-07T14:11:42Z",
    "last_refresh_attempted_at": "2026-05-07T14:11:42Z",
    "consecutive_failed_refreshes": 0,
    "source_revision": "def5678",
    "host_count": 42
  }
}
```

**Response 502** — refresh failed; the previously cached copy is
preserved unchanged:

```json
{
  "error": "inventory_refresh_failed",
  "message_key": "inventory.refresh_failed.body",
  "meta": {
    "last_refreshed_at": "2026-05-07T13:41:42Z",
    "last_refresh_attempted_at": "2026-05-07T14:11:42Z",
    "consecutive_failed_refreshes": 2,
    "source_revision": "def5678",
    "host_count": 42
  }
}
```

Per R2 / FR-027: the frontend MUST continue to use the cached inventory
returned by the prior `GET /api/inventory` and MUST NOT block the
wizard. The `meta` block in the 502 response lets the SPA update its
banner state without an extra round-trip. Surfacing of the persistent
warning banner is gated on
`meta.consecutive_failed_refreshes >= threshold` (configurable, default
3); below the threshold the failure SHOULD be silent (background-only).

---

## `POST /api/runs`

Triggers one diagnostic run. Synchronous: blocks until the run reaches a
terminal state (R5). Server-side hard timeout **30 s** (FR-025).

**Request body**

```json
{ "host_id": "ve-de-apollo" }
```

**Response 200** — run completed (any RunOutcome):

```json
{
  "host_id": "ve-de-apollo",
  "started_at": "2026-05-07T14:12:01Z",
  "completed_at": "2026-05-07T14:12:08Z",
  "outcome": "complete",
  "items": [
    {
      "id": "main_can_bus_reachable",
      "name_key": "item.main_can_bus_reachable.name",
      "description_key": "item.main_can_bus_reachable.description.working",
      "category": "communication",
      "status": "working",
      "recommended_action_key": null,
      "raw_detail": "candump can0: 1 frame in 47ms"
    },
    {
      "id": "expected_front_camera_connected",
      "name_key": "item.expected_front_camera_connected.name",
      "description_key": "item.front_camera.description.error",
      "category": "hardware",
      "status": "error",
      "recommended_action_key": "item.front_camera.action.reconnect",
      "raw_detail": "lsusb: device LI_IMX490 JP2J0208 not present"
    }
  ]
}
```

For `outcome` of `unreachable` or `timeout`, `items` is `[]` and the
frontend renders a single user-facing message keyed by the outcome
(FR-006).

**Response 409** — a run is already in progress for this host (FR-011):

```json
{
  "error": "run_in_progress",
  "message_key": "runs.in_progress.toast"
}
```

Frontend behaviour: disable the "Run check" button while a run is
in-flight to prevent this in normal operation; surface the toast
defensively if it does occur.

**Response 404** — host id is not in the current cached inventory (e.g.,
removed on the last refresh):

```json
{
  "error": "unknown_host",
  "message_key": "runs.unknown_host.body"
}
```

---

## (Intentionally not in v1) `GET /api/runs/latest`

A read endpoint returning the operator's persisted last run for a given
host is **not exposed in v1** per FR-028 — the result view always
opens blank, and the operator must trigger a fresh run to see anything.
Persistence still happens server-side per FR-026 and `research.md` R7,
but no v1 client surface reads it. A follow-up that re-introduces this
endpoint (e.g., to repopulate the result view after an accidental
browser refresh) would scope the lookup to the authenticated operator
identity, mirroring the on-disk layout
(`~/.cache/vayobd/runs/<operator-slug>/<host_id>.json`).

---

## Authentication

All endpoints require an authenticated identity forwarded by the upstream
proxy via `X-Vay-User` (R4). The app process trusts this header and uses
it for two purposes:

1. **Persistence keying** — the sanitised slug becomes the directory
   segment under `~/.cache/vayobd/runs/<operator-slug>/` (FR-026).
2. **Structured logging** — `triggered_by` on persisted run records.

If `X-Vay-User` is missing, empty, or sanitises to an empty slug, the
endpoint MUST return HTTP 401. There is no fallback "anonymous"
identity; the dev environment documents how to set the header (see
`quickstart.md`). No in-app login screen.

## Caching headers

- `GET /api/inventory` — `Cache-Control: no-store`. Cheap server-side
  (reads memory snapshot of last-loaded inventory).
- `POST /api/inventory/refresh`, `POST /api/runs` — `Cache-Control: no-store`.

## Versioning

The path prefix `/api` is unversioned for v1 of this feature. Breaking
changes to any of the schemas above require a follow-up amendment to
this file plus a coordinated frontend update; out-of-band consumers are
not supported in v1.
