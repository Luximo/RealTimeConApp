"""Reads/merges the two .txt files into ordered (speaker, line) turns."""

import logging
from pathlib import Path

import config

logger = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_lines(path: Path) -> list:
    """Return non-empty stripped lines from a script file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def _merge_short(lines: list, threshold: int) -> list:
    """
    Merge any line under `threshold` words with the immediately following line.
    Applied per-speaker before interleaving (Rule 3).
    If the short line is the last one with no successor, it stays as-is.
    """
    merged = []
    i = 0
    while i < len(lines):
        word_count = len(lines[i].split())
        if word_count < threshold and i + 1 < len(lines):
            merged.append(lines[i] + ", " + lines[i + 1])
            i += 2
        else:
            merged.append(lines[i])
            i += 1
    return merged


def _estimate_gen_time(speaker: str, text: str) -> float:
    """
    Estimate wall-clock generation time (seconds) for one turn.
    Uses Phase 2 RTF numbers and a fixed speech-rate estimate.
    """
    word_count = len(text.split())
    if word_count < 8:
        bucket = "short"
    elif word_count <= 30:
        bucket = "medium"
    else:
        bucket = "long"

    rtf            = config.RTF[speaker][bucket]
    estimated_audio = word_count / config.WORDS_PER_SECOND
    return estimated_audio * rtf


def _build_chunk(idx: int, turns: list) -> dict:
    """Package a list of turns into a chunk dict with all metadata a worker needs."""
    return {
        "chunk_idx":        idx,
        "turns":            turns,                        # [(speaker, text), ...]
        "speaker1_ref":     str(config.SPEAKER1_REF),
        "speaker2_ref":     str(config.SPEAKER2_REF),
        "speaker1_settings": config.SPEAKER1_SETTINGS,
        "speaker2_settings": config.SPEAKER2_SETTINGS,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def parse_script(s1_path=None, s2_path=None, num_workers=None) -> list:
    """
    Read two speaker script files and return a list of chunk dicts.

    Each chunk:
        {
            "chunk_idx":         int,
            "turns":             [("S1"|"S2", text), ...],
            "speaker1_ref":      str,
            "speaker2_ref":      str,
            "speaker1_settings": dict,
            "speaker2_settings": dict,
        }

    Rules applied (see Phase3.md):
        1  Turns are atomic — never split mid-turn.
        2  Chunk by estimated generation time, not word count.
        3  Merge turns under SHORT_TURN_WORD_THRESHOLD words with next same-speaker turn.
        4  Cut only at turn boundaries.
        5  Strict S1/S2 alternation guarantees speaker alternation at every seam.
        6  Every chunk carries its own metadata — workers are fully self-contained.
    """
    s1_path     = Path(s1_path    or config.SPEAKER1_SCRIPT)
    s2_path     = Path(s2_path    or config.SPEAKER2_SCRIPT)
    num_workers = num_workers or config.NUM_WORKERS

    # Load raw lines
    s1_lines = _load_lines(s1_path)
    s2_lines = _load_lines(s2_path)

    # Warn and truncate on unequal lengths — never silently drop turns (Rule 1)
    if len(s1_lines) != len(s2_lines):
        logger.warning(
            "Line count mismatch: speaker1=%d lines, speaker2=%d lines. "
            "Stopping at the shorter file.",
            len(s1_lines), len(s2_lines),
        )
    n        = min(len(s1_lines), len(s2_lines))
    s1_lines = s1_lines[:n]
    s2_lines = s2_lines[:n]

    # Merge short turns per speaker before interleaving (Rule 3)
    threshold = config.SHORT_TURN_WORD_THRESHOLD
    s1_lines  = _merge_short(s1_lines, threshold)
    s2_lines  = _merge_short(s2_lines, threshold)

    # Interleave into strict S1, S2, S1, S2 ... turn list
    turns = []
    for s1, s2 in zip(s1_lines, s2_lines):
        turns.append(("S1", s1))
        turns.append(("S2", s2))

    # Chunk by estimated generation time (Rules 2, 4, 5)
    total_time  = sum(_estimate_gen_time(spk, txt) for spk, txt in turns)
    target_time = total_time / num_workers

    chunks       = []
    current      = []
    current_time = 0.0

    for turn in turns:
        spk, txt = turn
        t = _estimate_gen_time(spk, txt)
        current.append(turn)
        current_time += t

        # Cut when we reach the target — but never create more than num_workers chunks.
        # Rule 4: we just finished a complete turn, so this is always a clean boundary.
        # Rule 5: strict alternation means the next turn is always the other speaker.
        if current_time >= target_time and len(chunks) < num_workers - 1:
            chunks.append(_build_chunk(len(chunks), current))
            current      = []
            current_time = 0.0

    if current:
        chunks.append(_build_chunk(len(chunks), current))

    return chunks