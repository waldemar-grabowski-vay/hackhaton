//! ree-debug-engine — diagnostic library shared by `ree-debug-tui` (binary)
//! and `ree-debug-cli` (binary).
//!
//! T026 lands the real `run_checks` orchestration: load the operator's
//! local inventory, find the requested host, warm the SSH ControlMaster
//! to detect reachability, fan out the check set from
//! [`checks::all_checks`] in parallel, collect the per-check rows, and
//! assemble an [`EngineReport`].
//!
//! The library stays pure — no `println!`, no terminal I/O. Rendering
//! belongs to `ree-debug-tui` (binary) or `ree-debug-cli` (binary).

use std::path::Path;
use std::sync::Arc;

use chrono::Utc;
use futures::future::join_all;
use thiserror::Error;

pub use types::*;

use crate::checks::{all_checks, Outcome};
use crate::inventory::{load as load_inventory, HostKind};
use crate::ssh::{warmup, SshTarget};

mod types;

pub mod checks;
pub mod inventory;
pub mod manifest;
pub mod ping;
pub mod session_init;
pub mod ssh;

#[derive(Debug, Error)]
pub enum EngineRunError {
    #[error("inventory missing at {path}")]
    InventoryMissing { path: String },

    #[error("inventory unparseable at {path}: {source}")]
    InventoryUnparseable {
        path: String,
        #[source]
        source: anyhow::Error,
    },

    #[error("unknown host id: {host_id}")]
    UnknownHostId { host_id: String },

    #[error("ssh layer failed during startup: {source}")]
    SshStartupFailed {
        #[source]
        source: anyhow::Error,
    },

    #[error("internal engine error: {source}")]
    Internal {
        #[source]
        source: anyhow::Error,
    },
}

impl From<&EngineRunError> for EngineErrorKind {
    fn from(err: &EngineRunError) -> Self {
        match err {
            EngineRunError::InventoryMissing { .. } => EngineErrorKind::InventoryMissing,
            EngineRunError::InventoryUnparseable { .. } => EngineErrorKind::InventoryUnparseable,
            EngineRunError::UnknownHostId { .. } => EngineErrorKind::UnknownHostId,
            EngineRunError::SshStartupFailed { .. } => EngineErrorKind::SshStartupFailed,
            EngineRunError::Internal { .. } => EngineErrorKind::Internal,
        }
    }
}

/// Run the full per-host diagnostic fan-out and return an
/// `EngineReport`.
///
/// - Loads the inventory at `inventory_path` (Ansible-style YAML).
/// - Looks up `host_id`. Returns `UnknownHostId` if absent.
/// - Probes SSH reachability via [`ssh::warmup`]. If the warmup fails,
///   returns `outcome: Unreachable` with empty checks (matching the
///   001 / FR-006 "host could not be reached" UX).
/// - Otherwise calls [`checks::all_checks`] for the host's kind, awaits
///   every per-check future in parallel, flattens the per-row results,
///   and maps to [`CheckEntry`].
///
/// `outcome`:
/// - `Unreachable` when SSH warmup fails or the inventory has zero
///   checks for the host's kind.
/// - `Complete` otherwise. (Phase 3 doesn't yet distinguish
///   `Partial` — every check produces *some* row even on failure
///   thanks to `fail_one`/`fail_all`.)
pub async fn run_checks(host_id: &str, inventory_path: &Path) -> Result<EngineReport, EngineRunError> {
    let started_at = Utc::now();

    let hosts = load_inventory(inventory_path).map_err(|source| {
        EngineRunError::InventoryUnparseable {
            path: inventory_path.display().to_string(),
            source,
        }
    })?;

    let host = hosts
        .iter()
        .find(|h| h.name == host_id)
        .ok_or_else(|| EngineRunError::UnknownHostId {
            host_id: host_id.to_string(),
        })?
        .clone();

    let target = Arc::new(SshTarget::new(host.name.clone()));

    // Reachability probe. If SSH refuses (timeout / connect error /
    // auth failure), don't run the full check set — render the
    // dedicated "unreachable" outcome so the operator sees a single
    // clear message rather than a wall of "ssh failed" rows.
    if warmup(&target).await.is_err() {
        let now = Utc::now();
        return Ok(EngineReport {
            schema: "ree-debug-engine".to_string(),
            version: engine_version(),
            host_id: host.name,
            host_type: host_kind_to_type(host.kind),
            started_at: format_iso8601(started_at),
            completed_at: format_iso8601(now),
            outcome: RunOutcome::Unreachable,
            checks: Vec::new(),
        });
    }

    let plan = all_checks(host.kind);
    let futures = plan.into_iter().map(|check| {
        let target = target.clone();
        async move { (check.run)(target, check.category, check.planned).await }
    });
    let per_check_rows = join_all(futures).await;

    let mut entries: Vec<CheckEntry> = Vec::new();
    for rows in per_check_rows {
        for row in rows {
            entries.push(CheckEntry {
                id: slugify(&row.name),
                name: row.name,
                status: outcome_to_status(row.outcome),
                raw_detail: if row.summary.is_empty() {
                    None
                } else {
                    Some(row.summary)
                },
                duration_ms: 0, // not tracked at this granularity in v1
            });
        }
    }

    let outcome = if entries.is_empty() {
        RunOutcome::Unreachable
    } else {
        RunOutcome::Complete
    };

    Ok(EngineReport {
        schema: "ree-debug-engine".to_string(),
        version: engine_version(),
        host_id: host.name,
        host_type: host_kind_to_type(host.kind),
        started_at: format_iso8601(started_at),
        completed_at: format_iso8601(Utc::now()),
        outcome,
        checks: entries,
    })
}

