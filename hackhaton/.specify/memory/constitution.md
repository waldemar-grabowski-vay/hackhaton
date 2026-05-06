<!--
SYNC IMPACT REPORT
==================
Version change: (uninitialized template) → 1.0.0
Bump rationale: Initial ratification. All placeholder tokens replaced with concrete
values. SemVer baseline established at 1.0.0.

Modified principles: N/A (initial draft)
Added sections:
  - Core Principles: I. Simplicity First, II. Ship Fast, III. Non-Technical User UX
  - Web App Standards (additional constraints)
  - Development Workflow
  - Governance
Removed sections:
  - Template principle slots IV and V (only 3 principles requested by stakeholders)

Templates requiring updates:
  ✅ .specify/templates/plan-template.md — references constitution generically; no edit needed
  ✅ .specify/templates/spec-template.md — no principle-specific gates; no edit needed
  ✅ .specify/templates/tasks-template.md — no principle-specific categories; no edit needed
  ✅ .specify/templates/checklist-template.md — generic; no edit needed
  ✅ CLAUDE.md — references "current plan" generically; no edit needed

Follow-up TODOs: none
-->

# VayOBD Tool Constitution

## Core Principles

### I. Simplicity First (NON-NEGOTIABLE)

Every feature MUST be the simplest implementation that solves the user-facing
problem. Reject premature abstractions, configuration knobs, and frameworks
introduced for hypothetical future needs. Each new dependency, screen, route,
or option MUST justify itself against concrete user value; "we might need it"
is not justification.

**Rationale**: Complexity is the primary risk for hackathon delivery and is the
single largest barrier to adoption by the non-technical end users this tool
serves. Fewer moving parts means fewer failures and a comprehensible product.

### II. Ship Fast

Time-to-running-feature beats time-to-perfect-feature. Prefer a working spike
deployed to a shared environment, then iterate. The mainline branch MUST be
deployable at all times; a broken main build MUST be fixed or reverted within
the working hour. Polish, refactors, and abstractions are acceptable only
*after* the user-facing flow is demonstrably working end-to-end.

**Rationale**: The value of this project is demonstrated working software, not
internal elegance. Working code in users' hands generates feedback that no
amount of upfront design can substitute for.

### III. Non-Technical User UX (NON-NEGOTIABLE)

The primary user is non-technical and has no exposure to vehicle diagnostics
internals or developer tooling. Therefore:

- User-facing copy MUST avoid jargon, raw OBD codes, stack traces, and
  developer terminology. Where a technical term is unavoidable, it MUST be
  paired with a plain-language explanation.
- Every user-facing flow MUST be operable without reading external
  documentation; the UI itself is the documentation.
- Error states MUST tell the user what to do next (recovery action), not only
  what went wrong.
- Default settings MUST produce a useful result; configuration is opt-in.

**Rationale**: VayOBD's audience cannot interpret diagnostic output directly. A
technically correct app that the target user cannot operate has zero value.

## Web App Standards

The product is delivered as a web application. The following constraints are
binding:

- **Delivery**: Browser-based only. No native desktop or mobile binaries unless
  a future amendment lifts this constraint.
- **Browser support**: Current versions of Chrome, Firefox, Safari, and Edge.
  Internet Explorer and end-of-life browsers are out of scope.
- **Responsive layout**: All primary flows MUST be usable on a phone-sized
  viewport (≥360 px wide), since OBD usage frequently happens at the vehicle
  rather than at a desk.
- **Transport security**: Production traffic MUST be served over HTTPS.
  Credentials, tokens, and vehicle data MUST NOT be transmitted in clear text.
- **Privacy**: Vehicle identifiers (VIN) and any personally identifiable
  information are treated as sensitive. They MUST NOT appear in client-side
  logs, analytics events, or URLs.

## Development Workflow

- **Change review**: All changes MUST go through a pull request. Reviewer's
  first question MUST be "is this the simplest path that achieves the goal?"
  per Principle I.
- **Quality gates during the hackathon**: Critical-path code (anything on the
  main user flow) MUST have at least one smoke test or manual reproduction
  step recorded in the PR description. Non-critical code MAY ship without
  tests but SHOULD be flagged as such.
- **Demo readiness**: A working deployment of the latest main MUST exist at all
  times during the hackathon window. If a change risks breaking the demo,
  it lands behind a feature flag or is held until after the demo.
- **Decisions**: Reversible decisions are made quickly without consensus.
  Irreversible decisions (data model, persisted schema, third-party paid
  services, public API shape) require team alignment before merge.

## Governance

This constitution supersedes ad-hoc practices. When a proposed change conflicts
with a principle here, the principle wins unless the constitution is amended
first.

**Amendment procedure**: Any team member may propose an amendment via a pull
request modifying `.specify/memory/constitution.md`. The PR MUST include the
Sync Impact Report block at the top, the rationale for the change, and the
intended version bump. Merge requires acknowledgement from at least one other
listed author.

**Versioning policy** (semantic versioning of this document):
- **MAJOR**: A principle is removed, redefined in a backward-incompatible way,
  or governance rules are materially restructured.
- **MINOR**: A new principle or normative section is added, or an existing
  principle is materially expanded.
- **PATCH**: Wording clarifications, typo fixes, or non-semantic refinements
  that do not change what is required of contributors.

**Compliance review**: Every pull request description MUST confirm the change
is consistent with all three principles, or explicitly justify any deviation
under "Complexity Tracking" in the implementation plan. Reviewers MUST block
merges that violate Principle I or III without justification.

**Runtime guidance**: Day-to-day development guidance not codified here lives
in `CLAUDE.md` at the project root and in feature-specific plans under
`specs/`.

**Version**: 1.0.0 | **Ratified**: 2026-05-06 | **Last Amended**: 2026-05-06
