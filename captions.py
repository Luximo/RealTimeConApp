"""Word-timestamp alignment for the scrolling captions."""

import json
from pathlib import Path

import config
from audio_utils import build_captions


def generate_captions(results: list, output_path=None) -> Path:
    """
    Build word-level timestamps from stitching results and write captions.json.

    This is the single entry point for caption generation — Phase 5 imports
    from here, not directly from audio_utils.

    Args:
        results:     List of sub-clip result dicts (same format as stitch_conversation).
                     Each dict must have:
                         chunk_idx    (int)
                         turn_idx     (int)
                         sub_clip_idx (int, default 0)
                         speaker      ("S1" | "S2")
                         path         (str | Path)
                         text         (str) — clean words, markers already stripped
                         pause_after  (float, default 0.0)
        output_path: Destination path for captions.json.
                     Defaults to output/captions.json.

    Returns:
        Path to the written captions.json file.
    """
    output_path = Path(output_path or (config.OUTPUT_DIR / "captions.json"))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    caption_data = build_captions(results)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(caption_data, f, indent=2, ensure_ascii=False)

    return output_path
