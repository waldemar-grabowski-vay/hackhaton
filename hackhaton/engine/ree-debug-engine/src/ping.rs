// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

// Lightweight reachability probe — opens a TCP socket to `<target>:22` and
// reads the SSH banner. We need both steps because the SD-WAN tunnel that
// routes some testbed VLANs accepts the TCP SYN even when no host is
// behind it, so a successful connect alone produces false positives. Real
// sshd sends `SSH-2.0-...\r\n` within ~100 ms of accept; nothing else
// matches that signature.

use std::time::Duration;

use tokio::io::AsyncReadExt;
use tokio::net::TcpStream;
use tokio::time::timeout;

#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub enum PingStatus {
    #[default]
    Unknown,
    Probing,
    Online,
    Offline,
}

#[derive(Debug, Clone)]
pub struct PingUpdate {
    pub host: String,
    pub status: PingStatus,
}

pub async fn probe_ssh(target: &str, total_timeout_ms: u64) -> bool {
    let addr = format!("{}:22", target);
    let mut stream = match timeout(
        Duration::from_millis(total_timeout_ms),
        TcpStream::connect(&addr),
    )
    .await
    {
        Ok(Ok(s)) => s,
        _ => return false,
    };
    // Cap banner-read at the smaller of the budget remaining or 1 s.
    let banner_budget = Duration::from_millis(total_timeout_ms.min(1000));
    let mut buf = [0u8; 8];
    match timeout(banner_budget, stream.read(&mut buf)).await {
        Ok(Ok(n)) if n >= 4 => buf.starts_with(b"SSH-"),
        _ => false,
    }
}
