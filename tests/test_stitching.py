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
    {"chunk_idx": 0, "turn_idx": 0, "speaker": "S1",
     "path": str(config.OUTPUT_DIR / "chunk_00_turn_00.wav")},
    {"chunk_idx": 1, "turn_idx": 0, "speaker": "S2",
     "path": str(config.OUTPUT_DIR / "chunk_01_turn_00.wav")},
    {"chunk_idx": 2, "turn_idx": 0, "speaker": "S1",
     "path": str(config.OUTPUT_DIR / "chunk_02_turn_00.wav")},
    {"chunk_idx": 3, "turn_idx": 0, "speaker": "S2",
     "path": str(config.OUTPUT_DIR / "chunk_03_turn_00.wav")},
]


def main():
    # Confirm source files exist
    for r in RESULTS:
        p = Path(r["path"])
        assert p.exists(), f"Missing Day 3 output file: {p}\nRun test_parallel.py first."

    print("Stitching 4 turns into conversation_final.wav ...")
    output = stitch_conversation(RESULTS)
    print(f"Written: {output}")

    # ── Verify output ─────────────────────────────────────────────────────────
    assert output.exists(),         "Output file was not created"
    assert output.stat().st_size > 10_000, \
        f"Output suspiciously small: {output.stat().st_size} bytes"

    # Check duration using pydub
    from pydub import AudioSegment
    final   = AudioSegment.from_wav(str(output))
    sources = [AudioSegment.from_wav(r["path"]) for r in RESULTS]

    src_total_ms   = sum(len(s) for s in sources)
    pause_total_ms = (len(RESULTS) - 1) * int(config.INTER_SPEAKER_PAUSE * 1000)
    expected_ms    = src_total_ms + pause_total_ms

    print(f"\nSource audio total : {src_total_ms / 1000:.2f}s")
    print(f"Pauses (3 × {config.INTER_SPEAKER_PAUSE}s)  : {pause_total_ms / 1000:.2f}s")
    print(f"Expected total     : {expected_ms / 1000:.2f}s")
    print(f"Actual total       : {len(final) / 1000:.2f}s")

    tolerance_ms = 50   # allow 50ms rounding tolerance
    assert abs(len(final) - expected_ms) <= tolerance_ms, (
        f"Duration mismatch: expected ~{expected_ms}ms, got {len(final)}ms"
    )

    print("\nAll assertions passed.")
    print(f"\nListen to: {output}")
    print("Check for natural pauses at speaker transitions and no seam artifacts.")


if __name__ == "__main__":
    main()