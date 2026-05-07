//! T005 — embed the workspace git SHA at build time.
//!
//! The Python backend's startup self-check (FR-003a) compares this
//! against an expected SHA recorded in backend metadata. Because the
//! engine and the backend ship from the same monorepo SHA, this is
//! the contract version per `data-model.md`'s "no separate
//! schema_version" decision.

use std::process::Command;

fn main() {
    // Re-run if HEAD moves so the SHA stays current.
    println!("cargo:rerun-if-changed=../../.git/HEAD");
    println!("cargo:rerun-if-changed=../../.git/refs");

    let sha = Command::new("git")
        .args(["rev-parse", "--short", "HEAD"])
        .output()
        .ok()
        .and_then(|out| {
            if out.status.success() {
                String::from_utf8(out.stdout).ok().map(|s| s.trim().to_string())
            } else {
                None
            }
        })
        .unwrap_or_else(|| "unknown".to_string());

    println!("cargo:rustc-env=REE_DEBUG_VERSION={sha}");
}
