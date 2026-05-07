"""
TS Diagnostic Tool — POC entrypoint.

Layout:
    +----------------------------------------------------------+
    | toolbar:  [Connect] [Disconnect]  status: ...            |
    +----------------------------+-----------------------------+
    | TS System State (signals)  | Decoded Errors (errq)       |
    |                            |                             |
    +----------------------------+-----------------------------+
    | Raw CAN log (collapsible dock)                           |
    +----------------------------------------------------------+

Run:
    python main.py
"""
from __future__ import annotations

import logging
import sys
from collections import deque
from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

import paramiko

from config import (
    AUTO_GIT_PULL,
    MAX_ERROR_ROWS,
    MAX_LOG_ROWS,
    REMOTE_HOST,
    REMOTE_PORT,
    REMOTE_USER,
    REPO_ROOT,
    TS_STATE_INDICATORS,
    TS_STATE_SIGNALS,
    UI_REFRESH_MS,
)
from app_log import attach_log_handler
from asc_recorder import AscRecorder
from connection_dialog import ConnectionCreds, ConnectionDialog
from dbc_handler import DbcDecoder, DecodedFrame, find_dbc
from errq_aggregator import ErrqAggregator
from errq_bridge import (
    decode_errq_buffer,
    errq_path as errq_current_path,
    is_resolved as errq_is_resolved,
    model_status as errq_model_status,
    set_errq_path,
)
from errq_state import ESTOP_KEY, ErrqEntry, ErrqStateTracker, VIRTUAL_CHANNEL
from repo_updater import start_git_pull
from ssh_can_reader import CanStreamer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ts_diag")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
SEVERITY_COLOR = {
    "critical": QColor(170, 0, 0),
    "error":    QColor(220, 60, 60),
    "warn":     QColor(220, 160, 30),
    "info":     QColor(70, 130, 180),
}

# Column indices for the Decoded Errors table.
_COL_TIME = 0
_COL_CHANNEL = 1
_COL_BUS = 2
_COL_CAN_ID = 3
_COL_BYTE = 4
_COL_BIT = 5
_COL_ERROR = 6
_COL_CLEARED = 7
_COL_STATUS = 8

ERROR_HEADERS = (
    "First seen", "Channel", "Bus", "CAN ID",
    "Byte", "Bit", "Error", "Cleared at", "Status",
)

# Active = bright red, Passive = muted gray italic so cleared errors stay
# visible but don't compete for attention.
COLOR_ACTIVE = QColor(200, 35, 35)
COLOR_PASSIVE = QColor(120, 120, 120)
COLOR_INDICATOR_ORANGE = QColor(255, 165, 0)
COLOR_INDICATOR_RED = QColor(220, 60, 60)


class _NumericItem(QTableWidgetItem):
    """Table item that sorts numerically by a separately-stored value."""

    def __init__(self, text: str, sort_value: float):
        super().__init__(text)
        self._sort_value = sort_value

    def __lt__(self, other) -> bool:  # noqa: D401
        try:
            return self._sort_value < other._sort_value  # type: ignore[attr-defined]
        except AttributeError:
            return super().__lt__(other)


class StatusLED(QFrame):
    """Small round colored indicator. Use set_state('green'|'yellow'|'red'|'gray')."""

    _COLORS = {
        "gray":   ("#777", "no data"),
        "green":  ("#1a7f37", "OK — no faults"),
        "yellow": ("#e3a008", "Soft fault active (recoverable)"),
        "red":    ("#c0392b", "Hard fault active (unrecoverable)"),
    }

    def __init__(self, diameter: int = 16, parent=None):
        super().__init__(parent)
        self.setFixedSize(diameter, diameter)
        self._diameter = diameter
        self.set_state("gray")

    def set_state(self, name: str) -> None:
        color, tooltip = self._COLORS.get(name, self._COLORS["gray"])
        # Round LED with subtle border so it's visible on both light & dark themes.
        self.setStyleSheet(
            f"background-color: {color}; "
            f"border-radius: {self._diameter // 2}px; "
            f"border: 1px solid #444;"
        )
        self.setToolTip(tooltip)


