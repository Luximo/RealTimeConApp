# Phase 4 — Caption Timing & Pause Markers

**Project:** RealTimeConApp
**Branch for this phase:** `phase4-caption-timing` (off `main`)

## Goal

Produce word-level timestamps for every spoken word in `conversation_final.wav` —
without any transcription model — by deriving them directly from the `.txt` files and
audio clip durations captured during stitching. Also add `[pause:N]` marker support
to `script_parser.py` so mid-turn silences can be scripted naturally. By the end of
this phase, `captions.json` exists, is accurate, and the caption display layer in
Phase 5 has everything it needs to scroll words in sync with the audio.

## Core Design Decision (replaces the faster-whisper approach)

We already know exactly what every word is — we wrote the script. Running a
transcription model to re-discover that same text from audio we just synthesized
from it is redundant. Instead:

- `audio_utils.py` tracks the absolute start time of every clip as it stitches
- Word timestamps are derived proportionally from clip duration ÷ word count
- Words come directly from the `.txt` files — no guessing, no transcription
- `[pause:N]` markers in the script produce real silence gaps in the audio, and
  their timestamps map to holds in the caption display

This is faster, simpler, fully offline, and produces timestamps that are guaranteed
to be grounded in the actual audio structure rather than inferred from it.

## What Phase 3 Already Confirmed (don't re-investigate)

- `audio_utils.py` already concatenates clips with silence gaps between turns
- Silence trimming (-45dBFS, 150ms) and 25ms fade-in are already applied per clip
- Inter-speaker pause is 0.3s — already inserted between turns by `audio_utils.py`
- Merge separator is a space `" "` — comma caused unnatural mid-turn TTS pauses
- All clip durations are known at stitch time — this is the timing source for Phase 4

## Pause Marker Format

`[pause:N]` markers go directly in the `.txt` files, inline within a turn's text.
`N` is seconds (integer or float). Examples:

```
# scripts/speaker1.txt
Well I mean [pause:0.5] okay hold on [pause:3] maybe we do it this way
or talk to Sarah about our plan like this
That bad, huh?

# scripts/speaker2.txt
Don't even get me started.
Honestly yes [pause:1] the whole thing was a mess from start to finish.
I know I know. But here we are.
```

**What `script_parser.py` does with `[pause:N]`:**
- Splits the turn text at each marker into separate sub-clips
- Passes each sub-clip to the TTS engine as its own generation call
- Records the pause duration between sub-clips for `audio_utils.py` to insert
- Strips the marker from the text before sending to Chatterbox — it never
  sees `[pause:N]`, only clean words

**What `audio_utils.py` does with pauses:**
- Inserts exactly N seconds of silence between the sub-clips of a split turn
- Treats this silence identically to any other gap — just a chunk of zeros
  at the correct sample rate

**Supported shorthand (defined in `config.py`):**
```
[pause]       →  config.DEFAULT_PAUSE_DURATION   (default: 0.5s)
[pause:short] →  config.SHORT_PAUSE_DURATION     (default: 0.3s)
[pause:long]  →  config.LONG_PAUSE_DURATION      (default: 3.0s)
[pause:N]     →  N seconds exactly (float or int)
```

## Timestamp Derivation (how captions.json gets built)

`audio_utils.py` already processes clips in order during stitching. Phase 4 extends
that pass to also emit timestamps. The logic per clip:

1. Record `clip_start` = current absolute position in the final audio (seconds)
2. Measure `clip_duration` = length of this clip in seconds (known from the audio)
3. Split the clip's clean text into words
4. Distribute timestamps proportionally:
   `word_start = clip_start + (word_index / word_count) * clip_duration`
   `word_end   = clip_start + ((word_index + 1) / word_count) * clip_duration`
5. Emit one JSON entry per word
6. Advance `clip_start` by `clip_duration + pause_after` before the next clip

**For `[pause:N]` gaps within a turn:**
- The silence maps to a hold in the caption — last word of the pre-pause sub-clip
  stays displayed on screen for N seconds, then the next sub-clip's words begin
- No word entry is emitted for the silence itself — just a gap in the timestamps

## Output Format

`output/captions.json` — one entry per word, globally ordered:

```json
[
  {"word": "Did",       "start": 0.00,  "end": 0.31,  "speaker": "S1"},
  {"word": "you",       "start": 0.31,  "end": 0.52,  "speaker": "S1"},
  {"word": "catch",     "start": 0.52,  "end": 0.78,  "speaker": "S1"},
  {"word": "the",       "start": 0.78,  "end": 0.89,  "speaker": "S1"},
  {"word": "news",      "start": 0.89,  "end": 1.14,  "speaker": "S1"},
  {"word": "today",     "start": 1.14,  "end": 1.52,  "speaker": "S1"},
  {"word": "Don't",     "start": 1.82,  "end": 2.20,  "speaker": "S2"},
  ...
]
```

Speaker label is included here — Phase 5 needs it to know when to clear the screen
and start a new speaker block. It does NOT come from transcription; it comes directly
from the turn metadata already tracked in `script_parser.py`.

The 0.3s gap between S1's last word (end: 1.52) and S2's first word (start: 1.82)
is the `INTER_SPEAKER_PAUSE` — Phase 5 uses that gap to trigger the screen clear
and visual break between speakers.

## How the Three Files Divide the New Work

```
script_parser.py  — parse [pause:N] markers, split turns into sub-clips,
                    pass clean text and pause durations downstream

audio_utils.py    — insert pause silences between sub-clips during stitching,
                    track absolute timestamps per clip, emit captions.json

captions.py       — thin wrapper: accepts audio path + turn metadata,
                    calls audio_utils timestamp logic, writes captions.json
                    (keeps captions.py as the single entry point Phase 5 imports)
```

