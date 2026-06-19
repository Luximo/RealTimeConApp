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

    if silences and silences[0][0] == 0:
        start = silences[0][1]

    if silences and silences[-1][1] >= len(segment) - 10:
        end = silences[-1][0]

    return segment[start:end] if start < end else segment


def stitch_conversation(results: list, output_path=None) -> Path:
    """
    Concatenate per-sub-clip WAV files into one final conversation audio file,
    inserting pauses between clips based on whether they are within the same
    turn (intra-turn [pause:N] gap) or crossing a turn boundary (speaker gap).

    Each clip is silence-trimmed then fade-in applied before concatenation
    to eliminate TTS tail-silence gaps and leading plosives.

    Args:
        results:     List of dicts, one per sub-clip, with keys:
                         chunk_idx    (int)
                         turn_idx     (int)
                         sub_clip_idx (int, default 0 if absent — Phase 3 compat)
                         speaker      ("S1" | "S2")
                         path         (str | Path) — WAV file for this sub-clip
                         pause_after  (float, default 0.0) — seconds of silence to
                                      insert after this clip IF the next clip is in
                                      the same turn. Ignored at turn boundaries.
                     Sorting is applied internally — arrival order does not matter.
        output_path: Destination .wav path. Defaults to output/conversation_final.wav.

    Returns:
        Path to the written output file.

    Pause rules:
        Intra-turn (same chunk_idx + turn_idx):
            prev["pause_after"] seconds of silence  (from [pause:N] marker)
        Inter-turn, different speakers:
            config.INTER_SPEAKER_PAUSE  (default 0.3s)
        Inter-turn, same speaker:
            config.SAME_SPEAKER_PAUSE   (default 0.15s)

    Output format: 44100 Hz, mono, 16-bit PCM.
    """
    output_path = Path(output_path or (config.OUTPUT_DIR / "conversation_final.wav"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    inter_ms = int(config.INTER_SPEAKER_PAUSE * 1000)
    same_ms = int(config.SAME_SPEAKER_PAUSE * 1000)

    # Normalise optional fields for backward compatibility with Phase 3 results
    for r in results:
        r.setdefault("sub_clip_idx", 0)
        r.setdefault("pause_after", 0.0)

    # Sort by (chunk, turn, sub-clip) — arrival order is nondeterministic
    sorted_results = sorted(
        results,
        key=lambda r: (r["chunk_idx"], r["turn_idx"], r["sub_clip_idx"]),
    )

    combined = AudioSegment.empty()

    for i, result in enumerate(sorted_results):
        segment = AudioSegment.from_wav(result["path"])
        segment = _trim_silence(segment)

        if config.TURN_FADE_IN_MS > 0:
            segment = segment.fade_in(config.TURN_FADE_IN_MS)

        if i > 0:
            prev = sorted_results[i - 1]
            same_turn = (
                prev["chunk_idx"] == result["chunk_idx"]
                and prev["turn_idx"] == result["turn_idx"]
            )

            if same_turn:
                # Intra-turn gap from [pause:N] marker
                pause_ms = int(prev["pause_after"] * 1000)
            else:
                # Turn boundary — speaker-based gap
                pause_ms = inter_ms if prev["speaker"] != result["speaker"] else same_ms

            combined += AudioSegment.silent(duration=pause_ms)

        combined += segment

    combined = combined.set_frame_rate(44100).set_channels(1).set_sample_width(2)
    combined.export(str(output_path), format="wav")
    return output_path
