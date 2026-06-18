"""Sanity check: generates a short clip with Chatterbox's default voice and saves it to a .wav file."""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import torchaudio as ta

from tts_engine import load_model

TEST_SENTENCE = "This is a sanity check for the Chatterbox text to speech engine running on CPU."
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "output" / "day2_sanity_clip.wav"

if __name__ == "__main__":
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Loading Chatterbox model on CPU...")
    model = load_model()

    print("Generating clip for test sentence (default voice, no cloning)...")
    wav = model.generate(TEST_SENTENCE)

    ta.save(str(OUTPUT_PATH), wav, model.sr)
    print(f"Saved generated clip to {OUTPUT_PATH}")