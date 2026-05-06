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
  3. On a fixed-cadence background scheduler running inside the FastAPI
     process (`asyncio` task at default 30-minute interval, configurable).
- Refresh failures do NOT replace the previously cached copy; the loader
  continues to read whatever is on disk. The most-recent successful refresh
  timestamp is kept in `~/.cache/vayobd/inventory.meta.json` and returned
  by `GET /api/inventory` for FR-018.

**Rationale**:
- Constitution I (Simplicity First): one moving part — a local git
  checkout. Familiar to anyone on the team.
- Survives intermittent VPN/network blips without downgrading the
  operator's UX.
- Avoids ambient state: refresh is observable through one endpoint and one
  metadata file.

**Alternatives considered**:
- *rsync from a snapshot server* — rejected: requires a snapshot server we
  don't have.
- *Tarball download from a release artefact* — rejected: needs a release
  pipeline; git pull is what the team already does manually.
- *Live read on every request* — rejected: violates FR-015 (offline
  tolerance) and adds latency to picker render.

---

## R3. Which concrete diagnostic items run per host class?

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
trusted header (`X-Vay-User`). The app reads the header for logging and
audit; it does not gate access to specific hosts in v1. All authenticated
operators can run any check on any in-scope host. There is no role split
in v1 — Developer mode is a UI affordance, not an authorization boundary.

**Rationale**:
- Spec assumption already says auth is handled by existing internal SSO and
  is out of scope for the feature spec. This plan honours that.
- Constitution II (Ship Fast): no per-host RBAC in v1.
- Putting SSO at the proxy is the project-typical pattern at Vay and means
  this app stays unaware of OIDC / SAML / cookie internals.

**Alternatives considered**:
- *Per-host role-based access* — rejected for v1: requires a role mapping
  registry the team doesn't have and the hackathon doesn't need. Easy to
  add later without breaking the API shape.
- *In-app session login* — rejected: reinvents what corp SSO already does.

---

## R5. How is the in-progress run modelled, given FR-024 (wait-only, no cancel, no background)?

**Decision**:
- `POST /api/runs` is a synchronous request that does not return until the
  run terminates (complete / partial / unreachable / timeout).
- Server-side hard timeout: 25 s (slightly above SC-006's 10 s typical so
  slow-but-honest runs aren't cut off prematurely; well under common
  reverse-proxy and browser request timeouts).
- The frontend shows a generic "Running checks against `<host>`…" spinner
  while the request is in flight (FR-009). No item-level streaming.
- Concurrency lock (FR-011): an in-memory `asyncio.Lock` keyed by
  `host_id`. A second `POST /api/runs` for a host that already has a run
  in flight returns HTTP 409 with a `{"reason": "run_in_progress"}` body;
  the frontend translates this into a plain-English toast and disables
  the "Run check" button while a run is active.

**Rationale**:
- Synchronous request = simplest possible state machine. No queue, no
  WebSocket, no SSE, no background worker.
- An in-memory lock is sufficient because v1 is a single-process backend
  (FR-011 only requires "from the same operator" — a single process
  inherently sees all live runs).

**Alternatives considered**:
- *Job queue + polling* — rejected: more code, more components, no v1
  benefit since runs are <25 s.
- *WebSocket per-item progress streaming* — rejected: would require
  per-check streaming primitives in the executor and a stateful frontend
  store, all for cosmetic value the spec already chose to forgo (FR-009
  needs only generic in-progress feedback).

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

## Summary of unresolved items at the end of Phase 0

None. Every `NEEDS CLARIFICATION` originally implied by the Technical
Context and the deferred-to-plan portions of `spec.md` is closed above.
