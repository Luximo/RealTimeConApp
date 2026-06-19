"""
Day 4 sanity test — audio_utils.stitch_conversation.

Stitches the 4 WAV files already in output/ from Day 3 directly —
no generation needed, so this test runs in under a second.

Verifies:
  - output/conversation_final.wav is created and non-empty
  - Duration matches the sum of input clips plus expected pause time
  - No crash or format error

Listen to conversation_final.wav to confirm:
  - Natural flow between speakers
  - Audible pause at each transition (~0.4s between speakers)
  - No clicks, glitches, or seam artifacts at chunk boundaries
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from audio_utils import stitch_conversation

# ── Reconstruct the results list from Day 3's known output ───────────────────
# The Day 3 short test was: S1, S2, S1, S2 (one turn per chunk).
# All transitions are inter-speaker → all pauses should be 0.4s.
RESULTS = [
    {
        "chunk_idx": 0,
        "turn_idx": 0,
        "speaker": "S1",
        "path": str(config.OUTPUT_DIR / "chunk_00_turn_00.wav"),
    },
    {
        "chunk_idx": 1,
        "turn_idx": 0,
        "speaker": "S2",
        "path": str(config.OUTPUT_DIR / "chunk_01_turn_00.wav"),
    },
    {
        "chunk_idx": 2,
        "turn_idx": 0,
        "speaker": "S1",
        "path": str(config.OUTPUT_DIR / "chunk_02_turn_00.wav"),
    },
    {
        "chunk_idx": 3,
        "turn_idx": 0,
        "speaker": "S2",
        "path": str(config.OUTPUT_DIR / "chunk_03_turn_00.wav"),
    },
]


def main():
    # Confirm source files exist
    for r in RESULTS:
        p = Path(r["path"])
        assert (
            p.exists()
        ), f"Missing Day 3 output file: {p}\nRun test_parallel.py first."

    print("Stitching 4 turns into conversation_final.wav ...")
    output = stitch_conversation(RESULTS)
    print(f"Written: {output}")

    # ── Verify output ─────────────────────────────────────────────────────────
    assert output.exists(), "Output file was not created"
    assert (
        output.stat().st_size > 10_000
    ), f"Output suspiciously small: {output.stat().st_size} bytes"

    # Check duration using pydub
    from pydub import AudioSegment

    final = AudioSegment.from_wav(str(output))
    sources = [AudioSegment.from_wav(r["path"]) for r in RESULTS]

    src_total_ms = sum(len(s) for s in sources)
    pause_total_ms = (len(RESULTS) - 1) * int(config.INTER_SPEAKER_PAUSE * 1000)
    expected_ms = src_total_ms + pause_total_ms

    # With silence trimming active, actual duration will be ≤ the naive sum.
    # Check it's within a generous range rather than an exact match.
    print(f"\nSource audio total (pre-trim): {src_total_ms / 1000:.2f}s")
    print(
        f"Pauses ({len(RESULTS)-1} × {config.INTER_SPEAKER_PAUSE}s) : {pause_total_ms / 1000:.2f}s"
    )
    print(f"Actual total (post-trim)      : {len(final) / 1000:.2f}s")

    # Must be shorter than the naive sum (trimming removes silence)
    # and longer than just the pauses (there is actual speech in there)
    assert (
        len(final) < src_total_ms + pause_total_ms + 200
    ), "Output longer than expected — silence trimming may not have run"
    assert (
        len(final) > pause_total_ms + 2000
    ), f"Output suspiciously short: {len(final)}ms"

    print("\nAll assertions passed.")
    print(f"\nListen to: {output}")
    print("Check for natural pauses at speaker transitions and no seam artifacts.")


if __name__ == "__main__":
    main()