def fmt_ts(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%H:%M:%S.%f")[:-3]


# --------------------------------------------------------------------------
# Main window
# --------------------------------------------------------------------------
class DiagnosticWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TS Diagnostic Tool — POC")
        self.resize(1280, 800)

        self.decoder = DbcDecoder()
        self.streamer: CanStreamer | None = None
        self.state_rows: dict[str, int] = {}
        self.recent_log: deque[str] = deque(maxlen=MAX_LOG_ROWS)
        self.errq_aggregator = ErrqAggregator()
        self.errq_state = ErrqStateTracker()
        # State panel signal patterns — case-insensitive for matching.
        self._state_signal_patterns = tuple(s.lower() for s in TS_STATE_SIGNALS)
        # Latest SSMAN values per role ("VE_A","VE_B","TS_A","TS_B") used
        # to compute the status LED. Stored as the enum string.
        self._ssman: dict[str, str] = {}
        # Diagnostic flags so we log "first ERRQ frame seen" exactly once.
        self._errq_signal_logged = False
        self._errq_nonzero_logged = False
        self._errq_decode_failure_logged = False
        # Recording state.
        self._recorder: AscRecorder | None = None
        # Background git-pull thread (kept on self so it isn't GC'd mid-run).
        self._git_thread = None
        self._git_worker = None

        # Session-only credentials. Defaults come from config; overridden
        # by the Connection Settings dialog. Never persisted to disk.
        self.creds = ConnectionCreds(
            host=REMOTE_HOST,
            user=REMOTE_USER,
            port=REMOTE_PORT,
            key_filename=None,
            passphrase=None,
            password=None,
        )
        self._last_connect_error: str | None = None

        self._build_ui()
        self._build_toolbar()

        # Kick off git pull in the background — it's network-bound, so we
        # don't block startup. DBC + errq are loaded once it finishes (or
        # immediately if AUTO_GIT_PULL is disabled).
        if AUTO_GIT_PULL:
            self.repo_label.setText("Repo: pulling...")
            self.repo_label.setStyleSheet("color: #888;")
            self._git_thread, self._git_worker = start_git_pull(self, self._on_git_pull_done)
        else:
            self.repo_label.setText("Repo: pull disabled")
            self._post_repo_init()

    def _on_git_pull_done(self, short: str, full_output: str) -> None:
        log.info("repo pull: %s", short)
        if full_output:
            for line in full_output.splitlines():
                if line.strip():
                    log.info("repo: %s", line)
        if "fail" in short.lower() or "missing" in short.lower() or "timed out" in short.lower():
            self.repo_label.setText(f"Repo: {short}")
            self.repo_label.setStyleSheet("color: #c0392b;")
        else:
            self.repo_label.setText(f"Repo: {short}")
            self.repo_label.setStyleSheet("color: #1a7f37;")
        self._post_repo_init()

    def _post_repo_init(self) -> None:
        """Run startup steps that depend on the repo being current."""
        self._auto_load_dbc()
        self._refresh_errq_status()
        if not errq_is_resolved():
            QTimer.singleShot(200, self._show_errq_startup_warning)

        # UI refresh tick — drains the queue and updates widgets.
        self._timer = QTimer(self)
        self._timer.setInterval(UI_REFRESH_MS)
        self._timer.timeout.connect(self._drain_queue)
        self._timer.start()

    # ---- UI build ----
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        # Visible handle so it's clear the divider can be dragged. Don't
        # let the user collapse a panel to nothing by accident.
        splitter.setHandleWidth(8)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter)

        # ---- left: TS state panel ----
        left = QWidget()
        lv = QVBoxLayout(left)

        # Title row: "TS System State" + status LED.
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel("TS System State")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_row.addWidget(title)
        self.state_led = StatusLED()
        title_row.addWidget(self.state_led)
        title_row.addStretch(1)
        lv.addLayout(title_row)

        self.state_table = QTableWidget(0, 2)
        self.state_table.setHorizontalHeaderLabels(["Signal", "Value"])
        # Interactive lets the user drag column boundaries. Stretch the
        # last (Value) column so the panel always fills its width but
        # the user can override by dragging.
        self.state_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.state_table.horizontalHeader().setStretchLastSection(True)
        self.state_table.setColumnWidth(0, 240)  # sensible default for signal name
        self.state_table.verticalHeader().setVisible(False)
        self.state_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lv.addWidget(self.state_table)
        splitter.addWidget(left)

        # ---- right: errors table ----
        right = QWidget()
        rv = QVBoxLayout(right)
        title2 = QLabel("Decoded Errors")
        title2.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        rv.addWidget(title2)
        self.error_table = QTableWidget(0, len(ERROR_HEADERS))
        self.error_table.setHorizontalHeaderLabels(list(ERROR_HEADERS))
        self.error_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.error_table.horizontalHeader().setStretchLastSection(True)
        self.error_table.verticalHeader().setVisible(False)
        self.error_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # Click any column header to re-sort. Default: group by Channel
        # ascending, then Byte ascending — matches what you'd want when
        # scanning a fresh ERRQ snapshot.
        self.error_table.setSortingEnabled(True)
        self.error_table.sortItems(_COL_CHANNEL, Qt.SortOrder.AscendingOrder)
        rv.addWidget(self.error_table)
        splitter.addWidget(right)

        splitter.setSizes([400, 880])

        # ---- raw log dock ----
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(MAX_LOG_ROWS)
        font = QFont("Consolas", 9)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.log_view.setFont(font)
        self.log_view.setMinimumHeight(180)
        self.log_dock = QDockWidget("Raw CAN log", self)
        self.log_dock.setWidget(self.log_view)
        self.log_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.log_dock)
        # Give the dock a sensible default share of vertical space — without
        # this Qt sometimes collapses it to ~30 px on first show.
        self.resizeDocks([self.log_dock], [260], Qt.Orientation.Vertical)

        # ---- App Log dock (tabified with Raw CAN log) ----
        self.app_log_view = QPlainTextEdit()
        self.app_log_view.setReadOnly(True)
        self.app_log_view.setMaximumBlockCount(MAX_LOG_ROWS)
        self.app_log_view.setFont(font)
        self.app_log_view.setMinimumHeight(180)
        self.app_log_dock = QDockWidget("App Log", self)
        self.app_log_dock.setWidget(self.app_log_view)
        self.app_log_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.app_log_dock)
        # Stack the two log docks as tabs at the bottom — one click to switch.
        self.tabifyDockWidget(self.log_dock, self.app_log_dock)
        # Default to showing the App Log tab on launch so the user notices
        # it (it's the new feature). They can flip back to Raw CAN log.
        self.app_log_dock.raise_()

        # Wire Python logging into the App Log view.
        self._app_log_handler = attach_log_handler(self.app_log_view)

        # ---- status bar ----
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Idle.")

    def _build_toolbar(self) -> None:
        tb = QToolBar("main")
        tb.setMovable(False)
        self.addToolBar(tb)

        self.act_connect = QAction("Connect", self)
        self.act_connect.triggered.connect(self._on_connect)
        tb.addAction(self.act_connect)

        self.act_disconnect = QAction("Disconnect", self)
        self.act_disconnect.setEnabled(False)
        self.act_disconnect.triggered.connect(self._on_disconnect)
        tb.addAction(self.act_disconnect)

        self.act_settings = QAction("Settings...", self)
        self.act_settings.triggered.connect(self._on_open_settings)
        tb.addAction(self.act_settings)

        tb.addSeparator()

        self.act_reload_dbc = QAction("Reload DBC", self)
        self.act_reload_dbc.triggered.connect(self._auto_load_dbc)
        tb.addAction(self.act_reload_dbc)

        self.act_browse_dbc = QAction("Browse DBC...", self)
        self.act_browse_dbc.triggered.connect(self._on_browse_dbc)
        tb.addAction(self.act_browse_dbc)

        self.act_browse_errq = QAction("Browse errq...", self)
        self.act_browse_errq.triggered.connect(self._on_browse_errq)
        tb.addAction(self.act_browse_errq)

        self.act_clear = QAction("Clear", self)
        self.act_clear.triggered.connect(self._clear_views)
        tb.addAction(self.act_clear)

        tb.addSeparator()
        self.act_record = QAction("Record...", self)
        self.act_record.setCheckable(True)
        self.act_record.toggled.connect(self._on_toggle_record)
        tb.addAction(self.act_record)

        tb.addSeparator()
        self.dbc_label = QLabel("DBC: <none>")
        tb.addWidget(self.dbc_label)

        tb.addSeparator()
        self.errq_label = QLabel("Errq: <pending>")
        tb.addWidget(self.errq_label)

        tb.addSeparator()
        self.repo_label = QLabel("Repo: idle")
        tb.addWidget(self.repo_label)

    # ---- DBC ----
    def _auto_load_dbc(self) -> None:
        path = find_dbc()
        if path is None:
            self.dbc_label.setText("DBC: <not found>")
            self._set_status(
                "DBC not found — use 'Browse DBC...' to pick one, or set REPO_ROOT / "
                "DBC_GLOB_PATTERNS in config.py."
            )
            return
        self._load_dbc_file(path)

    def _on_browse_dbc(self) -> None:
        from pathlib import Path
        from config import REPO_ROOT
        start = str(REPO_ROOT) if REPO_ROOT.exists() else ""
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select TS APP DBC file",
            start,
            "DBC files (*.dbc);;All files (*)",
        )
        if not path_str:
            return
        self._load_dbc_file(Path(path_str))

    def _on_browse_errq(self) -> None:
        from pathlib import Path
        start = str(errq_current_path()) if errq_current_path().exists() else ""
        path_str = QFileDialog.getExistingDirectory(
            self,
            "Select errq tool directory",
            start,
        )
        if not path_str:
            return
        set_errq_path(Path(path_str))
        # Reset aggregator state so the next frame triggers a fresh translation
        # via the new errq location.
        self.errq_aggregator.reset()
        self.errq_state.reset()
        self._set_status(f"errq path -> {path_str}")
        self._refresh_errq_status()

    def _show_errq_startup_warning(self) -> None:
        reason = errq_model_status() or "unknown reason"
        QMessageBox.warning(
            self,
            "errq decoder not loaded",
            f"The errq decoder could not be loaded:\n\n{reason}\n\n"
            "Decoded Errors will stay empty until this is fixed.\n\n"
            "Use 'Browse errq...' to point at the folder containing errq.py, "
            "or check the App Log tab (bottom dock) for the full trace.",
        )

    def _on_toggle_record(self, checked: bool) -> None:
        if checked:
            # Start recording — prompt for a path.
            from datetime import datetime as _dt
            default_name = f"ts_diag_{_dt.now().strftime('%Y%m%d_%H%M%S')}.asc"
            path, _ = QFileDialog.getSaveFileName(
                self,
                "Record CAN traffic to ASC",
                default_name,
                "Vector ASC log (*.asc);;All files (*)",
            )
            if not path:
                # User cancelled — pop the toggle back.
                self.act_record.blockSignals(True)
                self.act_record.setChecked(False)
                self.act_record.blockSignals(False)
                return
            try:
                self._recorder = AscRecorder(path)
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Recording failed", str(exc))
                self.act_record.blockSignals(True)
                self.act_record.setChecked(False)
                self.act_record.blockSignals(False)
                return
            self.act_record.setText("Stop recording")
            self._set_status(f"Recording to {path}")
        else:
            # Stop recording.
            if self._recorder is not None:
                count = self._recorder.count
                path = self._recorder.path
                self._recorder.close()
                self._recorder = None
                self.act_record.setText("Record...")
                self._set_status(f"Recording stopped: {count} frames -> {path}")
                QMessageBox.information(
                    self,
                    "Recording saved",
                    f"Wrote {count} frames to:\n{path}",
                )

    def _refresh_errq_status(self) -> None:
        """Re-check errq model load and reflect it in the toolbar label."""
        if errq_is_resolved():
            self.errq_label.setText(f"Errq: loaded ({errq_current_path().name})")
            self.errq_label.setStyleSheet("color: #1a7f37;")  # green
            self.errq_label.setToolTip(f"Loaded from {errq_current_path()}")
        else:
            reason = errq_model_status() or "unknown"
            self.errq_label.setText("Errq: NOT LOADED")
            self.errq_label.setStyleSheet("color: #c0392b; font-weight: bold;")  # red
            self.errq_label.setToolTip(reason)
            # Also surface the reason in the log dock so it's not buried.
            self.log_view.appendPlainText(f"[errq]  {reason}")

    def _load_dbc_file(self, path) -> None:
        try:
            self.decoder.load(path)
            self.dbc_label.setText(f"DBC: {path.name}")
            self._set_status(f"Loaded DBC {path}")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "DBC load failed", str(exc))

    # ---- Connection ----
    def _on_connect(self) -> None:
        if self.streamer is not None:
            return
        # Try once with current creds; if auth fails, show the dialog and
        # let the user retry. Up to 3 prompts before giving up.
        last_error: str | None = None
        for attempt in range(3):
            ok = self._try_connect(self.creds, last_error)
            if ok is True:
                self.act_connect.setEnabled(False)
                self.act_disconnect.setEnabled(True)
                return
            if ok is None:
                # User cancelled the dialog.
                return
            # ok is False — auth failure with a message in `ok_msg`.
            last_error = self._last_connect_error
        QMessageBox.critical(
            self,
            "SSH connection failed",
            f"Authentication still failing after 3 attempts:\n{last_error or 'unknown error'}",
        )

    def _try_connect(self, creds: ConnectionCreds, prior_error: str | None) -> bool | None:
        """
        Returns:
            True   on successful connect + stream start.
            False  on auth failure (caller should show dialog + retry).
            None   if the user cancelled the credentials dialog.
        """
        # Note: we deliberately do NOT pass on_frame — frames are drained
        # from the queue on the UI thread by the QTimer tick.
        streamer = CanStreamer(
            on_frame=None,
            on_status=lambda s: self.statusBar().showMessage(s),
            host=creds.host,
            user=creds.user,
            port=creds.port,
        )
        try:
            streamer.connect(
                key_filename=creds.key_filename,
                passphrase=creds.passphrase,
                password=creds.password,
            )
        except paramiko.AuthenticationException as exc:
            self._last_connect_error = str(exc) or "Authentication failed."
            log.warning("auth failed: %s", exc)
            dlg = ConnectionDialog(self, self.creds, error=self._last_connect_error)
            if dlg.exec() != dlg.DialogCode.Accepted:
                return None
            self.creds = dlg.result_creds()
            return False
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "SSH connection failed", str(exc))
            return None

        try:
            ifaces = streamer.discover_buses()
            streamer.start(ifaces)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Failed to start CAN streams", str(exc))
            try:
                streamer.stop()
            except Exception:  # noqa: BLE001
                pass
            return None

        self.streamer = streamer
        return True

    def _on_open_settings(self) -> None:
        dlg = ConnectionDialog(self, self.creds)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self.creds = dlg.result_creds()
            self._set_status(f"Settings updated for {self.creds.user}@{self.creds.host}")

    def _on_disconnect(self) -> None:
        if self.streamer is None:
            return
        self.streamer.stop()
        self.streamer = None
        self.act_connect.setEnabled(True)
        self.act_disconnect.setEnabled(False)

    # ---- UI tick ----
    def _drain_queue(self) -> None:
        if self.streamer is None:
            return
        # Drain raw lines first so the user sees activity even when frames
        # don't parse (helps debug `Cannot find device`, `permission denied`,
        # extra banner output from stdbuf, etc.).
        rq = self.streamer.raw_queue
        for _ in range(2000):
            try:
                item = rq.get_nowait()
            except Exception:
                break
            self._append_raw_line(item)
        # Then drain parsed frames for the state panel + error table.
        fq = self.streamer.frame_queue
        for _ in range(500):
            try:
                frame = fq.get_nowait()
            except Exception:
                break
            # If recording, dump the raw frame to ASC before any decoding so
            # we capture every byte verbatim.
            if self._recorder is not None:
                self._recorder.write(frame)
            self._handle_frame(frame)

    def _append_raw_line(self, item: dict) -> None:
        bus = item.get("bus", "?")
        text = item.get("text", "")
        stream = item.get("stream", "out")
        prefix = f"{bus:>5s}"
        if stream == "err":
            prefix += " [stderr]"
        self.log_view.appendPlainText(f"{prefix}  {text}")

    def _handle_frame(self, frame: dict) -> None:
        decoded = self.decoder.decode(
            ts=frame["ts"],
            bus=frame["bus"],
            can_id=frame["can_id"],
            ext=frame["ext"],
            data=frame["data"],
        )
        self._update_state_panel(decoded)
        # Only re-render the error table when the tracker actually changed —
        # otherwise we'd rebuild ~100 rows per frame at 100 Hz.
        changed = False
        if self._maybe_emit_errq(decoded):
            changed = True
        if self._maybe_update_estop(decoded):
            changed = True
        if changed:
            self._render_error_table()
            # Active count may have shifted — refresh the LED.
            self._recompute_led()

    def _maybe_emit_errq(self, decoded: DecodedFrame) -> bool:
        if not self._errq_signal_logged and decoded.signals:
            errq_signals = [n for n in decoded.signals if "ERRQ" in str(n).upper()]
            if errq_signals:
                self._errq_signal_logged = True
                self.log_view.appendPlainText(
                    f"[errq]  first ERRQ frame seen on {decoded.bus} {decoded.hex_id} "
                    f"({decoded.message_name or '?'}) with {len(errq_signals)} byte signals"
                )

        touched = self.errq_aggregator.ingest(decoded.signals)
        if not touched:
            return False
        any_change = False
        for ch in touched:
            buf = self.errq_aggregator.snapshot(ch)
            changes = self.errq_state.update_buffer(
                channel=ch,
                buffer=buf,
                ts=decoded.ts,
                bus=decoded.bus,
                can_id=decoded.can_id,
                hex_id=decoded.hex_id,
                decode_buffer_fn=decode_errq_buffer,
            )
            if changes:
                any_change = True
        return any_change

    def _maybe_update_estop(self, decoded: DecodedFrame) -> bool:
        sig = decoded.signals.get("TS_ESTOP_BUTTON_STATE") if decoded.signals else None
        if sig is None:
            return False
        sig_str = str(sig).upper()
        is_pressed = sig_str == "PRESSED" or (
            isinstance(sig, (int, float)) and not isinstance(sig, bool) and int(sig) == 1
        ) or (isinstance(sig, bool) and sig)
        change = self.errq_state.set_virtual(
            ESTOP_KEY,
            active=is_pressed,
            ts=decoded.ts,
            description="TS e-Stop Button pressed",
            severity="critical",
            bus=decoded.bus,
            can_id=decoded.can_id,
            hex_id=decoded.hex_id,
        )
        # set_virtual returns the entry only on status change.
        return change is not None and (
            change.status == "active" and change.last_active == decoded.ts
            or change.status == "passive" and change.cleared_at == decoded.ts
        )

    # -----------------------------------------------------------------
    # Rendering
    # -----------------------------------------------------------------
    def _render_error_table(self) -> None:
        """
        Rebuild the error table from the tracker. We keep this O(N) where
        N = active+passive rows currently tracked (typically <100), which
        is well within the UI tick budget.
        """
        entries = sorted(
            self.errq_state.values(),
            key=lambda e: (
                # Active first, then passive, both grouped by channel,
                # within channel by byte then bit.
                0 if e.status == "active" else 1,
                e.channel,
                e.byte,
                e.bit_index,
            ),
        )
        # Cap to MAX_ERROR_ROWS — keep the most recently active.
        if len(entries) > MAX_ERROR_ROWS:
            entries = entries[:MAX_ERROR_ROWS]

        self.error_table.setSortingEnabled(False)
        self.error_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            self._set_error_row(row, entry)
        self.error_table.setSortingEnabled(True)

    def _set_error_row(self, row: int, entry: ErrqEntry) -> None:
        bit_text = f"{entry.bit_index}  (0x{entry.bit_mask:02X})" if entry.bit_mask else "-"
        cleared_text = fmt_ts(entry.cleared_at) if entry.cleared_at else "—"
        items: list[QTableWidgetItem] = [
            QTableWidgetItem(fmt_ts(entry.first_seen)),
            QTableWidgetItem(entry.channel),
            QTableWidgetItem(entry.bus or ""),
            QTableWidgetItem(entry.hex_id or ""),
            _NumericItem(f"{entry.byte:02d}" if entry.byte else "-", float(entry.byte)),
            _NumericItem(bit_text, float(entry.bit_index)),
            QTableWidgetItem(entry.name),
            QTableWidgetItem(cleared_text),
            QTableWidgetItem(entry.status.upper()),
        ]
        if entry.status == "active":
            color = COLOR_ACTIVE
            italic = False
        else:
            color = COLOR_PASSIVE
            italic = True
        for it in items:
            it.setForeground(QBrush(color))
            if italic:
                f = it.font()
                f.setItalic(True)
                it.setFont(f)
        for col, it in enumerate(items):
            self.error_table.setItem(row, col, it)

    # -----------------------------------------------------------------
    # State panel
    # -----------------------------------------------------------------
    def _update_state_panel(self, decoded: DecodedFrame) -> None:
        if not decoded.signals:
            return
        ssman_changed = False
        for name, value in decoded.signals.items():
            sig_name = str(name)
            if not self._is_state_signal(sig_name):
                continue
            row = self.state_rows.get(sig_name)
            if row is None:
                row = self.state_table.rowCount()
                self.state_table.insertRow(row)
                self.state_rows[sig_name] = row
                self.state_table.setItem(row, 0, QTableWidgetItem(sig_name))
            value_text = self._fmt_value(value)
            value_item = QTableWidgetItem(value_text)
            indicator_color = self._indicator_for(sig_name, value_text)
            if indicator_color == "red":
                value_item.setBackground(QBrush(COLOR_INDICATOR_RED))
                value_item.setForeground(QBrush(QColor("white")))
            elif indicator_color == "orange":
                value_item.setBackground(QBrush(COLOR_INDICATOR_ORANGE))
                value_item.setForeground(QBrush(QColor("black")))
            self.state_table.setItem(row, 1, value_item)

            # Cache SSMAN state for the LED computation.
            ssman_role = self._ssman_role_for(sig_name)
            if ssman_role:
                self._ssman[ssman_role] = value_text.upper()
                ssman_changed = True
        if ssman_changed:
            self._recompute_led()

    @staticmethod
    def _ssman_role_for(name: str) -> str | None:
        n = name.lower()
        if "ve_cha_ssman_state" in n:
            return "VE_A"
        if "ve_chb_ssman_state" in n:
            return "VE_B"
        if "ts_cha_ssman_state" in n:
            return "TS_A"
        if "ts_chb_ssman_state" in n:
            return "TS_B"
        return None

    def _recompute_led(self) -> None:
        """
        LED rules:
          red    — any SSMAN reports a hard/unrecoverable fault state and at
                   least one ERRQ entry is currently active
          yellow — any SSMAN reports a soft/recoverable fault state and at
                   least one ERRQ entry is currently active
          green  — none of the above (or no SSMAN data yet but no active
                   errors either)
        """
        hard_fault_states = {"DISENGAGED_HARD_FAULT", "FAULT"}
        soft_fault_states = {"DISENGAGED_FAULT", "RECOVERABLE_MRM_B1"}

        hard = any(s in hard_fault_states for s in self._ssman.values())
        soft = any(s in soft_fault_states for s in self._ssman.values())
        active_count = sum(1 for e in self.errq_state.values() if e.status == "active")

        if hard and active_count > 0:
            self.state_led.set_state("red")
        elif soft and active_count > 0:
            self.state_led.set_state("yellow")
        else:
            self.state_led.set_state("green")

    def _is_state_signal(self, name: str) -> bool:
        lname = name.lower()
        return any(p in lname for p in self._state_signal_patterns)

    @staticmethod
    def _indicator_for(name: str, value_text: str) -> str | None:
        for pattern, mapping in TS_STATE_INDICATORS.items():
            if pattern.lower() in name.lower():
                # match on the value text (which is the enum name when
                # the DBC has a VAL_ table for this signal)
                color = mapping.get(value_text.upper()) or mapping.get(value_text)
                if color:
                    return color
        return None

    @staticmethod
    def _fmt_value(value: object) -> str:
        if isinstance(value, float):
            return f"{value:.3f}"
        return str(value)

    # ---- misc ----
    def _set_status(self, msg: str) -> None:
        self.statusBar().showMessage(msg)
        log.info(msg)

    def _clear_views(self) -> None:
        self.error_table.setRowCount(0)
        self.state_table.setRowCount(0)
        self.state_rows.clear()
        self.errq_aggregator.reset()
        self.errq_state.reset()
        self._ssman.clear()
        self.state_led.set_state("gray")
        self._errq_signal_logged = False
        self._errq_nonzero_logged = False
        self._errq_decode_failure_logged = False
        self.log_view.clear()

    def closeEvent(self, ev) -> None:  # noqa: N802 (Qt signature)
        try:
            self._on_disconnect()
        except Exception:  # noqa: BLE001
            pass
        if self._recorder is not None:
            try:
                self._recorder.close()
            except Exception:  # noqa: BLE001
                pass
            self._recorder = None
        super().closeEvent(ev)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = DiagnosticWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
