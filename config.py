"""Paths, constants, default settings (speed, pause length, etc.)."""

from pathlib import Path

# ── Directories ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
SCRIPTS_DIR = BASE_DIR / "scripts"
OUTPUT_DIR = BASE_DIR / "output"

# ── Script & reference clip paths ─────────────────────────────────────────────
SPEAKER1_SCRIPT = SCRIPTS_DIR / "speaker1.txt"
SPEAKER2_SCRIPT = SCRIPTS_DIR / "speaker2.txt"
SPEAKER1_REF = SCRIPTS_DIR / "speaker1_ref.wav"
SPEAKER2_REF = SCRIPTS_DIR / "speaker2_ref.wav"

# ── Per-speaker generation settings (tuned in Phase 2, Day 4) ─────────────────
SPEAKER1_SETTINGS = {"exaggeration": 0.6, "cfg_weight": 0.4, "temperature": 0.85}
SPEAKER2_SETTINGS = {"exaggeration": 0.7, "cfg_weight": 0.5, "temperature": 0.90}

# ── Parallel workers ──────────────────────────────────────────────────────────
NUM_WORKERS = 8  # matches Ryzen 7 5700G core count; tune down in config if RAM pressure

# ── Pause durations between turns (seconds) ───────────────────────────────────
INTER_SPEAKER_PAUSE = 0.3  # gap between different speakers
SAME_SPEAKER_PAUSE = 0.15  # gap between consecutive same-speaker turns
TURN_FADE_IN_MS = 25  # ms fade-in on each clip to eliminate leading plosives

# ── Mid-turn pause marker durations (seconds) ─────────────────────────────────
DEFAULT_PAUSE_DURATION = 0.5  # [pause]        — no argument
SHORT_PAUSE_DURATION = 0.3  # [pause:short]
LONG_PAUSE_DURATION = 3.0  # [pause:long]

# ── Silence trimming ──────────────────────────────────────────────────────────
SILENCE_THRESH_DB = -45  # dBFS below which audio is treated as silence
SILENCE_MIN_MS = 150  # minimum silence duration to detect and trim (ms)

# ── Chunking ──────────────────────────────────────────────────────────────────
SHORT_TURN_WORD_THRESHOLD = 8  # turns below this get merged with next same-speaker turn

# ── RTF estimates per speaker per word-count bucket (Phase 2, Day 5) ──────────
# Used only for chunk time estimation, not actual generation.
# Buckets: short = <8 words, medium = 8–30 words, long = >30 words
RTF = {
    "S1": {"short": 23.27, "medium": 10.36, "long": 8.13},
    "S2": {"short": 14.50, "medium": 9.05, "long": 8.24},
}

WORDS_PER_SECOND = 2.5  # rough speech rate used to estimate audio duration per turn


# ── Playback & display (Phase 5) ──────────────────────────────────────────────
MIN_SPEED = 0.5
MAX_SPEED = 2.0
DEFAULT_SPEED = 1.0

CAPTION_FONT_FAMILY = "Segoe UI"
CAPTION_FONT_SIZE = 28  # points
SCROLL_SPEED_BASE = 120  # pixels per second at 1.0x
SPEAKER_LABEL_DISPLAY_DURATION = 1.0  # seconds the speaker label shows per transition
