# Vay OBD Live — POC

(formerly "TS Diagnostic Tool" — same project, broader scope: TS and VE.)

Local Windows GUI that SSHes into the Vay TS controller, streams CAN traffic
via `candump`, decodes it with the TS APP DBC, and translates error codes
through the local `errq` tool.

## Pieces

```
diagnostic_tool/
├── main.py            PyQt6 window: state panel + error table + raw log
├── ssh_can_reader.py  paramiko SSH + candump live streamer (one thread/bus)
├── dbc_handler.py     cantools-based DBC loader and decoder
├── errq_bridge.py     dynamic import of platform/tools/errq with CLI fallback
├── config.py          all paths, host, signal lists — edit this first
├── requirements.txt
├── build.bat          one-shot Windows build: PyInstaller + Inno Setup
└── packaging/
    ├── ts_diag.spec   PyInstaller spec (one-folder, windowed)
    └── installer.iss  Inno Setup script — produces Vay_OBD_Live-Setup-*.exe
```

## Setup

```powershell
cd diagnostic_tool
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Make sure your local SSH agent has the key for `wilhelm.leonhardt@10.1.200.15`
loaded — paramiko reuses agent keys, no passwords are prompted.

## Run

```powershell
python main.py
```

1. Click **Connect** — the toolbar shows the SSH status.
2. The streamer auto-detects every UP `can*` interface on the remote and
   spawns one `candump -tz -L <iface>` per bus.
3. Decoded messages whose name matches a TS state signal show up in the
   left panel; anything that smells like an error/fault/DTC code is routed
   to the right table and translated through `errq`.
4. The Raw CAN log dock at the bottom shows every frame in candump format.

## What you'll likely tune

- **`config.REPO_ROOT`** — defaults to `C:\__REPOS\ree-reecu_main`. Override
  with the `REE_REECU_ROOT` env var if needed.
- **`config.DBC_GLOB_PATTERNS`** — adjust if the TS APP DBC isn't found.
- **`config.TS_STATE_SIGNALS`** — names of signals to surface in the state
  panel. The current list is a guess; replace with real signal names from
  your DBC.
- **`errq_bridge._resolve()`** — the bridge probes for `lookup`, `translate`,
  `decode_error` etc. If the real entry point in `platform/tools/errq`
  is something else (or wants a different argument shape), change this
  function — that's the only place that knows about errq's API.

## Building the Windows installer

Produces a real `setup.exe` that installs into Program Files with a
Start Menu entry, optional desktop shortcut, and an uninstaller.

**Prerequisites (one-time, on the build machine):**

1. Python 3.11 or 3.12 on `PATH`.
2. [Inno Setup 6](https://jrsoftware.org/isdl.php) — default install
   location is auto-detected. If you put it elsewhere, set the `ISCC`
   environment variable to the full path of `ISCC.exe` before running.

**Build:**

```powershell
cd diagnostic_tool
build.bat
```

What it does:

1. Creates `.build_venv\` (isolated from your dev venv).
2. `pip install -r requirements.txt && pip install pyinstaller`.
3. Runs PyInstaller against `packaging\ts_diag.spec` — output is
   `dist\Vay_OBD_Live\Vay_OBD_Live.exe` (portable folder build, ready to run).
4. Runs `ISCC.exe packaging\installer.iss` — output is
   `dist_installer\Vay_OBD_Live-Setup-<version>.exe`.

Bump the version string in `packaging\installer.iss` (`AppVersion`) for each
release. The `AppId` GUID must stay the same across versions — that's how
Windows recognizes upgrades vs side-by-side installs.

The DBC and the `errq` tool are **not** bundled into the installer: they're
read at runtime from `C:\__REPOS\ree-reecu_main`. Anyone using the installer
needs that repo cloned locally (or `REE_REECU_ROOT` pointed elsewhere).

## Known limitations of the POC

- No reconnect-on-drop. Disconnect/reconnect manually.
- No persistence — the error table is in-memory only.
- Severity colours are heuristic; they only kick in if `errq` returns a
  `severity` field.
- `candump -L` is the parser format. If a DBC message has a different
  `frame_id` mask (e.g. J1939 PGN), the lookup will miss — easy to extend
  in `dbc_handler.DbcDecoder.decode`.
