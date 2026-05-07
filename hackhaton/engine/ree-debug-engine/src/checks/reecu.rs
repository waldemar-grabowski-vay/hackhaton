// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

use std::sync::Arc;

use crate::checks::decode::{decode_bit, decode_bits, parse_candump_frame};
use crate::checks::{
    fail_all, fail_one, warn_all, Category, Check, CheckFuture, CheckResult, Outcome, PlannedRow,
};
use crate::inventory::HostKind;
use crate::ssh::{run_remote, SshTarget};

// --- Single-frame, single-row checks ---------------------------------------

pub fn reecu_gateway_container_check(planned: Vec<PlannedRow>) -> Check {
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                // On TS the OosOps containers are owned by user `ree`; on VE
                // there's no `ree` user so we run docker as root. Try -u ree
                // first, fall back to plain sudo.
                let cmd = "(sudo -n -u ree docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null \
                            || sudo -n docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null) \
                           | grep oos_reecu_gateway || true";
                let result = match run_remote(&target, cmd).await {
                    Ok(r) if r.ok() => {
                        let line = r.stdout.trim().to_string();
                        if line.is_empty() {
                            fail_one(&row, category, "container not found", &r.stdout)
                        } else {
                            let outcome = if line.contains("Up ") { Outcome::Ok } else { Outcome::Warn };
                            CheckResult {
                                id: row.id, category, name: row.name.into(),
                                outcome, summary: line.clone(), raw: line,
                            }
                        }
                    }
                    Ok(r) => fail_one(&row, category, format!("docker ps failed (exit {:?})", r.exit_code), &r.stderr),
                    Err(e) => fail_one(&row, category, format!("ssh error: {}", e), e.to_string()),
                };
                vec![result]
            })
        }),
    }
}

pub fn can_buses_check(planned: Vec<PlannedRow>) -> Check {
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                let cmd = "ip -br link show type can; echo ---; cat /etc/ree/can_bus_map 2>/dev/null";
                let result = match run_remote(&target, cmd).await {
                    Ok(r) if r.ok() => {
                        let parts: Vec<&str> = r.stdout.split("---").collect();
                        let links = parts.first().copied().unwrap_or("");
                        let map = parts.get(1).copied().unwrap_or("");
                        let app_can = pick(map, "CAN_BUS_APP_CAN");
                        let xcp = pick(map, "CAN_BUS_XCP");
                        let mut up = 0usize;
                        let mut down = 0usize;
                        for line in links.lines() {
                            if line.contains(" UP ") { up += 1; }
                            else if line.contains("DOWN") { down += 1; }
                        }
                        let app_state = app_can.as_ref()
                            .and_then(|b| links.lines().find(|l| l.starts_with(b)))
                            .map(|l| if l.contains(" UP ") { "UP" } else { "DOWN" })
                            .unwrap_or("?");
                        let outcome = if app_state == "UP" { Outcome::Ok } else { Outcome::Fail };
                        CheckResult {
                            id: row.id, category, name: row.name.into(), outcome,
                            summary: format!("APP_CAN={} ({}), XCP={}, {} up / {} down",
                                opt(&app_can), app_state, opt(&xcp), up, down),
                            raw: r.stdout,
                        }
                    }
                    Ok(r) => fail_one(&row, category, format!("probe failed (exit {:?})", r.exit_code), &r.stderr),
                    Err(e) => fail_one(&row, category, format!("ssh error: {}", e), e.to_string()),
                };
                vec![result]
            })
        }),
    }
}

pub fn app_can_rate_check(planned: Vec<PlannedRow>) -> Check {
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                let cmd = "BUS=$(grep CAN_BUS_APP_CAN /etc/ree/can_bus_map | cut -d= -f2); \
                           [ -n \"$BUS\" ] || { echo 'no APP_CAN bus mapped' >&2; exit 1; }; \
                           A=$(cat /sys/class/net/$BUS/statistics/rx_packets); \
                           sleep 1; \
                           B=$(cat /sys/class/net/$BUS/statistics/rx_packets); \
                           ERR=$(cat /sys/class/net/$BUS/statistics/rx_errors); \
                           echo \"bus=$BUS rate=$((B - A)) rx_err=$ERR\"";
                let result = match run_remote(&target, cmd).await {
                    Ok(r) if r.ok() => {
                        let line = r.stdout.trim().to_string();
                        let rate = pick_kv(&line, "rate").and_then(|v| v.parse::<u64>().ok()).unwrap_or(0);
                        let err = pick_kv(&line, "rx_err").and_then(|v| v.parse::<u64>().ok()).unwrap_or(0);
                        let outcome = if rate == 0 { Outcome::Fail }
                                      else if err > 0 { Outcome::Warn }
                                      else { Outcome::Ok };
                        CheckResult {
                            id: row.id, category, name: row.name.into(), outcome,
                            summary: format!("{} msgs/s, rx_errors={}", rate, err),
                            raw: r.stdout,
                        }
                    }
                    Ok(r) => fail_one(&row, category, format!("rate sample failed (exit {:?})", r.exit_code), &r.stderr),
                    Err(e) => fail_one(&row, category, format!("ssh error: {}", e), e.to_string()),
                };
                vec![result]
            })
        }),
    }
}

