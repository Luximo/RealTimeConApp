"""
Day 5 timing test — full parallel batch render on the complete sample script.

Uses scripts/speaker1.txt + speaker2.txt (10 lines per speaker = 16 turns after
merging, 7 chunks). Runs the full pipeline: parse → parallel generate → stitch.

Records:
  - Wall-clock render time
  - Parallel speedup vs sequential estimate from Day 1 (724.6s)
  - Per-chunk turn count and estimated gen time
  - Final audio duration

Results are printed and appended to ARCHITECTURE.md for the permanent record.

Expect 10–20 minutes on this hardware (7 workers competing for 8 cores).

CRITICAL: `if __name__ == "__main__":` guard is mandatory on Windows.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from script_parser import parse_script, _estimate_gen_time
from orchestrator import render_conversation

SEQUENTIAL_ESTIMATE_S = 724.6   # from Day 1 parser output


def main():
    # ── Parse full script ─────────────────────────────────────────────────────
    chunks      = parse_script()   # uses config defaults: speaker1.txt + speaker2.txt
    total_turns = sum(len(c["turns"]) for c in chunks)

    print(f"\nFull script: {len(chunks)} chunk(s), {total_turns} turn(s)")
    print(f"Sequential estimate: {SEQUENTIAL_ESTIMATE_S:.1f}s\n")

    print("Chunk layout:")
    for chunk in chunks:
        chunk_time = sum(_estimate_gen_time(spk, txt) for spk, txt in chunk["turns"])
        speakers   = " ".join(spk for spk, _ in chunk["turns"])
        print(f"  Chunk {chunk['chunk_idx']}: {len(chunk['turns'])} turn(s) "
              f"[{speakers}]  ~{chunk_time:.1f}s est.")

    print(f"\nStarting render — expect 10–20 min on this hardware ...\n")

    # ── Run full pipeline ─────────────────────────────────────────────────────
    start      = time.time()
    final_path = render_conversation(chunks)
    elapsed    = time.time() - start

    speedup = SEQUENTIAL_ESTIMATE_S / elapsed

    # ── Measure output duration ───────────────────────────────────────────────
    from pydub import AudioSegment
    final_audio    = AudioSegment.from_wav(str(final_path))
    audio_duration = len(final_audio) / 1000.0   # ms → seconds

    # ── Print results ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  FULL RENDER RESULTS — Phase 3, Day 5")
    print(f"{'='*60}")
    print(f"  Script          : {total_turns} turns, {len(chunks)} chunks")
    print(f"  Workers used    : {min(config.NUM_WORKERS, len(chunks))}")
    print(f"  Wall-clock time : {elapsed:.1f}s  ({elapsed/60:.1f} min)")
    print(f"  Sequential est. : {SEQUENTIAL_ESTIMATE_S:.1f}s")
    print(f"  Parallel speedup: {speedup:.2f}x")
    print(f"  Output audio    : {audio_duration:.2f}s")
    print(f"  Output file     : {final_path}")
    print(f"{'='*60}\n")

    # ── Verify output ─────────────────────────────────────────────────────────
    assert final_path.exists(),                 "conversation_final.wav not created"
    assert final_path.stat().st_size > 100_000, "Output file suspiciously small"
    assert audio_duration > 30.0,               f"Audio too short: {audio_duration:.2f}s"

    print("All assertions passed.")
    print(f"\nListen to: {final_path}")
    print("Check: natural flow, correct voices, no seam artifacts at chunk boundaries.\n")

    # ── Write results to ARCHITECTURE.md ─────────────────────────────────────
    arch_path = config.BASE_DIR / "docs" / "ARCHITECTURE.md"
    if not arch_path.exists():
        arch_path = config.BASE_DIR / "ARCHITECTURE.md"

    entry = f"""
## Parallel Batch Render Timing (Phase 3, Day 5)

Full pipeline test on the complete sample script (speaker1.txt + speaker2.txt).

| Metric              | Value                        |
|---------------------|------------------------------|
| Total turns         | {total_turns}                            |
| Chunks              | {len(chunks)}                             |
| Workers used        | {min(config.NUM_WORKERS, len(chunks))}                             |
| Wall-clock time     | {elapsed:.1f}s ({elapsed/60:.1f} min)         |
| Sequential estimate | {SEQUENTIAL_ESTIMATE_S:.1f}s                       |
| Parallel speedup    | {speedup:.2f}x                         |
| Output audio length | {audio_duration:.2f}s                      |
| Inter-speaker pause | {config.INTER_SPEAKER_PAUSE}s (tuned Day 4)           |

**Key implication for longer scripts:**
At {speedup:.2f}x speedup on a {total_turns}-turn script, a 60-turn (~10 min audio)
conversation would render in roughly {(SEQUENTIAL_ESTIMATE_S / total_turns * 60 / speedup / 60):.1f} min wall-clock time.
"""

    with open(arch_path, "a", encoding="utf-8") as f:
        f.write(entry)

    print(f"Results appended to {arch_path.name}")


if __name__ == "__main__":
    main()