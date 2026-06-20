# Phase 6 — Integration: One App, End to End

**Project:** RealTimeConApp
**Branch for this phase:** `phase6-integration` (off `main`)

## Goal

Turn the working prototype into a usable application. Every piece exists and works
in isolation — this phase wires them into one coherent flow a real user can operate
without editing config files or running scripts from a terminal. By the end, a user
can open the app, pick their script files and voice clips, watch a render progress
indicator during the wait, and go straight into the playback window when it's done.
Phase 7 (packaging) produces the final `.exe` — Phase 6 makes the app ready for it.

## What Phases 1–5 Already Confirmed (don't re-investigate)

- Full render pipeline works: script → parallel batch → audio + captions.json
- GUI playback works: audio + captions.json → scrolling captions, speed slider, controls
- Known sync drift between Phase 4's mismatched files resolves on any fresh render —
  `render_conversation()` already guarantees both files from the same pass
- PyQt6 6.11.0 confirmed working, FFmpeg backend auto-detected, no codec installs needed
- `QMediaPlayer.position()` returns media time — caption sync correct at any speed
- All constants live in `config.py`, all GUI lives in `gui/player_window.py`

## The Four Gaps This Phase Closes

```
Gap 1 — Sync drift never verified resolved in a real end-to-end run
Gap 2 — main.py has no entry point logic: no state detection, no routing
Gap 3 — Render gives zero feedback during 38+ minute waits
Gap 4 — All paths are hardcoded — user can't choose files without editing code
```

## How the App Should Flow (the target state after this phase)

```
User double-clicks the app
        ↓
main.py checks: do output files exist?
   ├── YES → launch player_window.py directly (skip render)
   └── NO  → launch setup_window.py (file pickers + render button)
                    ↓
             User picks script files + voice clips
             User clicks "Generate Conversation"
                    ↓
             render_window.py shows progress:
             "Chunk 3 of 7 — Turn 14 of 24 — ~18 min remaining"
             [Cancel button available]
                    ↓
             Render completes → automatically opens player_window.py
```

No terminal. No config editing. No hardcoded paths.

## New Files This Phase Adds

```
gui/setup_window.py    — file picker UI: script files, voice clips, render button
gui/render_window.py   — progress display during render: chunk/turn count, ETA, cancel
```

`main.py` gets real logic. `orchestrator.py` gains progress reporting.
Everything else stays exactly as-is — no changes to audio, captions, or TTS modules.

## Progress Reporting Design (the trickiest part)

Currently `orchestrator.py` uses `multiprocessing.Pool.map()` — this blocks until
all workers finish with no intermediate output. To show per-turn progress, we need
`Pool.imap_unordered()` instead, which yields results as each worker finishes a turn.

Each yielded result carries: `chunk_idx`, `turn_idx`, speaker, text (already in the
result dict from Phase 3). The orchestrator counts completed turns against the total
and emits that to the GUI via a `multiprocessing.Queue`.

`render_window.py` polls that Queue on a `QTimer` every 500ms and updates the display.
ETA is calculated as:
```
elapsed / turns_done * turns_remaining
```
Simple, honest, updates as each turn completes.

**Important:** `imap_unordered()` means results arrive out of order — we still sort
by `(chunk_idx, turn_idx)` before stitching, same as before. Progress counting just
needs the count, not the order, so this is safe.

**Cancel behavior:** cancel sets a `multiprocessing.Event` that workers check between
turns. On cancel: pool is terminated, partial output files are cleaned up, app returns
to setup_window.py with a clear "Render cancelled" message.

## File Selection Design

`gui/setup_window.py` shows four file pickers and a render button:

```
┌─────────────────────────────────────────────────────┐
│           RealTimeConApp — Setup                    │
│                                                     │
│  Speaker 1 Script:  [scripts/speaker1.txt    ] [📂] │
│  Speaker 2 Script:  [scripts/speaker2.txt    ] [📂] │
│                                                     │
│  Speaker 1 Voice:   [scripts/speaker1_ref.wav] [📂] │
│  Speaker 2 Voice:   [scripts/speaker2_ref.wav] [📂] │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  [  Generate Conversation  ]                │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [▶ Open Last Render]  (greyed out if none exists)  │
└─────────────────────────────────────────────────────┘
```

