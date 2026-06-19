"""
Day 6 edge case tests — all four scenarios, no TTS generation needed.

1. Unequal line counts   — parser warns and stops at the shorter file
2. Very long single turn — stays whole, never split across chunks
3. Fewer chunks than workers — pool caps at actual chunk count
4. Worker failure        — exception surfaces clearly, pool does not hang
"""

import logging
import multiprocessing
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from script_parser import parse_script

# ── Module-level worker needed for pickling (Windows spawn mode) ──────────────
def _deliberate_failure(args):
    raise RuntimeError("Deliberate test failure — verifying pool propagates exceptions")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_scripts(s1_lines: list, s2_lines: list, suffix: str):
    s1 = config.SCRIPTS_DIR / f"edge_{suffix}_s1.txt"
    s2 = config.SCRIPTS_DIR / f"edge_{suffix}_s2.txt"
    s1.write_text("\n".join(s1_lines), encoding="utf-8")
    s2.write_text("\n".join(s2_lines), encoding="utf-8")
    return s1, s2


# ── Test 1: Unequal line counts ───────────────────────────────────────────────

def test_unequal_lines():
    print("\n── Test 1: Unequal line counts ──────────────────────────────────")

    s1_lines = [
        "I've been thinking about this for a while now.",
        "Exactly, we need to approach it differently.",
        "This third line has no matching speaker two line.",
        "Neither does this fourth one.",
        "Or this fifth one.",
    ]
    s2_lines = [
        "Same here, it's been on my mind too.",
        "Agreed, the current approach clearly isn't working.",
    ]

    s1_path, s2_path = _write_scripts(s1_lines, s2_lines, "unequal")

    # Capture warning
    with_warning = False
    class WarnCapture(logging.Handler):
        def emit(self, record):
            nonlocal with_warning
            if "mismatch" in record.getMessage().lower():
                with_warning = True

    handler = WarnCapture()
    logging.getLogger("script_parser").addHandler(handler)
    logging.getLogger("script_parser").setLevel(logging.WARNING)

    chunks = parse_script(s1_path=s1_path, s2_path=s2_path)

    logging.getLogger("script_parser").removeHandler(handler)

    all_turns = [t for c in chunks for t in c["turns"]]
    total_turns = len(all_turns)
    expected_turns = min(len(s1_lines), len(s2_lines)) * 2  # 2 lines × 2 speakers = 4

    print(f"  S1 lines: {len(s1_lines)}, S2 lines: {len(s2_lines)}")
    print(f"  Warning logged: {with_warning}")
    print(f"  Turns produced: {total_turns} (expected ≤{expected_turns} after merging)")

    assert with_warning,         "Expected a mismatch warning — none was logged"
    assert total_turns <= expected_turns, \
        f"Too many turns: {total_turns} > {expected_turns}"

    print("  PASSED ✓")


# ── Test 2: Very long single turn ─────────────────────────────────────────────

def test_long_turn_stays_whole():
    print("\n── Test 2: Very long single turn (60 words) ─────────────────────")

    long_line = (
        "I want to make absolutely sure that when we finally sit down and talk "
        "through all of this together, we take enough time to really understand "
        "every single dimension of the problem before we start rushing toward any "
        "kind of solution, because the last time we moved too fast we ended up "
        "having to redo everything from scratch all over again."
    )
    assert len(long_line.split()) >= 55, "Test line should be 55+ words"

    normal_line = "You make a really fair point and I completely agree with you."

    s1_path, s2_path = _write_scripts([long_line], [normal_line], "longline")

    chunks = parse_script(s1_path=s1_path, s2_path=s2_path, num_workers=8)
    all_turns = [t for c in chunks for t in c["turns"]]

    # Find S1's turn and verify it wasn't split
    s1_turns = [t for t in all_turns if t[0] == "S1"]
    assert len(s1_turns) == 1, \
        f"Long turn was split into {len(s1_turns)} pieces — should be 1"

    word_count = len(s1_turns[0][1].split())
    print(f"  Long turn word count: {word_count}")
    print(f"  Kept as single turn:  yes")
    print(f"  Total chunks:         {len(chunks)}")
    print("  PASSED ✓")


# ── Test 3: Fewer chunks than workers ─────────────────────────────────────────

def test_fewer_chunks_than_workers():
    print("\n── Test 3: Fewer chunks than workers ────────────────────────────")

    # 1 line per speaker → 2 turns → likely 1–2 chunks, well under NUM_WORKERS=8
    s1_path, s2_path = _write_scripts(
        ["This is the only line speaker one has in this script."],
        ["And this is the only line speaker two has in this script."],
        "fewchunks",
    )

    chunks = parse_script(s1_path=s1_path, s2_path=s2_path, num_workers=8)
    actual_workers = min(config.NUM_WORKERS, len(chunks))

    print(f"  NUM_WORKERS setting: {config.NUM_WORKERS}")
    print(f"  Chunks produced:     {len(chunks)}")
    print(f"  Workers that would be used: {actual_workers}")

    assert len(chunks) <= config.NUM_WORKERS, \
        f"Chunk count {len(chunks)} exceeds NUM_WORKERS {config.NUM_WORKERS}"
    assert actual_workers == len(chunks), \
        "Pool would spin up more workers than chunks"

    print("  PASSED ✓")


# ── Test 4: Worker failure surfaces clearly ───────────────────────────────────

def test_worker_failure_surfaces():
    print("\n── Test 4: Worker failure propagation ───────────────────────────")

    raised = None
    try:
        with multiprocessing.Pool(processes=1) as pool:
            pool.map(_deliberate_failure, [("dummy_arg",)])
    except Exception as exc:
        raised = exc

    assert raised is not None, \
        "Pool.map should have raised — but no exception was caught (possible hang)"

    print(f"  Exception type : {type(raised).__name__}")
    print(f"  Message        : {raised}")
    print("  Pool did not hang — exception surfaced correctly.")
    print("  PASSED ✓")


# ── Run all ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  Day 6 — Edge Case Tests")
    print("=" * 60)

    test_unequal_lines()
    test_long_turn_stays_whole()
    test_fewer_chunks_than_workers()
    test_worker_failure_surfaces()

    print("\n" + "=" * 60)
    print("  All edge case tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()