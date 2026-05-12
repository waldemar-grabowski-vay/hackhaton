# VE errq CSV Subpath Contract

**Owner**: `backend/src/vayobd/live/errq_bridge.py` (or the local
equivalent — the port of Wilhelm's `errq_bridge.py`).
**Phase**: 008 — implements 2026-05-12 clarification Q2 + Q5.

## Goal

When the connected Live Diagnostic host is a vehicle, the errq panel
decodes VE-side error codes using VE-specific CSV files inside the
**same** `ree-reecu` clone the runtime already uses for TS errq.

## Resolution rule

```python
def errq_csv_root(ree_reecu_root: Path, host_type: HostType) -> Path:
    if host_type is HostType.VEHICLE:
        return ree_reecu_root / "ve" / "6_tools" / "VE_Generators" / \
               "Errq" / "ve_errq_cfg_generator" / "csv"
    return ree_reecu_root / "ts" / "6_tools" / "TS_Generators" / \
           "Errq" / "ts_errq_cfg_generator" / "csv"
```

**Preliminary path** (to be confirmed against the team's actual
`ree-reecu` clone at task time):

```
{ree_reecu_root}/ve/6_tools/VE_Generators/Errq/ve_errq_cfg_generator/csv/
```

The `/speckit-tasks` step includes a 1-minute verification:

```bash
find "$REE_REECU_ROOT/ve" -type d -name "*errq*" 2>/dev/null
```

The directory the grep returns is the authoritative subpath. If the
directory layout differs from the preliminary path, the resolver
constant is updated to match before task implementation.

## Fallback semantics

If the resolved directory does not exist, OR if any required CSV
within it is missing, the errq panel falls back to the **004
FR-012 degraded-mode message** — identical to the TS-side fallback:

> "errq data unavailable for this host"

Plus the recovery suggestion ("Refresh your `ree-reecu` clone or
contact the platform team"). Plain-language; matches the 005
no-jargon policy.

The rest of the Live Diagnostic surface (state panel, raw frames
log) MUST keep functioning — errq degraded mode does not block the
session.

## Required CSV files

The TS resolver currently reads (at minimum):

- `Error_Group_List.csv`
- `Error_Message_List.csv`
- the per-group CSVs referenced by `Error_Group_List.csv`

The VE resolver reads the analogous VE-prefixed CSVs (concrete file
names confirmed at task time against the actual VE subpath).

## `.deb` packaging — unchanged

The 006 `.deb` does **not** bundle either TS or VE errq CSVs. The
operator runs against a local `ree-reecu` clone. This contract
does not require any change to packaging.

## Acceptance contract

| ID | When | Then |
|---|---|---|
| VE-ERRQ-1 | Connect to a reachable VE host on `/live`, and the VE errq subpath exists in the local `ree-reecu` clone | The errq panel renders decoded VE-side errors as rows; severity / group label rendering matches the TS panel's pattern. |
| VE-ERRQ-2 | Connect to a reachable VE host, and the VE errq subpath is missing | The errq panel shows the 004 FR-012 degraded-mode message. Raw frames + state panel keep streaming. |
| VE-ERRQ-3 | Connect to a reachable TS host (regression check) | The errq panel renders TS-side errors exactly as before. The VE resolver is not invoked. |
| VE-ERRQ-4 | The `ree-reecu` clone is shallow / incomplete | Same degraded-mode fallback as `VE-ERRQ-2`. The session does not error or block. |

## Out of scope (per Q1 of the 2026-05-12 clarifications)

- Per-channel ERRQ aggregation (Wilhelm's `errq_aggregator.py`).
- Severity grouping (`IMMEDIATE_PULLOVER` / `SAFETY` / etc.).
- A `ree-reecu-ve` separate repo, or bundled CSVs in the `.deb`.