Selected paths persist to `config/last_session.json` so they're remembered next run.
"Open Last Render" is active only if `output/conversation_final.wav` already exists —
gives the user a way to replay without re-rendering.

## main.py Entry Point Logic

```python
# Simplified flow — actual implementation in main.py
if output_files_exist():
    launch_player()          # go straight to playback
else:
    launch_setup()           # go to file pickers first
```

`output_files_exist()` checks for both `conversation_final.wav` AND `captions.json`
— if either is missing, treat as no output and show setup. Avoids the mismatch case
that caused Phase 4's sync drift.

A `--setup` command-line flag forces setup_window.py even if output files exist —
lets the user start a new render without deleting the old output manually.

## Module Separation — What Changes, What Doesn't

```
main.py            — CHANGED: real entry point logic, state detection, routing
orchestrator.py    — CHANGED: imap_unordered + Queue for progress reporting,
                     cancel Event checked between turns
gui/setup_window.py   — NEW: file picker UI, session persistence
gui/render_window.py  — NEW: progress display, ETA, cancel button
gui/player_window.py  — UNCHANGED: loads files, plays, scrolls captions
config.py          — MINOR: add SESSION_FILE path constant
audio_utils.py     — UNCHANGED
captions.py        — UNCHANGED
tts_engine.py      — UNCHANGED
voice_manager.py   — UNCHANGED
script_parser.py   — UNCHANGED
```

The TTS, audio, and caption pipeline is untouched. Only the orchestration shell
and GUI entry flow change.

## Day-by-Day Plan

### Day 1 — Branch + End-to-End Integration Run
- [ ] Create and switch to `phase6-integration`
- [ ] Run `render_conversation()` fresh on a real script end-to-end — this is the
  first time the full pipeline runs as one system since Phase 5 was completed
- [ ] Verify: does the known sync drift resolve? Play the output in the Phase 5
  player window and confirm captions track the correct speaker at every transition
- [ ] Record actual wall-clock render time for this script in ARCHITECTURE.md
- [ ] If sync drift does NOT resolve: investigate before proceeding — this is a
  Day 1 blocker, not something to carry forward

**Checkpoint:** fresh end-to-end render produces audio + captions.json that play
back in sync with correct speaker labels at every transition. No drift.
**Commit:** "Day 1: end-to-end integration verified, sync confirmed clean"

### Day 2 — main.py Entry Point
- [ ] Implement real entry point logic in `main.py`:
  - Check for both `conversation_final.wav` and `captions.json`
  - If both exist: launch `player_window.py` directly
  - If either missing: launch `setup_window.py`
  - Support `--setup` flag to force setup even when output exists
- [ ] Test all three paths: fresh install (no output), existing output, `--setup` flag
- [ ] Confirm the PyQt6 app launches cleanly from `python main.py` in all three cases

**Checkpoint:** all three routing paths work correctly from `python main.py`.
**Commit:** "Day 2: main.py entry point implemented"

### Day 3 — Progress Reporting in orchestrator.py
- [ ] Switch `orchestrator.py` from `Pool.map()` to `Pool.imap_unordered()`
- [ ] Add a `multiprocessing.Queue` that workers push progress events to after
  each turn completes: `{chunk_idx, turn_idx, speaker, total_turns, done_turns}`
- [ ] Add a `multiprocessing.Event` for cancel — workers check it between turns
  and exit cleanly if set
- [ ] Add cancel cleanup: terminate pool, delete partial output files
- [ ] Verify existing output is still correct — `imap_unordered` changes arrival
  order only, not content. Sort by `(chunk_idx, turn_idx)` before stitching as before
- [ ] Run a full render and confirm output is identical to Phase 5's output

**Checkpoint:** render produces identical output to before, progress Queue emits
correct turn counts, cancel terminates cleanly with no corrupted files left behind.
**Commit:** "Day 3: progress reporting and cancel added to orchestrator"

