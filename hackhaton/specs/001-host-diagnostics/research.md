# Phase 0 Research — Remote Host Diagnostics

This document resolves the open implementation questions left by `spec.md`
and `plan.md`, using the format Decision / Rationale / Alternatives.

---

## R1. How does the app reach a remote host to run a check?

**Decision**: Define an `Executor` interface in
`backend/src/vayobd/checks/executor.py` with two implementations selected
at startup by configuration:

- `FixtureExecutor` — reads canned per-host fixture YAML from
  `backend/tests/fixtures/runs/<host_id>.yaml`. Used in development, in CI,
  and for the hackathon demo when no live host is reachable.
- `SshExecutor` — uses `asyncssh` with key-based authentication, host key
  fingerprints loaded from a configured known-hosts file. Connects per-run,
  executes a small set of probe commands defined by the host class, and
  returns structured results.

The default in development is `FixtureExecutor`. The default in production
is `SshExecutor`. Selection is one config flag (`VAYOBD_EXECUTOR`) — no
runtime branching outside startup.

**Rationale**:
- Honours Constitution II (Ship Fast): the fixture path lets the rest of
  the app — picker, wizard, two-mode UI, inventory sync — be built and
  demoed even when no real vehicle is on the network.
- Keeps the live execution path simple and small: SSH + a list of
  `(item_name, command, parser)` tuples per host class. No agent to deploy,
  no daemon to maintain.
- Avoids inventing a new RPC protocol for the hackathon.

**Alternatives considered**:
- *Pre-installed agent on the host* — rejected: another moving part, plus a
  deployment step against vehicles which is out of scope for this feature.
- *HTTP probe endpoint on the host* — rejected: same problem; assumes a
  service we haven't built. Also less natural for CAN/USB introspection,
  which is best done with shell-level commands.
- *Pure simulation (no SSH path at all in v1)* — rejected: the spec is
  about diagnosing real hosts. A simulation-only v1 would be a demo, not a
  feature.

**Open follow-up (not blocking v1)**: The exact commands per host class
are defined in `R3` below.

---

## R2. How is the local inventory cached and refreshed?

**Decision**:
- Treat `ree-vehicle-configs` as a git repository cloned to a configurable
  local path (default `~/.cache/vayobd/ree-vehicle-configs`).
- Refresh = `git fetch && git reset --hard origin/<configured-branch>`,
  shelled out via `subprocess.run` with a hard timeout. No GitPython
  dependency; the operation is small enough that shelling out is simpler
  and easier to reason about.
- Refresh triggers:
  1. Once on backend startup (FR-016).
  2. On `POST /api/inventory/refresh` (FR-017).
  3. On a periodic background scheduler running inside the FastAPI
     process (`asyncio` task). Default cadence 30 minutes when the last
     attempt succeeded.
- **Refresh failure handling (FR-027)**: when a scheduled or manual
  refresh fails *and a non-empty cached copy already exists*, the cache
  is left untouched and the scheduler switches to **exponential
  backoff** for retries: base interval 30 s, multiplier 2, ceiling 5
  minutes (e.g., 30 s → 60 s → 2 min → 4 min → 5 min cap). The
  scheduler returns to the normal 30-minute cadence on the next
  successful refresh. A counter `consecutive_failed_refreshes` is
  incremented on each failure and zeroed on success; this counter is
  surfaced in `InventoryMeta` (see `data-model.md`) so the frontend can
  render the FR-027 warning banner once it crosses the configurable
  threshold (default 3). Manual `POST /api/inventory/refresh` remains
  available throughout and counts the same way — a manual success
  resets the counter.
- Refresh failures with **no usable cached copy** still surface as the
  FR-019 blocking message at the API boundary (HTTP 503 from
  `GET /api/inventory`).
- Inventory **filtering**: the loader drops every host whose filename
  prefix is not `ve-de-` or `ts-de-` (Clarification 2026-05-07 — DE-only
  scope). US/Belgium/other regions never reach the API surface; the
  Country wizard step's "United States (Coming soon)" tile is a static
  frontend affordance, not data flowing from the inventory.

