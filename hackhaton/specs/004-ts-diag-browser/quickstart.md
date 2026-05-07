# Quickstart — Live diagnostic surface (004)

This walks a fresh clone through running and smoke-testing 004 end-to-end
against a real testbed. It assumes 002's Real Executor (`VAYOBD_EXECUTOR=ree`)
quickstart already runs cleanly on your machine — the live surface reuses
the same backend / frontend dev servers and the same inventory.

## Prerequisites

- macOS or Linux with **Python 3.11+**, **Node 20+**, and **`ssh`** on
  `PATH`. (The `ssh` binary is the credential channel — Q2 of clarify.)
- Working SSH access to at least one in-scope TS host. Verify with:
  ```sh
  ssh ts-de-ber-00005 echo ok
  ```
  If this fails, fix `~/.ssh/config` first; the live surface inherits
  whatever your terminal's `ssh` does.
- Local clone of `ree-reecu`:
  ```sh
  ls ~/GitHub/ree-reecu/platform/tools/errq/errq.py
  ls ~/GitHub/ree-reecu/.../ts.dbc   # team-confirmed path TBD
  ```
  If the clone lives elsewhere, set `VAYOBD_REE_REECU_PATH` and
  `VAYOBD_DBC_PATH` (see Settings below).

## Install / build

From the repo root:

```sh
cd hackhaton/backend
python -m venv .venv
. .venv/bin/activate
pip install -e .
pip install cantools          # new in 004
```

```sh
cd ../frontend
npm install
```

(No engine workspace changes for 004 — the Rust workspace from 002 stays
as-is.)

## Settings: enable Developer mode

Edit `~/.config/vayobd/settings.toml` (created on first 002 run; create it
if missing):

```toml
developer_mode = true
ree_reecu_path = "/home/<you>/GitHub/ree-reecu"
dbc_path       = "/home/<you>/GitHub/ree-reecu/.../ts.dbc"   # confirm exact path
```

Save. The backend reads this on startup; `/api/health` will show
`live_diagnostic.enabled = true` and the frontend will render the "Live
diagnostic" button.

Alternatively, toggle Developer mode through the SPA settings card once
the dev servers are up — it round-trips the same TOML file.

## Run dev servers

Two terminals.

**Backend** (port 8002, matches the merged 003 vite proxy target):

```sh
cd hackhaton/backend
. .venv/bin/activate
VAYOBD_EXECUTOR=ree uvicorn vayobd.app:create_app --factory --port 8002 --reload
```

Watch the startup logs for two probes:
- `live: errq model loaded with 220 errors, 19 groups` — errq healthy.
- `live: DBC loaded from /home/<you>/.../ts.dbc — 84 messages` — DBC
  healthy.

If either probe fails, the live surface will still load (FR-012 / soft
DBC failure), but in degraded mode. Logs explain what's missing.

**Frontend** (port 5173 by default):

```sh
cd hackhaton/frontend
npm run dev
```

Open `http://localhost:5173` in a modern browser.

## Smoke-test US1 — "I see live signals"

1. On the main page, confirm the "**Live diagnostic**" button is visible
   next to the existing primary action. (If it isn't, Developer mode is
   off — re-check `settings.toml` or toggle through Settings.)
2. Click it. Land on `/live`.
3. Pick `ts-de-ber-00005` from the host picker. Click **Connect**.
4. Within ~10 s the page should transition from "Connecting…" to
   "Connected". The Signals tab fills with decoded names and live
   updating values.

If the connection fails, the page surfaces the first line of `ssh`'s
stderr along with a Retry button. Common failures:
- `ssh: connect to host ... port 22: No route to host` — your VPN is off
  or the testbed is down. Connect VPN and retry.
- `Permission denied (publickey,password)` — no key match in
  `~/.ssh/config`. Add a `Host ts-de-ber-*` entry pointing at the right
  identity file.

## Smoke-test US2 — "I see active REECU errors"

1. With a connection live, click the **REECU error queue** tab.
2. If the testbed has at least one active error, it should appear within
   ~1 s with symbolic name (e.g. `TS_FOO_BAR_ERR`), severity, channel,
   and byte/bit position.
3. If the panel shows "REECU error decoding unavailable — raw byte values
   shown instead", the errq model failed to load — check `ree_reecu_path`
   in settings and the backend startup log.

## Smoke-test US3 — "Filters and toolbar work"

1. Type `BRAKE` into the signal-name filter. The Signals table should
   shrink to brake-related signals only, with a count next to the filter.
2. Click **Channel B only**. Channel-A signals disappear from the
   Signals table; the errq panel filters to channel-B errors only.
3. Click **Pause**. The page stops updating but the "frames buffered"
   counter increments. Click **Resume** — values update again with the
   latest snapshot.
4. Toggle **Raw frames log**. A scrolling log of `<can_id> [<dlc>] <hex>`
   lines appears below the Signals tab on desktop, or as a third tab on
   phone viewports. Verify it caps at 500 lines.

## Phone smoke

Resize the browser to ≤ 360 px (DevTools → toggle device toolbar →
iPhone SE or similar). The three panels (Signals / Errq / Raw frames)
collapse into Tabs. The host picker stays single-column. The filter
input is sticky-bottom so the on-screen keyboard does not hide it.

## Clean up

- Click **Disconnect** in the page header, or close the tab. The backend
  receives the WebSocket close, terminates the `ssh` child, and drops
  the session.
- Backend logs should show `live: session 01HXXX closed cleanly`.
- No state persists on disk for live sessions (FR-021 + R5).

## What's NOT in 004

- Recording or replay of live sessions.
- Alerting on errors.
- Historical trends across runs.
- Mutating commands to the testbed.
- Multi-host single-screen view (one host per page, switching hosts
  closes and reopens the session).
