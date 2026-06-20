# Phase 5 — Playback GUI: Scrolling Captions & Speed Control

**Project:** RealTimeConApp
**Branch for this phase:** `phase5-player-gui` (off `main`)

## Goal

Build the playback window in `gui/player_window.py` — load `conversation_final.wav`
and `captions.json`, play the audio, scroll words right-to-left in sync, clear the
screen at speaker transitions, hold display during `[pause:N]` gaps, and let the user
adjust playback speed with a slider. No rendering happens here. No TTS calls. This
phase is purely the display and playback layer consuming what Phases 3 and 4 produced.

## What Phases 1–4 Already Confirmed (don't re-investigate)

- `conversation_final.wav` — 44100Hz, mono, 16-bit PCM, fully stitched with pauses
- `captions.json` — one entry per word: `{word, start, end, speaker}`, globally ordered
- Speaker transitions detected by label change between consecutive entries (S1 → S2)
- `[pause:N]` gaps appear as timestamp gaps — no word entry emitted for silence,
  last pre-pause word just holds on screen until the next entry's `start` time
- Python timer accuracy: +0.2ms average — sufficient for caption sync
- `captions.json` and audio are always produced together from the same pipeline pass

## GUI Library: PyQt6

PyQt6 is the right choice for this project:
- Native Windows look and feel with no extra configuration
- `QMediaPlayer` handles WAV audio playback with position tracking in milliseconds
- `QTimer` drives the caption animation loop at 30ms intervals — smooth enough for
  scrolling text without hammering the CPU
- `QPainter` on a custom `QWidget` gives full control over the scrolling animation
- `QSlider` for the speed control, `QPushButton` for play/pause/stop
- Packages cleanly into a Windows `.exe` via PyInstaller in Phase 7

Install: `pip install PyQt6`

**Important:** `QMediaPlayer` on Windows requires the `PyQt6-Qt6-Multimedia` backend.
If audio doesn't play on first run, install: `pip install PyQt6-Qt6-Multimedia`

## How the Caption Display Works

The caption area is a custom `QWidget` that `player_window.py` owns entirely.
`gui/player_window.py` knows about captions and audio. Nothing else touches the GUI.

**Right-to-left scrolling within a speaker turn:**
- Words enter from the right edge of the display area
- Each word moves left at a speed calibrated to match the audio's speaking pace
- Words wrap naturally to the next line when they reach the left edge
- The display area holds 3–4 lines of text at once — older lines scroll up and
  off the top as new lines come in from the right

**Speaker transition — screen clear:**
- When the `speaker` label changes between two consecutive `captions.json` entries,
  the display clears completely after the last word of the outgoing speaker finishes
- A brief visual pause (matching `INTER_SPEAKER_PAUSE` = 0.3s) before the new
  speaker's first word enters from the right
- Optional: a subtle speaker label ("Speaker 1" / "Speaker 2") fades in at the
  top of the display area for 1s at each transition, then fades out

**`[pause:N]` hold behavior:**
- No special logic needed — the caption loop simply finds no new word to display
  during the gap between entries
- The last displayed word stays visible on screen naturally
- When the next entry's `start` time arrives, new words begin scrolling in

**Speed slider effect on captions:**
- The slider does NOT re-render audio — it adjusts the playback rate of
  `QMediaPlayer` directly via `setPlaybackRate(factor)`
- PyQt6's `QMediaPlayer.setPlaybackRate()` handles pitch-preserving time-stretch
  internally on Windows — no ffmpeg call needed for this
- Caption timestamps are divided by the speed factor at load time so the timer
  loop always works in "display time" not "audio time":
  `display_start = entry["start"] / speed_factor`
- When the slider moves, timestamps are recalculated and the audio rate updated
  in one atomic step — no drift between audio and captions

**Speed range:** 0.5x (slow) to 2.0x (fast), default 1.0x normal.
Exposed as `config.MIN_SPEED`, `config.MAX_SPEED`, `config.DEFAULT_SPEED`.

## Window Layout

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   [caption display area — scrolling text here]      │
│                                                     │
│   line 3: older words scrolling left ←←←           │
│   line 2: more words ←←←←←←←←←←←←←←←←             │
│   line 1: newest words entering from right →→→      │
│                                                     │
├─────────────────────────────────────────────────────┤
│  ◀◀  ▶/⏸  ■■   ────────●──────── Speed: [━━●━━]   │
│  Restart Play  Stop     Progress          0.5x–2.0x │
└─────────────────────────────────────────────────────┘
```

Controls bar at the bottom — separated cleanly from the caption display widget.
Progress bar shows playback position, clickable for seeking.

## How the Timer Loop Works

A `QTimer` fires every 30ms. On each tick:

1. Get current playback position from `QMediaPlayer.position()` (milliseconds)
2. Convert to seconds: `audio_time = position_ms / 1000.0`
3. Adjust for speed: `display_time = audio_time` (timestamps already pre-scaled)
4. Find the next unshown word whose `start <= display_time`
5. If found: add that word to the scrolling display, advance the word pointer
6. If speaker changed from previous word: trigger screen clear sequence
7. Repaint the caption widget

This loop is lightweight — just a list index comparison and a repaint call.
No heavy computation happens inside the timer.

## How the Scrolling Animation Works

Each word on screen has an `x` position that decreases by a fixed number of pixels
per timer tick — this is the scroll speed. Scroll speed is derived from:

```
pixels_per_tick = base_scroll_speed * speed_factor
```

Where `base_scroll_speed` is calibrated so that at 1.0x, the word's visible
duration on screen roughly matches its `end - start` duration in the captions.

Words are stored in a list of `(text, x, y, opacity)` tuples. Each tick:
- All existing words shift left by `pixels_per_tick`
- Words that move off the left edge are removed
- New words enter at `x = display_width + word_width + padding`
- Line wrapping: when a new word would overlap the left boundary, it's placed
  on the next line down instead (y increases by line_height)
- When lines exceed the display area height, the oldest line is removed (scroll up)

## Module Separation — What Lives Where

```
gui/player_window.py  — the ONLY file that imports PyQt6
                        owns the window, controls, timer loop, and repaint logic
                        imports captions.py for loading captions.json
                        imports config.py for speed range and display constants
                        knows nothing about TTS, scripts, or workers

