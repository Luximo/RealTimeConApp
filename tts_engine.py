"""All calls to the TTS engine isolated here."""

import torch

# --- CPU loading patch (Day 3 finding, Phase 0 ARCHITECTURE.md) ---
# ChatterboxTTS.from_pretrained() calls torch.load() internally without
# map_location. The checkpoint files were saved from a CUDA context, so on
# a machine with no CUDA at all this throws a hard RuntimeError instead of
# loading on CPU. Known, open issue in resemble-ai/chatterbox, not specific
# to this setup. Fix: monkey-patch torch.load to default map_location="cpu"
# whenever it is not explicitly passed, before calling from_pretrained --
# same pattern Resemble AI uses in their own example_for_mac.py.
_original_torch_load = torch.load


def _patched_torch_load(*args, **kwargs):
    if "map_location" not in kwargs and len(args) < 2:
        kwargs["map_location"] = torch.device("cpu")
    return _original_torch_load(*args, **kwargs)


torch.load = _patched_torch_load

from chatterbox.tts import ChatterboxTTS


def load_model():
    """Load the Chatterbox TTS model on CPU."""
    return ChatterboxTTS.from_pretrained(device="cpu")

def generate_speech(model, text, audio_prompt_path=None,
                    exaggeration=0.5, cfg_weight=0.5, temperature=0.8):
    """Generate speech for text, with optional voice cloning via audio_prompt_path.
    
    Tuning knobs:
      exaggeration: 0.0-1.0, higher = more expressive/dramatic (default 0.5)
      cfg_weight:   0.0-1.0, higher = more faithful to prompt voice (default 0.5)
      temperature:  0.0-1.0, higher = more varied/less robotic (default 0.8)
    """
    return model.generate(
        text,
        audio_prompt_path=audio_prompt_path,
        exaggeration=exaggeration,
        cfg_weight=cfg_weight,
        temperature=temperature,
    )


if __name__ == "__main__":
    print("Loading Chatterbox TTS model on CPU...")
    model = load_model()
    print("Model loaded successfully:", type(model))