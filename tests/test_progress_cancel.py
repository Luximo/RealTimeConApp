"""
Day 3 verification — cancel Event behaviour.

Sets cancel_event before render starts. Workers load models (~1-2 min),
then immediately cancel on turn 0 before any TTS call.

Expected:
  - render_conversation returns None
  - No chunk WAV files left in the output dir
  - Progress queue received 0 events (cancelled before any turn completed)

Uses a temp dir so existing output files are never touched.
"""

import sys
import multiprocessing
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from script_parser import parse_script
from orchestrator import render_conversation


def test_cancel():
    print("\n── Cancel test: cancel_event set before render ──────────────────")
    chunks = parse_script()
    total_turns = sum(len(c["turns"]) for c in chunks)
    print(f"Script: {len(chunks)} chunks, {total_turns} turns")

    cancel_event = multiprocessing.Event()
    progress_queue = multiprocessing.Queue()

    cancel_event.set()  # set BEFORE render — workers cancel on their first turn
    print("cancel_event pre-set. Workers will exit before turn 0.\n")
    print("(Model loading still takes ~1-2 min — waiting ...)\n")

    with tempfile.TemporaryDirectory() as tmp_dir:
        result = render_conversation(
            chunks,
            output_dir=Path(tmp_dir),
            cancel_event=cancel_event,
            progress_queue=progress_queue,
        )

        # 1 — return value must be None
        assert result is None, f"Expected None on cancel, got {result}"
        print("✅ render_conversation returned None")

        # 2 — no partial chunk files left behind
        chunk_files = list(Path(tmp_dir).glob("chunk_*.wav"))
        assert (
            len(chunk_files) == 0
        ), f"Expected 0 chunk files, found {len(chunk_files)}: {chunk_files}"
        print("✅ Temp output dir clean — no partial chunk files")

    # 3 — queue should have 0 events (no turn completed before cancel)
    events = []
    while not progress_queue.empty():
        events.append(progress_queue.get_nowait())
    assert len(events) == 0, f"Expected 0 queue events, got {len(events)}"
    print(f"✅ Progress queue: {len(events)} event(s) received (expected 0)")

    print("\nAll cancel checks passed.\n")


if __name__ == "__main__":
    test_cancel()
