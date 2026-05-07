//! ree-debug-cli — Phase 1 stub.
//!
//! Phase 3 (US1, T030) replaces this with a real clap-based subcommand
//! parser that calls `ree_debug_engine::run_checks` and serialises the
//! result to stdout per `contracts/engine-cli.md`. The Phase 1 stub
//! prints an empty `EngineReport` so the FastAPI backend can compile
//! its `ReeCliExecutor` against the contract shape.

use ree_debug_engine::EngineReport;

fn main() {
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|a| a == "--version") {
        println!("ree-debug-cli {}", env!("REE_DEBUG_VERSION"));
        return;
    }

    // Hardcoded empty report. Real implementation lands in T030.
    let report = EngineReport {
        schema: "ree-debug-engine".to_string(),
        version: env!("REE_DEBUG_VERSION").to_string(),
        host_id: "stub".to_string(),
        host_type: ree_debug_engine::HostType::Vehicle,
        started_at: "1970-01-01T00:00:00Z".to_string(),
        completed_at: "1970-01-01T00:00:00Z".to_string(),
        outcome: ree_debug_engine::RunOutcome::Unreachable,
        checks: Vec::new(),
    };

    serde_json::to_writer_pretty(std::io::stdout(), &report).expect("stdout closed");
    println!();
}