`captions.py` stays in the project as a clean module boundary — Phase 5 imports
from it, not directly from `audio_utils.py`. But the actual timestamp math lives
in `audio_utils.py` where the clip durations are already known.

## Day-by-Day Plan

### Day 1 — Branch + Pause Marker Parsing
- [x] Create and switch to `phase4-caption-timing`
- [x] Extend `script_parser.py` to detect and handle `[pause:N]` markers:
  - Split turns at each marker into ordered sub-clips + pause durations
  - Strip markers from text before any TTS call
  - Support all four formats: `[pause]`, `[pause:short]`, `[pause:long]`, `[pause:N]`
  - Add constants to `config.py`: `DEFAULT_PAUSE_DURATION`, `SHORT_PAUSE_DURATION`,
    `LONG_PAUSE_DURATION`
- [x] Write a test in `tests/` that feeds a script with multiple pause markers and
  prints the resulting sub-clip + pause sequence — verify markers are stripped,
  pause durations are correct, surrounding words are intact

**Checkpoint:** parser test correctly splits turns, strips markers, and reports
pause durations for all four supported formats. ✅
**Commit:** "Day 1: [pause:N] marker parsing implemented and tested"

### Day 2 — Pause Silence Insertion in audio_utils.py
- [x] Extend `audio_utils.py` to accept sub-clips and pause durations per turn
- [x] Insert correct silence duration between sub-clips of a split turn
- [x] Verify the inserted silence is the right length (measure output file duration)
- [x] Listen to a test render with a few `[pause:N]` markers — silence confirmed
  at correct moments

**Checkpoint:** stitched audio contains correctly-timed silences (0ms error on
0.5s, 1.0s, 3.0s tests; inter-turn pause_after correctly ignored at boundaries). ✅
**Commit:** "Day 2: pause silence insertion verified in stitched audio"

### Day 3 — Timestamp Derivation in audio_utils.py
- [x] Extend `audio_utils.py`'s stitching pass to track absolute clip start times
- [x] Implement proportional word timestamp distribution per clip
- [x] Handle `[pause:N]` gaps correctly — last pre-pause word holds, next sub-clip
  starts after the silence
- [x] Write intermediate output to confirm timestamps look reasonable before
  writing the final JSON — first 20 entries printed to terminal

**Checkpoint:** first 20 timestamp entries printed and verified. Intra-turn pause
gap = 1.000s (exact), inter-turn gap = 0.300s (exact). 7/7 checks passed. ✅
**Commit:** "Day 3: timestamp derivation implemented"

### Day 4 — captions.json Output + captions.py Wrapper
- [x] Implement `captions.py` as a clean entry point
- [x] Run against Phase 3 output WAVs via reconstructed results
- [x] Verified: 187 words, ascending timestamps, correct speaker labels,
  no overlaps, start < end for every entry, final timestamp 63.37s

**Checkpoint:** `captions.json` exists, all 11 structural checks passed. ✅
**Commit:** "Day 4: captions.json output verified"

### Day 5 — Visual Sync Verification
- [x] Wrote terminal sync test — plays audio while printing words at timestamps
- [x] Python timing accuracy: +0.2ms average, 0ms drift growth — excellent
- [x] Proportional distribution is approximate by design; turn-level sync acceptable
- [x] Observed: captions/audio must share the same pipeline pass to avoid drift
- [x] Findings documented in ARCHITECTURE.md

**Checkpoint:** timing accuracy confirmed. Perceptual sync finding documented. ✅
**Commit:** "Day 5: visual sync verified via terminal simulation"

### Day 6 — Wire into Orchestrator + Edge Cases
- [x] Updated `orchestrator.py` for Phase 4 turn format (sub_clips per turn)
- [x] `render_conversation()` now calls `generate_captions` automatically after
  stitching — both derived from the same result set
- [x] New filename format: `chunk_XX_turn_YY_sc_ZZ.wav`
- [x] All four edge cases verified: consecutive markers, marker at start/end,
  marker-only turn (warned + skipped), no-marker script (clean passthrough)

**Checkpoint:** all edge cases handled cleanly, 17/17 checks passed. ✅
**Commit:** "Day 6: captions wired into pipeline, edge cases hardened"

### Day 7 — Docs, Final Verification, Merge & Tag
- [x] Update ARCHITECTURE.md with Phase 4 findings
- [x] Update this Phase4.md checklist
- [x] Re-run Days 1, 2, 4, 6 checkpoints once more
- [x] Merge `phase4-caption-timing` → `main`
- [x] Tag the merge commit: `phase4-complete`

**Checkpoint:** `main` now contains a full pipeline: script in → audio out →
captions.json out, with pause marker support and no external transcription dependency.

## Buffer: Day 8 (use only if needed)

Reserve for timestamp drift discovered in Day 5. Proportional distribution drift
was found to be acceptable (+0.2ms Python timing, approximate word-level sync).
No correction pass needed — buffer not required.

## Definition of Done

- [x] `[pause:N]` markers parsed correctly in all four formats
- [x] Pause silences inserted at correct durations in stitched audio, verified by ear
- [x] Word timestamps derived from clip durations — no transcription model used
- [x] `captions.json` produced with correct words, speaker labels, and timestamps
- [x] Terminal sync test confirms Python timing accuracy (+0.2ms); proportional
      sync noted as approximate but acceptable for scrolling caption display
- [x] `captions.json` generated automatically on every render call
- [x] Edge cases all handled cleanly
- [x] `phase4-caption-timing` merged into `main` and tagged `phase4-complete`
