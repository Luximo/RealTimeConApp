"""Sanity check: generates a short clip with Chatterbox's default voice and saves it to a .wav file."""

import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import torchaudio as ta

from tts_engine import load_model

TEST_SENTENCE = "This is a sanity check for the Chatterbox text to speech engine running on CPU."
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "output" / "day2_sanity_clip.wav"

if __name__ == "__main__":
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Loading Chatterbox model on CPU...")
    load_start = time.perf_counter()
    model = load_model()
    load_time = time.perf_counter() - load_start

    print("Generating clip for test sentence (default voice, no cloning)...")
    gen_start = time.perf_counter()
    wav = model.generate(TEST_SENTENCE)
    gen_time = time.perf_counter() - gen_start

    ta.save(str(OUTPUT_PATH), wav, model.sr)

    audio_seconds = wav.shape[-1] / model.sr
    real_time_factor = gen_time / audio_seconds

    print(f"Saved generated clip to {OUTPUT_PATH}")
    print("--- Day 3 performance baseline ---")
    print(f'Test sentence: "{TEST_SENTENCE}" ({len(TEST_SENTENCE.split())} words, {len(TEST_SENTENCE)} chars)')
    print(f"Model load time:     {load_time:.2f} s")
    print(f"Generation time:     {gen_time:.2f} s")
    print(f"Output audio length: {audio_seconds:.2f} s")
    print(f"Real-time factor:    {real_time_factor:.2f}x (seconds of CPU work per second of speech)")