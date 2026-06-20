"""Drives turn-by-turn generation (batch in Phase 3, live in Phase 6)."""

import logging
import multiprocessing
from pathlib import Path

import torchaudio

import config
import tts_engine
from audio_utils import stitch_conversation
from captions import generate_captions

logger = logging.getLogger(__name__)

# ── Per-worker globals ────────────────────────────────────────────────────────
_model = None
_progress_queue = None
_cancel_event = None


def _worker_init(progress_queue, cancel_event):
    """
    Load the TTS model once per worker process at pool startup.
    Store the shared Queue and Event for use inside _worker_run.
    Must accept these explicitly — Windows spawn mode cannot inherit globals.
    """
    global _model, _progress_queue, _cancel_event
    name = multiprocessing.current_process().name
    print(f"  [{name}] loading model ...", flush=True)
    _model = tts_engine.load_model()
    _progress_queue = progress_queue
    _cancel_event = cancel_event
    print(f"  [{name}] model ready.", flush=True)


def _worker_run(args):
    """
    Process one chunk: generate every sub-clip and save numbered WAV files.

    Phase 6 additions:
    - Checks _cancel_event before each turn — raises InterruptedError if set.
    - Pushes a progress event to _progress_queue after each full turn completes.

    Progress event format:
        {"chunk_idx": int, "turn_idx": int, "speaker": str, "text": str}

    Handles the Phase 4 turn format:
        chunk["turns"] = [
            {"speaker": "S1", "sub_clips": [{"text": str, "pause_after": float}, ...]},
            ...
        ]

    Output filename per sub-clip:
        chunk_{chunk_idx:02d}_turn_{turn_idx:02d}_sc_{sc_idx:02d}.wav

    Self-contained and picklable — required for Windows spawn mode.
    """
    chunk, output_dir_str = args
    output_dir = Path(output_dir_str)

    chunk_idx = chunk["chunk_idx"]
    s1_ref = chunk["speaker1_ref"]
    s2_ref = chunk["speaker2_ref"]
    s1_settings = chunk["speaker1_settings"]
    s2_settings = chunk["speaker2_settings"]

    results = []

    for turn_idx, turn in enumerate(chunk["turns"]):
        # ── Cancel check (before each turn) ──────────────────────────────────
        if _cancel_event is not None and _cancel_event.is_set():
            raise InterruptedError(
                f"Render cancelled at chunk {chunk_idx}, turn {turn_idx}"
            )

        speaker = turn["speaker"]
        ref_clip = s1_ref if speaker == "S1" else s2_ref
        settings = s1_settings if speaker == "S1" else s2_settings

        for sc_idx, sub_clip in enumerate(turn["sub_clips"]):
            text = sub_clip["text"]
            pause_after = sub_clip["pause_after"]

            try:
                wav = tts_engine.generate_speech(
                    _model,
                    text,
                    audio_prompt_path=ref_clip,
                    **settings,
                )

                out_path = (
                    output_dir
                    / f"chunk_{chunk_idx:02d}_turn_{turn_idx:02d}_sc_{sc_idx:02d}.wav"
                )
                torchaudio.save(str(out_path), wav, _model.sr)

            except Exception as exc:
                raise RuntimeError(
                    f"Worker failed at chunk {chunk_idx}, turn {turn_idx}, "
                    f"sub-clip {sc_idx} ({speaker}: {text[:60]!r})"
                ) from exc

            results.append(
                {
                    "chunk_idx": chunk_idx,
                    "turn_idx": turn_idx,
                    "sub_clip_idx": sc_idx,
                    "speaker": speaker,
                    "path": str(out_path),
                    "text": text,
                    "pause_after": pause_after,
                }
            )

        # ── Progress event (after full turn — all sub-clips done) ─────────────
        if _progress_queue is not None:
            _progress_queue.put(
                {
                    "chunk_idx": chunk_idx,
                    "turn_idx": turn_idx,
                    "speaker": speaker,
                    "text": turn["sub_clips"][0]["text"][:60],
                }
            )

    return results


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cleanup_partial_output(output_dir: Path) -> None:
    """Delete partial chunk WAV files left behind after a cancelled render."""
    for f in output_dir.glob("chunk_*.wav"):
        try:
            f.unlink()
            print(f"  Deleted partial file: {f.name}")
        except Exception as exc:
            print(f"  Warning: could not delete {f.name}: {exc}")


# ── Public API ────────────────────────────────────────────────────────────────


