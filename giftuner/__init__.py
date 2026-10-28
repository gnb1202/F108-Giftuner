"""Giftuner - GIF tuner for AULA F108 Pro LCD (240x135)."""

TARGET_WIDTH = 240
TARGET_HEIGHT = 135
TARGET_RATIO = TARGET_WIDTH / TARGET_HEIGHT  # 16:9

# F108 Pro keyboard variants support different max GIF frame counts:
#   - 131: some early/overseas batches
#   - 141: most common (default)
#   - 255: newer firmware revisions
FRAME_LIMITS = (131, 141, 255)
MAX_FRAMES = 141  # default / legacy fallback

__version__ = "0.1.0"
