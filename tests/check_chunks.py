import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from script_parser import parse_script, _estimate_gen_time

chunks = parse_script()
total = sum(len(c["turns"]) for c in chunks)
print(f"{len(chunks)} chunks, {total} turns\n")

for c in chunks:
    t = sum(
        _estimate_gen_time(
            turn["speaker"], " ".join(sc["text"] for sc in turn["sub_clips"])
        )
        for turn in c["turns"]
    )
    speakers = " ".join(turn["speaker"] for turn in c["turns"])
    print(
        f"  Chunk {c['chunk_idx']}: {len(c['turns'])} turns [{speakers}]  ~{t:.0f}s est."
    )
