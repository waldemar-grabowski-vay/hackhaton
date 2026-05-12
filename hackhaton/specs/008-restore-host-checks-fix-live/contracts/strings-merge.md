# `strings.ts` Hand-Merge Guide — 008

**Owner**: `frontend/src/strings.ts`
**Phase**: 008 — the only file in the restoration that needs a manual
merge instead of a clean `git checkout HEAD --`.

This file documents exactly what the merged `strings.ts` looks like
after 008 lands. Future contributors editing the file should not
have to re-derive the merge logic from the spec — this is the
canonical answer.

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
