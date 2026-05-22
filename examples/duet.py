#!/usr/bin/env python3
"""
duet.py — Two musicians playing together.

Demonstrates listening, coherence measurement,
and clock synchronization between rooms.
"""

from flux_tensor_midi import FluxVector, RoomMusician
from flux_tensor_midi.core.snap import RhythmicRole
from flux_tensor_midi.ensemble.band import Band

# Create two musicians with different rhythmic roles
piano = RoomMusician("piano", role=RhythmicRole.ROOT)
bass = RoomMusician("bass", role=RhythmicRole.HALFTIME)

# Set their states
piano.update_state(FluxVector([0.9, 0.7, 0.5, 0.3, 0.2, 0.8, 0.6, 0.4, 0.1]))
bass.update_state(FluxVector([0.5, 0.3, 0.9, 0.1, 0.0, 0.4, 0.7, 0.2, 0.8]))

# Bass listens to piano for timing
bass.listen_to(piano)

# Form a band with piano as conductor
band = Band("duet", conductor=piano, bpm=120.0)
band.add_musician(bass)

print("=== Duet ===")
print(f"Band: {band}")
print(f"Piano role: {piano.role.name}")
print(f"Bass role: {bass.role.name}")

# Tick through a few beats
for beat in range(4):
    print(f"\n--- Beat {beat} ---")
    events = band.tick_all()
    for name, (ts, vec) in events.items():
        print(f"  {name}: {ts:.1f}ms")

    coherence = piano.coherence_with(bass)
    print(f"  Coherence: {coherence:.3f}")

# Check what bass hears from piano
heard = bass.listen()
for name, ts, vec in heard:
    print(f"\nBass heard {name} at {ts:.1f}ms: {vec.values[:3]}...")

# Ensemble harmony
harmony = band.harmony()
print(f"\nEnsemble harmony:")
print(f"  Quality: {harmony.quality()}")
print(f"  Consonance: {harmony.consonance():.3f}")
print(f"  Mean coherence: {band.mean_coherence():.3f}")
