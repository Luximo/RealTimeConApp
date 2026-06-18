# Phase 0 — Project Foundation & Environment Setup

**Project:** RealTimeConApp
**Branch for this phase:** `phase0-setup` (off `main`)

## Goal

Establish a clean, modular project skeleton and a verified development environment — nothing TTS-related yet. By the end of this phase, every later phase has its own dedicated file to grow into, and the underlying tooling (Python, virtual environment, ffmpeg) is confirmed working on this exact machine, before any model code gets written.

## Branch & Release Workflow (applies to every phase, not just this one)

- `main` only ever holds work that's been fully verified. It should always be in a runnable state.
- Each phase gets its own branch: `phase0-setup`, `phase1-tts-engine`, `phase2-voice-cloning`, and so on.
- Commit at the end of each day/checkpoint *on the phase branch* — this gives rollback points within the phase if something later in the same phase breaks.
- Only merge into `main` once every checkpoint in the phase is verified working.
- Tag the merge commit (e.g. `phase0-complete`, `phase1-complete`) so there's always a labeled, known-good point to return to.
- If a phase branch goes sideways and isn't worth saving, it's safe to abandon entirely — `main` was never touched.

## Project Skeleton

Created in this phase as empty/stub files — purpose documented, no real logic yet:

```
RealTimeConApp/
├── main.py                # Entry point; wires everything together
├── config.py              # Paths, constants, default settings (speed, pause length, etc.)
├── tts_engine.py          # All calls to the TTS engine isolated here
├── voice_manager.py       # Maps each speaker to their reference voice clip
├── script_parser.py       # Reads/merges the two .txt files into ordered (speaker, line) turns
├── orchestrator.py        # Drives turn-by-turn generation (batch in Phase 3, live in Phase 6)
├── audio_utils.py         # Stitching, pause insertion, speed/time-stretch
├── captions.py            # Word-timestamp alignment for the scrolling captions
├── gui/
│   └── player_window.py   # Playback UI + scrolling captions, kept fully separate from backend
├── scripts/                # Your .txt dialogue files + voice reference clips live here
├── tests/                   # One small sanity script per module
├── docs/
│   ├── Phase0.md            # This file
│   └── ARCHITECTURE.md      # Brief living doc of how the pieces fit together
├── requirements.txt
└── .gitignore
```

## Day-by-Day Plan

### Day 1 — Git & Repo Foundation
- [ ] `git init` (if not already a repo)
- [ ] Create `.gitignore` (venv/, `__pycache__/`, `*.pyc`, model cache folders, generated audio output)
- [ ] Initial commit to `main`: bare `.gitignore` + empty `README.md`
- [ ] Create and switch to `phase0-setup`

**Checkpoint:** `git log` shows the initial commit on `main`; everything after this happens on `phase0-setup`.

### Day 2 — Folder & Module Skeleton
- [ ] Create the full folder tree above
- [ ] Each `.py` file gets a one-line docstring describing its purpose — no logic yet
- [ ] `main.py` just prints `"Scaffold OK"` so we can confirm it runs

**Checkpoint:** `python main.py` prints `Scaffold OK` with no errors.
**Commit:** "Day 2: project skeleton scaffolded"

### Day 3 — Python Environment & Dependencies
- [ ] Create a virtual environment inside the project folder
- [ ] Confirm the exact Python version Chatterbox needs on Windows — verify rather than assume, this is exactly the kind of thing that quietly breaks later if skipped
- [ ] Write `requirements.txt` with the expected packages (chatterbox-tts, the CPU build of torch, audio libs), pinned once confirmed

**Checkpoint:** venv activates cleanly; `pip list` shows the baseline packages with no install errors.
**Commit:** "Day 3: virtual environment + requirements.txt"

### Day 4 — External Tools (ffmpeg)
- [ ] Install ffmpeg, confirm `ffmpeg -version` works from this same PowerShell session
- [ ] Add a tiny sanity test in `tests/` that calls ffmpeg through a stub in `audio_utils.py`

**Checkpoint:** the sanity test passes and prints ffmpeg's version string.
**Commit:** "Day 4: ffmpeg verified"

### Day 5 — Docs, Final Verification, Merge & Tag
- [ ] Update this Phase0.md if anything changed from the plan along the way
- [ ] Re-run every checkpoint above, top to bottom, once more
- [ ] Merge `phase0-setup` → `main`
- [ ] Tag the merge commit: `phase0-complete`

**Checkpoint:** `main` now contains the full skeleton plus a verified environment, tagged.

## Buffer: Day 6–7 (use only if needed)

Reserve these in case Day 3 or 4 hits dependency or driver friction — given this is CPU-first Windows with no prior Chatterbox install on this exact machine, that's a real possibility, not a hypothetical. If everything goes smoothly, skip straight to merging on Day 5.

## Definition of Done

- [ ] Skeleton exists with every file in its own place, properly separated
- [ ] venv + requirements.txt verified working
- [ ] ffmpeg verified working
- [ ] `phase0-setup` merged into `main` and tagged `phase0-complete`