"""Day 4 quality tuning: generates variants at different knob settings per speaker."""

import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import torchaudio as ta

from tts_engine import load_model, generate_speech

TEST_LINE = "Hey, how are you doing today? I hope everything is going well on your end."

SPEAKERS = {
    "speaker1": "scripts/speaker1_ref.wav",
    "speaker2": "scripts/speaker2_ref.wav",
}

# Variants to try — (label, exaggeration, cfg_weight, temperature)
VARIANTS = [
    ("default",     0.5, 0.5, 0.8),
    ("expressive",  0.7, 0.5, 0.9),
    ("controlled",  0.3, 0.7, 0.7),
    ("natural",     0.6, 0.4, 0.85),
]

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output" / "tuning"

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading Chatterbox model on CPU...")
    model = load_model()
    print("Model loaded.\n")

    for speaker_name, ref_path in SPEAKERS.items():
        ref_full = ROOT / ref_path
        print(f"=== {speaker_name.upper()} ===")
        for label, exag, cfg, temp in VARIANTS:
            out_path = OUTPUT_DIR / f"{speaker_name}_{label}.wav"
            print(f"  Generating [{label}] exaggeration={exag} cfg_weight={cfg} temperature={temp} ...")
            start = time.perf_counter()
            wav = generate_speech(
                model, TEST_LINE,
                audio_prompt_path=str(ref_full),
                exaggeration=exag,
                cfg_weight=cfg,
                temperature=temp,
            )
            elapsed = time.perf_counter() - start
            ta.save(str(out_path), wav, model.sr)
            audio_seconds = wav.shape[-1] / model.sr
            print(f"  Saved to {out_path.name} ({audio_seconds:.2f}s audio, {elapsed:.2f}s gen)\n")

    print("All variants generated. Listen to output/tuning/ and pick the best per speaker.")