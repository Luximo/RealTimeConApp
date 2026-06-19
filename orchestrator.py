"""Drives turn-by-turn generation (batch in Phase 3, live in Phase 6)."""

import logging
from pathlib import Path

import torchaudio

import config
import tts_engine

logger = logging.getLogger(__name__)


def run_sequential(chunks: list, output_dir: Path = None) -> list:
    """
    Generate all turns sequentially — one model load, one loop, no workers.

    Used on Day 2 to verify generation logic is correct before parallelism
    is introduced on Day 3. Output files are identically named to what the
    parallel version will produce, so Day 3 can diff them directly.

    Returns a list of result dicts sorted by (chunk_idx, turn_idx):
        [{"chunk_idx": int, "turn_idx": int, "path": str}, ...]
    """
    output_dir = Path(output_dir or config.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading model (once) ...")
    model = tts_engine.load_model()
    print("Model loaded.\n")

    results = []

    for chunk in chunks:
        chunk_idx    = chunk["chunk_idx"]
        s1_ref       = chunk["speaker1_ref"]
        s2_ref       = chunk["speaker2_ref"]
        s1_settings  = chunk["speaker1_settings"]
        s2_settings  = chunk["speaker2_settings"]

        for turn_idx, (speaker, text) in enumerate(chunk["turns"]):
            ref_clip = s1_ref      if speaker == "S1" else s2_ref
            settings = s1_settings if speaker == "S1" else s2_settings

            print(f"  chunk {chunk_idx:02d} | turn {turn_idx:02d} | {speaker} | {text[:60]}")

            wav = tts_engine.generate_speech(
                model, text,
                audio_prompt_path=ref_clip,
                **settings,
            )

            out_path = output_dir / f"chunk_{chunk_idx:02d}_turn_{turn_idx:02d}.wav"
            torchaudio.save(str(out_path), wav, model.sr)
            print(f"    → saved: {out_path.name}\n")

            results.append({
                "chunk_idx": chunk_idx,
                "turn_idx":  turn_idx,
                "path":      str(out_path),
            })

    # Always sort by index — arrival order will be nondeterministic in Day 3's parallel mode
    results.sort(key=lambda r: (r["chunk_idx"], r["turn_idx"]))
    return results