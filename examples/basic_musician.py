#!/usr/bin/env python3
"""
basic_musician.py — Create a single room musician.

Demonstrates creating a RoomMusician, setting its state,
emitting events, and reading the clock.
"""

from flux_tensor_midi import FluxVector, TZeroClock, RoomMusician
from flux_tensor_midi.core.snap import RhythmicRole

# Create a musician with ROOT role (downbeat)
musician = RoomMusician("alice", role=RhythmicRole.ROOT)

# Set the 9-channel state vector
# Channels: Arousal, Valence, Dominance, Uncertainty, Novelty,
#           Relevance, Competence, Affiliation, Urgency
musician.update_state(FluxVector([0.8, 0.6, 0.4, 0.2, 0.1, 0.9, 0.7, 0.5, 0.3]))

print(f"Musician: {musician}")
print(f"State: {musician.state.values}")

# Emit 4 events (advances clock each time)
for i in range(4):
    ts, vec = musician.emit()
    print(f"  Event {i}: timestamp={ts:.1f}ms, vector={vec.values[:3]}...")

print(f"\nClock: ticks={musician.clock.ticks}, drift={musician.clock.drift_ms():.4f}ms")
print(f"History: {len(musician.event_history)} events")
