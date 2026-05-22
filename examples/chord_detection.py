#!/usr/bin/env python3
"""
chord_detection.py — Harmony analysis across multiple musicians.

Demonstrates Jaccard similarity, chord quality classification,
and spectral analysis.
"""

from flux_tensor_midi import FluxVector, RoomMusician
from flux_tensor_midi.core.snap import RhythmicRole
from flux_tensor_midi.harmony.jaccard import jaccard_index, weighted_jaccard, jaccard_distance
from flux_tensor_midi.harmony.chord import HarmonyState, ChordQuality
from flux_tensor_midi.harmony.spectrum import spectral_centroid, spectral_flux, dominant_channel, autocorrelation

print("=== Chord Detection ===\n")

# --- Jaccard Similarity ---
print("--- Jaccard Similarity ---")
v1 = FluxVector([1.0, 0.0, 0.8, 0.0, 0.0, 0.0, 0.7, 0.0, 0.0])
v2 = FluxVector([0.9, 0.0, 0.7, 0.0, 0.0, 0.0, 0.8, 0.0, 0.0])
v3 = FluxVector([0.0, 1.0, 0.0, 0.9, 0.8, 0.0, 0.0, 0.7, 0.0])

print(f"v1 vs v2 (similar): jaccard={jaccard_index(v1, v2):.3f}, weighted={weighted_jaccard(v1, v2):.3f}")
print(f"v1 vs v3 (different): jaccard={jaccard_index(v1, v3):.3f}, weighted={weighted_jaccard(v1, v3):.3f}")
print(f"v1 vs v3 distance: {jaccard_distance(v1, v3):.3f}")

# --- Chord Quality ---
print("\n--- Chord Quality ---")

# Major-ish chord: channels 0, 4, 7 active (like C-E-G spacing)
major_v1 = FluxVector([1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 0.0])
major_v2 = FluxVector([0.8, 0.0, 0.0, 0.0, 0.9, 0.0, 0.0, 0.7, 0.0])
state = HarmonyState([major_v1, major_v2])
print(f"Major chord: quality={state.quality()}, consonance={state.consonance():.3f}")

# Minor-ish: channels 0, 3, 7
minor_v1 = FluxVector([1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0])
state_minor = HarmonyState([minor_v1])
print(f"Minor chord: quality={state_minor.quality()}")

# Dissonant: channels 0, 6 (tritone spacing)
dissonant = FluxVector([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0])
state_dissonant = HarmonyState([dissonant])
print(f"Dissonant: quality={state_dissonant.quality()}, consonance={state_dissonant.consonance():.3f}")

# Voice leading cost
cost = state.voice_leading_cost(state_minor)
print(f"Voice leading cost (major → minor): {cost:.3f}")

# --- Spectral Analysis ---
print("\n--- Spectral Analysis ---")

# A sequence of vectors over time
sequence = [
    FluxVector([0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    FluxVector([0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    FluxVector([0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    FluxVector([0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
    FluxVector([0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
]

centroid = spectral_centroid(sequence, channel=0)
flux = spectral_flux(sequence)
dom = dominant_channel(sequence)
acf = autocorrelation(sequence, max_lag=3)

print(f"Spectral centroid (ch 0): {centroid:.3f}")
print(f"Spectral flux: {flux:.3f}")
print(f"Dominant channel: {dom}")
print(f"Autocorrelation: {[f'{v:.3f}' for v in acf]}")
