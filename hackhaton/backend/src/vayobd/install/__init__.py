"""First-run / refresh / credential orchestration for the .deb (spec 006).

Public entry points (filled in as Phases 2-5 land):
- `manifest.load_manifest(path)` — read /usr/share/vayobd/manifest.toml
- `state.load_state()` / `state.save_state_atomic()` — read/write per-user state
- `credentials.probe_credentials()` — SSH → gh → credential-helper auto-detect
- `clone.clone_all(...)` — driver used by both first-run and refresh
- `messages.*` — plain-language strings rendered to CLI and HTTP surfaces
"""
