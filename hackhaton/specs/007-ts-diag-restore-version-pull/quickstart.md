# Quickstart — 007 acceptance walk-through

**Audience**: anyone reviewing or demoing this feature
**Date**: 2026-05-11
**Estimated time**: 10 minutes end-to-end against a real testbed

This walkthrough drives every acceptance scenario in `spec.md` once,
in order, with the exact commands and expected results.

---

## Prerequisites

1. Working tree built from this branch (007-ts-diag-restore-version-pull).
2. The 006 dependency repos cloned (`ree-vehicle-configs`, `ree-reecu`,
   `system-release-deployment`) at the paths
   `~/.config/vayobd/settings.toml` already points at.
3. SSH config (`~/.ssh/config`) has a working entry for at least one
   in-scope TS host (e.g. `ts-de-ber-00005`).
4. `ree-debug-cli` binary on `$PATH` (or `engine_binary_path` set in
   `settings.toml`). Confirm with `ree-debug-cli --version`.

---

## Step 1 — Rebuild and start

```bash
# backend
cd backend && pip install -e . && cd ..

# frontend
cd frontend && npm install && npm run build && cd ..

# launch (loopback)
vayobd run   # or however the existing local dev script starts uvicorn
```

Open the printed URL (typically `http://127.0.0.1:8000`).

---

## Step 2 — US1: Restore TS_diag entry points (Clarifications Q5, Q3)

**Goal**: confirm the "Live diagnostic" button appears in BOTH the
global header and the main-page primary action area when Developer
mode is toggled on, and disappears from both when toggled off.

1. Open the main page.
2. Locate the Developer-mode switch in the global header (top-right).
3. **Toggle Developer mode OFF.** Expected:
   - Header button: hidden.
   - Main-page primary action area: no Live diagnostic button next to
     the existing primary action.
