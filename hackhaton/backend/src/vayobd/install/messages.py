"""Plain-language strings rendered to the CLI (stderr) and the HTTP API.

Wording aligned with Constitution Principle III (Non-Technical User UX) — names
each surface tried and the next concrete action; never prints stack traces.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vayobd.install.state import ManifestState


@dataclass(frozen=True)
class ProbeSurfaceResult:
    """Outcome of probing one credential surface."""

    surface: str  # "ssh" | "gh" | "credential-helper"
    succeeded: bool
    detail: str  # one-line, plain language; "not configured", "Permission denied", etc.


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of probing every credential surface in order."""

    surfaces: list[ProbeSurfaceResult] = field(default_factory=list)

    @property
    def winner(self) -> str | None:
        for s in self.surfaces:
            if s.succeeded:
                return s.surface
        return None

    @property
    def all_failed(self) -> bool:
        return self.winner is None


# Display names used in user-facing copy. Keep terse, no jargon.
_SURFACE_LABEL: dict[str, str] = {
    "ssh": "SSH (ssh -T git@github.com)",
    "gh": "GitHub CLI (gh auth status)",
    "credential-helper": "System credential helper",
}


def credential_failure_message(result: ProbeResult) -> str:
    """Render the FR-005 plain-language credential-failure block.

    Spec source: research.md § 5 (this VayOBD couldn't read your GitHub credentials).
    """
    lines = ["VayOBD couldn't read your GitHub credentials.", "", "I tried, in order:"]
    for s in result.surfaces:
        label = _SURFACE_LABEL.get(s.surface, s.surface)
        arrow = "→ ok" if s.succeeded else f"→ failed: {s.detail}"
        lines.append(f"  • {label:<38} {arrow}")
    lines.extend(
        [
            "",
            "To fix this, do one of:",
            "  • Add your SSH key to GitHub and make sure ssh-agent has it loaded, OR",
            "  • Run `gh auth login` (the GitHub CLI is installed by this package)",
            "",
            "Then run `vayobd run` again. No data has been changed.",
        ]
    )
    return "\n".join(lines)


def partial_clone_warning(repo_id: str, reason: str) -> str:
    """Per-repo failure line printed when one clone fails inside `clone_all`."""
    return f"Couldn't fetch `{repo_id}`: {reason}. No changes have been kept for this repo."


def refresh_outcome_message(state: ManifestState) -> str:
    """One-line refresh summary suitable for stdout or the staleness banner."""
    if state.last_refresh_outcome is None:
        return "All repos refreshed successfully."
    if state.last_refresh_outcome == "partial_failure":
        broken = [
            rid for rid, rs in state.repo.items() if rs.last_outcome != "ok"
        ]
        if broken:
            joined = ", ".join(f"`{r}`" for r in broken)
            return f"Refresh partially failed. These repos still use older data: {joined}."
        return "Refresh partially failed. See `vayobd doctor` for details."
    if state.last_refresh_outcome == "credentials_failed":
        return "Refresh stopped: your GitHub credentials are no longer working."
    if state.last_refresh_outcome == "network_error":
        return "Refresh couldn't reach GitHub. Check your network and try again."
    if state.last_refresh_outcome == "conflict":
        return "Refresh found a conflict in your local cache; see `vayobd doctor`."
    return f"Refresh outcome: {state.last_refresh_outcome}."


def must_run_as_user_message() -> str:
    """FR-015 message printed when `vayobd` is invoked as root."""
    return (
        "VayOBD must run as your normal user, not as root.\n"
        "The `.deb` installs system files at install time; running the app\n"
        "itself as root would put your cached repos in /root and break things\n"
        "for everyone else on this machine."
    )
