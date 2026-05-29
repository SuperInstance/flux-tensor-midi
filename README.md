# flux-tensor-midi

4D tensor MIDI representation where PLATO rooms become musicians — T-0 clocks, Eisenstein rhythm snapping, gene regulatory networks, neural music cortex, and constraint repair.

## What This Gives You

- **Room musicians** — each PLATO room has a clock, produces notes, and listens to neighbors
- **T-0 clock** — distributed tempo with Eisenstein lattice rhythm snapping
- **Gene regulatory networks** — 25-gene musical genome with activation, repression, and horizontal transfer
- **Neural music cortex** — brain-inspired architecture with dopamine, hippocampus memory, and multiple cortex types
- **Constraint repair** — automatic fixing of constraint violations in generated MIDI
- **Genre brain** — style-aware composition with genre classification
- **Zero dependencies** — pure Python 3.10+

## Quick Start

```python
from flux_tensor_midi import RoomMusician, Arrangement, Track, MidiFileWriter

# Create room musicians
rooms = [
    RoomMusician(name="bass", role="rhythm"),
    RoomMusician(name="harmony", role="harmony"),
    RoomMusician(name="melody", role="lead"),
]

# Arrange and perform
arrangement = Arrangement(rooms=rooms, bpm=120, key="C", bars=8)
arrangement.perform()

# Export to MIDI
writer = MidiFileWriter(arrangement)
writer.save("output.mid")
```

### Gene Regulatory Networks

```python
from flux_tensor_midi import GeneRegulatoryNetwork, MusicalGene

# Build a musical genome
grn = GeneRegulatoryNetwork()
grn.add_gene(MusicalGene("harmonic_tension", threshold=0.5, output_rate=1.0))
grn.add_gene(MusicalGene("rhythmic_density", threshold=0.3, output_rate=0.8))

# Run regulatory dynamics
grn.express(timesteps=100)
notes = grn.to_notes()
```

### Neural Performance

```python
from flux_tensor_midi import MusicalBrain, neural_performance

brain = MusicalBrain(cortex_types=["motor", "auditory", "prefrontal"])
performance = neural_performance(brain, duration=60.0, bpm=120)
```

## API Reference

| Module | Key Types | Description |
|---|---|---|
| `core` | `RoomMusician`, `TZeroClock`, `FluxVector`, `EisensteinSnap` | Core room/clock architecture |
| `gene_regulatory` | `GeneRegulatoryNetwork`, `MusicalGene` | GRN-based composition |
| `neural_music` | `MusicalBrain`, `MusicalCortex`, `DopamineSystem` | Brain-inspired music |
| `genre_brain` | `GenreBrain` | Style-aware generation |
| `constraint_repair` | `ConstraintRepairSystem` | Auto-fix constraint violations |
| `tracks` | `Arrangement`, `Track` | Multi-track arrangement |
| `midi_writer` | `MidiFileWriter` | MIDI export |

## How It Fits

The **composition engine** of the FLUX music ecosystem:

- [constraint-theory-core](https://github.com/SuperInstance/constraint-theory-core) — constraint primitives used for verification
- [flux-genome](https://github.com/SuperInstance/flux-genome) — 25-gene genome that feeds the GRN
- [flux-algebra](https://github.com/SuperInstance/flux-algebra) — algebraic operations on pitch classes
- [constraint-instrument](https://github.com/SuperInstance/constraint-instrument) — performance rendering

## Testing

```bash
pip install -e ".[dev]"
pytest -v  # 28 test files
```

## Installation

```bash
pip install flux-tensor-midi
```

Requires Python ≥ 3.10.

## License

MIT
