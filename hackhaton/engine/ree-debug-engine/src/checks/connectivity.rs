// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

use std::sync::Arc;

use crate::checks::{Category, Check, CheckFuture, CheckResult, Outcome, PlannedRow};
use crate::inventory::HostKind;
use crate::ssh::{run_remote, SshTarget};

// Vay private control-plane endpoints. They aren't in public DNS; resolving
// them requires an internal resolver. Confirmed missing on both TS and VE on
// 2026-04-30, which traced to the lobby's "Checking session status" loop
// never advancing.
const VAY_BACKENDS: &[&str] = &[
    "api.prod.reeapis.com",
    "lobby.prod.reeapis.com",
    "tdms.prod.reeapis.com",
    "cloud-telemetry.prod.reeapis.com",
];

pub fn reach_check(planned: Vec<PlannedRow>) -> Check {
    Check {
        category: Category::Connectivity,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                let result = match run_remote(&target, "true").await {
                    Ok(r) if r.ok() => CheckResult {
                        id: row.id, category, name: row.name.into(),
                        outcome: Outcome::Ok,
                        summary: format!("connected to {}", target.host),
                        raw: String::new(),
                    },
                    Ok(r) => CheckResult {
                        id: row.id, category, name: row.name.into(),
                        outcome: Outcome::Fail,
                        summary: format!("ssh exit {:?}", r.exit_code),
                        raw: r.stderr,
                    },
                    Err(e) => CheckResult {
                        id: row.id, category, name: row.name.into(),
                        outcome: Outcome::Fail,
                        summary: format!("ssh failed: {}", e),
                        raw: e.to_string(),
                    },
                };
                vec![result]
            })
        }),
    }
}

/// Probe DNS resolution for the Vay private control-plane endpoints. One row
/// per FQDN — each fails individually so the dashboard pinpoints exactly which
/// records are missing rather than collapsing to a single pass/fail.
pub fn dns_resolve_check(planned: Vec<PlannedRow>) -> Check {
    Check {
        category: Category::Connectivity,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                assert_eq!(
                    planned.len(),
                    VAY_BACKENDS.len(),
                    "dns_resolve_check expects {} planned rows",
                    VAY_BACKENDS.len()
                );
                let mut script = String::new();
                for (i, fqdn) in VAY_BACKENDS.iter().enumerate() {
                    script.push_str(&format!(
                        "ip=$(getent hosts {fqdn} 2>/dev/null | head -1 | awk '{{print $1}}'); \
                         echo \"R{i}=${{ip:-NXDOMAIN}}\"; "
                    ));
                }
                match run_remote(&target, &script).await {
                    Ok(r) if r.ok() => planned
                        .iter()
                        .enumerate()
                        .map(|(i, row)| {
                            let prefix = format!("R{}=", i);
                            let val = r
                                .stdout
                                .lines()
                                .find_map(|l| l.strip_prefix(&prefix))
                                .map(|s| s.trim().to_string())
                                .unwrap_or_default();
                            if val.is_empty() || val == "NXDOMAIN" {
                                CheckResult {
                                    id: row.id,
                                    category,
                                    name: row.name.into(),
                                    outcome: Outcome::Fail,
                                    summary: "NXDOMAIN".into(),
                                    raw: r.stdout.clone(),
                                }
                            } else {
                                CheckResult {
                                    id: row.id,
                                    category,
                                    name: row.name.into(),
                                    outcome: Outcome::Ok,
                                    summary: val.clone(),
                                    raw: r.stdout.clone(),
                                }
                            }
                        })
                        .collect(),
                    Ok(r) => super::fail_all(
                        &planned,
                        category,
                        format!("dns probe failed (exit {:?})", r.exit_code),
                    ),
                    Err(e) => super::fail_all(&planned, category, format!("ssh error: {}", e)),
                }
            })
        }),
    }
}

