# Quickstart — Real Diagnostic Engine via ree-debug-tui

A walkthrough from "fresh clone" to "I see real engine output in
the result view". Two demoable paths:

- **Live engine** (`VAYOBD_EXECUTOR=ree`, default): runs the actual
  `ree-debug-cli` against your operator-configured inventory.
  Requires the engine workspace built and a reachable testbed.
- **Fixture mode** (`VAYOBD_EXECUTOR=fixture`): same as the 001
  quickstart — canned per-host YAML, no engine, no SSH. The demo
  build path; your fallback when the testbed is unavailable.

## Prerequisites

- Python 3.11+
- Node 20+ and `npm`
- Rust toolchain (`rustup` → `cargo`, `rustc`). MSRV ≥ 1.74. Same
  toolchain `ree-debug-tui` already requires.
- A local clone of `ree-vehicle-configs` (the team-maintained
  inventory repo). Typical: `~/GitHub/ree-vehicle-configs`.
- For live engine runs: SSH access to your DE testbed hosts via
  `~/.ssh/config` — same setup `ree-debug-tui` already requires.

Linux / macOS only; Windows operators run inside WSL2.

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

# Engine workspace
cd engine
cargo build --release --workspace
cd ..

# Confirm the CLI binary is present
ls engine/target/release/ree-debug-cli
```

Total time on a warm Cargo cache: ~2 minutes for the engine build,
the rest is fast.

## 2. Run in dev mode (live engine, two processes)

In one terminal — backend:

```bash
cd hackhaton
source .venv/bin/activate
VAYOBD_EXECUTOR=ree \
uvicorn vayobd.app:app --reload --port 8000
```

In a second terminal — frontend:

```bash
cd hackhaton/frontend
VAYOBD_DEV_USER=you@vay.io npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api/*` to `:8000` and
injects `X-Vay-User` (carried over from 001).

## 3. First-launch inventory setup (User Story 2)

On first launch — no `~/.config/vayobd/settings.toml` yet — the SPA
opens the **InventorySetupCard** instead of the wizard:

1. The card asks for the path to your `ree-vehicle-configs` clone.
   Pre-filled with `~/GitHub/ree-vehicle-configs`.
2. Type the actual path (or paste). Click **Save**.
3. The backend validates synchronously: directory exists +
   `org/vay/inventory.yaml` parses + non-empty.
4. On success: settings file written, wizard appears.
5. On failure: the card stays visible with a plain-language error
   ("That folder is missing org/vay/inventory.yaml — is this the
   right repo?").

Re-launch the backend / frontend — the wizard renders directly. The
"Inventory location" affordance in the wizard header lets you
change the path later (User Story 3).

## 4. Walk the P1 happy path against a real testbed

1. Header shows the brand mark, the Developer-mode switch, **and**
   an `EngineModeBadge` showing `live` (FR-007 visibility rule).
2. Wizard step 1 (Country): Germany selectable, United States
   greyed-out "Coming soon" (carried from 001). Pick **Germany**.
3. Wizard step 2 (Type): Vehicle / Telestation. Pick **Vehicle**.
4. Wizard step 4 (Host): pick a real DE testbed you have SSH access
   to. Click **Continue**.
5. Result page opens **blank** with a single "Run check" CTA
   (FR-028 carried from 001).
6. Click **Run check**. The engine subprocess runs (~5–20 s on a
   healthy host).
7. Result populates with **every** check the engine ran:
   - Working: green check icons.
   - Needs attention: items with `error` in red, `warning` items in
     amber (FR-004a / FR-004b).
   - Each row shows a category badge — Communication, Hardware,
     Configuration, Software, or Calibration (FR-006).
8. Toggle Developer mode. Each row's expand button reveals the
   engine's raw `raw_detail` output (CAN trace excerpts, exit
   codes, parser messages).
9. Click **Run check again**. The same flow re-runs (FR-008 carry).

## 5. Walk the failure paths

- **Engine binary not built** (you skipped step 1's `cargo build`):
  the result page renders with the `engine_unavailable` banner and
  a disabled "Run check" CTA. Banner copy includes `cargo build
  --release --workspace` as the remediation. Build the binary,
  refresh, CTA enables.
- **Engine binary stale** (you `git pull`'d new Python without
  re-building the workspace): the FR-003a startup self-check
  catches the mismatch; the banner switches to `engine_incompatible`
  with "rebuild the engine" copy.
- **Unreachable host**: pick a DE host that's powered off. Result
  shows the single "Host could not be reached" message (carried
  from 001).
- **Run timeout** (engine wedged for >30 s): demo by piping a
  fixture from `backend/tests/fixtures/runs/ve-de-saturn-slow.yaml`
  through fixture mode (next section), or manually disconnect the
  testbed mid-run.
- **Inventory file broken** (intentionally corrupt the YAML): the
  wizard shows the FR-019-style blocking empty-state with copy
  "your inventory file looks malformed" + the "Inventory location"
  affordance highlighted as the recovery path.

## 6. Fixture-mode demo (no engine, no testbed)

The 001 demo path is unchanged — same fixture executor, same canned
YAML in `backend/tests/fixtures/runs/`. Switch by setting:

```bash
VAYOBD_EXECUTOR=fixture \
VAYOBD_INVENTORY_PATH="$HOME/GitHub/ree-vehicle-configs" \
uvicorn vayobd.app:app --reload --port 8000
```

The header `EngineModeBadge` switches to `fixture`. Everything else
in the SPA looks identical — the operator never sees fixtures
described as "live" (per FR-007's visibility rule). Useful for:

- Demo days with no testbed network.
- CI / Playwright runs.
- Frontend development without a Rust toolchain.

## 7. Build for prod-ish demo

```bash
cd hackhaton/frontend
npm run build               # writes dist/ that the backend serves as static
cd ../engine
cargo build --release --workspace
cd ../backend
VAYOBD_EXECUTOR=ree uvicorn vayobd.app:app --port 8000
```

Single-process serve at `http://localhost:8000`.

## 8. Tests

```bash
# Engine workspace
cd hackhaton/engine
cargo test --workspace
cargo build --release --workspace      # also ensure release builds clean

# Backend
cd ../backend
source ../.venv/bin/activate
pytest                                  # includes test_ree_cli_executor.py against a fake CLI binary

# Frontend
cd ../frontend
npm run typecheck
npm run lint
npm test                                # vitest, if present
npm run test:e2e                        # Playwright; needs both servers running
```

The Playwright smoke covers the P1 happy path + Developer toggle +
the new `warning` row + the setup-card walkthrough. Constitution's
Workflow gate.

## 9. Switch to live SSH executor (already covered)

Live engine is the default in step 2. There's no separate
"executor" toggle in 002 — the `VAYOBD_EXECUTOR=ree` invocation IS
the live path.

## 10. What's intentionally not in v1

- No `GET /api/runs/latest` (FR-028 carries forward — result view
  blank-on-entry, no auto-recall of stored runs).
- No engine daemon — every run is its own subprocess (FR-003).
- No PyO3 bindings (clarified in 002's spec; rejected for v1).
- No mutating actions in the SPA — `b` (bring up XCP bus) and `d`
  (toggle debug-mode sentinel) live only in the `ree-debug-tui`
  binary, not in `ree-debug-cli` or the engine library.
- No periodic inventory refresh / "Update inventory" button — the
  cache + refresh layer from 001 is retired (FR-013a).
- No semver schema versioning — git SHA is the contract (FR-003a).
