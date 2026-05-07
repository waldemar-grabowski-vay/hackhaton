// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

// Repair playbooks surfaced through the dashboard overlay (`f` on a connected
// host) and the standalone guides view (main menu → "Open repair guides").
//
// Each `RepairKind` owns an ordered list of `RepairStep`s. Steps are either
// hardware inspections (read-the-harness checklists, `Inspect`) or runnable
// software actions (`Command`, executed over SSH on a connected host).
// Hardware-first ordering reflects the actual debugging flow: bench-check
// the wiring before assuming a software fault.

use ree_debug_engine::inventory::HostKind;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RepairKind {
    Xcp,
    SwButtons,
}

impl RepairKind {
    pub const ALL: &'static [RepairKind] = &[RepairKind::Xcp, RepairKind::SwButtons];

    pub fn label(self) -> &'static str {
        match self {
            RepairKind::Xcp => "XCP traffic",
            RepairKind::SwButtons => "Steering wheel buttons",
        }
    }

    pub fn problem_check_name(self) -> &'static str {
        match self {
            RepairKind::Xcp => "XCP traffic",
            // First SW-button check name; used by the dashboard overlay's
            // "is this failing?" header — the cluster of TS_SEC_CMD rows all
            // turn warn together, so picking one is fine.
            RepairKind::SwButtons => "TS horn",
        }
    }

    /// Look up which repair playbook applies to a failing dashboard row by
    /// name. Returns None when no playbook owns the row — the operator has
    /// to read the failure summary and improvise.
    ///
    /// Distinct from `problem_check_name`, which goes the other way (picks
    /// one canonical row per kind for the overlay header).
    #[allow(dead_code)] // Wired by the dashboard once A picks up the new lookup.
    pub fn for_failing_row(name: &str) -> Option<RepairKind> {
        match name {
            // XCP playbook covers the link layer (`CAN buses`) and the
            // active probe (`XCP traffic`). The hardware checklist also
            // exercises the connectors APP_CAN rides on, but APP_CAN
            // failures more often have software causes (gateway down) the
            // playbook doesn't address — keep the mapping narrow there.
            "XCP traffic" | "CAN buses" => Some(RepairKind::Xcp),
            // TS_SEC_CMD cluster + TS_PRIM_CMD turn-indicator are all
            // driven by the steering wheel via CAN_SW.
            "TS horn"
            | "TS front wiper"
            | "TS rear wiper"
            | "TS wiper interval vol"
            | "TS turn indicator" => Some(RepairKind::SwButtons),
            _ => None,
        }
    }
}

#[derive(Debug, Clone)]
pub enum RepairAction {
    /// Manual hardware/physical inspection. The TUI shows the checklist; the
    /// user verifies it on the bench. Pressing Enter in the dashboard overlay
    /// is a no-op for these steps — there's nothing to run remotely.
    Inspect,
    /// Bash command run over SSH on the connected host.
    Command(String),
}

/// One granular item inside a `RepairStep` — a continuity test, a multimeter
/// reading, or a visual confirmation. Each sub-check is independently
/// tickable in the guides walkthrough.
#[derive(Debug, Clone)]
pub struct SubCheck {
    pub label: &'static str,
    /// Optional second line for measurement targets / expected values.
    pub detail: Option<&'static str>,
}

/// Color tag used in ASCII diagrams. Mapped to terminal colors at render time
/// so the wire labels match real harness colors at a glance.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
#[allow(dead_code)] // Yellow/Green/White used by future diagrams (other harnesses).
pub enum WireColor {
    Default,
    Black,
    Red,
    Blue,
    Brown,
    Yellow,
    Green,
    Gray,
    White,
    /// Bold default — used for pin numbers, dots, etc.
    Pin,
    /// Dim default — used for notes / annotations on the diagram.
    Note,
}

#[derive(Debug, Clone)]
pub struct DiagramSpan {
    pub text: &'static str,
    pub color: WireColor,
}