/// Active XCP probe: send a CONNECT REQUEST (CAN ID 0x790, payload 0xFF 0x00)
/// and listen for the REECU's CONNECT_RESPONSE on 0x791. Bus is taken from
/// `/etc/ree/can_bus_map::CAN_BUS_XCP`, falling back to `can2` on TS / `can1`
/// on VE per the platform default.
pub fn xcp_traffic_check(planned: Vec<PlannedRow>, kind: HostKind) -> Check {
    let default_bus: &'static str = match kind {
        HostKind::Ts => "can2",
        HostKind::Ve => "can1",
    };
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(move |target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                let cmd = format!(
                    "BUS=$(grep ^CAN_BUS_XCP= /etc/ree/can_bus_map 2>/dev/null | cut -d= -f2); \
                     [ -n \"$BUS\" ] || BUS={default_bus}; \
                     DUMP=$(mktemp); \
                     ( timeout 2 candump -n 1 \"$BUS,791:7FF\" >\"$DUMP\" 2>&1 ) & PID=$!; \
                     sleep 0.15; \
                     cansend \"$BUS\" 790##0FF00 2>&1; SEND_RC=$?; \
                     wait $PID 2>/dev/null; \
                     echo \"BUS=$BUS\"; \
                     echo \"SEND_RC=$SEND_RC\"; \
                     echo ---; \
                     cat \"$DUMP\"; \
                     rm -f \"$DUMP\""
                );
                let result = match run_remote(&target, &cmd).await {
                    Ok(r) if r.ok() => {
                        let stdout = &r.stdout;
                        let bus = pick(stdout, "BUS").unwrap_or_else(|| default_bus.to_string());
                        let send_rc = pick(stdout, "SEND_RC").unwrap_or_else(|| "?".into());
                        let parts: Vec<&str> = stdout.split("---").collect();
                        let dump = parts.get(1).copied().unwrap_or("");
                        if send_rc != "0" {
                            fail_one(
                                &row,
                                category,
                                format!("cansend on {} failed (rc={})", bus, send_rc),
                                stdout,
                            )
                        } else if let Some(line) = dump.lines().find(|l| {
                            let t = l.trim_start();
                            t.starts_with(&bus) && t.contains(" 791 ")
                        }) {
                            CheckResult {
                                id: row.id,
                                category,
                                name: row.name.into(),
                                outcome: Outcome::Ok,
                                summary: format!("REECU CONNECT_RESPONSE on {}", bus),
                                raw: line.trim().to_string(),
                            }
                        } else {
                            fail_one(
                                &row,
                                category,
                                format!("no REECU CONNECT_RESPONSE on {} within 2s", bus),
                                stdout,
                            )
                        }
                    }
                    Ok(r) => fail_one(
                        &row,
                        category,
                        format!("probe failed (exit {:?})", r.exit_code),
                        &r.stderr,
                    ),
                    Err(e) => fail_one(&row, category, format!("ssh error: {}", e), e.to_string()),
                };
                vec![result]
            })
        }),
    }
}

pub fn reecu_heartbeat_check(planned: Vec<PlannedRow>, kind: HostKind) -> Check {
    let (msg_id, msg_name) = match kind {
        HostKind::Ts => (0x004u32, "TS_STATE_MSG"),
        HostKind::Ve => (0x010u32, "VE_PRIM_TELEMETRY_MSG"),
    };
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(move |target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                let cmd = format!(
                    "BUS=$(grep CAN_BUS_APP_CAN /etc/ree/can_bus_map | cut -d= -f2); \
                     [ -n \"$BUS\" ] || exit 1; \
                     timeout 2 candump $BUS,{:X}:7FF -n 1 -t a 2>/dev/null || true",
                    msg_id,
                );
                let result = match run_remote(&target, &cmd).await {
                    Ok(r) if r.ok() => {
                        let line = r.stdout.trim().to_string();
                        if line.is_empty() {
                            fail_one(&row, category, format!("no {} (0x{:03X}) within 2s", msg_name, msg_id), &r.stdout)
                        } else {
                            CheckResult {
                                id: row.id, category, name: row.name.into(),
                                outcome: Outcome::Ok,
                                summary: format!("{} (0x{:03X}) flowing", msg_name, msg_id),
                                raw: line,
                            }
                        }
                    }
                    Ok(r) => fail_one(&row, category, format!("candump failed (exit {:?})", r.exit_code), &r.stderr),
                    Err(e) => fail_one(&row, category, format!("ssh error: {}", e), e.to_string()),
                };
                vec![result]
            })
        }),
    }
}

/// TS lobby polling-loop detector: count `Checking session status` log lines
/// over the last 30s and look for any progression event (`session started`,
/// `software settings up to date`). Many polls + zero progression = stuck
/// loop, the symptom we hit all of 2026-04-30. TS-only; n/a on VE.
pub fn lobby_polling_loop_check(planned: Vec<PlannedRow>, kind: HostKind) -> Check {
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(move |target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                if matches!(kind, HostKind::Ve) {
                    return vec![CheckResult {
                        id: row.id,
                        category,
                        name: row.name.into(),
                        outcome: Outcome::Ok,
                        summary: "n/a (vehicle)".into(),
                        raw: String::new(),
                    }];
                }
                let cmd = "(sudo -n -u ree docker logs --since 30s oosops-lobby-1 2>&1 \
                           || sudo -n docker logs --since 30s oosops-lobby-1 2>&1) \
                           | awk '/Checking session status/{c++} \
                                  /session started|session ready|software settings up.to.date/{p++} \
                                  END{printf \"polls=%d progress=%d\\n\", c+0, p+0}'";
                let result = match run_remote(&target, cmd).await {
                    Ok(r) if r.ok() => {
                        let line = r.stdout.trim();
                        let polls = pick_kv(line, "polls")
                            .and_then(|v| v.parse::<u64>().ok())
                            .unwrap_or(0);
                        let progress = pick_kv(line, "progress")
                            .and_then(|v| v.parse::<u64>().ok())
                            .unwrap_or(0);
                        let (outcome, summary) = if polls == 0 {
                            (Outcome::Ok, "no polling activity (last 30s)".to_string())
                        } else if progress == 0 && polls > 5 {
                            (
                                Outcome::Fail,
                                format!("{} polls, 0 progression in last 30s — stuck", polls),
                            )
                        } else {
                            (
                                Outcome::Ok,
                                format!("polls={}, progress={} (last 30s)", polls, progress),
                            )
                        };
                        CheckResult {
                            id: row.id,
                            category,
                            name: row.name.into(),
                            outcome,
                            summary,
                            raw: r.stdout,
                        }
                    }
                    Ok(r) => fail_one(
                        &row,
                        category,
                        format!("docker logs failed (exit {:?})", r.exit_code),
                        &r.stderr,
                    ),
                    Err(e) => fail_one(
                        &row,
                        category,
                        format!("ssh error: {}", e),
                        e.to_string(),
                    ),
                };
                vec![result]
            })
        }),
    }
}

