"""
Day 6 — Phase 4: edge case hardening for the parser → captions pipeline.

Tests all four edge cases from Phase4.md without any TTS generation:
  1. Multiple consecutive [pause:N] markers in one turn
  2. [pause:N] at the very start or end of a turn
  3. Turn consisting entirely of pause markers (no words) → warn + skip
  4. Script with no pause markers at all → still produces correct timestamps

Also verifies that build_captions handles sub-clips from all the above
correctly (ascending timestamps, correct word counts, no crashes).

Uses existing Phase 3 WAV files for clip durations — no generation needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydub import AudioSegment
import config
from script_parser import _parse_pause_markers, _build_chunk
from audio_utils import build_captions

OUTPUT_DIR = config.OUTPUT_DIR
WAV_A = OUTPUT_DIR / "chunk_00_turn_00.wav"  # ~2.4s
WAV_B = OUTPUT_DIR / "chunk_00_turn_01.wav"  # ~5.3s

all_passed = True


def check(label, condition, detail=""):
    global all_passed
    status = "PASS" if condition else "FAIL"
    if not condition:
        all_passed = False
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")


def make_result(chunk_idx, turn_idx, sc_idx, speaker, path, text, pause_after):
    return {
        "chunk_idx": chunk_idx,
        "turn_idx": turn_idx,
        "sub_clip_idx": sc_idx,
        "speaker": speaker,
        "path": str(path),
        "text": text,
        "pause_after": pause_after,
    }


print("=" * 65)
print("test_edge_cases_phase4.py — Phase 4 Day 6")
print("=" * 65)

for path in (WAV_A, WAV_B):
    if not path.exists():
        print(f"ERROR: {path} not found.")
        sys.exit(1)


# ── Edge case 1: Multiple consecutive [pause:N] markers ───────────────────────
print("\n[Edge case 1] Multiple consecutive [pause:N] markers")
text = "Hold on [pause:0.5] wait [pause:1.0] okay I'm ready"
parts = _parse_pause_markers(text)
check("3 sub-clips produced", len(parts) == 3, str(parts))
check(
    "Sub-clip texts correct",
    [p["text"] for p in parts] == ["Hold on", "wait", "okay I'm ready"],
)
check("Pause durations correct", [p["pause_after"] for p in parts] == [0.5, 1.0, 0.0])

# build_captions on these sub-clips
results_ec1 = [
    make_result(0, 0, 0, "S1", WAV_A, parts[0]["text"], parts[0]["pause_after"]),
    make_result(0, 0, 1, "S1", WAV_B, parts[1]["text"], parts[1]["pause_after"]),
    make_result(0, 0, 2, "S1", WAV_A, parts[2]["text"], parts[2]["pause_after"]),
]
caps = build_captions(results_ec1)
expected_words = sum(len(p["text"].split()) for p in parts)
check(
    "Correct word count in captions",
    len(caps) == expected_words,
    f"got {len(caps)}, expected {expected_words}",
)
check(
    "Timestamps ascending",
    all(caps[i]["start"] >= caps[i - 1]["end"] - 0.001 for i in range(1, len(caps))),
)


# ── Edge case 2a: [pause:N] at the very START of a turn ───────────────────────
print("\n[Edge case 2a] [pause:N] at very start of turn")
text = "[pause:1.0] okay so anyway"
parts = _parse_pause_markers(text)
# Marker at start with no preceding text → warning logged, duration discarded
# Remaining text "okay so anyway" should be a single sub-clip
check("1 sub-clip (marker-at-start discarded)", len(parts) == 1, str(parts))
check("Text intact", parts[0]["text"] == "okay so anyway" if parts else False)
check("pause_after is 0.0", parts[0]["pause_after"] == 0.0 if parts else False)


# ── Edge case 2b: [pause:N] at the very END of a turn ────────────────────────
print("\n[Edge case 2b] [pause:N] at very end of turn")
text = "let me think about that [pause:2.0]"
parts = _parse_pause_markers(text)
# Trailing marker: text before it becomes a sub-clip, pause_after forced to 0.0
# (last sub-clip always has pause_after=0.0 — inter-speaker gap handled separately)
check("1 sub-clip produced", len(parts) == 1, str(parts))
check("Text intact", parts[0]["text"] == "let me think about that" if parts else False)
check(
    "pause_after forced to 0.0 (last sub-clip rule)",
    parts[0]["pause_after"] == 0.0 if parts else False,
)


# ── Edge case 3: Turn consisting entirely of pause markers ────────────────────
print("\n[Edge case 3] Turn consisting entirely of pause markers (no words)")
text = "[pause:2]"
parts = _parse_pause_markers(text)
check("Empty sub-clip list returned", parts == [])

# _build_chunk should warn and skip this turn
fake_turns = [("S1", "[pause:2]"), ("S2", "This is a real line")]
chunk = _build_chunk(0, fake_turns)
# Only S2's turn should appear (S1's marker-only turn is skipped)
check("Marker-only turn skipped in chunk", len(chunk["turns"]) == 1)
check(
    "Remaining turn is S2",
    chunk["turns"][0]["speaker"] == "S2" if chunk["turns"] else False,
)


# ── Edge case 4: Script with no pause markers at all ─────────────────────────
print("\n[Edge case 4] Script with no pause markers (passthrough)")
turns_no_markers = [
    ("S1", "Did you catch the news today"),
    ("S2", "Don't even get me started"),
    ("S1", "That bad huh"),
]
chunk = _build_chunk(0, turns_no_markers)
check("All 3 turns preserved", len(chunk["turns"]) == 3)
check(
    "Each turn has exactly 1 sub-clip",
    all(len(t["sub_clips"]) == 1 for t in chunk["turns"]),
)
check(
    "All pause_after values are 0.0",
    all(sc["pause_after"] == 0.0 for t in chunk["turns"] for sc in t["sub_clips"]),
)

# build_captions works correctly with no markers
results_ec4 = [
    make_result(0, 0, 0, "S1", WAV_A, "Did you catch the news today", 0.0),
    make_result(0, 1, 0, "S2", WAV_B, "Don't even get me started", 0.0),
    make_result(0, 2, 0, "S1", WAV_A, "That bad huh", 0.0),
]
caps = build_captions(results_ec4)
check("Correct word count (no markers)", len(caps) == 14, f"got {len(caps)}")
check(
    "Timestamps ascending (no markers)",
    all(caps[i]["start"] >= caps[i - 1]["end"] - 0.001 for i in range(1, len(caps))),
)
check(
    "Speaker labels alternate correctly",
    caps[0]["speaker"] == "S1" and caps[6]["speaker"] == "S2",
)


# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("ALL PASSED" if all_passed else "SOME TESTS FAILED")
print("=" * 65)
