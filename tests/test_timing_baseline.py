"""Day 5 timing baseline: 3 lines of varying length per speaker at tuned settings.
Results feed into Phase 3's parallel batch budget.
"""

import sys
import time
import tracemalloc
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

import torchaudio as ta

from tts_engine import load_model, generate_speech

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT / "output" / "timing"

# 3 lines of varying length
TEST_LINES = [
    ("short",  "See you later!"),
    ("medium", "Hey, how are you doing today? I hope everything is going well on your end."),
    ("long",   "I was thinking about what you said earlier, and honestly I think you make a really good point. It is something I had not considered before, but now that you mention it, it changes how I see the whole situation."),
]

# Tuned settings per speaker (Day 4 findings)
SPEAKERS = {
    "speaker1": {
        "ref": "scripts/speaker1_ref.wav",
        "exaggeration": 0.6,
        "cfg_weight": 0.4,
        "temperature": 0.85,
    },
    "speaker2": {
        "ref": "scripts/speaker2_ref.wav",
        "exaggeration": 0.7,
        "cfg_weight": 0.5,
        "temperature": 0.9,
    },
}

if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading Chatterbox model on CPU...")
    load_start = time.perf_counter()
    model = load_model()
    load_time = time.perf_counter() - load_start
    print(f"Model loaded in {load_time:.2f}s\n")

    results = []

    for speaker_name, settings in SPEAKERS.items():
        ref_path = str(ROOT / settings["ref"])
        print(f"=== {speaker_name.upper()} (exaggeration={settings['exaggeration']}, "
              f"cfg_weight={settings['cfg_weight']}, temperature={settings['temperature']}) ===")

        for length_label, text in TEST_LINES:
            out_path = OUTPUT_DIR / f"{speaker_name}_{length_label}.wav"

            # Measure memory during generation
            tracemalloc.start()
            gen_start = time.perf_counter()

            wav = generate_speech(
                model, text,
                audio_prompt_path=ref_path,
                exaggeration=settings["exaggeration"],
                cfg_weight=settings["cfg_weight"],
                temperature=settings["temperature"],
            )

            gen_time = time.perf_counter() - gen_start
            _, mem_peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            ta.save(str(out_path), wav, model.sr)

            audio_seconds = wav.shape[-1] / model.sr
            rtf = gen_time / audio_seconds
            mem_mb = mem_peak / 1024 / 1024

            results.append((speaker_name, length_label, len(text.split()), gen_time, audio_seconds, rtf, mem_mb))

            print(f"  [{length_label}] {len(text.split())} words → "
                  f"{audio_seconds:.2f}s audio | {gen_time:.2f}s gen | "
                  f"{rtf:.2f}x RTF | peak mem: {mem_mb:.1f} MB")

        print()

    print("=== SUMMARY (Phase 3 budget numbers) ===")
    print(f"{'Speaker':<10} {'Length':<8} {'Words':<6} {'GenTime':>8} {'Audio':>7} {'RTF':>6} {'MemMB':>8}")
    print("-" * 60)
    for row in results:
        print(f"{row[0]:<10} {row[1]:<8} {row[2]:<6} {row[3]:>8.2f}s {row[4]:>6.2f}s {row[5]:>6.2f}x {row[6]:>7.1f}MB")