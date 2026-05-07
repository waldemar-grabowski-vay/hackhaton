// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

use std::collections::HashSet;
use std::sync::Arc;

use serde::Deserialize;

use crate::checks::{fail_one, Category, Check, CheckFuture, CheckResult, Outcome, PlannedRow};
use crate::inventory::HostKind;
use crate::ssh::{run_remote, SshTarget};

const EXPECTED_USB_YAML: &str = include_str!("../../config/expected_usb.yaml");

#[derive(Debug, Deserialize, Default)]
struct ExpectedUsbConfig {
    #[serde(default)]
    marmot: Vec<ExpectedUsb>,
    #[serde(default)]
    qebra: Vec<ExpectedUsb>,
}

#[derive(Debug, Deserialize, Clone)]
struct ExpectedUsb {
    vid_pid: String,
    name: String,
}

#[derive(Debug, Clone)]
struct UsbDevice {
    vid_pid: String,
    name: String,
}

fn parse_lsusb(out: &str) -> Vec<UsbDevice> {
    let mut v = Vec::new();
    for line in out.lines() {
        if line.contains("root hub") {
            continue;
        }
        let Some(idx) = line.find(" ID ") else { continue };
        let rest = &line[idx + 4..];
        if rest.len() < 9 || rest.as_bytes().get(4) != Some(&b':') {
            continue;
        }
        v.push(UsbDevice {
            vid_pid: rest[..9].to_string(),
            name: rest[9..].trim().to_string(),
        });
    }
    v
}

fn expected_for(kind: HostKind) -> Vec<ExpectedUsb> {
    let cfg: ExpectedUsbConfig = serde_yaml::from_str(EXPECTED_USB_YAML).unwrap_or_default();
    match kind {
        HostKind::Ts => cfg.marmot,
        HostKind::Ve => cfg.qebra,
    }
}

pub fn usb_inventory_check(planned: Vec<PlannedRow>, kind: HostKind) -> Check {
    Check {
        category: Category::Usb,
        planned,
        run: Box::new(move |target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                let result = match run_remote(&target, "lsusb").await {
                    Ok(r) if r.ok() => {
                        let devices = parse_lsusb(&r.stdout);
                        let expected = expected_for(kind);

                        let exp_keys: HashSet<&str> =
                            expected.iter().map(|e| e.vid_pid.as_str()).collect();
                        let dev_keys: HashSet<&str> =
                            devices.iter().map(|d| d.vid_pid.as_str()).collect();

                        let extras: Vec<&UsbDevice> = devices
                            .iter()
                            .filter(|d| !exp_keys.contains(d.vid_pid.as_str()))
                            .collect();
                        let missing: Vec<&ExpectedUsb> = expected
                            .iter()
                            .filter(|e| !dev_keys.contains(e.vid_pid.as_str()))
                            .collect();

                        let outcome = if !missing.is_empty() {
                            Outcome::Fail
                        } else if !extras.is_empty() {
                            Outcome::Warn
                        } else {
                            Outcome::Ok
                        };

                        let summary = if missing.is_empty() && extras.is_empty() {
                            format!("{} devices, all expected", devices.len())
                        } else {
                            let mut parts = Vec::new();
                            if !missing.is_empty() {
                                let m: Vec<String> = missing.iter()
                                    .map(|e| format!("{} ({})", e.vid_pid, e.name))
                                    .collect();
                                parts.push(format!("missing: {}", m.join(", ")));
                            }
                            if !extras.is_empty() {
                                let e: Vec<String> = extras.iter()
                                    .map(|d| format!("{} ({})", d.vid_pid, d.name))
                                    .collect();
                                parts.push(format!("extras: {}", e.join(", ")));
                            }
                            parts.join("; ")
                        };

                        CheckResult { id: row.id, category, name: row.name.into(), outcome, summary, raw: r.stdout }
                    }
                    Ok(r) => fail_one(&row, category, format!("lsusb failed (exit {:?})", r.exit_code), &r.stderr),
                    Err(e) => fail_one(&row, category, format!("ssh error: {}", e), e.to_string()),
                };
                vec![result]
            })
        }),
    }
}
