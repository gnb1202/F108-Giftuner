"""Multi-format frame loader.

Supports: GIF, MP4, MOV, WebP (animated), APNG, PNG sequence.
Returns a list of PIL.Image frames in **RGBA** mode + per-frame duration in ms.

RGBA is used throughout so that transparency from sources such as a
ProRes 4444 / alpha MOV survives all the way to the GIF exporter.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageSequence


VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
ANIM_IMG_EXTS = {".gif", ".webp", ".apng", ".png"}


def load_frames(path: str | Path) -> Tuple[List[Image.Image], List[int]]:
    """Load animation frames from a file.

    Returns (frames, durations_ms). If a still image is given, single frame
    with 100ms duration is returned.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    ext = p.suffix.lower()
    if ext in VIDEO_EXTS:
        return _load_video(p)
    return _load_pillow(p)


def _load_pillow(p: Path) -> Tuple[List[Image.Image], List[int]]:
    im = Image.open(p)
    frames: List[Image.Image] = []
    durations: List[int] = []
    for frame in ImageSequence.Iterator(im):
        frames.append(frame.convert("RGBA").copy())
        durations.append(int(frame.info.get("duration", 100)))
    if not frames:
        raise ValueError(f"No frames decoded from {p}")
    return frames, durations


def _load_video(p: Path) -> Tuple[List[Image.Image], List[int]]:
    """Decode a video to RGBA frames.

    Uses imageio-ffmpeg's low-level ``read_frames`` with ``pix_fmt="rgba"``
    so that an alpha channel (e.g. a transparent ProRes 4444 MOV) is kept.
    The default imageio reader hard-codes RGB output and silently drops
    alpha, which is why we go one level lower here.
    """
    try:
        return _load_video_rgba(p)
    except Exception:
        # Last-resort fallback: RGB-only decode (no transparency, but at
        # least the clip still loads).
        return _load_video_rgb(p)


def _load_video_rgba(p: Path) -> Tuple[List[Image.Image], List[int]]:
    import numpy as np
    import imageio_ffmpeg

    gen = imageio_ffmpeg.read_frames(str(p), pix_fmt="rgba", bits_per_pixel=32)
    meta = next(gen)  # first item is the metadata dict
    w, h = meta["size"]
    fps = float(meta.get("fps") or 30.0)
    duration_ms = int(round(1000.0 / max(fps, 1.0)))

    frames: List[Image.Image] = []
    try:
        for raw in gen:
            arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 4)
            frames.append(Image.fromarray(arr, "RGBA").copy())
    finally:
        gen.close()

    if not frames:
        raise ValueError(f"No frames in {p}")
    return frames, [duration_ms] * len(frames)


def _load_video_rgb(p: Path) -> Tuple[List[Image.Image], List[int]]:
    import imageio.v3 as iio

    arr_frames = list(iio.imiter(p))
    if not arr_frames:
        raise ValueError(f"No frames in {p}")
    try:
        fps = iio.immeta(p).get("fps", 30.0)
    except Exception:
        fps = 30.0
    duration_ms = int(round(1000.0 / max(fps, 1.0)))
    frames = [Image.fromarray(arr).convert("RGBA") for arr in arr_frames]
    return frames, [duration_ms] * len(frames)
