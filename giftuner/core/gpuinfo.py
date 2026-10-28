"""GPU detection for Giftuner.

Primary method: parse the ncnn-vulkan binary's startup banner, which prints
lines like:
    [0 NVIDIA GeForce RTX 3060]  queueC=2[8]  queueG=0[16]  queueT=1[2]

This gives us the *exact* device ordering that `-g N` uses later.

Fallback (Windows): PowerShell Get-CimInstance Win32_VideoController.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

from ..paths import bundled_bin_dir

# (index, name)
GpuList = List[Tuple[int, str]]

_NCNN_LINE = re.compile(r"\[(\d+)\s+([^\]]+?)\]\s*queue", re.IGNORECASE)


def _run(cmd: list[str], timeout: float = 5.0) -> str:
    try:
        r = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=_no_window_flag(),
        )
    except Exception:
        return ""
    return (r.stderr or "") + "\n" + (r.stdout or "")


def _no_window_flag() -> int:
    """Hide console window on Windows when running child processes."""
    try:
        import subprocess as sp
        return getattr(sp, "CREATE_NO_WINDOW", 0)
    except Exception:
        return 0


def _find_any_ncnn_exe() -> str | None:
    """Prefer bundled binaries, fall back to PATH."""
    bundled = bundled_bin_dir()
    for name in (
        "rife-ncnn-vulkan.exe",
        "rife-ncnn-vulkan",
        "realesrgan-ncnn-vulkan.exe",
        "realesrgan-ncnn-vulkan",
    ):
        candidate = bundled / name
        if candidate.exists():
            return str(candidate)
    for name in (
        "rife-ncnn-vulkan",
        "rife-ncnn-vulkan.exe",
        "realesrgan-ncnn-vulkan",
        "realesrgan-ncnn-vulkan.exe",
    ):
        found = shutil.which(name)
        if found:
            return found
    return None


def detect_gpus_ncnn() -> GpuList:
    """Probe the ncnn-vulkan binary for its GPU enumeration banner.

    The binaries only print their GPU list to stderr when they actually
    initialize a Vulkan context — `-h` is just a usage dump. To trigger
    init we feed an empty input directory so ncnn boots up, prints the
    banner, then fails cleanly when there's nothing to process.
    """
    exe = _find_any_ncnn_exe()
    if not exe:
        return []
    with tempfile.TemporaryDirectory() as tmp:
        empty_in = Path(tmp) / "in"
        empty_out = Path(tmp) / "out"
        empty_in.mkdir()
        empty_out.mkdir()
        output = _run([exe, "-i", str(empty_in), "-o", str(empty_out)])
    matches = _NCNN_LINE.findall(output)
    # Dedupe — the banner is repeated multiple times per device
    seen: set[int] = set()
    gpus: GpuList = []
    for i, name in matches:
        idx = int(i)
        if idx not in seen:
            seen.add(idx)
            gpus.append((idx, name.strip()))
    return gpus


def detect_gpus_wmi() -> GpuList:
    """Windows fallback: query video controllers via PowerShell."""
    output = _run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "Get-CimInstance Win32_VideoController | "
            "Select-Object -ExpandProperty Name",
        ]
    )
    names = [line.strip() for line in output.splitlines() if line.strip()]
    return list(enumerate(names))


def detect_gpus() -> GpuList:
    """Return a best-effort ordered list of (index, name) GPUs.

    Prefers the ncnn-vulkan ordering (matches `-g N` flag). Falls back to
    WMI on Windows if the binary isn't on PATH.
    """
    gpus = detect_gpus_ncnn()
    if gpus:
        return gpus
    return detect_gpus_wmi()
