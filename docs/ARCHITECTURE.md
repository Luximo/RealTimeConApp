# Architecture

## Environment Notes (Day 3 findings)

**Target Python: 3.11**, not whatever's newest on the machine. Chatterbox is developed and tested on 3.11; Python 3.13 has documented PyTorch/torchvision wheel resolution failures for this stack.

**CPU loading bug — patch required in `tts_engine.py`:** `ChatterboxTTS.from_pretrained(device="cpu")` calls `torch.load()` internally without a `map_location`, and the checkpoint files were saved from a CUDA context. On a machine with no CUDA at all, this throws a hard `RuntimeError` instead of loading on CPU. This is a known, open issue in the upstream library (resemble-ai/chatterbox), not specific to this setup. Fix: monkey-patch `torch.load` to default `map_location="cpu"` whenever it isn't explicitly passed, *before* calling `from_pretrained`. Same pattern Resemble AI uses in their own `example_for_mac.py`.

**Dependency surprises from `pip install chatterbox-tts==0.1.7`:**
- Hard-pins `torch==2.6.0` and `torchaudio==2.6.0` — overrides whatever version is manually installed beforehand. Resolved build is still CPU-only (`2.6.0+cpu`), so this doesn't break the CPU-first plan, just fixes the exact version.
- Pulls in `gradio` and its full demo-app web stack (fastapi, starlette, uvicorn, pandas, etc.) as a hard dependency, unused by this project. Harmless, just bulkier than expected.
- `pydub` and `soundfile` arrive for free as transitive dependencies (via gradio and librosa respectively) — covers the audio-library need without a separate install step.

## TTS Engine API Notes (Phase 1 findings)

**Import path:** `from chatterbox.tts import ChatterboxTTS` — confirmed against the installed `0.1.7` source rather than assumed, since wrapper APIs like this can shift between versions.

**`generate()` signature:** `generate(text, repetition_penalty=1.2, min_p=0.05, top_p=1.0, audio_prompt_path=None, exaggeration=0.5, cfg_weight=0.5, temperature=0.8)`. The three knobs that matter for tuning naturalness later are `exaggeration`, `cfg_weight`, and `temperature` — left untouched at their defaults for Phase 1's purposes.

**Default voice mechanism:** `from_pretrained()` downloads and loads a built-in `conds.pt` (~107KB) that pre-populates `self.conds`. `generate()` has a hard assertion — `assert self.conds is not None` — if no `audio_prompt_path` is given and conds were somehow missing, so the default-voice path only "just works" because that file loads automatically; there's no silent fallback. For Phase 2, voice cloning happens by passing a reference clip through `audio_prompt_path`, which internally calls `self.prepare_conditionals(audio_prompt_path, exaggeration=exaggeration)` to replace `self.conds` with the cloned voice's conditioning.

**Return value:** a `torch.Tensor` shaped `(1, N)` (mono, channels-first) with Resemble's Perth watermark already baked in — watermarking isn't optional or toggleable through any parameter seen in this version. `model.sr` holds the sample rate, used directly with `torchaudio.save(path, wav, model.sr)`.

**Output quality at defaults:** the built-in default voice sounds flat and somewhat robotic — closer to a GPS/navigation voice than natural speech — at the default `exaggeration=0.5`, `cfg_weight=0.5`, `temperature=0.8`. Not a bug; this voice was never meant to be the final product. Real naturalness evaluation is deferred to Phase 2, once actual reference clips are in the loop.

