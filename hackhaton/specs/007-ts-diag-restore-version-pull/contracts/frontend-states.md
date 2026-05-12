# Frontend State Contract — Per-cell rendering on the host-detail page

**Owner**: `frontend/src/pages/HostDetailPage.tsx`
**Phase**: 007 — captures the visual contract for each
`VersionField` state so the page reads cleanly at a glance (FR-010,
SC-005).

This file is the single source of truth for how the page renders
each combination of `verdict` × loading state. Implementation MUST
match this table exactly; visual regressions are tested via the
Playwright spec `host-detail-versions.spec.ts`.

---

## State matrix per cell

| State | Trigger | Value cell | Verdict pill | Reason / expected line | Timestamp |
|---|---|---|---|---|---|
| `loading` | React Query in-flight (mount, refresh, TTL miss) | `—` + spinner | hidden | hidden | hidden |
| `match` | Response, verdict = `match` | live value (e.g. `R12.3.0`) | green pill "matches manifest" | hidden | "as of HH:MM:SS" small text |
| `drift` | Response, verdict = `drift` | live value, **rendered with a warning marker** (icon + amber tint) | amber pill "drift vs manifest" | small line "manifest expects `<expected>`" | "as of HH:MM:SS" |
| `no-manifest` | Response, verdict = `no-manifest` | live value | grey pill "no manifest to compare" | small line "check `~/GitHub/system-release-deployment`" | "as of HH:MM:SS" |
| `unavailable` | Response, verdict = `unavailable` | `—` (no spinner) | red pill "couldn't read" | small line with `reason` (plain language) | "as of HH:MM:SS" — the read time, even though we got nothing |

The three pills use the existing sun-theme palette (002) — no new
colour tokens. Specifically:
- green → `--ok` (matches existing successful-check pills)
- amber → `--warn` (matches existing drift / partial pills)
- grey  → `muted-foreground` border on a neutral bg
- red   → `--fail` (matches existing reachability-failure pills)

---

## Source pill (response-level)

A single response-level `source` pill sits at the top of the
versions card, **above** the three cells (not in a corner — FR-011):

| `source` | Rendered text | Pill colour |
|---|---|---|
| `live` (any field resolved) | "Live from `<host_id>` · as of HH:MM:SS" | green |
| `unavailable` (all fields unavailable) | "Couldn't reach `<host_id>`" | red |

This pill is the operator's at-a-glance summary; the per-cell
pills below disambiguate the per-field details (Clarification Q2).

---

## Refresh affordance

A single icon-button (refresh arrow icon, no label by default — use
the `<RefreshCw>` lucide icon already imported elsewhere) sits in the
top-right of the versions card.

| Sub-state | Visual |
|---|---|
| idle | enabled, default styling |
| pressed (in-flight) | disabled, icon spins |
| just-completed | enabled, brief 1 s "updated" tooltip auto-dismissed |

Clicking the button triggers a `GET /api/host/<id>/versions?fresh=true`
via React Query. The query key includes `{ fresh: true }` so React
Query treats it as a separate inflight from the cached read. While
the fresh request is in flight, the three cells flip back to
`loading` state — clarifies to the operator that values are being
re-read.

---

## Loading-state details (FR-020)

While any of the three cells are in `loading`:

- Cell value renders as the em-dash character (`—`, U+2014).
- Adjacent to the em-dash, the existing `<Loader2 />` icon
  (`lucide-react`) spins at 16 px.
- Verdict pill, reason line, and timestamp are all hidden (not
  rendered as empty placeholders — full collapse to keep visual
  noise low).
- When the response lands, ALL three cells flip atomically within
  one React render — no per-cell progressive reveal that could be
  read as "still loading" when the others are already done.

The "atomic flip" requirement maps directly to React Query's
single-`data` handoff: the page reads `data?.versions` and either
all three cells render their post-load state, or all three remain
in `loading`.

---

## Out-of-scope visual contracts (intentional)

- **No skeleton shimmer** — the user picked spinner + em-dash in
  Clarification Q4 explicitly.
- **No animated value transitions** when a cell flips from `loading`
  to `match` or `drift`. The transition is a single render; no
  cross-fade.
- **No tooltips that hide the reason text.** All
  `reason` / `expected` strings are visible in the cell, not behind
  a hover affordance — Principle III and FR-006 require side-by-side
  rendering.

---

## TS_diag entry-point states

`LiveDiagnosticButton` and the new `PickerPage` mount of the same
component share a state contract:

| Developer-mode toggle | `/api/health` (capability probe) | Rendered? |
|---|---|---|
| off | (any) | NO (both copies hidden) |
| on | reachable, `live_diagnostic.enabled` field present | YES (both copies, identical styling per FR-013) |
| on | reachable, `live_diagnostic` block missing | YES (button visible — backend just doesn't think the gate matters; the per-component readiness check on `/live` itself owns failure UI) |
| on | unreachable (network down, backend dead) | YES (button visible; the /live surface will surface the unreachable state via its own connection dialog) |

The button is rendered whenever the UI toggle is on. The backend
flag has been demoted from "gate" to "informational" — see research
§3 for the bug-driven rationale.
