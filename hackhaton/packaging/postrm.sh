#!/usr/bin/env bash
# postrm — runs after `dpkg --remove` (and `--purge`).
# Spec 006 FR-011: a normal `remove` MUST preserve the user's cached repos
# and settings. Only on `purge` do we surface the cleanup hint.
set -e

case "$1" in
    remove)
        # Nothing to do — per-user cache survives, by design.
        ;;
    purge)
        cat <<'NOTE'
Note: VayOBD's per-user cache and settings were left in place at:
  ~/.cache/vayobd/    (cloned repos + manifest-state.toml)
  ~/.config/vayobd/   (settings.toml)

Each user on this machine can remove their own copy with:
  rm -rf ~/.cache/vayobd ~/.config/vayobd
NOTE
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database -q /usr/share/applications || true
        fi
        ;;
esac

exit 0
