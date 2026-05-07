# Tasks: Frontend SUN Color Palette Rebrand

**Input**: Design documents from `/specs/002-sun-theme-palette/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, contracts/color-tokens.md ✓, quickstart.md ✓

**Tests**: No test suite exists in the project; no test tasks generated.

**Organization**: Tasks grouped by user story. The entire implementation targets a single file: `hackhaton/frontend/src/theme/globals.css`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)

---

## Phase 1: Setup

**Purpose**: Confirm the development environment is running and baseline is understood.

- [x] T001 Start the frontend dev server (`npm run dev` in `hackhaton/frontend/`) and confirm the app loads at http://localhost:5173 with the current teal/cyan palette visible

---

## Phase 2: Foundational (Token Updates)

**Purpose**: Apply the SUN palette token values in `globals.css`. Both tasks target the same file but different CSS rule blocks — complete T002 before T003 to avoid conflicts.

**⚠️ CRITICAL**: Both token changes must be complete before user story verification can begin.

Reference: `specs/002-sun-theme-palette/contracts/color-tokens.md` for exact before/after values.

- [x] T002 Update light mode tokens in the `:root` block of `hackhaton/frontend/src/theme/globals.css`: set `--primary: 17 48% 57%`, `--primary-foreground: 0 30% 22%`, `--accent: 17 48% 57%`, `--accent-foreground: 0 30% 22%`, `--ring: 17 48% 57%`
- [x] T003 Update dark mode tokens in the `.dark` block of `hackhaton/frontend/src/theme/globals.css`: set `--primary: 17 55% 62%`, `--primary-foreground: 24 20% 8%`, `--accent: 17 55% 62%`, `--accent-foreground: 24 20% 8%`, `--ring: 17 55% 62%`

**Checkpoint**: Token values updated — dev server hot-reload should reflect the new warm terracotta immediately.

---

## Phase 3: User Story 1 — View Application in SUN Theme (Priority: P1) 🎯 MVP

**Goal**: End user opens the app and all primary UI elements (buttons, links, active states, focus rings) render in the SUN warm terracotta palette in both dark and light modes.

**Independent Test**: Load the app in a browser, confirm primary buttons are terracotta (not teal), toggle dark/light mode via DevTools, confirm both modes display the warm palette.

### Implementation for User Story 1

- [ ] T004 [US1] With dev server running in dark mode (default), visually verify primary buttons and interactive elements display warm terracotta (`hsl(17, 55%, 62%)`) instead of teal — open `http://localhost:5173` and inspect with browser DevTools
- [ ] T005 [US1] Switch to light mode by removing the `.dark` class from `<html>` in DevTools and verify primary elements show the lighter terracotta (`hsl(17, 48%, 57%)`) with dark foreground text
- [ ] T006 [US1] Tab through interactive elements using keyboard navigation and confirm focus rings render in SUN terracotta (not teal) in both dark and light modes
- [ ] T007 [US1] Confirm gradient text (`.gradient-text` utility class in `hackhaton/frontend/src/theme/globals.css`) renders in warm tones — if used in the app, it should flow from terracotta to accent

**Checkpoint**: User Story 1 complete — all primary interactive elements display consistent SUN warm terracotta in both modes.

---

## Phase 4: User Story 2 — Consistent Visual Identity Across All Screens (Priority: P2)

**Goal**: Every screen and overlay in the application consistently displays the SUN palette — no screen retains the old teal/cyan color scheme.

**Independent Test**: Navigate through all application routes; open any dialogs/modals/tooltips — zero teal/cyan accent colors visible anywhere.

### Implementation for User Story 2

- [ ] T008 [US2] Navigate to the Picker page (`/`) and verify no teal/cyan accent colors appear in any component (cards, badges, buttons, navigation)
- [ ] T009 [US2] Navigate to the Run Result page and verify result groups, status badges, and hero elements use SUN terracotta tones with no teal/cyan remnants
- [ ] T010 [US2] Trigger any dialogs, tooltips, or toast notifications (e.g., via the wizard components) and confirm they render in the SUN palette
- [ ] T011 [US2] Verify the `RunningState`, `EmptyInventoryState`, `PartialRunState`, and `UnreachableState` components in `hackhaton/frontend/src/components/states/` display without any residual teal/cyan accents
- [ ] T012 [US2] Confirm the `AppHeader` (`hackhaton/frontend/src/components/chrome/AppHeader.tsx`) and any navigation chrome display in the SUN palette

**Checkpoint**: All screens verified — full visual consistency achieved across the application.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Accessibility and final quality gate.

- [ ] T013 [P] Use browser DevTools accessibility checker or contrast tool on a primary button in light mode to confirm text contrast ratio meets 4.5:1 (dark foreground `hsl(0, 30%, 22%)` on SUN background `hsl(17, 48%, 57%)`)
- [ ] T014 [P] Verify semantic status colors remain unaffected: trigger an error state and confirm it still renders red (`--destructive`), trigger a success state and confirm it still renders green (`--success`), trigger a warning and confirm amber (`--warning`)
- [x] T015 Perform a final grep of the compiled/running app CSS to confirm no `196` hue value (the old teal hue) remains in any primary/accent/ring property — run: `grep "196" hackhaton/frontend/src/theme/globals.css` and expect zero matches on primary/accent/ring lines

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (dev server must be running to observe changes)
- **User Stories (Phase 3 & 4)**: Both depend on Phase 2 completion (token updates must be in place)
  - US1 (Phase 3) and US2 (Phase 4) can be verified in parallel once Phase 2 is done
- **Polish (Phase 5)**: Depends on Phase 3 + Phase 4 completion

### User Story Dependencies

- **User Story 1 (P1)**: Start after Phase 2 — no dependency on US2
- **User Story 2 (P2)**: Start after Phase 2 — no dependency on US1, but verifying US1 first provides a useful mental baseline

### Within Each Phase

- T002 before T003 (same file, sequential edits to different blocks)
- T004–T007 can be done in any order after T002+T003 complete
- T008–T012 can be done in any order after T002+T003 complete
- T013, T014 can run in parallel; T015 runs last as final gate

### Parallel Opportunities

- Once T002 + T003 are done, all of T004–T012 can be addressed in any order
- T013 and T014 (polish checks) can run in parallel

---

## Parallel Example: After Phase 2

```text
# Once T002 + T003 complete, launch verification in any order:
Task T004: Dark mode button colour check
Task T005: Light mode colour check
Task T008: Picker page cross-screen verification
Task T009: Run Result page verification
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1: Start dev server (T001)
2. Complete Phase 2: Update CSS tokens (T002, T003)
3. Complete Phase 3: Verify primary elements in both modes (T004–T007)
4. **STOP and VALIDATE**: Primary palette change is live and correct
5. Ship or demo if ready

### Full Delivery

1. Complete MVP above
2. Add Phase 4: Cross-screen consistency check (T008–T012)
3. Add Phase 5: Accessibility + final gate (T013–T015)
4. All done — no legacy teal/cyan remains anywhere

---

## Notes

- All implementation work touches exactly one file: `hackhaton/frontend/src/theme/globals.css`
- `tailwind.config.ts` requires no changes — it reads from CSS vars via `hsl(var(--))`
- No data entities, no API contracts — contracts/ contains the color token mapping only
- Verify with browser DevTools; no automated test infrastructure exists
- Commit after T003 (token change complete) as a clean, minimal diff