**Rationale**:
- Constitution I (Simplicity First): one moving part — a local git
  checkout. Familiar to anyone on the team.
- FR-027 backoff strategy keeps transient network blips silent (matches
  the operator's "tool that works when other things are broken"
  expectation) while still telling them honestly when the source has
  been unreachable for several attempts.
- Filtering at load time (not request time) means the API is
  unconditionally DE-only — no per-request defensive checks scattered
  across endpoints.

**Alternatives considered**:
- *rsync from a snapshot server* — rejected: requires a snapshot server we
  don't have.
- *Tarball download from a release artefact* — rejected: needs a release
  pipeline; git pull is what the team already does manually.
- *Live read on every request* — rejected: violates FR-015 (offline
  tolerance) and adds latency to picker render.
- *Filter at API/serialisation time instead of load time* — rejected:
  forces every endpoint and every test to repeat the country guard, and
  the eventual "add US back" amendment becomes a search-and-replace in
  multiple places instead of one config change.

---

## R3. Which concrete diagnostic items run per host class?

> Only `ve-de-*` and `ts-de-*` hosts reach the catalog in v1
> (Clarification 2026-05-07). The catalog itself is host-class-keyed and
> remains region-agnostic, so re-enabling US later is a one-line config
> change in the loader, not a catalog change.


**Decision**: Define an explicit, code-reviewed catalog per host class in
`backend/src/vayobd/checks/catalog.py`. v1 ships with the three categories
the spec called out (CAN, USB, Configuration) realised as the following
items. The catalog is a Python module (a `dict[HostClass, list[CheckSpec]]`),
not a config file, because the parsing logic lives next to it and the
hackathon doesn't need pluggability.

**Vehicle host class — initial check set:**

| Operator-visible name | Category | Probe (live executor) |
|---|---|---|
| Main CAN bus reachable | Communication | `cansend` smoke + `candump -n 1 can0` returns within timeout |
| Expected front camera connected | Hardware | `lsusb` matches the camera ID declared in the host's YAML |
| Expected left/right cameras connected | Hardware | Same as above per side |
| Vehicle integration config valid | Configuration | YAML parse + required-key check on the deployed config file |
| Network addresses reachable | Communication | `ping` against the `network.ve_addresses` declared in the host's YAML |

**Telestation host class — initial check set:**

| Operator-visible name | Category | Probe (live executor) |
|---|---|---|
| Display surface reachable | Communication | TCP connect on the configured display port |
| Expected input devices connected | Hardware | `lsusb`/`evtest` matches declared input device IDs |
| Telestation config valid | Configuration | YAML parse + required-key check |

**Rationale**:
- Item names map directly to what an operator can act on in the field
  (FR-005 recommended-next-action). Categories map to the plain-language
  labels in FR-010.
- Anchoring the probes in the host's *own* YAML in `ree-vehicle-configs`
  (camera IDs, network addresses, etc.) means each item's "expected vs
  actual" is grounded in a source the team already maintains — no
  duplicate registry of "what should be on this car".
- Listing the catalog by operator-visible name in the plan makes it
  reviewable today and gives `/speckit-tasks` a concrete enumeration to
  generate test data and Playwright fixtures from.

**Alternatives considered**:
- *Plugin model (each check is a discoverable Python entry-point)* —
  rejected: more machinery than v1 needs; defer to the day a third
  contributor wants to add a check from outside this repo.
- *Config-driven catalog (YAML defines the checks)* — rejected: every
  check has a Python parser anyway; the YAML would be a lookup table that
  duplicates what the code already encodes.
- *Reuse `ree-vehicle-configs` Ansible playbooks as the catalog* —
  attractive but out of scope: Ansible execution semantics differ from a
  point-in-time diagnostic and would re-introduce the "what is happening
  underneath" complexity the constitution explicitly hides from
  operators.

---

## R4. How is authentication and authorization handled?

