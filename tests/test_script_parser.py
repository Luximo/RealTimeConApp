"""
Sanity test for script_parser.py — Day 1, Phase 3.

Prints the full chunk layout for the sample script so we can visually verify:
  - Turn order is preserved (S1, S2, S1, S2 ...)
  - No mid-turn cuts
  - Short turns were merged before chunking
  - Speaker alternation holds at every chunk seam
  - Chunk count does not exceed NUM_WORKERS
"""

import logging
import sys
from pathlib import Path

# Make sure project root is on the path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from script_parser import parse_script, _estimate_gen_time

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


def main():
    chunks = parse_script()

    print(f"\n{'='*60}")
    print(f"  Script parsed into {len(chunks)} chunk(s)  (max workers: {config.NUM_WORKERS})")
    print(f"{'='*60}")

    grand_total_estimated = 0.0

    for chunk in chunks:
        idx   = chunk["chunk_idx"]
        turns = chunk["turns"]
        chunk_time = sum(_estimate_gen_time(spk, txt) for spk, txt in turns)
        grand_total_estimated += chunk_time

        print(f"\n── Chunk {idx}  ({len(turns)} turn(s), ~{chunk_time:.1f}s estimated gen time) ──")
        for i, (spk, txt) in enumerate(turns):
            word_count = len(txt.split())
            print(f"  [{i}] {spk} ({word_count:2d} words): {txt[:70]}{'...' if len(txt) > 70 else ''}")

    print(f"\n{'='*60}")
    print(f"  Total turns : {sum(len(c['turns']) for c in chunks)}")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Est. total gen time (sequential): {grand_total_estimated:.1f}s")
    print(f"  Est. wall time (parallel, {config.NUM_WORKERS} workers): "
          f"~{grand_total_estimated / config.NUM_WORKERS:.1f}s")
    print(f"{'='*60}\n")

    # ── Assertions ──────────────────────────────────────────────────────────
    assert len(chunks) <= config.NUM_WORKERS, \
        f"Too many chunks: {len(chunks)} > {config.NUM_WORKERS}"

    # Verify strict S1/S2 alternation across the entire interleaved turn list
    all_turns = [turn for chunk in chunks for turn in chunk["turns"]]
    for i in range(1, len(all_turns)):
        prev_spk = all_turns[i - 1][0]
        curr_spk = all_turns[i][0]
        assert prev_spk != curr_spk, \
            f"Speaker alternation broken at global turn {i}: {prev_spk} followed by {curr_spk}"

    print("All assertions passed.")


if __name__ == "__main__":
    main()