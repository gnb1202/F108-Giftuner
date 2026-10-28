"""Lightweight dict-based i18n for Giftuner.

Usage:
    from .i18n import tr, set_language
    set_language("ko")
    label.setText(tr("load_file"))
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, List

# ---------------------------------------------------------------- strings
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # Window
        "app_title": "Giftuner — F108 Pro GIF Editor",

        # Menus
        "menu_file": "File",
        "menu_language": "Language",
        "menu_english": "English",
        "menu_korean": "한국어",
        "menu_exit": "Exit",

        # Buttons
        "load_file": "Load file…",
        "process_preview": "Process preview",
        "export_gif": "Export GIF…",
        "reset_size": "Reset to 240×135 (LCD)",
        "rescan_gpus": "Re-scan GPUs",

        # Groups
        "group_gpu": "GPU acceleration (Vulkan)",
        "group_resize": "Resize",
        "keep_ratio": "Keep source aspect ratio",
        "free_size": "Free size (unlock W/H)",
        "group_framecap": "Frame cap",
        "frame_limit": "Max frames",
        "frame_limit_tooltip": "F108 Pro variants support different maximums: 131, 141, or 255 frames.",
        "group_rife": "Frame interpolation (RIFE)",
        "group_upscale": "Upscale (Real-ESRGAN)",

        # Fields
        "use_gpu": "Use GPU",
        "gpu_id": "GPU ID",
        "gpu_id_tooltip": "0 = first GPU. Increase for multi-GPU systems.",
        "cpu_fallback_note": "Off = CPU fallback (slow)",
        "width": "Width",
        "height": "Height",
        "auto_cap": "Auto-cap frames",
        "frames_placeholder": "Frames: —",
        "enable_rife": "Enable RIFE",
        "multiplier": "Multiplier",
        "rife_note": "Requires rife-ncnn-vulkan on PATH",
        "enable_upscale": "Enable Real-ESRGAN",
        "scale": "Scale",
        "upscale_note": "Requires realesrgan-ncnn-vulkan on PATH",

        # Background
        "group_background": "Background",
        "bg_transparent": "Keep transparent",
        "bg_color": "Fill with color",
        "bg_choose_color": "Choose color…",
        "bg_current": "Current: {hex}",
        "bg_note": "Transparent GIF is 1-bit (no soft edges); some LCDs ignore it.",

        # GPU status
        "gpu_cpu_mode": "⚙ CPU fallback mode",
        "gpu_not_detected": "⚠ No GPU detected\n(install rife/realesrgan-ncnn-vulkan first)",
        "gpu_ok": "✓ {name}",
        "gpu_missing_index": "⚠ GPU #{idx} not found",

        # Status bar
        "ready": "Ready. Load a file to start.",
        "loaded": "Loaded {name} — {n} frames",
        "running_rife": "Running RIFE {mult}x on {backend}…",
        "running_upscale": "Running Real-ESRGAN on {backend}…",
        "processed": "Processed.",
        "processing_title": "Processing",
        "stage_prepare": "Preparing…",
        "stage_resize": "Resizing & finalizing…",
        "cancel": "Cancel",
        "cancelling": "Cancelling…",
        "cancelled": "Cancelled.",
        "saved": "Saved {path}",
        "detected": "Detected: {list}",
        "no_gpu_detected": "No GPU detected.",

        # Frame info
        "frames_src": "Frames: {n} (source)",
        "frames_out": "Frames: src={src}  →  out={out} @ {size}",

        # Dialogs
        "dlg_load_title": "Load animation",
        "dlg_load_filter": "Animations (*.gif *.mp4 *.webp *.png *.apng *.mov *.mkv *.webm *.avi);;All files (*.*)",
        "dlg_save_title": "Save GIF",
        "dlg_save_filter": "GIF (*.gif)",
        "dlg_filename_title": "Export GIF",
        "dlg_filename_prompt": "Base filename (suffixes will be appended automatically):",
        "dlg_filename_default": "output",
        "preview_filename": "→ {name}",

        # Errors
        "err_load_title": "Load error",
        "err_process_title": "Processing error",
        "err_export_title": "Export error",
        "info_no_source": "Load a file first.",
        "info_no_source_title": "No source",
        "info_nothing_title": "Nothing to export",
        "info_nothing": "Run 'Process preview' first.",
        "warn_rife_title": "RIFE unavailable",
        "warn_upscale_title": "Upscaler unavailable",
    },
    "ko": {
        "app_title": "Giftuner — F108 Pro GIF 편집기",

        "menu_file": "파일",
        "menu_language": "언어",
        "menu_english": "English",
        "menu_korean": "한국어",
        "menu_exit": "종료",

        "load_file": "파일 열기…",
        "process_preview": "미리보기 처리",
        "export_gif": "GIF 내보내기…",
        "reset_size": "240×135로 초기화 (LCD)",
        "rescan_gpus": "GPU 다시 검색",

        "group_gpu": "GPU 가속 (Vulkan)",
        "group_resize": "크기 조정",
        "keep_ratio": "원본 비율 유지",
        "free_size": "사이즈 자유 (W/H 잠금 해제)",
        "group_framecap": "프레임 제한",
        "frame_limit": "최대 프레임",
        "frame_limit_tooltip": "F108 Pro는 기기/펌웨어 버전에 따라 131, 141, 255 프레임까지 지원합니다.",
        "group_rife": "프레임 보간 (RIFE)",
        "group_upscale": "업스케일 (Real-ESRGAN)",

        "use_gpu": "GPU 사용",
        "gpu_id": "GPU 번호",
        "gpu_id_tooltip": "0 = 첫 번째 GPU. 멀티 GPU 시스템에서 변경.",
        "cpu_fallback_note": "끄면 CPU 폴백 (느림)",
        "width": "가로",
        "height": "세로",
        "auto_cap": "프레임 자동 제한",
        "frames_placeholder": "프레임: —",
        "enable_rife": "RIFE 사용",
        "multiplier": "배율",
        "rife_note": "PATH에 rife-ncnn-vulkan 필요",
        "enable_upscale": "Real-ESRGAN 사용",
        "scale": "배율",
        "upscale_note": "PATH에 realesrgan-ncnn-vulkan 필요",

        "group_background": "배경",
        "bg_transparent": "투명 배경 유지",
        "bg_color": "배경색으로 채우기",
        "bg_choose_color": "색상 선택…",
        "bg_current": "현재: {hex}",
        "bg_note": "투명 GIF는 1비트(가장자리 거칠어짐). 일부 LCD는 투명을 무시합니다.",

        "gpu_cpu_mode": "⚙ CPU 폴백 모드",
        "gpu_not_detected": "⚠ GPU를 찾을 수 없음\n(rife/realesrgan-ncnn-vulkan 먼저 설치)",
        "gpu_ok": "✓ {name}",
        "gpu_missing_index": "⚠ GPU #{idx} 없음",

        "ready": "준비 완료. 파일을 먼저 불러오세요.",
        "loaded": "{name} 불러옴 — {n} 프레임",
        "running_rife": "RIFE {mult}x 실행 중 ({backend})…",
        "running_upscale": "Real-ESRGAN 실행 중 ({backend})…",
        "processed": "처리 완료.",
        "processing_title": "처리 중",
        "stage_prepare": "준비 중…",
        "stage_resize": "크기 조정 및 마무리 중…",
        "cancel": "취소",
        "cancelling": "취소 중…",
        "cancelled": "취소됨.",
        "saved": "저장됨: {path}",
        "detected": "감지됨: {list}",
        "no_gpu_detected": "GPU를 찾을 수 없음.",

        "frames_src": "프레임: {n} (원본)",
        "frames_out": "프레임: 원본={src}  →  출력={out} @ {size}",

        "dlg_load_title": "애니메이션 불러오기",
        "dlg_load_filter": "애니메이션 (*.gif *.mp4 *.webp *.png *.apng *.mov *.mkv *.webm *.avi);;모든 파일 (*.*)",
        "dlg_save_title": "GIF 저장",
        "dlg_save_filter": "GIF (*.gif)",
        "dlg_filename_title": "GIF 내보내기",
        "dlg_filename_prompt": "파일 이름을 입력하세요 (뒤에 옵션 접미사가 자동으로 붙습니다):",
        "dlg_filename_default": "output",
        "preview_filename": "→ {name}",

        "err_load_title": "불러오기 오류",
        "err_process_title": "처리 오류",
        "err_export_title": "내보내기 오류",
        "info_no_source": "먼저 파일을 불러오세요.",
        "info_no_source_title": "원본 없음",
        "info_nothing_title": "내보낼 것 없음",
        "info_nothing": "먼저 '미리보기 처리'를 실행하세요.",
        "warn_rife_title": "RIFE 사용 불가",
        "warn_upscale_title": "업스케일러 사용 불가",
    },
}

_current_lang = "en"
_listeners: List[Callable[[], None]] = []

_CONFIG_PATH = Path.home() / ".giftuner" / "config.json"


def load_saved_language() -> str:
    try:
        if _CONFIG_PATH.exists():
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
            lang = data.get("language", "en")
            if lang in TRANSLATIONS:
                return lang
    except Exception:
        pass
    return "en"


def save_language(lang: str) -> None:
    try:
        _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CONFIG_PATH.write_text(
            json.dumps({"language": lang}, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def set_language(lang: str) -> None:
    global _current_lang
    if lang not in TRANSLATIONS:
        return
    _current_lang = lang
    save_language(lang)
    for cb in list(_listeners):
        try:
            cb()
        except Exception:
            pass


def current_language() -> str:
    return _current_lang


def on_language_changed(cb: Callable[[], None]) -> None:
    _listeners.append(cb)


def tr(key: str, **kwargs) -> str:
    table = TRANSLATIONS.get(_current_lang, TRANSLATIONS["en"])
    template = table.get(key) or TRANSLATIONS["en"].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


# Initialize from saved config
_current_lang = load_saved_language()
