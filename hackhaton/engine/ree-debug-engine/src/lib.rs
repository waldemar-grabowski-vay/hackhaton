//! ree-debug-engine — Phase 1 stub.
//!
//! T002: this crate is the shared diagnostic library that both
//! `ree-debug-tui` and `ree-debug-cli` consume. The full port from
//! `~/GitHub/ree-debug-tui/src/{checks,inventory,ssh,manifest,ping,
//! session_init}.rs` lands in Phase 3 (US1, T022 — T026); for now the
//! crate exposes a placeholder `run_checks` that returns a hardcoded
//! empty `EngineReport` — enough for downstream binaries (`ree-debug-tui`,
//! `ree-debug-cli`) and the FastAPI backend to compile against the
//! shape Phase 2 (T017) defined.

use std::path::Path;

use thiserror::Error;

pub use types::*;

mod types;

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

/// Run the full per-host diagnostic fan-out and return a structured
/// `EngineReport`. Phase 1 stub: returns a hardcoded empty report so
/// the workspace compiles end-to-end before the Phase 3 port lands.
pub async fn run_checks(host_id: &str, _inventory_path: &Path) -> Result<EngineReport, EngineRunError> {
    let now = "1970-01-01T00:00:00Z".to_string();
    Ok(EngineReport {
        schema: "ree-debug-engine".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
        host_id: host_id.to_string(),
        host_type: HostType::Vehicle,
        started_at: now.clone(),
        completed_at: now,
        outcome: RunOutcome::Unreachable,
        checks: Vec::new(),
    })
}
