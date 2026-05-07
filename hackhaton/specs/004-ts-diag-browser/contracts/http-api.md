# HTTP API delta — what 004 adds and changes

This document only covers the HTTP API delta for 004. The base contract
lives in `specs/002-real-executor/contracts/http-api.md`. Changes here are
additive — no existing endpoints are altered.

## Added endpoints

### `GET /api/live/{host_id}/ws` — WebSocket upgrade

See `contracts/websocket.md` for the full message contract. The HTTP-side
behaviour:

- **Upgrade**: `HTTP/1.1 101 Switching Protocols` on success.
- **`400 Bad Request`** if `host_id` is not a valid inventory id format.
- **`401 Unauthorized`** if `X-Vay-User` is missing.
- **`403 Forbidden`** if Developer mode is off in the on-disk settings or
  the `developer_mode_check=1` query param is missing.
- **`404 Not Found`** if `host_id` does not exist in the in-scope inventory
  (Germany only).

The WebSocket itself owns the lifecycle once upgraded; failures inside the
session use WebSocket close codes (see `websocket.md`), not HTTP statuses.

## Modified endpoints

### `GET /api/health`

Adds two booleans to the existing JSON body:

```json
{
  "executor": "ree",
  "engine_version": "abc123d",
  "live_diagnostic": {
    "enabled": true,
    "errq_loaded": true,
    "errq_source_path": "/home/op/GitHub/ree-reecu",
    "dbc_loaded": true,
    "dbc_source_path": "/home/op/GitHub/ree-reecu/.../ts.dbc"
  }
}
```

`live_diagnostic.enabled` is `true` iff the on-disk setting
`developer_mode = true`. The frontend uses this to decide whether to render
the "Live diagnostic" button (FR-001).

`errq_loaded` / `dbc_loaded` reflect the startup probe results and are the
authoritative signal for FR-012 degraded mode visibility on the frontend.

### `GET /api/settings`

Adds three keys to the existing settings response (writes go through the
existing `PUT /api/settings`):

```json
{
  ...existing keys from 002...,
  "developer_mode": false,
  "ree_reecu_path": "/home/op/GitHub/ree-reecu",
  "dbc_path": "/home/op/GitHub/ree-reecu/.../ts.dbc"
}
```

Validation on `PUT`:
- `developer_mode` MUST be a boolean.
- `ree_reecu_path` and `dbc_path` are echoed as-is; the backend validates
  reachability at next startup and surfaces results via `/api/health`. This
  matches the existing 002 settings flow's "save now, validate at
  refresh" pattern.

## Endpoints NOT changed

- `GET /api/inventory` — unchanged. The Live diagnostic page reuses the
  same in-scope host list.
- `POST /api/runs` and `GET /api/runs/...` — unchanged. The Live
  diagnostic surface does not interact with the existing run history.
- `GET /api/repair-guide/...` — unchanged.

## Authentication

Same X-Vay-User SSO header as 001 / 002. The Live diagnostic surface is
NOT exempt — every WebSocket handshake validates the header before
upgrading.
