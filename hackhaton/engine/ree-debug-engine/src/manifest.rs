// This document contains proprietary information belonging to Vay Technology GmbH. Passing on and copying of this
// document, and communication of its contents is not permitted without prior written authorization.
//
// Copyright 2026 Vay Technology GmbH. All rights reserved.

// Reads the expected release versions from system-release-deployment/release-configs.yaml.
// Used to flag drift between what's deployed on a host and what the current branch
// of system-release-deployment says should be there.

use std::path::PathBuf;
use std::sync::OnceLock;

#[derive(Debug, Clone, Default)]
pub struct ReleaseManifest {
    pub reecu_ts: Option<String>,
    pub reecu_ve: Option<String>,
    pub sec_ts: Option<String>,
    pub sec_ve: Option<String>,
    pub vdrive_ts: Option<String>,
    pub vdrive_ve: Option<String>,
    // Kept so we can surface the manifest path in error messages later.
    #[allow(dead_code)]
    pub source_path: Option<PathBuf>,
}

pub fn manifest() -> &'static ReleaseManifest {
    static MANIFEST: OnceLock<ReleaseManifest> = OnceLock::new();
    MANIFEST.get_or_init(load_default)
}

fn load_default() -> ReleaseManifest {
    let Some(home) = std::env::var_os("HOME") else { return ReleaseManifest::default() };
    let path = PathBuf::from(home).join("GitHub/system-release-deployment/release-configs.yaml");
    let Ok(raw) = std::fs::read_to_string(&path) else { return ReleaseManifest::default() };
    let Ok(val): Result<serde_yaml::Value, _> = serde_yaml::from_str(&raw) else {
        return ReleaseManifest::default();
    };

    fn pluck(v: &serde_yaml::Value, component: &str, side: &str) -> Option<String> {
        v.get(component)?
            .get(side)?
            .get("sw_version")?
            .as_str()
            .map(str::to_owned)
    }

    ReleaseManifest {
        reecu_ts: pluck(&val, "reecu", "telestation"),
        reecu_ve: pluck(&val, "reecu", "vehicle"),
        sec_ts: pluck(&val, "sec", "telestation"),
        sec_ve: pluck(&val, "sec", "vehicle"),
        vdrive_ts: pluck(&val, "vdrive", "telestation"),
        vdrive_ve: pluck(&val, "vdrive", "vehicle"),
        source_path: Some(path),
    }
}

/// Strip the "R" / "v" prefix from manifest version strings so they compare
/// cleanly against bare numeric versions read from CAN.
pub fn normalize_version(s: &str) -> &str {
    s.trim_start_matches(|c: char| matches!(c, 'R' | 'v'))
}

/// Pull the rightmost git-SHA-shaped segment out of a deb version string.
/// e.g. "109.0.2+rc+7511b25cc" -> Some("7511b25cc"); "109.0.2" -> None.
pub fn extract_sha(version: &str) -> Option<&str> {
    version
        .split('+')
        .rev()
        .find(|seg| seg.len() >= 7 && seg.chars().all(|c| c.is_ascii_hexdigit()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn extract_sha_from_rc_build() {
        assert_eq!(extract_sha("109.0.2+rc+7511b25cc"), Some("7511b25cc"));
    }

    #[test]
    fn extract_sha_skips_non_hex() {
        assert_eq!(extract_sha("109.0.2+rc"), None);
    }

    #[test]
    fn normalize_strips_prefixes() {
        assert_eq!(normalize_version("R12.3.0"), "12.3.0");
        assert_eq!(normalize_version("v4.1.1"), "4.1.1");
        assert_eq!(normalize_version("12.3.0"), "12.3.0");
    }
}