**Benign warnings seen on every load/generate call** (logged once here so they don't get re-investigated every phase): an unauthenticated-HF-Hub-requests notice, a `LoRACompatibleLinear` deprecation from `diffusers`, a `torch.backends.cuda.sdp_kernel()` deprecation, and an `sdpa`/`output_attentions` notice. All are upstream library noise unrelated to this project's code — none require action.

## Performance Baseline (Phase 1, Day 3)

Single run, default built-in voice, no cloning, on the project's target hardware (Ryzen 7 5700G, CPU-only — the RX 6750 XT has no reliable ROCm path on this setup, see environment notes above).

**Test sentence:** "This is a sanity check for the Chatterbox text to speech engine running on CPU." (15 words, 79 characters)

**Recorded numbers:**
- Model load time: 7.89 s
- Generation time: 30.16 s
- Output audio length: 4.08 s
- Real-time factor: 7.39x (CPU seconds spent per second of generated speech)

Of the 30.16s generation time, roughly the first 18s is the autoregressive token-sampling pass (visible in the `Sampling` progress bar); the remainder belongs to the `s3gen` vocoder and watermarking steps that follow it.

**Implication:** at ~7.4x real-time, CPU-only generation suits Phase 3's pre-render approach fine, since the whole conversation only needs to be rendered once before playback. It's a number worth flagging for Phase 6, though — a live generate-and-play pipeline at this speed would feel sluggish without GPU acceleration, a faster model, or some pipelining trick. Not a blocker now, just a flag for later.

## Voice Cloning Findings (Phase 2)

### Reference Clips
Both clips recorded by the actual speakers, converted to proper WAV format via ffmpeg
(originals were 3GP/AMR from phone recordings). Final format: 44100Hz, mono, 16-bit PCM.
- `scripts/speaker1_ref.wav` — male voice, 31.17s
- `scripts/speaker2_ref.wav` — female voice, 30.44s

Note: speaker2_ref source was AMR at 8000Hz (phone voice memo). Upsampled to 44100Hz on
conversion — cloning quality was still verified acceptable on listening test.

### How Cloning Works (confirmed against 0.1.7 source)
Passing `audio_prompt_path` to `generate()` triggers an internal call to
`prepare_conditionals(audio_prompt_path, exaggeration=exaggeration)`, which replaces
`self.conds` with conditioning derived from the reference clip. Zero-shot — no training,
no fine-tuning, happens at generation time on every call.

### Tuned Settings Per Speaker (Day 4 findings)
Both voices verified to sound recognizably like their reference clips at these settings.
Speaker 1 and Speaker 2 respond differently — do not use the same settings for both.

**Speaker 1 (male):**
- exaggeration: 0.6
- cfg_weight: 0.4
- temperature: 0.85
- Variant label: "natural"

**Speaker 2 (female):**
- exaggeration: 0.7
- cfg_weight: 0.5
- temperature: 0.9
- Variant label: "expressive"

### Timing Baseline With Cloning (Day 5 findings)
Measured on Ryzen 7 5700G, CPU-only, at tuned settings per speaker.
Same hardware as Phase 1 baseline (7.39x RTF, no cloning).

| Speaker  | Length | Words | Gen Time | Audio  | RTF    | Peak Mem |
|----------|--------|-------|----------|--------|--------|----------|
| speaker1 | short  | 3     | 25.13s   | 1.08s  | 23.27x | 23.4 MB  |
| speaker1 | medium | 15    | 53.43s   | 5.16s  | 10.36x | 14.4 MB  |
| speaker1 | long   | 40    | 99.57s   | 12.24s | 8.13x  | 14.4 MB  |
| speaker2 | short  | 3     | 19.72s   | 1.36s  | 14.50x | 14.0 MB  |
| speaker2 | medium | 15    | 43.45s   | 4.80s  | 9.05x  | 14.0 MB  |
| speaker2 | long   | 40    | 82.42s   | 10.00s | 8.24x  | 14.0 MB  |

**Key implications for Phase 3:**
- Budget ~8–10x RTF for medium/long lines (the realistic conversation range)
- Short lines (<5 words) are outliers at 14–23x RTF due to fixed model startup overhead
  — avoid splitting dialogue into tiny fragments in the batch renderer
- Peak memory per worker (Python-side): ~14MB — 8 parallel workers won't fight over RAM
- Speaker 2 generates consistently faster than Speaker 1 at equivalent word counts
- Model load time with cloning: ~8–13s (vs 7.89s Phase 1 baseline) — load once, reuse

## Phase 3 Findings

### Parallel Batch Render Timing (best run, 16-turn sample script)

| Metric              | Value                  |
|---------------------|------------------------|
| Total turns         | 16                     |
| Chunks              | 7                      |
| Workers used        | 7                      |
| Wall-clock time     | 622.6s (10.4 min)      |
| Sequential estimate | 724.6s                 |
| Parallel speedup    | 1.16x                  |
| Output audio length | 70.58s                 |
| Inter-speaker pause | 0.3s (tuned Day 4)     |

**Speedup reality on this hardware:** With 7 workers competing for 8 cores, each worker
gets ~1 core and runs ~4–5x slower individually. Wall-clock time is gated by the slowest
chunk, so speedup is modest (1.09–1.16x across runs) on a 16-turn script. The real payoff
will appear with GPU acceleration (Phase 6) or on hardware with more cores.

**Implication for longer scripts:** At ~1.1x speedup on this hardware, a 60-turn
(~10 min audio) conversation would render in roughly 38–42 min wall-clock time on CPU.

### Audio Pipeline Tuning (Days 4–6)

- **Inter-speaker pause:** tuned to **0.3s** (down from default 0.4s) for natural flow
- **Merge separator:** changed from `", "` to `" "` (space) — comma caused TTS to
  insert an unnatural pause mid-merged-turn
- **Silence trimming:** `-45 dBFS` threshold, `150ms` minimum — strips leading/trailing
  dead air that TTS sometimes generates at utterance boundaries
- **Fade-in per clip:** `25ms` — eliminates leading plosive ("B") artifacts from
  voice conditioning at the start of male speaker turns
- **Worker error wrapping:** `_worker_run` wraps generation in try/except and re-raises
  with `chunk_idx`, `turn_idx`, speaker, and text context for readable failure messages

### Edge Cases Verified (Day 6)

- Unequal line counts: parser warns and stops at shorter file, no silent data loss ✅
- Very long turn (61 words): kept as one atomic turn, no split ✅
- Fewer chunks than workers: pool caps at `min(NUM_WORKERS, len(chunks))` ✅
- Worker failure: exception propagates through `pool.map` cleanly, no hang ✅

**Key implication for longer scripts:**
At 1.16x speedup on a 16-turn script, a 60-turn (~10 min audio)
conversation would render in roughly 38.9 min wall-clock time.


## Phase 4 Findings

### Caption Timing Design
Word-level timestamps are derived proportionally from clip durations — no transcription
model used. For each sub-clip, its trimmed duration is divided evenly across its words:

    word_start = clip_start + (word_idx / word_count) * clip_duration
    word_end   = clip_start + ((word_idx + 1) / word_count) * clip_duration

This is faster, fully offline, and grounded in the actual audio structure rather than
inferred from it. Approximation is inherent — short words ("I", "a") get the same time
slice as long words ("conversation", "frustrating") — but is acceptable for scrolling
caption display where turn-level sync matters more than frame-accurate word highlighting.

### [pause:N] Marker System
Four formats supported, constants defined in `config.py`:

| Marker          | Duration             |
|-----------------|----------------------|
| `[pause]`       | DEFAULT_PAUSE_DURATION = 0.5s |
| `[pause:short]` | SHORT_PAUSE_DURATION  = 0.3s |
| `[pause:long]`  | LONG_PAUSE_DURATION   = 3.0s |
| `[pause:N]`     | exactly N seconds (float or int) |

Markers are stripped before any TTS call — Chatterbox never sees them. Each turn is
split into sub-clips at marker positions; each sub-clip gets its own WAV file and its
own timestamp range in captions.json. The silence between sub-clips is inserted by
`stitch_conversation` using the `pause_after` field carried in every result dict.

Edge cases verified:
- Multiple consecutive markers in one turn → each pause duration preserved correctly
- Marker at very start of turn → duration discarded (nothing to hold), warning logged
- Marker at very end of turn → pause_after forced to 0.0 (last sub-clip rule)
- Turn consisting entirely of markers (no words) → empty sub-clip list, turn skipped
  with warning, surrounding turns unaffected
- Script with no markers → single sub-clip per turn, timestamps correct throughout

### captions.json Format (Phase 5 reference)
Written to `output/captions.json` automatically on every `render_conversation()` call.
One entry per word, globally ordered:

```json
[
  {"word": "Did",   "start": 0.000, "end": 0.237, "speaker": "S1"},
  {"word": "you",   "start": 0.237, "end": 0.474, "speaker": "S1"},
  {"word": "Don't", "start": 2.431, "end": 2.701, "speaker": "S2"},
  ...
]
```

- `word` — clean text token (punctuation attached, markers stripped)
- `start` / `end` — absolute seconds from the start of `conversation_final.wav`
- `speaker` — "S1" or "S2", from turn metadata, never from transcription

The 0.3s gap between the last S1 word's `end` and the first S2 word's `start` is
`INTER_SPEAKER_PAUSE`. Phase 5 detects this gap to trigger screen clears and visual
speaker transitions.

For `[pause:N]` gaps within a turn: the last word of the pre-pause sub-clip holds on
screen for N seconds, then the next sub-clip's words begin. No entry is emitted for
the silence itself — it appears as a gap in the timestamps.

### Timestamp Accuracy (Day 5 observations)
- Python `time.sleep()` accuracy: **+0.2ms average offset** — precise enough for
  caption display; no drift accumulation across 187 words / 63s of content
- Perceptual sync is good at the **turn level** (speaker switches happen at the right
  moments); individual word timing within a turn is approximate by design
- Captions and audio **must be produced in the same pipeline pass** to guarantee
  consistent clip durations. Using mismatched processing paths (e.g. a Phase 3 restitch
  vs Phase 4 `build_captions`) causes compounding drift that makes speaker labels appear
  offset by one turn. Day 6's `render_conversation()` fixes this by calling both
  `stitch_conversation` and `generate_captions` on the same result set.

### Output File Naming (Phase 4 format)
Sub-clip WAV files use a three-part index:

    chunk_{chunk_idx:02d}_turn_{turn_idx:02d}_sc_{sc_idx:02d}.wav

For turns with no pause markers, `sc_idx` is always `00`. Turns with markers produce
`sc_00`, `sc_01`, ... for each text segment between markers.

### Phase 4 Verification Stats (Day 4)
- Script: 16 turns, 7 chunks, 187 total words
- captions.json final timestamp: 63.37s
- All 11 structural checks passed: ascending timestamps, correct word count,
  correct speaker labels, no overlaps, no negatives, start < end for every entry

## Phase 5 Findings

### GUI Stack (confirmed working)
- **PyQt6 6.11.0** + **PyQt6-Qt6 6.11.1** — installed via `pip install PyQt6`
- Qt multimedia backend: **FFmpeg 7.1.3** (auto-detected from the ffmpeg 8.1.1
  install done in Phase 0 — no separate multimedia extras package needed)
- `QMediaPlayer` + `QAudioOutput` for WAV playback with millisecond position tracking
- `QTimer` at 30ms interval for the caption animation loop
- `QPainter` on a custom `QWidget` (`ScrollingCaptionWidget`) for all scrolling text
- `QMediaPlayer.setPlaybackRate()` confirmed pitch-preserving on Windows at 0.5x–2.0x
  — no ffmpeg call or external time-stretch library needed

### Caption Sync Approach
`QMediaPlayer.position()` returns position in **media time** (not wall-clock time),
so caption timestamp comparisons (`entry["start"] <= pos_s`) work correctly at any
playback speed without recalculating timestamps. The speed factor only needs to scale
the scroll pixel rate, not the timestamp comparisons.

### Scrolling Animation Design
Words enter from the right edge (`x = widget.width() + WORD_SPACING`) when their
audio timestamp fires. Natural spacing between words comes from the timing gap between
fires multiplied by scroll speed — no cumulative x-position tracking is needed.

**Key bug found and fixed (Day 4):** Tracking a cumulative `_next_x` that both scrolls
left and accumulates new word widths causes words to pile up invisibly off the right
edge when the word-addition rate exceeds the scroll rate. At 3 words/sec × ~94px per
word = 282 px/sec of content added vs 120 px/sec scroll, `_next_x` grew at +162 px/sec,
making words appear on screen seconds late. Fix: always place new words at
`x = width + WORD_SPACING`; natural spacing is created by timing alone.

### Tuned Display Constants (config.py)
| Constant                      | Value      | Notes                                  |
|-------------------------------|------------|----------------------------------------|
| `SCROLL_SPEED_BASE`           | 250 px/s   | Tuned Day 4; feels natural at 1.0x     |
| `CAPTION_FONT_SIZE`           | 28 pt      | Readable at normal viewing distance    |
| `CAPTION_FONT_FAMILY`         | Segoe UI   | Native Windows, clean on dark bg       |
| `SPEAKER_LABEL_DISPLAY_DURATION` | 1.0s    | Fade-out over ~33 ticks at 30ms each   |
| `LEFT_MARGIN` / `FADE_WIDTH`  | 55 / 60 px | Wrap triggers just inside the fade zone|

### Speaker Visual Identity
- S1 (male): teal `#4ecca3` — words, label, transition flash
- S2 (female): amber `#f5a623` — words, label, transition flash
- Older lines fade in opacity (1.0 → 0.72 → 0.44 → 0.25 per line above bottom)
- Left-edge gradient: `#1a1a2e` opaque → transparent over 60px — words melt away
  rather than hard-clipping as they exit

### Line Wrap Logic
Wrap triggers when the leftmost word on the bottom line reaches `LEFT_MARGIN = 55px`.
On wrap: all existing words shift up by `line_height`, pruning any that go above the
widget top. The bottom line resets and the new word enters at the right edge.
At 250 px/s and ~3 words/sec, a line typically holds 10–12 words before wrapping.

### captions.py — load_captions() added (Phase 5)
Phase 4 left `captions.py` with only `generate_captions()` (render-time).
Phase 5 added `load_captions(path=None) -> list` — reads `captions.json` from disk
and returns the word entry list. `gui/player_window.py` calls this once at startup.

### Known Sync Limitation (carried from Phase 4)
Captions and audio must be produced in the same pipeline pass. The existing
`output/captions.json` and `output/conversation_final.wav` were produced in different
passes during Phase 4 development, causing turn-level drift (audio says one speaker's
words while captions show the other's, converging toward the end). This will resolve
automatically when the full pipeline is re-run end-to-end after Phase 5 — `render_conversation()`
already guarantees both are produced from the same result set.

Living doc of how the pieces fit together — filled in as modules take shape.