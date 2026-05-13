"""
Background `git pull --ff-only` runner.

Used to keep the local ree-reecu repo current at app launch — the DBC and
errq CSVs both live under there, so a stale clone produces stale results.

Runs in a QThread so the UI doesn't freeze for the network round-trip.
Emits a signal with a short status string the UI can drop into the
toolbar / log dock.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from config import GIT_PULL_TIMEOUT_S, REPO_ROOT, VEHICLE_CONFIGS_ROOT

log = logging.getLogger(__name__)


class GitPullWorker(QObject):
    # short_status, full_output, repo_label (e.g. "ree-reecu_main")
    finished = pyqtSignal(str, str, str)
    # Per-repo progress so the UI can update its labels as each repo finishes.
    repo_done = pyqtSignal(str, str, str)  # (repo_label, short, full_output)

    def __init__(
        self,
        repos: list[Path] | None = None,
        timeout_s: int = GIT_PULL_TIMEOUT_S,
    ):
        super().__init__()
        # Default: pull both repos the app depends on. Caller can override.
        self._repos = repos if repos is not None else [REPO_ROOT, VEHICLE_CONFIGS_ROOT]
        self._timeout = timeout_s
        # Bound at run() — the currently-pulling repo, used by helpers.
        self._repo: Path = self._repos[0]

    @staticmethod
    def _is_ref_conflict(output: str) -> bool:
        out = output.lower()
        return (
            "cannot lock ref" in out
            or "some local refs could not be updated" in out
            or "unable to update local ref" in out
        )

    def _git_simple(self, args: list[str], timeout: int = 10) -> subprocess.CompletedProcess | None:
        cmd = ["git", "-C", str(self._repo), *args]
        log.info("repo: running %s", " ".join(cmd))
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError:
            log.warning("repo: git executable not found on PATH")
            return None
        except subprocess.TimeoutExpired:
            log.warning("repo: %s exceeded %ds", " ".join(cmd), timeout)
            return None
        except Exception:  # noqa: BLE001
            log.exception("repo: %s failed", " ".join(cmd))
            return None

    def run(self) -> None:
        last_short = "ok"
        last_full = ""
        for repo in self._repos:
            self._repo = repo
            label = repo.name
            short, full = self._pull_one()
            self.repo_done.emit(label, short, full)
            last_short, last_full = short, full
        # finished is emitted once at the end with the LAST repo's status —
        # most callers care about overall progress; per-repo updates go via
        # repo_done.
        self.finished.emit(last_short, last_full, self._repos[-1].name if self._repos else "")

    def _pull_one(self) -> tuple[str, str]:
        """
        Update remote refs (`fetch --prune`) and, if the current branch has
        an upstream and is fast-forward-able, advance it.

        We deliberately don't use `pull --ff-only` because it needs the
        local branch to track a remote — many engineers work on local
        topic branches that don't, and `pull` then fails with "no
        tracking information for the current branch".
        """
        if not self._repo.exists():
            return "repo missing", f"{self._repo} does not exist"
        if not (self._repo / ".git").exists():
            return "not a git repo", f"{self._repo} has no .git directory"

        # Fetch (with prune to clean up stale remote refs).
        fetch_proc = self._git_fetch()
        if fetch_proc is None:
            return "fetch failed", "(see App Log)"
        fetch_out = (fetch_proc.stdout or "") + (fetch_proc.stderr or "")

        # Self-heal stale-ref conflicts and retry once.
        if fetch_proc.returncode != 0 and self._is_ref_conflict(fetch_out):
            log.warning("repo: fetch blocked by stale ref, running 'git remote prune origin'")
            prune_proc = self._git_simple(["remote", "prune", "origin"], timeout=10)
            if prune_proc is not None:
                log.info("repo: prune output: %s",
                         (prune_proc.stdout + prune_proc.stderr).strip())
            fetch_proc = self._git_fetch()
            if fetch_proc is None:
                return "fetch failed", "(see App Log)"
            fetch_out = (fetch_proc.stdout or "") + (fetch_proc.stderr or "")

        if fetch_proc.returncode != 0:
            lowered = fetch_out.lower()
            if "permission denied" in lowered or "could not read from remote" in lowered:
                return "auth failed", fetch_out.strip()
            if "could not resolve host" in lowered or "network is unreachable" in lowered:
                return "offline", fetch_out.strip()
            return "fetch failed", fetch_out.strip() or f"exit {fetch_proc.returncode}"

        # Fetch succeeded. Now figure out where HEAD is and whether it can
        # fast-forward to its upstream.
        branch = self._git_branch()
        head_short = self._git_head_short() or "?"

        if not branch or branch == "HEAD":
            return f"fetched (detached @ {head_short})", fetch_out.strip()

        upstream = self._git_upstream()
        if not upstream:
            return f"fetched (no upstream for {branch} @ {head_short})", fetch_out.strip()

        # Try fast-forward; ff-only ensures we never silently merge.
        merge_proc = self._git_simple(["merge", "--ff-only", upstream], timeout=15)
        merge_out = ""
        if merge_proc is not None:
            merge_out = (merge_proc.stdout or "") + (merge_proc.stderr or "")
        if merge_proc is None or merge_proc.returncode != 0:
            return (
                f"fetched ({branch} @ {head_short} — local diverged, no ff)",
                (fetch_out + "\n" + merge_out).strip(),
            )

        new_head = self._git_head_short() or head_short
        full = (fetch_out + "\n" + merge_out).strip()
        if new_head == head_short:
            return f"up to date @ {head_short}", full
        return f"fast-forwarded {head_short}→{new_head}", full

    # ----- small git helpers used by _pull_one -----
    def _git_fetch(self) -> "subprocess.CompletedProcess | None":
        return self._git_simple(["fetch", "--prune", "origin"], timeout=self._timeout)

    def _git_branch(self) -> str:
        proc = self._git_simple(["rev-parse", "--abbrev-ref", "HEAD"], timeout=5)
        return (proc.stdout if proc else "").strip()

    def _git_upstream(self) -> str:
        # Empty string + non-zero exit when no upstream is set.
        proc = self._git_simple(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            timeout=5,
        )
        if proc is None or proc.returncode != 0:
            return ""
        return (proc.stdout or "").strip()

    def _git_head_short(self) -> str:
        proc = self._git_simple(["rev-parse", "--short", "HEAD"], timeout=5)
        return (proc.stdout if proc else "").strip()


def start_git_pull(
    parent: QObject,
    on_repo_done,
    on_all_done,
    repos: list[Path] | None = None,
) -> tuple[QThread, GitPullWorker]:
    """
    Spawn the worker on a fresh QThread. The caller keeps refs to the
    returned (thread, worker) pair so they aren't garbage-collected mid-run.

      on_repo_done(repo_label, short, full_output)  — fired once per repo
      on_all_done(short, full_output, last_label)   — fired when everything is done
    """
    thread = QThread(parent)
    worker = GitPullWorker(repos=repos)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.repo_done.connect(on_repo_done)
    worker.finished.connect(on_all_done)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread, worker
