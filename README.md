Authors: Ezequiel, Wilhelm, Spyros, Miguel, Waldemar

# VayOBD — diagnostic tooling

This repo houses **two** complementary diagnostic surfaces for Vay TS / VE
testbeds:

| Surface | Where | Audience | Story |
|---|---|---|---|
| **VayOBD web app** | `hackhaton/` (FastAPI + React + Rust workspace) | Vay engineers on a phone-sized viewport | Pick a host through a 4-step wizard, open the host-detail page to see the three deployed versions (vDrive manifest, vREECU, SEC) pulled live from the host and cross-checked against the bundled manifest. Developer mode adds a Live diagnostic surface for live CAN / REECU error-queue inspection. Real engine via `engine/ree-debug-cli`. |
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

- **Web app (current host-detail flow)**: `hackhaton/specs/007-ts-diag-restore-version-pull/quickstart.md`.
- **Desktop tool**: `TS_diagnostic_tool/README.md`.

## How they relate

The desktop tool predates the web app and contains real diagnostic IP that
the web app surfaces through a Developer-mode-gated **Live diagnostic**
page — implemented under
[`hackhaton/specs/004-ts-diag-browser/`](hackhaton/specs/004-ts-diag-browser/).
The browser edition shells out to the operator's local `ssh` (no
credential collection), streams `candump`, decodes CAN with the TS DBC
via `cantools`, and reuses the desktop tool's REECU `errq` IP verbatim.
Operators on Developer mode see a "Live diagnostic" button next to the
primary action and land on a page with a state panel, a REECU error
queue, and an optional raw-frames log. See
[`specs/004-ts-diag-browser/quickstart.md`](hackhaton/specs/004-ts-diag-browser/quickstart.md)
for the operator walkthrough.

Both surfaces remain alive: the desktop tool is still the canonical
deep-CAN inspection environment on Windows, and the web app's
Live-diagnostic page is the same IP made accessible from any browser
on the operator's machine.
