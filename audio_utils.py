"""Stitching, pause insertion, speed/time-stretch."""

import subprocess
from pathlib import Path

from pydub import AudioSegment

import config


def get_ffmpeg_version() -> str:
    """Run ffmpeg -version and return the first line of its output."""
    result = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.splitlines()[0]


def stitch_conversation(results: list, output_path=None) -> Path:
    """
    Concatenate per-turn WAV files into one final conversation audio file,
    inserting pauses between turns based on speaker transition.

    Args:
        results:     Sorted list of dicts with keys:
                         chunk_idx, turn_idx, speaker ("S1"|"S2"), path
                     Must already be sorted by (chunk_idx, turn_idx).
        output_path: Destination .wav path. Defaults to output/conversation_final.wav.

    Returns:
        Path to the written output file.

    Pause rules (from config):
        Different speakers  → INTER_SPEAKER_PAUSE  (default 0.4s)
        Same speaker        → SAME_SPEAKER_PAUSE   (default 0.15s)

    Output format: 44100 Hz, mono, 16-bit PCM — matches reference clip format.
    """
    output_path = Path(output_path or (config.OUTPUT_DIR / "conversation_final.wav"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    inter_ms = int(config.INTER_SPEAKER_PAUSE * 1000)
    same_ms  = int(config.SAME_SPEAKER_PAUSE  * 1000)

    combined = AudioSegment.empty()

    for i, result in enumerate(results):
        segment = AudioSegment.from_wav(result["path"])

        if i > 0:
            prev_speaker = results[i - 1]["speaker"]
            curr_speaker = result["speaker"]
            pause_ms = inter_ms if prev_speaker != curr_speaker else same_ms
            combined += AudioSegment.silent(duration=pause_ms)

        combined += segment

    # Normalize to 44100 Hz mono 16-bit PCM regardless of source format
    combined = (
        combined
        .set_frame_rate(44100)
        .set_channels(1)
        .set_sample_width(2)
    )

    combined.export(str(output_path), format="wav")
    return output_path