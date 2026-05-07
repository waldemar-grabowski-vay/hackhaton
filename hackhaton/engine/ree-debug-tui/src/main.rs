//! ree-debug-tui — Phase 1 stub.
//!
//! The real terminal UI ports in Phase 3 (US1, T028) — moving
//! `~/GitHub/ree-debug-tui/src/{main,app,repair,ui/*}.rs` into this
//! crate and pointing them at `ree_debug_engine::run_checks` instead
//! of owning the diagnostic logic. Until then this binary exists so
//! the workspace compiles.

fn main() {
    eprintln!("ree-debug-tui: Phase 1 stub — TUI lands in Phase 3 (T028)");
    std::process::exit(0);
}
