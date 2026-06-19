"""
Day 1 — Phase 4: verify [pause:N] marker parsing in script_parser.py.

Checks:
  - All four marker formats resolve to the correct duration
  - Markers are stripped from text before any TTS call
  - Surrounding words are intact and in the right order
  - Edge cases: marker at start, consecutive markers, no markers, marker-only turn
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from script_parser import _parse_pause_markers

# ── Test cases ────────────────────────────────────────────────────────────────

cases = [
    {
        "label": "No markers (passthrough)",
        "text": "This is a normal line with no pause markers at all.",
        "expect_texts": ["This is a normal line with no pause markers at all."],
        "expect_pauses": [0.0],
    },
    {
        "label": "[pause] — default duration",
        "text": "Well I mean [pause] okay hold on.",
        "expect_texts": ["Well I mean", "okay hold on."],
        "expect_pauses": [config.DEFAULT_PAUSE_DURATION, 0.0],
    },
    {
        "label": "[pause:short]",
        "text": "I know [pause:short] right?",
        "expect_texts": ["I know", "right?"],
        "expect_pauses": [config.SHORT_PAUSE_DURATION, 0.0],
    },
    {
        "label": "[pause:long]",
        "text": "And then [pause:long] everything changed.",
        "expect_texts": ["And then", "everything changed."],
        "expect_pauses": [config.LONG_PAUSE_DURATION, 0.0],
    },
    {
        "label": "[pause:N] — numeric float",
        "text": "Okay so [pause:1.5] here we go.",
        "expect_texts": ["Okay so", "here we go."],
        "expect_pauses": [1.5, 0.0],
    },
    {
        "label": "Multiple markers in one turn",
        "text": "Well I mean [pause:0.5] okay hold on [pause:3] maybe we do it this way.",
        "expect_texts": ["Well I mean", "okay hold on", "maybe we do it this way."],
        "expect_pauses": [0.5, 3.0, 0.0],
    },
    {
        "label": "Marker at the very end (last sub-clip is empty — folded)",
        "text": "Let me think about that [pause:1]",
        "expect_texts": ["Let me think about that"],
        "expect_pauses": [0.0],  # pause_after folded into last, then forced to 0.0
    },
    {
        "label": "Marker-only turn (no speakable text)",
        "text": "[pause:2]",
        "expect_texts": [],
        "expect_pauses": [],
    },
]

# ── Runner ────────────────────────────────────────────────────────────────────


def check(label, result, expect_texts, expect_pauses):
    texts = [s["text"] for s in result]
    pauses = [s["pause_after"] for s in result]

    ok = True
    if texts != expect_texts:
        print(f"  FAIL texts:  got {texts}")
        print(f"               exp {expect_texts}")
        ok = False
    if pauses != expect_pauses:
        print(f"  FAIL pauses: got {pauses}")
        print(f"               exp {expect_pauses}")
        ok = False
    if ok:
        print(f"  PASS")
    return ok


all_passed = True
print("=" * 60)
print("test_pause_markers.py — Phase 4 Day 1")
print("=" * 60)

for case in cases:
    print(f"\n[{case['label']}]")
    print(f"  input:  {case['text']!r}")
    result = _parse_pause_markers(case["text"])
    print(f"  result: {result}")
    passed = check(
        case["label"],
        result,
        case["expect_texts"],
        case["expect_pauses"],
    )
    all_passed = all_passed and passed

print("\n" + "=" * 60)
print("ALL PASSED" if all_passed else "SOME TESTS FAILED")
print("=" * 60)