**Decision**: The app process **assumes** an upstream reverse proxy
performs Vay corporate SSO and forwards an authenticated identity in a
trusted header (`X-Vay-User`). The app reads the header for two
purposes:

1. **Run persistence keying (FR-026)**: every persisted run lives at
   `~/.cache/vayobd/runs/<operator>/<host_id>.json`. The directory
   segment is the proxy-supplied identity, sanitised (lowercased,
   non-`[a-z0-9._-]` characters stripped). One operator's runs are
   unreachable through any API surface another operator hits.
2. **Structured logging / audit**: every executed run logs a structured
   line including the triggering operator (the `triggered_by` field
   internal to the persisted record).

The app does NOT gate access to specific hosts in v1 — every
authenticated operator can trigger a run on every in-scope host.
Developer mode is a UI affordance, not an authorization boundary.

If `X-Vay-User` is missing or empty, the API returns HTTP 401 — the
app process refuses to fall back to a synthetic "anonymous" operator,
both because that would silently violate FR-026's per-operator scoping
and because in production the proxy is contractually expected to set
this header.

**Rationale**:
- Spec assumption already says auth is handled by existing internal SSO
  and is out of scope for the feature spec. This plan honours that.
- Constitution II (Ship Fast): no per-host RBAC in v1.
- FR-026 made the operator identity load-bearing for persistence
  scoping — it is no longer "for logs only", so refusing to operate
  without the header is the safer default.
- Putting SSO at the proxy is the project-typical pattern at Vay and
  means this app stays unaware of OIDC / SAML / cookie internals.

**Alternatives considered**:
- *Per-host role-based access* — rejected for v1: requires a role mapping
  registry the team doesn't have and the hackathon doesn't need. Easy to
  add later without breaking the API shape.
- *In-app session login* — rejected: reinvents what corp SSO already
  does.
- *Default to a synthetic "anonymous" operator when the header is
  missing* — rejected: would collapse all dev-time runs into one shared
  bucket and silently undermine FR-026; instead, the dev environment
  documents how to set the header (see `quickstart.md`).

---

## R5. How is the in-progress run modelled, given FR-024 (wait-only, no cancel, no background) and FR-025 (30 s hard timeout)?

**Decision**:
- `POST /api/runs` is a synchronous request that does not return until
  the run terminates (complete / partial / unreachable / timeout).
- **Server-side hard timeout: 30 s** (FR-025, Clarification
  2026-05-07). Implemented via `asyncio.wait_for(run_coro, timeout=30)`
  in `checks/runner.py`. On expiry the run is cancelled, the per-host
  lock is released, and the response is shaped as
  `outcome: "timeout"` with `items: []` and a populated `started_at` /
  `completed_at` pair.
- The frontend shows a generic "Running checks against `<host>`…"
  spinner while the request is in flight (FR-009) and after a soft
  threshold (default 15 s, configurable) swaps in a "this is taking
  longer than usual" hint. The hard 30 s ceiling is the request
  timeout; the frontend's request timeout is set slightly above (35 s)
  so the server's structured timeout response always wins over a
  client-side abort.
- Concurrency lock (FR-011): an in-memory `asyncio.Lock` keyed by
  `host_id`. A second `POST /api/runs` for a host that already has a
  run in flight returns HTTP 409 with a
  `{"error": "run_in_progress"}` body; the frontend disables the
  "Run check" button while a run is active and surfaces a toast
  defensively if the 409 still arrives.
- FR-011's "same operator" wording is preserved because in v1 cross-
  operator concurrent runs against the same host are not constrained
  (each operator's results are persisted to a separate path-segment per
  R4/FR-026, so they do not collide). The in-memory `host_id` lock is
  intentionally stricter than FR-011 requires — locking globally on
  `host_id` is simpler than locking per `(host_id, operator)` and
  prevents two operators from racing the same SSH endpoint, which is
  the actually-bad outcome.

**Rationale**:
- Synchronous request = simplest possible state machine. No queue, no
  WebSocket, no SSE, no background worker.
- An in-memory lock is sufficient because v1 is a single-process
  backend.
