"""Sanity check: clones Speaker 1 (male) voice and generates a test line."""

import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import torchaudio as ta

from tts_engine import load_model, generate_speech

TEST_LINE = "Hey, how are you doing today? I hope everything is going well on your end."
SPEAKER1_REF = Path(__file__).resolve().parent.parent / "scripts" / "speaker1_ref.wav"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "output" / "day2_speaker1_cloned.wav"

if __name__ == "__main__":
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Loading Chatterbox model on CPU...")
    load_start = time.perf_counter()
    model = load_model()
    load_time = time.perf_counter() - load_start
    print(f"Model loaded in {load_time:.2f}s")

    print(f"Cloning Speaker 1 voice from: {SPEAKER1_REF}")
    print(f"Generating: '{TEST_LINE}'")
    gen_start = time.perf_counter()
    wav = generate_speech(model, TEST_LINE, audio_prompt_path=str(SPEAKER1_REF))
    gen_time = time.perf_counter() - gen_start

    ta.save(str(OUTPUT_PATH), wav, model.sr)

    audio_seconds = wav.shape[-1] / model.sr
    real_time_factor = gen_time / audio_seconds

    print(f"Saved to: {OUTPUT_PATH}")
    print("--- Speaker 1 cloning timings ---")
    print(f"Model load time:     {load_time:.2f} s")
    print(f"Generation time:     {gen_time:.2f} s")
    print(f"Output audio length: {audio_seconds:.2f} s")
    print(f"Real-time factor:    {real_time_factor:.2f}x")