fn outcome_to_status(o: Outcome) -> CheckStatus {
    match o {
        Outcome::Ok => CheckStatus::Pass,
        Outcome::Warn => CheckStatus::Warn,
        Outcome::Fail | Outcome::Pending => CheckStatus::Fail,
    }
}

fn host_kind_to_type(k: HostKind) -> HostType {
    match k {
        HostKind::Ts => HostType::Telestation,
        HostKind::Ve => HostType::Vehicle,
    }
}

/// Slugify a check's planned-row name into a stable id the Python-side
/// catalog (T039) can key off. Lowercases, replaces every non-`[a-z0-9]`
/// run with a single underscore, strips leading/trailing underscores.
fn slugify(name: &str) -> String {
    let mut out = String::with_capacity(name.len());
    let mut last_was_sep = true; // avoid leading underscore
    for ch in name.chars() {
        if ch.is_ascii_alphanumeric() {
            out.push(ch.to_ascii_lowercase());
            last_was_sep = false;
        } else if !last_was_sep {
            out.push('_');
            last_was_sep = true;
        }
    }
    while out.ends_with('_') {
        out.pop();
    }
    out
}

fn format_iso8601(t: chrono::DateTime<Utc>) -> String {
    t.format("%Y-%m-%dT%H:%M:%S%.3fZ").to_string()
}

fn engine_version() -> String {
    // `CARGO_PKG_VERSION` is the workspace-pinned 0.0.1 today. The CLI
    // binary's build.rs embeds the workspace git SHA via
    // `REE_DEBUG_VERSION`; the library exposes the cargo version
    // because it doesn't have its own build.rs.
    env!("CARGO_PKG_VERSION").to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn slugify_handles_punctuation() {
        assert_eq!(slugify("Main CAN bus reachable"), "main_can_bus_reachable");
        assert_eq!(slugify("vDrive package vs manifest"), "vdrive_package_vs_manifest");
        assert_eq!(slugify("api.prod.reeapis.com"), "api_prod_reeapis_com");
        assert_eq!(slugify("TS_SYSTEM_STATE (0x004)"), "ts_system_state_0x004");
        assert_eq!(slugify("VE_EPB_ERR"), "ve_epb_err");
    }

    #[test]
    fn outcome_mapping_is_total() {
        assert_eq!(outcome_to_status(Outcome::Ok), CheckStatus::Pass);
        assert_eq!(outcome_to_status(Outcome::Warn), CheckStatus::Warn);
        assert_eq!(outcome_to_status(Outcome::Fail), CheckStatus::Fail);
        assert_eq!(outcome_to_status(Outcome::Pending), CheckStatus::Fail);
    }
}
