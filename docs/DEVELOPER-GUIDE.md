# Developer Guide

Architecture, contributing, and extending flux-tensor-midi.

---

## Architecture

The codebase is organized into five layers, each building on the one below:

```
┌──────────────────────────────────────────────────────────┐
│  ensemble/                                               │
│  Band · Score · listening matrix · harmony aggregation    │
├──────────────────────────────────────────────────────────┤
│  sidechannel/                                            │
│  Nod · Smile · Frown — non-verbal ensemble signals       │
├──────────────────────────────────────────────────────────┤
│  harmony/                                                │
│  Jaccard · ChordQuality · Spectrum (DCT/centroid/flux)   │
├──────────────────────────────────────────────────────────┤
│  midi/                                                   │
│  MidiEvent · MidiClock (24 PPQN) · Channel mapping       │
├──────────────────────────────────────────────────────────┤
│  core/                                                   │
│  FluxVector · TZeroClock · EisensteinSnap · RoomMusician │
└──────────────────────────────────────────────────────────┘
```

### Directory Structure

```
flux-tensor-midi/
├── python/               Python package (PyPI: flux-tensor-midi)
│   ├── flux_tensor_midi/
│   │   ├── core/         FluxVector, TZeroClock, RoomMusician, Snap
│   │   ├── midi/         MidiEvent, MidiClock, Channel
│   │   ├── harmony/      Jaccard, ChordQuality, Spectrum
│   │   ├── ensemble/     Band, Score
│   │   ├── sidechannel/  Nod, Smile, Frown
│   │   └── adapters/     daw_bridge.py
│   ├── tests/
│   └── pyproject.toml
├── rust/                 Rust crate (crates.io: flux-tensor-midi)
│   ├── src/
│   │   ├── core/         tensor.rs, mod.rs (FluxVector, TZeroClock, RoomMusician, SnapRatio)
│   │   ├── midi/         events.rs, clock.rs, channel.rs
│   │   ├── harmony/      jaccard.rs, chord.rs, spectrum.rs
│   │   ├── ensemble/     band.rs, score.rs
│   │   └── sidechannel/  nod.rs, smile.rs, frown.rs
│   └── Cargo.toml
├── c/                    C library (cmake)
│   ├── include/flux_midi/  Headers
│   ├── src/                Implementation
│   └── tests/              Unity-based tests
├── cuda/                 CUDA kernels (cmake)
│   ├── include/          Headers (.cuh)
│   └── src/              Kernel implementations (.cu)
├── fortran/              Fortran implementation (cmake/make)
│   ├── src/              Modules (.f90)
│   └── tests/            Test programs
├── js/                   JavaScript module (npm)
│   ├── index.js          ESM module
│   └── package.json
├── docs/                 Documentation
├── examples/             Runnable examples
└── vms.py                Visual Music Score encoder/decoder
```

### Key Design Decisions

**INT8 saturation (Rust)** — The Rust implementation uses `i8` (-128 to 127) for flux channel intensities instead of floating-point. This gives:
- Zero allocation (stack-only, `Copy` trait)
- Deterministic cross-platform behavior
- Natural mapping to MIDI velocity (0–127)
- SIMD-friendly layout for future optimization

**EWMA drift correction** — T-0 clocks use Exponentially Weighted Moving Average instead of PID or Kalman filtering. EWMA is:
- Simple to implement (one multiply, one add)
- Predictable (no oscillation)
- Tunable via single parameter (alpha)
- O(1) memory

**Eisenstein lattice** — Rhythmic snapping uses the hexagonal lattice because:
- Covering radius 1/√3 ≈ 0.577 is optimal for 2D packing
- Natural mapping to musical ratios (3:2 = triplet, 4:3 = compound)
- Phase relationships fall out from the geometry
- The Eisenstein norm `a² + b² - ab` has musical meaning

**Side-channels as types, not data** — Nods, smiles, and frowns are lightweight value types, not message objects. They carry intent without payload. This keeps the hot path allocation-free in Rust and avoids GC pressure in Python/JS.

---

## Adding a New Language Implementation

Each language needs to implement the five layers. Here's the checklist:

### 1. Core Layer (Required)