/// Per-session ROS node liveness: scan all `/opt/ree-drive/lib/ree_*` node
/// processes, compare CPU-time vs wall-time. A node with wall ≥ 30s but
/// CPU < 1s is stuck in init (today's `ts_telemetry_streamer_node`
/// signature: futex_wait on a subscription that never publishes).
pub fn session_node_liveness_check(planned: Vec<PlannedRow>) -> Check {
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                // ps emits one line per matching node: "comm etime_s cputime"
                // where cputime is "[[DD-]HH:]MM:SS".
                let cmd = "for p in $(pgrep -f '/opt/ree-drive/lib/ree_' 2>/dev/null); do \
                           ps -p $p -o comm=,etimes=,cputime= --no-headers 2>/dev/null; \
                           done";
                let result = match run_remote(&target, cmd).await {
                    Ok(r) if r.ok() => {
                        let trimmed = r.stdout.trim();
                        if trimmed.is_empty() {
                            CheckResult {
                                id: row.id,
                                category,
                                name: row.name.into(),
                                outcome: Outcome::Ok,
                                summary: "no session active".into(),
                                raw: r.stdout,
                            }
                        } else {
                            let mut total = 0usize;
                            let mut stuck: Vec<String> = Vec::new();
                            for line in trimmed.lines() {
                                let parts: Vec<&str> = line.split_whitespace().collect();
                                if parts.len() < 3 {
                                    continue;
                                }
                                let comm = parts[0];
                                let etime: u64 = parts[1].parse().unwrap_or(0);
                                let cputime_s = parse_hms_seconds(parts[2]);
                                total += 1;
                                if etime >= 30 && cputime_s < 1 {
                                    stuck.push(format!("{} (wall={}s)", comm, etime));
                                }
                            }
                            let outcome = if stuck.is_empty() {
                                Outcome::Ok
                            } else {
                                Outcome::Fail
                            };
                            let summary = if stuck.is_empty() {
                                format!("{} session nodes healthy", total)
                            } else {
                                format!(
                                    "{}/{} stuck-in-init: {}",
                                    stuck.len(),
                                    total,
                                    stuck.join(", ")
                                )
                            };
                            CheckResult {
                                id: row.id,
                                category,
                                name: row.name.into(),
                                outcome,
                                summary,
                                raw: r.stdout,
                            }
                        }
                    }
                    Ok(r) => fail_one(
                        &row,
                        category,
                        format!("ps query failed (exit {:?})", r.exit_code),
                        &r.stderr,
                    ),
                    Err(e) => fail_one(
                        &row,
                        category,
                        format!("ssh error: {}", e),
                        e.to_string(),
                    ),
                };
                vec![result]
            })
        }),
    }
}

fn parse_hms_seconds(s: &str) -> u64 {
    // ps cputime: "[[DD-]HH:]MM:SS"
    let (days, rest) = match s.split_once('-') {
        Some((d, r)) => (d.parse::<u64>().unwrap_or(0), r),
        None => (0, s),
    };
    let parts: Vec<u64> = rest.split(':').map(|p| p.parse::<u64>().unwrap_or(0)).collect();
    let hms = match parts.len() {
        3 => parts[0] * 3600 + parts[1] * 60 + parts[2],
        2 => parts[0] * 60 + parts[1],
        1 => parts[0],
        _ => 0,
    };
    days * 86400 + hms
}

/// SAS (Bourns Steering Angle Sensor) calibration check — TS-only.
///
/// The Bourns sensor sends `SASn_DATA` (CAN ID `0x11F`, 5 bytes, 100 Hz) to
/// the TS_SAFETY_ECU. Per the DBC (`bourns_sas{0,1}.dbc`):
/// - bit 24 = `SAS_STATUS_OK` (1 = OK)
/// - bit 25 = `SAS_STATUS_CAL` (1 = CALIBRATED)
/// - bit 26 = `SAS_STATUS_TRIM` (1 = factory trim)
///
/// The frame may not be on the application CAN bus — sometimes the SAS is on
/// a private bus only the safety ECU sees. We scan every UP CAN interface;
/// if none carries `0x11F`, we Warn rather than Fail (the operator may need
/// to confirm calibration through the safety ECU directly).
pub fn sas_calibration_check(planned: Vec<PlannedRow>, kind: HostKind) -> Check {
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(move |target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                if matches!(kind, HostKind::Ve) {
                    return vec![CheckResult {
                        id: row.id,
                        category,
                        name: row.name.into(),
                        outcome: Outcome::Ok,
                        summary: "n/a (vehicle)".into(),
                        raw: String::new(),
                    }];
                }
                // Scan all UP CAN ifaces for one 0x11F frame.
                let cmd = "ARGS=''; for b in $(ls /sys/class/net/ 2>/dev/null | grep -E '^can[0-9]+$'); do \
                           s=$(cat /sys/class/net/$b/operstate 2>/dev/null); \
                           [ \"$s\" = up ] && ARGS=\"$ARGS $b,11F:7FF\"; \
                           done; \
                           [ -z \"$ARGS\" ] && { echo NO_UP_BUSES; exit 0; }; \
                           FRAME=$(timeout 2 candump -n 1 $ARGS 2>/dev/null); \
                           echo \"FRAME=$FRAME\"";
                let result = match run_remote(&target, cmd).await {
                    Ok(r) if r.ok() => {
                        if r.stdout.contains("NO_UP_BUSES") {
                            return vec![fail_one(
                                &row,
                                category,
                                "no UP CAN interface on host",
                                &r.stdout,
                            )];
                        }
                        let frame_line = r
                            .stdout
                            .lines()
                            .find_map(|l| l.strip_prefix("FRAME="))
                            .unwrap_or("")
                            .trim();
                        if frame_line.is_empty() {
                            return vec![CheckResult {
                                id: row.id,
                                category,
                                name: row.name.into(),
                                outcome: Outcome::Warn,
                                summary: "0x11F not seen on host CAN within 2s — verify via safety ECU".into(),
                                raw: r.stdout,
                            }];
                        }
                        let bytes = parse_candump_frame(frame_line);
                        if bytes.len() < 5 {
                            return vec![fail_one(
                                &row,
                                category,
                                "candump frame parse failed",
                                &r.stdout,
                            )];
                        }
                        let ok_bit = decode_bit(&bytes, 24);
                        let cal = decode_bit(&bytes, 25);
                        let trim = decode_bit(&bytes, 26);
                        let outcome = match (cal, ok_bit) {
                            (true, true) => Outcome::Ok,
                            (true, false) => Outcome::Warn,
                            (false, _) => Outcome::Fail,
                        };
                        let summary = format!(
                            "{} (ok={}, trim={})",
                            if cal { "CALIBRATED" } else { "NOT_CALIBRATED" },
                            ok_bit as u8,
                            trim as u8,
                        );
                        CheckResult {
                            id: row.id,
                            category,
                            name: row.name.into(),
                            outcome,
                            summary,
                            raw: r.stdout,
                        }
                    }
                    Ok(r) => fail_one(
                        &row,
                        category,
                        format!("candump scan failed (exit {:?})", r.exit_code),
                        &r.stderr,
                    ),
                    Err(e) => fail_one(
                        &row,
                        category,
                        format!("ssh error: {}", e),
                        e.to_string(),
                    ),
                };
                vec![result]
            })
        }),
    }
}

