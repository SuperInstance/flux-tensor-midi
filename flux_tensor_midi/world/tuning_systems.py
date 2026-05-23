"""Tuning systems — equal temperament, just intonation, shruti, quarter-tone, meantone, pythagorean."""

from __future__ import annotations

import math
from typing import Sequence


# ---------------------------------------------------------------------------
# Tuning generators  (return cents from root, always starting at 0)
# ---------------------------------------------------------------------------

def equal_temperament(notes: int = 12) -> list[float]:
    """N-tone equal temperament.  Returns *notes* pitch-classes in cents."""
    return [i * (1200.0 / notes) for i in range(notes)]


def just_intonation() -> list[float]:
    """5-limit just intonation ratios (within one octave) in cents."""
    ratios = [1, 16/15, 9/8, 6/5, 5/4, 4/3, 45/32, 3/2, 8/5, 5/3, 9/5, 15/8]
    return [_ratio_to_cents(r) for r in ratios]


def shruti_22() -> list[float]:
    """Indian 22-shruti positions in cents (ascending within one octave)."""
    # Ratios from standard shruti theory
    ratios = [
        1,        # Shadja (Sa)
        256/243,  # Komal Rati
        16/15,    # Komal Re
        10/9,     # Shuddha Re
        9/8,      # Shuddha Re (high)
        32/27,    # Komal Ga
        6/5,      # Komal Ga (high)
        5/4,      # Shuddha Ga
        81/64,    # Shuddha Ga (high)
        4/3,      # Shuddha Ma
        27/20,    # Tivra Ma
        45/32,    # Tivra Ma (high)
        729/512,  # Tivra Ma (max)
        3/2,      # Pancham (Pa)
        128/81,   # Komal Dha
        8/5,      # Komal Dha (high)
        5/3,      # Shuddha Dha
        27/16,    # Shuddha Dha (high)
        16/9,     # Komal Ni
        9/5,      # Komal Ni (high)
        15/8,     # Shuddha Ni
        243/128,  # Shuddha Ni (high)
    ]
    return [_ratio_to_cents(r) for r in ratios]


def quarter_tone_24() -> list[float]:
    """24-tone equal division (quarter-tone scale) in cents."""
    return [i * 50.0 for i in range(24)]


def pentatonic_5() -> list[float]:
    """5-tone equal temperament (approximate slendro) in cents."""
    return [i * 240.0 for i in range(5)]


def meantone() -> list[float]:
    """Quarter-comma meantone tuning (12 notes) in cents."""
    # Generator = 3/2 flattened by 1/4 syntonic comma
    # Fifth = 1200 * log2(5**0.25) ≈ 696.578 cents
    fifth_cents = 1200.0 * math.log2(5 ** 0.25)
    notes: list[float] = [0.0]
    acc = 0.0
    for _ in range(11):
        acc += fifth_cents
        acc %= 1200.0
        notes.append(acc)
    notes.sort()
    return notes


def pythagorean() -> list[float]:
    """Pythagorean tuning (12 notes, 3/2 fifths) in cents."""
    fifth_cents = 1200.0 * math.log2(3 / 2)  # ~701.955
    notes: list[float] = [0.0]
    acc = 0.0
    for _ in range(11):
        acc += fifth_cents
        acc %= 1200.0
        notes.append(acc)
    notes.sort()
    return notes


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def snap_to_tuning(
    note_cents: float,
    tuning: Sequence[float],
    epsilon: float = 0.0,
) -> float:
    """Snap *note_cents* to the nearest pitch in *tuning*.

    If *epsilon* > 0 and the nearest tuning pitch is farther than *epsilon*
    cents away, return *note_cents* unchanged (no snap).
    """
    best = min(tuning, key=lambda t: abs(t - note_cents))
    # Wrap into octave
    best_wrapped = best % 1200.0
    note_wrapped = note_cents % 1200.0
    # Handle wrap-around (e.g. 1190 vs 10)
    diff = abs(best_wrapped - note_wrapped)
    diff = min(diff, 1200.0 - diff)
    if epsilon > 0 and diff > epsilon:
        return note_cents
    return best_wrapped


def _ratio_to_cents(ratio: float) -> float:
    """Convert a frequency ratio to cents."""
    return 1200.0 * math.log2(ratio)
