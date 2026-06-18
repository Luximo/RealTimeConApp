"""Sanity check: confirms audio_utils can reach ffmpeg and prints its version."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from audio_utils import get_ffmpeg_version

if __name__ == "__main__":
    print(get_ffmpeg_version())