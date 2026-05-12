# Quickstart — 008 acceptance walk-through

**Audience**: anyone reviewing or demoing 008
**Date**: 2026-05-12
**Estimated time**: ~15 minutes end-to-end against a real testbed (TS + VE)

This walkthrough drives every acceptance scenario in `spec.md` once,
in order, with the exact commands and expected results. It supersedes
the 2026-05-11 version by absorbing the 2026-05-12 clarifications:
tiered restoration (Ezequiel's FE branch + local `01d3979` for BE +
engine), 3-way file merges, VE-signal + VE-errq port from Wilhelm,
the repair-guide library surface, and the 005 → 009 spec rename.

---

## Prerequisites

1. Working tree on this branch (`008-restore-host-checks-fix-live`),
   build artefacts current.
2. `ree-vehicle-configs` and `ree-reecu` clones present at the
   paths `~/.config/vayobd/settings.toml` points to. The `ree-reecu`
   clone MUST include the VE errq subpath (see Step 4 — the spike
   command finds it).
3. SSH config (`~/.ssh/config`) with working entries for **at least
   one in-scope TS host AND one in-scope VE host** (e.g.
   `ts-de-ber-00005` and `ve-de-00012`).
4. The .deb installed at `dist/vayobd_0.0.X_amd64.deb` (any 0.0.6+
   build will work); `/usr/bin/vayobd --version` succeeds.

---

## Step 1 — Tiered restoration: bring the deletions back

Per `contracts/ezequiel-cherry-pick.md`, restoration sources split
into three tiers. Tier A is from Ezequiel's branch; Tiers B + C are
from local commit `01d3979`.

```bash
# from repo root (where this file's grandparent .specify/ lives)

# ─── Tier A: Frontend from origin/005-ve-harness-repair-guide ───
# Improved replacements (existing files):
for path in \
  hackhaton/frontend/src/components/result/HarnessDiagram.tsx \
  hackhaton/frontend/src/components/result/RepairGuideSheet.tsx \
  hackhaton/frontend/src/components/result/TelestationDiagram.tsx
do
  git checkout origin/005-ve-harness-repair-guide -- "$path"
done

# Net-new files (no HEAD counterpart):
for path in \
  hackhaton/frontend/src/components/chrome/RepairGuideLibraryDialog.tsx \
  hackhaton/frontend/src/pages/RepairGuidesPage.tsx \
  hackhaton/frontend/src/guideLibrary.ts \
  hackhaton/frontend/public/ve-pigtail-f61-harness.jpg \
  hackhaton/frontend/public/ve-reebox-power-cable-harness.jpg \
  hackhaton/frontend/public/ve-vs040815-harness-p1.png \
  hackhaton/frontend/public/ve-vs040815-harness.pdf
do
  git checkout origin/005-ve-harness-repair-guide -- "$path"
done

# Pre-007 frontend deletions, recovered from Ezequiel's branch:
for path in \
  hackhaton/frontend/src/api/runs.ts \
  hackhaton/frontend/src/components/result/CategoryBadge.tsx \
  hackhaton/frontend/src/components/result/DiagnosticItemRow.tsx \
  hackhaton/frontend/src/components/result/ResultGroup.tsx \
  hackhaton/frontend/src/components/result/ResultHero.tsx \
  hackhaton/frontend/src/components/states/EmptyInventoryState.tsx \
  hackhaton/frontend/src/components/states/PartialRunState.tsx \
  hackhaton/frontend/src/components/states/RunningState.tsx \
  hackhaton/frontend/src/components/states/UnreachableState.tsx \
  hackhaton/frontend/src/components/motion/StaggeredList.tsx \
  hackhaton/frontend/src/pages/RunResultPage.tsx
do
  git checkout origin/005-ve-harness-repair-guide -- "$path"
done

# ─── Tier B: Backend from local pre-007 commit 01d3979 ───
for path in \
  hackhaton/backend/src/vayobd/api/runs.py \
  hackhaton/backend/src/vayobd/checks/__init__.py \
  hackhaton/backend/src/vayobd/checks/catalog.py \
  hackhaton/backend/src/vayobd/checks/executor.py \
  hackhaton/backend/src/vayobd/checks/peplink.py \
  hackhaton/backend/src/vayobd/checks/ree_cli.py \
  hackhaton/backend/src/vayobd/checks/runner.py \
  hackhaton/backend/tests/integration/test_runs_endpoint.py \
  hackhaton/backend/tests/unit/test_catalog.py
do
  git checkout 01d3979 -- "$path"
done

# ─── Tier C: Engine Rust from local pre-007 commit 01d3979 ───
for path in \
  hackhaton/engine/ree-debug-engine/src/checks/cameras.rs \
  hackhaton/engine/ree-debug-engine/src/checks/connectivity.rs \
  hackhaton/engine/ree-debug-engine/src/checks/decode.rs \
  hackhaton/engine/ree-debug-engine/src/checks/mod.rs \
  hackhaton/engine/ree-debug-engine/src/checks/reecu.rs \
  hackhaton/engine/ree-debug-engine/src/checks/usb.rs
do
  git checkout 01d3979 -- "$path"
done

# Verify no deletions remain:
git status --short | grep "^ D " || echo "OK: no deletions remain"
```

