// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

// Reads ree-vehicle-configs/org/vay/inventory.yaml and exposes the
// list of telestation and vehicle hosts.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result};
use serde::Deserialize;

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum HostKind {
    Ts,
    Ve,
}

impl HostKind {
    pub fn tag(self) -> &'static str {
        match self {
            HostKind::Ts => "TS",
            HostKind::Ve => "VE",
        }
    }

    #[allow(dead_code)] // reserved for future picker grouping UI
    pub fn group_label(self) -> &'static str {
        match self {
            HostKind::Ts => "Telestations",
            HostKind::Ve => "Vehicles",
        }
    }
}

#[derive(Debug, Clone)]
pub struct Host {
    pub name: String,
    pub kind: HostKind,
    pub ansible_host: Option<String>,
}

pub fn default_inventory_path() -> Option<PathBuf> {
    std::env::var_os("HOME").map(|home| {
        PathBuf::from(home).join("GitHub/ree-vehicle-configs/org/vay/inventory.yaml")
    })
}

pub fn load_default() -> Result<Vec<Host>> {
    let path = default_inventory_path().context("HOME not set")?;
    load(&path)
}

pub fn load(path: &Path) -> Result<Vec<Host>> {
    let raw = std::fs::read_to_string(path)
        .with_context(|| format!("read {}", path.display()))?;
    let inv: InventoryFile = serde_yaml::from_str(&raw)
        .with_context(|| format!("parse {}", path.display()))?;

    let mut hosts = Vec::new();
    for (group, info) in inv.all.children {
        let kind = match group.as_str() {
            "telestations" => HostKind::Ts,
            "vehicles" => HostKind::Ve,
            _ => continue,
        };
        for (name, host) in info.hosts {
            hosts.push(Host { name, kind, ansible_host: host.ansible_host });
        }
    }
    hosts.sort_by(|a, b| a.kind.cmp(&b.kind).then_with(|| a.name.cmp(&b.name)));
    Ok(hosts)
}

#[derive(Debug, Deserialize, Default)]
struct InventoryFile {
    #[serde(default)]
    all: All,
}

#[derive(Debug, Deserialize, Default)]
struct All {
    #[serde(default)]
    children: BTreeMap<String, Group>,
}

#[derive(Debug, Deserialize, Default)]
struct Group {
    #[serde(default)]
    hosts: BTreeMap<String, HostInfo>,
}

#[derive(Debug, Deserialize, Default)]
struct HostInfo {
    #[serde(default)]
    ansible_host: Option<String>,
}
