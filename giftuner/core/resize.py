"""Aspect-ratio-locked resize helpers for the 240x135 LCD (16:9)."""
from __future__ import annotations

from typing import List, Tuple

from PIL import Image

from .. import TARGET_HEIGHT, TARGET_RATIO, TARGET_WIDTH


def lock_ratio_from_width(width: int, ratio: float = TARGET_RATIO) -> Tuple[int, int]:
    """Given a width, return (width, height) locked to `ratio` (w/h).

    Defaults to the 240:135 LCD ratio; pass the source ratio to keep the
    original aspect.
    """
    width = max(1, int(width))
    height = max(1, round(width / ratio))
    return width, height


def lock_ratio_from_height(height: int, ratio: float = TARGET_RATIO) -> Tuple[int, int]:
    """Given a height, return (width, height) locked to `ratio` (w/h)."""
    height = max(1, int(height))
    width = max(1, round(height * ratio))
    return width, height


def resize_frames(
    frames: List[Image.Image],
    width: int = TARGET_WIDTH,
    height: int = TARGET_HEIGHT,
    resample: int = Image.Resampling.LANCZOS,
) -> List[Image.Image]:
    """Resize all frames to (width, height). No letterboxing — assumes
    caller already enforced aspect ratio via lock_ratio_from_*.
    """
    return [f.resize((width, height), resample) for f in frames]