/// Inspect the host's DNS resolver list. Warn when only public resolvers
/// (Google / Cloudflare / Quad9) are configured, because the host then can't
/// resolve `*.reeapis.com` private records — same root cause we hit
/// 2026-04-30. Heuristic: an internal resolver is identified by having any
/// configured DNS server with an RFC1918 address.
pub fn dns_resolver_check(planned: Vec<PlannedRow>) -> Check {
    Check {
        category: Category::Connectivity,
        planned,
        run: Box::new(|target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                // Prefer resolvectl (systemd-resolved); fall back to /etc/resolv.conf.
                let cmd = "(resolvectl status 2>/dev/null \
                            | awk -F: '/Current DNS Server|^[[:space:]]*DNS Servers:/ {print $2}' \
                            | tr ' ' '\\n' \
                            | grep -E '^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+$' \
                            | sort -u) \
                            || (grep ^nameserver /etc/resolv.conf 2>/dev/null \
                                | awk '{print $2}')";
                let result = match run_remote(&target, cmd).await {
                    Ok(r) if r.ok() => {
                        let ips: Vec<String> = r
                            .stdout
                            .lines()
                            .map(|l| l.trim().to_string())
                            .filter(|s| !s.is_empty())
                            .collect();
                        if ips.is_empty() {
                            super::fail_one(&row, category, "no DNS servers configured", &r.stdout)
                        } else {
                            let has_internal = ips.iter().any(|ip| is_private_ipv4(ip));
                            if has_internal {
                                CheckResult {
                                    id: row.id,
                                    category,
                                    name: row.name.into(),
                                    outcome: Outcome::Ok,
                                    summary: ips.join(", "),
                                    raw: r.stdout,
                                }
                            } else {
                                CheckResult {
                                    id: row.id,
                                    category,
                                    name: row.name.into(),
                                    outcome: Outcome::Warn,
                                    summary: format!(
                                        "{} (only public — no internal resolver)",
                                        ips.join(", ")
                                    ),
                                    raw: r.stdout,
                                }
                            }
                        }
                    }
                    Ok(r) => super::fail_one(
                        &row,
                        category,
                        format!("resolvectl/resolv.conf failed (exit {:?})", r.exit_code),
                        &r.stderr,
                    ),
                    Err(e) => super::fail_one(
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

fn is_private_ipv4(ip: &str) -> bool {
    let parts: Vec<&str> = ip.split('.').collect();
    if parts.len() != 4 {
        return false;
    }
    let p: Vec<u8> = match parts.iter().map(|s| s.parse::<u8>()).collect::<Result<Vec<_>, _>>() {
        Ok(v) => v,
        Err(_) => return false,
    };
    p[0] == 10
        || (p[0] == 172 && (16..=31).contains(&p[1]))
        || (p[0] == 192 && p[1] == 168)
}

pub fn host_type_check(planned: Vec<PlannedRow>, kind: HostKind) -> Check {
    Check {
        category: Category::Connectivity,
        planned,
        run: Box::new(move |target: Arc<SshTarget>, category, planned| -> CheckFuture {
            Box::pin(async move {
                let row = planned[0].clone();
                // /etc/ree/host-type is only populated on telestations (the value
                // is `marmot`). On vehicles the file doesn't exist; treat that
                // as expected.
                let result = match run_remote(&target, "cat /etc/ree/host-type 2>/dev/null").await {
                    Ok(r) => {
                        let label = r.stdout.trim().to_string();
                        if !label.is_empty() {
                            CheckResult {
                                id: row.id, category, name: row.name.into(),
                                outcome: Outcome::Ok,
                                summary: label.clone(),
                                raw: label,
                            }
                        } else {
                            match kind {
                                HostKind::Ts => CheckResult {
                                    id: row.id, category, name: row.name.into(),
                                    outcome: Outcome::Warn,
                                    summary: "missing on TS".into(),
                                    raw: r.stderr,
                                },
                                HostKind::Ve => CheckResult {
                                    id: row.id, category, name: row.name.into(),
                                    outcome: Outcome::Ok,
                                    summary: "n/a (vehicle)".into(),
                                    raw: r.stderr,
                                },
                            }
                        }
                    }
                    Err(e) => CheckResult {
                        id: row.id, category, name: row.name.into(),
                        outcome: Outcome::Fail,
                        summary: format!("ssh error: {}", e),
                        raw: e.to_string(),
                    },
                };
                vec![result]
            })
        }),
    }
}
