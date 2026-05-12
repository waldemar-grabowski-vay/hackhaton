#!/usr/bin/env bash
# /usr/bin/vayobd — thin launcher installed by the VayOBD .deb (spec 006).
#
# Runs as the invoking user; never as root (the Python CLI enforces this with
# a clear message, see backend/src/vayobd/cli.py).
#
# Exec's the bundled venv's Python with the vayobd.cli module so user laptops
# never need their own venv, pip install, or PYTHONPATH gymnastics.

set -e

VAYOBD_PREFIX="/usr/lib/vayobd"
VENV_PY="${VAYOBD_PREFIX}/venv/bin/python"

if [[ ! -x "${VENV_PY}" ]]; then
    cat >&2 <<'ERR'
VayOBD's bundled Python is missing. The package looks broken — please reinstall:
    sudo apt install --reinstall vayobd
ERR
    exit 1
fi

# Let the engine binary be found by the backend without env hacks.
export VAYOBD_REE_CLI_BIN="${VAYOBD_REE_CLI_BIN:-${VAYOBD_PREFIX}/bin/ree-debug-cli}"
# Default the static SPA path — the user can still override via VAYOBD_STATIC_DIR.
export VAYOBD_STATIC_DIR="${VAYOBD_STATIC_DIR:-/usr/share/vayobd/spa}"
# Default to the real engine in production. The Python class default is
# FIXTURE (so unit tests don't need a built engine binary); the .deb is
# always production-mode unless the operator explicitly overrides.
export VAYOBD_EXECUTOR="${VAYOBD_EXECUTOR:-ree}"

exec "${VENV_PY}" -m vayobd.cli "$@"
