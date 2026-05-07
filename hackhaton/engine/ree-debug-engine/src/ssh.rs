// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

// Thin async wrapper around the system `ssh` binary so we inherit ~/.ssh/config
// (CanonicalizeHostname, ts-* / ve-* / router-* blocks already configured).

use std::sync::OnceLock;
use std::time::Duration;

use anyhow::{Context, Result};
use tokio::process::Command;
use tokio::sync::Semaphore;

// Cap concurrent SSH sessions to one host. sshd's default MaxSessions is 10
// per multiplexed connection — keep below that so no probe falls back to a
// fresh TCP/auth handshake (which would also race against MaxStartups).
const MAX_CONCURRENT_SSH: usize = 8;

fn ssh_semaphore() -> &'static Semaphore {
    static SEM: OnceLock<Semaphore> = OnceLock::new();
    SEM.get_or_init(|| Semaphore::new(MAX_CONCURRENT_SSH))
}

#[derive(Debug, Clone)]
pub struct SshTarget {
    pub host: String,
    pub connect_timeout: Duration,
}

impl SshTarget {
    pub fn new(host: impl Into<String>) -> Self {
        Self { host: host.into(), connect_timeout: Duration::from_secs(10) }
    }
}

#[derive(Debug, Clone)]
pub struct CommandResult {
    pub stdout: String,
    pub stderr: String,
    pub exit_code: Option<i32>,
}

impl CommandResult {
    pub fn ok(&self) -> bool {
        self.exit_code == Some(0)
    }
}

pub async fn run_remote(target: &SshTarget, remote_cmd: &str) -> Result<CommandResult> {
    let _permit = ssh_semaphore().acquire().await.expect("semaphore closed");
    let timeout_arg = format!("ConnectTimeout={}", target.connect_timeout.as_secs());
    let control_path_arg = format!("ControlPath={}", control_path());
    let output = Command::new("ssh")
        .args([
            "-o", "BatchMode=yes",
            "-o", &timeout_arg,
            "-o", "StrictHostKeyChecking=accept-new",
            // Multiplex over a single connection. The first call sets up the master;
            // subsequent calls reuse the socket. Avoids hitting sshd MaxStartups when
            // we fire ~14 probes in parallel.
            "-o", "ControlMaster=auto",
            "-o", &control_path_arg,
            "-o", "ControlPersist=60s",
            // Detect dead connections. Without these, abrupt network drops leave
            // remote shells (especially the long-lived debug-mode hold) running
            // for hours because sshd doesn't notice the client is gone — this
            // bit us 2026-04-30 when our trap-based sentinel cleanup didn't
            // fire after the WAN dropped. ServerAliveInterval=30 + Count=2 means
            // the local client sends a probe every 30s, drops after 2 missed
            // responses (~60s) — fast enough for the EXIT trap to fire on
            // session-end / disconnect, slow enough not to thrash on a brief blip.
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=2",
            &target.host,
            "--",
            remote_cmd,
        ])
        // If the future is cancelled (e.g., the debug-mode hold task is
        // aborted), tokio kills the local ssh process. The remote sshd then
        // sees the channel close and sends SIGHUP to the remote shell —
        // important because some commands (debug-mode hold) rely on a remote
        // EXIT trap firing to clean up sentinel files.
        .kill_on_drop(true)
        .output()
        .await
        .with_context(|| format!("spawning ssh to {}", target.host))?;

    Ok(CommandResult {
        stdout: String::from_utf8_lossy(&output.stdout).into_owned(),
        stderr: String::from_utf8_lossy(&output.stderr).into_owned(),
        exit_code: output.status.code(),
    })
}

/// Establish (or reuse) the ControlMaster connection. Currently unused —
/// stepwise dispatch fires one SSH at a time, so the first `run_remote`
/// implicitly establishes the master. Kept for parallel re-introduction
/// or for batched checks later.
#[allow(dead_code)]
pub async fn warmup(target: &SshTarget) -> Result<()> {
    run_remote(target, "true").await.map(|_| ())
}

fn control_path() -> String {
    // OpenSSH expands %C to a hash of (local_host, remote_host, port, user) —
    // unique per user/target, so no collisions between concurrent runs.
    "/tmp/ree-debug-tui-cm-%C".to_string()
}
