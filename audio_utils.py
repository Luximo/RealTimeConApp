"""Stitching, pause insertion, speed/time-stretch."""

import subprocess
from pathlib import Path

from pydub import AudioSegment
from pydub.silence import detect_silence as _detect_silence

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


def _trim_silence(segment: AudioSegment) -> AudioSegment:
    """
    Strip leading and trailing silence from a TTS clip.

    TTS models often generate dead air at the start or end of an utterance.
    Left untrimmed, these stack with the inter-speaker pause and produce
    noticeable gaps in the stitched conversation.

    Uses config.SILENCE_THRESH_DB and config.SILENCE_MIN_MS as thresholds.
    If no qualifying silence is found, the segment is returned unchanged.
    """
    silences = _detect_silence(
        segment,
        min_silence_len=config.SILENCE_MIN_MS,
        silence_thresh=config.SILENCE_THRESH_DB,
    )

    start = 0
    end = len(segment)

    # Trim leading silence if the first detected block starts at position 0
    if silences and silences[0][0] == 0:
        start = silences[0][1]

    # Trim trailing silence if the last detected block reaches the end
    if silences and silences[-1][1] >= len(segment) - 10:
        end = silences[-1][0]

    return segment[start:end] if start < end else segment


def stitch_conversation(results: list, output_path=None) -> Path:
    """
    Concatenate per-turn WAV files into one final conversation audio file,
    inserting pauses between turns based on speaker transition.

    Each clip is silence-trimmed then fade-in applied before concatenation
    to eliminate TTS tail-silence gaps and leading plosives.

    Args:
        results:     Sorted list of dicts with keys:
                         chunk_idx, turn_idx, speaker ("S1"|"S2"), path
                     Must already be sorted by (chunk_idx, turn_idx).
        output_path: Destination .wav path. Defaults to output/conversation_final.wav.

    Returns:
        Path to the written output file.

    Pause rules (from config):
        Different speakers  → INTER_SPEAKER_PAUSE  (default 0.3s)
        Same speaker        → SAME_SPEAKER_PAUSE   (default 0.15s)

    Output format: 44100 Hz, mono, 16-bit PCM.
    """
    output_path = Path(output_path or (config.OUTPUT_DIR / "conversation_final.wav"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    inter_ms = int(config.INTER_SPEAKER_PAUSE * 1000)
    same_ms = int(config.SAME_SPEAKER_PAUSE * 1000)

    combined = AudioSegment.empty()

    for i, result in enumerate(results):
        segment = AudioSegment.from_wav(result["path"])
        segment = _trim_silence(segment)

        if config.TURN_FADE_IN_MS > 0:
            segment = segment.fade_in(config.TURN_FADE_IN_MS)

        if i > 0:
            prev_speaker = results[i - 1]["speaker"]
            curr_speaker = result["speaker"]
            pause_ms = inter_ms if prev_speaker != curr_speaker else same_ms
            combined += AudioSegment.silent(duration=pause_ms)

        combined += segment

    combined = combined.set_frame_rate(44100).set_channels(1).set_sample_width(2)

    combined.export(str(output_path), format="wav")
    return output_path