/// Watchdog for VE `oos_gnss_fusion_node`'s "Yaw rate input is unavailable"
/// log pattern. VE-only — on TS the node doesn't run, so we report n/a.
///
/// Why this matters: when yaw rate doesn't reach gnss_fusion, VE never
/// publishes fused pose, TS's gnss_fusion has no input, and the in-session
/// `ts_telemetry_streamer_node` blocks forever on `/telestation/fused_gnss_pose`
/// — exactly the "session won't initialize" symptom we traced 2026-04-30.
/// The node logs the warning once per second when stuck, so ≥3 hits in a 5s
/// window is a confident Fail.
pub fn gnss_fusion_yaw_rate_check(planned: Vec<PlannedRow>, kind: HostKind) -> Check {
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(move |target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                if matches!(kind, HostKind::Ts) {
                    return vec![CheckResult {
                        id: row.id,
                        category,
                        name: row.name.into(),
                        outcome: Outcome::Ok,
                        summary: "n/a (telestation)".into(),
                        raw: String::new(),
                    }];
                }
                // gnss_fusion on VE runs as root-owned docker (no `ree` user).
                let cmd = "sudo -n docker logs --since 5s oosops-gnss_fusion-1 2>&1 \
                           | grep -c 'Yaw rate input is unavailable' || true";
                let result = match run_remote(&target, cmd).await {
                    Ok(r) if r.ok() => {
                        let count: u64 = r.stdout.trim().parse().unwrap_or(0);
                        let (outcome, summary) = match count {
                            0 => (Outcome::Ok, "no yaw-rate warnings (last 5s)".into()),
                            1..=2 => (
                                Outcome::Warn,
                                format!("{} yaw-rate warnings in last 5s", count),
                            ),
                            _ => (
                                Outcome::Fail,
                                format!(
                                    "yaw rate unavailable — {} warnings in last 5s",
                                    count
                                ),
                            ),
                        };
                        CheckResult {
                            id: row.id,
                            category,
                            name: row.name.into(),
                            outcome,
                            summary,
                            raw: r.stdout,
                        }
                    }
                    Ok(r) => fail_one(
                        &row,
                        category,
                        format!("docker logs failed (exit {:?})", r.exit_code),
                        &r.stderr,
                    ),
                    Err(e) => fail_one(
                        &row,
                        category,
                        format!("ssh error: {}", e),
                        e.to_string(),
                    ),
                };
                vec![result]
            })
        }),
    }
}

pub fn gateway_log_errors_check(planned: Vec<PlannedRow>) -> Check {
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                // Capture the most recent ERROR line alongside the counts so
                // a non-technical user sees what's actually failing without
                // SSH-ing in to read the logs themselves.
                let cmd = "(sudo -n -u ree docker logs --since 5m oosops-oos_reecu_gateway-1 2>/dev/null \
                            || sudo -n docker logs --since 5m oosops-oos_reecu_gateway-1 2>&1) \
                           | awk '/\\[ERROR\\]/ {e++; last=$0} /\\[ WARN\\]/ {w++} \
                                  END {printf \"err=%d warn=%d\\n\", e+0, w+0; \
                                       if (last) printf \"last=%s\\n\", last}'";
                let result = match run_remote(&target, cmd).await {
                    Ok(r) if r.ok() => {
                        let counts_line = r.stdout.lines().next().unwrap_or("").trim().to_string();
                        let err = pick_kv(&counts_line, "err").and_then(|v| v.parse::<u64>().ok()).unwrap_or(0);
                        let warn = pick_kv(&counts_line, "warn").and_then(|v| v.parse::<u64>().ok()).unwrap_or(0);
                        let last = r.stdout
                            .lines()
                            .find_map(|l| l.strip_prefix("last="))
                            .map(|s| s.trim().to_string())
                            .unwrap_or_default();
                        let outcome = match err {
                            0 => Outcome::Ok,
                            1..=2 => Outcome::Warn,
                            _ => Outcome::Fail,
                        };
                        let summary = if err > 0 && !last.is_empty() {
                            format!("ERROR={}, WARN={} — last: {}", err, warn, truncate_err(&last))
                        } else {
                            format!("ERROR={}, WARN={}", err, warn)
                        };
                        CheckResult {
                            id: row.id, category, name: row.name.into(), outcome,
                            summary,
                            raw: r.stdout,
                        }
                    }
                    Ok(r) => fail_one(&row, category, format!("docker logs failed (exit {:?})", r.exit_code), &r.stderr),
                    Err(e) => fail_one(&row, category, format!("ssh error: {}", e), e.to_string()),
                };
                vec![result]
            })
        }),
    }
}

// --- TS-side DBC-driven decoders -------------------------------------------

const CANDUMP_PROLOGUE: &str =
    "BUS=$(grep CAN_BUS_APP_CAN /etc/ree/can_bus_map | cut -d= -f2); [ -n \"$BUS\" ] || exit 1;";

fn capture_cmd(msg_id: u32) -> String {
    format!(
        "{} timeout 2 candump -n 1 $BUS,{:X}:7FF 2>/dev/null || true",
        CANDUMP_PROLOGUE, msg_id
    )
}

/// TS_STATE_MSG (0x004) — TS_SYSTEM_STATE at bits 0..5 (5-bit enum).
pub fn ts_state_msg_decoder(planned: Vec<PlannedRow>) -> Check {
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                match run_remote(&target, &capture_cmd(0x004)).await {
                    Ok(r) if r.ok() => {
                        let bytes = parse_candump_frame(r.stdout.trim());
                        if bytes.is_empty() {
                            return warn_all(&planned, category, "no TS_STATE_MSG (0x004) within 2s");
                        }
                        let row = planned[0].clone();
                        let v = decode_bits(&bytes, 0, 5);
                        let (label, outcome) = ts_system_state(v);
                        vec![CheckResult {
                            id: row.id, category, name: row.name.into(),
                            outcome,
                            summary: format!("{} ({})", label, v),
                            raw: r.stdout,
                        }]
                    }
                    Ok(r) => fail_all(&planned, category, format!("candump failed (exit {:?})", r.exit_code)),
                    Err(e) => fail_all(&planned, category, format!("ssh error: {}", e)),
                }
            })
        }),
    }
}

