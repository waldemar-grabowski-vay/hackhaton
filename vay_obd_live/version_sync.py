"""
Match a controller's reported FW version to a git ref in ree-reecu_main,
then check it out so the loaded DBC + errq line up with what's running on
the actual TS / VE.

Released firmware reports `MAJOR.MINOR.PATCH` where PATCH is decimal — the
matching ref is the tag `R{MAJOR}.{MINOR}.{PATCH}` (e.g. R10.1.2).

Custom-branch firmware encodes a short commit hash into the 16-bit PATCH
field (no release number). In that case we render the patch as a 4-char
hex string and try it as a commit prefix via `git rev-parse`.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class FwVersion:
    major: int
    minor: int
    patch: int

    @property
    def release_tag(self) -> str:
        return f"R{self.major}.{self.minor}.{self.patch}"

    @property
    def patch_hex4(self) -> str:
        # 16-bit field rendered as a 4-char lowercase hex prefix —
        # how custom-branch firmwares encode their commit hash.
        return f"{self.patch & 0xFFFF:04x}"

    def short(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch} (0x{self.patch_hex4})"


@dataclass
class RefMatch:
    ref: str          # the symbolic ref the user accepts (tag, branch, sha)
    commit: str       # full SHA the ref resolves to
    kind: str         # "tag" | "branch" | "commit"


def _git(repo: Path, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:  # noqa: BLE001
        log.exception("git %s failed", " ".join(args))
        return None


def _resolve_ref(repo: Path, ref: str) -> str | None:
    """Return the full SHA for `ref` if it exists, else None."""
    proc = _git(repo, ["rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"])
    if proc is None or proc.returncode != 0:
        return None
    sha = (proc.stdout or "").strip()
    return sha or None


def find_match(repo: Path, ver: FwVersion) -> RefMatch | None:
    """
    Try a sequence of conventional refs; return the first one that resolves.

    Order:
        1. Tag R{maj}.{min}.{patch}      — release builds
        2. Tag v{maj}.{min}.{patch}      — alternate convention
        3. Branch release/{maj}.{min}.{patch}
        4. Patch-as-hex commit prefix    — custom branch builds
    """
    candidates: list[tuple[str, str]] = [
        (ver.release_tag, "tag"),
        (f"v{ver.major}.{ver.minor}.{ver.patch}", "tag"),
        (f"release/{ver.major}.{ver.minor}.{ver.patch}", "branch"),
    ]
    if ver.patch > 0:
        # Hex commit prefix; rev-parse will resolve a unique short SHA.
        candidates.append((ver.patch_hex4, "commit"))

    for ref, kind in candidates:
        sha = _resolve_ref(repo, ref)
        if sha:
            log.info("version-sync: matched %s -> %s (%s)", ref, sha[:10], kind)
            return RefMatch(ref=ref, commit=sha, kind=kind)
        else:
            log.debug("version-sync: no match for %s", ref)
    return None


def working_tree_clean(repo: Path) -> bool:
    proc = _git(repo, ["status", "--porcelain"])
    if proc is None or proc.returncode != 0:
        return False
    return not (proc.stdout or "").strip()


def current_head(repo: Path) -> tuple[str, str]:
    """Return (ref-name, short-sha). Ref-name is "HEAD" when detached."""
    name = ""
    proc = _git(repo, ["symbolic-ref", "--short", "-q", "HEAD"])
    if proc and proc.returncode == 0:
        name = (proc.stdout or "").strip()
    if not name:
        # detached
        name = "HEAD (detached)"
    proc = _git(repo, ["rev-parse", "--short", "HEAD"])
    short = (proc.stdout or "").strip() if proc else ""
    return name, short


def checkout(repo: Path, ref: str) -> tuple[bool, str]:
    """Check out `ref`. Returns (ok, output)."""
    proc = _git(repo, ["checkout", ref], timeout=20)
    if proc is None:
        return False, "git checkout did not run"
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, out.strip()
