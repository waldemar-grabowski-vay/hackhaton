# Phase 0 Research — Restore TS_diag entry, host-side version pull, drop API check battery, readability tweaks

**Date**: 2026-05-11
**Status**: complete — all NEEDS CLARIFICATION resolved (spec clarification round 2026-05-11 + this document)

This file resolves the four implementation-direction questions that the
spec's clarification round didn't have to answer because they are
plan-level rather than spec-level. Each section has one decision, the
rationale, and the alternatives considered.

---

## 1. Engine-output mapping — which `CheckEntry` rows feed which version field?

**Decision**: Map the engine report's per-host `checks: Vec<CheckEntry>` to the three
version fields by **name match** against a small hard-coded table inside
`backend/src/vayobd/api/host_versions.py`. The mapping table is:

| Spec field | Engine CheckEntry `name` (substring match) | Notes |
|---|---|---|
| `vdrive_manifest` | `vDrive package vs manifest` | Produced by `vdrive_release_drift_check` (`engine/ree-debug-engine/src/checks/reecu.rs:1191`). One row per host kind (TS / VE); the engine emits the kind-appropriate one. |
| `vreecu_version` | `Aurix firmware` (or whatever the engine names the REECU firmware row) | Produced by the `compose_version_summary` path with `m.reecu_ts` / `m.reecu_ve` as the manifest expectation (`engine/ree-debug-engine/src/checks/reecu.rs:758-760, 1020-1023`). |
| `sec_version` | `SEC version` | Produced by the same `compose_version_summary` path with `m.sec_ts` / `m.sec_ve` (`engine/ree-debug-engine/src/checks/reecu.rs:761-763, 1023-1025`). |

The verdict mapping is derived from `CheckEntry.status` plus the
free-form `name` text the engine already emits:

| Engine signal | Spec verdict | Detection |
|---|---|---|
| `status: Pass` and name ends with `(matches manifest)` | `match` | substring `matches manifest` present in `name` |
| `status: Warn` and name contains `manifest expects` or `≠ manifest` | `drift` | substring `manifest expects` OR `≠ manifest` present |
| `status: Warn` and name contains `no manifest available` | `no-manifest` | substring `no manifest available` |
| `status: Fail`, or the row is missing entirely from the engine report | `unavailable` | either condition |

The actual displayed version string is the **substring of `CheckEntry.name`
before the parenthesised tail** (e.g., `R12.3.0 (matches manifest)` →
display `R12.3.0`). When `verdict = drift`, the engine's `name` already
carries `manifest expects <X>` — the backend extracts `<X>` and exposes
it as the expected-value sibling field per spec FR-006.

**Rationale**: The engine is the source of truth for the comparison
logic; replicating its verdict rules in Python would be a guaranteed-
divergence trap. By string-matching the engine's already-emitted summary
text, the backend stays a thin adapter and any future engine-side
tightening of the comparison flows through transparently. Name-match is
fragile to engine wording changes; we accept that fragility because the
engine repo is in-monorepo and any rename will be caught by the
integration test (`backend/tests/integration/test_host_versions_endpoint.py`)
which asserts at least one of each verdict against a recorded engine
fixture.

**Alternatives considered**:

- *Have the engine emit a structured `versions` block alongside `checks`.*
  Cleanest API but requires an engine-side change (and a rust release),
  violating Clarification Q1's "no rust changes." Defer to a follow-up
  if name-matching causes drift in practice.
- *Re-implement the comparison in Python by reading
  `release-configs.yaml` directly.* Duplicates engine logic in two
  languages, exactly the trap above. Rejected.
- *Run a dedicated `--versions-only` engine flag.* No such flag exists
  today (`engine/ree-debug-cli/src/main.rs` only declares `Report`).
  Adding one is an engine change; rejected for the same reason.

**Open issue tracked under contracts/engine-mapping.md**: if the engine
report does not include a `name` containing `SEC version` for VE hosts
(SEC is TS-specific in current code), the backend MUST treat the field
as `unavailable` for VE hosts and surface "SEC version not applicable
to vehicle hosts" rather than as a generic error. Confirm against the
engine's actual VE planned-row list in T-impl time.

---

## 2. TTL cache implementation choice

**Decision**: Single-process in-memory cache, structured as
`dict[str, CacheEntry]` keyed by `host_id`, guarded by a
`threading.Lock`, with a fixed 60 s TTL. Refresh-button path bypasses
the cache by writing `cache.invalidate(host_id)` immediately before the
engine call.

```python
# Sketch — actual home: backend/src/vayobd/_internal/version_cache.py
@dataclass(frozen=True, slots=True)
class CacheEntry:
    cached_at: datetime
    response: HostVersionsResponse  # The Pydantic model the endpoint returns

class VersionCache:
    def __init__(self, ttl_seconds: int = 60) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._store: dict[str, CacheEntry] = {}
        self._lock = threading.Lock()

    def get(self, host_id: str, now: datetime) -> HostVersionsResponse | None:
        with self._lock:
            entry = self._store.get(host_id)
            if entry is None or (now - entry.cached_at) >= self._ttl:
                return None
            return entry.response

    def set(self, host_id: str, response: HostVersionsResponse, now: datetime) -> None:
        with self._lock:
            self._store[host_id] = CacheEntry(cached_at=now, response=response)

    def invalidate(self, host_id: str) -> None:
        with self._lock:
            self._store.pop(host_id, None)
```

