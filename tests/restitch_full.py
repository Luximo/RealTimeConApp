"""Re-stitch the full conversation from existing Day 5 WAV files."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from script_parser import parse_script
from audio_utils import stitch_conversation

chunks  = parse_script()
results = []
for chunk in chunks:
    for turn_idx, (speaker, _) in enumerate(chunk["turns"]):
        p = config.OUTPUT_DIR / f"chunk_{chunk['chunk_idx']:02d}_turn_{turn_idx:02d}.wav"
        if p.exists():
            results.append({
                "chunk_idx": chunk["chunk_idx"],
                "turn_idx":  turn_idx,
                "speaker":   speaker,
                "path":      str(p),
            })

results.sort(key=lambda r: (r["chunk_idx"], r["turn_idx"]))
print(f"Re-stitching {len(results)} turn(s) from existing files ...")
final = stitch_conversation(results)
print(f"Written: {final}")