#!/usr/bin/env python3
"""
side_channels.py — Nods, smiles, and frowns between musicians.

Demonstrates the non-verbal communication layer.
"""

from flux_tensor_midi import FluxVector, RoomMusician
from flux_tensor_midi.core.snap import RhythmicRole

# Create a small ensemble
piano = RoomMusician("piano", role=RhythmicRole.ROOT)
drums = RoomMusician("drums", role=RhythmicRole.DOUBLETIME)
bass = RoomMusician("bass", role=RhythmicRole.HALFTIME)

# Everyone listens to each other
piano.listen_to(drums)
piano.listen_to(bass)
drums.listen_to(piano)
bass.listen_to(piano)

print("=== Side Channels ===")

# Piano nods at drums (acknowledgment)
piano.send_nod(drums)
print(f"Piano → drums: nod (count={piano.nod.count})")

# Bass smiles at piano (approval)
bass.send_smile(piano)
print(f"Bass → piano: smile (count={bass.smile.count})")

# Piano frowns at bass (something's off)
piano.send_frown(bass)
print(f"Piano → bass: frown (count={piano.frown.count})")

# Drums receives side-channel messages
drums_msgs = drums.receive_sidechannels()
print(f"\nDrums received:")
print(f"  Nods: {drums_msgs['nods']}")
print(f"  Smiles: {drums_msgs['smiles']}")
print(f"  Frowns: {drums_msgs['frowns']}")

# Piano receives
piano_msgs = piano.receive_sidechannels()
print(f"\nPiano received:")
print(f"  Nods: {piano_msgs['nods']}")
print(f"  Smiles: {piano_msgs['smiles']}")
print(f"  Frowns: {piano_msgs['frowns']}")

# Check rates
print(f"\nPiano nod rate: {piano.nod.rate(10.0):.2f}/s")
print(f"Bass smile rate: {bass.smile.rate(10.0):.2f}/s")
print(f"Piano frown rate: {piano.frown.rate(10.0):.2f}/s")

# Reset
bass.smile.reset()
print(f"\nBass smile count after reset: {bass.smile.count}")
