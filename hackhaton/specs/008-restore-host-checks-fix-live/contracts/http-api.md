# HTTP API Contract — 008 unified host-detail surface

**Owner**: `backend/src/vayobd/api/host_versions.py` (host detail);
`backend/src/vayobd/api/runs.py` (restored runs endpoint).
**Phase**: 008 — extends 007's `GET /api/host/{id}/versions` to carry
the restored check battery and re-exposes the pre-007 `/api/runs`
route.

This file specifies wire shape, query parameters, status codes, and
caching semantics for the two endpoints the host-detail page
consumes.

---

## 1. `GET /api/host/{host_id}/versions[?fresh=true]`

**Owner**: 007 collector (`api/host_versions.py`), extended in 008.
**Auth**: `Depends(current_operator)`.

The same query-parameter contract from 007 (FR-019): `?fresh=true`
invalidates the per-host TTL entry and forces a fresh capture of
both pipelines. Any other `fresh` value returns HTTP 400.

### Successful response (200 OK)

```jsonc
{
  "host": { /* inventory Host */ },

  "versions": {                      // 007's version card (unchanged)
    "vdrive_manifest": { ... },
    "vreecu_version":  { ... },      // populated from REECU pipeline
    "sec_version":     { ... }       // populated from REECU pipeline
  },

  "run": {                           // restored check battery (008)
    "host_id":      "ts-de-ber-zeus",
    "started_at":   "2026-05-11T14:02:08Z",
    "completed_at": "2026-05-11T14:02:13Z",
    "outcome":      "complete",      // | "partial" | "unreachable" | "timeout"
    "items": [
      {
        "id":        "main_can_bus_reachable",
        "name_key":  "item.main_can_bus_reachable.name",
        "category":  "communication",
        "status":    "working",
        "raw_detail": "candump can0 returned frames within 2 s"
      },
      {
        "id":        "peplink_cellular_connected",
        "name_key":  "item.peplink_cellular_connected.name",
        "description_key": "item.peplink_cellular.description.error",
        "category":  "communication",
        "status":    "error",
        "recommended_action_key": "item.peplink_cellular.action",
        "raw_detail": "HTTP GET https://192.168.50.1/cgi-bin/MANGA/api.cgi returned 502"
      }
      // … one item per restored catalog entry; REECU items are NOT here
      //   (those live in `versions` per FR-011)
    ]
  },

  "source": "live"                   // "unavailable" only if BOTH pipelines fail entirely
}
```

### Loading semantics (parallel pipelines)

Per FR-010, the two pipelines run in parallel:

- **REECU pipeline** — one-shot candump capture (4 s wall-clock per
  research §3) → DBC decode → field extraction. Drives the
  `versions.vreecu_version` and `versions.sec_version` cells and any
  REECU-tagged items.
- **Non-REECU pipeline** — `ree-debug-cli report --host <id> --json`
  → parse → map to `DiagnosticItem` rows + `versions.vdrive_manifest`.

The endpoint returns ONE response once BOTH pipelines complete.
The SPA renders the loading state (em-dash + spinner from 007) on
both surfaces until that response arrives. The 60-second TTL cache
makes re-mounts within the window instant.

### Response composition rules (FR-011 — no duplicates)

A row that the REECU pipeline produces MUST NOT also appear in
`run.items`. Concretely:

- REECU rows (`vREECU firmware`, `SEC version`, `SEC state`,
  ERRQ-decoded errors) → live in `versions` (or as a future
  per-item entry there) — never in `run.items`.
- Non-REECU rows (vDrive package, Peplink, network, cameras, WAKE,
  config validity, harness layout, etc.) → live in `run.items`.

The unified collector enforces this by filtering out any row
emitted by `ree-debug-cli report` whose name overlaps the REECU
patterns (the same patterns 007's `_find_row` uses) before it
hits `run.items`.

### Error responses

| HTTP | Body shape | When |
|---|---|---|
| 400 | `{"error":"bad_query","message_key":"host_versions.bad_query"}` | `?fresh` value other than `"true"` or absent |
| 401 | (existing auth shim payload) | No / invalid operator header |
| 404 | `{"error":"host_not_found","message_key":"host.not_found"}` | Host id not in inventory |
| 503 | `{"error":"inventory_unavailable","message_key":"inventory.empty.body"}` | Inventory file missing or unparseable |

Never 5xx on engine / REECU pipeline failures — those collapse to
`source: "unavailable"` with `run.outcome: "unreachable"` and
every version cell marked `unavailable`. Same disposition as 007 +
the pre-007 unreachable contract.

### Caching

Same as 007 (FR-017 / FR-018):

- 60-second per-host TTL.
- `?fresh=true` invalidates the entry for the requested host
  before the pipelines run.
- Per-host scoping — refreshing host A doesn't bust host B.

Cache holds the entire `HostDetailResponse`; both pipelines'
results are served from the same cached object.

---

## 2. `POST /api/runs` (restored)

**Owner**: 008 — restored verbatim via
`git checkout HEAD -- backend/src/vayobd/api/runs.py`.

The pre-007 run endpoint comes back unchanged. Used by the
restored `RunResultPage` AND by the unified host-detail collector
internally (the same `execute_run` path runs underneath the new
endpoint to populate `HostDetailResponse.run`).

### Request

```jsonc
POST /api/runs
Content-Type: application/json

{ "host_id": "ts-de-ber-zeus" }
```

### Response (200 OK)

```jsonc
{
  "host_id":      "ts-de-ber-zeus",
  "started_at":   "2026-05-11T14:02:08Z",
  "completed_at": "2026-05-11T14:02:13Z",
  "outcome":      "complete",
  "items":        [ /* DiagnosticItem[] */ ]
}
```

Identical shape to `HostDetailResponse.run`. The endpoint stays
exposed for the restored `RunResultPage` (which exists in v1 as a
fallback / power-user view; the unified host-detail page is the
primary surface).

### Server-side timeout

30 seconds (`Settings.run_timeout_seconds`, restored from pre-007).

### Persistence

Each successful run writes
`backend/.cache/vayobd/runs/<operator-slug>/<host-id>.json`. Same
location and shape pre-007 used.

---

## 3. `GET /api/runs/{run_id}`

Restored from HEAD; same shape as `POST /api/runs` response. Used by
the restored result page for direct-link sharing of a recorded run.

---

## What this contract intentionally omits

- **No new endpoint for the REECU one-shot capture.** The capture
  is internal to the unified collector — it doesn't have a public
  surface. If a future feature wants to expose it (e.g., for
  the live page to consume), that's its own contract.
- **No streaming / SSE for the host-detail page.** The unified
  response is read-on-demand; the page is not a live surface.
  (Live Diagnostic at `/live` is the streaming surface; it has its
  own WebSocket contract from 004.)
- **No batch endpoint.** Same as 007 — one host per request.
- **No "list recent runs" endpoint.** The persisted run records
  exist for future use; 008 does not add a list surface over them.
