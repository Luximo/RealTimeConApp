# Phase 1 — TTS Engine: Get Chatterbox Running

**Project:** RealTimeConApp
**Branch for this phase:** `phase1-tts-engine` (off `main`)

## Goal

Prove the core TTS engine actually runs on this exact machine and produces audio — using its default built-in voice, no cloning, no orchestration, no GUI yet. This isolates the single riskiest unknown (does the model even run here) before anything else gets built on top of it.

## Known Issue to Address (carried over from Day 3 findings in ARCHITECTURE.md)

- `ChatterboxTTS.from_pretrained(device="cpu")` calls `torch.load()` internally without `map_location`, and the checkpoints were saved from a CUDA context — on this no-CUDA machine that throws a hard `RuntimeError` instead of loading.
- Fix: monkey-patch `torch.load` to default `map_location="cpu"` whenever it isn't explicitly passed, *before* calling `from_pretrained`, inside `tts_engine.py`.

## Day-by-Day Plan

### Day 1 — Branch & Patch
- [ ] Create and switch to `phase1-tts-engine`
- [ ] Implement the `torch.load` monkey-patch in `tts_engine.py`
- [ ] Write the minimal call to `ChatterboxTTS.from_pretrained(device="cpu")`

**Checkpoint:** the model loads without the CUDA `RuntimeError` — confirms the Day 3 fix actually works in practice, not just on paper.
**Commit:** "Day 1: torch.load CPU patch + model loads"

### Day 2 — First Generated Clip
- [ ] Add a small sanity test in `tests/` that calls the loaded model with a short, hardcoded sentence — default voice, no cloning
- [ ] Save the output as a `.wav` file
- [ ] Listen to it

**Checkpoint:** the `.wav` plays back as clear, intelligible speech.
**Commit:** "Day 2: first generated clip"

### Day 3 — Performance Baseline
- [ ] Time how long generation takes for that test sentence on this exact machine
- [ ] Log the result somewhere durable — a real first-hand number for this hardware, not someone else's benchmark

**Checkpoint:** a recorded generation time for a known text length, written into ARCHITECTURE.md.
**Commit:** "Day 3: generation time baseline recorded"

### Day 4 — Docs, Final Verification, Merge & Tag
- [ ] Update ARCHITECTURE.md with anything new found this phase
- [ ] Update this Phase1.md checklist
- [ ] Re-run Day 1–3 checkpoints once more, top to bottom
- [ ] Merge `phase1-tts-engine` → `main`
- [ ] Tag the merge commit: `phase1-complete`

**Checkpoint:** `main` now also contains a working, verified TTS engine call.

## Buffer: Day 5 (use only if needed)

Reserve in case the CPU patch needs more than one attempt, or installed dependency versions have drifted from what Day 3 pinned.

## Definition of Done

- [ ] Model loads on CPU without the `torch.load` error
- [ ] A test clip generates and plays back correctly
- [ ] Generation time baseline recorded for this machine
- [ ] `phase1-tts-engine` merged into `main` and tagged `phase1-complete`
