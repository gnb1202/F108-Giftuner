"""Main window for Giftuner."""
from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .. import FRAME_LIMITS, MAX_FRAMES, TARGET_HEIGHT, TARGET_WIDTH
from ..core.exporter import export_gif
from ..core.cancel import CancelToken, ProcessCancelled
from ..core.framecap import cap_frames
from ..core.gpuinfo import detect_gpus
from ..core.io import load_frames
from ..core.resize import (
    lock_ratio_from_height,
    lock_ratio_from_width,
    resize_frames,
)
from ..core.rife import RifeInterpolator, RifeNotFoundError
from ..core.upscale import RealEsrgan, UpscalerNotFoundError
from ..i18n import current_language, on_language_changed, set_language, tr
from ..paths import output_dir
from .busy import BusyDialog
from .preview import PreviewWidget


class ProcessWorker(QThread):
    """Runs the heavy preview pipeline (RIFE / Real-ESRGAN / resize / cap)
    off the UI thread so the loading dialog stays animated."""

    stage = pyqtSignal(str)
    done = pyqtSignal(object, object, object, object, object)
    failed = pyqtSignal(str)
    cancelled = pyqtSignal()

    def __init__(self, params: dict):
        super().__init__()
        self.p = params
        self._cancel = CancelToken()

    def cancel(self):
        """Called from the UI thread; flags + kills the running binary."""
        self._cancel.cancel()

    def run(self):
        frames = list(self.p["src_frames"])
        durations = list(self.p["src_durations"])
        applied_rife: int | None = None
        applied_upscale: int | None = None
        warnings: list[tuple[str, str]] = []
        try:
            gpu_id = self.p["gpu_id"]
            backend = self.p["backend"]

            if self.p["rife_enabled"]:
                try:
                    rife = RifeInterpolator(gpu_id=gpu_id)
                except RifeNotFoundError as e:
                    warnings.append((tr("warn_rife_title"), str(e)))
                else:
                    mult = self.p["rife_mult"]
                    self.stage.emit(tr("running_rife", mult=mult, backend=backend))
                    frames, durations = rife.interpolate(
                        frames, durations, mult, cancel=self._cancel
                    )
                    applied_rife = mult

            self._cancel.raise_if_cancelled()

            if self.p["upscale_enabled"]:
                try:
                    scale = self.p["upscale_scale"]
                    up = RealEsrgan(scale=scale, gpu_id=gpu_id)
                except UpscalerNotFoundError as e:
                    warnings.append((tr("warn_upscale_title"), str(e)))
                else:
                    self.stage.emit(tr("running_upscale", backend=backend))
                    frames = up.upscale(frames, cancel=self._cancel)
                    applied_upscale = scale

            self._cancel.raise_if_cancelled()

            self.stage.emit(tr("stage_resize"))
            frames = resize_frames(
                frames, self.p["target_w"], self.p["target_h"]
            )

            self._cancel.raise_if_cancelled()

            if self.p["cap_enabled"]:
                frames, durations = cap_frames(
                    frames, durations, self.p["frame_limit"]
                )
        except ProcessCancelled:
            self.cancelled.emit()
            return
        except Exception as e:  # noqa: BLE001 - surfaced to the user
            self.failed.emit(str(e))
            return

        self.done.emit(frames, durations, applied_rife, applied_upscale, warnings)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(900, 600)

        self._src_frames: List[Image.Image] = []
        self._src_durations: List[int] = []
        self._out_frames: List[Image.Image] = []
        self._out_durations: List[int] = []
        self._suppress_spin = False
        self._gpus = detect_gpus()
        self._last_status_key: tuple[str, dict] | None = None
        # Track the processing options actually applied to the current output,
        # so the export filename can reflect them.
        self._applied_rife_mult: int | None = None
        self._applied_upscale_scale: int | None = None
        # Export background: None = keep transparent, else (r, g, b).
        self._bg_color = QColor(0, 0, 0)
        # Background processing worker + its modal busy dialog.
        self._worker: ProcessWorker | None = None
        self._busy: BusyDialog | None = None

        self._build_ui()
        self._refresh_gpu_label()
        self._retranslate()
        self._set_status("ready")

        on_language_changed(self._retranslate)

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # Menu bar
        mb = self.menuBar()
        self.file_menu = mb.addMenu("")
        self.exit_action = QAction(self)
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)

        self.lang_menu = mb.addMenu("")
        lang_group = QActionGroup(self)
        lang_group.setExclusive(True)
        self.act_en = QAction("English", self, checkable=True)
        self.act_ko = QAction("한국어", self, checkable=True)
        for act, code in ((self.act_en, "en"), (self.act_ko, "ko")):
            lang_group.addAction(act)
            act.triggered.connect(lambda _checked=False, c=code: self._change_language(c))
            self.lang_menu.addAction(act)
        self.act_en.setChecked(current_language() == "en")
        self.act_ko.setChecked(current_language() == "ko")

        # Central layout
        central = QWidget()
        root = QHBoxLayout(central)

        # Left: preview
        self.preview = PreviewWidget()
        root.addWidget(self.preview, stretch=3)

        # Right: controls
        controls = QWidget()
        cl = QVBoxLayout(controls)
        cl.setSpacing(10)
        root.addWidget(controls, stretch=2)

        self.load_btn = QPushButton()
        self.load_btn.clicked.connect(self._on_load)
        cl.addWidget(self.load_btn)

        # GPU group
        self.gpu_group = QGroupBox()
        gl = QVBoxLayout(self.gpu_group)
        self.gpu_check = QCheckBox()
        self.gpu_check.setChecked(True)
        self.gpu_check.toggled.connect(self._on_gpu_toggled)
        gl.addWidget(self.gpu_check)
        gid_row = QHBoxLayout()
        self.gpu_id_label = QLabel()
        gid_row.addWidget(self.gpu_id_label)
        self.gpu_id_spin = QSpinBox()
        max_id = max(0, len(self._gpus) - 1) if self._gpus else 7
        self.gpu_id_spin.setRange(0, max_id)
        self.gpu_id_spin.setValue(0)
        self.gpu_id_spin.valueChanged.connect(self._refresh_gpu_label)
        gid_row.addWidget(self.gpu_id_spin)
        gl.addLayout(gid_row)
        self.gpu_name_label = QLabel("")
        self.gpu_name_label.setWordWrap(True)
        self.gpu_name_label.setStyleSheet("color:#4ade80;font-weight:bold;")
        gl.addWidget(self.gpu_name_label)
        self.rescan_btn = QPushButton()
        self.rescan_btn.clicked.connect(self._rescan_gpus)
        gl.addWidget(self.rescan_btn)
        self.cpu_note_label = QLabel()
        gl.addWidget(self.cpu_note_label)
        cl.addWidget(self.gpu_group)

        # Resize group
        self.resize_group = QGroupBox()
        rl = QVBoxLayout(self.resize_group)
        w_row = QHBoxLayout()
        self.width_label = QLabel()
        w_row.addWidget(self.width_label)
        self.w_spin = QSpinBox()
        self.w_spin.setRange(16, 7680)
        self.w_spin.setValue(TARGET_WIDTH)
        self.w_spin.valueChanged.connect(self._on_width_changed)
        w_row.addWidget(self.w_spin)
        rl.addLayout(w_row)

        h_row = QHBoxLayout()
        self.height_label = QLabel()
        h_row.addWidget(self.height_label)
        self.h_spin = QSpinBox()
        self.h_spin.setRange(9, 4320)
        self.h_spin.setValue(TARGET_HEIGHT)
        self.h_spin.valueChanged.connect(self._on_height_changed)
        h_row.addWidget(self.h_spin)
        rl.addLayout(h_row)

        self.keep_ratio_check = QCheckBox()
        self.keep_ratio_check.toggled.connect(self._on_keep_ratio_toggled)
        rl.addWidget(self.keep_ratio_check)

        self.free_size_check = QCheckBox()
        self.free_size_check.toggled.connect(self._on_free_size_toggled)
        rl.addWidget(self.free_size_check)

        self.reset_btn = QPushButton()
        self.reset_btn.clicked.connect(self._reset_size)
        rl.addWidget(self.reset_btn)
        cl.addWidget(self.resize_group)

        # Frame cap group
        self.framecap_group = QGroupBox()
        fl = QVBoxLayout(self.framecap_group)
        self.cap_check = QCheckBox()
        self.cap_check.setChecked(True)
        self.cap_check.toggled.connect(self._on_cap_toggled)
        fl.addWidget(self.cap_check)
        limit_row = QHBoxLayout()
        self.frame_limit_label = QLabel()
        limit_row.addWidget(self.frame_limit_label)
        self.frame_limit_combo = QComboBox()
        for v in FRAME_LIMITS:
            self.frame_limit_combo.addItem(str(v), v)
        # Select the default (MAX_FRAMES) if present
        default_idx = self.frame_limit_combo.findData(MAX_FRAMES)
        if default_idx >= 0:
            self.frame_limit_combo.setCurrentIndex(default_idx)
        limit_row.addWidget(self.frame_limit_combo)
        fl.addLayout(limit_row)
        self.frame_info = QLabel()
        fl.addWidget(self.frame_info)
        cl.addWidget(self.framecap_group)

        # RIFE group
        self.rife_group = QGroupBox()
        rfl = QVBoxLayout(self.rife_group)
        self.rife_check = QCheckBox()
        rfl.addWidget(self.rife_check)
        mult_row = QHBoxLayout()
        self.rife_mult_label = QLabel()
        mult_row.addWidget(self.rife_mult_label)
        self.rife_mult = QComboBox()
        self.rife_mult.addItems(["2x", "4x"])
        mult_row.addWidget(self.rife_mult)
        rfl.addLayout(mult_row)
        self.rife_note_label = QLabel()
        rfl.addWidget(self.rife_note_label)
        cl.addWidget(self.rife_group)

        # Upscale group
        self.upscale_group = QGroupBox()
        ul = QVBoxLayout(self.upscale_group)
        self.upscale_check = QCheckBox()
        ul.addWidget(self.upscale_check)
        scale_row = QHBoxLayout()
        self.scale_label = QLabel()
        scale_row.addWidget(self.scale_label)
        self.upscale_scale = QComboBox()
        self.upscale_scale.addItems(["2", "3", "4"])
        scale_row.addWidget(self.upscale_scale)
        ul.addLayout(scale_row)
        self.upscale_note_label = QLabel()
        ul.addWidget(self.upscale_note_label)
        cl.addWidget(self.upscale_group)

        # Background group
        self.bg_group = QGroupBox()
        bl = QVBoxLayout(self.bg_group)
        self.bg_combo = QComboBox()
        self.bg_combo.addItem("", "transparent")
        self.bg_combo.addItem("", "color")
        self.bg_combo.currentIndexChanged.connect(self._on_bg_mode_changed)
        bl.addWidget(self.bg_combo)

        color_row = QHBoxLayout()
        self.bg_color_btn = QPushButton()
        self.bg_color_btn.clicked.connect(self._pick_bg_color)
        color_row.addWidget(self.bg_color_btn)
        self.bg_color_swatch = QLabel()
        self.bg_color_swatch.setFixedWidth(48)
        color_row.addWidget(self.bg_color_swatch)
        bl.addLayout(color_row)

        self.bg_note_label = QLabel()
        self.bg_note_label.setWordWrap(True)
        bl.addWidget(self.bg_note_label)
        cl.addWidget(self.bg_group)
        self._on_bg_mode_changed()

        cl.addStretch()

        self.process_btn = QPushButton()
        self.process_btn.clicked.connect(self._on_process)
        cl.addWidget(self.process_btn)

        self.export_btn = QPushButton()
        self.export_btn.clicked.connect(self._on_export)
        cl.addWidget(self.export_btn)

        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

    # ------------------------------------------------------------- i18n
    def _change_language(self, code: str):
        set_language(code)
        self.act_en.setChecked(code == "en")
        self.act_ko.setChecked(code == "ko")

    def _retranslate(self):
        self.setWindowTitle(tr("app_title"))

        self.file_menu.setTitle(tr("menu_file"))
        self.exit_action.setText(tr("menu_exit"))
        self.lang_menu.setTitle(tr("menu_language"))
        self.act_en.setText(tr("menu_english"))
        self.act_ko.setText(tr("menu_korean"))

        self.load_btn.setText(tr("load_file"))

        self.gpu_group.setTitle(tr("group_gpu"))
        self.gpu_check.setText(tr("use_gpu"))
        self.gpu_id_label.setText(tr("gpu_id"))
        self.gpu_id_spin.setToolTip(tr("gpu_id_tooltip"))
        self.rescan_btn.setText(tr("rescan_gpus"))
        self.cpu_note_label.setText(tr("cpu_fallback_note"))

        self.resize_group.setTitle(tr("group_resize"))
        self.width_label.setText(tr("width"))
        self.height_label.setText(tr("height"))
        self.keep_ratio_check.setText(tr("keep_ratio"))
        self.free_size_check.setText(tr("free_size"))
        self.reset_btn.setText(tr("reset_size"))

        self.framecap_group.setTitle(tr("group_framecap"))
        self.cap_check.setText(tr("auto_cap"))
        self.frame_limit_label.setText(tr("frame_limit"))
        self.frame_limit_combo.setToolTip(tr("frame_limit_tooltip"))

        self.rife_group.setTitle(tr("group_rife"))
        self.rife_check.setText(tr("enable_rife"))
        self.rife_mult_label.setText(tr("multiplier"))
        self.rife_note_label.setText(tr("rife_note"))

        self.upscale_group.setTitle(tr("group_upscale"))
        self.upscale_check.setText(tr("enable_upscale"))
        self.scale_label.setText(tr("scale"))
        self.upscale_note_label.setText(tr("upscale_note"))

        self.bg_group.setTitle(tr("group_background"))
        self.bg_combo.setItemText(0, tr("bg_transparent"))
        self.bg_combo.setItemText(1, tr("bg_color"))
        self.bg_note_label.setText(tr("bg_note"))
        self._refresh_bg_swatch()

        self.process_btn.setText(tr("process_preview"))
        self.export_btn.setText(tr("export_gif"))

        # Dynamic labels
        self._refresh_gpu_label()
        self._refresh_frame_info()
        self._refresh_status()

    # ------------------------------------------------------- spin handlers
    def _active_ratio(self) -> float | None:
        """Aspect ratio (w/h) the spinboxes are locked to.

        None  -> free size (no locking)
        source ratio -> 'keep original ratio' with a clip loaded
        TARGET_RATIO -> default 240:135 LCD lock
        """
        if self.free_size_check.isChecked():
            return None
        if self.keep_ratio_check.isChecked() and self._src_frames:
            sw, sh = self._src_frames[0].size
            if sw > 0 and sh > 0:
                return sw / sh
        return TARGET_WIDTH / TARGET_HEIGHT

    def _reapply_ratio_lock(self):
        """Re-derive height from the current width using the active ratio."""
        ratio = self._active_ratio()
        if ratio is None:
            return
        self._suppress_spin = True
        _, h = lock_ratio_from_width(self.w_spin.value(), ratio)
        self.h_spin.setValue(h)
        self._suppress_spin = False

    def _on_keep_ratio_toggled(self, _checked: bool):
        self._reapply_ratio_lock()

    def _on_free_size_toggled(self, checked: bool):
        # Ratio-keeping is meaningless when size is fully free.
        self.keep_ratio_check.setEnabled(not checked)
        if not checked:
            self._reapply_ratio_lock()

    def _on_width_changed(self, w: int):
        if self._suppress_spin:
            return
        ratio = self._active_ratio()
        if ratio is None:
            return  # free size: leave height untouched
        self._suppress_spin = True
        _, h = lock_ratio_from_width(w, ratio)
        self.h_spin.setValue(h)
        self._suppress_spin = False

    def _on_height_changed(self, h: int):
        if self._suppress_spin:
            return
        ratio = self._active_ratio()
        if ratio is None:
            return  # free size: leave width untouched
        self._suppress_spin = True
        w, _ = lock_ratio_from_height(h, ratio)
        self.w_spin.setValue(w)
        self._suppress_spin = False

    def _on_gpu_toggled(self, checked: bool):
        self.gpu_id_spin.setEnabled(checked)
        self._refresh_gpu_label()

    def _on_cap_toggled(self, checked: bool):
        self.frame_limit_combo.setEnabled(checked)

    def _current_frame_limit(self) -> int:
        data = self.frame_limit_combo.currentData()
        return int(data) if data is not None else MAX_FRAMES

    def _refresh_gpu_label(self):
        if not self.gpu_check.isChecked():
            self.gpu_name_label.setText(tr("gpu_cpu_mode"))
            self.gpu_name_label.setStyleSheet("color:#fbbf24;font-weight:bold;")
            return
        if not self._gpus:
            self.gpu_name_label.setText(tr("gpu_not_detected"))
            self.gpu_name_label.setStyleSheet("color:#f87171;font-weight:bold;")
            return
        idx = self.gpu_id_spin.value()
        match = next((name for i, name in self._gpus if i == idx), None)
        if match:
            self.gpu_name_label.setText(tr("gpu_ok", name=match))
            self.gpu_name_label.setStyleSheet("color:#4ade80;font-weight:bold;")
        else:
            self.gpu_name_label.setText(tr("gpu_missing_index", idx=idx))
            self.gpu_name_label.setStyleSheet("color:#f87171;font-weight:bold;")

    def _refresh_frame_info(self):
        if not self._out_frames and not self._src_frames:
            self.frame_info.setText(tr("frames_placeholder"))
        elif self._out_frames:
            size = self._out_frames[0].size if self._out_frames else "-"
            self.frame_info.setText(
                tr(
                    "frames_out",
                    src=len(self._src_frames),
                    out=len(self._out_frames),
                    size=size,
                )
            )
        else:
            self.frame_info.setText(tr("frames_src", n=len(self._src_frames)))

    def _rescan_gpus(self):
        self._gpus = detect_gpus()
        max_id = max(0, len(self._gpus) - 1) if self._gpus else 7
        self.gpu_id_spin.setRange(0, max_id)
        self._refresh_gpu_label()
        if self._gpus:
            names = ", ".join(f"[{i}] {n}" for i, n in self._gpus)
            self._set_status("detected", list=names)
        else:
            self._set_status("no_gpu_detected")

    def _gpu_id(self) -> int:
        return self.gpu_id_spin.value() if self.gpu_check.isChecked() else -1

    def _reset_size(self):
        self._suppress_spin = True
        self.w_spin.setValue(TARGET_WIDTH)
        self.h_spin.setValue(TARGET_HEIGHT)
        self._suppress_spin = False

    # ------------------------------------------------------- background
    def _bg_is_transparent(self) -> bool:
        return self.bg_combo.currentData() == "transparent"

    def _background_rgb(self) -> tuple[int, int, int] | None:
        """None when transparent, else the (r, g, b) fill color."""
        if self._bg_is_transparent():
            return None
        c = self._bg_color
        return (c.red(), c.green(), c.blue())

    def _on_bg_mode_changed(self, *_):
        use_color = not self._bg_is_transparent()
        self.bg_color_btn.setEnabled(use_color)
        self.bg_color_swatch.setEnabled(use_color)
        self._refresh_bg_swatch()

    def _pick_bg_color(self):
        c = QColorDialog.getColor(self._bg_color, self, tr("bg_choose_color"))
        if c.isValid():
            self._bg_color = c
            self._refresh_bg_swatch()

    def _refresh_bg_swatch(self):
        hex_ = self._bg_color.name()
        if self._bg_is_transparent():
            self.bg_color_swatch.setText("—")
            self.bg_color_swatch.setStyleSheet("color:#888;")
        else:
            self.bg_color_swatch.setText("")
            self.bg_color_swatch.setStyleSheet(
                f"background:{hex_};border:1px solid #555;"
            )
        self.bg_color_btn.setText(tr("bg_current", hex=hex_))

    # ------------------------------------------------------------- actions
    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("dlg_load_title"),
            "",
            tr("dlg_load_filter"),
        )
        if not path:
            return
        try:
            frames, durations = load_frames(path)
        except Exception as e:
            QMessageBox.critical(self, tr("err_load_title"), str(e))
            return
        self._src_frames = frames
        self._src_durations = durations
        self._out_frames = []
        self._out_durations = []
        self._refresh_frame_info()
        # If 'keep original ratio' is active, sync H to the new clip's ratio.
        self._reapply_ratio_lock()
        # Show the raw source as-is; do NOT run the pipeline on load.
        # Processing happens only when the user clicks "Process preview".
        self.preview.set_frames(self._src_frames, self._src_durations)
        self._set_status("loaded", name=Path(path).name, n=len(frames))

    def _on_process(self):
        if not self._src_frames:
            QMessageBox.information(self, tr("info_no_source_title"), tr("info_no_source"))
            return
        if self._worker is not None:
            return  # a run is already in progress

        gpu_id = self._gpu_id()
        params = {
            "src_frames": list(self._src_frames),
            "src_durations": list(self._src_durations),
            "gpu_id": gpu_id,
            "backend": f"GPU#{gpu_id}" if gpu_id >= 0 else "CPU",
            "rife_enabled": self.rife_check.isChecked(),
            "rife_mult": 2 if self.rife_mult.currentText() == "2x" else 4,
            "upscale_enabled": self.upscale_check.isChecked(),
            "upscale_scale": int(self.upscale_scale.currentText()),
            "target_w": self.w_spin.value(),
            "target_h": self.h_spin.value(),
            "cap_enabled": self.cap_check.isChecked(),
            "frame_limit": self._current_frame_limit(),
        }

        self._busy = BusyDialog(self)
        self._worker = ProcessWorker(params)
        self._worker.stage.connect(self._on_process_stage)
        self._worker.done.connect(self._on_process_done)
        self._worker.failed.connect(self._on_process_failed)
        self._worker.cancelled.connect(self._on_process_cancelled)
        self._worker.finished.connect(self._worker.deleteLater)
        self._busy.cancel_requested.connect(self._worker.cancel)

        self._set_status("stage_prepare")
        self._worker.start()
        # Modal: blocks here while the Qt event loop keeps delivering the
        # worker's signals; closed via accept() from the result slots.
        self._busy.exec()

    def _on_process_stage(self, msg: str):
        if self._busy is not None:
            self._busy.set_text(msg)
        self.statusBar().showMessage(msg)

    def _finish_worker(self):
        if self._busy is not None:
            self._busy.accept()
            self._busy = None
        self._worker = None

    def _on_process_done(self, frames, durations, applied_rife, applied_upscale, warnings):
        self._out_frames = frames
        self._out_durations = durations
        self._applied_rife_mult = applied_rife
        self._applied_upscale_scale = applied_upscale
        self.preview.set_frames(frames, durations)
        self._refresh_frame_info()
        self._set_status("processed")
        self._finish_worker()
        for title, text in warnings:
            QMessageBox.warning(self, title, text)

    def _on_process_failed(self, msg: str):
        self._finish_worker()
        self._set_status("ready")
        QMessageBox.critical(self, tr("err_process_title"), msg)

    def _on_process_cancelled(self):
        # Keep whatever preview existed before; just stop and report.
        self._finish_worker()
        self._set_status("cancelled")

    def _build_suffix(self) -> str:
        """Build the auto-appended suffix based on applied processing options.

        Example: '_RIFEx2_ESRGANx2_120fps'
        """
        parts: list[str] = []
        if self._applied_rife_mult:
            parts.append(f"RIFEx{self._applied_rife_mult}")
        if self._applied_upscale_scale:
            parts.append(f"ESRGANx{self._applied_upscale_scale}")
        bg = self._background_rgb()
        parts.append("alpha" if bg is None else "bg%02X%02X%02X" % bg)
        parts.append(f"{len(self._out_frames)}fps")
        return "_" + "_".join(parts)

    @staticmethod
    def _sanitize_basename(name: str) -> str:
        """Strip extension and invalid filename characters."""
        name = Path(name).stem.strip()
        if not name:
            return "output"
        bad = '<>:"/\\|?*'
        for ch in bad:
            name = name.replace(ch, "_")
        return name

    def _on_export(self):
        if not self._out_frames:
            QMessageBox.information(self, tr("info_nothing_title"), tr("info_nothing"))
            return

        base, ok = QInputDialog.getText(
            self,
            tr("dlg_filename_title"),
            tr("dlg_filename_prompt"),
            QLineEdit.EchoMode.Normal,
            tr("dlg_filename_default"),
        )
        if not ok:
            return
        base = self._sanitize_basename(base)

        out_dir = output_dir()
        out_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{base}{self._build_suffix()}.gif"
        out_path = out_dir / filename

        try:
            export_gif(
                self._out_frames,
                self._out_durations,
                out_path,
                background=self._background_rgb(),
            )
        except Exception as e:
            QMessageBox.critical(self, tr("err_export_title"), str(e))
            return
        self._set_status("saved", path=str(out_path))

    # ------------------------------------------------------------- status
    def _set_status(self, key: str, **kwargs):
        self._last_status_key = (key, kwargs)
        self.statusBar().showMessage(tr(key, **kwargs))

    def _refresh_status(self):
        if self._last_status_key is None:
            return
        key, kwargs = self._last_status_key
        self.statusBar().showMessage(tr(key, **kwargs))