/// TS_SEC_TELEMETRY_MSG (0x050) — captures one frame and emits 4 rows:
///   0: Aurix MCU FW       — TS_SPCB_FW_VER_{MAJOR,MINOR,PATCH,BUILD_TYPE}
///   1: SEC FPGA gateware  — TS_SPCB_GW_VER_{MAJOR,MINOR,PATCH,BUILD_TYPE}
///   2: Hardware rev       — TS_SPCB_HW_VER + TS_SPCB_HW_VER_PATCH
///   3: TS_SEC_STATE       — bits 0..8
///
/// Build-type per DBC VAL_TABLE:
///   FW_BUILD_TYPE_TABLE:  0=Vehicle, 1=TS
///   SEC_BUILD_TYPE_TABLE: 0=UNSAFE, 1=VEHICLE, 2=TS, 3=INVALID
pub fn ts_sec_telemetry_decoder(planned: Vec<PlannedRow>) -> Check {
    assert_eq!(planned.len(), 4, "ts_sec_telemetry_decoder expects 4 planned rows");
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                match run_remote(&target, &capture_cmd(0x050)).await {
                    Ok(r) if r.ok() => {
                        let bytes = parse_candump_frame(r.stdout.trim());
                        if bytes.is_empty() {
                            return warn_all(&planned, category, "no TS_SEC_TELEMETRY_MSG (0x050) within 2s");
                        }

                        let fw_build = decode_bits(&bytes, 32, 1);
                        let fw_major = decode_bits(&bytes, 104, 8);
                        let fw_minor = decode_bits(&bytes, 96, 8);
                        let fw_patch = decode_bits(&bytes, 112, 16);

                        let gw_build = decode_bits(&bytes, 24, 2);
                        let gw_major = decode_bits(&bytes, 128, 8);
                        let gw_minor = decode_bits(&bytes, 136, 8);
                        let gw_patch = decode_bits(&bytes, 144, 16);

                        let hw_major = decode_bits(&bytes, 88, 8);
                        let hw_patch = decode_bits(&bytes, 16, 8);

                        let sec_state_v = decode_bits(&bytes, 0, 8);
                        let (sec_state_label, sec_state_outcome) = ts_sec_state(sec_state_v);

                        let row = |i: usize, outcome: Outcome, summary: String| CheckResult {
                            id: planned[i].id, category, name: planned[i].name.into(),
                            outcome, summary, raw: String::new(),
                        };

                        let aurix_actual = format!("{}.{}.{}", fw_major, fw_minor, fw_patch);
                        let sec_actual = format!("{}.{}.{}", gw_major, gw_minor, gw_patch);

                        let m = crate::manifest::manifest();
                        let (aurix_summary, aurix_drift) = compose_version_summary(
                            fw_build_type(fw_build), &aurix_actual, m.reecu_ts.as_deref(),
                        );
                        let (sec_summary, sec_drift) = compose_version_summary(
                            gw_build_type(gw_build), &sec_actual, m.sec_ts.as_deref(),
                        );

                        let fw_outcome = if fw_major == 0 && fw_minor == 0 && fw_patch == 0 {
                            Outcome::Warn
                        } else if fw_build != 1 {
                            Outcome::Warn
                        } else if aurix_drift {
                            Outcome::Warn
                        } else {
                            Outcome::Ok
                        };
                        let gw_outcome = match gw_build {
                            2 if gw_major == 0 && gw_minor == 0 && gw_patch == 0 => Outcome::Warn,
                            2 if sec_drift => Outcome::Warn,
                            2 => Outcome::Ok,
                            0 | 3 => Outcome::Fail,
                            1 => Outcome::Warn,
                            _ => Outcome::Warn,
                        };
                        let hw_outcome = if hw_major == 0 { Outcome::Warn } else { Outcome::Ok };

                        vec![
                            row(0, fw_outcome, aurix_summary),
                            row(1, gw_outcome, sec_summary),
                            row(2, hw_outcome, format!("{}.{}", hw_major, hw_patch)),
                            row(3, sec_state_outcome,
                                format!("{} ({})", sec_state_label, sec_state_v)),
                        ]
                    }
                    Ok(r) => fail_all(&planned, category, format!("candump failed (exit {:?})", r.exit_code)),
                    Err(e) => fail_all(&planned, category, format!("ssh error: {}", e)),
                }
            })
        }),
    }
}

/// TS_PRIM_CMD_MSG (0x001) — captures one frame, emits 9 rows:
///   0: TS_ESTOP_BUTTON_STATE      (bit 168)
///   1: TS_LATENCY_MONITOR_STATE   (bits 393..395, 2-bit)
///   2: TS_CAMERA_LATENCY_HIGH     (bit 320)
///   3: TS_TELEMETRY_LATENCY_HIGH  (bit 322)
///   4: TS_BRAKE_PEDAL_DIAGC_COV   (bits 48..52, 4-bit)
///   5: TS_ACC_PEDAL_DIAGC_COV     (bits 104..108, 4-bit)
///   6: TS_STEERING_DIAGC_COV      (bits 160..164, 4-bit)
///   7: TS_ESTOP_BUTTON_DIAGC_COV  (bits 169..173, 4-bit)
///   8: TS_TURN_INDICATOR_STATE    (bits 176..178, 2-bit, 0=OFF/1=LEFT/2=RIGHT)
pub fn ts_prim_cmd_decoder(planned: Vec<PlannedRow>) -> Check {
    assert_eq!(planned.len(), 9, "ts_prim_cmd_decoder expects 9 planned rows");
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                match run_remote(&target, &capture_cmd(0x001)).await {
                    Ok(r) if r.ok() => {
                        let bytes = parse_candump_frame(r.stdout.trim());
                        if bytes.is_empty() {
                            return warn_all(&planned, category, "no TS_PRIM_CMD_MSG (0x001) within 2s");
                        }

                        let estop_pressed = decode_bit(&bytes, 168);
                        let lat_state = decode_bits(&bytes, 393, 2);
                        let cam_lat_high = decode_bit(&bytes, 320);
                        let tel_lat_high = decode_bit(&bytes, 322);
                        let brake_cov = decode_bits(&bytes, 48, 4);
                        let acc_cov = decode_bits(&bytes, 104, 4);
                        let steer_cov = decode_bits(&bytes, 160, 4);
                        let estop_cov = decode_bits(&bytes, 169, 4);
                        let turn_state = decode_bits(&bytes, 176, 2);

                        let row = |i: usize, outcome: Outcome, summary: String| CheckResult {
                            id: planned[i].id, category, name: planned[i].name.into(),
                            outcome, summary, raw: String::new(),
                        };

                        vec![
                            row(0,
                                if estop_pressed { Outcome::Fail } else { Outcome::Ok },
                                if estop_pressed { "PRESSED".into() } else { "RELEASED".into() }),
                            row(1, latency_monitor_outcome(lat_state),
                                format!("state={}", lat_state)),
                            row(2,
                                if cam_lat_high { Outcome::Fail } else { Outcome::Ok },
                                if cam_lat_high { "HIGH".into() } else { "OK".into() }),
                            row(3,
                                if tel_lat_high { Outcome::Fail } else { Outcome::Ok },
                                if tel_lat_high { "HIGH".into() } else { "OK".into() }),
                            { let (l, o) = diagc_cov(brake_cov); row(4, o, l.into()) },
                            { let (l, o) = diagc_cov(acc_cov);   row(5, o, l.into()) },
                            { let (l, o) = diagc_cov(steer_cov); row(6, o, l.into()) },
                            { let (l, o) = diagc_cov(estop_cov); row(7, o, l.into()) },
                            row(8, Outcome::Ok, turn_indicator_label(turn_state).into()),
                        ]
                    }
                    Ok(r) => fail_all(&planned, category, format!("candump failed (exit {:?})", r.exit_code)),
                    Err(e) => fail_all(&planned, category, format!("ssh error: {}", e)),
                }
            })
        }),
    }
}

