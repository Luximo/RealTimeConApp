"""Stitching, pause insertion, speed/time-stretch."""

import subprocess


def get_ffmpeg_version() -> str:
    """Run ffmpeg -version and return the first line of its output."""
    result = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()[0]