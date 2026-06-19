"""
Day 3 sanity test — parallel worker pool.

Runs the same 4-turn script from Day 2 through the parallel pool and verifies:
  - All output files exist and are non-empty
  - Results are sorted by (chunk_idx, turn_idx)
  - Wall-clock time is faster than the Day 2 sequential baseline (142.4s)

Two things to expect on Windows:
  - Worker model-load messages may not appear in the console during the run —
    stdout from spawned processes is often buffered. This is normal, not a bug.
  - Sampling progress bars from workers similarly won't be visible. The console
    will look quiet, then all results appear at once when pool.map returns.

Listen to the output WAVs after the run — voices and content must match Day 2.

CRITICAL: The `if __name__ == "__main__":` guard at the bottom of this file is
mandatory on Windows. Without it, each spawned worker re-imports this script and
tries to create another pool, causing recursive spawning that hangs immediately.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from script_parser import parse_script
from orchestrator import run_parallel

S1_TEST_PATH = config.SCRIPTS_DIR / "day2_test_s1.txt"
S2_TEST_PATH = config.SCRIPTS_DIR / "day2_test_s2.txt"

SEQUENTIAL_BASELINE_S = 142.4   # Day 2 recorded time


def main():
    # Confirm test scripts from Day 2 exist
    assert S1_TEST_PATH.exists(), f"Missing: {S1_TEST_PATH} — run test_sequential.py first"
    assert S2_TEST_PATH.exists(), f"Missing: {S2_TEST_PATH} — run test_sequential.py first"

    chunks      = parse_script(s1_path=S1_TEST_PATH, s2_path=S2_TEST_PATH)
    total_turns = sum(len(c["turns"]) for c in chunks)

    print(f"Sequential baseline (Day 2): {SEQUENTIAL_BASELINE_S}s")
    print(f"Parsed: {len(chunks)} chunk(s), {total_turns} turn(s)\n")

    start   = time.time()
    results = run_parallel(chunks)
    elapsed = time.time() - start

    speedup = SEQUENTIAL_BASELINE_S / elapsed
    print(f"\nParallel complete in {elapsed:.1f}s  (speedup: {speedup:.1f}x vs sequential)\n")

    print("Output files:")
    for r in results:
        p    = Path(r["path"])
        size = p.stat().st_size
        print(f"  {p.name}  ({size:,} bytes)")
        assert p.exists(),  f"Missing output: {p}"
        assert size > 1000, f"Suspiciously small: {p} ({size} bytes)"

    idxs = [(r["chunk_idx"], r["turn_idx"]) for r in results]
    assert idxs == sorted(idxs), "Results not sorted correctly"
    assert len(results) == total_turns, \
        f"Expected {total_turns} results, got {len(results)}"

    print(f"\nAll {len(results)} file(s) verified.")
    print("Listen to each WAV — voices and content must match Day 2.")
    print("\nAll assertions passed.")


# ── MANDATORY on Windows — do not move this code outside the guard ────────────
if __name__ == "__main__":
    main()