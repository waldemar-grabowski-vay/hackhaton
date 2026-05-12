#!/usr/bin/env bash
# postinst — runs after `dpkg --install vayobd_*.deb`, as root.
# Per spec 006 plan: maintainer scripts only handle system-level wiring; no
# per-user state is touched here. First-run cloning happens in `vayobd run`
# as the invoking user.
set -e

# Refresh the desktop-launcher cache so the app icon appears immediately.
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database -q /usr/share/applications || true
fi

exit 0