Expected: `OK: no deletions remain`.

---

## Step 2 — 3-way hand-merge: strings.ts + 3 shared files

Per `contracts/strings-merge.md` and `contracts/ezequiel-cherry-pick.md`
section B. Four files have legitimate edits in all three sources
(post-007 HEAD, Ezequiel's branch, pre-007 `HEAD~N`). Merge rule:
**post-007 HEAD wins on key collision; otherwise union all three**.

```bash
# 2a. strings.ts — full 3-way merge
cp hackhaton/frontend/src/strings.ts /tmp/strings.post007.ts
git show 01d3979:hackhaton/frontend/src/strings.ts > /tmp/strings.pre007.ts
git checkout origin/005-ve-harness-repair-guide -- \
  hackhaton/frontend/src/strings.ts
# Open all three in $EDITOR:
#   - hackhaton/frontend/src/strings.ts   (Ezequiel's, working tree)
#   - /tmp/strings.post007.ts             (HEAD; contains hostVersions block)
#   - /tmp/strings.pre007.ts              (HEAD~N; contains runs/outcomes/result/category/guide/item)
# Layer the hostVersions block from post007 into the working tree.
# Layer the runs/outcomes/result/category/guide/item blocks and
# categoryLabel() from pre007 into the working tree.
# On any key collision, the post007 value wins.

# 2b. The other three shared files — verify, then merge
for path in \
  hackhaton/frontend/src/connectorLocations.ts \
  hackhaton/frontend/src/connectorSpecs.ts \
  hackhaton/frontend/src/guides.ts
do
  # Confirm post-007 HEAD had no meaningful edits to these (orphans in HEAD):
  git diff 01d3979..HEAD -- "$path" | head -20
  # If diff is small/empty: clean-replace from Ezequiel's branch is safe.
  git checkout origin/005-ve-harness-repair-guide -- "$path"
done
```

Verify:

```bash
cd hackhaton/frontend
npm run build && npm run lint   # both MUST exit zero
# Also: grep the rendered dist/ for literal "strings." path keys —
# zero hits (SC-004).
grep -rE 'strings\.[a-z]+\.' dist/ 2>&1 | head -5 || echo "OK: no path keys"
```

---

## Step 3 — Re-wire runs_router + cherry-pick App.tsx route

```bash
# 3a. Backend: re-include the restored runs_router
# Edit hackhaton/backend/src/vayobd/app.py:
#   - Add: from vayobd.api.runs import router as runs_router
#   - Add: app.include_router(runs_router)
# (Next to the other include_router calls.)

# 3b. Frontend: register the /repair-guides route
# Edit hackhaton/frontend/src/App.tsx by hand to add the route delta
# Ezequiel introduces (his branch has unrelated chrome edits that
# would mis-merge):
#   - import { RepairGuidesPage } from "./pages/RepairGuidesPage";
#   - Add <Route path="/repair-guides" element={<RepairGuidesPage />} />
#     in the existing <Routes>.

# 3c. Frontend: chrome entry point (research §9 — header link, not gated)
# Edit hackhaton/frontend/src/components/chrome/AppHeader.tsx:
#   - Add a Link to "/repair-guides" labelled "Repair guides" beside
#     the existing nav items. NOT inside a Developer-mode-gated branch.

# Verify routes are wired:
cd hackhaton
pytest backend/ -q                            # MUST pass
cd frontend && npm run build && npm run lint  # MUST pass
```

---

## Step 4 — VE errq CSV path lookup + add the resolver

Per `contracts/ve-errq.md`. Confirm the VE subpath inside the local
`ree-reecu` clone, then implement the resolver.

```bash
# 4a. Find the actual VE errq subpath
REE_REECU_ROOT=$(grep -E '^ree_reecu_root' ~/.config/vayobd/settings.toml \
  | sed -E 's/.*= *"?([^"]+).*/\1/')
echo "ree-reecu clone at: $REE_REECU_ROOT"
find "$REE_REECU_ROOT/ve" -type d -name "*errq*" 2>/dev/null

# 4b. Use the directory the find returned to bake the resolver
# constant in hackhaton/backend/src/vayobd/live/errq_bridge.py.
# /speckit-tasks generates the exact edit task.

# 4c. Verify the resolver
pytest hackhaton/backend/tests/unit/test_errq_bridge.py -q
# Both TS-host and VE-host resolution paths covered.
```

If the find returns no directory: the resolver still ships, but the
`/live` errq panel surfaces the 004 FR-012 degraded-mode message on
VE-host connections. Document the missing-clone state in the PR.

---

## Step 5 — VE state-signal port

Per `contracts/ve-signals.md`. Extend the state-panel allowlist.

```bash
# 5a. Grep the current Wilhelm allowlist
grep -E '^[[:space:]]*"(VE|TS)_' \
  /home/waldemar-grabowski/GitHub/hackhathon/TS_diagnostic_tool/config.py \
  | sort -u

# 5b. Apply the diff: the web app's state-panel allowlist (location
# confirmed at /speckit-plan) MUST include every entry in 5a's output
# that isn't already there. /speckit-tasks emits the exact edit task.

# 5c. Verify
pytest hackhaton/backend/tests/unit/test_live_state_filter.py -q
cd hackhaton/frontend
npx playwright test live-diagnostic.spec.ts
```

---

## Step 6 — Wire the REECU one-shot capture

Per `contracts/reecu-pipeline.md`. Concrete tasks generated by
`/speckit-tasks`:

- New module `hackhaton/backend/src/vayobd/api/_reecu_capture.py`
  wrapping `vayobd.live.session.LiveSession` with a 4-second bounded
  capture window.
- Extend `hackhaton/backend/src/vayobd/api/host_versions.py::_collect_versions`
  to call `capture_reecu_state(host_id, host_type, settings)` in
  parallel with the existing `_invoke_engine` call. Merge results.
  Note `host_type` is passed through so the capture knows the
  appropriate signal allowlist.
- Add `hackhaton/backend/tests/unit/test_reecu_capture.py` driving
  the capture against a recorded `candump` log fixture (one TS
  fixture + one VE fixture).

Verify after implementation:

```bash
pytest hackhaton/backend/tests/unit/test_reecu_capture.py -q
pytest hackhaton/backend/tests/integration/test_host_versions_endpoint.py -q
```

---

## Step 7 — Compose the unified host-detail layout

In `hackhaton/frontend/src/pages/HostDetailPage.tsx`:

- Keep 007's `<SourcePill>` + version cells + refresh button at the
  top.
- Add a second section below it that renders, when `data.run` is
  non-null, the restored `<ResultHero>` + `<ResultGroup>` instances
  (Working / Needs attention groups), using Ezequiel's improved
  `<HarnessDiagram>` and `<RepairGuideSheet>` for any failed-item
  drilldowns.
- Route REECU rows from `data.versions` to the version card only;
  route non-REECU rows from `data.run.items` to the result groups.
- When `data.run` is `null` (in flight), render the restored
  `<RunningState>` below the version card.
- Inventory dialog used by `/live` gets the `TS` / `VE` pill
  (per FR-019).

Verify:

```bash
cd hackhaton/frontend
npm run build && npm run lint
npx playwright test     # all specs MUST pass
```

---

## Step 8 — Pull in Ezequiel's spec dir as 009

Documentation companion, no code.

```bash
git checkout origin/005-ve-harness-repair-guide -- \
  hackhaton/specs/005-ve-harness-repair-guide/
git mv hackhaton/specs/005-ve-harness-repair-guide \
       hackhaton/specs/009-ve-harness-repair-guide
# Hand-edit hackhaton/specs/009-ve-harness-repair-guide/spec.md:
#   **Feature Branch**: `005-ve-harness-repair-guide` → `009-ve-harness-repair-guide`
# (Self-references only; cross-references to other 005-* features stay as 005.)
```

---

## Step 9 — Manual end-to-end against the installed .deb

```bash
# Run the .deb-installed binary (full path bypasses any pyenv shim).
/usr/bin/vayobd run

# Open http://127.0.0.1:8000 in your browser.
```

### 9a. TS-host walkthrough (US1, US2, US3, US4)

1. **Pick a reachable TS host through the wizard.** Within 10 s of
   landing on the detail page, you should see:
   - The version card at the top with vDrive / vREECU / SEC
     resolved (live values + verdict pills + as-of timestamps +
     source pill + refresh button — all 007's UI intact).
   - The check battery below: a "Working" group with the passing
     checks (e.g. SSH reachable, network reachable) and a "Needs
     attention" group with any failing ones (e.g. Peplink VPN if
     a tunnel is down).
   - Repair-guide buttons next to failed items where a guide is
     registered (harness diagram, WAKE signal-path, etc.).
   - Improved harness diagrams: tap a connector chip; the harness
     panel auto-switches tabs and pulses red over the connector
     location (Ezequiel's enhancement).
2. **Click a repair-guide button.** Confirm it opens as a SHEET
   over the page — the version card remains visible behind it.
3. **Click the Refresh button on the version card.** Confirm:
   - Both pipelines re-run with `?fresh=true`.
   - All three version cells go back to loading (em-dash + spinner)
     until the response lands.
   - The check battery either re-runs alongside OR keeps its prior
     result — never silently disappears.
4. **Navigate away and back within 60 s.** The page renders the
   cached values instantly (no spinner, no engine call).
5. **Toggle Developer mode on.** Confirm BOTH "Live diagnostic"
   buttons appear (header + main page primary-action area).
6. **Click the header "Live diagnostic" copy.** Lands on `/live`.
   - The page mounts; connection dialog renders; inventory list
     populates within 5 s; no console errors; no 4xx/5xx.
   - **Each host row carries a small `TS` / `VE` pill** (FR-019).
7. **Pick the TS host, click Connect.** Within 10 s, decoded CAN
   signals stream into the state panel. The errq panel either
   shows active errors OR a plain-language degraded-mode message —
   the rest of the surface keeps working.
8. **Toggle Developer mode off.** Both Live-diagnostic buttons
   disappear together. Direct navigation to `/live` still
   redirects to the picker.
9. **Read any user-facing string anywhere on the page.** No
   literal `strings.xxx.yyy` path keys appear. No stale "Run check
   against this host" copy.

### 9b. VE-host walkthrough (US2 + SC-009 + VE-SIG-* + VE-ERRQ-*)

10. **Open `/live` (Developer mode on).** Confirm the inventory
    list shows the VE host with a `VE` pill.
11. **Pick the VE host, click Connect.** Within 10 s:
    - Decoded CAN signals stream into the state panel.
    - The state panel **includes** `VE_ChA_SSMAN_State`,
      `VE_ChB_SSMAN_State`, `VE_PRND_STATE` (and any additional
      `VE_*` signals carried by Wilhelm's `TS_STATE_SIGNALS`).
    - **No** `TS_*` entries that don't broadcast on this bus appear
      (allowlist falls through naturally on data).
12. **Inspect the errq panel.**
    - If `find $REE_REECU_ROOT/ve -name "*errq*"` returned a
      directory at Step 4: panel renders decoded VE-side errors
      using the resolved VE CSVs.
    - If not: panel shows the 004 FR-012 degraded-mode message.
      State panel and raw frames log keep streaming.
13. **Navigate back to the host-detail page for the VE host.**
    The version card renders whatever fields apply for vehicles
    (engine's `parse_engine_report(host_type="vehicle", …)`
    decides). The check battery from `catalog_for("vehicle")`
    appears below.

### 9c. Library walkthrough (US5 + SC-008)

14. **Click the "Repair guides" link in the header.** From any
    page, the route navigates to `/repair-guides` and
    `RepairGuidesPage` mounts.
15. **Verify the catalogue lists every registered guide** —
    grouped sensibly (harness or host type, per `guideLibrary.ts`).
16. **Click a guide entry.** A `RepairGuideSheet` opens with the
    harness diagram + step list — exactly as the host-detail surface
    opens the same guide. Same component, same data.
17. **Toggle Developer mode off.** The "Repair guides" link in the
    chrome **stays visible** (operator-facing, not gated — FR-017).

---

## Step 10 — Release-readiness gate

```bash
# Final triple-green:
cd hackhaton/backend && pytest -q
cd ../frontend && npm run build && npm run lint && npx playwright test
```

All three MUST exit zero. Mention in the PR description, including:

- Confirmation that the VE walkthrough (9b) passed against a real
  VE host, OR a note that VE CSVs were unavailable so the
  degraded-mode fallback was verified instead.
- The chrome entry point chosen for the library (header link, not
  Developer-mode-gated).

If you want to rebuild the .deb to test on a fresh machine:

```bash
./hackhaton/packaging/build.sh --version 0.0.7
# → dist/vayobd_0.0.7_amd64.deb
```

(The bundled-Python work from the 006 .deb continues to apply —
no system Python dependency. 008 does not modify packaging.)

---

## Acceptance-scenario mapping

| Spec section | Step in this quickstart |
|---|---|
| US1 #1–#5 | Step 9a (1–4) |
| US2 #1, #2, #4, #5, #6 | Step 9a (6–9) |
| US2 #3 (VE state signals) | Step 9b (11) |
| US3 #1–#4 | Step 7 + Step 9a (1, 2) |
| US4 #1–#4 | Step 9a (3, 8, 9) |
| US5 #1–#4 | Step 9c (14–17) |
| SC-001 (versions + checks render) | Step 9a (1) |
| SC-002 (LD reaches decoded-signal state) | Step 9a (6, 7); Step 9b (11) |
| SC-003 (every pre-007 check appears) | Step 9a (1) — confirm against pre-007 catalog if uncertain |
| SC-004 (no literal strings.xxx paths) | Step 2 verification + Step 9a (9) |
| SC-005 (007's TTL cache holds) | Step 9a (3, 4) |
| SC-006 (operator scans in <3 s) | Step 9a (1, 2) — informal usability check |
| SC-007 (.deb-installed binary preferred) | Step 9 (start with `/usr/bin/vayobd run`) |
| SC-008 (library reachable in ≤2 clicks) | Step 9c (14, 16) |
| SC-009 (VE signals + TS regression check) | Step 9b (11) + Step 9a (7) |
| VE-SIG-1..VE-SIG-4 | Step 9b (11) |
| VE-ERRQ-1..VE-ERRQ-4 | Step 9b (12) + Step 9a (7) |
