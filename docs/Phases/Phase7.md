# Phase 7 — Packaging: Windows .exe

**Project:** RealTimeConApp
**Branch for this phase:** `phase7-packaging` (off `main`)

## Goal

Turn `python main.py` into a double-clickable Windows `.exe` that a user with no
Python, no venv, and no terminal can run. By the end of this phase, the deliverable
is a single distributable folder containing the app, ffmpeg, and a launcher — ready
to zip and hand to someone else.

## What Phase 6 Already Confirmed (don't re-investigate)

- Full app flow works end-to-end: setup → render → player, no terminal required
- PyQt6 6.11.0 + FFmpeg backend confirmed working on this machine
- `multiprocessing` uses Windows spawn mode — workers load from scratch each time
- `config/last_session.json` is gitignored — not committed
- `OSError: paging file too small` is a Windows virtual memory blip, not a code bug
- gradio and its web stack are transitive dependencies of chatterbox, completely unused

## Four Specific Challenges This Phase Solves

```
Challenge 1 — multiprocessing in a frozen .exe requires freeze_support()
               without it, packaged workers recursively relaunch the whole app

Challenge 2 — PyTorch (2GB+) + gradio web stack bundled naively = 4GB+ .exe folder
               need to exclude unused packages and verify nothing breaks

Challenge 3 — Chatterbox model weights live in HuggingFace cache, not in the project
               need a first-run download screen so users aren't staring at a frozen window

Challenge 4 — ffmpeg is on this machine's PATH but won't be on a clean user's machine
               need to bundle the ffmpeg binary with the distribution
```

## Packaging Strategy: Single-Folder, Not Single-File

PyInstaller can produce either one giant `.exe` file or a folder of files with a
launcher `.exe`. For this project, single-folder is the right choice:

- **Single-file** unpacks everything to a temp directory on every launch — with
  PyTorch's 2GB+ of files, that means 30–60 seconds of silent unpacking before the
  window appears. Users will think it crashed.
- **Single-folder** starts immediately — the launcher `.exe` is small, the rest of
  the files are already on disk next to it. Standard approach for large Python apps.

Distribution structure:
```
RealTimeConApp/
├── RealTimeConApp.exe     # launcher — double-click this
├── _internal/             # PyInstaller's bundled Python + all packages
│   └── ...
├── bin/
│   └── ffmpeg.exe         # bundled ffmpeg binary
├── scripts/               # user's .txt files and .wav reference clips go here
├── output/                # generated audio + captions.json written here
└── README.txt             # one-page: what to do on first launch, where to put files
```

## multiprocessing.freeze_support() — Most Critical Fix

This is the single most important change in Phase 7. Without it, the packaged `.exe`
will hang or spawn infinite processes when workers are launched.

In `main.py`, the very first lines after imports must be:

```python
import multiprocessing
multiprocessing.freeze_support()   # MUST be first — before any other logic
```

This tells Python's multiprocessing module that it's running inside a frozen
executable. Worker processes call `freeze_support()` and exit immediately when they
detect they're a worker, rather than re-running the full app. Without this call,
every worker spawn re-runs `main.py` from the top, which spawns more workers, and
so on until the machine runs out of memory or file handles.

This is a one-line fix with catastrophic consequences if omitted — verify it works
in the packaged build before anything else on Day 2.

## Model Weights Strategy: First-Run Download

Chatterbox's model weights (~1–2GB) are downloaded by `ChatterboxTTS.from_pretrained()`
to `~/.cache/huggingface/hub/` on first use. This cache persists across runs and is
already on this machine from Phase 1. On a clean user machine, the weights don't exist.

The approach: detect on startup whether the weights are already cached. If not, show
a "First Launch" screen before the normal app flow with a clear message and a download
button. The download runs `ChatterboxTTS.from_pretrained()` in a background thread
with a progress indicator, then proceeds normally once complete.

```
First launch on a clean machine:
        ↓
main.py detects: HuggingFace cache for chatterbox is empty
        ↓
"First Launch" screen appears:
"RealTimeConApp needs to download the voice model (~1.5 GB).
 This happens once. Internet connection required.
 [Download Now]"
        ↓
Download runs in background, progress bar updates
        ↓
Download complete → normal app flow begins (setup → render → player)
```

On all subsequent launches: cache exists, skip straight to normal flow. Zero extra
startup time after first run.

## ffmpeg Bundling

ffmpeg is currently on the system PATH from Phase 0's winget install. On a clean
user machine, it won't be. The fix: bundle `ffmpeg.exe` inside the distribution
in a `bin/` folder, and at app startup, prepend that folder to `os.environ["PATH"]`
before any audio processing begins. pydub, which uses ffmpeg internally, will find
it automatically once it's on PATH.

