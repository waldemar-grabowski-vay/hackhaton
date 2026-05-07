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

from config import GIT_PULL_TIMEOUT_S, REPO_ROOT

log = logging.getLogger(__name__)


class GitPullWorker(QObject):
    finished = pyqtSignal(str, str)  # (short_status, full_output)

    def __init__(self, repo_root: Path = REPO_ROOT, timeout_s: int = GIT_PULL_TIMEOUT_S):
        super().__init__()
        self._repo = repo_root
        self._timeout = timeout_s

    def run(self) -> None:
        if not self._repo.exists():
            self.finished.emit("repo missing", f"{self._repo} does not exist")
            return
        if not (self._repo / ".git").exists():
            self.finished.emit("not a git repo", f"{self._repo} has no .git directory")
            return

        cmd = ["git", "-C", str(self._repo), "pull", "--ff-only"]
        log.info("repo: running %s", " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                # Don't open a console window on Windows for the GUI build.
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError:
            self.finished.emit("git missing", "git executable not found on PATH")
            return
        except subprocess.TimeoutExpired:
            self.finished.emit("pull timed out", f"git pull exceeded {self._timeout}s")
            return
        except Exception as exc:  # noqa: BLE001
            self.finished.emit("pull failed", repr(exc))
            return

        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            self.finished.emit("pull failed", out.strip() or f"exit {proc.returncode}")
            return

        # Build a short summary from the output
        lower = out.lower()
        if "already up to date" in lower or "already up-to-date" in lower:
            short = "up to date"
        elif "fast-forward" in lower:
            short = "fast-forwarded"
        elif "files changed" in lower:
            short = "updated"
        else:
            short = "ok"

        # Capture HEAD short hash so the user can verify the version.
        try:
            head = subprocess.run(
                ["git", "-C", str(self._repo), "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout.strip()
            if head:
                short = f"{short} @ {head}"
        except Exception:  # noqa: BLE001
            pass

        self.finished.emit(short, out.strip())


def start_git_pull(parent: QObject, on_done) -> tuple[QThread, GitPullWorker]:
    """
    Spawn the worker on a fresh QThread. The caller keeps refs to the
    returned (thread, worker) pair so they aren't garbage-collected mid-run.

    `on_done(short_status, full_output)` is invoked on the GUI thread.
    """
    thread = QThread(parent)
    worker = GitPullWorker()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(on_done)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    thread.start()
    return thread, worker
