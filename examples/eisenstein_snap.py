#!/usr/bin/env python3
"""
eisenstein_snap.py — Snap events to the Eisenstein lattice.

Demonstrates rhythmic quantization using the hexagonal lattice.
Each musician snaps to a different grid based on their rhythmic role.
"""

from flux_tensor_midi import EisensteinSnap
from flux_tensor_midi.core.snap import RhythmicRole

snap = EisensteinSnap(base_period_ms=500.0)  # 120 BPM quarter note

print("=== Eisenstein Lattice Snap ===")
print(f"Base period: {snap.base_period_ms}ms")
print(f"Covering radius: {snap.COVERING_RADIUS:.4f}")

# Show grids for different rhythmic roles
roles = [
    RhythmicRole.ROOT,
    RhythmicRole.HALFTIME,
    RhythmicRole.TRIPLET,
    RhythmicRole.WALTZ,
    RhythmicRole.DOUBLETIME,
]

for role in roles:
    grid = snap.grid_for(role)
    print(f"\n{role.name:12s} grid: {[f'{g:.0f}' for g in grid[:8]]}...")

# Snap some raw timestamps
raw_times = [123.4, 456.7, 789.1, 1234.5, 2345.6]

print("\n--- Snapping raw timestamps ---")
for t in raw_times:
    for role in [RhythmicRole.ROOT, RhythmicRole.HALFTIME]:
        snapped = snap.snap(t, role=role)
        dist = snap.distance_to_grid(t, role=role)
        print(f"  {t:8.1f}ms → {snapped:8.1f}ms ({role.name:12s}) distance={dist:.4f}")

# Check phase alignment
print("\n--- Phase alignment ---")
pairs = [(100.0, 500.0), (250.0, 500.0), (0.0, 1000.0)]
for t1, t2 in pairs:
    for role in [RhythmicRole.ROOT, RhythmicRole.TRIPLET]:
        in_phase = snap.in_phase(t1, t2, role=role)
        print(f"  {t1}ms vs {t2}ms ({role.name:10s}): {'in phase' if in_phase else 'off phase'}")
