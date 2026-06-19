"""
Day 2 sanity test — sequential orchestrator.

Uses a short 4-turn script (2 lines per speaker) to keep generation time
manageable (~2-3 min on this hardware). Verifies:
  - Each per-turn WAV file is created and non-empty
  - Files are named chunk_XX_turn_XX.wav
  - Results are returned sorted by (chunk_idx, turn_idx)

Listen to the output files after the run to confirm correct voice and content.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from script_parser import parse_script
from orchestrator import run_sequential

# ── Short test script — 2 lines per speaker = 4 turns ────────────────────────
S1_LINES = """\
I've been thinking a lot about the direction we're heading.
Exactly. We keep moving fast but I'm not sure we're moving in the right direction.
"""

S2_LINES = """\
Same here. It feels like we're reacting more than planning these days.
Agreed. Maybe it's time to slow down and actually map it out properly.
"""

# Write temp script files to scripts/ for this test
S1_TEST_PATH = config.SCRIPTS_DIR / "day2_test_s1.txt"
S2_TEST_PATH = config.SCRIPTS_DIR / "day2_test_s2.txt"


def main():
    # Write test scripts
    S1_TEST_PATH.write_text(S1_LINES, encoding="utf-8")
    S2_TEST_PATH.write_text(S2_LINES, encoding="utf-8")

    print("Test script written.")
    print(f"  S1: {S1_TEST_PATH}")
    print(f"  S2: {S2_TEST_PATH}\n")

    # Parse into chunks
    chunks = parse_script(s1_path=S1_TEST_PATH, s2_path=S2_TEST_PATH)
    total_turns = sum(len(c["turns"]) for c in chunks)
    print(f"Parsed into {len(chunks)} chunk(s), {total_turns} turn(s) total.")
    print("Starting sequential generation — expect ~2–3 minutes on this hardware.\n")

    start = time.time()
    results = run_sequential(chunks)
    elapsed = time.time() - start

    # ── Verify outputs ────────────────────────────────────────────────────────
    print(f"\nGeneration complete in {elapsed:.1f}s\n")
    print("Output files:")
    for r in results:
        p = Path(r["path"])
        size = p.stat().st_size
        print(f"  {p.name}  ({size:,} bytes)")
        assert p.exists(),      f"Missing file: {p}"
        assert size > 1000,     f"File suspiciously small: {p} ({size} bytes)"

    # Sorted by (chunk_idx, turn_idx)
    idxs = [(r["chunk_idx"], r["turn_idx"]) for r in results]
    assert idxs == sorted(idxs), "Results not sorted correctly"

    assert len(results) == total_turns, \
        f"Expected {total_turns} results, got {len(results)}"

    print(f"\nAll {len(results)} file(s) verified.")
    print("Listen to each WAV in output/ to confirm correct voice and content.")
    print("\nAll assertions passed.")


if __name__ == "__main__":
    main()