impl DiagramSpan {
    pub const fn plain(text: &'static str) -> Self {
        Self { text, color: WireColor::Default }
    }
    pub const fn wire(text: &'static str, color: WireColor) -> Self {
        Self { text, color }
    }
}

#[derive(Debug, Clone)]
pub struct Diagram {
    pub title: &'static str,
    pub lines: Vec<Vec<DiagramSpan>>,
}

#[derive(Debug, Clone)]
pub struct RepairStep {
    pub label: &'static str,
    /// Multi-line description. Newlines are preserved when rendered.
    pub detail: &'static str,
    pub action: RepairAction,
    /// Granular sub-checks for hardware drilldown. Empty for software steps
    /// or any step that doesn't warrant per-pin/per-measurement breakdown.
    pub checks: Vec<SubCheck>,
    /// Optional ASCII pinout / harness diagram with color-coded wires.
    pub diagram: Option<Diagram>,
}

pub fn steps_for(kind: RepairKind, host_kind: HostKind) -> Vec<RepairStep> {
    match kind {
        RepairKind::Xcp => xcp_steps(host_kind),
        RepairKind::SwButtons => sw_button_steps(host_kind),
    }
}

// --- Diagram-building helpers ----------------------------------------------
//
// Each diagram is a Vec<Vec<DiagramSpan>> — one line per inner Vec, one
// span per (text, color) chunk. The helpers below let each step's diagram
// read like a small pinout drawing instead of nested vec! noise.

