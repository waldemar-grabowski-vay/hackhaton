# Contract — HTTP API delta

**Baseline**: `specs/004-ts-diag-browser/contracts/http-api.md` (current API surface).
**Delta in this feature**: two new endpoints under `/api/refresh*`. No existing endpoint changes shape.

Both endpoints require the same `X-Vay-User` header the rest of the API requires (delegated to the upstream proxy in production, injected by Vite in dev). No new permissions model.

---

## `POST /api/refresh`

Drives the manifest-driven refresh from the in-app button (the UI half of FR-008). Internally calls the same function `vayobd refresh` calls (FR-008 "MUST drive the same underlying refresh logic").

### Request

```http
POST /api/refresh HTTP/1.1
X-Vay-User: alice@vay.io
Content-Type: application/json

{}
```

Body is currently empty `{}`. Reserved for a future `repos: ["id1", "id2"]` filter that would mirror `vayobd refresh --repo ID`. v1: full refresh only.

### Response — refresh started

```http
HTTP/1.1 202 Accepted
Content-Type: application/json

{
  "refresh_id": "01HXY...",
  "started_at": "2026-05-11T09:42:48Z"
}
```

Returned immediately. The actual git work runs in a background task on the backend. Poll `GET /api/refresh/status` for completion.

### Response — refresh already in progress

```http
HTTP/1.1 409 Conflict
Content-Type: application/json

{
  "error": "refresh_in_progress",
  "message_key": "refresh.already_running",
  "refresh_id": "01HXY...",
  "started_at": "2026-05-11T09:42:48Z"
}
```

A second POST while a refresh is already running returns 409 with the in-flight refresh's ID. The frontend should not retry; it should poll status instead.

### Response — auth / manifest error

```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "error": "credentials_failed",
  "message_key": "refresh.credentials_failed",
  "tried": [
    {"surface": "ssh", "outcome": "no key loaded"},
    {"surface": "gh",  "outcome": "not installed"},
    {"surface": "credential-helper", "outcome": "not configured"}
  ],
  "suggestions": [
    "Add your SSH key to GitHub and run ssh-add",
    "Run `gh auth login`"
  ]
}
```

The frontend renders these in the StalenessBanner. Same shape as the FR-005 first-run error so the UI has one code path.

---

## `GET /api/refresh/status`

Polled by the UI while a refresh is running. Also the source of the staleness banner's data when no refresh is in progress.

### Response — idle

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "state": "idle",
  "stalest_age_seconds": 187234,
  "repos": [
    {
      "id": "ree-vehicle-configs",
      "last_synced_at": "2026-05-09T05:30:00Z",
      "last_outcome": "ok",
      "resolved_revision": "a1b2c3d4..."
    },
    {
      "id": "ree-reecu",
      "last_synced_at": "2026-05-09T05:30:00Z",
      "last_outcome": "ok",
      "resolved_revision": "f0e1d2c3..."
    }
  ]
}
```

`stalest_age_seconds` is the max age across all repos. The UI shows the staleness banner when this exceeds the configured threshold (default 86400 = 24 h).

### Response — running

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "state": "running",
  "refresh_id": "01HXY...",
  "started_at": "2026-05-11T09:42:48Z",
  "current_repo": "ree-reecu",
  "completed": ["ree-vehicle-configs"]
}
```

Lets the UI show "Refreshing ree-reecu… (1 of 2 done)". The button is disabled while `state == "running"`.

### Response — last refresh failed

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "state": "idle",
  "stalest_age_seconds": 187234,
  "last_refresh_outcome": "partial_failure",
  "last_refresh_at": "2026-05-11T09:43:12Z",
  "repos": [
    {
      "id": "ree-vehicle-configs",
      "last_synced_at": "2026-05-11T09:43:00Z",
      "last_outcome": "ok",
      "resolved_revision": "b2c3d4..."
    },
    {
      "id": "ree-reecu",
      "last_synced_at": "2026-05-09T05:30:00Z",
      "last_outcome": "network-error",
      "resolved_revision": "f0e1d2c3..."
    }
  ]
}
```

`last_refresh_outcome` is `null` on a clean install or after a fully successful refresh; otherwise one of `partial_failure | credentials_failed | network_error | conflict`. The banner uses this to show "last refresh: 1 of 2 repos updated; ree-reecu couldn't be reached".

---

## Errors (shared)

Reuses the existing 401 `missing_operator_identity` and the existing error envelope (`error`, `message_key`). No new global error shapes are introduced.
