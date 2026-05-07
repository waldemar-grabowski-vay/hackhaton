// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

pub mod cameras;
pub mod connectivity;
pub mod decode;
pub mod reecu;
pub mod usb;

use std::future::Future;
use std::pin::Pin;
use std::sync::Arc;

use crate::ssh::SshTarget;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Outcome {
    Ok,
    Warn,
    Fail,
    Pending,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Category {
    Reecu,
    Usb,
    Cameras,
    Connectivity,
}

impl Category {
    pub fn label(self) -> &'static str {
        match self {
            Category::Reecu => "REECU",
            Category::Usb => "USB",
            Category::Cameras => "Cameras",
            Category::Connectivity => "Connectivity",
        }
    }
}

#[derive(Debug, Clone)]
pub struct CheckResult {
    pub id: usize,
    pub category: Category,
    pub name: String,
    pub outcome: Outcome,
    pub summary: String,
    // Reserved for a future "show raw" UI affordance. Set by every check
    // (so the data is captured) but not yet rendered anywhere.
    #[allow(dead_code)]
    pub raw: String,
}

#[derive(Debug, Clone)]
pub struct PlannedRow {
    pub id: usize,
    pub name: &'static str,
}

pub type CheckFuture = Pin<Box<dyn Future<Output = Vec<CheckResult>> + Send>>;

pub struct Check {
    pub category: Category,
    pub planned: Vec<PlannedRow>,
    pub run: Box<dyn Fn(Arc<SshTarget>, Category, Vec<PlannedRow>) -> CheckFuture + Send + Sync>,
}

pub fn all_checks(kind: crate::inventory::HostKind) -> Vec<Check> {
    use crate::inventory::HostKind;
    let mut next_id = 0usize;
    let mut alloc = |names: &[&'static str]| -> Vec<PlannedRow> {
        names
            .iter()
            .map(|n| {
                let id = next_id;
                next_id += 1;
                PlannedRow { id, name: n }
            })
            .collect()
    };

    let mut checks = vec![
        connectivity::reach_check(alloc(&["SSH reachable"])),
        connectivity::host_type_check(alloc(&["Host type"]), kind),
        connectivity::dns_resolver_check(alloc(&["DNS resolver"])),
        connectivity::dns_resolve_check(alloc(&[
            "api.prod.reeapis.com",
            "lobby.prod.reeapis.com",
            "tdms.prod.reeapis.com",
            "cloud-telemetry.prod.reeapis.com",
        ])),
        reecu::vdrive_release_drift_check(alloc(&["vDrive package vs manifest"]), kind),
        reecu::reecu_gateway_container_check(alloc(&["REECU gateway container"])),
        reecu::can_buses_check(alloc(&["CAN buses"])),
        reecu::app_can_rate_check(alloc(&["APP_CAN traffic"])),
        reecu::xcp_traffic_check(alloc(&["XCP traffic"]), kind),
        reecu::reecu_heartbeat_check(alloc(&["REECU heartbeat"]), kind),
        reecu::sas_calibration_check(alloc(&["SAS calibration"]), kind),
        reecu::gnss_fusion_yaw_rate_check(alloc(&["gnss_fusion yaw rate"]), kind),
        reecu::lobby_polling_loop_check(alloc(&["Lobby polling loop"]), kind),
        reecu::session_node_liveness_check(alloc(&["Session ROS nodes alive"])),
        reecu::gateway_log_errors_check(alloc(&["Gateway log errors (5m)"])),
    ];
    match kind {
        HostKind::Ts => {
            checks.push(reecu::ts_state_msg_decoder(alloc(&["TS_SYSTEM_STATE (0x004)"])));
            checks.push(reecu::ts_sec_telemetry_decoder(alloc(&[
                "Aurix MCU firmware",
                "SEC FPGA gateware",
                "REECU hardware rev",
                "TS_SEC_STATE (0x050)",
            ])));
            checks.push(reecu::ts_prim_cmd_decoder(alloc(&[
                "TS e-Stop button",
                "TS latency monitor",
                "TS camera latency",
                "TS telemetry latency",
                "TS brake pedal channels",
                "TS accelerator pedal channels",
                "TS steering channels",
                "TS e-Stop button channels",
                "TS turn indicator",
            ])));
            checks.push(reecu::ts_sec_cmd_decoder(alloc(&[
                "TS horn",
                "TS front wiper",
                "TS rear wiper",
                "TS wiper interval vol",
            ])));
        }
        HostKind::Ve => {
            checks.push(reecu::ve_sec_telemetry_decoder(alloc(&[
                "Aurix MCU firmware",
                "SEC FPGA gateware",
                "REECU hardware rev",
                "VE_SEC_STATE (0x011)",
            ])));
            checks.push(reecu::ve_prim_telemetry_decoder(alloc(&[
                "VE_EPB_ERR",
                "VE_EPAS_CRITICAL_ERR",
                "VE_EPAS_ERR",
                "VE_BRAKE_ERR",
                "VE_ENGINE_ERR",
                "VE_AIRBAG_ERR",
                "VE_BMS_ERR",
                "VE_TIND_ERR",
                "VE latency monitor",
                "VE cmd latency",
                "VE e2e latency",
            ])));
        }
    }
    checks.push(usb::usb_inventory_check(alloc(&["USB inventory vs expected"]), kind));
    checks
}

// --- shared error helpers ---------------------------------------------------

pub(super) fn fail_one(
    row: &PlannedRow,
    category: Category,
    summary: impl Into<String>,
    raw: impl Into<String>,
) -> CheckResult {
    CheckResult {
        id: row.id,
        category,
        name: row.name.into(),
        outcome: Outcome::Fail,
        summary: summary.into(),
        raw: raw.into(),
    }
}

pub(super) fn warn_one(
    row: &PlannedRow,
    category: Category,
    summary: impl Into<String>,
    raw: impl Into<String>,
) -> CheckResult {
    CheckResult {
        id: row.id,
        category,
        name: row.name.into(),
        outcome: Outcome::Warn,
        summary: summary.into(),
        raw: raw.into(),
    }
}

pub(super) fn fail_all(planned: &[PlannedRow], category: Category, summary: impl Into<String>) -> Vec<CheckResult> {
    let s: String = summary.into();
    planned.iter().map(|row| fail_one(row, category, s.clone(), "")).collect()
}

pub(super) fn warn_all(planned: &[PlannedRow], category: Category, summary: impl Into<String>) -> Vec<CheckResult> {
    let s: String = summary.into();
    planned.iter().map(|row| warn_one(row, category, s.clone(), "")).collect()
}
