"""
Signal picker dialog — search-as-you-type list of every signal in the
loaded DBC. Supports multi-select (Ctrl/Shift) so the user can add
multiple signals to a group with one trip through the dialog.
"""
from __future__ import annotations

from typing import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


class SignalPickerDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        signals: Iterable[str],
        current: str = "",
        allow_multi: bool = True,
    ):
        super().__init__(parent)
        self.setWindowTitle("Pick signal(s)")
        self.setMinimumSize(440, 520)
        self._all_signals = sorted(set(s for s in signals if s))
        self._current = current

        root = QVBoxLayout(self)

        hint_lines = [
            "Type to filter. Click a signal to select it.",
        ]
        if allow_multi:
            hint_lines.append("Hold Ctrl to toggle individual signals, Shift to select a range.")
        hint_lines.append("Double-click a single signal to add it immediately.")
        hint = QLabel("  •  ".join(hint_lines))
        hint.setStyleSheet("color: #666;")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search signals (e.g. SSMAN, brake, SAS)...")
        self.search.textChanged.connect(self._on_filter)
        root.addWidget(self.search)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(self.accept)
        if allow_multi:
            self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        root.addWidget(self.list)

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #666;")
        root.addWidget(self.count_label)
        self.list.itemSelectionChanged.connect(self._refresh_count)

        self._on_filter("")
        # Pre-select current if present.
        if current:
            for i in range(self.list.count()):
                if self.list.item(i).text() == current:
                    self.list.setCurrentRow(i)
                    self.list.item(i).setSelected(True)
                    break

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Add selected")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self._refresh_count()

    def _on_filter(self, text: str) -> None:
        text = text.strip().lower()
        self.list.clear()
        if not text:
            items = self._all_signals
        else:
            items = [s for s in self._all_signals if text in s.lower()]
        # Cap to avoid jankiness on huge DBCs.
        for s in items[:2000]:
            self.list.addItem(QListWidgetItem(s))
        if items:
            self.list.setCurrentRow(0)
        self._refresh_count()

    def _refresh_count(self) -> None:
        n = len(self.list.selectedItems())
        if n <= 1:
            self.count_label.setText("")
        else:
            self.count_label.setText(f"{n} signals selected")

    def selected(self) -> str | None:
        """Single-select compatibility shim — returns the focused row."""
        item = self.list.currentItem()
        return item.text() if item else None

    def selected_many(self) -> list[str]:
        """All highlighted rows (Ctrl/Shift selection)."""
        items = self.list.selectedItems()
        if items:
            return [it.text() for it in items]
        # Fall back to the focused row when nothing is highlighted (e.g.
        # double-click already accepted the dialog).
        cur = self.list.currentItem()
        return [cur.text()] if cur else []

    def keyPressEvent(self, ev) -> None:  # noqa: N802
        if ev.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.search.hasFocus():
            self.accept()
            return
        super().keyPressEvent(ev)
