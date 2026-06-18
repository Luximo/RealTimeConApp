# Architecture

## Environment Notes (Day 3 findings)

**Target Python: 3.11**, not whatever's newest on the machine. Chatterbox is developed and tested on 3.11; Python 3.13 has documented PyTorch/torchvision wheel resolution failures for this stack.

**CPU loading bug — patch required in `tts_engine.py`:** `ChatterboxTTS.from_pretrained(device="cpu")` calls `torch.load()` internally without a `map_location`, and the checkpoint files were saved from a CUDA context. On a machine with no CUDA at all, this throws a hard `RuntimeError` instead of loading on CPU. This is a known, open issue in the upstream library (resemble-ai/chatterbox), not specific to this setup. Fix: monkey-patch `torch.load` to default `map_location="cpu"` whenever it isn't explicitly passed, *before* calling `from_pretrained`. Same pattern Resemble AI uses in their own `example_for_mac.py`.

**Dependency surprises from `pip install chatterbox-tts==0.1.7`:**
- Hard-pins `torch==2.6.0` and `torchaudio==2.6.0` — overrides whatever version is manually installed beforehand. Resolved build is still CPU-only (`2.6.0+cpu`), so this doesn't break the CPU-first plan, just fixes the exact version.
- Pulls in `gradio` and its full demo-app web stack (fastapi, starlette, uvicorn, pandas, etc.) as a hard dependency, unused by this project. Harmless, just bulkier than expected.
- `pydub` and `soundfile` arrive for free as transitive dependencies (via gradio and librosa respectively) — covers the audio-library need without a separate install step.
- 
Living doc of how the pieces fit together — filled in as modules take shape.
