"""
Connection Settings dialog.

Pops up either from the toolbar (Settings...) or automatically on auth
failure. Returns a dict of credentials when the user clicks Connect.
"""
from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


@dataclass
class ConnectionCreds:
    host: str
    user: str
    port: int
    key_filename: str | None
    passphrase: str | None
    password: str | None


class ConnectionDialog(QDialog):
    def __init__(self, parent: QWidget | None, creds: ConnectionCreds, error: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Connection Settings")
        self.setMinimumWidth(480)
        self._creds = creds

        root = QVBoxLayout(self)

        if error:
            err = QLabel(f"<b>Authentication failed:</b><br>{error}")
            err.setWordWrap(True)
            err.setStyleSheet("color: #c0392b;")
            root.addWidget(err)

        form = QFormLayout()
        root.addLayout(form)

        self.host_edit = QLineEdit(creds.host)
        self.user_edit = QLineEdit(creds.user)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(creds.port)

        self.key_edit = QLineEdit(creds.key_filename or "")
        self.key_edit.setPlaceholderText("(leave blank to auto-detect / use SSH agent)")
        self.key_browse = QPushButton("Browse...")
        self.key_browse.clicked.connect(self._on_browse_key)
        key_row = QHBoxLayout()
        key_row.addWidget(self.key_edit, 1)
        key_row.addWidget(self.key_browse)
        key_widget = QWidget()
        key_widget.setLayout(key_row)

        self.passphrase_edit = QLineEdit(creds.passphrase or "")
        self.passphrase_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_edit.setPlaceholderText("(only if your key is encrypted)")

        self.password_edit = QLineEdit(creds.password or "")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setPlaceholderText("(only if no key auth is available)")

        self.show_secret = QCheckBox("Show passphrase / password")
        self.show_secret.toggled.connect(self._on_toggle_secret)

        form.addRow("Host", self.host_edit)
        form.addRow("User", self.user_edit)
        form.addRow("Port", self.port_spin)
        form.addRow("Private key", key_widget)
        form.addRow("Key passphrase", self.passphrase_edit)
        form.addRow("Password", self.password_edit)
        form.addRow("", self.show_secret)

        hint = QLabel(
            "<small>Tip: if your keys live in WSL (<code>~/.ssh/</code> in Ubuntu), "
            "the app auto-tries <code>\\\\wsl$\\&lt;distro&gt;\\home\\&lt;user&gt;\\.ssh\\</code> "
            "as well as <code>%USERPROFILE%\\.ssh\\</code>.</small>"
        )
        hint.setWordWrap(True)
        hint.setTextFormat(Qt.TextFormat.RichText)
        root.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Connect")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_browse_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select SSH private key",
            self.key_edit.text() or "",
            "All files (*)",
        )
        if path:
            self.key_edit.setText(path)

    def _on_toggle_secret(self, checked: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        self.passphrase_edit.setEchoMode(mode)
        self.password_edit.setEchoMode(mode)

    def result_creds(self) -> ConnectionCreds:
        return ConnectionCreds(
            host=self.host_edit.text().strip(),
            user=self.user_edit.text().strip(),
            port=int(self.port_spin.value()),
            key_filename=self.key_edit.text().strip() or None,
            passphrase=self.passphrase_edit.text() or None,
            password=self.password_edit.text() or None,
        )
