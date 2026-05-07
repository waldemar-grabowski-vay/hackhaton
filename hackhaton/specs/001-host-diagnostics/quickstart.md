# Quickstart — Remote Host Diagnostics

A working walkthrough from "fresh clone" to "I see the result screen with
real animations" using the fixture executor — no live host needed.

## Prerequisites

- Python 3.11+
- Node 20+ and `npm` (or `pnpm`)
- A local checkout of `ree-vehicle-configs`. The default expected path is
  `~/.cache/vayobd/ree-vehicle-configs`. If you already have the repo
  somewhere (e.g., `~/GitHub/ree-vehicle-configs`), just symlink it into
  the cache path or set `VAYOBD_INVENTORY_PATH` to the existing checkout.

## 1. One-time setup

```bash
# from the repo root
cd hackhaton

# Backend
python -m venv .venv && source .venv/bin/activate
pip install -e backend

# Frontend
cd frontend
npm install
cd ..

# Inventory cache (skip if you already have ree-vehicle-configs locally)
mkdir -p ~/.cache/vayobd
git clone git@github.com:vay/ree-vehicle-configs.git ~/.cache/vayobd/ree-vehicle-configs
```

## 2. Run in dev mode (two processes, fixture executor)

In one terminal:

```bash
cd hackhaton
source .venv/bin/activate
VAYOBD_EXECUTOR=fixture \
VAYOBD_INVENTORY_PATH=~/.cache/vayobd/ree-vehicle-configs \
uvicorn vayobd.app:app --reload --port 8000
```

In a second terminal:

```bash
cd hackhaton/frontend
# Set a dev-only X-Vay-User header so the backend's per-operator
# persistence (FR-026) has something to key on. The dev Vite proxy
# injects this header on every /api/* request.
VAYOBD_DEV_USER=you@vay.io npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api/*` to `:8000` and
adds `X-Vay-User: $VAYOBD_DEV_USER` (default `dev@local`) to each
proxied request. In production the upstream SSO-terminating proxy
provides this header instead.

## 3. Walk the P1 happy path

1. Header shows "VayOBD" + a Developer-mode switch (off).
2. Wizard step 1 (Country): two tiles — **Germany** (selectable) and
   **United States** (greyed out with a "Coming soon" sublabel; clicking
   it does nothing per FR-001a step 1). Pick **Germany**.
3. Wizard step 2 (Type): two cards **Vehicle** / **Telestation**. Pick
   **Vehicle** to skip the city step.
4. Wizard step 4 (Host): a card grid of German vehicle hosts. Pick
   `apollo` (`ve-de-apollo`).
5. The result screen opens **blank** — only the host header and a
   single "Run check" CTA are visible (FR-028). No prior run is
   auto-displayed even if you ran one yesterday.
6. Press **Run check**. The animated "Running checks…" state plays for
   ~1–2 s (fixture executor sleeps).
7. Result populates: glass hero card with the host name, run timestamp,
   and the status donut. Below it, two groups: **Working** (green,
   animated check icons) and **Needs attention** (amber, with
   recommended next actions). Every catalog item appears by name in
   exactly one group (FR-003).
8. Flip the **Developer mode** switch in the header. Each item row
   gains an expand control revealing the raw output (lsusb output,
   candump excerpt, parser message). Flip it off — the controls
   disappear with no data refetch (FR-021/FR-022).
9. Click **Run check again**. The same flow runs against the same host
   (US2 / FR-008). The just-completed run remains visible until the new
   one replaces it.

## 4. Walk the failure paths

- **Unreachable host**: edit the fixture file at
  `backend/tests/fixtures/runs/<host_id>.yaml` to set `outcome: unreachable`.
  Run the check. The result screen renders the single user-facing
  unreachable message — no item list (FR-006).
- **Run timeout**: edit the fixture file to set `delay_seconds: 35`
  (above the 30 s hard ceiling per FR-025). Run the check. The result
  is `outcome: "timeout"` with no items, and the frontend renders a
  single "the check did not finish in time" message keyed by outcome
  (FR-006 + FR-025).
- **Inventory missing**: stop the backend, move the inventory checkout
  aside, restart the backend. The picker renders the blocking
  "Inventory could not be loaded" state with an "Update inventory"
  button (FR-019). Click the button — it calls
  `POST /api/inventory/refresh`, which fails (no source). Move the
  checkout back, click again — the wizard appears.
- **Inventory refresh fails with cache present** (FR-027): with a
  working cached inventory loaded, set `VAYOBD_INVENTORY_REMOTE` to a
  bogus URL and click **Update inventory** three times in a row. The
  first two failures are silent (background-only). After the third
  consecutive failure the persistent banner
  "Inventory refresh failed — using last good copy from {timestamp}"
  appears at the top of the wizard. Restore the URL, click **Update
  inventory** once — the banner disappears.
- **Concurrent run**: trigger two `POST /api/runs` for the same host
  back-to-back. The second returns 409 and the frontend toast appears.
  The "Run check" button stays disabled while a run is in flight
  (FR-011).
- **Per-operator persistence sanity check** (FR-026): start a run as
  `VAYOBD_DEV_USER=alice@vay.io`, stop the dev server, restart it as
  `VAYOBD_DEV_USER=bob@vay.io`, navigate to the same host, and inspect
  `~/.cache/vayobd/runs/`. There are two operator subdirectories, each
  containing only that operator's run JSON. Per FR-028, neither
  operator sees the other's run auto-loaded in the UI; this is a
  filesystem-level check.

## 5. Build for prod-ish demo

```bash
cd hackhaton/frontend
npm run build               # writes dist/ that the backend serves as static
cd ../backend
VAYOBD_EXECUTOR=fixture uvicorn vayobd.app:app --port 8000
```

Open `http://localhost:8000` — single-process serve.

## 6. Switch to live SSH executor

Set `VAYOBD_EXECUTOR=ssh` and provide:

- `VAYOBD_SSH_KEY=/path/to/private_key`
- `VAYOBD_SSH_KNOWN_HOSTS=/path/to/known_hosts`

The `Host.address` field for each host is read from the matching
`ree-vehicle-configs` YAML (`network.ve_addresses[0]` for vehicles,
configured equivalent for telestations). The fixture executor and the
SSH executor are interchangeable behind the same `Executor` interface, so
no other code changes.

## 7. Tests

```bash
# Backend unit + integration
cd hackhaton/backend
pytest

# Frontend unit
cd ../frontend
npm test

# End-to-end smoke (Playwright, fixture executor)
npm run test:e2e
```

The Playwright smoke covers exactly the P1 happy path from step 3 above
plus the Developer-mode toggle round-trip — that is the demo-readiness
gate per the constitution's Development Workflow section.

## 8. What's intentionally not in v1

- No login screen (corp SSO at the proxy — R4)
- No historical runs view (assumption in `spec.md`)
- No background/streaming updates while a run is in flight (R5)
- No cancel button (FR-024)
- No German UI (FR-014; revisit when prioritised)
- No in-app developer guides surface (Session 2026-05-06 chose mode B only)
- No US/Belgium hosts in the picker (Clarification 2026-05-07; US is
  rendered as a disabled "Coming soon" tile only)
- No `GET /api/runs/latest` endpoint and no auto-recall of stored runs
  in the UI (FR-028 + `research.md` R7)