**Rationale**: The deployment model is single-user single-process
(loopback uvicorn on the operator's laptop). A shared cache layer
(Redis, lru-cache decorator, etc.) is overkill; FastAPI dependency-
injection sugar would make the surface harder to test without giving
us cross-process semantics we don't need. Forty lines of plain Python
matches Principle I exactly. The same shape is already in use in
`backend/src/vayobd/api/refresh.py` for the refresh-state singleton.

**Alternatives considered**:

- *`functools.lru_cache` with manual TTL bookkeeping.* Awkward fit:
  `lru_cache` doesn't expose entry timestamps, so TTL checks would
  require a wrapper of comparable size to the explicit class.
- *Per-request cache (no shared state).* Doesn't satisfy SC-007's
  sub-500 ms re-visit budget.
- *Redis / memcached.* Wildly over-engineered for one user, one
  process; introduces a new dependency for the .deb to ship.

**TTL value (60 s)**: matches Clarification Q3's "short" framing.
Operators bouncing between hosts during a debug session feel instant
re-visit (≤ 60 s round-trips); a fresh deploy on the host is reflected
within at most one TTL window without manual intervention. The explicit
refresh button (FR-018) is the operator's escape hatch when 60 s is
too long.

---

## 3. Developer-mode UI gate — why the entry point is invisible today

**Decision**: The frontend `LiveDiagnosticButton` (and any new copy in
`PickerPage`) MUST read from the **frontend's local Developer-mode
store** (`useDeveloperMode` in `frontend/src/lib/developerMode.ts`,
backed by `localStorage`) — not from `/api/health.live_diagnostic.enabled`
as it does today. The server-side health flag is repurposed as a
**capability probe** (does the backend have errq/DBC loaded? is the
live diagnostic surface buildable at all?) but is not the authoritative
toggle for the entry-point button.

The decoupling stems from a real bug discovered while writing this
plan: the `useDeveloperMode` UI switch (`AppHeader.tsx` line ~52)
writes to `localStorage`, but never tells the backend. Backend
`settings.developer_mode` is sourced from env / settings.toml at
startup and is the sole input to `/api/health.live_diagnostic.enabled`
(see `backend/src/vayobd/app.py:170-171`). The current
`LiveDiagnosticButton` polls `/api/health` and gates on that flag —
which is permanently `false` unless the operator manually sets
`VAYOBD_DEVELOPER_MODE=1` in the environment (or edits
`~/.config/vayobd/settings.toml`). Flipping the UI switch does
nothing. The operator who reported "TS_diag got removed" was almost
certainly looking at this dead toggle.

The fix is one-directional: trust the UI toggle. The button checks
`useDeveloperMode((s) => s.enabled)` first and only consults
`/api/health` for the secondary readiness signal (errq loaded? DBC
loaded?) used by the /live surface itself.

**Rationale**: The whole point of the in-UI Developer mode toggle (
introduced in 002 US2) is to give the operator a one-click reveal/
hide. Routing that through the backend would require either a
mutating endpoint to write `settings.developer_mode` (security
review territory — see Principle I) or a session-cookie scheme
(over-engineered for a single-user desktop app). Treating the UI
toggle as the source of truth restores the originally-shipped 002 UX.

The server-side flag remains useful as a backend-managed capability
hint: if errq or DBC files are missing on the operator's machine,
`/api/health` still reports that, and the /live surface can degrade
accordingly (FR-012 in 004's spec) — but the entry-point's visibility
is no longer hostage to whether the user remembered to set an env
var.

**Alternatives considered**:

- *Add a `POST /api/dev-mode` to let the UI write the backend
  setting.* Mutating endpoint, new auth surface, persistence question.
  Rejects Principle I. Skip.
- *Read settings.toml on every page render via a polled health
  endpoint.* Already what we're doing; doesn't help because nothing
  writes to settings.toml from the UI.
- *Remove Developer mode entirely and always show TS_diag.*
  Possible follow-up but explicitly out of scope for 007 — the spec
  preserves 004's gating intent.

**Backwards-compat note**: Operators who already set
`VAYOBD_DEVELOPER_MODE=1` continue to see the entry point because
the localStorage default (false on a fresh browser) is overridden by
their own toggle action. No setting migration required.

---

## 4. Per-field reason copy — sourcing the one-liner

**Decision**: The backend produces the per-field `reason` string for
the `unavailable` verdict by applying a small mapping over the
engine's `CheckEntry.raw_detail` (when present) or `CheckEntry.name`
(when `raw_detail` is None). The mapping is:

| Engine signal | Operator-facing reason |
|---|---|
| `ssh error: <stderr>` (engine row `status: Fail`) | "couldn't reach `<host>` over SSH" |
| `dpkg failed (exit ?)` | "package query failed on the host" |
| `<pkg> not installed` (vDrive row) | "vDrive package not installed on this host" |
| Row missing entirely from the engine report | "host didn't report this version" |
| Any other Fail with non-empty `raw_detail` | "engine couldn't read this — see logs" |

When a `drift` verdict is reported, the spec wants both the actual and
the expected manifest version (FR-006). The expected value is extracted
from `CheckEntry.name` by parsing the parenthesised tail
(`R12.3.0 (manifest expects R12.4.0)` → expected `R12.4.0`).

The frontend never composes operator-facing text from raw engine output
on its own — that contract is owned by the backend so all plain-language
copy is in one place (`backend/src/vayobd/api/host_versions.py`) and
i18n / wording reviews land in a single PR.

**Rationale**: Centralising the copy in Python avoids the trap where
the frontend forms strings the backend should own (Principle III's
plain-language requirement applies wherever the copy is composed).
A small dictionary is easier to review than a templated copy file.

**Alternatives considered**:

- *Pass the engine's raw `raw_detail` through to the frontend
  untouched.* Violates spec FR-007 ("one-line plain-language reason
  per field"). Engine output is engineering-internal.
- *Move the copy into a dedicated `strings.py`.* Possibly worth doing
  when there's a second consumer; today there isn't, and Principle I
  defers it.

---

## 5. Frontend file dedup (`hostVersions.ts` vs `host-versions.ts`)

**Decision**: Keep `frontend/src/api/hostVersions.ts` (camelCase) as
the canonical module; delete `frontend/src/api/host-versions.ts`. All
imports across the codebase MUST converge on the camelCase path.

**Rationale**: Both files exist in the current working tree (one a
near-duplicate of the other — see `git status` and the `grep` audit
in the spec-writing session). The convention elsewhere in the SPA is
camelCase filenames for hooks / typed client modules
(`useInventory.ts`, `useLiveSession.ts`); the kebab-case
`host-versions.ts` is an outlier accidentally introduced during the
006 pivot. Picking the convention-matching one keeps the diff tiny
and the imports consistent.

**Alternatives considered**:

- *Keep both with one re-exporting from the other.* Adds indirection
  for no gain; violates Principle I.
- *Move both to a kebab-case convention.* Larger refactor, more
  files churned, more PR conflict risk against the 006 in-flight
  changes. Defer.

---

## 6. Refresh affordance — fresh-pull semantics on the host-detail endpoint

**Decision**: The host-detail page's refresh button calls the same
`GET /api/host/{id}/versions` endpoint with a `?fresh=true` query
parameter. The backend interprets `?fresh=true` as "invalidate the
cache for this host before the engine call." No separate `POST
/api/host/{id}/versions/refresh` endpoint is added.

**Rationale**: The endpoint already exists; adding a query parameter
is a smaller surface than a new route, keeps the wire shape identical
between cached and fresh responses, and means the frontend uses one
React Query key with `{ fresh: boolean }` parameters rather than two
client modules. Matches Principle I.

**Alternatives considered**:

- *Dedicated `POST /api/host/{id}/versions/refresh` returning the same
  body.* More REST-correct (POST is the right verb for "force this
  side effect"), but adds a route and a duplicated parse-and-render
  client path. The cache invalidation IS a side effect of "fetch with
  freshness" which idempotently re-pulls; the GET semantics still
  describe it accurately enough for our single-user desktop scope.
- *Client-side cache invalidation only (React Query's
  `queryClient.invalidateQueries`).* Doesn't bust the *server*-side
  TTL cache, so a refresh click would still serve cached data.
  Rejected.

---

## 7. Engine binary discovery

**Decision**: The backend invokes the engine at the path specified by
the existing `Settings.engine_binary_path` setting if set, otherwise
falls back to `ree-debug-cli` on `$PATH`. Both paths are already the
convention elsewhere in `backend/src/vayobd/dependencies.py` (engine
mode detection) — this feature reuses that resolver and does not add
its own.

**Rationale**: Reuse over re-invention. The 006 .deb work installs
the engine binary into a deterministic location and points
`engine_binary_path` at it; users running from source rely on `$PATH`.
This feature does neither layer — it just reads where the resolver
points.

**Alternatives considered**:

- *Hard-code the path.* Brittle and reintroduces a known footgun.
- *Add a new `host_versions_binary_path` setting.* Splits the
  configuration surface for no operator-visible benefit.

---

## Outstanding follow-ups (not blocking this feature)

- **Engine adding a `--versions-only` flag** would let the backend skip
  the broader check fan-out and shave latency for hosts where only
  versions are needed. Out of scope here per Clarification Q1; track
  separately if SC-002 latency turns out tight in practice.
- **Engine emitting a structured `versions` block** would replace
  this feature's name-match parser with a typed deserialiser. Same
  tracking note.
- **The Developer-mode UI store could push state to the backend** (with
  a properly scoped mutating endpoint) so that env vars and the UI
  toggle stay in sync. Lower priority than the bug-fix this feature
  ships.
- **Investigate whether VE hosts emit a SEC row at all** (planned-row
  list in `engine/ree-debug-engine/src/checks/reecu.rs`). If they
  don't, surface a non-applicable state rather than `unavailable`.
