# flux-tensor-midi v0.2 Roadmap

Prioritized from beta testing (internal + Grok external review)

## P0 — Critical for v0.2
- [ ] Jupyter notebook walkthrough (create band → tick → score → export MIDI)
- [ ] `FluxVector.from_dict({"arousal": 0.8, "valence": 0.6, ...})` 
- [ ] `Score.to_midi()` / `Score.from_midi()` (already partially done)
- [ ] Classic grid snapping fallback alongside Eisenstein
- [ ] Save/load Band state (serialization)

## P1 — Important
- [ ] Visualization: flux vector over time, rhythm lattice, coherence heatmap
- [ ] Real MIDI I/O (input from ports, output to synths/DAW)
- [ ] More docstrings: salience vs tolerance semantics, channel meanings
- [ ] Side-channel examples (nod/smile/frown workflows)
- [ ] Extreme BPM/jitter stability tests for EWMA clock

## P2 — Nice to have
- [ ] Python vs Rust benchmark comparison
- [ ] `Band.harmony()` exposed in public API with chord quality detail
- [ ] Integration with pretty_midi for downstream users
- [ ] Live coding examples (compatible with Sonic Pi / TidalCycles patterns)

## External validation
- Grok (external beta tester): "genuinely creative and well-executed"
- Conceptual framework is "original and sticky"
- Use cases: algorithmic composition, AI music agents, education, live coding
