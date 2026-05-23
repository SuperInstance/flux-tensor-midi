# flux-tensor-midi

**4-dimensional tensor representation of MIDI events.**  
6 languages: Python, Rust, C, CUDA, Fortran, JavaScript.

Room musicians, Eisenstein snap, INT8 saturation, side-channels.

---

## What It Does

flux-tensor-midi represents musical events as 4-dimensional tensors:

```
┌──────────────────────────────────────────────────────────┐
│                  TensorMIDIEvent (4D)                     │
├──────────────┬──────────────┬────────────┬───────────────┤
│  Time (T-0)  │   Intent     │  Harmony   │ SideChannel   │
│  Clock       │  (FluxVector)│  (Jaccard/ │  (Nod/Smile/  │
│  EWMA drift  │  9 channels  │   Chord)   │   Frown)      │
│  correction  │  INT8 sat.   │  Cosine    │  Ensemble     │
│              │  Salience    │  similarity│  coordination │
│              │  Tolerance   │            │               │
├──────────────┼──────────────┼────────────┼───────────────┤
│  When        │  What        │  How it    │  Body         │
│              │              │  relates   │  language     │
└──────────────┴──────────────┴────────────┴───────────────┘
```

Think of a jazz ensemble. Each musician (a "room") has their own sense of time (T-0 clock), their own expressive voice (FluxVector), awareness of how they fit with others (harmony), and non-verbal cues like nods, smiles, and frowns (side-channels).

### Core Concepts

**Room Musicians** — PLATO rooms as musicians. Each room has a clock, produces timestamped events, listens to others, and coordinates via side-channels.

**T-0 Clocks** — Adaptive clocks using Exponentially Weighted Moving Average (EWMA) for drift correction. Each room tracks its own temporal reference point ("T-zero") and smooths out timing jitter.

**FluxVectors** — 9-channel tensors with per-channel salience (importance) and tolerance (allowed jitter). The 9 channels map to: Arousal, Valence, Dominance, Uncertainty, Novelty, Relevance, Competence, Affiliation, Urgency. In Rust, channels use INT8 saturation (-128 to 127) for zero-allocation performance.

**EisensteinSnap** — Rhythmic quantization via the Eisenstein integer lattice (hexagonal tiling). The covering radius 1/√3 ≈ 0.577 provides optimal packing for snapping timestamps to musical grid points. Ratios map to rhythmic roles: unison (1:1), halftime (2:1), triplet (3:2), waltz (3:1), compound (4:3).

**Side-Channels** — Non-verbal communication between musicians:
- **Nod** (note-on) — acknowledgment, "I hear you," ready to proceed
- **Smile** (CC) — approval, harmonic agreement, positive reinforcement  
- **Frown** (note-off) — disagreement, dissonance, something's off

---

## Install

### Python (pip)

```bash
pip install flux-tensor-midi
```

Requires Python 3.10+. Zero external dependencies.

### Rust (cargo)

```toml
[dependencies]
flux-tensor-midi = "0.1"
```

Optional serde support: `flux-tensor-midi = { version = "0.1", features = ["serde"] }`

### C (cmake)

```bash
mkdir build && cd build
cmake ..
make
```

Headers in `include/flux_midi/`. Link against `libflux_midi.a`.

### JavaScript (npm)

```bash
npm install @superinstance/flux-tensor-midi
```

Zero dependencies. ESM module. Node.js >= 18.

### CUDA / Fortran

Build from source. See language-specific READMEs in `cuda/` and `fortran/`.

---

## Quick Start: Python

```python
from flux_tensor_midi import FluxVector, TZeroClock, RoomMusician, EisensteinSnap
from flux_tensor_midi.core.snap import RhythmicRole
from flux_tensor_midi.ensemble.band import Band

# Create musicians with different rhythmic roles
conductor = RoomMusician("conductor", role=RhythmicRole.ROOT)
bass = RoomMusician("bass", role=RhythmicRole.HALFTIME)
drums = RoomMusician("drums", role=RhythmicRole.DOUBLETIME)

# Set their states (9-channel vectors)
conductor.update_state(FluxVector([0.8, 0.6, 0.4, 0.2, 0.1, 0.9, 0.7, 0.5, 0.3]))
bass.update_state(FluxVector([0.5, 0.3, 0.8, 0.1, 0.0, 0.4, 0.6, 0.2, 0.7]))

# Bass listens to conductor
bass.listen_to(conductor)

# Emit events (clock advances, Eisenstein snap applied)
timestamp, vector = conductor.emit()
print(f"Conductor at {timestamp:.1f}ms: {vector.values}")

# Check coherence between rooms
coherence = conductor.coherence_with(bass)
print(f"Coherence: {coherence:.3f}")

# Form a band
band = Band("quartet", conductor=conductor, bpm=120.0)
band.add_musician(bass)
band.add_musician(drums)

# Tick all musicians together
events = band.tick_all()
for name, (ts, vec) in events.items():
    print(f"  {name}: {ts:.1f}ms")

# Analyze ensemble harmony
harmony = band.harmony()
print(f"Chord quality: {harmony.quality()}")
print(f"Consonance: {harmony.consonance():.3f}")
```

