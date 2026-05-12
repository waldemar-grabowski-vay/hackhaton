# Ezequiel Cherry-Pick — Exact Source Map

**Owner**: `/speckit-tasks` will generate one task per row in the
tables below. The tables are the source of truth for which file
comes from which source.
**Phase**: 008 — implements the 2026-05-12 clarifications Q1 / Q2 / Q3 / Q4.

## A. Direct cherry-pick from `origin/005-ve-harness-repair-guide`

These files are copied **verbatim** from Ezequiel's branch (no
hand-edit). Use `git checkout origin/005-ve-harness-repair-guide -- <path>`
per file. Ezequiel's branch has unrelated backend deletions in the
same commits, so a clean `git cherry-pick` of his merge commit is
**not** appropriate — file-scoped checkout is.

### A.1 Improved replacements of existing files

| Path | Replaces (HEAD) | Why Ezequiel's wins |
|---|---|---|
| `frontend/src/components/result/HarnessDiagram.tsx` | yes | True splice branching; correct H/L wire colours per connector. |
| `frontend/src/components/result/RepairGuideSheet.tsx` | yes | +94 lines: connector-chip routing, harness-tab auto-switch, locate-connector animation. |
| `frontend/src/components/result/TelestationDiagram.tsx` | yes | Minimal +3 — keeps parity with HarnessDiagram. |

### A.2 Net-new (no HEAD counterpart)

| Path | Role |
|---|---|
| `frontend/src/components/chrome/RepairGuideLibraryDialog.tsx` | Library entry dialog (open from chrome). |
| `frontend/src/pages/RepairGuidesPage.tsx` | Top-level repair-guide library page (`/repair-guides`). |
| `frontend/src/guideLibrary.ts` | Index over `guides.ts`; drives library listing. |
| `frontend/public/ve-pigtail-f61-harness.jpg` | VE harness asset. |
| `frontend/public/ve-reebox-power-cable-harness.jpg` | VE harness asset. |
| `frontend/public/ve-vs040815-harness-p1.png` | VE harness asset. |
| `frontend/public/ve-vs040815-harness.pdf` | VE harness asset (PDF for hi-res). |

### A.3 Frontend pre-007 deletions, recovered

These files were deleted by 007 from the local HEAD but **still
exist on Ezequiel's branch** (his fork base predates 007). One
consistent FE source per Q4 of the 2026-05-12 clarifications.

| Path |
|---|
| `frontend/src/api/runs.ts` |
| `frontend/src/components/result/CategoryBadge.tsx` |
| `frontend/src/components/result/DiagnosticItemRow.tsx` |
| `frontend/src/components/result/ResultGroup.tsx` |
| `frontend/src/components/result/ResultHero.tsx` |
| `frontend/src/components/states/EmptyInventoryState.tsx` |
| `frontend/src/components/states/PartialRunState.tsx` |
| `frontend/src/components/states/RunningState.tsx` |
| `frontend/src/components/states/UnreachableState.tsx` |
| `frontend/src/components/motion/StaggeredList.tsx` |
| `frontend/src/pages/RunResultPage.tsx` |

## B. 3-way merge (do NOT clobber HEAD)

Per Q2 of the 2026-05-12 clarifications, these files have legitimate
edits in all three sources. The merge rule is: **post-007 HEAD wins
on key collision; otherwise the union of all three**.

| Path | post-007 HEAD owns | Ezequiel adds | Pre-007 restores |
|---|---|---|---|
| `frontend/src/strings.ts` | `hostVersions` block; refresh keys; dev-mode keys | `+107` (harness / guide / library copy) | `runs / outcomes / result / category / guide / item` blocks; `categoryLabel()` |
| `frontend/src/connectorLocations.ts` | _verify; expected none_ | `+86` VE-side connector locations | — |
| `frontend/src/connectorSpecs.ts` | _verify; minimal_ | `+863` VE connector specs | — |
| `frontend/src/guides.ts` | _verify none — orphan in HEAD_ | `+763` guide entries | — |

`contracts/strings-merge.md` is the per-file hand-merge guide. The
implementation pattern per merge file:

```bash
git checkout origin/005-ve-harness-repair-guide -- <path>
# Then hand-edit to re-introduce post-007 HEAD blocks.
# Pre-007 blocks come from `git show HEAD~N:<path>` where HEAD~N is
# the most recent commit that had the deleted blocks intact.
```

## C. Route registration delta

| Path | Action |
|---|---|
| `frontend/src/App.tsx` | Add the route delta Ezequiel introduces: `/repair-guides` → `RepairGuidesPage`. Hand-edit (Ezequiel's branch has unrelated chrome changes here). |

## D. Backend (NOT from Ezequiel — from local 01d3979)

Per Q4 of the 2026-05-12 clarifications, Ezequiel's branch backend /
engine code is **stale** (his fork predates recent pushes). These
files restore from `git checkout 01d3979 -- <path>`, NOT from his
branch.

| Path |
|---|
| `backend/src/vayobd/api/runs.py` |
| `backend/src/vayobd/checks/__init__.py` |
| `backend/src/vayobd/checks/catalog.py` |
| `backend/src/vayobd/checks/executor.py` |
| `backend/src/vayobd/checks/peplink.py` |
| `backend/src/vayobd/checks/ree_cli.py` |
| `backend/src/vayobd/checks/runner.py` |
| `backend/tests/integration/test_runs_endpoint.py` |
| `backend/tests/unit/test_catalog.py` |

## E. Engine (NOT from Ezequiel — from local 01d3979)

| Path |
|---|
| `engine/ree-debug-engine/src/checks/cameras.rs` |
| `engine/ree-debug-engine/src/checks/connectivity.rs` |
| `engine/ree-debug-engine/src/checks/decode.rs` |
| `engine/ree-debug-engine/src/checks/mod.rs` |
| `engine/ree-debug-engine/src/checks/reecu.rs` |
| `engine/ree-debug-engine/src/checks/usb.rs` |

## F. Explicitly NOT carried over from Ezequiel's branch

These would silently regress 006 / 007 work and are excluded by the
cherry-pick scope:

| Path on Ezequiel's branch | Why excluded |
|---|---|
| `backend/src/vayobd/api/host_versions.py` (deleted) | FR-008 requires keeping 007's version-pull surface. |
| `backend/src/vayobd/_internal/version_cache.py` (deleted) | FR-008 — 60 s TTL cache must stay. |
| `backend/src/vayobd/api/refresh.py` (deleted) | FR-008 — refresh affordance must stay. |
| `backend/src/vayobd/install/*.py` (deleted) | 006 install workflow. |
| `backend/src/vayobd/cli.py` (deleted) | 006 packaging CLI. |
| `backend/src/vayobd/{app,models,config,settings_file}.py` (modified) | Modifications on his stale base would regress 006 / 007. |
| `backend/src/vayobd/live/{candump_runner,dbc_decoder,session,ws_router}.py` (modified) | Same — 004 / 007 work is more recent. 008 modifies these files directly per research §1 + §10. |
| `backend/tests/conftest.py` (modified) | Same — stale base. |
| `backend/tests/fixtures/engine_reports/*.json` (deleted) | 007 added these; need them for tests. |
