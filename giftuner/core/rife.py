"""RIFE frame interpolation via the `rife-ncnn-vulkan` external binary.

Download the binary from:
  https://github.com/nihui/rife-ncnn-vulkan/releases
and place it somewhere on PATH, or pass the executable path via
`RifeInterpolator(exe_path=...)`.

Usage:
    rife = RifeInterpolator()
    new_frames, new_durations = rife.interpolate(frames, durations, multiplier=2)
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image

from ..paths import bundled_bin_dir
from .cancel import CancelToken, ProcessCancelled


class RifeNotFoundError(RuntimeError):
    pass


def _has_transparency(frames: List[Image.Image]) -> bool:
    """True if any frame has a non-fully-opaque alpha channel."""
    for f in frames:
        if f.mode == "RGBA":
            lo, _ = f.getchannel("A").getextrema()
            if lo < 255:
                return True
    return False


class RifeInterpolator:
    def __init__(
        self,
        exe_path: str | None = None,
        model: str = "rife-v4.6",
        gpu_id: int = 0,
    ):
        """`gpu_id`: 0..N for a specific GPU, -1 to force CPU fallback."""
        self.exe_path = exe_path or self._find_exe()
        self.model = model
        self.gpu_id = gpu_id

    @staticmethod
    def _find_exe() -> str:
        # 1) Bundled bin/ folder (next to Giftuner.exe or in project root).
        bundled = bundled_bin_dir()
        for name in ("rife-ncnn-vulkan.exe", "rife-ncnn-vulkan"):
            candidate = bundled / name
            if candidate.exists():
                return str(candidate)
        # 2) System PATH fallback.
        for name in ("rife-ncnn-vulkan", "rife-ncnn-vulkan.exe"):
            found = shutil.which(name)
            if found:
                return found
        raise RifeNotFoundError(
            "rife-ncnn-vulkan not found. Place it in the bundled bin/ folder "
            "or download from https://github.com/nihui/rife-ncnn-vulkan/releases"
        )

    def available(self) -> bool:
        try:
            self._find_exe() if not self.exe_path else None
            return True
        except RifeNotFoundError:
            return False

    def interpolate(
        self,
        frames: List[Image.Image],
        durations_ms: List[int],
        multiplier: int = 2,
        cancel: CancelToken | None = None,
    ) -> Tuple[List[Image.Image], List[int]]:
        """Interpolate frames by an integer multiplier (2x or 4x).

        Durations are scaled down proportionally so the total length stays
        the same. Pass a `cancel` token to allow aborting mid-run.
        """
        if multiplier < 2:
            return list(frames), list(durations_ms)
        if len(frames) < 2:
            return list(frames), list(durations_ms)

        target_count = (len(frames) - 1) * multiplier + 1
        rgba = [f.convert("RGBA") for f in frames]

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            if _has_transparency(rgba):
                # rife-ncnn-vulkan is RGB-only: it silently drops alpha and
                # warps the (garbage) RGB of transparent regions, which is
                # what wrecks background-removed clips. Interpolate
                # premultiplied color and the alpha matte in two separate
                # passes, then unpremultiply & recombine.
                new_frames = self._interpolate_rgba(
                    rgba, target_count, tmp_path, cancel
                )
            else:
                new_frames = self._interpolate_rgb(
                    rgba, target_count, tmp_path, cancel
                )

        # Scale durations so overall length is unchanged
        total_ms = sum(durations_ms)
        per_frame = max(1, round(total_ms / max(len(new_frames), 1)))
        new_durations = [per_frame] * len(new_frames)
        return new_frames, new_durations

    def _run(
        self,
        in_dir: Path,
        out_dir: Path,
        target_count: int,
        cancel: CancelToken | None = None,
    ) -> List[Path]:
        cmd = [
            self.exe_path,
            "-i", str(in_dir),
            "-o", str(out_dir),
            "-m", self.model,
            "-n", str(target_count),
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
        return sorted(out_dir.glob("*.png"))

    def _interpolate_rgb(
        self,
        frames: List[Image.Image],
        target_count: int,
        tmp: Path,
        cancel: CancelToken | None = None,
    ) -> List[Image.Image]:
        in_dir = tmp / "in"
        out_dir = tmp / "out"
        in_dir.mkdir()
        out_dir.mkdir()
        for i, f in enumerate(frames):
            f.convert("RGB").save(in_dir / f"{i:06d}.png")
        out_files = self._run(in_dir, out_dir, target_count, cancel)
        return [Image.open(p).convert("RGBA").copy() for p in out_files]

    def _interpolate_rgba(
        self,
        frames: List[Image.Image],
        target_count: int,
        tmp: Path,
        cancel: CancelToken | None = None,
    ) -> List[Image.Image]:
        rgb_in = tmp / "rgb_in"
        rgb_out = tmp / "rgb_out"
        a_in = tmp / "a_in"
        a_out = tmp / "a_out"
        for d in (rgb_in, rgb_out, a_in, a_out):
            d.mkdir()

        for i, f in enumerate(frames):
            arr = np.asarray(f, dtype=np.float32)  # H x W x 4
            a = arr[..., 3:4] / 255.0
            premult = np.clip(arr[..., :3] * a + 0.5, 0, 255).astype(np.uint8)
            Image.fromarray(premult, "RGB").save(rgb_in / f"{i:06d}.png")
            am = arr[..., 3].astype(np.uint8)
            Image.fromarray(np.dstack([am, am, am]), "RGB").save(
                a_in / f"{i:06d}.png"
            )

        rgb_files = self._run(rgb_in, rgb_out, target_count, cancel)
        a_files = self._run(a_in, a_out, target_count, cancel)

        out_frames: List[Image.Image] = []
        for rp, ap in zip(rgb_files, a_files):
            pm = np.asarray(Image.open(rp).convert("RGB"), dtype=np.float32)
            a = np.asarray(Image.open(ap).convert("L"), dtype=np.float32)
            a = np.clip(a, 0.0, 255.0)
            a_safe = np.where(a < 1.0, 1.0, a)
            straight = np.clip(pm * 255.0 / a_safe[..., None], 0, 255)
            straight[a < 1.0] = 0.0
            rgba = np.dstack([straight, a]).astype(np.uint8)
            out_frames.append(Image.fromarray(rgba, "RGBA"))
        return out_frames