- [ ] `FluxVector` — 9-channel tensor with salience/tolerance (or intensity/cluster)
- [ ] `TZeroClock` — EWMA-adaptive clock with drift correction
- [ ] `EisensteinSnap` / `SnapRatio` — Rhythmic quantization
- [ ] `RoomMusician` — Room with clock, flux state, and listening

### 2. MIDI Layer (Required)

- [ ] `MidiEvent` — Note on/off, CC, program change
- [ ] `MidiClock` — 24 PPQN clock with beat/measure tracking
- [ ] Channel mapping — Roles to MIDI channels

### 3. Harmony Layer (Required)

- [ ] `jaccard` — Active channel overlap
- [ ] `weighted_jaccard` — Intensity-weighted similarity
- [ ] `HarmonyState` / chord quality (optional but recommended)

### 4. Side-Channel Layer (Required)

- [ ] `Nod` — Acknowledgment signal
- [ ] `Smile` — Approval signal
- [ ] `Frown` — Disapproval signal

### 5. Ensemble Layer (Optional)

- [ ] `Band` — Multi-musician collection with conductor
- [ ] `Score` — Event recording and export

### Template

Follow the C implementation as the most portable reference:

1. Define header files matching `c/include/flux_midi/*.h`
2. Implement the functions in your language's idiom
3. Add tests matching `c/tests/test_*.c` patterns
4. Add a README.md with build instructions
5. Update the language support matrix in the root README

### Cross-Language Consistency

All implementations must agree on:

- **FluxVector has 9 channels** — no more, no less
- **T-0 clock alpha defaults to 0.1** — EWMA smoothing factor
- **Eisenstein covering radius is 1/√3** — this is mathematical, not configurable
- **Side-channels are Nod/Smile/Frown** — mapped from note-on/CC/note-off
- **Jaccard treats double-silence as similarity 1.0** — two rooms at rest agree

---

## Adding a New Side-Channel Type

Side-channels follow a strict pattern. To add a new one (e.g., `Wave` — a greeting):

### Python

1. Create `flux_tensor_midi/sidechannel/wave.py`:

```python
class Wave:
    def __init__(self, intensity: float = 0.5):
        self._intensity = intensity
        self._sent_to: set[str] = set()
        self._timestamps: list[float] = []

    def send(self, target: RoomMusician) -> None:
        self._sent_to.add(target.room_id)
        self._timestamps.append(time.monotonic())

    def has_sent_to(self, room_id: str) -> bool:
        return room_id in self._sent_to

    def rate(self, window_seconds: float = 10.0) -> float:
        now = time.monotonic()
        recent = [t for t in self._timestamps if now - t <= window_seconds]
        return len(recent) / max(window_seconds, 0.001)

    def reset(self) -> None:
        self._sent_to.clear()
        self._timestamps.clear()
```

2. Add to `RoomMusician`:
   - New property `wave: Wave`
   - Initialize in `__init__`
   - Add `send_wave(target)` method
   - Include in `receive_sidechannels()`

3. Update `receive_sidechannels()` to include `"waves": []`

### Rust

1. Create `src/sidechannel/wave.rs`:

```rust
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct Wave {
    pub note: i16,
    pub intensity: i16,
}
```

2. Add `pub mod wave;` to `src/sidechannel/mod.rs`
3. Add the mapping in `MidiEvent` (e.g., `to_wave()`)

### C

1. Add `SIDE_WAVE = 3` to `SideChannelType` enum in `sidechannel.h`
2. Add `side_wave()` factory function
3. Update `side_type_name()`

---

## Adding a New Harmony Analysis Method

Harmony analysis methods take FluxVectors and produce similarity or classification scores.

### Pattern

```python
# In harmony/your_method.py
from flux_tensor_midi.core.flux import FluxVector

def your_similarity(a: FluxVector, b: FluxVector) -> float:
    """Compute similarity between two flux vectors.
    
    Returns
    -------
    float
        Similarity in [0, 1] where 1 = identical.
    """
    # Your implementation
    ...
```

### Requirements

1. **Must handle edge cases** — Empty vectors, all-zero vectors, single-channel activity
2. **Must return [0, 1]** for similarity, [0, ∞] for distance
3. **Must be documented** with docstrings explaining the musical interpretation
4. **Must have tests** — At minimum: identical, disjoint, partial overlap, both silent
5. **Must integrate** with `HarmonyState` if it produces a scalar score

