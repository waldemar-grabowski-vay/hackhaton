# REECU Pipeline Contract — One-shot capture for the host-detail page

**Owner**: `backend/src/vayobd/api/host_versions.py` (new thin wrapper);
underpinned by `backend/src/vayobd/live/session.py` (existing).
**Phase**: 008 — implements 2026-05-11 Clarification Q1 + Q4; extended
2026-05-12 for VE-host capture (Q1 of the 2026-05-12 round).

This file specifies the contract between the host-detail collector
and the Live Diagnostic code path that supplies REECU values.

---

## 1. Entry point

```python
async def capture_reecu_state(
    host_id: str,
    settings: Settings,
    *,
    window_seconds: float = 4.0,
) -> ReecuCaptureResult:
    """One-shot SSH+candump session against `host_id`, ~window_seconds of
    frames, decoded via the configured TS DBC.

    Returns a ReecuCaptureResult that the unified collector merges into
    `HostDetailResponse.versions` (vREECU + SEC) and may also emit as
    additional `DiagnosticItem` rows for SEC state / ERRQ-decoded errors.
    """
```

Lives in a new module — proposed path
`backend/src/vayobd/api/_reecu_capture.py` — to keep `host_versions.py`
tightly scoped. The module is internal (`_` prefix); only the unified
collector imports it.

---

## 2. Capture window

**4.0 seconds wall-clock**, fixed. Rationale in `research.md` § 3:

- Catches at least 3 firmware-version broadcast cycles (1 Hz) and
  ~40 ERRQ frames per channel (10 Hz).
- Stays inside the 10 s SC-002 budget with headroom for SSH setup
  + teardown + transit.

If the SSH session can't open within `window_seconds`, the result
is `ReecuCaptureResult(status="unreachable")` with a plain-language
reason. The collector translates this to `vREECU.unavailable` and
`SEC.unavailable` on the version card.

---

## 3. `ReecuCaptureResult` shape

```python
@dataclass(frozen=True, slots=True)
class ReecuCaptureResult:
    status: Literal["ok", "empty", "unreachable", "decode_failed"]

    # Populated when status == "ok" (or "empty" — values may be None):
    aurix_version: tuple[int, int, int] | None  # (major, minor, patch)
    aurix_build_type: int | None                # 0/1/2 → R/D/T per engine convention
    sec_version: tuple[int, int, int] | None
    sec_build_type: int | None
    sec_state: tuple[str, ItemStatus] | None    # ("ARMED", WORKING) etc.

    # ERRQ-decoded errors (mapped against the local errq tool's model).
    # Empty list means "no errors active in the capture window."
    errq_errors: list[ErrqEntry]

    # Diagnostic context — never operator-facing; used in logs only.
    frames_seen: int
    elapsed_ms: int
    reason: str | None  # populated when status != "ok"
```

The `ItemStatus` for `sec_state` reuses the restored `ItemStatus`
enum from `models.py` (working / warning / error) — matches the
engine's `ts_sec_state` table.

---

## 4. SSH and `candump` invocation

Reuse `vayobd.live.session.LiveSession` exactly as the
`/live` page uses it. The new wrapper:

1. Resolves the host's ssh target via the inventory loader (same
   path 004 already uses).
2. Constructs a `LiveSession` configured for a **bounded** lifetime:
   - Subprocess command: `candump -t a -L can0`
     (same as the streaming surface).
   - Output filter: stop processing after `window_seconds`.
3. Wires the session's decoded-frame callback into an in-memory
   accumulator that retains the latest value per relevant signal.
4. Closes the session after `window_seconds`, harvests the
   accumulator, builds the `ReecuCaptureResult`.

**Concurrency**: the host-detail capture is independent of any open
`/live` session — 004 FR-019 already specifies "each session
independent." The capture spawns its own SSH process.

**Error paths**:

| LiveSession failure mode | ReecuCaptureResult.status |
|---|---|
| SSH cannot reach host | `"unreachable"` |
| SSH connects but `candump` exits non-zero | `"decode_failed"` |
| Capture window elapses with zero frames decoded | `"empty"` |
| DBC fails to load (degraded errq path from 004) | `"decode_failed"` |
| Unhandled exception in the session | `"unreachable"` |

In every non-ok case the collector marks `vREECU` and `SEC` as
`VersionField(verdict=UNAVAILABLE)` with a plain-language reason
sourced from `result.reason`.

---

## 5. Signal extraction (when status == "ok")

The DBC the session loads is the TS application protocol DBC (per
research § 1b — glob pattern tightening makes this reliable).
Relevant signals — names match the existing 004 / engine
conventions:

| Field on host-detail page | Signal in TS DBC |
|---|---|
| Aurix major / minor / patch | `TS_FW_VERSION_MAJOR` / `TS_FW_VERSION_MINOR` / `TS_FW_VERSION_PATCH` |
| Aurix build type | `TS_FW_BUILD_TYPE` |
| SEC (Gateway) major / minor / patch | `TS_GW_VERSION_MAJOR` / `TS_GW_VERSION_MINOR` / `TS_GW_VERSION_PATCH` |
| SEC build type | `TS_GW_BUILD_TYPE` |
| SEC state | `TS_SEC_STATE` (decoded via `ts_sec_state` table) |
| ERRQ buffers | `ERRQ_Byte01` … `ERRQ_Byte64` per channel — same aggregation 004 already does |

If a signal is missing from the DBC, that field comes back `None`
and the collector marks the corresponding cell `unavailable`.

Manifest cross-check uses the same engine helpers 007 already
relies on (`vayobd.live.manifest`-equivalent path or the restored
`vayobd.checks.ree_cli` helpers — implementation choice for tasks).
The verdict mapping (match / drift / no-manifest) matches 007's
`parse_engine_report` rules so a row that looks the same on the
page resolves to the same verdict regardless of which pipeline
produced it.

---

## 6. ERRQ → `ItemStatus` mapping

The ERRQ-decoded errors land as ITEMS on the host-detail page, not
just as version values. Each ERRQ entry becomes:

```python
DiagnosticItem(
    id=f"errq_{error.symbol.lower()}",
    name_key=f"item.errq.{error.symbol}.name",  # falls back to literal symbol if missing
    category=CheckCategory.SOFTWARE,
    status=_map_errq_severity(error.severity),  # info/warn → WARNING; error/critical → ERROR
    recommended_action_key=…  # from the errq model when registered
)
```

These items are added to `HostDetailResponse.run.items` alongside
the non-REECU items but tagged so the renderer can group them
under a dedicated "REECU errors" sub-section if desired. The
mapping rule is recorded in `research.md` § 1c.

---

## 7. TTL cache behaviour

The REECU capture's output is part of the unified
`HostDetailResponse` and shares the 60-second per-host TTL with
the non-REECU pipeline. Within the TTL window:

- Re-mount → cache hit → no capture spawned, no SSH session.
- `?fresh=true` → cache invalidate → new capture (and new
  `ree-debug-cli report`) in parallel.

This bounds the testbed load to ~one capture per host per minute
of operator activity.

---

## 8. Observability

Log events the new module emits:

| Event | Level | Fields |
|---|---|---|
| `reecu_capture.start` | info | `host_id`, `window_seconds` |
| `reecu_capture.frames_seen` | info | `host_id`, `frames_seen` (after window) |
| `reecu_capture.ok` | info | `host_id`, `aurix=…`, `sec=…`, `errq_count`, `elapsed_ms` |
| `reecu_capture.empty` | warning | `host_id`, `elapsed_ms` |
| `reecu_capture.unreachable` | warning | `host_id`, `reason` |
| `reecu_capture.decode_failed` | warning | `host_id`, `reason` |

Same FR-015 stricture as 007: never log raw SSH stderr, never log
agent socket paths or key material.

---

## 8a. Host-type behaviour (2026-05-12)

The capture function takes `host_type: HostType` (or reads it from
the `Host` object passed in). The `host_type` parameter has two
effects, both confined to the post-decode field-extraction step;
the SSH + candump + DBC-decode pipeline is **unchanged**:

1. **Signal allowlist passed to the decoder**: TS hosts get the
   pre-008 allowlist (`TS_FW_VERSION_*`, `TS_GW_VERSION_*`,
   `TS_SEC_STATE`, plus the existing TS state-panel allowlist).
   VE hosts get the TS allowlist **plus** the VE signals Wilhelm's
   desktop tool surfaces (`VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`,
   `VE_PRND_STATE`, and any further `VE_*` in
   `TS_diagnostic_tool/config.py::TS_STATE_SIGNALS`). See
   `contracts/ve-signals.md` for the source-list grep at task time.
2. **errq CSV resolver**: TS hosts read from the existing TS subpath
   inside the local `ree-reecu` clone; VE hosts read from the VE
   subpath (preliminary
   `{ree_reecu_root}/ve/6_tools/VE_Generators/Errq/ve_errq_cfg_generator/csv/`).
   Concrete path is a `/speckit-tasks` lookup against the actual
   clone. See `contracts/ve-errq.md`.

Both effects are pass-throughs on the *existing* one-shot capture
flow. No new transport, no new code path, no new contract surface.
The capture window (4 s) and signal extraction strategy stay the
same.

## 9. What this contract intentionally omits

- **No streaming output to the SPA.** The capture is one-shot;
  what the SPA sees is the final `HostDetailResponse`. The
  streaming surface is `/live`, governed by 004's WebSocket
  contract.
- **No persistence of capture results.** The cache is in-memory
  per process; capture results aren't written to disk. (The
  `runs.py` persistence path writes the full `DiagnosticRun` —
  which includes the REECU-derived items — to the operator-slug
  directory; that's the existing persistence story.)
- **No retry logic on capture failure.** A failed capture surfaces
  as `unavailable` cells; the operator's recovery is to click the
  refresh button (FR-018). No backoff / retry inside the capture
  function itself.