captions.py           — already complete from Phase 4
                        provides load_captions(path) → list of word entries
                        player_window.py calls this once at startup

config.py             — add display constants here:
                        CAPTION_FONT_SIZE, CAPTION_FONT_FAMILY,
                        SCROLL_SPEED_BASE, MIN_SPEED, MAX_SPEED, DEFAULT_SPEED,
                        SPEAKER_LABEL_DISPLAY_DURATION
```

No other file changes. The entire GUI lives in `gui/player_window.py`.

## Day-by-Day Plan

### Day 1 — Branch + PyQt6 Shell
- [x] Create and switch to `phase5-player-gui`
- [x] Install PyQt6: `pip install PyQt6`
- [x] Implement the bare window shell in `gui/player_window.py`
- [x] Confirm window opens and closes cleanly with no errors

**Checkpoint:** window opens, displays correctly, closes cleanly. ✅
**Commit:** "Day 1: PyQt6 window shell implemented"

### Day 2 — Audio Playback
- [x] Wire `QMediaPlayer` to load and play `output/conversation_final.wav`
- [x] Play/pause button toggles correctly
- [x] Stop button returns to beginning
- [x] Progress bar updates in real time during playback
- [x] Progress bar is clickable for seeking
- [x] Confirm audio plays through speakers at correct quality

**Checkpoint:** audio plays, pauses, stops, and seeks correctly. ✅
**Commit:** "Day 2: audio playback implemented"

### Day 3 — Caption Sync Loop
- [x] Load `output/captions.json` via `captions.py` at window startup
- [x] Implement the 30ms `QTimer` loop
- [x] Words displayed on a `QLabel` in sync with audio

**Checkpoint:** words appear on the label in sync with the audio. ✅
**Commit:** "Day 3: caption sync loop verified"

### Day 4 — Scrolling Animation
- [x] Replace `QLabel` with custom `QPainter`-based `ScrollingCaptionWidget`
- [x] Words enter from right, scroll left, wrap to next line, older lines scroll up
- [x] Fixed cumulative `_next_x` pile-up bug — words now always enter at right edge
- [x] `SCROLL_SPEED_BASE` tuned to 250 px/s

**Checkpoint:** words scroll right-to-left continuously, wrap correctly. ✅
**Commit:** "Day 4: scrolling animation implemented, scroll speed tuned to 250px/s"

### Day 5 — Speaker Transitions
- [x] Detect speaker label changes between consecutive caption entries
- [x] Display clears on transition; speaker label fades in for 1s
- [x] S1 = teal, S2 = amber — both label and word colours

**Checkpoint:** screen clears cleanly at every speaker transition. ✅
**Commit:** "Day 5: speaker transitions implemented"

### Day 6 — Speed Slider
- [x] `QMediaPlayer.setPlaybackRate()` confirmed pitch-preserving on Windows
- [x] Caption scroll rate scales with speed factor
- [x] Verified in sync at 0.5x, 1.0x, 2.0x and during mid-playback changes

**Checkpoint:** speed slider changes audio pace and caption scroll together. ✅
**Commit:** no new code — wiring was complete from Days 2 and 4

### Day 7 — Polish & Edge Cases
- [x] Per-speaker word colours (teal S1, amber S2)
- [x] Line opacity gradient (newest line = full, older lines fade)
- [x] Left-edge gradient fade (60px, words melt away)
- [x] Live time counter (M:SS / M:SS) in controls bar
- [x] End-of-audio: progress fills, button resets to ▶, timer stops
- [x] Missing file: styled error overlay in caption area, no crash
- [x] Pause freezes captions exactly; resume continues from same position

**Checkpoint:** clean end-of-playback, graceful missing-file handling. ✅
**Commit:** "Day 7: polish — speaker word colours, line opacity, left-edge fade, time counter, end-of-audio, missing file handling"

### Day 8 — Docs, Final Verification, Merge & Tag
- [x] Update ARCHITECTURE.md with Phase 5 findings
- [x] Update this Phase5.md checklist
- [x] Re-run all Day 1–7 checkpoints — all 14 passed
- [x] Merge `phase5-player-gui` → `main`
- [x] Tag the merge commit: `phase5-complete`

**Checkpoint:** `main` now contains a fully working playback window.

## Definition of Done

- [x] Window opens cleanly, audio plays correctly
- [x] Words scroll right-to-left in sync with audio
- [x] Lines wrap naturally, older lines scroll up and off
- [x] Screen clears cleanly at every speaker transition
- [x] `[pause:N]` gaps hold the last word on screen correctly
- [x] Speed slider adjusts audio pace and caption scroll together, in sync
- [x] Graceful handling of missing files and end-of-playback
- [x] Stable over full-length playback without drift or memory growth
- [x] `phase5-player-gui` merged into `main` and tagged `phase5-complete`