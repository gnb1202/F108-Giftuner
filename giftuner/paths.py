"""Runtime path helpers.

Returns different paths depending on whether the app is running in dev
mode (Python interpreter) or frozen mode (PyInstaller --onedir exe).

Frozen layout (PyInstaller 6.x --onedir):

    dist/Giftuner/
    ├── Giftuner.exe            <- sys.executable, writable area
    ├── output/                 <- user-writable (lives next to exe)
    └── _internal/              <- sys._MEIPASS, read-only bundled data
        ├── bin/                <-- bundled_bin_dir()
        ├── PyQt6/
        └── ...

Dev layout:

    D:/Github/Giftuner/
    ├── giftuner/
    ├── bin/                    <-- bundled_bin_dir()
    └── output/                 <-- output_dir()
"""
from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _meipass_dir() -> Path:
    """PyInstaller's bundled-data directory.

    In --onedir mode this is `dist/Giftuner/_internal/`.
    In --onefile mode this is a temp extraction dir.
    Outside of a frozen app this is the project root.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parents[1]


def exe_dir() -> Path:
    """Directory of the running executable.

    In frozen mode this is the folder containing `Giftuner.exe` — it's
    the right place for user-writable content (`output/`, configs, etc.).
    In dev mode this is the project root.
    """
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[1]


def base_dir() -> Path:
    """Backwards-compat alias for `exe_dir()`."""
    return exe_dir()


def bundled_bin_dir() -> Path:
    """Directory containing bundled ncnn-vulkan binaries (read-only)."""
    return _meipass_dir() / "bin"


def output_dir() -> Path:
    """Directory where exported GIFs are saved (user-writable)."""
    return exe_dir() / "output"
