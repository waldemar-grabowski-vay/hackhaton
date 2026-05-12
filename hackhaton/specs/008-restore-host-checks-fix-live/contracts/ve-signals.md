# VE State-Signal Port Contract

**Owner**: `backend/src/vayobd/live/candump_runner.py` (allowlist),
`frontend/src/pages/LiveDiagnosticPage.tsx` (state panel render).
**Phase**: 008 — implements 2026-05-12 clarification Q1.

## Goal

Port the VE-channel state signals Wilhelm's desktop tool
(`TS_diagnostic_tool/config.py::TS_STATE_SIGNALS`) surfaces onto the
hackhaton web app's `/live` state panel, so a Live Diagnostic
session against a vehicle host shows VE-side state alongside the
TS-side state it already shows.

## Source list (verbatim from Wilhelm)

The grep at task time MUST be:

```bash
grep -E '"VE_' /home/waldemar-grabowski/GitHub/hackhathon/TS_diagnostic_tool/config.py
```

Confirmed at plan time:

```python
"VE_ChA_SSMAN_State",
"VE_ChB_SSMAN_State",
"VE_PRND_STATE",
```

If the grep returns additional `VE_*` entries by task time, they are
added too (Wilhelm may extend the list in future). The allowlist is
"the union of Wilhelm's TS-side + VE-side `TS_STATE_SIGNALS`".

## Decode pipeline

The decoder is **unchanged**:

```text
SSH → candump -tz -L <iface> → cantools.decode(...) against TS APP DBC
  → DecodedFrame{signals: dict[str, value]}
  → filter signals by state-signal allowlist
  → push to WebSocket → state panel render
```

The TS APP DBC carries both TS_* and VE_* signal definitions
(verified against Wilhelm's `config.py::DBC_GLOB_PATTERNS` —
`**/TS_APP*.dbc`). No new DBC is loaded; no new transport.

## Host-type behaviour

The web app's inventory loader already tags `ve-*` IDs as
`HostType.VEHICLE`. The allowlist is **not** filtered by host type:

- On a TS host, the bus broadcasts `TS_*` signals; `VE_*` allowlist
  entries match nothing; they don't appear in the panel.
- On a VE host, the bus broadcasts `VE_*` signals; `TS_*` allowlist
  entries match nothing; they don't appear in the panel.

Naturally falls through on data. No host-type-gated render code.

## Acceptance contract

| ID | When | Then |
|---|---|---|
| VE-SIG-1 | Connect to a reachable VE host on `/live` | Within 10 s, the state panel renders `VE_ChA_SSMAN_State`, `VE_ChB_SSMAN_State`, `VE_PRND_STATE`, with decoded values from the bus. |
| VE-SIG-2 | Connect to a reachable TS host on `/live` (regression check) | Within 10 s, the state panel renders the existing TS state signals; **none** of the `VE_*` entries appear in the panel. |
| VE-SIG-3 | The TS APP DBC is missing or stale | The state panel surfaces the 004 FR-012 degraded-mode message; raw frames log keeps streaming. Applies identically to TS and VE hosts. |
| VE-SIG-4 | A `VE_*` signal name in the allowlist isn't defined in the DBC | The signal is silently absent from the panel (it's just not decoded). No error; logged at backend `WARN` once on session start. |

## Out of scope (per Q1 of the 2026-05-12 clarifications)

The following are explicitly deferred to a follow-up spec — **not**
008:

- Per-channel ERRQ aggregation (`errq_aggregator.py` in Wilhelm's tool).
- Multi-bus auto-detect (one candump per UP `can*` interface).
- Error severity grouping (`IMMEDIATE_PULLOVER / SAFETY / TS_BRAKES /
  TS_STEERING / ERROR_GROUP / TS_THROTTLE`).
