"""
Vay OBD Live — POC entrypoint.

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
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
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
from app_settings import AppSettings, load as load_settings, save as save_settings
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
from signal_picker import SignalPickerDialog
from ssh_can_reader import CanStreamer
from state_view import (
    StateView, SubGroup, TopGroup,
    load as load_state_view,
    save as save_state_view,
)
from telestations import Telestation, load as load_telestations
from telestations import open_overrides_in_editor as open_ts_overrides
from vehicles import Vehicle, load as load_vehicles
from vehicles import open_overrides_in_editor as open_ve_overrides
from version_sync import (
    FwVersion, checkout as vs_checkout, current_head, find_match,
    working_tree_clean,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("vay_obd_live")


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
        self.setWindowTitle("Vay OBD Live — POC")
        self.resize(1280, 800)

        self.decoder = DbcDecoder()
        self.streamer: CanStreamer | None = None
        self.recent_log: deque[str] = deque(maxlen=MAX_LOG_ROWS)
        self.errq_aggregator = ErrqAggregator()
        self.errq_state = ErrqStateTracker()
        # State panel signal patterns — case-insensitive for matching.
        self._state_signal_patterns = tuple(s.lower() for s in TS_STATE_SIGNALS)
        # Latest SSMAN values per role ("VE_A","VE_B","TS_A","TS_B") used
        # to compute the status LED. Stored as the enum string.
        self._ssman: dict[str, str] = {}
        # Latest TS / VE FW version values seen on the bus — used by the
        # Sync DBC feature to pick a matching git ref.
        self._fw_versions: dict[str, int] = {}
        # Diagnostic flags so we log "first ERRQ frame seen" exactly once.
        self._errq_signal_logged = False
        self._errq_nonzero_logged = False
        self._errq_decode_failure_logged = False
        # Recording state.
        self._recorder: AscRecorder | None = None
        # Background git-pull thread (kept on self so it isn't GC'd mid-run).
        self._git_thread = None
        self._git_worker = None

        # Persistent settings (key file path, last TS/VE, etc).
        self._settings: AppSettings = load_settings()

        # Persisted, user-configurable state-panel layout.
        self._state_view: StateView = load_state_view()

        # Vehicle directory — loaded from ree-vehicle-configs/org/vay/vehicles.
        self._vehicles, _ = load_vehicles()

        # Telestation directory — loaded from ree-vehicle-configs YAMLs.
        self._telestations, self._telestations_path = load_telestations()

        # Active target: "TS", "VE", or "" (none). TS and VE selections are
        # mutually exclusive — picking one deselects the other so the
        # connection always has exactly one target.
        self._active_target: str = ""

        # Pick a seed: prefer last-used VE if that's what was last selected,
        # otherwise last-used TS, otherwise the first TS with a host.
        seed_ts = None
        seed_ve = None
        if self._settings.last_ve_id:
            seed_ve = next(
                (v for v in self._vehicles if v.id == self._settings.last_ve_id and v.host),
                None,
            )
        if seed_ve is not None:
            self._active_target = "VE"
        else:
            if self._settings.last_ts_id:
                seed_ts = next(
                    (t for t in self._telestations if t.id == self._settings.last_ts_id and t.host),
                    None,
                )
            if seed_ts is None:
                seed_ts = next((t for t in self._telestations if t.host), None)
            if seed_ts is not None:
                self._active_target = "TS"

        seed = seed_ve or seed_ts
        self.creds = ConnectionCreds(
            host=(seed.host if seed else REMOTE_HOST),
            user=(self._settings.ssh_user or (seed.user if seed else REMOTE_USER)),
            port=(seed.port if seed else REMOTE_PORT),
            key_filename=(self._settings.ssh_key_filename or None),
            passphrase=None,
            password=None,
            remember=self._settings.remember_ssh,
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
            # Track per-repo statuses so the toolbar label shows both.
            self._repo_statuses: dict[str, str] = {}
            self._git_thread, self._git_worker = start_git_pull(
                self,
                on_repo_done=self._on_git_pull_repo_done,
                on_all_done=self._on_git_pull_all_done,
            )
        else:
            self.repo_label.setText("Repo: pull disabled")
            self._post_repo_init()

    def _on_pull_now(self) -> None:
        """Manually re-trigger the repo update (same worker as startup)."""
        if getattr(self, "_git_thread", None) is not None and self._git_thread.isRunning():
            self._set_status("Pull already in progress — please wait.")
            return
        self.btn_pull_now.setEnabled(False)
        self.repo_label.setText("Repo: pulling...")
        self.repo_label.setStyleSheet("color: #888;")
        self._repo_statuses = {}
        self._git_thread, self._git_worker = start_git_pull(
            self,
            on_repo_done=self._on_git_pull_repo_done,
            on_all_done=self._on_pull_now_all_done,
        )

    def _on_pull_now_all_done(self, short: str, full_output: str, last_label: str) -> None:
        """Variant that re-enables the button after a manual pull."""
        self.btn_pull_now.setEnabled(True)
        # _on_git_pull_all_done already reloads the dropdowns + DBC + errq via _post_repo_init.
        self._on_git_pull_all_done(short, full_output, last_label)

    def _on_git_pull_repo_done(self, label: str, short: str, full_output: str) -> None:
        log.info("repo pull [%s]: %s", label, short)
        if full_output:
            for line in full_output.splitlines():
                if line.strip():
                    log.info("repo[%s]: %s", label, line)
        self._repo_statuses[label] = short
        # Live-update the toolbar label as each repo finishes.
        summary = " | ".join(f"{k}: {v}" for k, v in self._repo_statuses.items())
        self.repo_label.setText(f"Repo: {summary}")

    def _on_git_pull_all_done(self, short: str, full_output: str, last_label: str) -> None:
        # Color the label based on the worst status across repos.
        statuses = list(self._repo_statuses.values()) or [short]
        any_failed = any("fail" in s.lower() or "missing" in s.lower() or "timed out" in s.lower()
                         for s in statuses)
        if any_failed:
            self.repo_label.setStyleSheet("color: #c0392b;")
        else:
            self.repo_label.setStyleSheet("color: #1a7f37;")
        self._post_repo_init()

    def _post_repo_init(self) -> None:
        """Run startup steps that depend on the repo being current."""
        # Reload TS + VE lists now that ree-vehicle-configs is current.
        self._telestations, self._telestations_path = load_telestations()
        self._populate_ts_combo()
        self._vehicles, _ = load_vehicles()
        self._populate_ve_combo()
        log.info(
            "config: dropdowns reloaded — %d telestations, %d vehicles",
            len(self._telestations), len(self._vehicles),
        )

        self._auto_load_dbc()
        self._refresh_errq_status()
        if not errq_is_resolved() and not getattr(self, "_errq_warning_shown", False):
            self._errq_warning_shown = True
            QTimer.singleShot(200, self._show_errq_startup_warning)

        # UI refresh tick — drains the queue and updates widgets. Only set
        # up once; if _post_repo_init is called again (manual pull), keep
        # the same timer.
        if not hasattr(self, "_timer"):
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

        # ---- left: System State panel ----
        left = QWidget()
        lv = QVBoxLayout(left)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title = QLabel("System State")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        title_row.addWidget(title)
        self.state_led = StatusLED()
        title_row.addWidget(self.state_led)
        title_row.addStretch(1)
        # Hint that the tree is configurable.
        config_hint = QLabel("(right-click to edit)")
        config_hint.setStyleSheet("color: #888; font-size: 9pt;")
        title_row.addWidget(config_hint)
        lv.addLayout(title_row)

        self.state_tree = QTreeWidget()
        self.state_tree.setColumnCount(2)
        self.state_tree.setHeaderLabels(["Signal", "Value"])
        self.state_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.state_tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.state_tree.setColumnWidth(0, 260)
        self.state_tree.setUniformRowHeights(True)
        self.state_tree.setExpandsOnDoubleClick(False)
        # Allow Ctrl/Shift multi-select on signals so bulk delete works.
        self.state_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.state_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.state_tree.customContextMenuRequested.connect(self._on_state_tree_menu)
        lv.addWidget(self.state_tree)
        splitter.addWidget(left)

        # signal-name -> (group_index, child_item) for fast value updates
        self._state_items: dict[str, QTreeWidgetItem] = {}
        self._build_state_tree()

        # ---- right: errors table ----
        right = QWidget()
        rv = QVBoxLayout(right)

        # Header row: title + "Clear passive" button on the right.
        err_title_row = QHBoxLayout()
        err_title_row.setSpacing(8)
        title2 = QLabel("Decoded Errors")
        title2.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        err_title_row.addWidget(title2)
        err_title_row.addStretch(1)
        self.btn_clear_passive = QPushButton("Clear passive")
        self.btn_clear_passive.setToolTip(
            "Remove cleared (passive) errors from the table. Active errors stay."
        )
        self.btn_clear_passive.clicked.connect(self._clear_passive_errors)
        err_title_row.addWidget(self.btn_clear_passive)
        rv.addLayout(err_title_row)

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

        # ---- TS + VE selectors stacked ----
        selector_widget = QWidget()
        selector_v = QVBoxLayout(selector_widget)
        selector_v.setContentsMargins(0, 0, 0, 0)
        selector_v.setSpacing(2)

        ts_row = QHBoxLayout()
        ts_row.setContentsMargins(0, 0, 0, 0)
        ts_row.addWidget(QLabel("TS:"))
        self.ts_combo = QComboBox()
        self.ts_combo.setMinimumWidth(260)
        self._populate_ts_combo()
        self.ts_combo.currentIndexChanged.connect(self._on_ts_changed)
        ts_row.addWidget(self.ts_combo)
        edit_ts_btn = QPushButton("Edit overrides...")
        edit_ts_btn.clicked.connect(self._on_edit_telestations)
        ts_row.addWidget(edit_ts_btn)
        selector_v.addLayout(ts_row)

        ve_row = QHBoxLayout()
        ve_row.setContentsMargins(0, 0, 0, 0)
        ve_row.addWidget(QLabel("VE:"))
        self.ve_combo = QComboBox()
        self.ve_combo.setMinimumWidth(260)
        self._populate_ve_combo()
        self.ve_combo.currentIndexChanged.connect(self._on_ve_changed)
        ve_row.addWidget(self.ve_combo)
        edit_ve_btn = QPushButton("Edit overrides...")
        edit_ve_btn.clicked.connect(self._on_edit_vehicles)
        ve_row.addWidget(edit_ve_btn)
        selector_v.addLayout(ve_row)

        tb.addWidget(selector_widget)
        tb.addSeparator()

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

        self.act_sync_dbc = QAction("Sync DBC", self)
        self.act_sync_dbc.setEnabled(False)
        self.act_sync_dbc.setToolTip(
            "Check out the ree-reecu_main version that matches the connected "
            "TS/VE firmware (FW_VER_MAJOR.MINOR.PATCH), then reload DBC + errq."
        )
        self.act_sync_dbc.triggered.connect(self._on_sync_dbc)
        tb.addAction(self.act_sync_dbc)

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
        self.btn_pull_now = QPushButton("Pull now")
        self.btn_pull_now.setToolTip("Re-run `git fetch --prune` on both repos.")
        self.btn_pull_now.clicked.connect(self._on_pull_now)
        tb.addWidget(self.btn_pull_now)

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
        log.info("user: clicked Browse DBC")
        start = str(REPO_ROOT) if REPO_ROOT.exists() else ""
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select TS APP DBC file",
            start,
            "DBC files (*.dbc);;All files (*)",
        )
        if not path_str:
            log.info("user: cancelled DBC selection")
            return
        log.info("user: chose DBC %s", path_str)
        self._load_dbc_file(Path(path_str))

    def _on_browse_errq(self) -> None:
        from pathlib import Path
        log.info("user: clicked Browse errq")
        start = str(errq_current_path()) if errq_current_path().exists() else ""
        path_str = QFileDialog.getExistingDirectory(
            self,
            "Select errq tool directory",
            start,
        )
        if not path_str:
            log.info("user: cancelled errq selection")
            return
        log.info("user: chose errq dir %s", path_str)
        set_errq_path(Path(path_str))
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
        log.info("user: %s recording toggle", "enabled" if checked else "disabled")
        if checked:
            # Start recording — prompt for a path.
            from datetime import datetime as _dt
            default_name = f"vay_obd_live_{_dt.now().strftime('%Y%m%d_%H%M%S')}.asc"
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
        log.info(
            "user: clicked Connect (target=%s, host=%s, user=%s)",
            self._active_target or "none", self.creds.host, self.creds.user,
        )
        if self.streamer is not None:
            return
        # Wipe any stale data (errors, state values, log) before the new
        # session starts. Active errors from a previous TS / VE shouldn't
        # bleed into the new one.
        self._clear_views()
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
        # Auth + stream-start succeeded — persist creds so next launch
        # comes up ready without prompting again.
        self._persist_ssh()
        self.act_sync_dbc.setEnabled(True)
        return True

    def _populate_ts_combo(self) -> None:
        # The combo always carries a sentinel "(none)" entry at index 0 so
        # the user can deselect TS (e.g. when picking a VE instead).
        self.ts_combo.blockSignals(True)
        self.ts_combo.clear()
        self.ts_combo.addItem("(none)", None)
        seed_index = 0
        last_id = self._settings.last_ts_id
        for i, ts in enumerate(self._telestations):
            label = ts.display() + (f"  —  {ts.host}" if ts.host else "  —  (no host)")
            self.ts_combo.addItem(label, ts)
            # Only seed-select TS if it was the last active target.
            if (
                self._active_target == "TS"
                and last_id and ts.id == last_id and seed_index == 0
            ):
                seed_index = i + 1
        self.ts_combo.setCurrentIndex(seed_index)
        self.ts_combo.blockSignals(False)

    def _on_ts_changed(self, idx: int) -> None:
        ts = self.ts_combo.itemData(idx)
        if ts is None:
            # User picked "(none)". If this was the active target, drop it.
            if self._active_target == "TS":
                self._active_target = ""
                self._settings.last_ts_id = ""
                save_settings(self._settings)
                self._set_status("TS deselected")
            return
        if not ts.host:
            QMessageBox.warning(
                self, "Telestation has no host",
                f"'{ts.name}' has no host configured. Edit the list to add an IP/hostname.",
            )
            return

        # Mutual exclusion: clear the VE selection.
        self._set_combo_to_none(self.ve_combo)

        self._active_target = "TS"
        self.creds = ConnectionCreds(
            host=ts.host, user=ts.user, port=ts.port,
            key_filename=self.creds.key_filename,
            passphrase=self.creds.passphrase,
            password=self.creds.password,
            remember=self.creds.remember,
        )
        self._clear_views()
        self._auto_collapse_inactive_target()
        self._settings.last_ts_id = ts.id
        self._settings.last_ve_id = ""
        save_settings(self._settings)
        self._set_status(f"Selected {ts.name} -> {ts.user}@{ts.host}:{ts.port}")

    @staticmethod
    def _set_combo_to_none(combo: QComboBox) -> None:
        """Programmatically set a combo to its '(none)' entry without firing signals."""
        combo.blockSignals(True)
        combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _populate_ve_combo(self) -> None:
        self.ve_combo.blockSignals(True)
        self.ve_combo.clear()
        self.ve_combo.addItem("(none)", None)
        seed_index = 0
        last_id = self._settings.last_ve_id if self._settings else ""
        for i, v in enumerate(self._vehicles):
            host_part = v.host if v.host else "(no host)"
            label = v.display() + f"  —  {host_part}"
            self.ve_combo.addItem(label, v)
            # Only seed-select VE if it was the last active target.
            if (
                self._active_target == "VE"
                and last_id and v.id == last_id and seed_index == 0
            ):
                seed_index = i + 1
        self.ve_combo.setCurrentIndex(seed_index)
        self.ve_combo.blockSignals(False)

    def _on_ve_changed(self, idx: int) -> None:
        v = self.ve_combo.itemData(idx)
        if v is None:
            if self._active_target == "VE":
                self._active_target = ""
                self._settings.last_ve_id = ""
                save_settings(self._settings)
                self._set_status("VE deselected")
            return
        if not v.host:
            QMessageBox.warning(
                self, "Vehicle has no host",
                f"'{v.name}' has no host. Add one in vehicles_overrides.json "
                f"(Edit overrides... button) and reselect.",
            )
            # Bounce back to (none) to keep state consistent.
            self._set_combo_to_none(self.ve_combo)
            return

        # Mutual exclusion: clear the TS selection.
        self._set_combo_to_none(self.ts_combo)

        self._active_target = "VE"
        self.creds = ConnectionCreds(
            host=v.host, user=v.user, port=v.port,
            key_filename=self.creds.key_filename,
            passphrase=self.creds.passphrase,
            password=self.creds.password,
            remember=self.creds.remember,
        )
        self._clear_views()
        self._auto_collapse_inactive_target()
        self._settings.last_ve_id = v.id
        self._settings.last_ts_id = ""
        save_settings(self._settings)
        self._set_status(f"Selected VE {v.name} -> {v.user}@{v.host}:{v.port}")

    def _on_edit_vehicles(self) -> None:
        path = open_ve_overrides()
        QMessageBox.information(
            self, "Vehicle overrides",
            f"Opened:\n{path}\n\n"
            "Format: a JSON object keyed by vehicle id. Each value can "
            "override host / user / port / location / name.\n\n"
            "After saving, restart the app (or pick the vehicle again) to apply.",
        )

    def _on_edit_telestations(self) -> None:
        # The TS list is generated from ree-vehicle-configs YAMLs. Per-station
        # overrides (host, user, port) live in a separate JSON file the user
        # can edit without rebuilding.
        path = open_ts_overrides()
        QMessageBox.information(
            self, "Telestation overrides",
            f"Opened:\n{path}\n\n"
            "Format: a JSON object keyed by telestation id. Each value can "
            "override host / user / port / location / name.\n\n"
            "After saving, restart the app or click 'Reload DBC' to pick up changes.",
        )

    def _on_open_settings(self) -> None:
        dlg = ConnectionDialog(self, self.creds)
        if dlg.exec() == dlg.DialogCode.Accepted:
            self.creds = dlg.result_creds()
            self._persist_ssh()
            self._set_status(f"Settings updated for {self.creds.user}@{self.creds.host}")

    def _persist_ssh(self) -> None:
        """Save key file + user to settings.json if 'remember' is checked."""
        self._settings.remember_ssh = bool(self.creds.remember)
        if self.creds.remember:
            self._settings.ssh_key_filename = self.creds.key_filename or ""
            self._settings.ssh_user = self.creds.user or ""
        else:
            # User explicitly opted out — clear stored credentials.
            self._settings.ssh_key_filename = ""
            self._settings.ssh_user = ""
        save_settings(self._settings)

    def _on_disconnect(self) -> None:
        if self.streamer is None:
            return
        self.streamer.stop()
        self.streamer = None
        self.act_connect.setEnabled(True)
        self.act_disconnect.setEnabled(False)
        self.act_sync_dbc.setEnabled(False)
        log.info("disconnected from %s@%s", self.creds.user, self.creds.host)

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
        self._snoop_fw_version(decoded)
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

    _FW_SIGS = (
        "TS_SPCB_FW_VER_MAJOR", "TS_SPCB_FW_VER_MINOR", "TS_SPCB_FW_VER_PATCH",
        "VE_SPCB_FW_VER_MAJOR", "VE_SPCB_FW_VER_MINOR", "VE_SPCB_FW_VER_PATCH",
    )

    def _snoop_fw_version(self, decoded: DecodedFrame) -> None:
        """Cache TS/VE_SPCB_FW_VER_* whenever the relevant frames arrive."""
        if not decoded.signals:
            return
        for sig_name in self._FW_SIGS:
            if sig_name in decoded.signals:
                try:
                    val = int(decoded.signals[sig_name])
                except (TypeError, ValueError):
                    continue
                if self._fw_versions.get(sig_name) != val:
                    log.info("fw-version: %s = %d", sig_name, val)
                self._fw_versions[sig_name] = val

    def _current_fw_version(self) -> FwVersion | None:
        """Return the FW version for the active target (TS or VE)."""
        if self._active_target == "TS":
            prefix = "TS"
        elif self._active_target == "VE":
            prefix = "VE"
        else:
            return None
        try:
            return FwVersion(
                major=self._fw_versions[f"{prefix}_SPCB_FW_VER_MAJOR"],
                minor=self._fw_versions[f"{prefix}_SPCB_FW_VER_MINOR"],
                patch=self._fw_versions[f"{prefix}_SPCB_FW_VER_PATCH"],
            )
        except KeyError:
            return None

    def _on_sync_dbc(self) -> None:
        """Match the active target's FW version to a git ref, then check it out."""
        log.info("sync-dbc: button pressed (target=%s)", self._active_target or "none")
        if not self._active_target:
            QMessageBox.information(
                self, "Sync DBC",
                "Connect to a TS or VE first — Sync DBC needs to know which "
                "firmware version to match.",
            )
            return
        ver = self._current_fw_version()
        if ver is None:
            QMessageBox.warning(
                self, "Sync DBC",
                "Firmware version not received yet — wait for a few seconds of "
                "telemetry from the connected target, then try again.\n\n"
                f"Need: {self._active_target}_SPCB_FW_VER_MAJOR/MINOR/PATCH",
            )
            return

        log.info("sync-dbc: %s firmware version is %s", self._active_target, ver.short())

        if not working_tree_clean(REPO_ROOT):
            QMessageBox.warning(
                self, "Working tree not clean",
                f"{REPO_ROOT}\n\nhas uncommitted changes — refusing to checkout. "
                "Commit / stash first, then click Sync DBC again.",
            )
            return

        match = find_match(REPO_ROOT, ver)
        head_name, head_short = current_head(REPO_ROOT)

        if match is None:
            QMessageBox.warning(
                self, "Sync DBC — no match",
                f"FW version {ver.short()} did not match any tag, branch, or "
                f"commit prefix in:\n{REPO_ROOT}\n\n"
                "Tried:\n"
                f"  • tag {ver.release_tag}\n"
                f"  • tag v{ver.major}.{ver.minor}.{ver.patch}\n"
                f"  • branch release/{ver.major}.{ver.minor}.{ver.patch}\n"
                f"  • commit {ver.patch_hex4} (custom branch hash)\n\n"
                "If the version is on a remote-only ref, use 'Pull now' first.",
            )
            return

        if QMessageBox.question(
            self, "Sync DBC",
            f"Connected firmware: {ver.short()}\n"
            f"Matched ref: {match.ref}  ({match.kind}, {match.commit[:10]})\n\n"
            f"Currently on: {head_name}  ({head_short})\n\n"
            f"Check out {match.ref}, then reload DBC + errq?",
        ) != QMessageBox.StandardButton.Yes:
            log.info("sync-dbc: cancelled by user")
            return

        log.info("sync-dbc: checking out %s (%s)", match.ref, match.commit[:10])
        ok, output = vs_checkout(REPO_ROOT, match.ref)
        for line in output.splitlines():
            if line.strip():
                log.info("sync-dbc: %s", line)
        if not ok:
            QMessageBox.critical(
                self, "Checkout failed",
                f"git checkout {match.ref} failed:\n\n{output}",
            )
            return

        # Reload DBC + errq from the new on-disk files.
        self._auto_load_dbc()
        # Force the errq bridge to re-import errq.py (it may have changed
        # between versions).
        set_errq_path(errq_current_path())
        self._refresh_errq_status()
        # Wipe stale rows so the user only sees data interpreted under the
        # newly-loaded DBC + errq.
        self._clear_views()
        self._set_status(
            f"Synced ree-reecu_main to {match.ref} ({match.commit[:10]}); "
            f"DBC + errq reloaded."
        )

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
            child_item = self._lookup_state_item(sig_name)
            if child_item is None:
                continue
            value_text = self._fmt_value(value)
            child_item.setText(0, sig_name)
            child_item.setText(1, value_text)
            indicator_color = self._indicator_for(sig_name, value_text)
            if indicator_color == "red":
                child_item.setBackground(1, QBrush(COLOR_INDICATOR_RED))
                child_item.setForeground(1, QBrush(QColor("white")))
            elif indicator_color == "orange":
                child_item.setBackground(1, QBrush(COLOR_INDICATOR_ORANGE))
                child_item.setForeground(1, QBrush(QColor("black")))
            else:
                child_item.setData(1, Qt.ItemDataRole.BackgroundRole, None)
                child_item.setData(1, Qt.ItemDataRole.ForegroundRole, None)

            ssman_role = self._ssman_role_for(sig_name)
            if ssman_role:
                self._ssman[ssman_role] = value_text.upper()
                ssman_changed = True
        if ssman_changed:
            self._recompute_led()

    # -----------------------------------------------------------------
    # State tree (3-level configurable view: top → sub → signal)
    # -----------------------------------------------------------------
    def _build_state_tree(self) -> None:
        """Rebuild the QTreeWidget from self._state_view."""
        self.state_tree.clear()
        self._state_items.clear()
        for t_idx, top in enumerate(self._state_view.groups):
            top_item = QTreeWidgetItem([top.name, ""])
            f = top_item.font(0)
            f.setBold(True)
            f.setPointSizeF(f.pointSizeF() + 0.5)
            top_item.setFont(0, f)
            top_item.setForeground(0, QBrush(QColor("#000")))
            top_item.setData(0, Qt.ItemDataRole.UserRole, ("top", t_idx))
            self.state_tree.addTopLevelItem(top_item)

            for s_idx, sub in enumerate(top.subgroups):
                sub_item = QTreeWidgetItem([sub.name, ""])
                sf = sub_item.font(0)
                sf.setBold(True)
                sub_item.setFont(0, sf)
                sub_item.setForeground(0, QBrush(QColor("#444")))
                sub_item.setData(0, Qt.ItemDataRole.UserRole, ("sub", t_idx, s_idx))
                top_item.addChild(sub_item)

                for sig_idx, sig_pat in enumerate(sub.signals):
                    leaf = QTreeWidgetItem([sig_pat, "—"])
                    leaf.setData(0, Qt.ItemDataRole.UserRole, ("signal", t_idx, s_idx, sig_idx))
                    sub_item.addChild(leaf)
                sub_item.setExpanded(sub.expanded)
            top_item.setExpanded(top.expanded)

        # Auto-collapse the inactive target so the relevant half is on top.
        self._auto_collapse_inactive_target()

    def _auto_collapse_inactive_target(self) -> None:
        """If TS is the active target, collapse the VE top group, and vice-versa."""
        if not self._active_target:
            return
        for t_idx in range(self.state_tree.topLevelItemCount()):
            top_item = self.state_tree.topLevelItem(t_idx)
            name = top_item.text(0).upper()
            if name in {"TS", "VE"}:
                top_item.setExpanded(name == self._active_target)

    def _lookup_state_item(self, signal_name: str) -> QTreeWidgetItem | None:
        """Find the tree leaf whose pattern is a substring of signal_name."""
        if signal_name in self._state_items:
            return self._state_items[signal_name]
        lname = signal_name.lower()
        for t_idx in range(self.state_tree.topLevelItemCount()):
            top_item = self.state_tree.topLevelItem(t_idx)
            for s_idx in range(top_item.childCount()):
                sub_item = top_item.child(s_idx)
                for c_idx in range(sub_item.childCount()):
                    leaf = sub_item.child(c_idx)
                    pat = leaf.text(0).lower()
                    if pat and pat in lname:
                        self._state_items[signal_name] = leaf
                        return leaf
        return None

    def _on_state_tree_menu(self, pos) -> None:
        item = self.state_tree.itemAt(pos)
        menu = QMenu(self)
        if item is None:
            menu.addAction("New top group...").triggered.connect(self._sv_new_top_group)
        else:
            tag = item.data(0, Qt.ItemDataRole.UserRole) or ("none",)
            kind = tag[0]
            if kind == "top":
                t_idx = tag[1]
                menu.addAction("Rename top group...").triggered.connect(
                    lambda: self._sv_rename_top(t_idx)
                )
                menu.addAction("Delete top group").triggered.connect(
                    lambda: self._sv_delete_top(t_idx)
                )
                menu.addSeparator()
                menu.addAction("Add subgroup...").triggered.connect(
                    lambda: self._sv_new_subgroup(t_idx)
                )
                menu.addSeparator()
                menu.addAction("New top group...").triggered.connect(self._sv_new_top_group)
            elif kind == "sub":
                _, t_idx, s_idx = tag
                menu.addAction("Rename subgroup...").triggered.connect(
                    lambda: self._sv_rename_sub(t_idx, s_idx)
                )
                menu.addAction("Delete subgroup").triggered.connect(
                    lambda: self._sv_delete_sub(t_idx, s_idx)
                )
                menu.addSeparator()
                menu.addAction("Add signal...").triggered.connect(
                    lambda: self._sv_add_signal(t_idx, s_idx)
                )
                # Move subgroup to another top group
                if len(self._state_view.groups) > 1:
                    move_menu = menu.addMenu("Move subgroup to top group")
                    for other_t in range(len(self._state_view.groups)):
                        if other_t == t_idx:
                            continue
                        other_name = self._state_view.groups[other_t].name
                        act = move_menu.addAction(other_name)
                        act.triggered.connect(
                            lambda _checked=False, src=t_idx, sub=s_idx, dst=other_t:
                            self._sv_move_subgroup(src, sub, dst)
                        )
            elif kind == "signal":
                _, t_idx, s_idx, sig_idx = tag
                # Collect every signal the user currently has highlighted
                # (the right-clicked one + any Ctrl/Shift selections).
                selected_keys = self._selected_signal_keys()
                # Always include the row that was right-clicked, even if it
                # wasn't part of the highlighted set.
                selected_keys.add((t_idx, s_idx, sig_idx))
                n_selected = len(selected_keys)

                menu.addAction("Change signal...").triggered.connect(
                    lambda: self._sv_change_signal(t_idx, s_idx, sig_idx)
                )

                if n_selected > 1:
                    act = menu.addAction(f"Remove {n_selected} selected signals")
                    act.triggered.connect(
                        lambda _c=False, keys=frozenset(selected_keys):
                        self._sv_remove_signals_bulk(keys)
                    )
                else:
                    menu.addAction("Remove signal").triggered.connect(
                        lambda: self._sv_remove_signal(t_idx, s_idx, sig_idx)
                    )

                # Move signal to another subgroup (single-only — bulk move
                # is rarely useful since you usually want to move to one
                # target subgroup; revisit if needed).
                move_menu = menu.addMenu("Move signal to subgroup")
                for ot in range(len(self._state_view.groups)):
                    top = self._state_view.groups[ot]
                    for os_idx in range(len(top.subgroups)):
                        if ot == t_idx and os_idx == s_idx:
                            continue
                        label = f"{top.name} / {top.subgroups[os_idx].name}"
                        act = move_menu.addAction(label)
                        act.triggered.connect(
                            lambda _c=False, st=t_idx, ss=s_idx, si=sig_idx, dt=ot, ds=os_idx:
                            self._sv_move_signal(st, ss, si, dt, ds)
                        )
        menu.exec(self.state_tree.viewport().mapToGlobal(pos))

    # ---- state-view mutation helpers ----
    def _sv_new_top_group(self) -> None:
        text, ok = QInputDialog.getText(self, "New top group", "Top group name:")
        if not ok or not text.strip():
            return
        name = text.strip()
        log.info("state_view: new top group %r", name)
        self._state_view.groups.append(TopGroup(name=name, subgroups=[]))
        self._save_and_rebuild_state()

    def _sv_rename_top(self, t_idx: int) -> None:
        if t_idx >= len(self._state_view.groups):
            return
        current = self._state_view.groups[t_idx].name
        text, ok = QInputDialog.getText(self, "Rename top group", "New name:", text=current)
        if not ok or not text.strip():
            return
        old = self._state_view.groups[t_idx].name
        new = text.strip()
        log.info("state_view: rename top group %r -> %r", old, new)
        self._state_view.groups[t_idx].name = new
        self._save_and_rebuild_state()

    def _sv_delete_top(self, t_idx: int) -> None:
        if t_idx >= len(self._state_view.groups):
            return
        top = self._state_view.groups[t_idx]
        sig_count = sum(len(s.signals) for s in top.subgroups)
        if QMessageBox.question(
            self, "Delete top group",
            f"Remove '{top.name}' and its {len(top.subgroups)} subgroups ({sig_count} signals)?",
        ) != QMessageBox.StandardButton.Yes:
            return
        log.info("state_view: delete top group %r (%d subgroups, %d signals)",
                 top.name, len(top.subgroups), sig_count)
        del self._state_view.groups[t_idx]
        self._save_and_rebuild_state()

    def _sv_new_subgroup(self, t_idx: int) -> None:
        if t_idx >= len(self._state_view.groups):
            return
        text, ok = QInputDialog.getText(self, "New subgroup", "Subgroup name:")
        if not ok or not text.strip():
            return
        name = text.strip()
        log.info("state_view: new subgroup %r under top %r",
                 name, self._state_view.groups[t_idx].name)
        self._state_view.groups[t_idx].subgroups.append(SubGroup(name=name, signals=[]))
        self._save_and_rebuild_state()

    def _sv_rename_sub(self, t_idx: int, s_idx: int) -> None:
        try:
            current = self._state_view.groups[t_idx].subgroups[s_idx].name
        except IndexError:
            return
        text, ok = QInputDialog.getText(self, "Rename subgroup", "New name:", text=current)
        if not ok or not text.strip():
            return
        new = text.strip()
        log.info("state_view: rename subgroup %r -> %r", current, new)
        self._state_view.groups[t_idx].subgroups[s_idx].name = new
        self._save_and_rebuild_state()

    def _sv_delete_sub(self, t_idx: int, s_idx: int) -> None:
        try:
            sub = self._state_view.groups[t_idx].subgroups[s_idx]
        except IndexError:
            return
        if QMessageBox.question(
            self, "Delete subgroup",
            f"Remove subgroup '{sub.name}' and its {len(sub.signals)} signals?",
        ) != QMessageBox.StandardButton.Yes:
            return
        log.info("state_view: delete subgroup %r (%d signals)",
                 sub.name, len(sub.signals))
        del self._state_view.groups[t_idx].subgroups[s_idx]
        self._save_and_rebuild_state()

    def _sv_move_subgroup(self, src_t: int, sub_idx: int, dst_t: int) -> None:
        try:
            sub = self._state_view.groups[src_t].subgroups.pop(sub_idx)
        except IndexError:
            return
        log.info("state_view: move subgroup %r from %r -> %r",
                 sub.name,
                 self._state_view.groups[src_t].name,
                 self._state_view.groups[dst_t].name)
        self._state_view.groups[dst_t].subgroups.append(sub)
        self._save_and_rebuild_state()

    def _sv_add_signal(self, t_idx: int, s_idx: int) -> None:
        try:
            sub = self._state_view.groups[t_idx].subgroups[s_idx]
        except IndexError:
            return
        chosen = self._pick_signals_multi()
        if not chosen:
            return
        # Skip duplicates so the user can mash Add Signal without polluting.
        existing_lower = {s.lower() for s in sub.signals}
        added = [s for s in chosen if s.lower() not in existing_lower]
        if not added:
            self._set_status("All selected signals already in this subgroup.")
            return
        sub.signals.extend(added)
        log.info(
            "state_view: added %d signal(s) to %s/%s: %s",
            len(added),
            self._state_view.groups[t_idx].name, sub.name,
            ", ".join(added),
        )
        self._save_and_rebuild_state()

    def _sv_change_signal(self, t_idx: int, s_idx: int, sig_idx: int) -> None:
        try:
            current = self._state_view.groups[t_idx].subgroups[s_idx].signals[sig_idx]
        except IndexError:
            return
        chosen = self._pick_signal(current)
        if not chosen:
            return
        log.info("state_view: change signal %r -> %r", current, chosen)
        self._state_view.groups[t_idx].subgroups[s_idx].signals[sig_idx] = chosen
        self._save_and_rebuild_state()

    def _selected_signal_keys(self) -> set[tuple[int, int, int]]:
        """Return (t_idx, s_idx, sig_idx) for every signal row the user has highlighted."""
        out: set[tuple[int, int, int]] = set()
        for item in self.state_tree.selectedItems():
            tag = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(tag, tuple) and len(tag) == 4 and tag[0] == "signal":
                out.add((tag[1], tag[2], tag[3]))
        return out

    def _sv_remove_signals_bulk(self, keys: frozenset[tuple[int, int, int]]) -> None:
        if not keys:
            return
        # Confirm once for the whole batch.
        names: list[str] = []
        for t_idx, s_idx, sig_idx in keys:
            try:
                names.append(self._state_view.groups[t_idx].subgroups[s_idx].signals[sig_idx])
            except IndexError:
                continue
        if QMessageBox.question(
            self, "Remove signals",
            f"Remove {len(keys)} selected signal(s) from the state view?\n\n"
            + "\n".join(f"  • {n}" for n in names[:20])
            + (f"\n  ...+{len(names) - 20} more" if len(names) > 20 else ""),
        ) != QMessageBox.StandardButton.Yes:
            return

        # Group deletions by (t_idx, s_idx) and delete by descending sig_idx
        # so earlier indices stay valid as we go.
        by_sub: dict[tuple[int, int], list[int]] = {}
        for t_idx, s_idx, sig_idx in keys:
            by_sub.setdefault((t_idx, s_idx), []).append(sig_idx)
        total = 0
        for (t_idx, s_idx), indices in by_sub.items():
            for sig_idx in sorted(indices, reverse=True):
                try:
                    del self._state_view.groups[t_idx].subgroups[s_idx].signals[sig_idx]
                    total += 1
                except IndexError:
                    continue
        log.info("state_view: bulk-removed %d signals", total)
        self._save_and_rebuild_state()

    def _sv_remove_signal(self, t_idx: int, s_idx: int, sig_idx: int) -> None:
        try:
            removed = self._state_view.groups[t_idx].subgroups[s_idx].signals[sig_idx]
            del self._state_view.groups[t_idx].subgroups[s_idx].signals[sig_idx]
        except IndexError:
            return
        log.info("state_view: remove signal %r from %s/%s",
                 removed,
                 self._state_view.groups[t_idx].name,
                 self._state_view.groups[t_idx].subgroups[s_idx].name)
        self._save_and_rebuild_state()

    def _sv_move_signal(self, st: int, ss: int, sig_idx: int, dt: int, ds: int) -> None:
        try:
            sig = self._state_view.groups[st].subgroups[ss].signals.pop(sig_idx)
            self._state_view.groups[dt].subgroups[ds].signals.append(sig)
        except IndexError:
            return
        log.info(
            "state_view: move signal %r from %s/%s -> %s/%s",
            sig,
            self._state_view.groups[st].name,
            self._state_view.groups[st].subgroups[ss].name,
            self._state_view.groups[dt].name,
            self._state_view.groups[dt].subgroups[ds].name,
        )
        self._save_and_rebuild_state()

    def _pick_signal(self, current: str = "") -> str | None:
        all_signals = self.decoder.all_signal_names() if self.decoder else []
        if not all_signals:
            QMessageBox.warning(
                self, "No DBC loaded",
                "Load a DBC first (Browse DBC...) — the picker needs the signal list.",
            )
            return None
        # Single-select mode for "Change signal..." — multi doesn't make sense here.
        dlg = SignalPickerDialog(self, all_signals, current=current, allow_multi=False)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return None
        return dlg.selected()

    def _pick_signals_multi(self) -> list[str]:
        all_signals = self.decoder.all_signal_names() if self.decoder else []
        if not all_signals:
            QMessageBox.warning(
                self, "No DBC loaded",
                "Load a DBC first (Browse DBC...) — the picker needs the signal list.",
            )
            return []
        dlg = SignalPickerDialog(self, all_signals, current="", allow_multi=True)
        if dlg.exec() != dlg.DialogCode.Accepted:
            return []
        return dlg.selected_many()

    def _save_and_rebuild_state(self) -> None:
        save_state_view(self._state_view)
        self._build_state_tree()

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
        """Full reset: table contents, tracker, state-tree values, log dock."""
        self.error_table.setRowCount(0)
        # Clear value cells in the state tree (3 levels deep) but keep its structure.
        for t_idx in range(self.state_tree.topLevelItemCount()):
            top_item = self.state_tree.topLevelItem(t_idx)
            for s_idx in range(top_item.childCount()):
                sub_item = top_item.child(s_idx)
                for c_idx in range(sub_item.childCount()):
                    leaf = sub_item.child(c_idx)
                    leaf.setText(1, "—")
                    leaf.setData(1, Qt.ItemDataRole.BackgroundRole, None)
                    leaf.setData(1, Qt.ItemDataRole.ForegroundRole, None)
        self._state_items.clear()
        self.errq_aggregator.reset()
        self.errq_state.reset()
        self._ssman.clear()
        self._fw_versions.clear()
        self.state_led.set_state("gray")
        self._errq_signal_logged = False
        self._errq_nonzero_logged = False
        self._errq_decode_failure_logged = False
        self.log_view.clear()

    def _clear_passive_errors(self) -> None:
        """Drop only passive entries from the tracker; active rows stay."""
        before = len(list(self.errq_state.values()))
        for key in [k for k, e in self.errq_state.entries.items() if e.status == "passive"]:
            del self.errq_state.entries[key]
        after = len(list(self.errq_state.values()))
        log.info("cleared %d passive error(s)", before - after)
        self._render_error_table()
        self._recompute_led()

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
