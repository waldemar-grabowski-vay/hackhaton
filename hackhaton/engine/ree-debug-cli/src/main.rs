//! ree-debug-cli — non-interactive JSON-emitting frontend for the
//! engine library. The Python backend shells out to this binary per
//! `POST /api/runs`.
//!
//! See `specs/002-real-executor/contracts/engine-cli.md` for the
//! contract: arg shape, exit codes, stdout/stderr conventions.

use std::path::PathBuf;
use std::process::ExitCode;

use clap::{Parser, Subcommand};
use ree_debug_engine::{run_checks, EngineError, EngineErrorKind, EngineRunError};

const REE_DEBUG_VERSION: &str = env!("REE_DEBUG_VERSION");

#[derive(Parser, Debug)]
#[command(name = "ree-debug-cli", about = "JSON-emitting frontend for the Vay diagnostic engine.", version = REE_DEBUG_VERSION)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand, Debug)]
enum Command {
    /// Run the full diagnostic fan-out for one host and print the result as JSON.
    Report {
        /// Host id from `org/vay/inventory.yaml`. Pattern: `(ve|ts)-de-…`.
        #[arg(long)]
        host: String,

        /// Path to the operator's local `ree-vehicle-configs` clone.
        #[arg(long)]
        inventory: PathBuf,

        /// Required in v1. Reserves stdout for the JSON document.
        /// Other output formats may follow; the flag exists so future
        /// callers don't break.
        #[arg(long)]
        json: bool,
    },
}

#[tokio::main(flavor = "current_thread")]
async fn main() -> ExitCode {
    let cli = Cli::parse();
    match cli.command {
        Command::Report {
            host,
            inventory,
            json,
        } => {
            if !json {
                emit_error_to_stderr(EngineErrorKind::Internal, "v1 of ree-debug-cli requires --json");
                return ExitCode::from(64);
            }
            run_report(host, inventory).await
        }
    }
}

async fn run_report(host: String, inventory: PathBuf) -> ExitCode {
    // Per `contracts/engine-cli.md`, `--inventory` is the operator's
    // ree-vehicle-configs *clone root* — append the canonical relative
    // path to the inventory YAML before handing it to the engine.
    let inventory_yaml = inventory.join("org").join("vay").join("inventory.yaml");
    let report = match run_checks(&host, &inventory_yaml).await {
        Ok(r) => r,
        Err(err) => {
            let kind = (&err).into();
            let exit = match &err {
                EngineRunError::InventoryMissing { .. } | EngineRunError::InventoryUnparseable { .. } => 2,
                EngineRunError::SshStartupFailed { .. } => 3,
                EngineRunError::UnknownHostId { .. } | EngineRunError::Internal { .. } => 1,
            };
            emit_error_to_stderr(kind, err.to_string());
            return ExitCode::from(exit);
        }
    };

    if let Err(io) = serde_json::to_writer(std::io::stdout().lock(), &report) {
        emit_error_to_stderr(
            EngineErrorKind::Internal,
            format!("failed to serialise report to stdout: {io}"),
        );
        return ExitCode::from(1);
    }
    println!();
    ExitCode::SUCCESS
}

fn emit_error_to_stderr(kind: EngineErrorKind, message: impl Into<String>) {
    let payload = EngineError {
        kind,
        message: message.into(),
    };
    if let Ok(line) = serde_json::to_string(&payload) {
        eprintln!("{line}");
    }
}
