"""Reads/merges the two .txt files into ordered (speaker, line) turns."""

import logging
import re
from pathlib import Path

import config

logger = logging.getLogger(__name__)


# ── Pause marker regex ────────────────────────────────────────────────────────
# Matches: [pause]  [pause:0.5]  [pause:short]  [pause:long]
_PAUSE_RE = re.compile(r"\[pause(?::([^\]]*))?\]", re.IGNORECASE)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _load_lines(path: Path) -> list:
    """Return non-empty stripped lines from a script file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip()]


def _resolve_pause_duration(arg: str | None) -> float:
    """
    Convert a [pause:ARG] argument to seconds.
    arg=None  → DEFAULT_PAUSE_DURATION
    'short'   → SHORT_PAUSE_DURATION
    'long'    → LONG_PAUSE_DURATION
    '0.5' etc → float(arg)
    Unknown   → DEFAULT_PAUSE_DURATION (with warning)
    """
    if arg is None:
        return config.DEFAULT_PAUSE_DURATION
    arg_lower = arg.strip().lower()
    if arg_lower == "short":
        return config.SHORT_PAUSE_DURATION
    if arg_lower == "long":
        return config.LONG_PAUSE_DURATION
    try:
        return float(arg)
    except ValueError:
        logger.warning(
            "Unrecognized [pause:%s] argument — using default %.1fs.",
            arg,
            config.DEFAULT_PAUSE_DURATION,
        )
        return config.DEFAULT_PAUSE_DURATION


def _parse_pause_markers(text: str) -> list:
    """
    Split a turn's text at [pause:N] markers into ordered sub-clips.

    Returns a list of dicts:
        [
            {"text": "clean text segment", "pause_after": 0.5},
            {"text": "more clean text",    "pause_after": 0.0},  # last is always 0.0
        ]

    Rules:
    - Markers are stripped — Chatterbox never sees them.
    - Empty segments (consecutive markers, marker at start) are skipped; their
      pause duration is folded into the preceding sub-clip's pause_after.
    - A turn with no markers returns a single sub-clip with pause_after=0.0.
    - A turn that is ONLY markers (no words) returns an empty list — caller warns.
    - The last sub-clip always has pause_after=0.0 (inter-speaker gap handled separately).
    """
    parts = []
    last_end = 0

    for match in _PAUSE_RE.finditer(text):
        segment = text[last_end : match.start()].strip()
        duration = _resolve_pause_duration(match.group(1))

        if segment:
            parts.append({"text": segment, "pause_after": duration})
        else:
            # No text before this marker — fold its duration into the previous part
            if parts:
                parts[-1]["pause_after"] += duration
            # If parts is empty the marker is at the very start; duration is discarded
            # (nothing to hold on screen yet) — log so the author knows.
            else:
                logger.warning(
                    "Ignored [pause] at the very start of a turn (no preceding text): %r",
                    text,
                )

        last_end = match.end()

    # Text after the last marker (or the whole string if no markers)
    remaining = text[last_end:].strip()
    if remaining:
        parts.append({"text": remaining, "pause_after": 0.0})

    # If the turn was only markers with no words, parts may still be empty
    if not parts:
        return []

    # Guarantee: last sub-clip has pause_after=0.0
    parts[-1]["pause_after"] = 0.0

    return parts


def _strip_markers(text: str) -> str:
    """Return text with all [pause:N] markers removed (used for word-count estimation)."""
    return _PAUSE_RE.sub("", text).strip()


def _merge_short(lines: list, threshold: int) -> list:
    """
    Merge any line under `threshold` words with the immediately following line.
    Applied per-speaker before interleaving (Rule 3).
    Word count is measured on marker-stripped text so markers don't inflate counts.
    If the short line is the last one with no successor, it stays as-is.
    """
    merged = []
    i = 0
    while i < len(lines):
        word_count = len(_strip_markers(lines[i]).split())
        if word_count < threshold and i + 1 < len(lines):
            merged.append(lines[i] + " " + lines[i + 1])
            i += 2
        else:
            merged.append(lines[i])
            i += 1
    return merged


def _estimate_gen_time(speaker: str, text: str) -> float:
    """
    Estimate wall-clock generation time (seconds) for one turn.
    Uses Phase 2 RTF numbers and a fixed speech-rate estimate.
    Markers are stripped before counting words.
    """
    word_count = len(_strip_markers(text).split())
    if word_count < 8:
        bucket = "short"
    elif word_count <= 30:
        bucket = "medium"
    else:
        bucket = "long"

    rtf = config.RTF[speaker][bucket]
    estimated_audio = word_count / config.WORDS_PER_SECOND
    return estimated_audio * rtf


def _build_chunk(idx: int, turns: list) -> dict:
    """
    Package a list of (speaker, text) turns into a chunk dict.

    Each turn is expanded into sub-clips via _parse_pause_markers().
    Turns that reduce to zero sub-clips (only markers, no words) are warned
    and skipped to prevent empty TTS calls.

    Chunk turn format (Phase 4):
        {
            "speaker":   "S1" | "S2",
            "sub_clips": [
                {"text": "clean text", "pause_after": 0.5},
                {"text": "more text",  "pause_after": 0.0},
            ]
        }
    """
    parsed_turns = []
    for speaker, text in turns:
        sub_clips = _parse_pause_markers(text)
        if not sub_clips:
            logger.warning(
                "Turn for %s produced no speakable text after marker parsing — skipped. "
                "Original text: %r",
                speaker,
                text,
            )
            continue
        parsed_turns.append({"speaker": speaker, "sub_clips": sub_clips})

    return {
        "chunk_idx": idx,
        "turns": parsed_turns,
        "speaker1_ref": str(config.SPEAKER1_REF),
        "speaker2_ref": str(config.SPEAKER2_REF),
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
            "turns":             [
                {
                    "speaker":   "S1" | "S2",
                    "sub_clips": [{"text": str, "pause_after": float}, ...]
                },
                ...
            ],
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
    s1_path = Path(s1_path or config.SPEAKER1_SCRIPT)
    s2_path = Path(s2_path or config.SPEAKER2_SCRIPT)
    num_workers = num_workers or config.NUM_WORKERS

    # Load raw lines
    s1_lines = _load_lines(s1_path)
    s2_lines = _load_lines(s2_path)

    # Warn and truncate on unequal lengths — never silently drop turns (Rule 1)
    if len(s1_lines) != len(s2_lines):
        logger.warning(
            "Line count mismatch: speaker1=%d lines, speaker2=%d lines. "
            "Stopping at the shorter file.",
            len(s1_lines),
            len(s2_lines),
        )
    n = min(len(s1_lines), len(s2_lines))
    s1_lines = s1_lines[:n]
    s2_lines = s2_lines[:n]

    # Merge short turns per speaker before interleaving (Rule 3)
    threshold = config.SHORT_TURN_WORD_THRESHOLD
    s1_lines = _merge_short(s1_lines, threshold)
    s2_lines = _merge_short(s2_lines, threshold)

    # Interleave into strict S1, S2, S1, S2 ... turn list
    turns = []
    for s1, s2 in zip(s1_lines, s2_lines):
        turns.append(("S1", s1))
        turns.append(("S2", s2))

    # Chunk by estimated generation time (Rules 2, 4, 5)
    total_time = sum(_estimate_gen_time(spk, txt) for spk, txt in turns)
    target_time = total_time / num_workers

    chunks = []
    current = []
    current_time = 0.0

    for turn in turns:
        spk, txt = turn
        t = _estimate_gen_time(spk, txt)
        current.append(turn)
        current_time += t

        if current_time >= target_time and len(chunks) < num_workers - 1:
            chunks.append(_build_chunk(len(chunks), current))
            current = []
            current_time = 0.0

    if current:
        chunks.append(_build_chunk(len(chunks), current))

    return chunks
