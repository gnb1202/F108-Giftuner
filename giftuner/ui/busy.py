"""Modal busy dialog shown while preview processing runs on a worker thread.

It has a Cancel button; window-close / Esc route to the same cancel action.
The dialog stays open until the owner closes it programmatically (via
``accept()``) once the worker has actually stopped.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from ..i18n import tr


class BusyDialog(QDialog):
    cancel_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("processing_title"))
        self.setModal(True)
        # Title bar without a close button; not resizable.
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
        )
        self.setFixedWidth(340)
        self._cancelling = False

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(20, 18, 20, 18)

        self._label = QLabel(tr("stage_prepare"))
        self._label.setWordWrap(True)
        lay.addWidget(self._label)

        bar = QProgressBar()
        bar.setRange(0, 0)  # indeterminate -> animated "busy" sweep
        bar.setTextVisible(False)
        lay.addWidget(bar)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._cancel_btn = QPushButton(tr("cancel"))
        self._cancel_btn.clicked.connect(self._request_cancel)
        btn_row.addWidget(self._cancel_btn)
        lay.addLayout(btn_row)

    def set_text(self, text: str) -> None:
        if not self._cancelling:
            self._label.setText(text)

    def _request_cancel(self) -> None:
        if self._cancelling:
            return
        self._cancelling = True
        self._cancel_btn.setEnabled(False)
        self._label.setText(tr("cancelling"))
        self.cancel_requested.emit()

    # --- User-initiated dismissal maps to "cancel", never an abrupt close
    def reject(self) -> None:  # Esc key
        self._request_cancel()

    def closeEvent(self, event) -> None:  # window close / Alt+F4
        event.ignore()
        self._request_cancel()
