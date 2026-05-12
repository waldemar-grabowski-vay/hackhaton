# `strings.ts` Hand-Merge Guide — 008

**Owner**: `frontend/src/strings.ts`
**Phase**: 008 — extended 2026-05-12 from a 2-way to a **3-way merge**
when Ezequiel's `origin/005-ve-harness-repair-guide` work was added
to the integration scope.

This file documents exactly what the merged `strings.ts` looks like
after 008 lands. Future contributors editing the file should not
have to re-derive the merge logic from the spec — this is the
canonical answer.

> **NOTE 2026-05-12**: Sections 1–8 below describe the original 2-way
> merge (post-007 HEAD ↔ pre-007 `HEAD~N`). The 2026-05-12
> clarifications added a **third** input — Ezequiel's branch — so the
> live procedure is the **3-way version in §9**. Sections 1–8 remain
> as background.

---

## 1. Why this file needs a merge

The working tree's `strings.ts` (post-007) is a slimmed-down version
of the pre-007 file. 007 removed:

- `wizard.runButton` (string)
- `runs` (block)
- `outcomes` (block)
- `result` (block)
- `category` (block)
- `guide` (block)
- `item` (block)
- `categoryLabel()` function

And modified:

- `wizard.host.subtitle` — wording changed from "Each tile is one
  machine you can run a check against." to "Each tile is one
  machine you can open."

And added:

- `hostVersions` block (cardTitle, refreshButton, refreshing,
  sourceLive, sourceUnavailable, asOfPrefix, loadingHint,
  verdict labels, expectedPrefix, noManifestHint, field labels)

008 needs:

- Every removed block back (the restored components reference
  them).
- The 007-added `hostVersions` block kept (007's version card
  references it).
- The 007 wording change on `wizard.host.subtitle` REVERTED
  ("Each tile is one machine you can run a check against." comes
  back — the restored run flow needs that phrasing).
- `wizard.runButton` and `categoryLabel()` restored.

Mechanical `git checkout HEAD --` would drop the new `hostVersions`
block and break 007's version card. Hand-merge is the answer.

---

## 2. Merge steps

```bash
# 1. Save the current strings.ts so we can lift the hostVersions block out of it.
cp frontend/src/strings.ts /tmp/strings.post007.ts

# 2. Restore the pre-007 strings.ts from HEAD.
git checkout HEAD -- hackhaton/frontend/src/strings.ts

# 3. Open frontend/src/strings.ts and the saved /tmp/strings.post007.ts
#    side by side. Paste the `hostVersions: { ... }` block from the
#    post-007 file into the restored file, placing it AFTER
#    `inventory` and BEFORE `runs` (keeping the alphabetical-ish
#    grouping the file uses). Comment marker:
#       // 007 host-detail surface — version pulls cross-checked against the manifest.
#       hostVersions: { ... },

# 4. Save the file.
```

After the merge, `frontend/src/strings.ts` is a strict superset:

- Every key the pre-007 file had → present (restored components
  resolve through `t("runs.runButton")` etc. without literal
  path leakage).
- The post-007 `hostVersions` block → present (007's version card
  continues to render).

---

## 3. Verification

```bash
cd frontend
grep -rn 't("' src/ | grep -oP 't\("[^"]+"' | sort -u | head -50
# For each path printed, confirm it resolves to a non-undefined
# value in strings.ts (visually or with a one-liner script).

grep -rn 'strings\.[a-z]' src/ | head -20
# Confirm every direct-property access resolves (e.g. strings.runs.runButton,
# strings.hostVersions.refreshButton, etc.).
```

If any access path doesn't resolve, the merge is missing that key.

---

## 4. Why `wizard.host.subtitle` reverts

007's wording — "Each tile is one machine you can open." —
made sense when the host-detail page was version-only ("opening"
the host just showed a few version cells). After 008 the
host-detail page IS a check run, so the pre-007 wording — "Each
tile is one machine you can run a check against." — is more
accurate again.

This is the one place in 008 where copy reverts to its pre-007
form. Everything else 007 worded better stays.

---

## 5. The `categoryLabel()` function

```ts
export function categoryLabel(category: string): string {
  return (strings.category as Record<string, string>)[category] ?? category;
}
```

Restored alongside the `category` block. Consumers: the restored
`CategoryBadge` component (which the result groups use to render
the five-category palette).

The 007 strings.ts removed both because there were no consumers
post-007. The restoration brings the consumers back, so the
function comes back too.

---

## 6. What MUST NOT be re-added

The 007 deletions removed cruft — these aren't worth restoring:

- The `// removed:` style comments on old keys.
- Any duplicate string keys 007 already de-duped.

If `git checkout HEAD --` brings any of those back into the merged
file, drop them in the merge.

---

## 7. Post-merge tests

```bash
cd frontend
npm run build       # MUST succeed — restored components import strings keys
npm run lint        # MUST exit zero (007's --max-warnings=0 setting still applies)
```

If either fails because of strings.ts, the merge needs another
iteration. The Playwright e2e specs from 007
(`live-diagnostic-entry.spec.ts`, `host-detail-versions.spec.ts`)
must also continue to pass.

---

## 8. Future-proofing

Once the merge lands, `strings.ts` becomes the single source of
truth for every visible string across BOTH 007's version card AND
the restored battery. Future features adding new copy should
extend it the same way — add a new top-level block with a clear
comment marker, don't fork or duplicate.