- 30 s is comfortably under any reverse-proxy idle timeout and any
  browser default (typically ≥60 s), so the server timeout always wins.

**Alternatives considered**:
- *Job queue + polling* — rejected: more code, more components, no v1
  benefit since runs are ≤30 s.
- *WebSocket per-item progress streaming* — rejected: would require
  per-check streaming primitives in the executor and a stateful frontend
  store, all for cosmetic value the spec already chose to forgo (FR-009
  needs only generic in-progress feedback).
- *Per-`(host, operator)` lock instead of per-`host` lock* — rejected:
  permits two operators to hammer one SSH endpoint simultaneously,
  which buys nothing and risks confusing diagnostics.

---

## R6. Where do operator-visible strings live?

**Decision**: A single TypeScript module `frontend/src/strings.ts` is the
canonical home for every operator-visible string in v1, keyed by a stable
identifier. Backend responses NEVER include English copy meant for
operators; the backend returns structured, identifier-bearing payloads
(item identifier, status, category code, raw_detail-when-developer-mode)
and the frontend renders the string for that identifier.

**Rationale**:
- Constitution III (Non-Technical UX) requires the operator-visible
  surface to be reviewable for jargon. A single file diff catches every
  copy change in a PR.
- FR-014 (English-only v1) is satisfied today; future German support
  would replace this one file with an i18n keyed dictionary without
  changing the API contract.
- Backend stays language-agnostic. Raw output included in Developer-mode
  responses is engineering-facing and explicitly outside Principle III.

**Alternatives considered**:
- *Backend returns rendered English copy* — rejected: leaks UX concerns
  into API responses, makes localization later mean an API rewrite,
  doubles the surface a reviewer must audit for jargon.
- *Per-component string literals in JSX* — rejected: makes the jargon
  audit a multi-file grep instead of a single-file review.

---

## R7. Result-view entry: persistence vs. blank-on-entry (FR-026 + FR-028)

**Decision**:
- Backend persists the most recent run per `(operator, host_id)` pair
  on disk (FR-026) — see R4 for the directory layout.
- The HTTP API in v1 **does not expose** an endpoint that returns the
  persisted run for a host. There is no `GET /api/runs/latest`. The
  result page calls `POST /api/runs` only when the operator clicks the
  CTA, and renders nothing host-specific until that response arrives
  (FR-028).
- The persisted record's purpose in v1 is twofold:
  1. **Backend audit / inspection** — engineers can read
     `~/.cache/vayobd/runs/<operator>/<host_id>.json` directly.
  2. **Same-tab refresh resilience** — a future iteration can
     reintroduce a `GET /api/runs/latest` endpoint to repopulate the
     result view after an accidental browser refresh, without changing
     the on-disk format.

**Rationale**:
- FR-028 is explicit that no UI affordance recalls a stored run
  without re-running. Defining a `GET` endpoint with no consumer in v1
  would invite drift between contract and behaviour (Constitution I).
- Keeping persistence on disk preserves the per-operator scoping
  decision (FR-026) without locking us into a "no persistence at all"
  shape that would force a backend rewrite the moment the team wants
  the audit log or the refresh-resilience affordance.

**Alternatives considered**:
- *No persistence at all in v1* — rejected: contradicts FR-026 and
  closes the door on cheap follow-ups (audit, refresh-resilience). The
  on-disk write costs nothing.
- *Expose `GET /api/runs/latest` even though FR-028 forbids the
  frontend from using it* — rejected: adds a contract surface the
  frontend won't call, increases the audit footprint for SC-003 (jargon
  audit on Operator-mode-visible surfaces) for zero v1 value.

---

## Summary of unresolved items at the end of Phase 0

None. Every `NEEDS CLARIFICATION` originally implied by the Technical
Context and the deferred-to-plan portions of `spec.md` is closed above,
including the five clarifications recorded in spec.md Session
2026-05-07 (timeout, scope, country-step UX, persistence scope,
refresh-failure handling) and the FR-028 result-view-on-entry rule.
