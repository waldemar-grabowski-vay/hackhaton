Authors: Ezequiel, Wilhelm, Spyros, Miguel, Waldemar

# VayOBD — diagnostic tooling

This repo houses **two** complementary diagnostic surfaces for Vay TS / VE
testbeds:

| Surface | Where | Audience | Story |
|---|---|---|---|
| **VayOBD web app** | `hackhaton/` (FastAPI + React + Rust workspace) | Non-technical operators on a phone-sized viewport | Pick a host through a 4-step wizard, click Run check, see plain-language results grouped Working / Needs attention with amber warnings + red errors. Real engine via `engine/ree-debug-cli`. |
| **TS Diagnostic Tool** | `TS_diagnostic_tool/` (PyQt6 Windows desktop) | Developers / hardware debuggers | Local Windows GUI that SSHes into the TS controller, streams `candump` over SSH, decodes CAN with the TS APP DBC, and translates REECU error-queue codes via the local `errq` tool. Builds to a Windows .exe via PyInstaller + Inno Setup. |

The web app is the production-default surface (`VAYOBD_EXECUTOR=ree`); the
desktop tool is for deep CAN/errq inspection on a Windows engineering box.
They share the same testbed hosts and SSH config but live in different
runtimes — same diagnostic intent, two operator profiles.

## Layout

```text
.
├── hackhaton/                 — VayOBD web app (most work happens here)
│   ├── backend/               — FastAPI + Pydantic
│   ├── frontend/              — React + Vite + shadcn/ui
│   ├── engine/                — Rust workspace: ree-debug-engine + ree-debug-tui + ree-debug-cli
│   └── specs/                 — feature specs (001-host-diagnostics, 002-real-executor, 002-sun-theme-palette, …)
└── TS_diagnostic_tool/        — PyQt6 Windows desktop diagnostic tool
```

## Quickstart per surface

- **Web app**: `hackhaton/specs/002-real-executor/quickstart.md`.
- **Desktop tool**: `TS_diagnostic_tool/README.md`.

## How they relate

The desktop tool predates the web app and contains real diagnostic IP that
the web app eventually wants to surface for operators — most notably the
REECU error-queue (`errq`) parsing, the CAN+DBC live decoding, and the
host/key/passphrase connection dialog. Porting these into the web app's
Rust engine library + SPA settings flow is tracked under
`hackhaton/specs/003-ts-diagnostic-cherry-picks/` (scaffold; not yet
implemented).

Until those ports land, both surfaces stay alive and operators pick the
one that fits their task.
