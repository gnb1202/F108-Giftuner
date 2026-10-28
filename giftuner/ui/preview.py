"""Animated preview widget that plays a list of PIL frames on a timer."""
from __future__ import annotations

from io import BytesIO
from typing import List

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy

from PIL import Image


def pil_to_qimage(img: Image.Image) -> QImage:
    """Convert a PIL image to a QImage, preserving alpha so the preview
    shows transparency against the widget's dark background."""
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    return QImage(
        data, img.width, img.height, img.width * 4, QImage.Format.Format_RGBA8888
    ).copy()


class PreviewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(480, 270)
        self.setStyleSheet("background:#111;color:#888;border:1px solid #333;")
        self.setText("No preview")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._frames: List[QPixmap] = []
        self._durations: List[int] = []
        self._idx = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    def set_frames(self, frames: List[Image.Image], durations_ms: List[int]):
        self._timer.stop()
        self._frames = [QPixmap.fromImage(pil_to_qimage(f)) for f in frames]
        self._durations = list(durations_ms) if durations_ms else [100] * len(frames)
        self._idx = 0
        if self._frames:
            self._show_current()
            self._timer.start(max(20, self._durations[0]))
        else:
            self.setText("No preview")

    def _advance(self):
        if not self._frames:
            return
        self._idx = (self._idx + 1) % len(self._frames)
        self._show_current()
        self._timer.start(max(20, self._durations[self._idx]))

    def _show_current(self):
        pm = self._frames[self._idx]
        scaled = pm.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._frames:
            self._show_current()