fn line(spans: &[(WireColor, &'static str)]) -> Vec<DiagramSpan> {
    spans.iter().map(|(c, t)| DiagramSpan::wire(t, *c)).collect()
}
fn blank() -> Vec<DiagramSpan> { Vec::new() }
fn plain(text: &'static str) -> Vec<DiagramSpan> {
    vec![DiagramSpan::plain(text)]
}

fn diagram_inline_can() -> Diagram {
    use WireColor::*;
    Diagram {
        title: "TE Superseal 2-pin inline (205203-3)",
        lines: vec![
            plain("           ┌──────────────┐"),
            line(&[
                (Default, "  pin 7  "),
                (Pin,     "● "),
                (Default, "── "),
                (Blue,    "Blue   "),
                (Default, "── "),
                (Pin,     "CAN_H"),
            ]),
            plain("           │              │"),
            line(&[
                (Default, "  pin 2  "),
                (Pin,     "● "),
                (Default, "── "),
                (Brown,   "Brown  "),
                (Default, "── "),
                (Pin,     "CAN_L"),
                (Note,    "   (Gray on CAN_OTA)"),
            ]),
            plain("           └──────────────┘"),
            blank(),
            line(&[
                (Note, "Backshell 1991253-9 closes the back of the housing."),
            ]),
        ],
    }
}

fn diagram_molex_mini50() -> Diagram {
    use WireColor::*;
    Diagram {
        title: "Molex_Mini_50 breakout (34791-0080) — REECU pigtail mate",
        lines: vec![
            plain("    ┌──────────────────────────────────────────────────────┐"),
            line(&[
                (Default, "    │ "),
                (Pin,     "pin 1 "),
                (Note,    "(unused)                                        "),
                (Default, "│"),
            ]),
            line(&[
                (Default, "    │ "),
                (Pin,     "pin 2 ● "),
                (Default, "── "),
                (Blue,    "Blue   "),
                (Default, "── "),
                (Pin,     "CAN_H "),
                (Default, "→ CAN_REECU pin 7  "),
                (Note,    "T_8"),
                (Default, "   │"),
            ]),
            line(&[
                (Default, "    │ "),
                (Pin,     "pin 3 ● "),
                (Default, "── "),
                (Brown,   "Brown  "),
                (Default, "── "),
                (Pin,     "CAN_L "),
                (Default, "→ CAN_REECU pin 2  "),
                (Note,    "T_8"),
                (Default, "   │"),
            ]),
            line(&[
                (Default, "    │ "),
                (Pin,     "pin 4 ● "),
                (Default, "── "),
                (Black,   "Black  "),
                (Default, "── "),
                (Pin,     "GND   "),
                (Default, "→ S_GND_01    "),
                (Red,     "*shared*"),
                (Default, "    │"),
            ]),
            line(&[
                (Default, "    │ "),
                (Pin,     "pin 5 "),
                (Note,    "(unused)                                        "),
                (Default, "│"),
            ]),
            line(&[
                (Default, "    │ "),
                (Pin,     "pin 6 ● "),
                (Default, "── "),
                (Blue,    "Blue   "),
                (Default, "── "),
                (Pin,     "CAN_H "),
                (Default, "→ CAN_OTA   pin 7  "),
                (Note,    "T_9"),
                (Default, "   │"),
            ]),
            line(&[
                (Default, "    │ "),
                (Pin,     "pin 7 ● "),
                (Default, "── "),
                (Gray,    "Gray   "),
                (Default, "── "),
                (Pin,     "CAN_L "),
                (Default, "→ CAN_OTA   pin 2  "),
                (Note,    "T_9"),
                (Default, "   │"),
            ]),
            line(&[
                (Default, "    │ "),
                (Pin,     "pin 8 "),
                (Note,    "(unused)                                        "),
                (Default, "│"),
            ]),
            plain("    └──────────────────────────────────────────────────────┘"),
            blank(),
            line(&[
                (Red,  "*shared*"),
                (Note, " — pin 4 is the common ground. Bad GND breaks BOTH buses."),
            ]),
        ],
    }
}

fn diagram_reecu_power() -> Diagram {
    use WireColor::*;
    Diagram {
        title: "REECU power chain (REECU_PWR ↔ FuseBox_F)",
        lines: vec![
            plain("    REECU_PWR (DT06-4S-EP11)            FuseBox_F (19419-0001)"),
            plain("    ┌──────────┐                        ┌──────────┐"),
            line(&[
                (Default, "    │ "),
                (Pin,     "pin 1 ● "),
                (Default, "├── "),
                (Red,     "Red    "),
                (Default, "+12V (W47) ──── "),
                (Pin,     "pin 4 "),
                (Default, "│"),
            ]),
            plain("    │ pin 2    │                        │ pin 5    │"),
            line(&[
                (Default, "    │ "),
                (Pin,     "pin 3 ● "),
                (Default, "├── "),
                (Black,   "Black  "),
                (Default, "GND  (W49) ──── "),
                (Pin,     "pin 6 "),
                (Default, "│"),
            ]),
            plain("    │ pin 4    │                        │ pin 7    │"),
            plain("    └──────────┘                        └──────────┘"),
            blank(),
            line(&[
                (Note, "Fuse sits in FuseBox_F upstream of pin 4. Check intact."),
            ]),
            line(&[
                (Note, "Multimeter ~12V across REECU_PWR pins 1 ↔ 3."),
            ]),
        ],
    }
}

fn diagram_termination() -> Diagram {
    use WireColor::*;
    Diagram {
        title: "CAN bus termination — bench measurement",
        lines: vec![
            plain("                          120Ω                    120Ω"),
            plain("                       ┌───────┐                ┌───────┐"),
            plain("                       │       │                │       │"),
            line(&[
                (Pin,     "    CAN_H "),
                (Default, "──┬────────┴──┬────┄┄┄┄────┴──┬────────┴──┬─── REECU"),
            ]),
            plain("              │           │              │           │"),
            plain("              │           │              │           │"),
            line(&[
                (Pin,     "    CAN_L "),
                (Default, "──┴────────┬──┴────┄┄┄┄────┬──┴────────┬──┴─── REECU"),
            ]),
            plain("                       │       │                │       │"),
            plain("                       └───────┘                └───────┘"),
            blank(),
            line(&[
                (Note, "Two 120Ω terminators in parallel = "),
                (Pin,  "60Ω"),
                (Note, " across CAN_H/CAN_L."),
            ]),
            line(&[
                (Note, "Pull both terminators to verify no short between H and L."),
            ]),
        ],
    }
}

fn xcp_steps(host_kind: HostKind) -> Vec<RepairStep> {
    let default_bus = match host_kind {
        HostKind::Ts => "can2",
        HostKind::Ve => "can1",
    };
    let prelude = format!(
        "BUS=$(grep ^CAN_BUS_XCP= /etc/ree/can_bus_map 2>/dev/null | cut -d= -f2); \
         [ -n \"$BUS\" ] || BUS={default_bus};"
    );
    let bring_up = format!(
        "{prelude} \
         sudo -n ip link set \"$BUS\" up type can \
           bitrate 500000 sample-point 0.75 \
           dbitrate 2500000 dsample-point 0.75 \
           restart-ms 10 fd on 2>&1; \
         RC=$?; echo \"BUS=$BUS\"; echo \"RC=$RC\""
    );
    let down_up = format!(
        "{prelude} \
         sudo -n ip link set \"$BUS\" down 2>&1; \
         sleep 0.5; \
         sudo -n ip link set \"$BUS\" up type can \
           bitrate 500000 sample-point 0.75 \
           dbitrate 2500000 dsample-point 0.75 \
           restart-ms 10 fd on 2>&1; \
         RC=$?; echo \"BUS=$BUS\"; echo \"RC=$RC\""
    );
    // On TS the OosOps containers are owned by user `ree`; on VE there's no
    // `ree` user so we run docker as root. Try -u ree first, fall back to
    // plain sudo (mirrors the gateway-container check).
    let restart_gw = "(sudo -n -u ree docker restart oos_reecu_gateway 2>&1 \
                      || sudo -n docker restart oos_reecu_gateway 2>&1); \
                     RC=$?; echo \"RC=$RC\""
        .to_string();

    vec![
        // -- Hardware checks first: TIH harness (TS050100) -------------------
        RepairStep {
            label: "Identify which inline CAN connector carries XCP",
            detail: "Determines which 205203-3 inline pigtail to inspect in the\n\
                     following steps. CAN_SW is the steering-wheel bus — never XCP.",
            action: RepairAction::Inspect,
            diagram: None,
            checks: vec![
                SubCheck {
                    label: "Read CAN_BUS_XCP= from /etc/ree/can_bus_map on the host",
                    detail: Some("The dashboard's `CAN buses` check prints this when run."),
                },
                SubCheck {
                    label: "Map CAN_BUS_XCP → inline connector",
                    detail: Some(
                        "CAN_REECU pair → Molex_Mini_50 pins 2/3 (twist T_8). \
                         CAN_OTA pair → Molex_Mini_50 pins 6/7 (twist T_9).",
                    ),
                },
            ],
        },
        RepairStep {
            label: "Inspect inline CAN connector (TE 205203-3)",
            detail: "TE Superseal 2-pin inline — CAN_REECU or CAN_OTA per the mapping.\n\
                     Backshell 1991253-9. Pins 2/7 = CAN_L/CAN_H.",
            action: RepairAction::Inspect,
            diagram: Some(diagram_inline_can()),
            checks: vec![
                SubCheck {
                    label: "Connector fully seated, retainer locked",
                    detail: Some("Audible click when re-seating; no rocking."),
                },
                SubCheck {
                    label: "No bent / pushed-back / corroded pins",
                    detail: Some("Visual + gentle pin-tip wiggle from the front."),
                },
                SubCheck {
                    label: "Tug-test each wire at the back of the housing",
                    detail: Some("~5N pull — wire must not slide out of the crimp."),
                },
                SubCheck {
                    label: "Pin orientation: pin 2 = CAN_L, pin 7 = CAN_H",
                    detail: None,
                },
                SubCheck {
                    label: "Backshell 1991253-9 not cracked, no strain on wires",
                    detail: None,
                },
            ],
        },
        RepairStep {
            label: "Inspect Molex_Mini_50 breakout (34791-0080)",
            detail: "8-pos Molex Mini-50 that mates with the REECU CAN pigtail.\n\
                     Hosts both CAN_REECU and CAN_OTA — bad shared GND breaks both.",
            action: RepairAction::Inspect,
            diagram: Some(diagram_molex_mini50()),
            checks: vec![
                SubCheck {
                    label: "Connector fully mated, retainer clicked in",
                    detail: None,
                },
                SubCheck {
                    label: "CAN_REECU pair on pins 2 (Blue, CAN_H) / 3 (Brown, CAN_L)",
                    detail: Some("Twist T_8 leaves the connector toward CAN_REECU inline."),
                },
                SubCheck {
                    label: "CAN_OTA pair on pins 6 (Blue, CAN_H) / 7 (Gray, CAN_L)",
                    detail: Some("Twist T_9 leaves the connector toward CAN_OTA inline."),
                },
                SubCheck {
                    label: "Pin 4 (Black) = S_GND_01 — shared GND for both buses",
                    detail: Some("If pin 4 is open or high-resistance, BOTH buses fail."),
                },
                SubCheck {
                    label: "No bent terminals, no green corrosion",
                    detail: None,
                },
                SubCheck {
                    label: "Continuity: Molex_Mini_50 pin 2 ↔ inline CAN_REECU pin 7",
                    detail: Some("CAN_H trace, expect <1Ω."),
                },
                SubCheck {
                    label: "Continuity: Molex_Mini_50 pin 3 ↔ inline CAN_REECU pin 2",
                    detail: Some("CAN_L trace, expect <1Ω."),
                },
            ],
        },
        RepairStep {
            label: "Inspect REECU main connector (34566-0203)",
            detail: "20-pos Molex Mini-50 with backshell 34565-0003 on the REECU side.\n\
                     CAN exits here and reaches Molex_Mini_50 via the REECU pigtail.",
            action: RepairAction::Inspect,
            diagram: None,
            checks: vec![
                SubCheck {
                    label: "Backshell screws torqued, no gap to housing",
                    detail: None,
                },
                SubCheck {
                    label: "Connector retainer fully engaged, latch clicked",
                    detail: None,
                },
                SubCheck {
                    label: "No strain on wires entering the backshell",
                    detail: Some("Service loop slack, no kinks at the strain relief."),
                },
                SubCheck {
                    label: "Pigtail not chafed against chassis / nearby connectors",
                    detail: None,
                },
            ],
        },
        RepairStep {
            label: "Verify REECU power (REECU_PWR + FuseBox)",
            detail: "Without 12V the REECU can't drive XCP — check this BEFORE\n\
                     suspecting the bus. REECU_PWR is Deutsch DT06-4S-EP11.",
            action: RepairAction::Inspect,
            diagram: Some(diagram_reecu_power()),
            checks: vec![
                SubCheck {
                    label: "REECU fuse intact in FuseBox_F (19419-0001)",
                    detail: Some("Continuity across the fuse, or replace and recheck."),
                },
                SubCheck {
                    label: "FuseBox_F pin 4 → REECU_PWR pin 1 (W47, +12V)",
                    detail: Some("Continuity <1Ω end-to-end."),
                },
                SubCheck {
                    label: "FuseBox_F pin 6 → REECU_PWR pin 3 (W49, GND)",
                    detail: Some("Continuity <1Ω end-to-end."),
                },
                SubCheck {
                    label: "Multimeter: ~12V across REECU_PWR pins 1 and 3",
                    detail: Some("With FuseBox energized; pin 1 = +12V red, pin 3 = GND black."),
                },
                SubCheck {
                    label: "REECU_PWR connector seated, latch engaged",
                    detail: None,
                },
            ],
        },
        RepairStep {
            label: "Check twisted-pair integrity and termination",
            detail: "Untwisted, kinked, or shorted CAN pairs cause bus-off /\n\
                     error-passive that look exactly like \"no CONNECT_RESPONSE\".",
            action: RepairAction::Inspect,
            diagram: Some(diagram_termination()),
            checks: vec![
                SubCheck {
                    label: "Twist density consistent end-to-end",
                    detail: Some(
                        "T_8 on CAN_REECU pair (Molex_Mini_50 pins 2/3 ↔ inline 7/2). \
                         T_9 on CAN_OTA pair (Molex_Mini_50 pins 6/7 ↔ inline 7/2).",
                    ),
                },
                SubCheck {
                    label: "No abrasion, sharp bends, or pinch points along the run",
                    detail: None,
                },
                SubCheck {
                    label: "Multimeter: ~60Ω across CAN_H / CAN_L (REECU off)",
                    detail: Some(
                        "Two 120Ω terminators in parallel = 60Ω. \
                         Measured at any access point on the live pair.",
                    ),
                },
                SubCheck {
                    label: "No short to GND on either CAN_H or CAN_L",
                    detail: Some("Multimeter from CAN_H → GND and CAN_L → GND, expect open."),
                },
                SubCheck {
                    label: "No short between CAN_H and CAN_L (terminators removed)",
                    detail: Some("Pull both terminators, expect open across the pair."),
                },
            ],
        },
        // -- Software fallbacks (run on the connected host) ------------------
        RepairStep {
            label: "Bring up XCP bus",
            detail: "ip link set $BUS up type can bitrate 500k dbitrate 2.5M fd on\n\
                     (sample-point 0.75, restart-ms 10). Try this if the link is DOWN.",
            action: RepairAction::Command(bring_up),
            diagram: None,
            checks: Vec::new(),
        },
        RepairStep {
            label: "Down/up cycle XCP bus",
            detail: "ip link set $BUS down → sleep 0.5s → re-up with the same params.\n\
                     Clears stuck bus-off / error-passive after a wiring fix.",
            action: RepairAction::Command(down_up),
            diagram: None,
            checks: Vec::new(),
        },
        RepairStep {
            label: "Restart REECU gateway container",
            detail: "docker restart oos_reecu_gateway (TS: as user ree, VE: as root).\n\
                     Last resort once the harness and link layer look healthy.",
            action: RepairAction::Command(restart_gw),
            diagram: None,
            checks: Vec::new(),
        },
    ]
}

// --- Steering wheel buttons (TIH harness, TS-only) -------------------------

fn diagram_sw_signal_flow() -> Diagram {
    use WireColor::*;
    Diagram {
        title: "SW button signal flow",
        lines: vec![
            plain("    ┌──────────────┐        ┌──────────────┐        ┌──────────────┐"),
            line(&[
                (Default, "    │ "),
                (Pin,     "Steering    "),
                (Default, "│ ───── "),
                (Pin,     "CAN_SW"),
                (Default, " ─── │ "),
                (Pin,     "REECU       "),
                (Default, "│ → "),
                (Pin,     "APP_CAN"),
                (Default, " → │ "),
                (Pin,     "consumers   "),
                (Default, "│"),
            ]),
            line(&[
                (Default, "    │ "),
                (Pin,     "wheel module"),
                (Default, " │  "),
                (Note,    "(buttons →"),
                (Default, " │ "),
                (Pin,     "(re-publish)"),
                (Default, " │   "),
                (Pin,     "0x001/0x002"),
                (Default, "  │            │"),
            ]),
            plain("    └──────────────┘   CAN frames)│              │              │              │"),
            plain("                                  └──────────────┘              └──────────────┘"),
            blank(),
            line(&[
                (Note, "TS_PRIM_CMD (0x001) → TS_TURN_INDICATOR_STATE, TS_ESTOP_BUTTON_STATE"),
            ]),
            line(&[
                (Note, "TS_SEC_CMD  (0x002) → TS_HORN_STATE, TS_FRONT/REAR_WIPER_STATE, WIPER_INT_VOL"),
            ]),
        ],
    }
}

fn diagram_steering_wheel_m() -> Diagram {
    use WireColor::*;
    Diagram {
        title: "Steering_Wheel_M (504693-0403, Molex 4-pin)",
        lines: vec![
            plain("       ┌──────────────────┐"),
            line(&[
                (Default, "       │ "),
                (Pin,     "pin 1 ● "),
                (Default, "── "),
                (Black,   "Black "),
                (Default, "── "),
                (Pin,     "GND   "),
                (Default, "→ S_GND_02       │"),
            ]),
            line(&[
                (Default, "       │ "),
                (Pin,     "pin 2 ● "),
                (Default, "── "),
                (Red,     "Red   "),
                (Default, "── "),
                (Pin,     "+12V  "),
                (Default, "→ FuseBox_F p3   │"),
            ]),
            line(&[
                (Default, "       │ "),
                (Pin,     "pin 3 ● "),
                (Default, "── "),
                (Green,   "Green "),
                (Default, "── "),
                (Pin,     "CAN_H "),
                (Default, "→ CAN_SW pin 2   │"),
            ]),
            line(&[
                (Default, "       │ "),
                (Pin,     "pin 4 ● "),
                (Default, "── "),
                (Blue,    "Blue  "),
                (Default, "── "),
                (Pin,     "CAN_L "),
                (Default, "→ CAN_SW pin 7   │"),
            ]),
            plain("       └──────────────────┘"),
            blank(),
            line(&[
                (Note, "Twist T_7 on the CAN pair (pins 3/4)."),
            ]),
        ],
    }
}

fn diagram_can_sw_inline() -> Diagram {
    use WireColor::*;
    Diagram {
        title: "CAN_SW inline (TE Superseal 205203-3)",
        lines: vec![
            plain("           ┌──────────────┐"),
            line(&[
                (Default, "  pin 7  "),
                (Pin,     "● "),
                (Default, "── "),
                (Blue,    "Blue   "),
                (Default, "── "),
                (Pin,     "CAN_L"),
                (Note,    " (to Steering_Wheel_M pin 4)"),
            ]),
            plain("           │              │"),
            line(&[
                (Default, "  pin 2  "),
                (Pin,     "● "),
                (Default, "── "),
                (Green,   "Green  "),
                (Default, "── "),
                (Pin,     "CAN_H"),
                (Note,    " (to Steering_Wheel_M pin 3)"),
            ]),
            plain("           └──────────────┘"),
            blank(),
            line(&[
                (Note, "Other end of CAN_SW lands on the SW-side of the REECU CAN tree."),
            ]),
        ],
    }
}

fn sw_button_steps(_host_kind: HostKind) -> Vec<RepairStep> {
    vec![
        RepairStep {
            label: "Identify the SW button signal path",
            detail: "Buttons on the wheel are sensed by the Steering_Wheel module,\n\
                     which broadcasts state on CAN_SW. The REECU re-publishes them\n\
                     as TS_PRIM_CMD (0x001) and TS_SEC_CMD (0x002) on APP_CAN.",
            action: RepairAction::Inspect,
            diagram: Some(diagram_sw_signal_flow()),
            checks: vec![
                SubCheck {
                    label: "TS_PRIM_CMD (0x001): TURN_INDICATOR (bits 176..178), ESTOP (bit 168)",
                    detail: None,
                },
                SubCheck {
                    label: "TS_SEC_CMD (0x002): HORN (bit 22), FRONT/REAR_WIPER, WIPER_INT_VOL",
                    detail: None,
                },
                SubCheck {
                    label: "Press each button while watching the dashboard's SW rows",
                    detail: Some("Re-run the sweep with `r` after each press to confirm the value flips."),
                },
            ],
        },
        RepairStep {
            label: "Inspect Steering_Wheel_M connector (504693-0403)",
            detail: "Molex 4-pin on the steering-wheel side. Carries +12V, GND,\n\
                     and the CAN_SW twisted pair (T_7).",
            action: RepairAction::Inspect,
            diagram: Some(diagram_steering_wheel_m()),
            checks: vec![
                SubCheck {
                    label: "Connector fully seated, retainer clicked",
                    detail: None,
                },
                SubCheck {
                    label: "No bent / pushed-back / corroded pins",
                    detail: None,
                },
                SubCheck {
                    label: "Multimeter ~12V across pin 2 (Red) and pin 1 (Black)",
                    detail: Some("Wheel module is DC-powered; without 12V no buttons broadcast."),
                },
                SubCheck {
                    label: "Continuity: pin 3 (Green) ↔ CAN_SW pin 2 (Green)",
                    detail: Some("CAN_H trace, expect <1Ω."),
                },
                SubCheck {
                    label: "Continuity: pin 4 (Blue) ↔ CAN_SW pin 7 (Blue)",
                    detail: Some("CAN_L trace, expect <1Ω."),
                },
                SubCheck {
                    label: "Twist T_7 on pins 3/4 intact (no untwisted sections)",
                    detail: None,
                },
            ],
        },
        RepairStep {
            label: "Inspect CAN_SW inline connector (TE 205203-3)",
            detail: "TE Superseal 2-pin inline halfway between Steering_Wheel_M\n\
                     and the REECU side of the CAN tree.",
            action: RepairAction::Inspect,
            diagram: Some(diagram_can_sw_inline()),
            checks: vec![
                SubCheck {
                    label: "Connector fully seated, retainer locked",
                    detail: None,
                },
                SubCheck {
                    label: "No bent / pushed-back / corroded pins",
                    detail: None,
                },
                SubCheck {
                    label: "Tug-test each wire at the back of the housing",
                    detail: None,
                },
                SubCheck {
                    label: "Backshell 1991253-9 not cracked, no strain on wires",
                    detail: None,
                },
            ],
        },
        RepairStep {
            label: "Verify CAN_SW termination and pair integrity",
            detail: "CAN_SW is a separate bus from APP_CAN — it has its own\n\
                     terminators. Without proper termination the wheel module's\n\
                     frames don't make it to the REECU.",
            action: RepairAction::Inspect,
            diagram: None,
            checks: vec![
                SubCheck {
                    label: "Multimeter: ~60Ω across CAN_SW pins 2/7 (terminators in)",
                    detail: Some("Two 120Ω terminators in parallel. Power off."),
                },
                SubCheck {
                    label: "No short to GND on either CAN_H or CAN_L",
                    detail: Some("CAN_SW pin 2 → GND and pin 7 → GND, expect open."),
                },
                SubCheck {
                    label: "No abrasion / pinch points along the CAN_SW run",
                    detail: None,
                },
            ],
        },
        RepairStep {
            label: "Cross-check on the REECU side (APP_CAN re-broadcast)",
            detail: "If CAN_SW is healthy but TS_PRIM_CMD/TS_SEC_CMD show no\n\
                     change when buttons are pressed, the REECU isn't relaying\n\
                     the signal — separate fault from a wiring problem.",
            action: RepairAction::Inspect,
            diagram: None,
            checks: vec![
                SubCheck {
                    label: "Dashboard's APP_CAN rate row shows non-zero traffic",
                    detail: None,
                },
                SubCheck {
                    label: "0x001 and 0x002 land on APP_CAN (run candump on host)",
                    detail: Some("candump $APP_CAN,001:7FF and 002:7FF, both should arrive."),
                },
                SubCheck {
                    label: "If 0x001/0x002 are missing → REECU gateway issue, not harness",
                    detail: Some("Check the gateway container, then reboot the REECU."),
                },
            ],
        },
    ]
}

/// Parse the standard `BUS=...` / `RC=...` echo trailer used by the XCP repair
/// commands. Returns (rc, bus, detail) where `detail` is everything else from
/// stdout joined into one line.
pub fn parse_rc_trailer(stdout: &str) -> (Option<i32>, Option<String>, String) {
    let mut rc: Option<i32> = None;
    let mut bus: Option<String> = None;
    let mut other: Vec<&str> = Vec::new();
    for line in stdout.lines() {
        if let Some(rest) = line.strip_prefix("RC=") {
            rc = rest.trim().parse::<i32>().ok();
        } else if let Some(rest) = line.strip_prefix("BUS=") {
            bus = Some(rest.trim().to_string());
        } else if !line.trim().is_empty() {
            other.push(line);
        }
    }
    (rc, bus, other.join(" ").trim().to_string())
}
