// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

// Aggregate the dashboard's per-row check results into a single "can the
// session initialize?" verdict, so the UI can render a one-line banner that
// non-technical operators understand without reading the full row table.
//
// The criteria mirror the two faults we keep hitting:
//   1. Vay private endpoints don't resolve (DNS resolver missing, or NXDOMAIN
//      on `*.reeapis.com`) — the lobby's session-status loop never advances.
//   2. VE `gnss_fusion` reports yaw rate unavailable — TS's fused-pose subscriber
//      blocks forever and `ts_telemetry_streamer_node` never finishes init.
// Plus the directly observable failure modes: stuck session ROS nodes and the
// stuck lobby polling loop.

use crate::checks::{CheckResult, Outcome};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SessionInitStatus {
    /// All critical signals are Ok. Session should be able to initialize.
    Ready,
    /// At least one critical signal hasn't returned yet (Pending).
    Pending,
    /// A critical signal is failing. `reason` is the user-facing one-liner.
    Blocked { reason: String },
}

impl SessionInitStatus {
    #[allow(dead_code)] // Rendered by the dashboard once A wires the banner.
    pub fn banner(&self) -> String {
        match self {
            SessionInitStatus::Ready => "Session ready to initialize".into(),
            SessionInitStatus::Pending => "Checking session readiness…".into(),
            SessionInitStatus::Blocked { reason } => {
                format!("Session can't initialize — {reason}")
            }
        }
    }
}

/// Names of the rows that count as "critical for session-init", in priority
/// order. The first failing row wins the `reason` line. Order reflects how
/// upstream the fault is — without the gateway container or APP_CAN traffic
/// the downstream session-init steps can't even begin, so those come first.
///
/// `DNS resolver` and the `*.reeapis.com` rows are currently disabled in
/// `src/checks/mod.rs` (lane A's call: noise drowned signal). We still
/// reference them here so the verdict picks the failure up automatically
/// if/when those checks are reinstated.
const CRITICAL_NAMED: &[&str] = &[
    "REECU gateway container",
    "CAN buses",
    "APP_CAN traffic",
    "REECU heartbeat",
    "gnss_fusion yaw rate",
    "Lobby polling loop",
    "Session ROS nodes alive",
    "DNS resolver",
];

pub fn evaluate(results: &[CheckResult]) -> SessionInitStatus {
    let by_name = |n: &str| results.iter().find(|r| r.name == n);

    // 1. Named critical rows in priority order.
    for name in CRITICAL_NAMED {
        if let Some(r) = by_name(name) {
            if r.outcome == Outcome::Fail {
                return SessionInitStatus::Blocked {
                    reason: format!("{}: {}", r.name, r.summary),
                };
            }
        }
    }

    // 2. DNS NXDOMAIN on any reeapis endpoint — flagged separately because
    //    the dns_resolve_check splits one row per FQDN.
    for r in results {
        if r.name.ends_with(".reeapis.com") && r.outcome == Outcome::Fail {
            return SessionInitStatus::Blocked {
                reason: format!("DNS NXDOMAIN for {}", r.name),
            };
        }
    }

    // 3. If anything critical is still pending, hold the Pending verdict.
    let critical_pending = CRITICAL_NAMED
        .iter()
        .filter_map(|n| by_name(n))
        .any(|r| r.outcome == Outcome::Pending)
        || results
            .iter()
            .any(|r| r.name.ends_with(".reeapis.com") && r.outcome == Outcome::Pending);
    if critical_pending {
        return SessionInitStatus::Pending;
    }

    SessionInitStatus::Ready
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::checks::Category;

    fn row(name: &str, outcome: Outcome, summary: &str) -> CheckResult {
        CheckResult {
            id: 0,
            category: Category::Reecu,
            name: name.into(),
            outcome,
            summary: summary.into(),
            raw: String::new(),
        }
    }

    #[test]
    fn ready_when_all_ok() {
        let rs = vec![
            row("DNS resolver", Outcome::Ok, ""),
            row("api.prod.reeapis.com", Outcome::Ok, ""),
            row("gnss_fusion yaw rate", Outcome::Ok, ""),
            row("Lobby polling loop", Outcome::Ok, ""),
            row("Session ROS nodes alive", Outcome::Ok, ""),
        ];
        assert_eq!(evaluate(&rs), SessionInitStatus::Ready);
    }

    #[test]
    fn blocked_on_named_fail() {
        let rs = vec![
            row("DNS resolver", Outcome::Ok, ""),
            row("gnss_fusion yaw rate", Outcome::Fail, "yaw rate unavailable — 5 warnings in last 5s"),
        ];
        match evaluate(&rs) {
            SessionInitStatus::Blocked { reason } => {
                assert!(reason.contains("yaw rate"));
            }
            other => panic!("expected Blocked, got {:?}", other),
        }
    }

    #[test]
    fn blocked_on_reeapis_nxdomain() {
        let rs = vec![
            row("DNS resolver", Outcome::Ok, ""),
            row("api.prod.reeapis.com", Outcome::Fail, "NXDOMAIN"),
            row("gnss_fusion yaw rate", Outcome::Ok, ""),
        ];
        match evaluate(&rs) {
            SessionInitStatus::Blocked { reason } => {
                assert!(reason.contains("api.prod.reeapis.com"));
            }
            other => panic!("expected Blocked, got {:?}", other),
        }
    }

    #[test]
    fn pending_when_critical_not_done() {
        let rs = vec![
            row("DNS resolver", Outcome::Pending, ""),
            row("gnss_fusion yaw rate", Outcome::Ok, ""),
        ];
        assert_eq!(evaluate(&rs), SessionInitStatus::Pending);
    }

    #[test]
    fn upstream_failure_takes_priority_over_yaw_rate() {
        // REECU gateway container is upstream of every other check —
        // its failure must win even when the yaw-rate check also fails.
        let rs = vec![
            row("REECU gateway container", Outcome::Fail, "container not found"),
            row("gnss_fusion yaw rate", Outcome::Fail, "5 warnings in last 5s"),
        ];
        match evaluate(&rs) {
            SessionInitStatus::Blocked { reason } => {
                assert!(reason.contains("REECU gateway container"), "got: {}", reason);
            }
            other => panic!("expected Blocked, got {:?}", other),
        }
    }

    #[test]
    fn dns_failure_still_caught_if_check_is_reinstated() {
        // DNS rows are currently disabled in checks/mod.rs but session_init
        // remains forward-compatible — if A reinstates DNS checks, a
        // failure should still surface as a Blocked reason.
        let rs = vec![row("DNS resolver", Outcome::Fail, "no DNS servers configured")];
        match evaluate(&rs) {
            SessionInitStatus::Blocked { reason } => {
                assert!(reason.contains("DNS resolver"), "got: {}", reason);
            }
            other => panic!("expected Blocked, got {:?}", other),
        }
    }
}
