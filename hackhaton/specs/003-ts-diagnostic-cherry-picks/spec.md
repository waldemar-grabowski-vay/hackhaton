# Feature Specification: Cherry-pick from TS_diagnostic_tool into the SPA

**Feature Branch**: `003-ts-diagnostic-cherry-picks` (TBD)
**Created**: 2026-05-07
**Status**: Scaffold — captures intent; not yet specified or planned.
**Input**: User directive 2026-05-07: "Take the TS DIAG TOOL and implement
in our system. I think it checks REECU in very good way and adds the login
capability. Take what's the best."

## Why this exists

`002-real-executor` ported `ree-debug-tui`'s engine library into the web
app and made the SPA → real testbed flow work end-to-end against
`ts-de-ber-00005`. In the same conversation we co-located
`TS_diagnostic_tool/` (the team's PyQt6 Windows desktop diagnostic tool)
at the repo root.

The desktop tool contains diagnostic IP the web app does not yet have:

1. **REECU error-queue (`errq`) parsing** — see `TS_diagnostic_tool/errq_*.py`.
   Aggregates `TS_Ch[AB]_ERRQ_Byte01..64` signals from streaming CAN
   frames, stitches them into 64-byte buffers per channel, decodes
   active error bits via `~/GitHub/ree-reecu/platform/tools/errq`'s
   model (~220 errors per host class). This is a meaningful diagnostic
   surface the SPA's current ree-debug-engine doesn't reach.
2. **Live CAN streaming + DBC decoding** — `ssh_can_reader.py` +
   `dbc_handler.py`. Streams `candump` over SSH, decodes via cantools
   against the team's DBCs.
3. **Connection dialog UX** — `connection_dialog.py`. Host / user /
   port / key path / passphrase / password input with validation;
   pops up automatically on auth failure.

The user wants these surfaced through the SPA so non-technical
operators benefit from the deeper diagnostic IP. This spec captures
the *intent*; the actual `/speckit-specify` clarifying pass + plan +
tasks haven't been done yet.

## Why deferred (not implemented in this commit)

Each of the three is multi-hour work that deserves its own clarify
session:

- **Errq parsing** depends on streaming CAN over SSH, decoding via
  cantools-equivalent in Rust (or via a Python sidecar), AND access to
  the `errq` tool's CSV-defined error model. Several open questions:
  one-shot probe vs. continuous monitoring? Run `errq` in-process or
  shell out to the user's `~/GitHub/ree-reecu/platform/tools/errq`?
  How to surface in the result view — one item per active error, or
  one rolled-up "REECU error queue" item with an expandable list?
- **Live CAN streaming** is a fundamentally different UX from
  one-shot probe runs (the existing FR-009 / FR-024 contract). It
  needs its own user-story design — Developer-mode-only? A separate
  "Live CAN" panel?
- **Connection dialog** depends on the SPA's settings flow (US2
  setup card from `002-real-executor`, T052+) which itself hasn't
  been implemented yet. Once the setup card lands, adding SSH
  credential fields is a small extension; today there's nowhere
  natural to put it.

## Suggested next-session shape

Use the speckit loop: `/speckit-specify` with this directive as the
input, then `/speckit-clarify` (probably 3 — 5 questions about probe
cadence, where the errq output lives in the result view, whether to
run errq in-process via cantools or shell out, …), then `/speckit-plan`
+ `/speckit-tasks` + `/speckit-implement`.

The first task is likely to write a non-interactive `report --errq`
extension to `engine/ree-debug-cli` that runs candump for N seconds,
aggregates ERRQ_Byte signals, decodes active error bits. The Python
backend then surfaces each active error as a `DiagnosticItem` under
the existing result view.

## Out of scope here

- Real-time CAN streaming in the SPA (Tier 3 from the integration plan).
- PyInstaller / Inno Setup distribution path for the web app.
- Migrating the TS_diagnostic_tool away — both surfaces stay alive
  during and after the port; operators choose by task.

## References

- Source: `TS_diagnostic_tool/{errq_aggregator,errq_bridge,errq_state,
  ssh_can_reader,dbc_handler,connection_dialog}.py`.
- Engine library where errq logic should land:
  `hackhaton/engine/ree-debug-engine/src/checks/`.
- SPA settings flow that should host the connection dialog:
  `hackhaton/specs/002-real-executor/spec.md` US2 / FR-009 — FR-012,
  task T052 onward.
