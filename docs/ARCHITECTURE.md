# Architecture

## Environment Notes (Day 3 findings)

**Target Python: 3.11**, not whatever's newest on the machine. Chatterbox is developed and tested on 3.11; Python 3.13 has documented PyTorch/torchvision wheel resolution failures for this stack.

**CPU loading bug — patch required in `tts_engine.py`:** `ChatterboxTTS.from_pretrained(device="cpu")` calls `torch.load()` internally without a `map_location`, and the checkpoint files were saved from a CUDA context. On a machine with no CUDA at all, this throws a hard `RuntimeError` instead of loading on CPU. This is a known, open issue in the upstream library (resemble-ai/chatterbox), not specific to this setup. Fix: monkey-patch `torch.load` to default `map_location="cpu"` whenever it isn't explicitly passed, *before* calling `from_pretrained`. Same pattern Resemble AI uses in their own `example_for_mac.py`.

**Dependency surprises from `pip install chatterbox-tts==0.1.7`:**
- Hard-pins `torch==2.6.0` and `torchaudio==2.6.0` — overrides whatever version is manually installed beforehand. Resolved build is still CPU-only (`2.6.0+cpu`), so this doesn't break the CPU-first plan, just fixes the exact version.
- Pulls in `gradio` and its full demo-app web stack (fastapi, starlette, uvicorn, pandas, etc.) as a hard dependency, unused by this project. Harmless, just bulkier than expected.
- `pydub` and `soundfile` arrive for free as transitive dependencies (via gradio and librosa respectively) — covers the audio-library need without a separate install step.

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

Living doc of how the pieces fit together — filled in as modules take shape.