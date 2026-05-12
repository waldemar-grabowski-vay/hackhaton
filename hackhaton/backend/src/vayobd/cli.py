"""`vayobd` command-line entry point installed by the .deb at /usr/bin/vayobd.

Contract: specs/006-deb-package-distribution/contracts/cli.md.
Subcommands `run`, `refresh`, `doctor`. Also `--version`.
"""

from __future__ import annotations

import argparse
import getpass
import os
import socket
import sys
import webbrowser
from collections.abc import Sequence
from pathlib import Path

from vayobd.install.messages import must_run_as_user_message


def _exit_with_message(code: int, message: str, stream: str = "stderr") -> int:
    out = sys.stderr if stream == "stderr" else sys.stdout
    out.write(message.rstrip() + "\n")
    return code


def _refuse_if_root() -> int | None:
    """FR-015: refuse to run as root. Returns the exit code, or None to continue."""
    geteuid = getattr(os, "geteuid", None)
    if geteuid is not None and geteuid() == 0:
        return _exit_with_message(6, must_run_as_user_message())
    return None


def _cmd_run(args: argparse.Namespace) -> int:
    """Start the local diagnostic UI, after running the first-run flow if needed."""
    # Local imports keep startup fast for `--version` and root-guard paths.
    from vayobd.config import get_settings
    from vayobd.install.clone import clone_all
    from vayobd.install.credentials import probe_credentials
    from vayobd.install.manifest import (
        ManifestError,
        load_manifest,
    )
    from vayobd.install.messages import credential_failure_message
    from vayobd.install.state import load_state, save_state_atomic

    settings = get_settings()
    manifest_path = Path(args.manifest) if args.manifest else settings.manifest_path

    try:
        manifest = load_manifest(manifest_path)
    except ManifestError as exc:
        return _exit_with_message(3, f"Manifest at {manifest_path} couldn't be loaded: {exc}")

    state = load_state()

    # Trigger the clone flow when:
    #   - This is genuinely the first run (no repo ever synced), OR
    #   - The user has upgraded the .deb and the manifest now contains
    #     repos that aren't on disk yet (e.g. `ree-reecu-dbc` and
    #     `system-release-deployment` were added in 0.0.10). Without this,
    #     existing installs see "DBC not found" / "no-manifest" until the
    #     operator manually runs `vayobd refresh`.
    missing_targets = [
        entry for entry in manifest.repo if not entry.resolved_target().exists()
    ]
    if state.is_first_run or missing_targets:
        if missing_targets and not state.is_first_run:
            sys.stderr.write(
                f"⚠ Manifest has {len(missing_targets)} new repo(s) not yet cloned — "
                f"pulling now: {', '.join(e.id for e in missing_targets)}\n"
            )
        probe = probe_credentials()
        if probe.all_failed:
            return _exit_with_message(2, credential_failure_message(probe))
        result = clone_all(
            manifest, state, mode="clone", credential_surface=probe.winner
        )
        save_state_atomic(state)
        if not result.all_ok:
            failures = "\n".join(
                f"  • {r.repo_id}: {r.detail}" for r in result.failures
            )
            return _exit_with_message(
                3,
                "Couldn't fetch every required repo:\n"
                f"{failures}\nFix the issue above and run `vayobd run` again.",
            )

    if _port_in_use(args.port):
        return _exit_with_message(
            4,
            f"Port {args.port} is already in use. Use `vayobd run --port N` to pick a free port.",
        )

    # 008 / US2: warn loudly when the SPA static dir isn't configured. The
    # web UI returns 404 on every page in that state — confusing the operator
    # into thinking Live Diagnostic is broken. Most likely cause: running
    # through a pyenv/editable install that doesn't set VAYOBD_STATIC_DIR
    # the way the .deb's /usr/bin/vayobd wrapper does.
    if settings.static_dir is None:
        repo_relative_spa = Path(__file__).resolve().parents[3] / "frontend" / "dist" / "index.html"
        if not repo_relative_spa.is_file():
            sys.stderr.write(
                "⚠ SPA static dir not configured — the web UI will return 404 on every page.\n"
                "  Use /usr/bin/vayobd (the .deb wrapper) or export "
                "VAYOBD_STATIC_DIR=/usr/share/vayobd/spa before starting `vayobd run`.\n"
            )
            sys.stderr.flush()

    url = f"http://127.0.0.1:{args.port}/"
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except webbrowser.Error:
            pass  # Headless / no browser available — uvicorn still starts.

    # Spec 006: in the .deb (loopback, no proxy), seed the operator identity
    # from the OS user so authenticated routes (refresh, host versions, live)
    # work without a reverse proxy injecting X-Vay-User. A real proxy still
    # overrides this via the header — see backend/src/vayobd/api/auth.py.
    if not os.environ.get("VAYOBD_OPERATOR_USER"):
        try:
            os.environ["VAYOBD_OPERATOR_USER"] = getpass.getuser()
        except Exception:  # noqa: BLE001 — fall through to 401 if username unknown
            pass

    return _start_uvicorn(host="127.0.0.1", port=args.port)


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return True
    return False


def _start_uvicorn(*, host: str, port: int) -> int:
    """Run uvicorn in-process, bound to `host`. Returns the exit code."""
    import uvicorn  # local import — costly to import at module load

    try:
        uvicorn.run("vayobd.app:app", host=host, port=port, log_level="info")
    except KeyboardInterrupt:
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


