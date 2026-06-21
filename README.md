# RealTimeConApp

A Windows desktop application that synthesizes two-speaker conversations from plain text scripts using zero-shot voice cloning, then plays them back with synchronized scrolling captions.

Write a dialogue. Record two short voice samples. Generate a conversation in those voices. Press play.

---

## What It Does

- Reads two `.txt` script files (one per speaker) and interleaves them into a conversation
- Clones each speaker's voice from a short reference recording (~10–20 seconds)
- Renders the full conversation as a single audio file using parallel batch generation
- Plays back the audio with right-to-left scrolling captions synchronized word by word
- Clears the caption display at every speaker transition for a clean visual break
- Supports `[pause:N]` markers in scripts for natural mid-turn silences

Everything runs locally — no cloud API, no internet required after first launch.

---

## Demo

```
Speaker 1 script (speaker1.txt)       Speaker 2 script (speaker2.txt)
──────────────────────────────         ──────────────────────────────
Did you catch the news today?          Don't even get me started.
That bad, huh?                         Honestly yes [pause:1] the whole
I thought we said we'd be good         thing was a mess from start to
this week.                             finish.
```

↓ Generate

```
[S1 teal]  Did  you  catch  the  news  today?  ←←←←←←←←←←
                                                ─ visual break ─
[S2 amber] Don't  even  get  me  started.  ←←←←←←←←←←←←←
```

---

## Requirements

- **OS:** Windows 10/11 (64-bit)
- **CPU:** Any modern x86-64 processor — 8+ cores recommended
- **RAM:** 16 GB minimum, 24 GB recommended (8 parallel workers each load the model)
- **GPU:** Not required — runs entirely on CPU
- **Internet:** Required once on first launch to download the voice model (~1.5 GB)
- **Python:** 3.11 (for development); not needed to run the packaged `.exe`

---

## Installation

### Option A — Run the packaged .exe (no Python required)

1. Download the latest release zip from the [Releases](../../releases) page
2. Extract the zip to any folder
3. Double-click `RealTimeConApp.exe`
4. On first launch: the app will download the voice model (~1.5 GB) — this happens once

### Option B — Run from source

```powershell
# Clone the repo
git clone https://github.com/Luximo/RealTimeConApp.git
cd RealTimeConApp

# Create and activate a virtual environment (Python 3.11 required)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
```

> **Note:** ffmpeg must be installed and available on your PATH when running from source.
> Install via winget: `winget install ffmpeg`

---

## How to Use

### 1. Prepare your script files

Create two plain `.txt` files — one line per turn, one file per speaker:

```
# scripts/speaker1.txt
Did you catch the news today?
That bad, huh?
I thought we said we'd be good this week.
```

```
# scripts/speaker2.txt
Don't even get me started.
Honestly yes [pause:1] the whole thing was a mess.
I know I know. But here we are.
```

Turns are interleaved strictly in order: S1 line 1 → S2 line 1 → S1 line 2 → S2 line 2...

### 2. Record your voice reference clips

Record a short clip for each speaker (10–20 seconds, WAV format):

- Speak naturally — background noise gets cloned too, so record in a quiet room
- One speaker per file, no music or echo
- Save as `scripts/speaker1_ref.wav` and `scripts/speaker2_ref.wav`

### 3. Generate and play

1. Launch the app — it opens to the Setup window
2. Use the file pickers to select your two script files and two voice clips
3. Click **Generate Conversation** — a progress window shows turn-by-turn status and ETA
4. When generation completes, the app automatically opens the playback window
5. Press ▶ to play — captions scroll in sync with the audio

To generate a new conversation from a different script, use `--setup` flag or delete the `output/` folder:

```powershell
python main.py --setup
```

---

## Pause Markers

Add `[pause:N]` markers anywhere in a script line to insert a natural silence mid-turn:

```
Well I mean [pause:0.5] okay hold on [pause:3] maybe we do it this way
```

| Marker | Duration |
|--------|----------|
| `[pause]` | 0.5 seconds (default) |
| `[pause:short]` | 0.3 seconds |
| `[pause:long]` | 3.0 seconds |
| `[pause:N]` | exactly N seconds (float or int) |

Markers are stripped before synthesis — the TTS engine never sees them. The silence is inserted as real audio during stitching, and the caption display holds on the last word during the gap.

---

## Playback Controls

| Control | Function |
|---------|----------|
| ▶ / ⏸ | Play / Pause |
| ■ | Stop and return to beginning |
| ◀◀ | Restart |
| Progress bar | Click anywhere to seek |
| Speed slider | 0.5x (slow) → 1.0x (normal) → 2.0x (fast) |

