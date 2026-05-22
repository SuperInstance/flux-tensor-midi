# User Guide

Complete API reference for flux-tensor-midi across all languages.

---

## Table of Contents

- [Python API](#python-api)
  - [FluxVector](#fluxvector-python)
  - [TZeroClock](#tzeroclock-python)
  - [EisensteinSnap](#eisensteinsnap-python)
  - [RoomMusician](#roommusician-python)
  - [MidiEvent](#midievent-python)
  - [MidiClock](#midiclock-python)
  - [Side Channels](#side-channels-python)
  - [Harmony](#harmony-python)
  - [Ensemble](#ensemble-python)
  - [Score](#score-python)
- [Rust API](#rust-api)
  - [FluxChannel & FluxVector](#fluxchannel--fluxvector-rust)
  - [TZeroClock](#tzeroclock-rust)
  - [SnapRatio & Eisenstein Snap](#snapratio--eisenstein-snap-rust)
  - [RoomMusician](#roommusician-rust)
  - [MidiEvent](#midievent-rust)
  - [Side Channels](#side-channels-rust)
  - [Harmony / Jaccard](#harmony--jaccard-rust)
  - [Band & Score](#band--score-rust)
- [C API](#c-api)
  - [FluxVector](#fluxvector-c)
  - [TZeroClock](#tzeroclock-c)
  - [RoomMusician](#roommusician-c)
  - [MidiEvent](#midievent-c)
  - [Side Signals](#side-signals-c)
  - [Harmony](#harmony-c)
  - [Ensemble](#ensemble-c)
  - [Eisenstein Snap](#eisenstein-snap-c)
- [Concepts](#concepts)
  - [TensorMIDIEvent](#understanding-tensormidievent)
  - [Side-Channels](#understanding-side-channels)
  - [Harmony](#understanding-harmony)
  - [Clock System](#understanding-the-clock-system)
  - [Ensemble Mode](#ensemble-mode)
  - [VMS Format](#vms-format)

---

## Python API

### FluxVector (Python)

A 9-channel tensor with per-channel salience and tolerance.

```python
from flux_tensor_midi.core.flux import FluxVector

# Create from 9 values
v = FluxVector([0.8, 0.6, 0.4, 0.2, 0.1, 0.9, 0.7, 0.5, 0.3])

# With salience (importance) and tolerance (jitter)
v = FluxVector(
    [1.0, 0.8, 0.6, 0.4, 0.2, 0.9, 0.7, 0.5, 0.3],
    salience=[1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2],
    tolerance=[0.1, 0.2, 0.3, 0.1, 0.2, 0.3, 0.1, 0.2, 0.3],
)
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `values` | `tuple[float, ...]` | Length-9 tuple of channel values |
| `salience` | `tuple[float, ...]` | Per-channel importance (0–1) |
| `tolerance` | `tuple[float, ...]` | Per-channel jitter in ms |
| `magnitude` | `float` | Euclidean norm |
| `salience_weighted_magnitude` | `float` | Salience-weighted Euclidean norm |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `distance_to(other, weighted=False)` | `float` | Euclidean distance |
| `dot(other)` | `float` | Dot product |
| `cosine_similarity(other)` | `float` | Cosine similarity (-1 to 1) |
| `within_tolerance(other)` | `bool` | All channels within tolerance |
| `jitter(channel)` | `float` | Tolerance for a specific channel |

**Operators:** `+` (add), `-` (subtract), `*` (scale by scalar)

**Class methods:**

```python
v = FluxVector.zero()                    # All channels = 0
v = FluxVector.unit(channel=3)           # Unit vector along channel 3
```

### TZeroClock (Python)

Adaptive clock with EWMA drift correction.

```python
from flux_tensor_midi.core.clock import TZeroClock

clock = TZeroClock(bpm=120.0, alpha=0.125)
```

**Parameters:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `alpha` | 0.125 | EWMA smoothing factor (0–1) |
| `reference_clock` | `time.monotonic` | Wall clock source |
| `initial_ticks` | 0 | Starting tick count |
| `bpm` | 120.0 | Beats per minute |

**Methods:**

| Method | Returns | Description |
|--------|---------|-------------|
| `tick()` | `float` | Advance one tick, return corrected timestamp (ms) |
| `time_ms()` | `float` | Current corrected time without advancing |
| `drift_ms()` | `float` | Current drift estimate (negative = ahead) |
| `reset(bpm=None)` | `None` | Reset clock, optionally change BPM |
| `set_bpm(bpm)` | `None` | Change tempo mid-stream |
| `synchronize_to(other)` | `None` | Copy drift estimate from another clock |
| `align(reference_ts)` | `float` | Align to reference, return correction applied |

**Class method:**

```python
clock = TZeroClock.from_beat(beat_number=4, bpm=120.0)
```

### EisensteinSnap (Python)

Rhythmic quantization via Eisenstein lattice.

```python
from flux_tensor_midi.core.snap import EisensteinSnap, RhythmicRole

snap = EisensteinSnap(base_period_ms=500.0)  # 120 BPM quarter note
snap.set_tempo(140.0)  # Update tempo

# Snap a timestamp
snapped = snap.snap(1234.5, role=RhythmicRole.ROOT)

# Snap multiple timestamps
snapped_list = snap.snap_vector([100.0, 250.0, 400.0], role=RhythmicRole.TRIPLET)

# Get the grid for a role
grid = snap.grid_for(RhythmicRole.HALFTIME)  # Next 16 grid times

# Check grid alignment
dist = snap.distance_to_grid(1234.5, role=RhythmicRole.ROOT)
in_phase = snap.in_phase(100.0, 500.0, role=RhythmicRole.ROOT)
```

**Rhythmic Roles:**

| Role | Ratio | Musical Meaning |
|------|-------|----------------|
| `ROOT` | 1:1 | Downbeat |
| `HALFTIME` | 2:1 | Half speed |
| `TRIPLET` | 3:2 | Swung feel |
| `WALTZ` | 3:1 | Waltz time |
| `COMPOUND` | 4:3 | Compound meter |
| `DOUBLETIME` | 1:2 | Double speed |
| `OFFSET` | 1:1 + 120° phase | Offbeat |
| `QUINTUPLE` | 5:4 | Quintuple meter |
| `SEPTUPLE` | 7:4 | Septuple meter |

### RoomMusician (Python)

A PLATO room as a musician.

```python
from flux_tensor_midi import RoomMusician
from flux_tensor_midi.core.snap import RhythmicRole

# Create
musician = RoomMusician("bass", role=RhythmicRole.HALFTIME)

# Set state
musician.update_state(FluxVector([0.5, 0.3, 0.8, 0.1, 0.0, 0.4, 0.6, 0.2, 0.7]))

# Emit an event (advances clock, snaps timestamp)
timestamp, vector = musician.emit()

# Listen to another musician
other = RoomMusician("drums")
musician.listen_to(other)
events = musician.listen()  # Returns [(name, ts, vector), ...]

# Side-channels
musician.send_nod(other)
musician.send_smile(other)
musician.send_frown(other)
messages = musician.receive_sidechannels()  # {"nods": [...], "smiles": [...], "frowns": [...]}

# Ensemble
musician.join_ensemble(conductor)  # Listen + sync clock
musician.leave_ensemble()

# Coherence
similarity = musician.coherence_with(other)  # Cosine similarity of states
```

**Properties:** `name`, `room_id`, `role`, `clock`, `state`, `event_history`, `nod`, `smile`, `frown`, `listeners`

### MidiEvent (Python)

A MIDI note event.

```python
from flux_tensor_midi.midi.events import MidiEvent, NoteName

# Create directly
event = MidiEvent(note=60, velocity=100, start_ms=0.0, duration_ms=250.0, channel=0)

# From a FluxVector
events = MidiEvent.from_flux(
    vector_values=(0.8, 0.0, 0.6, 0.0, 0.0, 0.9, 0.0, 0.5, 0.0),
    start_ms=0.0,
    duration_ms=250.0,
    channel=0,
    base_note=NoteName.C4,  # 60
    velocity_scale=100,
)

# MIDI wire bytes
status, note, vel = event.note_on_bytes()   # (0x90, 60, 100)
status, note, vel = event.note_off_bytes()  # (0x80, 60, 0)
```

**Properties:** `note` (0–127), `velocity` (0–127), `start_ms`, `duration_ms`, `end_ms`, `channel` (0–15)

### MidiClock (Python)

Software MIDI clock at 24 PPQN.

```python
from flux_tensor_midi.midi.clock import MidiClock

clock = MidiClock(bpm=120.0)
clock.start()
clock.tick()  # Returns tick count
print(f"Beat: {clock.beat()}, Measure: {clock.measure()}")
print(f"Tick in beat: {clock.tick_in_beat()}")
print(f"Pulse interval: {clock.pulse_interval_ms:.2f}ms")

# Derive BPM from pulse delay
bpm = MidiClock.tempo_from_delay(pulse_delay_ms=20.833)
```

### Side Channels (Python)

Non-verbal signals between musicians.

```python
from flux_tensor_midi.sidechannel.nod import Nod
from flux_tensor_midi.sidechannel.smile import Smile
from flux_tensor_midi.sidechannel.frown import Frown

# Create and send
nod = Nod(intensity=0.8)
nod.send(target_musician)
print(f"Nod count: {nod.count}")
print(f"Rate: {nod.rate(window_seconds=10.0):.2f}/s")
print(f"Sent to room: {nod.has_sent_to(room_id)}")

# Same API for Smile and Frown
smile = Smile(intensity=0.6)
frown = Frown(intensity=0.9)
```

| Channel | Meaning | When to Use |
|---------|---------|-------------|
| **Nod** | Agreement, acknowledgment | Beat alignment, phrase boundaries |
| **Smile** | Approval, positive affect | Harmonic approval, good sync |
| **Frown** | Disagreement, concern | Dissonance, rhythmic mismatch |

### Harmony (Python)

#### Jaccard Similarity

```python
from flux_tensor_midi.harmony.jaccard import jaccard_index, weighted_jaccard, jaccard_distance

# Binary Jaccard (active/inactive channels)
idx = jaccard_index(vector_a, vector_b, threshold=0.01)

# Weighted Jaccard (considers intensity)
idx = weighted_jaccard(vector_a, vector_b)

# Distance
dist = jaccard_distance(vector_a, vector_b)
```

#### Chord Quality

```python
from flux_tensor_midi.harmony.chord import HarmonyState, ChordQuality

state = HarmonyState([vector_a, vector_b, vector_c])
print(f"Quality: {state.quality()}")         # major, minor, diminished, etc.
print(f"Consonance: {state.consonance():.3f}")  # 0–1
print(f"Correlation: {state.correlation():.3f}")  # Mean pairwise cosine

# Voice leading cost
cost = state.voice_leading_cost(target_state)
```

#### Spectral Analysis

```python
from flux_tensor_midi.harmony.spectrum import spectral_centroid, spectral_flux, dominant_channel, autocorrelation

vectors = [v1, v2, v3, v4, v5]

centroid = spectral_centroid(vectors, channel=0)
flux = spectral_flux(vectors)           # Rate of harmonic change
dom = dominant_channel(vectors)         # Most active channel
acf = autocorrelation(vectors, max_lag=4)  # Periodicity detection
```

### Ensemble (Python)

#### Band

```python
from flux_tensor_midi.ensemble.band import Band
from flux_tensor_midi import RoomMusician
from flux_tensor_midi.core.snap import RhythmicRole

conductor = RoomMusician("conductor", role=RhythmicRole.ROOT)
bass = RoomMusician("bass", role=RhythmicRole.HALFTIME)
drums = RoomMusician("drums", role=RhythmicRole.DOUBLETIME)

band = Band("quartet", conductor=conductor, bpm=120.0)
band.add_musician(bass)
band.add_musician(drums)

# Listening topology
band.everyone_listens_to_conductor()
band.everyone_listens_to_everyone()
band.set_listen(bass, drums)

# Performance
events = band.tick_all()  # {name: (timestamp, vector)}
harmony = band.harmony()  # HarmonyState
coherence = band.mean_coherence()  # Mean pairwise cosine

# Tempo changes
band.set_bpm(140.0)

# Membership
print(f"Members: {band.member_count}")
m = band.get_musician("bass")
```

### Score (Python)

Recorded performance with analysis and export.

```python
from flux_tensor_midi.ensemble.score import Score

score = Score(title="jam-session")
score.record_event("bass", timestamp=500.0, vector=bass_vector)
score.record_event("drums", timestamp=500.0, vector=drums_vector)
score.record_side_channel("bass", "nod", timestamp=500.0)

# Access
events = score.events_for("bass")
vectors = score.vectors_for("bass")
all_events = score.all_events()  # Sorted by timestamp

# Analysis
print(f"Total events: {score.total_events()}")
print(f"Duration: {score.duration_ms():.0f}ms")
flux = score.spectral_flux("bass")
harmony = score.harmony_at(timestamp=1000.0, window_ms=100.0)

# Export to MIDI events
midi_events = score.to_midi_events(velocity_scale=100)

# Summary
print(score.summary())
```

---

## Rust API

### FluxChannel & FluxVector (Rust)

INT8-saturated flux channels for zero-allocation performance.

```rust
use flux_tensor_midi::{FluxChannel, FluxVector};

// Create channels
let ch = FluxChannel::new(80);
let ch_clustered = FluxChannel::with_cluster(64, 1);

println!("Magnitude: {}", ch.magnitude());     // 80
println!("Normalized: {:.3}", ch.normalized()); // 0.812

// Create vector
let mut channels = [FluxChannel::new(0); 9];
channels[0] = FluxChannel::new(100);
channels[3] = FluxChannel::with_cluster(50, 2);
let flux = FluxVector::new(channels);
let uniform = FluxVector::uniform(64);

// Metrics
flux.energy();              // Sum of squared intensities
flux.mean();                // Mean intensity
flux.std_dev();             // Standard deviation
flux.l2_distance(&other);   // Euclidean distance
flux.chebyshev_distance(&other);  // Max channel difference
flux.dot(&other);           // Dot product
flux.scale(0.5);            // Scalar multiply (saturating)

// Clustering
let cluster_1 = flux.cluster_channels(1);  // Channels in cluster 1
```

### TZeroClock (Rust)

```rust
use flux_tensor_midi::TZeroClock;

let mut clock = TZeroClock::new(0.1);  // alpha = 0.1
let half_life_clock = TZeroClock::with_half_life(10.0);

clock.tick(1.0);
clock.tick(2.0);
println!("EWMA: {:.4}", clock.ema);
println!("Deviation: {:.4}", clock.deviation());

let prior = clock.ema;
clock.tick(3.0);
println!("Momentum: {:.4}", clock.momentum(prior));

clock.reset();
```

### SnapRatio & Eisenstein Snap (Rust)

```rust
use flux_tensor_midi::{SnapRatio, SnapClass, best_snap, within_covering_radius};

let sr = SnapRatio::new(1, 2);  // Half note
println!("Value: {:.2}", sr.value());  // 0.5
println!("Class: {}", sr.classify()); // "Half"

// Snap a BPM fraction
let snap = best_snap(0.5, 16);  // Returns Some(SnapRatio(1/2))
let on_grid = within_covering_radius(0.3);  // true (0.3 < 1/√3)
```

### RoomMusician (Rust)

```rust
use flux_tensor_midi::{RoomMusician, MidiEvent, FluxVector, TZeroClock};

let mut bass = RoomMusician::new("bass", 3);  // Channel index 3
let event = MidiEvent::note_on(60, 100);
bass.receive_midi(&event, 1.0);
println!("Active: {}", bass.active);
println!("Target: {}", bass.target);

// Express into a room flux vector
let mut room_flux = FluxVector::uniform(0);
bass.express_into(&mut room_flux);
```

### MidiEvent (Rust)

```rust
use flux_tensor_midi::MidiEvent;

let note_on = MidiEvent::note_on(60, 100);
let note_off = MidiEvent::note_off(60, 0);
let cc = MidiEvent::control_change(7, 127);

assert!(note_on.is_note_on());
assert!(note_off.is_note_off());
println!("Channel: {}", note_on.channel());
println!("Command: 0x{:02X}", note_on.command());

// Side-channel conversions
let nod = note_on.to_nod();      // Note-on → Nod
let smile = cc.to_smile();       // CC → Smile
let frown = note_off.to_frown(); // Note-off → Frown
```

### Side Channels (Rust)

```rust
use flux_tensor_midi::{Nod, Smile, Frown};

// Nod — acknowledgment
let nod = Nod::from_midi_velocity(64, 127);
println!("Confidence: {:.2}", nod.confidence());
println!("Normalized: {:.2}", nod.normalized());
println!("Enthusiastic: {}", nod.enthusiastic);  // true if > 96

// Smile and Frown follow the same pattern
```

### Harmony / Jaccard (Rust)

```rust
use flux_tensor_midi::{FluxVector, FluxChannel, jaccard_active, weighted_jaccard, harmonic_distance};

let a = FluxVector::uniform(100);
let b = FluxVector::uniform(50);
println!("Jaccard: {:.3}", jaccard_active(&a, &b));
println!("Weighted: {:.3}", weighted_jaccard(&a, &b));
println!("Distance: {:.3}", harmonic_distance(&a, &b));

// Chord quality
use flux_tensor_midi::{ChordQuality, HarmonyState};
let state = HarmonyState::new(vec![a, b]);
println!("Quality: {:?}", state.quality());
println!("Consonance: {:.3}", state.consonance());
```

### Band & Score (Rust)

```rust
use flux_tensor_midi::{Band, Score};

let mut band = Band::new("ensemble");
band.add_musician(/* ... */);
band.tick_all();
println!("Harmony: {:.3}", band.mean_coherence());

let mut score = Score::new("recording");
score.record_event(/* ... */);
println!("Events: {}", score.total_events());
```

---

## C API

Include the main header and link against `libflux_midi.a`:

```c
#include <flux_midi/flux.h>
#include <flux_midi/clock.h>
#include <flux_midi/room.h>
#include <flux_midi/midi_event.h>
#include <flux_midi/sidechannel.h>
#include <flux_midi/harmony.h>
#include <flux_midi/ensemble.h>
#include <flux_midi/snap.h>
```

### FluxVector (C)

```c
FluxVector v;
flux_zero(&v);                              // Initialize to zero
flux_uniform(&v, 0.8, 0.2);                // All channels = salience 0.8, tolerance 0.2

// Access single channel
FluxChannel ch;
flux_get(&v, 3, &ch);                      // Get channel 3
flux_set(&v, 3, 0.9, 0.1);                 // Set channel 3

// Similarity
double dist = flux_distance(&a, &b);        // Euclidean
double sim = flux_jaccard(&a, &b, 0.01);    // Jaccard
double cos = flux_cosine(&a, &b);           // Cosine

// Manipulation
flux_blend(&a, &b, 0.5, &out);             // Linear blend
flux_decay(&v, 0.95);                       // Decay all salience
flux_clamp(&v);                             // Clamp to [0, 1]
```

### TZeroClock (C)

```c
TZeroClock clk;
tzero_init(&clk, 0.5, 0.1, 1);  // interval=0.5s, alpha=0.1, adaptive=1
tzero_observe(&clk, 1.0);        // Observe tick at t=1.0

TZeroState state = tzero_check(&clk, 1.5);
// TZERO_ON_TIME, TZERO_LATE, TZERO_SILENT, TZERO_DEAD

double delta = tzero_delta(&clk, 1.5);
int missed = tzero_missed_ticks(&clk, 1.5);
double interval = tzero_effective_interval(&clk);
tzero_reset(&clk);
```

### RoomMusician (C)

```c
RoomMusician room;
room_init(&room, "bass_01", "bass", 120.0, 480, 1);
room_listen_to(&room, "drums_01");
room_update_flux(&room, &flux);
room_start(&room);
double interval = room_quarter_interval(&room);
room_free(&room);
```

### MidiEvent (C)

```c
MidiEvent ev;
midi_event_init(&ev);

MidiEvent note_on = midi_note_on(1, 60, 100, 0.0);
MidiEvent note_off = midi_note_off(1, 60, 1.0);
MidiEvent cc = midi_cc(1, 7, 127, 0.5);
MidiEvent nod = midi_sidechannel(MIDI_NOD, 1, 0.25);

const char* type = midi_event_type_name(MIDI_NOTE_ON);  // "NOTE_ON"

// Sort by timestamp
MidiEvent events[10];
qsort(events, 10, sizeof(MidiEvent), midi_event_compare);
```

### Side Signals (C)

```c
SideSignal sig = side_nod("room_1", "room_2", 1.0, 0.8);
SideSignal smile = side_smile("room_1", "", 2.0, 0.5);  // broadcast
SideSignal frown = side_frown("room_1", "room_2", 3.0, 0.9);

int is_broadcast = side_is_broadcast(&sig);  // 0
const char* name = side_type_name(SIDE_NOD); // "NOD"
```

### Harmony (C)

```c
HarmonyScore score = harmony_compute(&flux_a, &flux_b, 0.4, 0.4, 0.2);
printf("Jaccard: %.3f\n", score.jaccard);
printf("Cosine: %.3f\n", score.cosine);
printf("Euclidean: %.3f\n", score.euclidean);
printf("Combined: %.3f\n", score.combined);

int in_tune = harmony_in_tune(&a, &b, 0.7);  // threshold check

double alignment = connectome_alignment(listen_a, n_a, listen_b, n_b);
double harmonic = spectrum_harmonic_ratio(intervals, n_intervals);
```

### Ensemble (C)

```c
Ensemble ens;
ensemble_init(&ens, 120.0, 480);

RoomMusician room1, room2;
room_init(&room1, "bass", "bass", 120.0, 480, 1);
room_init(&room2, "drums", "drums", 120.0, 480, 10);
ensemble_add_room(&ens, &room1);
ensemble_add_room(&ens, &room2);

ensemble_tick(&ens, 1.0);

int on_time, late, silent, dead;
ensemble_tzero_stats(&ens, 1.0, &on_time, &late, &silent, &dead);

HarmonyScore* matrix = ensemble_harmony_matrix(&ens);
double avg = ensemble_average_harmony(&ens);

ensemble_free(&ens);
```

### Eisenstein Snap (C)

```c
SnapResult result;
eisenstein_snap(0.5, 0.25, 0.5, &result);
printf("Shape: %s\n", snap_shape_name(result.shape));
printf("Norm: %.3f\n", result.norm);

double snapped = snap_to_grid(0.37, 0.25, NULL);
```

---

## Concepts

### Understanding TensorMIDIEvent

Every musical event in flux-tensor-midi lives in a 4-dimensional space:

| Dimension | What | Example |
|-----------|------|---------|
| **Time** | When it happens | T-0 clock tick at 500.3ms |
| **Intent** | What it wants to say | FluxVector [0.8, 0.3, 0.0, ...] |
| **Harmony** | How it relates | Jaccard similarity 0.75 with bass |
| **SideChannel** | Body language | Nod to drums, smile at piano |

The 4-byte encoding packs this into a compact representation suitable for real-time processing, network transmission, and GPU kernels.

### Understanding Side-Channels

Side-channels are the non-verbal communication layer of the ensemble. They don't carry MIDI data — they carry intent.

**Nod (note-on)** — "I hear you." Agreement, acknowledgment. Bass nods at the start of each phrase to confirm it's locked with the drums.

**Smile (CC)** — "I like that." Positive affect, harmonic approval. Piano smiles when the guitar plays a chord it likes.

**Frown (note-off)** — "Something's off." Disagreement, dissonance. Drums frown when the tempo drifts beyond tolerance.

### Understanding Harmony

flux-tensor-midi provides three levels of harmonic analysis:

1. **Jaccard similarity** — Binary overlap of active channels. Fast, cheap. "Are these two rooms playing similar things?"

2. **Weighted Jaccard** — Considers intensity, not just active/inactive. "How similarly are they playing?"

3. **Chord quality** — Classifies the ensemble state as major, minor, diminished, augmented, suspended, seventh, or ninth. Uses interval consonance mapping (unison=1.0, tritone=0.5, perfect fifth=0.95).

### Understanding the Clock System

Each room has a T-0 clock that:

1. Maintains a **tick counter** and **BPM**
2. Computes **drift** using EWMA: `drift = α × observed_drift + (1-α) × prior_drift`
3. Returns **corrected timestamps**: `expected_ms - drift`
4. Supports **synchronization** between clocks (ensemble mode)

The `alpha` parameter controls adaptation speed:
- `0.05` — Very smooth, slow to adapt (good for steady tempo)
- `0.125` — Default, moderate response
- `0.5` — Fast adaptation (good for tempo changes)

Eisenstein snapping provides an additional rhythmic quantization layer on top of the clock, mapping timestamps to a hexagonal lattice grid based on each musician's rhythmic role.

### Ensemble Mode

Ensemble mode coordinates multiple room musicians:

1. **Band** — A collection of musicians with a conductor. The conductor provides the master clock. All members auto-sync to it.

2. **Listening matrix** — Who listens to whom. Supports:
   - Everyone listens to conductor
   - Everyone listens to everyone
   - Custom listening connections

3. **Score** — Records all events for playback and analysis. Supports export to standard MIDI.

4. **Harmony analysis** — Real-time chord quality and consonance computation across the ensemble.

### VMS Format

The Visual Music Score (`.vms`) format encodes video mockups as MIDI scores with FLUX metadata:

- JSON-based, human-readable
- Tempo, lattice divisions, and scene events
- Scene types map to MIDI pitches (closeup=C4, wide=C3, CTA=C7)
- Eisenstein lattice snapping for timing quantization
- Export to standard MIDI file format
- Frame-by-frame timeline rendering at configurable FPS

```python
from vms import VideoScore, SceneEvent, save_vms, load_vms

score = VideoScore(name="demo", tempo_bpm=72.0)
score.add_scene(SceneEvent(beat=0, scene_type=60, duration_beats=4, velocity=100))
save_vms(score, "output.vms")
loaded = load_vms("output.vms")
```
