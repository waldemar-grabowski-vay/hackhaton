//! Public serde-derivable types for the engine library.
//!
//! Phase 1 stub — only the types `lib.rs::run_checks` references right
//! now. The full type set (`CheckEntry`, `EngineError`, validation
//! rules, etc.) lands in Phase 2 (T017).

use serde::{Deserialize, Serialize};

/// Run-level outcome the CLI binary computes from per-check distribution
/// + the SSH layer's reachability signal.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum RunOutcome {
    Complete,
    Partial,
    Unreachable,
    Timeout,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum HostType {
    Vehicle,
    Telestation,
}

/// Per-check status as the engine sees it (engineering truth).
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum CheckStatus {
    Pass,
    Warn,
    Fail,
}

/// One thing that was checked.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CheckEntry {
    pub id: String,
    /// Human-readable name from the engine's planned-row table
    /// (e.g., "SSH reachable", "vDrive package vs manifest"). The
    /// Python backend uses this verbatim as operator-visible copy
    /// when no catalog entry overrides it.
    pub name: String,
    pub status: CheckStatus,
    pub raw_detail: Option<String>,
    pub duration_ms: u64,
}

/// What `ree-debug-cli` prints to stdout for one host run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineReport {
    pub schema: String,
    pub version: String,
    pub host_id: String,
    pub host_type: HostType,
    pub started_at: String,
    pub completed_at: String,
    pub outcome: RunOutcome,
    pub checks: Vec<CheckEntry>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum EngineErrorKind {
    InventoryMissing,
    InventoryUnparseable,
    UnknownHostId,
    SshStartupFailed,
    Internal,
}

/// The shape `ree-debug-cli` writes as a single line of JSON to stderr
/// when it exits non-zero. Mirrors the Python `EngineError` Pydantic
/// model.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EngineError {
    pub kind: EngineErrorKind,
    pub message: String,
}