The speed slider adjusts both audio playback rate and caption scroll speed simultaneously. No re-render required.

---

## Project Structure

```
RealTimeConApp/
├── main.py              # Entry point — detects app state, routes to setup or player
├── config.py            # All constants: paths, speeds, pause durations, display settings
├── tts_engine.py        # All Chatterbox TTS calls isolated here
├── voice_manager.py     # Maps each speaker to their reference clip
├── script_parser.py     # Parses .txt files, merges turns, handles [pause:N] markers
├── orchestrator.py      # Parallel worker pool — fans out chunks, collects results
├── audio_utils.py       # Stitching, pause insertion, silence trimming, timestamps
├── captions.py          # Generates and loads captions.json
├── gui/
│   ├── player_window.py     # Playback window — scrolling captions, controls
│   ├── setup_window.py      # File picker UI — script and voice clip selection
│   ├── render_window.py     # Render progress — turn count, ETA, cancel
│   └── first_run_window.py  # First-launch model download screen
├── scripts/             # Place your .txt script files and .wav reference clips here
├── output/              # Generated audio and captions.json written here
├── tests/               # Sanity tests per module
└── docs/                # Phase plans and architecture reference
```

---

## How It Works

**Parsing:** `script_parser.py` reads both `.txt` files and zips them into an ordered turn list. Short turns (under 8 words) are merged with the next same-speaker turn to avoid the RTF penalty of generating very short clips. Turns are chunked by estimated generation time — not word count — so parallel workers finish at roughly the same time.

**Parallel generation:** `orchestrator.py` spins up a `multiprocessing.Pool` with up to 8 workers. Each worker loads the Chatterbox model once at startup, then generates all turns in its assigned chunk sequentially. Results are collected and sorted by `(chunk_idx, turn_idx)` before stitching.

**Stitching:** `audio_utils.py` concatenates per-turn clips in order, inserting inter-speaker pauses (0.3s) between turns and `[pause:N]` silences within turns. Silence trimming (−45 dBFS, 150ms minimum) and a 25ms fade-in per clip eliminate leading artifacts. Word-level timestamps are derived proportionally from clip durations during this pass — no transcription model needed.

**Playback:** `gui/player_window.py` loads `conversation_final.wav` and `captions.json` at startup. A 30ms `QTimer` reads `QMediaPlayer.position()` (media time) and advances a word pointer through the caption list. Words enter from the right edge of the display and scroll left at 250 px/s, wrapping to new lines at the left margin. Older lines fade in opacity. The display clears on speaker label change.

---

## Performance

Tested on Ryzen 7 5700G (8 cores), CPU-only:

| Script length | Turns | Wall-clock render |
|---------------|-------|-------------------|
| ~1 min audio | 16 | ~11 min |
| ~3:28 audio | 44 | ~28 min |
| ~10 min audio | 60 | ~38–42 min (estimated) |

Render time scales with script length at roughly 8–10x real-time per turn, distributed across 8 parallel workers for ~1.1x speedup over sequential generation. You render once; the output is saved and replays instantly on subsequent launches.

---

## Tech Stack

| Component | Library / Version |
|-----------|------------------|
| TTS engine | [Chatterbox TTS](https://github.com/resemble-ai/chatterbox) 0.1.7 |
| Deep learning | PyTorch 2.6.0 (CPU) / torchaudio 2.6.0 |
| GUI | PyQt6 6.11.0 |
| Audio processing | pydub + ffmpeg 8.1.1 |
| Packaging | PyInstaller 6.21.0 |
| Python | 3.11.9 |

---

## Known Limitations

- **Render time:** ~28 min for a ~3.5-minute conversation on a Ryzen 7 5700G (CPU-only). GPU acceleration via ROCm or CUDA would significantly reduce this.
- **English only:** Chatterbox TTS 0.1.7 is English-only.
- **Two speakers only:** The current pipeline is designed for exactly two alternating speakers.
- **Word-level caption sync is approximate:** Timestamps are derived proportionally from clip durations. Individual word timing within a turn is evenly distributed — not frame-accurate. Turn-level sync (speaker transitions) is exact.
- **AMD GPU not accelerated:** The RX 6750 XT (gfx1031) is not on AMD's official ROCm support list. Generation runs on CPU.

---

## Voice Cloning & Privacy

Voice cloning uses Chatterbox's zero-shot conditioning — no training or fine-tuning required. Only use voice clips of yourself or people who have explicitly consented. Do not clone voices without permission.

Generated audio contains Resemble AI's Perth watermark, baked in by the model. This is not optional or removable through Chatterbox's public API.

---

## License

[MIT](LICENSE)

Chatterbox TTS is also MIT licensed. See [resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox) for details.