def run_sequential(chunks: list, output_dir: Path = None) -> list:
    """
    Generate all turns sequentially — one model load, one loop, no workers.
    Updated for Phase 4: handles sub-clip turn format, includes text/pause_after
    in results, uses new sc-indexed filename format.
    """
    output_dir = Path(output_dir or config.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading model (once) ...")
    model = tts_engine.load_model()
    print("Model loaded.\n")

    results = []

    for chunk in chunks:
        chunk_idx = chunk["chunk_idx"]
        s1_ref = chunk["speaker1_ref"]
        s2_ref = chunk["speaker2_ref"]
        s1_settings = chunk["speaker1_settings"]
        s2_settings = chunk["speaker2_settings"]

        for turn_idx, turn in enumerate(chunk["turns"]):
            speaker = turn["speaker"]
            ref_clip = s1_ref if speaker == "S1" else s2_ref
            settings = s1_settings if speaker == "S1" else s2_settings

            for sc_idx, sub_clip in enumerate(turn["sub_clips"]):
                text = sub_clip["text"]
                pause_after = sub_clip["pause_after"]

                print(
                    f"  chunk {chunk_idx:02d} | turn {turn_idx:02d} | sc {sc_idx:02d} "
                    f"| {speaker} | {text[:60]}"
                )

                wav = tts_engine.generate_speech(
                    model,
                    text,
                    audio_prompt_path=ref_clip,
                    **settings,
                )

                out_path = (
                    output_dir
                    / f"chunk_{chunk_idx:02d}_turn_{turn_idx:02d}_sc_{sc_idx:02d}.wav"
                )
                torchaudio.save(str(out_path), wav, model.sr)
                print(f"    → saved: {out_path.name}\n")

                results.append(
                    {
                        "chunk_idx": chunk_idx,
                        "turn_idx": turn_idx,
                        "sub_clip_idx": sc_idx,
                        "speaker": speaker,
                        "path": str(out_path),
                        "text": text,
                        "pause_after": pause_after,
                    }
                )

    results.sort(key=lambda r: (r["chunk_idx"], r["turn_idx"], r["sub_clip_idx"]))
    return results


def run_parallel(
    chunks: list,
    output_dir: Path = None,
    num_workers: int = None,
    progress_queue: multiprocessing.Queue = None,
    cancel_event: multiprocessing.Event = None,
) -> list:
    """
    Generate all turns using multiprocessing.Pool with imap_unordered.

    Phase 6 additions:
    - progress_queue: workers push a dict after each turn completes.
      If None, an internal queue is created (progress events are discarded).
    - cancel_event: workers check this before each turn.
      If None, an internal event is created (cancel not available).
    - Returns [] on cancellation (no partial output left on disk).

    IMPORTANT — Windows spawn mode: caller must guard with `if __name__ == "__main__":`.
    """
    output_dir = Path(output_dir or config.OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    num_workers = num_workers or config.NUM_WORKERS

    # Create internal queue/event if caller didn't provide them
    if progress_queue is None:
        progress_queue = multiprocessing.Queue()
    if cancel_event is None:
        cancel_event = multiprocessing.Event()

    actual_workers = min(num_workers, len(chunks))
    total_turns = sum(len(c["turns"]) for c in chunks)
    args = [(chunk, str(output_dir)) for chunk in chunks]

    print(
        f"Pool: {actual_workers} worker(s) for {len(chunks)} chunk(s), "
        f"{total_turns} total turn(s)"
    )
    print("Workers loading models in parallel ...\n")

    all_results = []

    try:
        with multiprocessing.Pool(
            processes=actual_workers,
            initializer=_worker_init,
            initargs=(progress_queue, cancel_event),
        ) as pool:
            for chunk_results in pool.imap_unordered(_worker_run, args):
                all_results.extend(chunk_results)

    except InterruptedError:
        print("\nRender cancelled — cleaning up partial output ...")
        _cleanup_partial_output(output_dir)
        return []

    all_results.sort(key=lambda r: (r["chunk_idx"], r["turn_idx"], r["sub_clip_idx"]))
    return all_results


def render_conversation(
    chunks: list,
    output_dir: Path = None,
    num_workers: int = None,
    progress_queue: multiprocessing.Queue = None,
    cancel_event: multiprocessing.Event = None,
) -> Path | None:
    """
    Full pipeline: parallel generation → stitching → captions → finished WAV.

    Produces two output files:
        output/conversation_final.wav  — stitched audio
        output/captions.json           — word-level timestamps

    Both are derived from the same result set in the same pass, so clip
    durations used for timestamp derivation exactly match the audio.

    Returns the path to conversation_final.wav, or None if cancelled.

    IMPORTANT — Windows spawn mode: caller must guard with `if __name__ == "__main__":`.
    """
    results = run_parallel(
        chunks,
        output_dir=output_dir,
        num_workers=num_workers,
        progress_queue=progress_queue,
        cancel_event=cancel_event,
    )

    if not results:
        print("Render cancelled — no output produced.")
        return None

    final_path = stitch_conversation(results)
    print(f"Audio written:    {final_path}")

    captions_path = generate_captions(results)
    print(f"Captions written: {captions_path}")

    return final_path