Where to get the bundled ffmpeg binary: download from https://www.gyan.dev/ffmpeg/builds/
— specifically the `ffmpeg-release-essentials.zip`, which contains just `ffmpeg.exe`
without the full GPL build. This is the standard Windows ffmpeg distribution used by
most Python audio projects.

The PATH prepend goes in `main.py`, immediately after `freeze_support()`:

```python
import os, sys
bin_dir = os.path.join(os.path.dirname(sys.executable), "bin")
os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
```

This works both in development (where `bin/` may not exist and system ffmpeg is used)
and in the packaged build (where `bin/ffmpeg.exe` is present).

## Size Optimization — Excluding the Gradio Web Stack

gradio, fastapi, starlette, uvicorn, aiohttp, pandas, and their dependencies arrived
as transitive dependencies of chatterbox-tts. They are completely unused by this app.
PyInstaller will bundle all of them by default — roughly 200–400MB of unnecessary files.

These go in the `.spec` file's `excludes` list:
```python
excludes=[
    'gradio', 'fastapi', 'starlette', 'uvicorn', 'aiohttp',
    'pandas', 'matplotlib', 'PIL', 'IPython', 'jupyter',
    'httpx', 'anyio', 'httpcore',
]
```

**Important:** after adding excludes, run the full app flow in the packaged build to
confirm nothing is silently broken. Some of these packages have transitive dependents
that are actually needed — if the app crashes on startup after adding an exclude,
remove it from the list and investigate before re-adding.

## Day-by-Day Plan

### Day 1 — Branch + freeze_support + First Build Attempt
- [ ] Create and switch to `phase7-packaging`
- [ ] Add `multiprocessing.freeze_support()` as the very first call in `main.py`
- [ ] Add ffmpeg PATH prepend in `main.py` (works transparently in dev mode too)
- [ ] Install PyInstaller into the venv: `pip install pyinstaller`
- [ ] Run a naive first build: `pyinstaller --windowed --name RealTimeConApp main.py`
- [ ] Try to launch the resulting `.exe` — what breaks? Document every error.
- [ ] Specifically verify: does the app start without recursively spawning? If yes,
  `freeze_support()` is working correctly.

**Checkpoint:** app launches from `.exe` without recursive spawning or immediate crash.
**Commit:** "Day 1: freeze_support added, first PyInstaller build attempted"

### Day 2 — .spec File: Hidden Imports + PyQt6 Plugins
- [ ] Generate a `.spec` file: `pyi-makespec --windowed --name RealTimeConApp main.py`
- [ ] Add hidden imports the naive build missed — common ones for this stack:
  ```python
  hiddenimports=[
      'chatterbox.tts',
      'torchaudio',
      'torchaudio.backend.soundfile_backend',
      'PyQt6.QtMultimedia',
      'PyQt6.QtMultimediaWidgets',
      'pydub',
      'soundfile',
  ]
  ```
- [ ] Add PyQt6 Qt plugins collection — without this, multimedia playback breaks:
  ```python
  from PyInstaller.utils.hooks import collect_all
  datas, binaries, hiddenimports = collect_all('PyQt6')
  ```
- [ ] Rebuild and re-test: does audio play? Do captions load? Does the render run?
- [ ] Document which hidden imports were actually needed vs which were unnecessary

**Checkpoint:** full app flow works in packaged build — setup, render, playback.
**Commit:** "Day 2: .spec file tuned, hidden imports and PyQt6 plugins resolved"

### Day 3 — ffmpeg Binary + Bundling
- [ ] Download `ffmpeg.exe` from https://www.gyan.dev/ffmpeg/builds/
  (ffmpeg-release-essentials build, just the .exe, not the full GPL suite)
- [ ] Place `ffmpeg.exe` in `bin/ffmpeg.exe` inside the project
- [ ] Add `bin/ffmpeg.exe` to the `.spec` file's `binaries` list:
  ```python
  binaries=[('bin/ffmpeg.exe', 'bin')]
  ```
- [ ] Temporarily rename the system ffmpeg or test in a clean environment to confirm
  the bundled binary is what the app actually uses during the packaged run
- [ ] Verify audio stitching and playback still work with the bundled binary

**Checkpoint:** app works with bundled ffmpeg.exe, not dependent on system PATH.
**Commit:** "Day 3: ffmpeg binary bundled and verified"

### Day 4 — Size Optimization
- [ ] Measure baseline folder size from Day 2's build
- [ ] Add excludes to `.spec` file (gradio stack + other unused packages listed above)
- [ ] Rebuild and measure new folder size
- [ ] Run full app flow again — confirm nothing is silently broken by the excludes
- [ ] If app crashes after an exclude: remove that package from the excludes list,
  rebuild, and note which exclude caused the issue in ARCHITECTURE.md
