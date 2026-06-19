"""
Day 4 — Phase 4: implement captions.py wrapper and verify captions.json
against the real Phase 3 output WAV files.

Strategy:
  - Run parse_script() to get chunks (with the Phase 4 sub-clip format)
  - Map each sub-clip to its existing chunk_XX_turn_YY.wav from Phase 3
  - Call captions.generate_captions() to write output/captions.json
  - Verify: file exists, correct JSON structure, word count matches script,
    speaker labels correct, timestamps ascending with no overlaps

No TTS generation needed — uses only existing Phase 3 WAV files.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from script_parser import parse_script
from captions import generate_captions

OUTPUT_DIR = config.OUTPUT_DIR


def reconstruct_results(chunks: list) -> list:
    """
    Map parse_script() chunks to existing Phase 3 WAV files.

    Since current scripts have no [pause:N] markers, every turn has exactly
    one sub-clip — each maps 1-to-1 to chunk_XX_turn_YY.wav.
    """
    results = []
    for chunk in chunks:
        chunk_idx = chunk["chunk_idx"]
        for turn_idx, turn in enumerate(chunk["turns"]):
            speaker = turn["speaker"]
            for sc_idx, sub_clip in enumerate(turn["sub_clips"]):
                wav_path = OUTPUT_DIR / f"chunk_{chunk_idx:02d}_turn_{turn_idx:02d}.wav"
                if not wav_path.exists():
                    print(f"  WARNING: {wav_path.name} not found — skipping.")
                    continue
                results.append(
                    {
                        "chunk_idx": chunk_idx,
                        "turn_idx": turn_idx,
                        "sub_clip_idx": sc_idx,
                        "speaker": speaker,
                        "path": str(wav_path),
                        "text": sub_clip["text"],
                        "pause_after": sub_clip["pause_after"],
                    }
                )
    return results


# ── Main ──────────────────────────────────────────────────────────────────────

print("=" * 65)
print("test_captions_json.py — Phase 4 Day 4")
print("=" * 65)

# Build results from existing Phase 3 WAVs
print("\nParsing script ...")
chunks = parse_script()
results = reconstruct_results(chunks)
print(f"  {len(chunks)} chunks → {len(results)} sub-clip results")

# Generate captions.json
out_path = OUTPUT_DIR / "captions.json"
print(f"\nWriting {out_path.name} ...")
generate_captions(results, output_path=out_path)
print(f"  Written: {out_path}")

# Load and inspect
with open(out_path, encoding="utf-8") as f:
    data = json.load(f)

print(f"\n-- First 20 entries --")
print(f"{'idx':>4}  {'speaker':<8} {'word':<28} {'start':>7}  {'end':>7}")
print("-" * 65)
for i, entry in enumerate(data[:20]):
    print(
        f"{i:>4}  {entry['speaker']:<8} {entry['word']:<28} "
        f"{entry['start']:>7.3f}  {entry['end']:>7.3f}"
    )
if len(data) > 20:
    print(f"  ... ({len(data) - 20} more entries)")

# ── Automated checks ──────────────────────────────────────────────────────────
print("\n-- Automated checks --")
all_passed = True


def check(label, condition, detail=""):
    global all_passed
    status = "PASS" if condition else "FAIL"
    if not condition:
        all_passed = False
    suffix = f"  ({detail})" if detail else ""
    print(f"  [{status}] {label}{suffix}")


# 1. File exists and is valid JSON
check("captions.json exists", out_path.exists())
check(
    "captions.json is a non-empty list",
    isinstance(data, list) and len(data) > 0,
    f"{len(data)} entries",
)

# 2. Every entry has required keys with correct types
required_keys = {"word", "start", "end", "speaker"}
structure_ok = all(required_keys.issubset(e.keys()) for e in data)
check("All entries have required keys (word, start, end, speaker)", structure_ok)

types_ok = all(
    isinstance(e["word"], str)
    and isinstance(e["start"], (int, float))
    and isinstance(e["end"], (int, float))
    and e["speaker"] in ("S1", "S2")
    for e in data
)
check("All entries have correct types", types_ok)

# 3. Word count matches what the script parser produced
expected_words = sum(
    len(sub_clip["text"].split())
    for chunk in chunks
    for turn in chunk["turns"]
    for sub_clip in turn["sub_clips"]
    if sub_clip["text"].strip()
)
check(
    "Word count matches script",
    len(data) == expected_words,
    f"got {len(data)}, expected {expected_words}",
)

# 4. Speaker labels are only S1 or S2
speakers_valid = all(e["speaker"] in ("S1", "S2") for e in data)
check("Speaker labels are only S1 or S2", speakers_valid)

# 5. Timestamps ascending — each start >= previous end
ascending = all(
    data[i]["start"] >= data[i - 1]["end"] - 0.001 for i in range(1, len(data))
)
check("Timestamps strictly ascending (no overlaps)", ascending)

# 6. No negative timestamps
no_negatives = all(e["start"] >= 0.0 and e["end"] >= 0.0 for e in data)
check("No negative timestamps", no_negatives)

# 7. start < end for every entry
start_lt_end = all(e["start"] < e["end"] for e in data)
check("start < end for every entry", start_lt_end)

# 8. Final timestamp is reasonable (> 10s for a 16-turn conversation)
final_end = data[-1]["end"]
check(
    f"Final timestamp is reasonable (> 10s)",
    final_end > 10.0,
    f"final end = {final_end:.3f}s",
)

# 9. Speaker alternation — check S1/S2 both appear
speakers_seen = {e["speaker"] for e in data}
check("Both S1 and S2 appear in captions", speakers_seen == {"S1", "S2"})

print(f"\n  Total entries : {len(data)}")
print(f"  Total duration: {data[-1]['end']:.2f}s")
print(f"  Speakers seen : {sorted(speakers_seen)}")

print("\n" + "=" * 65)
print("ALL PASSED" if all_passed else "SOME TESTS FAILED")
print("=" * 65)
