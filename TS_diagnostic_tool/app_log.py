"""
Tiny Qt-friendly logging handler — pipes Python's `logging` system into a
QPlainTextEdit so the user can read app diagnostics live, without a console.

Use it from main.py like:

    from app_log import attach_log_handler
    handler = attach_log_handler(self.app_log_view)
    # done — every logger.info/warn/error appears in the widget.
"""
from __future__ import annotations

import logging
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QPlainTextEdit


class _Bridge(QObject):
    """Carries log lines from any thread to the GUI thread via signals."""
    line = pyqtSignal(str)


class QtLogHandler(logging.Handler):
    LEVEL_PREFIX = {
        logging.DEBUG: "DBG",
        logging.INFO: "INF",
        logging.WARNING: "WRN",
        logging.ERROR: "ERR",
        logging.CRITICAL: "CRT",
    }

    def __init__(self, view: QPlainTextEdit) -> None:
        super().__init__()
        self._bridge = _Bridge()
        self._bridge.line.connect(view.appendPlainText)
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
            prefix = self.LEVEL_PREFIX.get(record.levelno, "LOG")
            msg = self.format(record)
            text = f"{ts} {prefix} {record.name}: {msg}"
            if record.exc_info:
                text += "\n" + logging.Formatter().formatException(record.exc_info)
            # Marshal onto GUI thread.
            self._bridge.line.emit(text)
        except Exception:  # noqa: BLE001
            self.handleError(record)


def attach_log_handler(view: QPlainTextEdit, level: int = logging.INFO) -> QtLogHandler:
    """Install the handler on the root logger and return it."""
    handler = QtLogHandler(view)
    handler.setLevel(level)
    root = logging.getLogger()
    root.addHandler(handler)
    if root.level > level:
        root.setLevel(level)
    return handler
