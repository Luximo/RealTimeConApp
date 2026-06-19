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

Living doc of how the pieces fit together — filled in as modules take shape.