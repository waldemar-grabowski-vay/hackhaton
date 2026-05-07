//! ree-debug-engine — diagnostic library shared by `ree-debug-tui` (binary)
//! and `ree-debug-cli` (binary).
//!
//! Phase 3 (T022 — T025): the diagnostic modules from the historical
//! `~/GitHub/ree-debug-tui` repo are ported in here verbatim. The
//! library is **pure** — no `println!`, no stdout/stderr writes,
//! no terminal I/O. Rendering belongs to the binaries.
//!
//! T026 (the high-level `run_checks` orchestration that wraps the
//! per-check fan-out into a single `EngineReport`) lands in a
//! follow-up. The TUI binary continues to drive its own task fan-out
//! using the per-check entry points exposed by `crate::checks::*`;
//! the CLI binary's call-site uses the `run_checks` stub below until
//! T026 lands the real one.

use std::path::Path;

use thiserror::Error;

pub use types::*;

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

/// High-level orchestration entry point. Phase 3 stub — returns a
/// hardcoded empty report so the CLI binary compiles. T026 (the next
/// session) extracts the real fan-out from the historical
/// `app.rs::confirm_pick`/`rerun` task plumbing into a synchronous
/// `EngineReport` builder.
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
