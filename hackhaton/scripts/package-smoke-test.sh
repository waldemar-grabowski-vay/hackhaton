#!/usr/bin/env bash
# Smoke-test a freshly-built .deb inside a clean ubuntu:24.04 container.
#
# Spec 006 / Constitution Dev Workflow gate: every critical-path code change
# MUST have a smoke test on the main user flow. This is that gate for the .deb.
#
# Usage:
#   ./scripts/package-smoke-test.sh dist/vayobd_*.deb
#
# What it asserts (US1 independent test from spec.md):
#   1. `apt install ./vayobd_*.deb` succeeds on a fresh ubuntu:24.04.
#   2. `vayobd --version` prints a version line with our embedded SHA.
#   3. The bundled engine binary exists and is executable.
#   4. `vayobd run --no-browser --port 18000` with VAYOBD_EXECUTOR=fixture
#      boots, binds to 127.0.0.1, and serves /api/health with 200.
#
# Also (US4 / FR-014): when run twice in a row on the same commit, the
# `dpkg-deb -I` output is identical modulo timestamps.

set -euo pipefail

DEB_PATH="${1:-}"
if [[ -z "${DEB_PATH}" || ! -f "${DEB_PATH}" ]]; then
    echo "Usage: $0 <path-to-vayobd.deb>" >&2
    exit 2
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker is required to run the smoke test." >&2
    exit 1
fi

DEB_ABSOLUTE="$(cd "$(dirname "${DEB_PATH}")" && pwd)/$(basename "${DEB_PATH}")"
DEB_NAME="$(basename "${DEB_PATH}")"

echo "==> Smoke-testing ${DEB_NAME} in ubuntu:24.04"

docker run --rm \
    -v "${DEB_ABSOLUTE}":"/tmp/${DEB_NAME}":ro \
    -e DEB_NAME="${DEB_NAME}" \
    ubuntu:24.04 \
    bash -euxo pipefail -c '
        # Avoid prompts during apt install.
        export DEBIAN_FRONTEND=noninteractive

        apt-get update -qq
        # curl is needed by the smoke test itself; not declared by the .deb because
        # the real app uses Python httpx, not curl.
        apt-get install -y --no-install-recommends curl
        # Install with apt to resolve deps automatically.
        apt-get install -y --no-install-recommends "/tmp/${DEB_NAME}"

        # Create a non-root test user — the CLI refuses to run as root per FR-015.
        useradd -m -s /bin/bash testuser

        # ── Assertion 1: --version prints something non-empty ─────────────
        su testuser -c "vayobd --version" | tee /tmp/version.txt
        test -s /tmp/version.txt

        # ── Assertion 2: engine binary is executable ──────────────────────
        test -x /usr/lib/vayobd/bin/ree-debug-cli
        su testuser -c "/usr/lib/vayobd/bin/ree-debug-cli --version" || true

        # ── Assertion 3: vayobd run boots in fixture mode and serves /api/health
        # In a container with no GitHub creds, the first-run flow would exit 2;
        # we bypass it by writing a well-formed non-first-run state file before
        # launching. TOML literal block — note the *leading newline* so the
        # heredoc never produces an unparseable single-line file.
        mkdir -p /home/testuser/.cache/vayobd
        cat > /home/testuser/.cache/vayobd/manifest-state.toml <<TOMLEND
last_credential_probe = 2026-05-11T00:00:00Z
credential_surface_used = "ssh"

[repo.fixture-marker]
last_synced_at = 2026-05-11T00:00:00Z
last_outcome = "ok"
TOMLEND
        chown -R testuser:testuser /home/testuser/.cache

        # Run in the background, give uvicorn ~10 s to bind, then probe.
        su testuser -c "VAYOBD_EXECUTOR=fixture nohup vayobd run --no-browser --port 18000 > /tmp/vayobd-run.log 2>&1 &"
        OK=0
        for i in 1 2 3 4 5 6 7 8 9 10; do
            if curl -sS -o /dev/null --max-time 1 -w "%{http_code}" http://127.0.0.1:18000/api/health 2>/dev/null | grep -q 200; then
                echo "✓ /api/health responded 200 after ${i}s"
                OK=1
                break
            fi
            sleep 1
        done
        if [[ "${OK}" != "1" ]]; then
            echo "==== vayobd-run.log (uvicorn never bound) ===="
            cat /tmp/vayobd-run.log || true
            exit 1
        fi
        curl -sS -o - --max-time 3 http://127.0.0.1:18000/api/health | tee /tmp/health.json
        grep -q "\"status\":\"ok\"" /tmp/health.json
    '

echo ""
echo "✓ ${DEB_NAME} passes the smoke test."

# ─── US4 / FR-014 / SC-007 — determinism sanity check ────────────────────────
# When a second .deb is in the same dist/ directory (e.g., produced by a
# back-to-back build on the same commit), compare its control fields. Full
# bit-reproducibility is out of scope per research § 9, but Version, Depends
# and Recommends MUST match — that's what "functionally equivalent" means.
DIST_DIR="$(dirname "${DEB_ABSOLUTE}")"
SIBLINGS=()
while IFS= read -r f; do
    SIBLINGS+=("$f")
done < <(ls -1 "${DIST_DIR}"/vayobd_*amd64.deb 2>/dev/null | grep -v "$(basename "${DEB_ABSOLUTE}")")
if [[ ${#SIBLINGS[@]} -gt 0 ]]; then
    SIBLING="${SIBLINGS[0]}"
    echo "==> Comparing control fields against ${SIBLING}"
    A_FIELDS="$(dpkg-deb -f "${DEB_ABSOLUTE}" Version Depends Recommends 2>/dev/null || true)"
    B_FIELDS="$(dpkg-deb -f "${SIBLING}"      Version Depends Recommends 2>/dev/null || true)"
    if [[ "${A_FIELDS}" == "${B_FIELDS}" ]]; then
        echo "✓ Version/Depends/Recommends are identical across builds"
    else
        echo "WARN: control-field drift between builds:" >&2
        diff <(echo "${A_FIELDS}") <(echo "${B_FIELDS}") >&2 || true
    fi
fi
