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
    "last_refreshed_at": "2026-05-06T14:08:11Z",
    "source_revision": "abc1234",
    "host_count": 97
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
    "last_refreshed_at": "2026-05-06T14:11:42Z",
    "source_revision": "def5678",
    "host_count": 98
  }
}
```

**Response 502** — refresh failed; the previously cached copy is
preserved unchanged:

```json
{
  "error": "inventory_refresh_failed",
  "message_key": "inventory.refresh_failed.body"
}
```

The frontend SHOULD surface this as a non-blocking toast and continue to
display the previously cached inventory (per R2: refresh failures do not
replace the existing copy).

---

## `POST /api/runs`

Triggers one diagnostic run. Synchronous: blocks until the run reaches a
terminal state (R5). Server-side hard timeout 25 s.

**Request body**

```json
{ "host_id": "ve-de-apollo" }
```

**Response 200** — run completed (any RunOutcome):

```json
{
  "host_id": "ve-de-apollo",
  "started_at": "2026-05-06T14:12:01Z",
  "completed_at": "2026-05-06T14:12:08Z",
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

## `GET /api/runs/latest?host_id=<HostId>`

Returns the most recent persisted run for a host, if any. Used by US3
(see what was checked) and to repopulate the result screen on
navigation.

**Response 200** — same shape as `POST /api/runs` 200.

**Response 404** — no run has been persisted for this host yet:

```json
{ "error": "no_run_yet", "message_key": "runs.none_yet.body" }
```

---

## Authentication

All endpoints require an authenticated identity forwarded by the upstream
proxy via `X-Vay-User` (R4). The app process trusts this header and uses
it for structured logging only (`triggered_by` on persisted runs). No
in-app login screen.

## Caching headers

- `GET /api/inventory` — `Cache-Control: no-store`. Cheap server-side
  (reads memory snapshot of last-loaded inventory).
- `POST /api/inventory/refresh`, `POST /api/runs` — `Cache-Control: no-store`.
- `GET /api/runs/latest` — `Cache-Control: no-store`.

## Versioning

The path prefix `/api` is unversioned for v1 of this feature. Breaking
changes to any of the schemas above require a follow-up amendment to
this file plus a coordinated frontend update; out-of-band consumers are
not supported in v1.