### Day 4 — Render Progress Window
- [ ] Implement `gui/render_window.py`:
  - Shows "Generating turn X of Y — Chunk Z of N"
  - Shows elapsed time and ETA (elapsed / done * remaining)
  - Cancel button — triggers the Event from Day 3, returns to setup_window
  - On completion: automatically opens `player_window.py`
- [ ] Wire to orchestrator's Queue via a 500ms `QTimer` poll
- [ ] Test: does ETA update reasonably as turns complete?
- [ ] Test: does cancel leave the output directory clean?

**Checkpoint:** progress window shows accurate turn counts and reasonable ETA,
cancel works cleanly, completion transitions automatically to player.
**Commit:** "Day 4: render progress window implemented"

### Day 5 — Setup Window + Session Persistence
- [ ] Implement `gui/setup_window.py`:
  - Four file pickers: speaker1.txt, speaker2.txt, speaker1_ref.wav, speaker2_ref.wav
  - File pickers use `QFileDialog` — user browses to files rather than typing paths
  - "Generate Conversation" button launches render_window.py with selected paths
  - "Open Last Render" button (active only if output files exist) goes to player
  - Basic validation before render: all four files must exist and be non-empty
- [ ] Persist selected paths to `config/last_session.json` on every change
- [ ] Load persisted paths on startup so they're pre-filled next run
- [ ] Test: what happens if a previously persisted path no longer exists?
  Show a clear warning rather than silently using a stale path

**Checkpoint:** file pickers work, paths persist between app restarts,
validation catches missing files before render starts.
**Commit:** "Day 5: setup window and session persistence implemented"

### Day 6 — Production Script Test
- [ ] Write or use a real script targeting ~60 turns (~10 min of speech)
  — this is the actual production target, not a short test script
- [ ] Run the full app flow from scratch: setup window → render → player
- [ ] Record actual wall-clock render time for 60 turns in ARCHITECTURE.md
- [ ] Verify playback is smooth for a full 10-minute session:
  - No memory growth over full playback duration
  - No caption drift by the end of a long render
  - Speaker transitions correct throughout
  - Speed slider works correctly mid-playback on long content
- [ ] Note anything that feels rough or needs polish before packaging

**Checkpoint:** full 60-turn script renders and plays back correctly end-to-end.
Wall-clock render time recorded in ARCHITECTURE.md.
**Commit:** "Day 6: production script test — 60 turns verified end-to-end"

### Day 7 — Docs, Final Verification, Merge & Tag
- [ ] Update ARCHITECTURE.md with Phase 6 findings:
  - Confirmed sync drift resolved
  - Progress reporting approach documented
  - Production render time for 60-turn script
  - Any polish notes for Phase 7
- [ ] Update this Phase6.md checklist
- [ ] Re-run Day 1–6 checkpoints once more, top to bottom
- [ ] Merge `phase6-integration` → `main`
- [ ] Tag the merge commit: `phase6-complete`

**Checkpoint:** `main` now contains a complete, usable application — no terminal
required, no hardcoded paths, progress visible during render, auto-transitions
from render to playback when done.

## Buffer: Days 8–9 (use only if needed)

Two likely friction points worth reserving time for:

**multiprocessing.Queue on Windows (Day 3):** Windows spawn mode means the Queue
must be passed explicitly to workers via `initargs` — it can't be a global. If
workers can't see the Queue, progress events silently disappear. The fix is
straightforward once the cause is identified, but it can eat an afternoon.

**imap_unordered result ordering (Day 3):** If the sort-by-index step gets missed
or the index fields change shape, the stitched audio comes out scrambled. Verify
by running the existing Phase 3 test suite against the updated orchestrator before
moving to Day 4.

## Definition of Done

- [ ] Fresh end-to-end render confirmed clean — sync drift resolved
- [ ] `main.py` routes correctly: existing output → player, no output → setup
- [ ] Progress window shows accurate turn counts and reasonable ETA during render
- [ ] Cancel terminates cleanly with no corrupted output left behind
- [ ] File pickers replace all hardcoded paths, session persists between runs
- [ ] 60-turn (~10 min) production script renders and plays back correctly
- [ ] No terminal required for any part of the user flow
- [ ] `phase6-integration` merged into `main` and tagged `phase6-complete`