"""Clone / fetch orchestrator that walks the manifest as the invoking user.

`clone_all(manifest, state, *, mode)`:

- `mode="clone"`: first-run path. For each repo, the working tree is built in a
  per-repo *temporary* directory under `~/.cache/vayobd/.tmp-<id>-<pid>/`, and
  is only moved into place (`os.replace`) once the clone succeeded. If any repo
  in the run fails, every still-staged temp dir is removed before returning;
  that delivers FR-009's "consistent or unchanged, never half-applied" promise
  AND Story 2 AS-3's "no partial cache".
- `mode="fetch"`: refresh path. Each repo's existing checkout is fetched and
  fast-forwarded in place; on failure the local checkout is left at its old
  revision and the run is reported as a partial failure.

`clone_all` shells out to `git` (declared as a `Depends` of the .deb). It uses
no in-process VCS library — keeps the runtime dependency surface small and
inherits whatever credential helper the user already has working.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from vayobd.install.manifest import Manifest, RepoEntry
from vayobd.install.state import (
    CredentialSurface,
    ManifestState,
    RepoOutcome,
    RepoState,
)
from vayobd.logging import get_logger

log = get_logger(__name__)

CloneMode = Literal["clone", "fetch"]


@dataclass(frozen=True)
class RepoCloneResult:
    repo_id: str
    outcome: RepoOutcome
    resolved_revision: str | None
    detail: str  # plain-language reason on failure; empty string on success


@dataclass(frozen=True)
class CloneAllResult:
    """Aggregate result of `clone_all` over every repo in the manifest."""

    repos: list[RepoCloneResult]

    @property
    def all_ok(self) -> bool:
        return all(r.outcome == "ok" for r in self.repos)

    @property
    def failures(self) -> list[RepoCloneResult]:
        return [r for r in self.repos if r.outcome != "ok"]


def clone_all(
    manifest: Manifest,
    state: ManifestState,
    *,
    mode: CloneMode,
    credential_surface: CredentialSurface | None = None,
    env: Mapping[str, str] | None = None,
    runner: "RepoRunner | None" = None,
) -> CloneAllResult:
    """Walk `manifest` and clone (or fetch) every repo per `mode`.

    Updates `state` in place: per-repo `last_attempted_at`, `last_synced_at`,
    `resolved_revision`, `last_outcome`, plus aggregate `last_refresh_at` /
    `last_refresh_outcome` when `mode == "fetch"`. Caller is responsible for
    persisting the state to disk via `state.save_state_atomic(...)`.

    `runner` is an injection seam for tests — defaults to a real `RepoRunner`
    that shells out to `git`.
    """
    runner = runner or RepoRunner(env=env)
    now = datetime.now(UTC).replace(microsecond=0)
    results: list[RepoCloneResult] = []

    # First-run "no partial cache": stage everything into tmp dirs, then move
    # them into place only after every repo succeeded. If any repo fails, every
    # staged tmp dir is removed before returning.
    staged_moves: list[tuple[Path, Path]] = []

    total = len(manifest.repo)
    for idx, entry in enumerate(manifest.repo, start=1):
        target = entry.resolved_target()
        repo_state = state.repo.setdefault(entry.id, RepoState())
        repo_state.last_attempted_at = now

        verb = "Cloning" if mode == "clone" else "Fetching"
        sys.stderr.write(
            f"  [{idx}/{total}] {verb} {entry.id} → {target} …\n"
        )
        sys.stderr.flush()

        try:
            if mode == "clone":
                staged = _stage_clone(runner, entry, target)
                staged_moves.append((staged, target))
                rev = runner.head_rev(staged)
            else:  # fetch
                rev = _fetch_in_place(runner, entry, target)
        except RepoOperationError as exc:
            repo_state.last_outcome = exc.outcome
            sys.stderr.write(f"  ✗ {entry.id}: {exc.detail}\n")
            sys.stderr.flush()
            results.append(
                RepoCloneResult(
                    repo_id=entry.id,
                    outcome=exc.outcome,
                    resolved_revision=repo_state.resolved_revision,
                    detail=exc.detail,
                )
            )
            if mode == "clone":
                _rollback_staged(staged_moves)
                state.last_refresh_at = now
                state.last_refresh_outcome = exc.outcome
                # Bail early — first-run failure means we never move anything into place.
                return CloneAllResult(repos=results)
            continue

        repo_state.last_synced_at = now
        repo_state.resolved_revision = rev
        repo_state.last_outcome = "ok"
        sys.stderr.write(f"  ✓ {entry.id} @ {rev[:8]}\n")
        sys.stderr.flush()
        results.append(
            RepoCloneResult(
                repo_id=entry.id,
                outcome="ok",
                resolved_revision=rev,
                detail="",
            )
        )

    # First-run: move all staged tmp dirs into place. We do this only once every
    # repo has cloned successfully, so a partial failure above leaves no trace.
    if mode == "clone":
        for staged, target in staged_moves:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                shutil.rmtree(target)
            os.replace(staged, target)

    state.last_refresh_at = now
    aggregate = _aggregate_outcome(results)
    state.last_refresh_outcome = aggregate
    if credential_surface is not None:
        state.credential_surface_used = credential_surface
        state.last_credential_probe = now
    return CloneAllResult(repos=results)


def _aggregate_outcome(
    results: list[RepoCloneResult],
) -> Literal["partial_failure", "credentials_failed", "network_error", "conflict"] | None:
    failures = [r for r in results if r.outcome != "ok"]
    if not failures:
        return None
    if any(r.outcome == "auth-error" for r in failures):
        return "credentials_failed"
    if any(r.outcome == "network-error" for r in failures):
        return "network_error" if len(failures) == len(results) else "partial_failure"
    if any(r.outcome == "conflict" for r in failures):
        return "conflict"
    return "partial_failure"


def _stage_clone(runner: "RepoRunner", entry: RepoEntry, final_target: Path) -> Path:
    """Clone `entry.url` into a per-repo tmp dir; return the tmp path."""
    cache_root = Path.home() / ".cache" / "vayobd"
    cache_root.mkdir(parents=True, exist_ok=True)
    staged = cache_root / f".tmp-{entry.id}-{os.getpid()}"
    if staged.exists():
        shutil.rmtree(staged)

    runner.clone(entry, staged)
    if entry.sparse_paths:
        runner.sparse_checkout(staged, entry.sparse_paths)
    return staged


def _fetch_in_place(runner: "RepoRunner", entry: RepoEntry, target: Path) -> str:
    """Fetch + fast-forward an existing checkout. Returns the new HEAD SHA."""
    if not target.exists():
        # Treat as a clone — caller (refresh mode) will see this as recovery.
        target.parent.mkdir(parents=True, exist_ok=True)
        runner.clone(entry, target)
        if entry.sparse_paths:
            runner.sparse_checkout(target, entry.sparse_paths)
        return runner.head_rev(target)
    runner.fetch(target, entry.branch)
    return runner.head_rev(target)


def _rollback_staged(staged_moves: list[tuple[Path, Path]]) -> None:
    """Remove every tmp dir that was staged for a clone but not yet moved."""
    for staged, _target in staged_moves:
        try:
            if staged.is_dir():
                shutil.rmtree(staged)
        except OSError as exc:  # pragma: no cover — best-effort cleanup
            log.warning("clone_rollback_cleanup_failed", path=str(staged), error=str(exc))


class RepoOperationError(Exception):
    """Raised by `RepoRunner` when a git invocation fails.

    Carries the typed `outcome` used to populate `RepoState.last_outcome` and
    drive the refresh-failure messaging.
    """

    def __init__(self, outcome: RepoOutcome, detail: str) -> None:
        super().__init__(detail)
        self.outcome = outcome
        self.detail = detail


@dataclass
class RepoRunner:
    """Thin shell-out wrapper around `git`. Injection seam for tests."""

    env: Mapping[str, str] | None = None
    _timeout: float = 120.0

    def _run(
        self,
        args: list[str],
        cwd: Path | None = None,
        *,
        stream_stderr: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        full_env = os.environ.copy()
        # Force non-interactive auth — never block on a prompt.
        full_env.setdefault("GIT_TERMINAL_PROMPT", "0")
        if self.env:
            full_env.update(self.env)
        if stream_stderr:
            # Capture stdout for parsing; let git's stderr (progress lines)
            # pass through to the operator's terminal so a long clone shows
            # "Receiving objects: N% …" instead of looking hung.
            return subprocess.run(
                args,
                cwd=str(cwd) if cwd else None,
                env=full_env,
                check=False,
                stdout=subprocess.PIPE,
                stderr=None,  # inherit
                text=True,
                timeout=self._timeout,
            )
        return subprocess.run(
            args,
            cwd=str(cwd) if cwd else None,
            env=full_env,
            check=False,
            capture_output=True,
            text=True,
            timeout=self._timeout,
        )

    def clone(self, entry: RepoEntry, target: Path) -> None:
        args = ["git", "clone", "--progress"]
        if entry.branch:
            args += ["--branch", entry.branch]
        if entry.sparse_paths:
            args += ["--no-checkout"]
        args += [entry.url, str(target)]
        # Stream stderr so the operator sees git's progress on slow clones.
        proc = self._run(args, stream_stderr=True)
        if proc.returncode != 0:
            stderr_text = proc.stderr or ""
            raise RepoOperationError(
                _classify_git_error(stderr_text),
                stderr_text.strip().splitlines()[-1] if stderr_text.strip() else "git clone failed",
            )

    def sparse_checkout(self, target: Path, paths: list[str]) -> None:
        # `git sparse-checkout` initialises + sets the include list in one go.
        init = self._run(["git", "sparse-checkout", "init", "--cone"], cwd=target)
        if init.returncode != 0:
            # Non-cone fallback for older git or non-cone-compatible paths.
            init = self._run(["git", "sparse-checkout", "init"], cwd=target)
            if init.returncode != 0:
                raise RepoOperationError(
                    "conflict",
                    f"sparse-checkout init failed: {init.stderr.strip().splitlines()[-1]}",
                )
        set_ = self._run(["git", "sparse-checkout", "set", *paths], cwd=target)
        if set_.returncode != 0:
            raise RepoOperationError(
                "conflict",
                f"sparse-checkout set failed: {set_.stderr.strip().splitlines()[-1]}",
            )
        # After --no-checkout, materialise the working tree.
        co = self._run(["git", "checkout"], cwd=target)
        if co.returncode != 0:
            raise RepoOperationError(
                "conflict",
                f"git checkout after sparse-checkout set failed: {co.stderr.strip().splitlines()[-1]}",
            )

    def fetch(self, target: Path, branch: str | None) -> None:
        fetch = self._run(["git", "fetch", "--prune", "origin"], cwd=target)
        if fetch.returncode != 0:
            raise RepoOperationError(
                _classify_git_error(fetch.stderr),
                fetch.stderr.strip().splitlines()[-1]
                if fetch.stderr.strip()
                else "git fetch failed",
            )
        if branch:
            reset = self._run(["git", "reset", "--hard", f"origin/{branch}"], cwd=target)
            if reset.returncode != 0:
                raise RepoOperationError(
                    "conflict",
                    reset.stderr.strip().splitlines()[-1]
                    if reset.stderr.strip()
                    else "git reset --hard failed",
                )

    def head_rev(self, target: Path) -> str:
        proc = self._run(["git", "rev-parse", "HEAD"], cwd=target)
        if proc.returncode != 0:
            raise RepoOperationError(
                "conflict",
                proc.stderr.strip().splitlines()[-1]
                if proc.stderr.strip()
                else "git rev-parse failed",
            )
        return proc.stdout.strip()


def _classify_git_error(stderr: str) -> RepoOutcome:
    """Heuristic: map git's stderr to one of our typed outcomes."""
    text = stderr.lower()
    if any(needle in text for needle in ("permission denied", "could not read", "authentication", "not found", "repository not found")):
        return "auth-error"
    if any(needle in text for needle in ("could not resolve host", "connection refused", "operation timed out", "network is unreachable")):
        return "network-error"
    return "conflict"
