"""GIF exporter.

Frames arrive as RGBA. The background can either be kept transparent
(GIF binary 1-bit transparency) or composited onto a solid color.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image

# Palette index reserved for the fully-transparent color.
_TRANSPARENT_INDEX = 255


def _to_p_transparent(im: Image.Image, alpha_threshold: int = 128) -> Image.Image:
    """RGBA -> P with index 255 reserved as the transparent color.

    GIF transparency is 1-bit, so the alpha channel is thresholded:
    pixels with alpha < `alpha_threshold` become fully transparent,
    everything else becomes fully opaque.
    """
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    # 255 where the pixel must be transparent, 0 where it stays.
    transparent_mask = alpha.point(lambda a: 255 if a < alpha_threshold else 0)

    # Quantize to 255 colors (0..254), leaving index 255 free.
    p = im.convert("RGB").quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    p.paste(_TRANSPARENT_INDEX, mask=transparent_mask)
    p.info["transparency"] = _TRANSPARENT_INDEX
    return p


def _to_p_on_background(im: Image.Image, bg: Tuple[int, int, int]) -> Image.Image:
    """RGBA -> P, transparency flattened onto a solid `bg` color."""
    im = im.convert("RGBA")
    base = Image.new("RGBA", im.size, (bg[0], bg[1], bg[2], 255))
    base.alpha_composite(im)
    return base.convert("RGB").convert("P", palette=Image.Palette.ADAPTIVE)


def export_gif(
    frames: List[Image.Image],
    durations_ms: List[int],
    out_path: str | Path,
    loop: int = 0,
    optimize: bool = True,
    background: Optional[Tuple[int, int, int]] = None,
    alpha_threshold: int = 128,
) -> Path:
    """Save frames as an animated GIF.

    `durations_ms` must be per-frame (same length as frames).

    `background`:
        * ``None``  -> keep transparency (1-bit transparent GIF)
        * ``(r,g,b)`` -> flatten transparency onto that solid color
    """
    if not frames:
        raise ValueError("No frames to export")
    if len(durations_ms) != len(frames):
        raise ValueError("durations_ms length must match frames length")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    transparent = background is None
    if transparent:
        pal_frames = [_to_p_transparent(f, alpha_threshold) for f in frames]
    else:
        pal_frames = [_to_p_on_background(f, background) for f in frames]

    save_kwargs = dict(
        save_all=True,
        append_images=pal_frames[1:],
        duration=durations_ms,
        loop=loop,
        optimize=optimize,
        disposal=2,
    )
    if transparent:
        save_kwargs["transparency"] = _TRANSPARENT_INDEX

    pal_frames[0].save(out, **save_kwargs)
    return out
