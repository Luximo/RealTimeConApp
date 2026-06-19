"""
Day 2 — Phase 4: verify that [pause:N] silences are inserted correctly
by audio_utils.stitch_conversation() when sub-clips share the same turn.

Strategy: reuse two existing Phase 3 output WAVs as fake sub-clips of a
single turn, request a known pause_after between them, stitch, then
measure the output duration and confirm the pause is present within
a small tolerance.

No TTS generation needed — pure audio assembly test.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydub import AudioSegment
import config
from audio_utils import stitch_conversation

OUTPUT_DIR = config.OUTPUT_DIR

# ── Pick two existing WAVs from the Phase 3 output ────────────────────────────
# Any two files will do — we only care about their durations, not their content.
WAV_A = OUTPUT_DIR / "chunk_00_turn_00.wav"
WAV_B = OUTPUT_DIR / "chunk_00_turn_01.wav"

TOLERANCE_MS = 80  # acceptable timing error in milliseconds


def duration_ms(path: Path) -> float:
    return len(AudioSegment.from_wav(str(path)))


def test_intra_turn_pause(pause_seconds: float, label: str):
    """
    Stitch WAV_A → [pause_seconds silence] → WAV_B as one turn,
    then verify the output duration matches expectation.
    """
    out_path = OUTPUT_DIR / f"test_pause_{label}.wav"

    results = [
        {
            "chunk_idx": 0,
            "turn_idx": 0,
            "sub_clip_idx": 0,
            "speaker": "S1",
            "path": str(WAV_A),
            "pause_after": pause_seconds,  # <-- the gap we're testing
        },
        {
            "chunk_idx": 0,
            "turn_idx": 0,
            "sub_clip_idx": 1,
            "speaker": "S1",
            "path": str(WAV_B),
            "pause_after": 0.0,
        },
    ]

    stitch_conversation(results, output_path=out_path)

    # Measure actual output duration
    actual_ms = duration_ms(out_path)

    # Expected: trimmed(A) + pause + trimmed(B)
    # We don't re-trim here — just use the raw durations as an upper bound
    # and check the gap is approximately right by comparing with/without pause.
    no_pause_results = [
        {**results[0], "pause_after": 0.0},
        results[1],
    ]
    no_pause_path = OUTPUT_DIR / f"test_pause_{label}_nopause.wav"
    stitch_conversation(no_pause_results, output_path=no_pause_path)
    no_pause_ms = duration_ms(no_pause_path)

    gap_ms = actual_ms - no_pause_ms
    expected_ms = int(pause_seconds * 1000)
    error_ms = abs(gap_ms - expected_ms)

    status = "PASS" if error_ms <= TOLERANCE_MS else "FAIL"
    print(
        f"  [{status}] pause={pause_seconds}s | "
        f"expected gap={expected_ms}ms | actual gap={gap_ms}ms | "
        f"error={error_ms}ms (tol={TOLERANCE_MS}ms)"
    )
    print(f"         output: {out_path.name}  ({actual_ms}ms total)")
    return status == "PASS"


def test_inter_turn_boundary():
    """
    Two clips as DIFFERENT turns — should use INTER_SPEAKER_PAUSE (300ms),
    not pause_after, even if pause_after is set on the first result.
    """
    out_path = OUTPUT_DIR / "test_pause_inter_turn.wav"

    results = [
        {
            "chunk_idx": 0,
            "turn_idx": 0,
            "sub_clip_idx": 0,
            "speaker": "S1",
            "path": str(WAV_A),
            "pause_after": 5.0,  # should be IGNORED at a turn boundary
        },
        {
            "chunk_idx": 0,
            "turn_idx": 1,  # <-- different turn_idx triggers boundary logic
            "sub_clip_idx": 0,
            "speaker": "S2",
            "path": str(WAV_B),
            "pause_after": 0.0,
        },
    ]

    stitch_conversation(results, output_path=out_path)
    actual_ms = duration_ms(out_path)

    # Reference: same two clips treated as ONE turn, pause_after=0.0 — truly no gap
    no_pause_results = [
        {**results[0], "turn_idx": 0, "pause_after": 0.0},
        {**results[1], "turn_idx": 0},  # same turn → no inter-speaker pause inserted
    ]
    no_pause_path = OUTPUT_DIR / "test_pause_inter_turn_nopause.wav"
    stitch_conversation(no_pause_results, output_path=no_pause_path)
    no_pause_ms = duration_ms(no_pause_path)

    gap_ms = actual_ms - no_pause_ms
    expected_gap = int(config.INTER_SPEAKER_PAUSE * 1000)  # 300ms
    error_ms = abs(gap_ms - expected_gap)
    status = "PASS" if error_ms <= TOLERANCE_MS else "FAIL"
    print(
        f"  [{status}] inter-turn boundary | "
        f"expected gap={expected_gap}ms (INTER_SPEAKER_PAUSE) | "
        f"actual gap={gap_ms}ms | error={error_ms}ms"
    )
    print(f"         (pause_after=5.0 on prev clip correctly ignored)")
    return status == "PASS"


# ── Main ──────────────────────────────────────────────────────────────────────

print("=" * 60)
print("test_stitching_pause.py — Phase 4 Day 2")
print("=" * 60)

for path in (WAV_A, WAV_B):
    if not path.exists():
        print(f"ERROR: required test WAV not found: {path}")
        print("Run a Phase 3 render first to generate output files.")
        sys.exit(1)

print(f"\nUsing WAV_A: {WAV_A.name}  ({duration_ms(WAV_A):.0f}ms)")
print(f"Using WAV_B: {WAV_B.name}  ({duration_ms(WAV_B):.0f}ms)")

all_passed = True
print("\n-- Intra-turn pause insertion --")
all_passed &= test_intra_turn_pause(0.5, "0.5s")
all_passed &= test_intra_turn_pause(1.0, "1.0s")
all_passed &= test_intra_turn_pause(3.0, "3.0s")

print("\n-- Inter-turn boundary (pause_after must be ignored) --")
all_passed &= test_inter_turn_boundary()

print("\n" + "=" * 60)
print("ALL PASSED" if all_passed else "SOME TESTS FAILED")
print("=" * 60)