---

## Testing Strategy

### Python

```bash
cd python
python -m pytest tests/ -v
```

Tests live in `python/tests/`. Each module has a corresponding test file:
- `test_flux.py` — FluxVector operations
- More test files follow the `test_*.py` pattern

### Rust

```bash
cd rust
cargo test
```

Tests are inline (`#[cfg(test)] mod tests`) in each source file. The Rust tests cover:
- FluxChannel creation, clamping, magnitude, normalization
- FluxVector energy, distance, dot product, scale, clustering
- TZeroClock recording, EWMA, deviation, momentum, reset
- RoomMusician MIDI reception, flux expression
- SnapRatio classification, lattice distance, best_snap
- MidiEvent construction, type detection, side-channel conversion
- Jaccard (identical, disjoint, partial, silent), weighted Jaccard

### C

```bash
cd c
mkdir build && cd build
cmake .. && make
ctest
```

Tests use the Unity test framework:
- `test_flux.c` — FluxVector operations
- `test_clock.c` — TZeroClock behavior
- `test_snap.c` — Eisenstein snap
- `test_room.c` — RoomMusician

### JavaScript

Tests are run manually or via Node.js:

```bash
node --test js/index.js  # If test assertions are added
```

### Cross-Language Consistency

The key invariant: **given the same inputs, all languages must produce the same outputs**.

Specific checks:
1. **FluxVector distance** — Same result in Python, Rust, C
2. **Jaccard index** — Same value for same channel sets
3. **Eisenstein snap** — Same grid points for same timestamps
4. **T-0 clock EWMA** — Same smoothed values for same tick sequence
5. **Side-channel mapping** — Nod=note-on, Smile=CC, Frown=note-off in all languages

---

## Build Systems

### Python

```bash
# Install from source
cd python
pip install -e .

# Build distribution
pip install build
python -m build
```

Uses `pyproject.toml` with setuptools. Python 3.10+, zero dependencies.

### Rust

```bash
cd rust
cargo build --release
cargo doc --open  # Generate documentation
```

Optional feature: `--features serde` for serialization support.

### C

```bash
cd c
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

Produces `libflux_midi.a` static library. Headers in `include/flux_midi/`.

### CUDA

```bash
cd cuda
mkdir build && cd build
cmake ..
make
```

Requires CUDA toolkit. Produces kernel library.

### Fortran

```bash
cd fortran
make
# or with cmake:
mkdir build && cd build
cmake ..
make
```

Requires gfortran. Produces `libflux_midi.a`.

### JavaScript

```bash
# No build step needed — pure ESM
cd js
npm pack  # Create tarball for publishing
```

---

## Release Process

1. Update version in all `pyproject.toml`, `Cargo.toml`, `package.json`, `CMakeLists.txt`
2. Run full test suite across all languages
3. Python: `python -m build && twine upload dist/*`
4. Rust: `cargo publish`
5. JS: `npm publish`
6. Git tag: `git tag v0.x.y && git push --tags`
7. Update GitHub release notes

---

## Code Style

- **Python**: PEP 8, type hints on all public APIs, docstrings on all public classes/methods
- **Rust**: `cargo fmt`, `cargo clippy`, doc comments (`///`) on all public items
- **C**: K&R style, `/* */` block comments for documentation, `snake_case`
- **JavaScript**: ESM, no dependencies, JSDoc comments

### Naming Conventions

| Concept | Python | Rust | C | JS |
|---------|--------|------|---|----|
| Flux vector | `FluxVector` | `FluxVector` | `FluxVector` | `FluxVector` |
| Clock | `TZeroClock` | `TZeroClock` | `TZeroClock` | `TZeroClock` |
| Room | `RoomMusician` | `RoomMusician` | `RoomMusician` | `RoomMusician` |
| Snap | `EisensteinSnap` | `SnapRatio` | `SnapResult` | `eisensteinSnap()` |
| Nod | `Nod` | `Nod` | `SideSignal` (type=NOD) | `Nod` |
| Jaccard | `jaccard_index()` | `jaccard_active()` | `flux_jaccard()` | `jaccardSimilarity()` |
| Band | `Band` | `Band` | `Ensemble` | `Band` |
