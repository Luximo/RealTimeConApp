"""
Day 5 — Phase 4: visual sync verification via terminal simulation.

Plays conversation_final.wav while printing each word at its captions.json
start timestamp — simulating exactly what Phase 5's GUI will do, without
any GUI yet.

What to watch for:
  - Words should appear in sync with the speech you hear
  - When a [pause:N] marker was in the script, the last word before the
    pause should hold on screen for the pause duration before the next
    word appears
  - S1 lines print on the LEFT, S2 lines on the RIGHT for easy tracking

Drift report printed at the end — any consistent offset gets noted
in ARCHITECTURE.md before calling Day 5 done.

Usage:
    python tests/test_sync_terminal.py              # full audio + words
    python tests/test_sync_terminal.py --no-audio   # timing only, no sound
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config

CAPTIONS_PATH = config.OUTPUT_DIR / "captions.json"
AUDIO_PATH = config.OUTPUT_DIR / "conversation_final.wav"

# Column layout
S1_COL = 0  # S1 words start at column 0
S2_COL = 42  # S2 words start at column 42
WIDTH = 80  # total terminal width

NO_AUDIO = "--no-audio" in sys.argv


def load_captions(path: Path) -> list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def format_line(entry: dict) -> str:
    """Format one word entry as a terminal line with speaker positioning."""
    speaker = entry["speaker"]
    word = entry["word"]
    ts = f"[{entry['start']:6.2f}s]"

    if speaker == "S1":
        return f"{ts} {word}"
    else:
        pad = " " * (S2_COL - len(ts) - 1)
        return f"{ts}{pad}{word}"


def run_sync_test(captions: list):
    """
    Start audio (unless --no-audio), then print each word at its timestamp.
    Returns a list of (expected_time, actual_time) drift samples.
    """
    audio_proc = None

    if not NO_AUDIO:
        audio_proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", str(AUDIO_PATH)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    start_wall = time.perf_counter()
    drift_samples = []  # (expected_s, actual_s)

    prev_speaker = None

    for entry in captions:
        target_s = entry["start"]
        now_s = time.perf_counter() - start_wall
        wait_s = target_s - now_s

        if wait_s > 0:
            time.sleep(wait_s)

        actual_s = time.perf_counter() - start_wall
        drift_samples.append((target_s, actual_s))

        # Print speaker header on speaker change
        speaker = entry["speaker"]
        if speaker != prev_speaker:
            label = (
                "── S1 (male) ──"
                if speaker == "S1"
                else " " * S2_COL + "── S2 (female) ──"
            )
            print(f"\n{label}")
            prev_speaker = speaker

        print(format_line(entry))

    if audio_proc:
        audio_proc.wait()

    return drift_samples


def print_drift_report(samples: list):
    """Analyse timing accuracy and print a summary."""
    if not samples:
        return

    drifts = [actual - expected for expected, actual in samples]
    avg = sum(drifts) / len(drifts)
    max_d = max(drifts)
    min_d = min(drifts)

    # Check for drift growth (late words accumulate more delay)
    first_half = drifts[: len(drifts) // 2]
    second_half = drifts[len(drifts) // 2 :]
    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)
    drift_growth = avg_second - avg_first

    print("\n" + "=" * WIDTH)
    print("DRIFT REPORT")
    print("=" * WIDTH)
    print(f"  Words timed  : {len(samples)}")
    print(f"  Avg offset   : {avg*1000:+.1f} ms  (positive = printed late)")
    print(f"  Max late     : {max_d*1000:+.1f} ms")
    print(f"  Max early    : {min_d*1000:+.1f} ms")
    print(
        f"  Drift growth : {drift_growth*1000:+.1f} ms  (first→second half avg delta)"
    )

    if abs(avg) < 0.050:
        verdict = "GOOD — average offset under 50ms, well within perceptual threshold."
    elif abs(avg) < 0.150:
        verdict = "ACCEPTABLE — average offset under 150ms; visible but not jarring."
    else:
        verdict = "NOTABLE — average offset over 150ms; consider a correction pass."

    if abs(drift_growth) > 0.100:
        verdict += f"\n  NOTE: drift is growing ({drift_growth*1000:+.1f}ms) — cumulative slip across the conversation."

    print(f"\n  Verdict: {verdict}")
    print("=" * WIDTH)


# ── Main ──────────────────────────────────────────────────────────────────────

print("=" * WIDTH)
print("test_sync_terminal.py — Phase 4 Day 5")
print("=" * WIDTH)

for path, label in [
    (CAPTIONS_PATH, "captions.json"),
    (AUDIO_PATH, "conversation_final.wav"),
]:
    if not path.exists():
        print(f"ERROR: {label} not found at {path}")
        print("Run tests/test_captions_json.py first to generate captions.json.")
        sys.exit(1)

captions = load_captions(CAPTIONS_PATH)
print(f"Loaded {len(captions)} words spanning {captions[-1]['end']:.2f}s\n")

if NO_AUDIO:
    print("-- Running in --no-audio mode (timing only, no sound) --\n")
else:
    print("-- Starting playback — watch words appear in sync with speech --")
    print("   S1 (male) on the LEFT   |   S2 (female) on the RIGHT\n")

print(f"{'[time]  S1 word':<{S2_COL}}{'[time]  S2 word'}")
print("-" * WIDTH)

drift_samples = run_sync_test(captions)

print_drift_report(drift_samples)