def _cmd_refresh(args: argparse.Namespace) -> int:
    """Re-fetch every repo in the manifest. CLI half of FR-008."""
    from vayobd.config import get_settings
    from vayobd.install.clone import clone_all
    from vayobd.install.credentials import probe_credentials
    from vayobd.install.manifest import ManifestError, load_manifest
    from vayobd.install.messages import credential_failure_message
    from vayobd.install.state import load_state, save_state_atomic

    settings = get_settings()
    try:
        manifest = load_manifest(settings.manifest_path)
    except ManifestError as exc:
        return _exit_with_message(3, f"Manifest couldn't be loaded: {exc}")

    if getattr(args, "repo", None):
        manifest = manifest.model_copy(
            update={"repo": [r for r in manifest.repo if r.id == args.repo]}
        )
        if not manifest.repo:
            return _exit_with_message(3, f"No repo with id={args.repo!r} in the manifest.")

    state = load_state()
    probe = probe_credentials()
    if probe.all_failed:
        return _exit_with_message(2, credential_failure_message(probe))

    result = clone_all(manifest, state, mode="fetch", credential_surface=probe.winner)
    save_state_atomic(state)

    if not args.quiet:
        for r in result.repos:
            if r.outcome == "ok":
                sys.stdout.write(f"{r.repo_id}: ok (HEAD {r.resolved_revision[:7] if r.resolved_revision else '?'})\n")
            else:
                sys.stdout.write(f"{r.repo_id}: {r.outcome} — {r.detail}\n")
    return 0 if result.all_ok else 5


def _cmd_doctor(_args: argparse.Namespace) -> int:
    """Read-only health probe — paste-into-ticket format. Contract: cli.md."""
    from vayobd.config import get_settings
    from vayobd.install.credentials import probe_credentials
    from vayobd.install.manifest import ManifestError, load_manifest
    from vayobd.install.state import load_state

    settings = get_settings()

    lines: list[str] = [_version_string()]
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    lines.append(f"Python:         {py_ver}")

    try:
        manifest = load_manifest(settings.manifest_path)
        lines.append(
            f"Manifest:       {settings.manifest_path} (version {manifest.manifest_version}, "
            f"{len(manifest.repo)} repos)"
        )
    except ManifestError as exc:
        lines.append(f"Manifest:       {settings.manifest_path} — UNAVAILABLE: {exc}")
        manifest = None

    lines.append("")
    lines.append("Credential probe:")
    probe = probe_credentials()
    for surface in probe.surfaces:
        mark = "✓" if surface.succeeded else "✗"
        lines.append(f"  {mark} {surface.surface:<20} {surface.detail}")

    state = load_state()
    lines.append("")
    lines.append("Repos:")
    if not state.repo:
        lines.append("  (none — first run hasn't completed yet)")
    else:
        for repo_id, rs in state.repo.items():
            sha = (rs.resolved_revision or "—")[:7]
            ts = rs.last_synced_at.isoformat() if rs.last_synced_at else "never"
            lines.append(f"  {repo_id:<20} {rs.last_outcome:<14} last synced {ts}  HEAD {sha}")

    engine_path = (
        settings.ree_cli_bin
        or Path("/usr/lib/vayobd/bin/ree-debug-cli")
    )
    lines.append("")
    lines.append(f"Engine binary:  {engine_path} {'(exists)' if Path(engine_path).is_file() else '(MISSING)'}")

    anomalies = (
        probe.all_failed
        or manifest is None
        or any(rs.last_outcome != "ok" for rs in state.repo.values())
        or not Path(engine_path).is_file()
    )
    sys.stdout.write("\n".join(lines) + "\n")
    return 0 if not anomalies else 1


def _version_string() -> str:
    """Print version metadata. Build-time embedding lands in T036/T037."""
    try:
        from vayobd import _version  # type: ignore[attr-defined]

        return f"vayobd {_version.__version__} (commit {_version.__commit__})"
    except ImportError:
        return "vayobd 0.0.0-dev (no build metadata; running from a source checkout)"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vayobd", description="VayOBD diagnostics launcher")
    parser.add_argument(
        "--version", action="store_true", help="print the installed version and exit"
    )

    subparsers = parser.add_subparsers(dest="subcommand", metavar="{run,refresh,doctor}")

    run_p = subparsers.add_parser("run", help="start the local diagnostic UI")
    run_p.add_argument("--port", type=int, default=8000, help="uvicorn port (default: 8000)")
    run_p.add_argument(
        "--no-browser",
        action="store_true",
        help="do not try to open the user's browser on start",
    )
    run_p.add_argument(
        "--manifest",
        type=str,
        default=None,
        help="path to the required-repos manifest (overrides VAYOBD_MANIFEST_PATH)",
    )
    run_p.set_defaults(func=_cmd_run)

    refresh_p = subparsers.add_parser("refresh", help="re-fetch every repo in the manifest")
    refresh_p.add_argument("--repo", type=str, default=None, help="refresh only the named repo")
    refresh_p.add_argument("--quiet", action="store_true", help="only print the overall outcome")
    refresh_p.set_defaults(func=_cmd_refresh)

    doctor_p = subparsers.add_parser(
        "doctor",
        help="read-only health probe (paste output into support tickets)",
    )
    doctor_p.set_defaults(func=_cmd_doctor)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        sys.stdout.write(_version_string() + "\n")
        return 0

    root_exit = _refuse_if_root()
    if root_exit is not None:
        return root_exit

    func = getattr(args, "func", None)
    if func is None:
        # No subcommand → default to `run` (matches the .desktop launcher behaviour).
        args.subcommand = "run"
        run_p = build_parser()
        # Re-parse so default flags on `run` are populated.
        args = run_p.parse_args(["run"])
        func = args.func

    return func(args)


if __name__ == "__main__":  # pragma: no cover — invoked via console_script
    sys.exit(main())
