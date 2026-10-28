"""Real-ESRGAN upscaling via the `realesrgan-ncnn-vulkan` external binary.

Download from https://github.com/xinntao/Real-ESRGAN/releases and place
on PATH, or pass the executable path explicitly.

Note: For the F108 Pro use-case (tiny 240x135 output), upscaling is only
useful when the *source* is lower-resolution than the target and you want
a cleaner downscale path. Typically: upscale small source -> downscale to
240x135.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from PIL import Image

from ..paths import bundled_bin_dir
from .cancel import CancelToken, ProcessCancelled


class UpscalerNotFoundError(RuntimeError):
    pass


class RealEsrgan:
    def __init__(
        self,
        exe_path: str | None = None,
        model: str = "realesr-animevideov3",
        scale: int = 2,
        gpu_id: int = 0,
    ):
        """`gpu_id`: 0..N for a specific GPU, -1 to force CPU fallback."""
        self.exe_path = exe_path or self._find_exe()
        self.model = model
        self.scale = scale
        self.gpu_id = gpu_id

    @staticmethod
    def _find_exe() -> str:
        # 1) Bundled bin/ folder.
        bundled = bundled_bin_dir()
        for name in ("realesrgan-ncnn-vulkan.exe", "realesrgan-ncnn-vulkan"):
            candidate = bundled / name
            if candidate.exists():
                return str(candidate)
        # 2) System PATH fallback.
        for name in ("realesrgan-ncnn-vulkan", "realesrgan-ncnn-vulkan.exe"):
            found = shutil.which(name)
            if found:
                return found
        raise UpscalerNotFoundError(
            "realesrgan-ncnn-vulkan not found. Place it in the bundled bin/ "
            "folder or download from https://github.com/xinntao/Real-ESRGAN/releases"
        )

    def available(self) -> bool:
        try:
            self._find_exe() if not self.exe_path else None
            return True
        except UpscalerNotFoundError:
            return False

    def upscale(
        self,
        frames: List[Image.Image],
        cancel: CancelToken | None = None,
    ) -> List[Image.Image]:
        if not frames:
            return []
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            in_dir = tmp_path / "in"
            out_dir = tmp_path / "out"
            in_dir.mkdir()
            out_dir.mkdir()
            for i, f in enumerate(frames):
                f.save(in_dir / f"{i:06d}.png")

            cmd = [
                self.exe_path,
                "-i", str(in_dir),
                "-o", str(out_dir),
                "-n", self.model,
                "-s", str(self.scale),
                "-f", "png",
                "-g", str(self.gpu_id),
            ]
            proc = subprocess.Popen(cmd)
            if cancel is not None:
                cancel.attach(proc)
            try:
                proc.wait()
            finally:
                if cancel is not None:
                    cancel.detach()
            if cancel is not None and cancel.cancelled:
                raise ProcessCancelled()
            if proc.returncode != 0:
                raise subprocess.CalledProcessError(proc.returncode, cmd)

            out_files = sorted(out_dir.glob("*.png"))
            # realesrgan-ncnn-vulkan upscales the alpha channel too; keep it.
            return [Image.open(p).convert("RGBA").copy() for p in out_files]
