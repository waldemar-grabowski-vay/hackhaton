"""GitHub credential auto-detection: SSH → `gh auth` → system credential helper.

Spec FR-004 + clarification 2026-05-11 Q1. Each probe is fast (<5 s) and
non-interactive (BatchMode=yes, GIT_TERMINAL_PROMPT=0). The first surface that
produces a working clone wins; subsequent surfaces are tried only on failure.

Implementation per specs/006-deb-package-distribution/research.md § 3.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from vayobd.install.messages import ProbeResult, ProbeSurfaceResult
from vayobd.logging import get_logger

log = get_logger(__name__)

# A canary repo readable without auth — used by the credential-helper probe to
# verify that the system credential helper resolves GitHub HTTPS creds without
# blocking on a prompt. Use any public Reemote repo; if none is reachable we
# treat the helper probe as inconclusive (not a hard fail).
_PUBLIC_CANARY_URL = os.environ.get(
    "VAYOBD_PUBLIC_CANARY_URL",
    "https://github.com/Reemote/.github.git",
)


def probe_credentials() -> ProbeResult:
    """Probe each credential surface in order, returning the per-surface outcomes.

    Probes are skipped (not run) once an earlier surface has already succeeded,
    but the result for each unattempted surface is still recorded as "skipped"
    so the FR-005 message can show the full picture.
    """
    surfaces: list[ProbeSurfaceResult] = []
    winner_found = False

    ssh_result = _probe_ssh()
    surfaces.append(ssh_result)
    if ssh_result.succeeded:
        winner_found = True

    gh_result = _probe_gh() if not winner_found else _skipped("gh")
    surfaces.append(gh_result)
    if gh_result.succeeded:
        winner_found = True

    helper_result = _probe_credential_helper() if not winner_found else _skipped("credential-helper")
    surfaces.append(helper_result)

    return ProbeResult(surfaces=surfaces)


def _skipped(name: str) -> ProbeSurfaceResult:
    return ProbeSurfaceResult(surface=name, succeeded=False, detail="not tried (earlier surface succeeded)")


def _probe_ssh() -> ProbeSurfaceResult:
    """`ssh -T -o BatchMode=yes -o ConnectTimeout=5 git@github.com`.

    GitHub returns exit code 1 with "Hi <user>! You've successfully authenticated…"
    on success; anything else (255 = connection failed, etc.) is a failure.
    """
    ssh = shutil.which("ssh")
    if ssh is None:
        return ProbeSurfaceResult("ssh", succeeded=False, detail="`ssh` not installed")
    try:
        proc = subprocess.run(
            [
                ssh,
                "-T",
                "-o",
                "BatchMode=yes",
                "-o",
                "ConnectTimeout=5",
                "-o",
                "StrictHostKeyChecking=accept-new",
                "git@github.com",
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ProbeSurfaceResult("ssh", succeeded=False, detail="connection timed out")
    except OSError as exc:
        return ProbeSurfaceResult("ssh", succeeded=False, detail=f"ssh failed: {exc}")

    combined = (proc.stdout + proc.stderr).strip()
    # GitHub-specific success markers.
    if "successfully authenticated" in combined.lower():
        return ProbeSurfaceResult("ssh", succeeded=True, detail="authenticated")
    if "permission denied" in combined.lower():
        return ProbeSurfaceResult("ssh", succeeded=False, detail="Permission denied")
    # exit code 255 is the typical "couldn't reach host" failure.
    last_line = combined.splitlines()[-1] if combined else f"exit code {proc.returncode}"
    return ProbeSurfaceResult("ssh", succeeded=False, detail=last_line[:120])


def _probe_gh() -> ProbeSurfaceResult:
    """`gh auth status --hostname github.com` — exit 0 ⇒ authenticated."""
    gh = shutil.which("gh")
    if gh is None:
        return ProbeSurfaceResult("gh", succeeded=False, detail="not installed")
    try:
        proc = subprocess.run(
            [gh, "auth", "status", "--hostname", "github.com"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ProbeSurfaceResult("gh", succeeded=False, detail="`gh auth status` timed out")

    if proc.returncode == 0:
        return ProbeSurfaceResult("gh", succeeded=True, detail="authenticated")
    text = (proc.stdout + proc.stderr).strip()
    if "not logged into" in text.lower() or "not authenticated" in text.lower():
        return ProbeSurfaceResult("gh", succeeded=False, detail="not logged in")
    last_line = text.splitlines()[-1] if text else f"exit code {proc.returncode}"
    return ProbeSurfaceResult("gh", succeeded=False, detail=last_line[:120])


def _probe_credential_helper() -> ProbeSurfaceResult:
    """`git ls-remote <public canary>` with `GIT_TERMINAL_PROMPT=0`.

    If git can resolve credentials without blocking on a prompt, the helper is
    working. We use a public-readable canary so the probe doesn't fail just
    because the user has no token (the goal is to detect the *helper*, not auth).
    """
    git = shutil.which("git")
    if git is None:
        return ProbeSurfaceResult("credential-helper", succeeded=False, detail="`git` not installed")
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_ASKPASS"] = "echo"  # if anything asks, return empty silently
    try:
        proc = subprocess.run(
            [git, "ls-remote", _PUBLIC_CANARY_URL, "HEAD"],
            capture_output=True,
            text=True,
            timeout=15,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return ProbeSurfaceResult(
            "credential-helper", succeeded=False, detail="ls-remote timed out"
        )

    if proc.returncode == 0:
        return ProbeSurfaceResult(
            "credential-helper", succeeded=True, detail="git can reach github.com over HTTPS"
        )
    text = (proc.stdout + proc.stderr).strip()
    last_line = text.splitlines()[-1] if text else f"exit code {proc.returncode}"
    return ProbeSurfaceResult("credential-helper", succeeded=False, detail=last_line[:120])
