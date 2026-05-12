# HTTP API Contract — `GET /api/host/{host_id}/versions`

**Owner**: `backend/src/vayobd/api/host_versions.py`
**Phase**: 007 — replaces the placeholder body that returns
`source: "placeholder"` with a real engine-shellout flow.

This file specifies the wire shape, query parameters, status codes,
and caching semantics for the host-detail version endpoint after
this feature lands. Mirrors `data-model.md` for the response body.

---

## Endpoint

```
GET /api/host/{host_id}/versions
GET /api/host/{host_id}/versions?fresh=true
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `host_id` | path | yes | Inventory `host_id` (e.g. `ts-de-ber-00005`). Resolved via the existing inventory loader (`load_inventory(settings.inventory_path)`). |
| `fresh` | query | no | `true` → invalidate the per-host TTL cache before the engine call, force a fresh engine invocation. Default `false`. Any other value MUST be rejected as 400 (avoids ambiguous `?fresh=1`). |

**Auth**: `Depends(current_operator)` — same shim every other route uses.

---

## Successful responses (200 OK)

```jsonc
{
  "host": {
    "id": "ts-de-ber-00005",
    "country": "de",
    "type": "telestation",
    "city": "berlin"
    // ... rest of existing Host shape
  },
  "versions": {
    "vdrive_manifest": {
      "value": "R12.3.0",
      "verdict": "drift",
      "expected": "R12.4.0",
      "reason": null,
      "as_of": "2026-05-11T14:02:11Z"
    },
    "vreecu_version": {
      "value": "8.5.3",
      "verdict": "match",
      "expected": null,
      "reason": null,
      "as_of": "2026-05-11T14:02:11Z"
    },
    "sec_version": {
      "value": null,
      "verdict": "unavailable",
      "expected": null,
      "reason": "SEC package not installed on this host",
      "as_of": "2026-05-11T14:02:11Z"
    }
  },
  "source": "live"
}
```

Three fields are always present. Each carries the `VersionField`
shape from `data-model.md` § 2. The `source` literal summarises the
three field verdicts (see `data-model.md` § 4).

A "no host reachable" response — all three fields `unavailable` —
still returns 200 OK with `source: "unavailable"`. The page renders
the failure inline; the SPA does not error-boundary on this case.

---

## Error responses

| HTTP | Body shape | When |
|---|---|---|
| 400 | `{"detail":{"error":"bad_query","message_key":"host_versions.bad_query"}}` | `?fresh` present with a non-`true` value |
| 401 | (existing auth shim payload) | No / invalid operator header |
| 404 | `{"detail":{"error":"host_not_found","message_key":"host.not_found"}}` | `host_id` not in current inventory |
| 503 | `{"detail":{"error":"inventory_unavailable","message_key":"inventory.empty.body"}}` | Inventory file missing or unparseable at request time |

Never 5xx for engine failures — those become `source: "unavailable"`
in the 200 body (FR-014).

---

## Caching semantics

- **Server-side**: per-host in-memory TTL cache, 60 s (FR-017,
  research §2). First request for a host triggers the engine; subsequent
  requests within 60 s serve the cached `HostVersionsResponse` verbatim.
  Across the TTL boundary, the next request transparently re-spawns the
  engine and updates the cache atomically.
- **`?fresh=true`**: invalidates the cache entry for `host_id`
  immediately before the engine call. Other hosts' cache entries are
  untouched (per-host invalidation).
- **Concurrent requests for the same cold host**: the second request
  blocks on the first's engine call, then serves the same cached
  response. Cache lock is `threading.Lock`; the engine invocation
  itself runs in a thread pool executor so the event loop stays
  responsive.
- **HTTP cache headers**: no `Cache-Control` / `ETag` set by this
  feature. The cache is server-internal; the SPA owns its own
  React Query cache (also keyed by `(host_id, fresh)`).

---

## Engine invocation

The handler shells out to:

```
<engine_binary> report --host <host_id> --inventory <ree-vehicle-configs-clone> --json
```

`<engine_binary>` is resolved from `Settings.engine_binary_path`
(falling back to `ree-debug-cli` on `$PATH`, research §7).
`<ree-vehicle-configs-clone>` is resolved from
`Settings.inventory_path.parent.parent.parent` (climb back up from
`org/vay/inventory.yaml` to the clone root), reusing the convention
already in place elsewhere in the backend.

Engine stdout is parsed as `EngineReport` JSON; the
`checks: list[CheckEntry]` array is mapped to the three version
fields via the rules in `contracts/engine-mapping.md`. Engine stderr
(when non-zero exit) is reduced to a one-line reason per failed
field via the table in `research.md` § 4.

Engine invocation is bounded by a hard 15 s wall clock (matches
SC-002's 10 s budget plus headroom). A timeout collapses every
field to `verdict: "unavailable"` with `reason: "engine timed out
reading versions for this host"`.

---

## Observability

| Log event | Level | Fields |
|---|---|---|
| `host_versions.engine_invoke` | info | `host_id`, `fresh`, `cache_hit` |
| `host_versions.engine_done` | info | `host_id`, `exit_code`, `duration_ms`, count of fields each verdict |
| `host_versions.engine_timeout` | warning | `host_id`, `duration_ms` |
| `host_versions.engine_parse_error` | warning | `host_id`, summary of unparseable line (no raw stderr — FR-015) |

No SSH credential material or agent socket paths appear in any log
line (FR-015 — mirrors 004's FR-021). The engine's structured stderr
is treated as engineering-only and reduced to the table in
research §4 before any operator surface or log emit.

---

## What this contract intentionally omits

- **No POST refresh endpoint.** `?fresh=true` on the GET is the
  refresh path. Research §6 has the rationale.
- **No streaming / SSE.** Versions read in a single round-trip; the
  in-flight UX is owned by the SPA's React Query loading state
  (FR-020), not by transport.
- **No batch endpoint.** One host per request; the page only displays
  one host at a time. Adding a `/hosts/versions?ids=...` plural is a
  future feature if a list-overview surface needs it.
- **No webhook / push.** Versions change only when an engineer
  deploys a package; no value in real-time push for a read-on-demand
  operator surface.