---

## 9. 3-way merge (live procedure, 2026-05-12)

Per the 2026-05-12 clarification round, the merge now has three
inputs:

| Source | Where | Contributes |
|---|---|---|
| post-007 HEAD | working tree at 008 start | `hostVersions` block, refresh keys, dev-mode keys, all 007 wording adjustments. **Wins all key collisions.** |
| Ezequiel's branch | `origin/005-ve-harness-repair-guide:hackhaton/frontend/src/strings.ts` | +107 lines of harness / repair-guide / library copy. |
| Pre-007 HEAD~N | `01d3979:hackhaton/frontend/src/strings.ts` | `runs / outcomes / result / category / guide / item` blocks; `categoryLabel()`; the `wizard.host.subtitle` original wording. |

**Merge rule**: union of all three; on any key collision, post-007
HEAD wins.

### 9a. Step-by-step

```bash
# Snapshot all three inputs.
cp hackhaton/frontend/src/strings.ts /tmp/strings.post007.ts
git show 01d3979:hackhaton/frontend/src/strings.ts > /tmp/strings.pre007.ts
git show origin/005-ve-harness-repair-guide:hackhaton/frontend/src/strings.ts \
  > /tmp/strings.ezequiel.ts

# Start from Ezequiel's file (it has the most additive content).
git checkout origin/005-ve-harness-repair-guide -- \
  hackhaton/frontend/src/strings.ts

# Now hand-edit, in order:
#   (a) Layer in the hostVersions block from /tmp/strings.post007.ts.
#       Place it AFTER `inventory` and BEFORE any 007-or-later block.
#       Marker comment:
#         // 007 host-detail surface — version pulls cross-checked against the manifest.
#       hostVersions: { ... },
#
#   (b) Layer in the pre-007 blocks from /tmp/strings.pre007.ts:
#       runs, outcomes, result, category, guide, item — verbatim, plus
#       the categoryLabel() function. Place them in the same order they
#       had pre-007.
#
#   (c) Resolve `wizard.host.subtitle`: take the pre-007 wording
#       ("Each tile is one machine you can run a check against."),
#       per §4.
#
#   (d) For every other key that exists in BOTH /tmp/strings.post007.ts
#       AND the working tree (now a mix of Ezequiel + pre-007 reads),
#       confirm the working-tree value matches post-007. If it doesn't,
#       overwrite with the post-007 value (HEAD wins on collision).
```

### 9b. Verification — three queries

```bash
cd hackhaton/frontend

# Build + lint
npm run build && npm run lint

# (i) Every key Ezequiel introduced is still present after the merge:
diff <(jq -r 'paths | join(".")' < /tmp/strings.ezequiel.json) \
     <(jq -r 'paths | join(".")' < src/strings.json) \
  | grep '^<' || echo "OK: all Ezequiel keys present"
# (jq invocation is illustrative; the file is .ts, not .json — adapt to
#  a TS-AST script or grep-based check at task time.)

# (ii) Every key post-007 HEAD had is still present:
# (similar diff against /tmp/strings.post007.ts)

# (iii) Every pre-007 block is back:
# (similar diff against /tmp/strings.pre007.ts)

# Final dom check: no literal path keys leak (SC-004):
npx vite build
grep -rE 'strings\.[a-z]+\.' dist/ | head || echo "OK: no path keys"
```

### 9c. Failure modes and recovery

- **A key collides and the working tree has Ezequiel's value, not HEAD's**:
  per the rule, HEAD wins. Fix by editing the working tree to match
  HEAD's value.
- **A restored component (`<CategoryBadge>` etc.) throws "undefined string"**:
  one of the pre-007 blocks didn't get unioned in. Re-run step (b).
- **Build error "Cannot find name `hostVersions`"**: step (a) didn't
  land. The block must exist at the top level of the strings object.
- **Lint error on the merged file**: `npm run lint -- --max-warnings=0`
  is still enforced. Typical cause: trailing commas, duplicate keys.
  Run the linter's `--fix` then re-verify.

### 9d. Same rule extended to three sibling files

Per `contracts/ezequiel-cherry-pick.md` §B, three other files have
the same 3-way merge pattern:

| File | post-007 HEAD owns | Ezequiel adds | Pre-007 restores |
|---|---|---|---|
| `connectorLocations.ts` | _verify; expected none_ | +86 VE-side connector locations | — |
| `connectorSpecs.ts` | _verify; minimal_ | +863 VE connector specs | — |
| `guides.ts` | _verify none — orphan in HEAD_ | +763 guide entries | — |

For these three, the pre-007 column is empty (007 didn't delete
their content — `guides.ts` was orphaned but not deleted; the other
two are stable). So the merge collapses to the 2-way variant: take
Ezequiel's file, then re-introduce any post-007 HEAD edits if they
exist.

Confirm the post-007 HEAD edit list per file before merging:

```bash
for f in \
  hackhaton/frontend/src/connectorLocations.ts \
  hackhaton/frontend/src/connectorSpecs.ts \
  hackhaton/frontend/src/guides.ts
do
  echo "--- $f ---"
  git log --oneline 01d3979..HEAD -- "$f"
done
```

If the log shows no commits for a file → clean Ezequiel-replace is
safe. Otherwise, diff and hand-reconcile.
