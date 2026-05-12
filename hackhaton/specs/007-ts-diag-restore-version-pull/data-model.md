# Phase 1 Data Model — Restore TS_diag entry, host-side version pull

**Date**: 2026-05-11
**Status**: complete

This file captures the shape of every domain object this feature
touches — both the wire shape (API responses) and the internal types
(cache entries, engine parse results). Pydantic models are the
in-Python source of truth; the equivalent Zod schemas in
`frontend/src/api/hostVersions.ts` mirror these shapes 1:1.

---

## 1. `VersionVerdict` (enum)

```python
class VersionVerdict(str, Enum):
    MATCH        = "match"          # live value matches manifest
    DRIFT        = "drift"          # live value present, manifest disagrees
    NO_MANIFEST  = "no-manifest"    # live value present, no manifest available
    UNAVAILABLE  = "unavailable"    # this field could not be read on this host
```

**Source of truth for the four values**: clarification Q2 (per-field
availability) + the spec's FR-005. Frontend uses the same string
literals — no remapping in the SPA.

---

## 2. `VersionField` (per-field record)

The new per-field wire shape introduced by Clarification Q2. One of
these per version (vDrive, vREECU, SEC).

```python
class VersionField(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    value: str | None = Field(
        default=None,
        description=(
            "The live version string read from the host (e.g. 'R12.3.0', "
            "'2025.04-rc3'). None when verdict is 'unavailable'."
        ),
    )
    verdict: VersionVerdict = Field(
        description="Comparison outcome of `value` against the manifest expectation.",
    )
    expected: str | None = Field(
        default=None,
        description=(
            "Manifest's expected value when verdict is 'drift'. None otherwise. "
            "Used by the page to render actual vs expected side-by-side (FR-006)."
        ),
    )
    reason: str | None = Field(
        default=None,
        description=(
            "Plain-language explanation when verdict is 'unavailable' "
            "(e.g. \"couldn't reach <host> over SSH\", "
            "\"SEC package not installed on this host\"). "
            "None for non-unavailable verdicts."
        ),
    )
    as_of: datetime = Field(
        description=(
            "Timestamp this field's value was read from the host. Drives the "
            "per-cell 'as of <time>' label (FR-019). For cached responses, "
            "this is the original read time, not the serve time."
        ),
    )
```

**Invariants** (enforced in `host_versions.py` model-validator):

- `verdict == MATCH` → `value` non-null, `expected` null, `reason` null
- `verdict == DRIFT` → `value` non-null, `expected` non-null, `reason` null
- `verdict == NO_MANIFEST` → `value` non-null, `expected` null, `reason` null
- `verdict == UNAVAILABLE` → `value` null, `expected` null, `reason` non-null

Violation of these invariants is a backend bug, not a runtime error —
unit tests must cover all four shapes.

---

## 3. `HostVersions` (envelope of the three fields)

```python
class HostVersions(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    vdrive_manifest: VersionField
    vreecu_version:  VersionField
    sec_version:     VersionField
```

Fields are always present in the response (no `Optional[VersionField]`);
absence of data is encoded as `verdict == UNAVAILABLE`.

---

## 4. `HostVersionsResponse` (top-level wire shape)

```python
class HostVersionsResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    host: Host                      # existing inventory model, unchanged
    versions: HostVersions          # per-field state (above)
    source: Literal["live", "unavailable"]
```

The `source` literal is derived from the three field verdicts at
response-build time:

- `"live"` if at least one field's verdict is `match`, `drift`, or
  `no-manifest`
- `"unavailable"` only if all three fields have verdict `unavailable`

The previous `"placeholder"` value is removed — see spec FR-004 / SC-004
(no placeholder code path in production).

---

## 5. `CacheEntry` (internal — not on the wire)

```python
@dataclass(frozen=True, slots=True)
class CacheEntry:
    cached_at: datetime
    response: HostVersionsResponse
```

Lives in `backend/src/vayobd/_internal/version_cache.py` (see
research §2). Not exposed to any other module.

---

## 6. State transitions

The four post-load steady states for a `VersionField` are mutually
exclusive — no in-place transitions between them within a single
response. A subsequent fetch (either TTL expiry or refresh button)
yields a new `VersionField` instance with whatever verdict the engine
produces at that moment.

```text
                  ┌──── engine row matches manifest ─→ MATCH
                  │
   engine call ───┼──── engine row reports drift     ─→ DRIFT
                  │
                  ├──── engine has no manifest entry ─→ NO_MANIFEST
                  │
                  └──── engine row missing or Fail   ─→ UNAVAILABLE
```

In-flight (UI-only) state — `loading` — is not part of the response
contract; the frontend models it as the absence of any
`HostVersionsResponse` for the current `(host_id, fresh)` query key
(React Query's `isLoading`).

---

## 7. Settings delta

No new entries in `Settings`. The existing `engine_binary_path` setting
(used by the engine-mode detector in `dependencies.py`) is reused.
The 60 s TTL is a module-level constant in `version_cache.py`; not
operator-configurable in v1 (Principle I — no configuration knob
without a concrete need).

---

## 8. Persistence

None. The cache is per-process in memory; restarting the backend
clears it. This matches the single-user desktop deployment model and
the spec's framing ("repeat visits within the TTL" — there is no
expectation of cross-restart persistence).

---

## 9. Compatibility with prior wire shape

The shipping `HostVersionsResponse` (post-006 pivot, before this
feature) has:

```json
{
  "host": { ... },
  "versions": {
    "vdrive_manifest": null,
    "vreecu_version":  null,
    "sec_version":     null
  },
  "source": "placeholder"
}
```

The new shape is a **breaking change** at the JSON level: each of the
three version fields becomes an object instead of a `str | null`. The
SPA's Zod schema is updated in the same PR; there is no third-party
consumer of this endpoint (loopback-only single-user app), so
versioning the endpoint is unnecessary. The `source` enum drops
`"placeholder"`.

---

## 10. Engine fixture used in tests

A small JSON fixture captured from a real engine run (TS host) goes
under `backend/tests/fixtures/engine_reports/ts_host_full.json` and
covers every verdict at least once:

- vDrive: drift (e.g. live `R12.3.0`, manifest expects `R12.4.0`)
- vREECU: match
- SEC: unavailable (`status: Fail`, `raw_detail: ssh error: ...`)

The integration test loads this fixture as the engine subprocess
stdout and asserts the resulting `HostVersionsResponse` against the
expected shape — locks in the engine-name-match parser as a
regression net against engine wording changes.