4. **Toggle Developer mode ON.** Expected:
   - Header button: visible, labelled "Live diagnostic", activates
     and routes to `/live` on click (FR-001 acceptance #1).
   - Main-page primary action area: a second "Live diagnostic"
     button appears, matching the visual weight of the existing
     primary action (FR-013).
   - Both buttons render within one render cycle of toggling the
     switch (SC-001).
5. Navigate to a host detail page or to `/live` directly. The header
   button MUST remain visible from the sub-page (FR-001 acceptance
   #4).
6. Click the header button from the sub-page; confirm it lands on
   `/live` (acceptance scenario #3).

**Pass criteria**: all four bullets above behave as expected; the
Developer-mode toggle drives both buttons in lockstep (no half-state
where one is visible and the other isn't).

---

## Step 3 — US2: Real host-side version pull (Clarifications Q1, Q2, Q3, Q4)

**Goal**: confirm the host-detail page renders real vDrive / vREECU /
SEC values pulled from the host, with the manifest cross-check
verdicts, the loading-state spinner, the refresh button, and the
per-cell timestamps.

1. From the main page, navigate to the host-detail page for a
   reachable TS host (e.g. `ts-de-ber-00005`).
2. **Observe the in-flight state** (Clarification Q4):
   - Each of the three version cells renders `—` plus a small
     spinner.
   - No verdict pill, no reason line, no timestamp yet.
   - The response-level source pill at the top of the card reads
     a neutral "Reading from `<host_id>`…" (or similar in-flight
     copy — see `frontend/src/strings.ts`).
3. **Wait up to 10 s for the engine call to complete.** Once it
   does, all three cells flip atomically to their post-load state
   (FR-020).
4. **Verify each post-load state:**
   - Each cell shows a non-em-dash value (unless that field truly
     can't be read on this host — in which case it shows the
     unavailable state, see below).
   - Each cell shows a verdict pill: green "matches manifest",
     amber "drift vs manifest", grey "no manifest to compare", or
     red "couldn't read".
   - Drifted cells show `manifest expects <X>` as a small line
     under the value (FR-006).
   - Unavailable cells show the plain-language reason inline
     (FR-007, e.g. "SEC package not installed on this host").
   - Each cell shows "as of HH:MM:SS" (FR-019).
   - The response-level source pill at the top reads "Live from
     `<host_id>` · as of HH:MM:SS" (green) or "Couldn't reach
     `<host_id>`" (red) per Clarification Q2.
5. **Visual scan test** (SC-005): glance at the page for ≤ 2 seconds
   without reading any small text. You should be able to tell at a
   glance which cells are `match`, which are `drift`, which are
   `unavailable`, purely from pill colour and icon. If you have to
   read the text to disambiguate, FR-010 is not satisfied.
6. **Cache test** (Clarification Q3, SC-007):
   - Navigate away from the host-detail page (e.g. back to the
     main page).
   - Within 30 s, navigate back to the same host-detail page.
   - Expected: the three cells render their previous values
     **instantly** (no spinner, no 10 s wait). The "as of" timestamp
     on each cell remains the original read time, not the re-mount
     time. Re-visit completes well under 500 ms.
7. **Refresh button test** (FR-018):
   - Click the refresh icon at the top-right of the versions card.
   - Expected: the three cells flip back to the loading state
     (spinner + em-dash); the engine is re-invoked; after up to 10 s
     the cells flip back to their (possibly updated) post-load state
     with a new timestamp.
8. **TTL boundary test** (FR-017):
   - Wait 61 s without interacting, then navigate away and back to
     the same host-detail page.
   - Expected: cells flip to loading, engine is re-invoked, fresh
     timestamps appear (cache miss after TTL expiry).
9. **Cross-host independence test** (per-host cache scoping):
   - Visit host A; let it cache.
   - Visit host B (different host); confirm host B triggers its own
     engine call (loading state visible).
   - Return to host A within 60 s of the first visit; confirm host
     A still serves from cache.
10. **Partial-success test** (Clarification Q2): pick a host known
    to have one field that fails — e.g. SEC not installed. Confirm:
    - The unavailable cell shows its plain-language reason.
    - The other cells show their live values with the appropriate
      verdict.
    - The response-level source pill reads `live` (because at least
      one field resolved), not `unavailable`.

**Pass criteria**: every numbered bullet behaves as expected against
the connected testbed.

### Spot-check against the rust CLI (SC-003)

For any host where step 4 reports `drift` on vDrive, run the rust
CLI for the same host:

```bash
ree-debug-cli report --host ts-de-ber-00005 \
  --inventory ~/GitHub/ree-vehicle-configs --json | jq '.checks[] | select(.name | test("vDrive"))'
```

The reported drift status (Pass/Warn/Fail and the embedded `name`
text) MUST match what the host-detail page shows. If they diverge,
US2 has a parser bug — fix `host_versions.py`, not the engine.

---

## Step 4 — US3: API-check battery removal

**Goal**: confirm no trace of the legacy run-checks flow remains.

1. Build the backend and frontend cleanly:
   ```bash
   cd backend && pytest && cd ..
   cd frontend && npm run build && npm run lint && cd ..
   ```
   Expected: no failures, no warnings about unresolved imports.
2. Grep for the deleted symbols:
   ```bash
   grep -rn "from vayobd.checks" backend/ || echo "OK: no imports"
   grep -rn "from vayobd.api.runs" backend/ || echo "OK: no imports"
   grep -rn "api/runs" frontend/src/ || echo "OK: no imports"
   grep -rn "RunResultPage\|ResultHero\|CategoryBadge" frontend/src/ || echo "OK: no refs"
   ```
   Each line must print the "OK" message — zero hits.
3. Start the backend and inspect the route list:
   ```bash
   curl -s http://127.0.0.1:8000/openapi.json | jq -r '.paths | keys[]' | grep -E "^/api/runs"
   ```
   Expected: empty (no path under `/api/runs`).
4. Read the in-repo docs (`README.md`, `quickstart.md`,
   `CLAUDE.md`). Confirm no mention of "Run checks" or
   "diagnostic run" as a battery-of-checks surface.

**Pass criteria**: every step above succeeds; nothing references the
removed namespace.

---

## Step 5 — US4: Readability tweaks

**Goal**: confirm the visual readability improvements landed on the
two surfaces in scope.

1. Open the host-detail page for a host where at least one cell is
   `drift` and one cell is `unavailable` (or open two hosts in
   quick succession to compare).
2. From a normal reading distance, **glance at the page for ≤ 2 s**
   without reading any small text. The colour-coded verdict pills
   and any iconography MUST let you identify which cells are
   "match" / "drift" / "unavailable" — no need to read the cell
   value to disambiguate (FR-010, SC-005).
3. Find the source pill (`Live from <host>` / `Couldn't reach <host>`)
   at the **top** of the versions card, not buried as a small chip in
   a corner (FR-011).
4. For any `unavailable` cell, confirm the reason is rendered as an
   inline line in the cell — not as a tooltip, not as a global
   banner (FR-012, Clarification Q2).
5. For any `no-manifest` field, confirm the `check
   ~/GitHub/system-release-deployment` hint renders inline with the
   affected cell (FR-004 acceptance #5, Edge case "Manifest stale").
6. Toggle Developer mode off, then on. Both TS_diag entry points
   match their respective context's visual weight (FR-013) — the
   main-page button reads as a primary action; the header button
   reads as actionable header chrome (not decorative).

**Pass criteria**: the page communicates state in under two seconds
of glancing without small-text reading; em-dashes never appear bare;
both TS_diag buttons read as actionable controls.

---

## Acceptance-scenario mapping

| Spec section | Quickstart step |
|---|---|
| US1 acceptance #1, #2, #3, #4 | Step 2 |
| US2 acceptance #1, #2, #3 | Step 3 (4) |
| US2 acceptance #4, #5 | Step 3 (4) — pick a host where the relevant condition holds |
| US2 acceptance #6 (partial success) | Step 3 (10) |
| US3 acceptance #1, #2, #3, #4 | Step 4 |
| US4 acceptance #1, #2, #3, #4 | Step 5 |
| SC-001 (entry-point dual visibility) | Step 2 (4) |
| SC-002 (≤10 s real versions) | Step 3 (3) |
| SC-003 (parity with rust CLI) | Step 3 (spot-check) |
| SC-004 (deletion scope) | Step 4 |
| SC-005 (under-2 s visual distinguishability) | Step 5 (2) |
| SC-006 (no run-checks docs) | Step 4 (4) |
| SC-007 (cache-served under 500 ms) | Step 3 (6) |