/// TS_SEC_CMD_MSG (0x002) — captures one frame, emits 4 rows:
///   0: TS_HORN_STATE             (bit 22)
///   1: TS_FRONT_WIPER_STATE      (bits 0..3, 3-bit, OFF/MIST/INT/LOW/HI)
///   2: TS_REAR_WIPER_STATE       (bits 14..16, 2-bit, OFF/LOW/HI)
///   3: TS_WIPER_INT_VOL_STATE    (bits 3..6, 3-bit, numeric volume)
///
/// All four reflect the physical state of switches/buttons on the TS
/// steering wheel. Rows are Outcome::Ok if the message arrives — they're
/// informational, not pass/fail. Press a button and re-run with `r` to
/// confirm the value flips.
pub fn ts_sec_cmd_decoder(planned: Vec<PlannedRow>) -> Check {
    assert_eq!(planned.len(), 4, "ts_sec_cmd_decoder expects 4 planned rows");
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                match run_remote(&target, &capture_cmd(0x002)).await {
                    Ok(r) if r.ok() => {
                        let bytes = parse_candump_frame(r.stdout.trim());
                        if bytes.is_empty() {
                            return warn_all(&planned, category, "no TS_SEC_CMD_MSG (0x002) within 2s");
                        }

                        let horn = decode_bit(&bytes, 22);
                        let front_wiper = decode_bits(&bytes, 0, 3);
                        let rear_wiper = decode_bits(&bytes, 14, 2);
                        let wiper_int_vol = decode_bits(&bytes, 3, 3);

                        let row = |i: usize, outcome: Outcome, summary: String| CheckResult {
                            id: planned[i].id, category, name: planned[i].name.into(),
                            outcome, summary, raw: String::new(),
                        };

                        vec![
                            row(0, Outcome::Ok,
                                if horn { "ON".into() } else { "OFF".into() }),
                            row(1, Outcome::Ok, front_wiper_label(front_wiper).into()),
                            row(2, Outcome::Ok, rear_wiper_label(rear_wiper).into()),
                            row(3, Outcome::Ok, format!("vol={}", wiper_int_vol)),
                        ]
                    }
                    Ok(r) => fail_all(&planned, category, format!("candump failed (exit {:?})", r.exit_code)),
                    Err(e) => fail_all(&planned, category, format!("ssh error: {}", e)),
                }
            })
        }),
    }
}

/// VE_PRIM_TELEMETRY_MSG (0x010) — captures one frame and emits 11 rows:
///   0..7: VE_{EPB,EPAS_CRITICAL,EPAS,BRAKE,ENGINE,AIRBAG,BMS,TIND}_ERR (bits 96..103)
///   8:    VE_LATENCY_MONITOR_STATE (bits 244..245, 2-bit)
///   9:    VE_CMD_LATENCY_HIGH (bit 248)
///   10:   VE_E2E_LATENCY_HIGH (bit 288)
pub fn ve_prim_telemetry_decoder(planned: Vec<PlannedRow>) -> Check {
    assert_eq!(planned.len(), 11, "ve_prim_telemetry_decoder expects 11 planned rows");
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                match run_remote(&target, &capture_cmd(0x010)).await {
                    Ok(r) if r.ok() => {
                        let bytes = parse_candump_frame(r.stdout.trim());
                        if bytes.is_empty() {
                            return warn_all(&planned, category, "no VE_PRIM_TELEMETRY (0x010) within 2s");
                        }

                        let row = |i: usize, outcome: Outcome, summary: String| CheckResult {
                            id: planned[i].id, category, name: planned[i].name.into(),
                            outcome, summary, raw: String::new(),
                        };

                        // Single-bit fault flags. DBC names them *_ERR (1 = active),
                        // so default outcome is Fail when set; user can flip if
                        // production data shows the convention is inverted.
                        let bit_flags: [usize; 8] = [96, 97, 98, 99, 100, 101, 102, 103];
                        let mut results = Vec::with_capacity(11);
                        for (i, bit) in bit_flags.iter().enumerate() {
                            let v = decode_bit(&bytes, *bit);
                            results.push(row(
                                i,
                                if v { Outcome::Fail } else { Outcome::Ok },
                                if v { "SET".into() } else { "CLEAR".into() },
                            ));
                        }

                        let lat_state = decode_bits(&bytes, 244, 2);
                        results.push(row(8, latency_monitor_outcome(lat_state),
                            format!("state={}", lat_state)));

                        let cmd_lat = decode_bit(&bytes, 248);
                        results.push(row(9,
                            if cmd_lat { Outcome::Fail } else { Outcome::Ok },
                            if cmd_lat { "HIGH".into() } else { "OK".into() }));

                        let e2e_lat = decode_bit(&bytes, 288);
                        results.push(row(10,
                            if e2e_lat { Outcome::Fail } else { Outcome::Ok },
                            if e2e_lat { "HIGH".into() } else { "OK".into() }));

                        results
                    }
                    Ok(r) => fail_all(&planned, category, format!("candump failed (exit {:?})", r.exit_code)),
                    Err(e) => fail_all(&planned, category, format!("ssh error: {}", e)),
                }
            })
        }),
    }
}

