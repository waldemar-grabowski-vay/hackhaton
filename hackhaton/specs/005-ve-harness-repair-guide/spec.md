# Feature Specification: Vehicle Harness in VE Repair Guides

**Feature Branch**: `005-ve-harness-repair-guide`  
**Created**: 2026-05-11  
**Status**: Draft  
**Input**: User description: "I want to work a bit more on the repair guides. It is still missing to show the Vehicle harness on the repair guides for VE hosts."

## Context

The VayOBD repair guide sheet is a side-by-side dialog: left panel shows checklist steps for the failing diagnostic item, right panel shows a wiring harness diagram. For TS hosts this works end-to-end — the telestation harness panel auto-switches harness tabs and highlights the relevant connector when an operator taps a "locate connector" chip in a repair step.

For VE hosts the infrastructure is partially in place (the `HarnessDiagram` component exists with 15 harness tabs and connector zoom), but the repair-guide experience is incomplete: most VE-specific diagnostic checks either have no connector location chips in their repair steps, or open the guide to a blank "board" harness with no guidance on which harness to look at. The `ve-roof-harness.png` image also exists on disk but is not registered as a harness tab.

This feature completes the VE repair guide surface so it is as actionable for vehicle operators as the TS guide already is for telestation operators.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Connector chip zooms vehicle harness to the right location (Priority: P1)

An operator opens a repair guide for a failing VE diagnostic check. In the right panel the vehicle harness diagram is visible. One of the repair steps includes a connector chip (e.g. "APCB_2_VIH"). The operator taps it; the right panel auto-switches to the correct harness tab and zooms to a pulsing red highlight over that connector, exactly as TS repair guides already behave.

**Why this priority**: This is the core gap. Without correct connector locations wired into VE repair steps the right panel is a decorative map with no actionable guidance.

**Independent Test**: Open a run result for any VE host, trigger a failing check that has a connector chip in its repair guide, open the guide, tap the connector chip, confirm the harness tab switches and the connector animates into view.

**Acceptance Scenarios**:

1. **Given** a VE run result with a failing check, **When** the operator opens the repair guide and taps a connector chip, **Then** the harness panel switches to the tab containing that connector and centers the animated highlight on the correct location.
2. **Given** the operator taps a connector chip for a connector on the current harness tab, **When** they tap it, **Then** the panel scrolls and zooms without switching tabs.
3. **Given** a connector chip with no location data registered, **When** tapped, **Then** no crash occurs and the chip still appears (no highlight is shown).

---

### User Story 2 - Roof harness tab is available and usable (Priority: P2)

An operator opens a vehicle repair guide and sees a "Roof" tab alongside the existing harness tabs. They can browse the roof harness diagram and any connector chips referencing roof-mounted connectors correctly zoom into that harness.

**Why this priority**: The `ve-roof-harness.png` image exists in the asset bundle but the harness is not registered — connectors on the roof harness cannot be located from any repair step.

**Independent Test**: Open any VE repair guide, confirm a "Roof" tab is present in the harness panel tab strip, click it, confirm the roof harness image loads without error.

**Acceptance Scenarios**:

1. **Given** the VE repair guide is open, **When** the operator clicks the "Roof" tab, **Then** the roof harness image loads and displays.
2. **Given** a repair step references a roof-mounted connector, **When** the operator taps the connector chip, **Then** the panel switches to the Roof tab and highlights the connector.

---

### User Story 3 - VE-specific diagnostic checks have complete repair step data (Priority: P3)

Diagnostic checks that are vehicle-only (e.g. `kl15`, `vehicle_integration_config_valid`, `vehicle_config`) include connector chips in their repair steps wherever a physical connector is referenced in the step body, matching the detail level of TS repair guides.

**Why this priority**: Connector chips and location data for VE-specific checks are the content that makes the harness panel useful. Without them the feature is structurally complete but provides no guidance.

**Independent Test**: Open each VE-specific repair guide; for every step that mentions a named connector, confirm a corresponding connector chip exists; tap each chip and confirm the harness zooms to the right location.

**Acceptance Scenarios**:

1. **Given** a VE diagnostic check repair guide that mentions a specific connector in a step body, **When** the operator views that step, **Then** a connector chip is present for that connector.
2. **Given** a connector chip is present, **When** tapped, **Then** the harness zooms to the registered location for that connector.

---

### Edge Cases

- What happens when a connector ID appears in a repair step but has no registered location in `vehicleConnectorLocations`? → chip should remain tappable but no highlight fires.
- What happens when `hostType` is undefined on the repair guide sheet? → fall back to showing `HarnessDiagram` (existing behaviour, preserve it).
- What happens on a very small viewport where the two-panel layout is cramped? → existing responsive behaviour is unchanged by this feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST register the `ve-roof` harness in the vehicle harness tab list alongside the existing 15 tabs, using the existing `ve-roof-harness.png` asset.
- **FR-002**: The system MUST add `CONNECTOR_HARNESS` entries and `vehicleConnectorLocations` coordinates for every connector chip referenced in VE-specific repair steps (`kl15`, `vehicle_integration_config_valid`, `vehicle_config`, and any other `vehicleOnly: true` checks in `guides.ts`).
- **FR-003**: Repair steps in VE-specific guides that describe a physical connector interaction MUST include a connector chip entry so the operator can tap to locate it on the harness diagram.
- **FR-004**: The harness panel header label for VE hosts MUST read "Vehicle harness" (not "Vehicle diagram") to match the TS label pattern.
- **FR-005**: Tapping a connector chip in a VE repair step MUST trigger the same auto-tab-switch and zoom-to-highlight behaviour already implemented for TS guides.

### Key Entities

- **VehicleHarnessKey**: Enum of registered harness tabs; gains a new `"roof"` value.
- **RepairStep connector chip**: `{ id: string; label: string }` entry within a `RepairStep`; triggers harness focus when tapped.
- **vehicleConnectorLocations**: Map of harness key → connector ID → `{ fx, fy }` normalised coordinates; gains new entries for roof connectors and any missing VE check connectors.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every VE repair guide step that names a physical connector has at least one tappable connector chip — 0 named connectors without chips in the final state.
- **SC-002**: Tapping any connector chip in a VE repair guide produces a visible highlight on the harness within 500 ms.
- **SC-003**: The Roof harness tab loads its image without error on 100% of attempts.
- **SC-004**: The harness panel header reads "Vehicle harness" for VE hosts, consistent with the TS label.
- **SC-005**: No existing TS repair guide behaviour regresses — all existing connector chips on TS guides continue to zoom correctly.

## Assumptions

- The `ve-roof-harness.png` image already in `public/` is the correct and final roof harness diagram; no new image work is needed.
- Connector physical locations (normalised `fx`/`fy` coordinates) for roof connectors will be calibrated by the same method used for existing harnesses (visual inspection of the PNG).
- The set of VE-specific diagnostic checks requiring connector data is bounded to the `vehicleOnly: true` entries in `guides.ts` plus any VE-path steps in shared guides that reference physical connectors.
- Mobile/touch interaction is out of scope; the connector chip tap targets are sized for desktop use.