## Quick Start: Rust

```rust
use flux_tensor_midi::{
    FluxChannel, FluxVector, TZeroClock, RoomMusician,
    MidiEvent, Nod, Smile,
    jaccard_active, weighted_jaccard,
};

// Create a flux vector with INT8 channels
let mut channels = [FluxChannel::new(0); 9];
channels[0] = FluxChannel::new(80);  // Arousal
channels[1] = FluxChannel::with_cluster(64, 1);  // Valence, cluster 1
let flux = FluxVector::new(channels);

println!("Energy: {}", flux.energy());
println!("Mean: {:.2}", flux.mean());
println!("Std dev: {:.2}", flux.std_dev());

// T-0 clock with half-life smoothing
let mut clock = TZeroClock::with_half_life(10.0);
clock.tick(1.0);
clock.tick(2.0);
clock.tick(3.0);
println!("EWMA: {:.4}", clock.ema);
println!("Deviation: {:.4}", clock.deviation());

// Create a room musician
let mut musician = RoomMusician::new("bass", 3);
let event = MidiEvent::note_on(60, 100);
musician.receive_midi(&event, 1.0);

// Express into a flux vector
let mut room_flux = FluxVector::uniform(0);
musician.express_into(&mut room_flux);
println!("Room flux: {}", room_flux);

// Side-channels
let nod = Nod::from_midi_velocity(64, 127);
println!("Nod confidence: {:.2}", nod.confidence());

// Jaccard similarity
let a = FluxVector::uniform(100);
let b = FluxVector::uniform(50);
println!("Jaccard: {:.3}", jaccard_active(&a, &b));
```

---

## Architecture

```
flux-tensor-midi/
├── core/          FluxVector, TZeroClock, EisensteinSnap, RoomMusician
├── midi/          MidiEvent, MidiClock, channel mapping
├── harmony/       Jaccard similarity, chord quality, spectral analysis
├── ensemble/      Band (multi-musician), Score (recorded performance)
├── sidechannel/   Nod, Smile, Frown
└── adapters/      DAW bridge (Python)
```

### Layer Diagram

```
  ┌─────────────────────────────────────────┐
  │              ensemble/                   │
  │    Band · Score · listening matrix       │
  ├─────────────────────────────────────────┤
  │    sidechannel/                         │
  │    Nod · Smile · Frown                  │
  ├──────────┬──────────────────────────────┤
  │  harmony │                              │
  │  Jaccard · Chord · Spectrum             │
  ├──────────┴──────────────────────────────┤
  │    midi/                                │
  │    MidiEvent · Clock · Channel          │
  ├─────────────────────────────────────────┤
  │              core/                       │
  │  FluxVector · TZeroClock · Snap · Room  │
  └─────────────────────────────────────────┘
```

---

## Language Support Matrix

| Feature | Python | Rust | C | CUDA | Fortran | JS |
|---------|--------|------|---|------|---------|----|
| FluxVector | ✅ float | ✅ INT8 | ✅ struct | ✅ | ✅ | ✅ |
| TZeroClock | ✅ EWMA | ✅ EWMA | ✅ EWMA | ✅ | ✅ | ✅ |
| EisensteinSnap | ✅ | ✅ SnapRatio | ✅ | ✅ | ✅ | ✅ |
| RoomMusician | ✅ | ✅ | ✅ | — | ✅ | ✅ |
| MidiEvent | ✅ | ✅ | ✅ | — | — | ✅ |
| SideChannels | ✅ | ✅ Nod/Smile/Frown | ✅ | — | — | ✅ |
| Harmony/Jaccard | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ChordQuality | ✅ | ✅ | — | — | — | — |
| Band (ensemble) | ✅ | ✅ | ✅ | ✅ | — | ✅ |
| Score (recording) | ✅ | ✅ | — | — | — | ✅ |
| Spectral analysis | ✅ | ✅ DCT | ✅ | ✅ | ✅ | — |
| Serde/serialization | — | ✅ optional | — | — | — | ✅ JSON |
| Package manager | PyPI | crates.io | cmake | cmake | cmake | npm |

---

## Documentation

- [User Guide](docs/USER-GUIDE.md) — Complete usage documentation
- [Developer Guide](docs/DEVELOPER-GUIDE.md) — Contributing and internals
- [Roadmap](docs/ROADMAP.md) — Planned features and direction
- [Examples](examples/) — Working code in Python
- [Demos](demos/) — Full demonstration scripts

## Related Projects

- **[plato-midi-bridge](https://github.com/SuperInstance/plato-midi-bridge)** — Connect PLATO rooms to real MIDI hardware
- **[counterpoint-engine](https://github.com/SuperInstance/counterpoint-engine)** — Species counterpoint generation using flux tensors
- **[groove-analyzer](https://github.com/SuperInstance/groove-analyzer)** — Micro-timing analysis with Eisenstein lattice

---

## License

Apache 2.0