/// VE_SEC_TELEMETRY_MSG (0x011) — captures one frame and emits 4 rows
/// mirroring `ts_sec_telemetry_decoder`. VE bit positions per DBC:
///   FW_BUILD bit 189 (1-bit)         GW_BUILD bit 176 (2-bit)
///   FW_MAJOR bit 160                 GW_MAJOR bit 136
///   FW_MINOR bit 168                 GW_MINOR bit 128
///   FW_PATCH bit 144 (16-bit)        GW_PATCH bit 112 (16-bit)
///   HW_VER   bit 104                 HW_PATCH bit  96
///   VE_SEC_STATE bits 48..56 (8-bit)
pub fn ve_sec_telemetry_decoder(planned: Vec<PlannedRow>) -> Check {
    assert_eq!(planned.len(), 4, "ve_sec_telemetry_decoder expects 4 planned rows");
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                match run_remote(&target, &capture_cmd(0x011)).await {
                    Ok(r) if r.ok() => {
                        let bytes = parse_candump_frame(r.stdout.trim());
                        if bytes.is_empty() {
                            return warn_all(&planned, category, "no VE_SEC_TELEMETRY (0x011) within 2s");
                        }

                        let fw_build = decode_bits(&bytes, 189, 1);
                        let fw_major = decode_bits(&bytes, 160, 8);
                        let fw_minor = decode_bits(&bytes, 168, 8);
                        let fw_patch = decode_bits(&bytes, 144, 16);

                        let gw_build = decode_bits(&bytes, 176, 2);
                        let gw_major = decode_bits(&bytes, 136, 8);
                        let gw_minor = decode_bits(&bytes, 128, 8);
                        let gw_patch = decode_bits(&bytes, 112, 16);

                        let hw_major = decode_bits(&bytes, 104, 8);
                        let hw_patch = decode_bits(&bytes, 96, 8);

                        let sec_state_v = decode_bits(&bytes, 48, 8);
                        let (sec_state_label, sec_state_outcome) = ve_sec_state(sec_state_v);

                        let aurix_actual = format!("{}.{}.{}", fw_major, fw_minor, fw_patch);
                        let sec_actual = format!("{}.{}.{}", gw_major, gw_minor, gw_patch);

                        let m = crate::manifest::manifest();
                        let (aurix_summary, aurix_drift) = compose_version_summary(
                            fw_build_type(fw_build), &aurix_actual, m.reecu_ve.as_deref(),
                        );
                        let (sec_summary, sec_drift) = compose_version_summary(
                            gw_build_type(gw_build), &sec_actual, m.sec_ve.as_deref(),
                        );

                        let row = |i: usize, outcome: Outcome, summary: String| CheckResult {
                            id: planned[i].id, category, name: planned[i].name.into(),
                            outcome, summary, raw: String::new(),
                        };

                        // For VE, FW_BUILD = 0 means "Vehicle"; GW_BUILD = 1 means "VEHICLE".
                        let fw_outcome = if fw_major == 0 && fw_minor == 0 && fw_patch == 0 {
                            Outcome::Warn
                        } else if fw_build != 0 {
                            Outcome::Warn
                        } else if aurix_drift {
                            Outcome::Warn
                        } else {
                            Outcome::Ok
                        };
                        let gw_outcome = match gw_build {
                            1 if gw_major == 0 && gw_minor == 0 && gw_patch == 0 => Outcome::Warn,
                            1 if sec_drift => Outcome::Warn,
                            1 => Outcome::Ok,
                            0 | 3 => Outcome::Fail,
                            2 => Outcome::Warn, // TS build on VE
                            _ => Outcome::Warn,
                        };
                        let hw_outcome = if hw_major == 0 { Outcome::Warn } else { Outcome::Ok };

                        vec![
                            row(0, fw_outcome, aurix_summary),
                            row(1, gw_outcome, sec_summary),
                            row(2, hw_outcome, format!("{}.{}", hw_major, hw_patch)),
                            row(3, sec_state_outcome,
                                format!("{} ({})", sec_state_label, sec_state_v)),
                        ]
                    }
                    Ok(r) => fail_all(&planned, category, format!("candump failed (exit {:?})", r.exit_code)),
                    Err(e) => fail_all(&planned, category, format!("ssh error: {}", e)),
                }
            })
        }),
    }
}

fn ve_sec_state(v: u64) -> (&'static str, Outcome) {
    // VAL_TABLE_ from application_protocol.dbc
    match v {
        0 => ("UNKNOWN_0", Outcome::Warn),
        1 => ("SAFEINIT", Outcome::Warn),
        2 => ("NORMAL", Outcome::Ok),
        4 => ("TELEOP", Outcome::Ok),
        8 => ("MCU_MRM", Outcome::Fail),
        16 => ("SEC_MRM", Outcome::Fail),
        32 => ("LIMPHOME", Outcome::Fail),
        64 => ("POWERDOWN", Outcome::Warn),
        128 => ("MIN_RISK_COND", Outcome::Fail),
        255 => ("UNKNOWN_255", Outcome::Warn),
        _ => ("UNKNOWN", Outcome::Warn),
    }
}

// --- enum / state mappings (sourced from ree-reecu-dbc/application_protocol.dbc) -----

fn ts_system_state(v: u64) -> (&'static str, Outcome) {
    match v {
        0 => ("UNINIT", Outcome::Fail),
        1 => ("INIT", Outcome::Warn),
        2 => ("READY", Outcome::Warn),
        3 => ("NORMAL_OPERATION", Outcome::Ok),
        4 => ("FAULT", Outcome::Fail),
        5 => ("RECOVERABLE_MRM_B1", Outcome::Fail),
        6 => ("TD_NEXT_SAFE_STOP", Outcome::Warn),
        7 => ("IMMEDIATE_PULLOVER", Outcome::Fail),
        8 => ("SHUTDOWN", Outcome::Warn),
        _ => ("UNKNOWN", Outcome::Warn),
    }
}

fn ts_sec_state(v: u64) -> (&'static str, Outcome) {
    match v {
        0 => ("RESET", Outcome::Fail),
        1 => ("SAFEINIT", Outcome::Warn),
        2 => ("TELECONTROL", Outcome::Ok),
        4 => ("ESTOP_EVENT", Outcome::Fail),
        8 => ("FAULT_EVENT", Outcome::Fail),
        _ => ("UNKNOWN", Outcome::Warn),
    }
}

