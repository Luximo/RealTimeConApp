# Phase 2 — Voice Cloning: Two Real Voices

**Project:** RealTimeConApp
**Branch for this phase:** `phase2-voice-cloning` (off `main`)

## Goal

Prove that Chatterbox's zero-shot voice cloning works acceptably for both Speaker 1 (male)
and Speaker 2 (female) using real recorded reference clips — and nail down the extra
overhead that `prepare_conditionals()` adds on top of base generation time, so Phase 3
can budget the parallel batch render accurately. No orchestration, no stitching, no GUI
yet — just one cloned line per speaker, verified and timed.

## What Phase 1 Already Confirmed (don't re-investigate)

- The `torch.load` CPU monkey-patch works — model loads cleanly every time.
- `generate()` signature and default parameters are known and documented.
- Base generation time on this hardware: **~7.4x real-time factor** (30s to produce 4s
  of speech), with ~18s of that being the autoregressive sampling pass.
- Benign warnings on load/generate are upstream noise — ignore them.

## How Voice Cloning Works in Chatterbox (already documented in ARCHITECTURE.md)

Passing `audio_prompt_path` to `generate()` triggers an internal call to
`prepare_conditionals(audio_prompt_path, exaggeration=exaggeration)`, which replaces the
default `self.conds` with conditioning derived from the reference clip. This is zero-shot
— no training, no fine-tuning, happens at generation time. The reference clip needs to be
a clean, single-speaker `.wav` file, ideally 10–20 seconds long.

## Reference Clip Requirements

Both clips go into `scripts/` alongside the dialogue `.txt` files:

```
scripts/
├── speaker1_ref.wav    # Male voice — 10–20s, clean recording, no background noise
├── speaker2_ref.wav    # Female voice — 10–20s, clean recording, no background noise
├── speaker1.txt        # (placeholder for now — a few lines of test dialogue)
└── speaker2.txt        # (placeholder for now — a few lines of test dialogue)
```

**Recording tips for best cloning results:**
- Record in a quiet room — background noise gets cloned too, not just the voice
- Speak naturally at a normal conversational pace — not reading-aloud stiff
- Avoid music, echo, or reverb in the recording environment
- 16kHz or higher sample rate, mono is fine
- WAV format preferred — no compression artifacts

## Day-by-Day Plan

### Day 1 — Branch + Reference Clips Ready
- [x] Create and switch to `phase2-voice-cloning`
- [x] Record or source `speaker1_ref.wav` (male, 10–20s)
- [x] Record or source `speaker2_ref.wav` (female, 10–20s)
- [x] Verify both clips play back cleanly — correct voice, no clipping, no noise floor issues

**Checkpoint:** both `.wav` files exist in `scripts/`, play back cleanly.
**Commit:** "Day 1: reference clips added"

### Day 2 — Clone Speaker 1 (Male)
- [x] Write a sanity test in `tests/` that calls `tts_engine.py` with `speaker1_ref.wav`
  as `audio_prompt_path` and a short hardcoded test line
- [x] Save output as `output/day2_speaker1_cloned.wav`
- [x] Listen — does it sound like the reference voice?
- [x] Time the full call: note `prepare_conditionals()` overhead on top of base generation

**Checkpoint:** output sounds recognizably like Speaker 1's reference clip.
**Commit:** "Day 2: Speaker 1 voice cloning verified"

### Day 3 — Clone Speaker 2 (Female)
- [x] Same test structure as Day 2, using `speaker2_ref.wav`
- [x] Save output as `output/day3_speaker2_cloned.wav`
- [x] Listen — does it sound like the reference voice?
- [x] Time the full call and compare to Speaker 1's numbers

**Checkpoint:** output sounds recognizably like Speaker 2's reference clip.
**Commit:** "Day 3: Speaker 2 voice cloning verified"

### Day 4 — Cloning Quality Tuning Pass
- [x] Experimented with exaggeration, cfg_weight, temperature for both speakers
- [x] Documented winning values per speaker in ARCHITECTURE.md
- [x] Re-generated both test lines with tuned settings and confirmed improvement

**Checkpoint:** both voices sound natural and distinct from each other at their tuned settings.
**Commit:** "Day 4: cloning quality tuned, settings documented"

### Day 5 — Timing Baseline with Cloning
- [x] Generated 3 lines of varying length for each speaker and recorded generation times
- [x] Calculated real-time factor with voice cloning active
- [x] Wrote updated numbers into ARCHITECTURE.md
- [x] Confirmed memory usage during a single cloned generate call

**Checkpoint:** cloning real-time factor recorded for both speakers, memory usage noted.
**Commit:** "Day 5: cloning timing baseline recorded"

### Day 6 — Docs, Final Verification, Merge & Tag
- [x] Update ARCHITECTURE.md with all Phase 2 findings
- [x] Update this Phase2.md checklist
- [ ] Re-run Day 1–5 checkpoints once more, top to bottom
- [ ] Merge `phase2-voice-cloning` → `main`
- [ ] Tag the merge commit: `phase2-complete`

**Checkpoint:** `main` now contains verified, tuned, timed voice cloning for both speakers.

## Definition of Done

- [x] Both reference clips recorded and verified clean
- [x] Speaker 1 cloned voice sounds recognizably like reference
- [x] Speaker 2 cloned voice sounds recognizably like reference
- [x] Naturalness settings tuned and documented per speaker in ARCHITECTURE.md
- [x] Real-time factor with cloning recorded (the number Phase 3 will budget against)
- [x] Memory usage per worker noted
- [ ] `phase2-voice-cloning` merged into `main` and tagged `phase2-complete`