- [ ] Record before/after sizes in ARCHITECTURE.md

**Checkpoint:** folder size reduced, full app flow still works after exclusions.
**Commit:** "Day 4: unused dependencies excluded, size optimized"

### Day 5 — First-Run Model Download Screen
- [ ] Implement model cache detection in `main.py`:
  - Check if HuggingFace cache for chatterbox exists and is non-empty
  - If present: proceed normally to setup or player as before
  - If missing: launch `gui/first_run_window.py` before anything else
- [ ] Implement `gui/first_run_window.py`:
  - Clear message: what's being downloaded, approximate size, internet required
  - "Download Now" button — runs `ChatterboxTTS.from_pretrained()` in a
    background thread (same pattern as render_window.py's render thread)
  - Progress indicator (indeterminate spinner — HuggingFace Hub doesn't expose
    download progress callbacks, so a spinner is honest)
  - On completion: close first_run_window, proceed to normal app flow
  - On failure (no internet): clear error message with retry button
- [ ] Add `gui/first_run_window.py` to PyInstaller build, rebuild

**Checkpoint:** on a fresh machine (or with cache cleared), first-run screen appears,
download completes, app proceeds to normal flow automatically.
**Commit:** "Day 5: first-run model download screen implemented"

### Day 6 — Clean Machine Test
- [ ] Copy the packaged distribution folder to a different user account on this
  machine, or a machine without Python/venv — the goal is a genuinely clean test,
  not running from the same environment that built the package
- [ ] Delete or rename the HuggingFace cache to simulate a first launch
- [ ] Run the full flow from scratch: first-run download → setup → render → player
- [ ] Verify every part works without the venv, without Python on PATH,
  without system ffmpeg, without any development environment present
- [ ] Note any issues discovered and fix them before Day 7

**Checkpoint:** full app flow verified on a clean environment with no dev dependencies.
**Commit:** "Day 6: clean machine test passed"

### Day 7 — README + Distribution Polish
- [ ] Write `README.txt` for the distribution folder — one page, plain English:
  - What the app does (one sentence)
  - Where to put your script files (`scripts/speaker1.txt`, `scripts/speaker2.txt`)
  - Where to put your voice reference clips (`scripts/speaker1_ref.wav`, etc.)
  - What happens on first launch (model download, ~1.5GB, internet required once)
  - How to start a new conversation after rendering one (use the --setup flag,
    or delete the `output/` folder)
  - Known limitation: render takes ~28 min for a 10-minute conversation on CPU
- [ ] Zip the distribution folder
- [ ] Verify the zip extracts cleanly and the app runs from the extracted location

**Checkpoint:** distributable zip exists, extracts cleanly, app runs from extracted path.
**Commit:** "Day 7: README and distribution zip ready"

### Day 8 — Docs, Final Verification, Merge & Tag
- [ ] Update ARCHITECTURE.md with Phase 7 findings:
  - Final distribution folder size
  - Packages successfully excluded and any that couldn't be excluded
  - freeze_support() behavior confirmed in packaged build
  - First-run download behavior on clean machine
- [ ] Update this Phase7.md checklist
- [ ] Re-run Day 1–7 checkpoints once more, top to bottom
- [ ] Merge `phase7-packaging` → `main`
- [ ] Tag the merge commit: `phase7-complete`

**Checkpoint:** `main` contains the complete, packaged, distributable application.

## Buffer: Days 9–10 (use only if needed)

PyInstaller friction on a stack this complex is almost guaranteed to surface
something unexpected. Two most likely issues:

**torch DLL loading errors in packaged build:** PyTorch uses custom DLL loading
that PyInstaller sometimes misses. Symptom: app crashes immediately on launch with
a DLL load error. Fix: add `torch` to `collect_all()` in the `.spec` file, same
as PyQt6. Warning: this adds ~1.5GB to the folder size.

**HuggingFace Hub not finding cache in packaged build:** The Hub library resolves
cache paths relative to the user's home directory, which works fine in a packaged
build — but some versions check for environment variables that PyInstaller strips.
If `from_pretrained()` fails in the packaged build but works in dev, check
`HF_HOME` and `TRANSFORMERS_CACHE` environment variables.

## Definition of Done

- [ ] `multiprocessing.freeze_support()` confirmed working in packaged build
- [ ] Full app flow (setup → render → player) works from the `.exe`
- [ ] ffmpeg.exe bundled — app not dependent on system PATH
- [ ] Unused dependencies excluded, folder size documented
- [ ] First-run model download screen works on a clean machine
- [ ] Distribution zip verified to extract and run cleanly
- [ ] README.txt written for end users
- [ ] `phase7-packaging` merged into `main` and tagged `phase7-complete`