fn diagc_cov(v: u64) -> (&'static str, Outcome) {
    match v {
        0 => ("OK", Outcome::Ok),
        1 => ("CH_A FAULT", Outcome::Warn),
        2 => ("CH_B FAULT", Outcome::Warn),
        3 => ("FAULT (both)", Outcome::Fail),
        _ => ("UNKNOWN", Outcome::Warn),
    }
}

fn latency_monitor_outcome(v: u64) -> Outcome {
    // 2-bit, no VAL_ in DBC; treat 0 as ok, anything else as warn.
    if v == 0 { Outcome::Ok } else { Outcome::Warn }
}

fn turn_indicator_label(v: u64) -> &'static str {
    match v {
        0 => "OFF",
        1 => "LEFT",
        2 => "RIGHT",
        _ => "UNKNOWN",
    }
}

fn front_wiper_label(v: u64) -> &'static str {
    match v {
        0 => "OFF",
        1 => "MIST",
        2 => "INT",
        3 => "LOW",
        4 => "HI",
        _ => "UNKNOWN",
    }
}

fn rear_wiper_label(v: u64) -> &'static str {
    match v {
        0 => "OFF",
        1 => "LOW",
        2 => "HI",
        _ => "UNKNOWN",
    }
}

// FW_BUILD_TYPE_TABLE: 0=Vehicle, 1=TS  (1-bit)
fn fw_build_type(v: u64) -> &'static str {
    match v { 0 => "Vehicle", 1 => "TS", _ => "?" }
}

// SEC_BUILD_TYPE_TABLE: 0=UNSAFE, 1=VEHICLE, 2=TS, 3=INVALID  (2-bit)
fn gw_build_type(v: u64) -> &'static str {
    match v { 0 => "UNSAFE", 1 => "VEHICLE", 2 => "TS", 3 => "INVALID", _ => "?" }
}

/// Compose the summary string for a CAN-decoded version row, decorated with
/// the manifest's expected version when one is available. Returns
/// `(summary, drift_detected)`.
fn compose_version_summary(
    build_type: &str,
    actual: &str,
    expected: Option<&str>,
) -> (String, bool) {
    match expected {
        None => (format!("{} {}", build_type, actual), false),
        Some(exp) => {
            let exp_norm = crate::manifest::normalize_version(exp);
            if actual == exp_norm {
                (format!("{} {} (matches manifest)", build_type, actual), false)
            } else {
                (format!("{} {} (manifest expects {})", build_type, actual, exp), true)
            }
        }
    }
}

/// vDrive deb package version cross-check against system-release-deployment manifest.
/// Compares the git SHA embedded in `dpkg-query ... ree-drive-{telestation,vehicle}`
/// against `vdrive.{telestation,vehicle}.sw_version` from release-configs.yaml.
pub fn vdrive_release_drift_check(planned: Vec<PlannedRow>, kind: HostKind) -> Check {
    let pkg = match kind {
        HostKind::Ts => "ree-drive-telestation",
        HostKind::Ve => "ree-drive-vehicle",
    };
    Check {
        category: Category::Reecu,
        planned,
        run: Box::new(move |target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                let cmd = format!("dpkg-query -W -f='${{Version}}' {} 2>/dev/null || true", pkg);
                let result = match run_remote(&target, &cmd).await {
                    Ok(r) if r.ok() => {
                        let ver = r.stdout.trim().to_string();
                        if ver.is_empty() {
                            fail_one(&row, category, format!("{} not installed", pkg), "")
                        } else {
                            decide_vdrive_drift(&row, category, &ver, kind)
                        }
                    }
                    Ok(r) => fail_one(&row, category, format!("dpkg failed (exit {:?})", r.exit_code), &r.stderr),
                    Err(e) => fail_one(&row, category, format!("ssh error: {}", e), e.to_string()),
                };
                vec![result]
            })
        }),
    }
}

fn decide_vdrive_drift(row: &PlannedRow, category: Category, ver: &str, kind: HostKind) -> CheckResult {
    let m = crate::manifest::manifest();
    let expected = match kind {
        HostKind::Ts => m.vdrive_ts.as_deref(),
        HostKind::Ve => m.vdrive_ve.as_deref(),
    };
    let actual_sha = crate::manifest::extract_sha(ver);
    let (outcome, summary) = match (expected, actual_sha) {
        (Some(exp), Some(actual)) if exp.starts_with(actual) => (
            Outcome::Ok,
            format!("{} (sha {} matches manifest)", ver, actual),
        ),
        (Some(exp), Some(actual)) => (
            Outcome::Warn,
            format!("{} (sha {} ≠ manifest {})", ver, actual, &exp[..actual.len().min(exp.len())]),
        ),
        (Some(exp), None) => (
            Outcome::Warn,
            format!("{} (no SHA in version; manifest expects {}…)", ver, &exp[..8.min(exp.len())]),
        ),
        (None, _) => (
            Outcome::Warn,
            format!("{} (no manifest available — check ~/GitHub/system-release-deployment)", ver),
        ),
    };
    CheckResult { id: row.id, category, name: row.name.into(), outcome, summary, raw: ver.to_string() }
}

// --- shared text helpers ---------------------------------------------------

fn pick(text: &str, key: &str) -> Option<String> {
    let needle = format!("{}=", key);
    for line in text.lines() {
        if let Some(rest) = line.strip_prefix(&needle) {
            return Some(rest.trim().to_string());
        }
    }
    None
}

fn pick_kv(text: &str, key: &str) -> Option<String> {
    let needle = format!("{}=", key);
    text.split_whitespace()
        .find(|tok| tok.starts_with(&needle))
        .map(|tok| tok[needle.len()..].to_string())
}

/// Shorten a log line to fit a single dashboard summary cell. Keeps the
/// `[ERROR]` marker and the message tail; drops the leading timestamp /
/// container-name noise that pads gateway logs.
fn truncate_err(line: &str) -> String {
    const MAX: usize = 80;
    let trimmed = match line.find("[ERROR]") {
        Some(i) => &line[i..],
        None => line,
    };
    if trimmed.len() <= MAX {
        trimmed.to_string()
    } else {
        format!("{}…", &trimmed[..MAX])
    }
}

fn opt(s: &Option<String>) -> &str {
    s.as_deref().unwrap_or("?")
}
