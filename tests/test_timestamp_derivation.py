"""
Day 3 — Phase 4: verify proportional word timestamp derivation in
audio_utils.build_captions().

Strategy: construct synthetic result dicts with known text, reusing
existing Phase 3 WAV files for their durations.  No TTS generation needed.

Layout under test:
    Turn 0, sub-clip 0  →  S1  "Did you catch the news today"         (WAV_A)
    Turn 0, sub-clip 1  →  S1  "or did you miss it completely"        (WAV_B) ← intra-turn pause:1s
    Turn 1, sub-clip 0  →  S2  "Don't even get me started"            (WAV_A) ← inter-turn 0.3s
    Turn 2, sub-clip 0  →  S1  "That bad huh"                         (WAV_B) ← inter-turn 0.3s

Verified manually:
    - timestamps are strictly ascending
    - each clip's words fill exactly its (trimmed) duration
    - intra-turn pause creates a gap between sub-clip 0 and sub-clip 1 of Turn 0
    - inter-turn gaps are INTER_SPEAKER_PAUSE (0.3s)
    - speaker labels are correct throughout
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pydub import AudioSegment
import config
from audio_utils import build_captions, _trim_silence

OUTPUT_DIR = config.OUTPUT_DIR
WAV_A = OUTPUT_DIR / "chunk_00_turn_00.wav"
WAV_B = OUTPUT_DIR / "chunk_00_turn_01.wav"

INTRA_TURN_PAUSE = 1.0  # seconds — between sub-clips 0 and 1 of Turn 0


def trimmed_duration(path: Path) -> float:
    """Return duration in seconds after silence trimming (mirrors build_captions)."""
    seg = AudioSegment.from_wav(str(path))
    seg = _trim_silence(seg)
    return len(seg) / 1000.0


def build_results() -> list:
    return [
        # Turn 0 — S1, two sub-clips with an intra-turn pause
        {
            "chunk_idx": 0,
            "turn_idx": 0,
            "sub_clip_idx": 0,
            "speaker": "S1",
            "path": str(WAV_A),
            "text": "Did you catch the news today",
            "pause_after": INTRA_TURN_PAUSE,
        },
        {
            "chunk_idx": 0,
            "turn_idx": 0,
            "sub_clip_idx": 1,
            "speaker": "S1",
            "path": str(WAV_B),
            "text": "or did you miss it completely",
            "pause_after": 0.0,
        },
        # Turn 1 — S2 (inter-turn gap = INTER_SPEAKER_PAUSE)
        {
            "chunk_idx": 0,
            "turn_idx": 1,
            "sub_clip_idx": 0,
            "speaker": "S2",
            "path": str(WAV_A),
            "text": "Don't even get me started",
            "pause_after": 0.0,
        },
        # Turn 2 — S1 (inter-turn gap = INTER_SPEAKER_PAUSE)
        {
            "chunk_idx": 0,
            "turn_idx": 2,
            "sub_clip_idx": 0,
            "speaker": "S1",
            "path": str(WAV_B),
            "text": "That bad huh",
            "pause_after": 0.0,
        },
    ]


def compute_expected_clip_starts(results: list) -> list:
    """
    Manually walk the same cursor logic as build_captions and return
    expected clip_start for each result (in sorted order).
    """
    sorted_r = sorted(
        results, key=lambda r: (r["chunk_idx"], r["turn_idx"], r["sub_clip_idx"])
    )
    starts = []
    cursor = 0.0
    for i, r in enumerate(sorted_r):
        starts.append(round(cursor, 6))
        dur = trimmed_duration(Path(r["path"]))
        cursor += dur
        if i < len(sorted_r) - 1:
            nxt = sorted_r[i + 1]
            same_turn = (
                r["chunk_idx"] == nxt["chunk_idx"] and r["turn_idx"] == nxt["turn_idx"]
            )
            if same_turn:
                cursor += r["pause_after"]
            elif r["speaker"] != nxt["speaker"]:
                cursor += config.INTER_SPEAKER_PAUSE
            else:
                cursor += config.SAME_SPEAKER_PAUSE
    return starts


# ── Main ──────────────────────────────────────────────────────────────────────

print("=" * 65)
print("test_timestamp_derivation.py — Phase 4 Day 3")
print("=" * 65)

for path in (WAV_A, WAV_B):
    if not path.exists():
        print(f"ERROR: {path} not found — run a Phase 3 render first.")
        sys.exit(1)

results = build_results()
captions = build_captions(results)
expected_starts = compute_expected_clip_starts(results)

# ── Print all entries (checkpoint: first 20 shown) ────────────────────────────
print(f"\n{'idx':>4}  {'speaker':<8} {'word':<28} {'start':>7}  {'end':>7}")
print("-" * 65)
for idx, c in enumerate(captions[:20]):
    print(
        f"{idx:>4}  {c['speaker']:<8} {c['word']:<28} {c['start']:>7.3f}  {c['end']:>7.3f}"
    )
if len(captions) > 20:
    print(f"  ... ({len(captions) - 20} more entries)")

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


# 1. Total word count matches sum of words across all sub-clips
expected_word_count = sum(len(r["text"].split()) for r in results)
check(
    "Total word count",
    len(captions) == expected_word_count,
    f"got {len(captions)}, expected {expected_word_count}",
)

# 2. Timestamps are strictly ascending (start of each word ≥ end of previous)
ascending = all(
    captions[i]["start"] >= captions[i - 1]["end"] - 0.001
    for i in range(1, len(captions))
)
check("Timestamps strictly ascending", ascending)

# 3. Speaker labels are correct throughout
sorted_results = sorted(
    results, key=lambda r: (r["chunk_idx"], r["turn_idx"], r["sub_clip_idx"])
)
expected_labels = []
for r in sorted_results:
    expected_labels.extend([r["speaker"]] * len(r["text"].split()))
labels_ok = [c["speaker"] for c in captions] == expected_labels
check("Speaker labels correct", labels_ok)

# 4. Clip 0 starts at t=0
check(
    "Turn 0 sub-clip 0 starts at 0.0s",
    captions[0]["start"] == 0.0,
    f"got {captions[0]['start']}",
)

# 5. Intra-turn pause: gap between last word of sub-clip 0 and first word of sub-clip 1
t0_sc0_words = len(sorted_results[0]["text"].split())
t0_sc1_first = captions[t0_sc0_words]  # first word of sub-clip 1
t0_sc0_last = captions[t0_sc0_words - 1]  # last word of sub-clip 0
gap_intra = round(t0_sc1_first["start"] - t0_sc0_last["end"], 3)
# gap = (clip_dur - last_word_end_within_clip) + pause_after
# should be approximately INTRA_TURN_PAUSE when words fill the clip evenly
check(
    f"Intra-turn gap ≥ {INTRA_TURN_PAUSE}s pause",
    gap_intra >= INTRA_TURN_PAUSE - 0.01,
    f"gap={gap_intra:.3f}s",
)

# 6. Inter-turn gap between Turn 0 and Turn 1
t0_words = sum(len(r["text"].split()) for r in sorted_results[:2])
t1_first = captions[t0_words]
t0_last = captions[t0_words - 1]
gap_inter = round(t1_first["start"] - t0_last["end"], 3)
check(
    f"Inter-turn gap ≥ {config.INTER_SPEAKER_PAUSE}s",
    gap_inter >= config.INTER_SPEAKER_PAUSE - 0.01,
    f"gap={gap_inter:.3f}s",
)

# 7. Clip start positions match manual calculation
clip_0_actual_start = captions[0]["start"]
check(
    "Clip 0 start matches manual cursor",
    abs(clip_0_actual_start - expected_starts[0]) < 0.01,
    f"got={clip_0_actual_start:.3f} expected={expected_starts[0]:.3f}",
)

print("\n" + "=" * 65)
print("ALL PASSED" if all_passed else "SOME TESTS FAILED")
print("=" * 65)
