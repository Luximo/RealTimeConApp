"""Drives turn-by-turn generation (batch in Phase 3, live in Phase 6)."""

import logging
import multiprocessing
from pathlib import Path

import torchaudio

import config
import tts_engine

logger = logging.getLogger(__name__)

# ── Per-worker global ─────────────────────────────────────────────────────────
# Set once by _worker_init at pool startup; reused for every turn in that worker.
# Must live at module level — NOT inside a function — for Windows spawn mode.
_model = None


def _worker_init():
    """Load the TTS model once per worker process at pool startup."""
    global _model
    name = multiprocessing.current_process().name
    print(f"  [{name}] loading model ...", flush=True)
    _model = tts_engine.load_model()
    print(f"  [{name}] model ready.", flush=True)


def _worker_run(args):
    """
    Process one chunk: generate every turn and save numbered WAV files.
    Receives (chunk_dict, output_dir_str) — fully self-contained and picklable,
    which is required for Windows spawn mode.
    """
    chunk, output_dir_str = args
    output_dir = Path(output_dir_str)

    chunk_idx   = chunk["chunk_idx"]
    s1_ref      = chunk["speaker1_ref"]
    s2_ref      = chunk["speaker2_ref"]
    s1_settings = chunk["speaker1_settings"]
    s2_settings = chunk["speaker2_settings"]

    results = []

    for turn_idx, (speaker, text) in enumerate(chunk["turns"]):
        ref_clip = s1_ref      if speaker == "S1" else s2_ref
        settings = s1_settings if speaker == "S1" else s2_settings

        wav = tts_engine.generate_speech(
            _model, text,
            audio_prompt_path=ref_clip,
            **settings,
        )

        out_path = output_dir / f"chunk_{chunk_idx:02d}_turn_{turn_idx:02d}.wav"
        torchaudio.save(str(out_path), wav, _model.sr)

        results.append({
            "chunk_idx": chunk_idx,
            "turn_idx":  turn_idx,
            "path":      str(out_path),
        })

    return results


# ── Public API ────────────────────────────────────────────────────────────────

def run_sequential(chunks: list, output_dir: Path = None) -> list:
    """
    Generate all turns sequentially — one model load, one loop, no workers.
    Written on Day 2 to verify generation logic before parallelism is introduced.
    """
    output_dir = Path(output_dir or config.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading model (once) ...")
    model = tts_engine.load_model()
    print("Model loaded.\n")

    results = []

    for chunk in chunks:
        chunk_idx   = chunk["chunk_idx"]
        s1_ref      = chunk["speaker1_ref"]
        s2_ref      = chunk["speaker2_ref"]
        s1_settings = chunk["speaker1_settings"]
        s2_settings = chunk["speaker2_settings"]

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

    results.sort(key=lambda r: (r["chunk_idx"], r["turn_idx"]))
    return results


def run_parallel(chunks: list, output_dir: Path = None, num_workers: int = None) -> list:
    """
    Generate all turns using multiprocessing.Pool.

    Each worker loads the model once at pool init (via _worker_init), then
    processes its assigned chunk. Workers are capped at min(num_workers, len(chunks))
    so we never spin up idle processes that still pay the model-load cost.

    IMPORTANT — Windows spawn mode:
    The caller MUST guard the call to this function with:
        if __name__ == "__main__":
    Omitting that guard causes recursive process spawning and the pool hangs.
    """
    output_dir  = Path(output_dir or config.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    num_workers = num_workers or config.NUM_WORKERS

    actual_workers = min(num_workers, len(chunks))
    args = [(chunk, str(output_dir)) for chunk in chunks]

    print(f"Pool: {actual_workers} worker(s) for {len(chunks)} chunk(s)")
    print("Workers loading models in parallel ...\n")

    with multiprocessing.Pool(
        processes=actual_workers,
        initializer=_worker_init,
    ) as pool:
        chunk_results = pool.map(_worker_run, args)

    # Flatten and sort — pool.map preserves submission order, but we sort
    # explicitly so downstream code never has to assume that invariant.
    results = [r for chunk_result in chunk_results for r in chunk_result]
    results.sort(key=lambda r: (r["chunk_idx"], r["turn_idx"]))
    return results