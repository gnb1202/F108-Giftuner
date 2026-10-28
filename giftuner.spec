# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Giftuner (Windows, --onedir).

Build with:
    pyinstaller giftuner.spec

Output:
    dist/Giftuner/Giftuner.exe   (+ bundled Qt, Pillow, ncnn bin/ folder)
"""
from pathlib import Path

# --------------------------------------------------------------------- paths
PROJECT_ROOT = Path.cwd()
BIN_DIR = PROJECT_ROOT / "bin"

# --------------------------------------------------------------------- datas
# Bundle the entire `bin/` tree (RIFE + Real-ESRGAN binaries + models).
# PyInstaller expects (src, dest_in_bundle) tuples.
datas = []
if BIN_DIR.exists():
    datas.append((str(BIN_DIR), "bin"))

# --------------------------------------------------------------------- hidden
hiddenimports = [
    # imageio video plugin (used by io._load_video)
    "imageio_ffmpeg",
    "imageio.plugins.ffmpeg",
    "imageio.plugins.pillow",
    # Pillow plugins that PyInstaller sometimes misses
    "PIL._tkinter_finder",
]

# --------------------------------------------------------------------- build
a = Analysis(
    ["run.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Shrink the build by excluding stuff we never use.
        # NOTE: keep `email`, `http`, `urllib` — pkg_resources /
        # setuptools runtime hooks import them transitively.
        "tkinter",
        "unittest",
        "xmlrpc",
        "pydoc",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Giftuner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,        # UPX can corrupt Qt plugins on Windows — leave off
    console=False,    # GUI app — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,        # TODO: add icon.ico when available
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Giftuner",
)
