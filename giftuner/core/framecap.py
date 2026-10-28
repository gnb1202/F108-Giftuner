"""Frame count cap for the F108 Pro LCD (max 141 frames)."""
from __future__ import annotations

from typing import List, Tuple

from PIL import Image

from .. import MAX_FRAMES


def cap_frames(
    frames: List[Image.Image],
    durations_ms: List[int],
    max_frames: int = MAX_FRAMES,
) -> Tuple[List[Image.Image], List[int]]:
    """Uniformly sample frames down to at most `max_frames`.

    When frames are dropped, their durations are merged into the kept
    neighbor so the total animation length stays the same.
    """
    n = len(frames)
    if n <= max_frames:
        return list(frames), list(durations_ms)

    # Uniformly pick `max_frames` indices across [0, n).
    indices = [round(i * (n - 1) / (max_frames - 1)) for i in range(max_frames)]
    # Deduplicate while preserving order
    seen = set()
    picked: List[int] = []
    for i in indices:
        if i not in seen:
            picked.append(i)
            seen.add(i)

    # Assign each original frame to the nearest picked index, summing durations.
    new_durations = [0] * len(picked)
    for orig_idx, dur in enumerate(durations_ms):
        # nearest picked
        nearest = min(range(len(picked)), key=lambda k: abs(picked[k] - orig_idx))
        new_durations[nearest] += dur

    new_frames = [frames[i] for i in picked]
    return new_frames, new_durations
