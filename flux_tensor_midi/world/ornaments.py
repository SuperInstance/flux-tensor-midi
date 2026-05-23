"""World music ornaments — meend, gamak, quarter bends, grace notes, murki, shakes."""

from __future__ import annotations

import math
from typing import Literal


def meend(
    start: float,
    end: float,
    steps: int = 20,
    curve: Literal["linear", "exponential", "logarithmic"] = "exponential",
) -> list[float]:
    """Indian glide (*meend*) from *start* to *end* pitch (semitones).

    *curve* controls the interpolation shape:
      - ``"exponential"`` — slow start, fast finish (default for meend)
      - ``"logarithmic"`` — fast start, slow finish
      - ``"linear"`` — even spacing
    """
    if steps < 1:
        return [start]
    result: list[float] = []
    for i in range(steps + 1):
        t = i / steps
        if curve == "exponential":
            value = start + (end - start) * (t ** 2)
        elif curve == "logarithmic":
            value = start + (end - start) * (1 - (1 - t) ** 2)
        else:  # linear
            value = start + (end - start) * t
        result.append(round(value, 4))
    return result


def gamak(
    center: float,
    amplitude: float = 0.5,
    speed: float = 6.0,
    cycles: int = 3,
) -> list[float]:
    """Indian oscillation (*gamak*) around *center* pitch (semitones).

    Returns a list of pitch values simulating rapid oscillation.
    *amplitude* is in semitones, *speed* is oscillations per cycle,
    *cycles* is the number of full back-and-forth swings.
    """
    total_points = int(speed * cycles * 4)  # 4 samples per oscillation
    result: list[float] = []
    for i in range(total_points + 1):
        t = i / max(total_points, 1)
        # Decaying amplitude
        decay = 1.0 - (t * 0.3)  # gentle decay
        val = center + amplitude * decay * math.sin(2 * math.pi * speed * cycles * t)
        result.append(round(val, 4))
    return result


def quarter_bend(
    note: float,
    direction: Literal["up", "down"] = "up",
    cents: float = 50.0,
) -> list[float]:
    """Arabic quarter-tone bend.

    Returns a brief pitch trajectory from *note* by *cents* in the given
    *direction*.
    """
    semitones = cents / 100.0
    target = note + semitones if direction == "up" else note - semitones
    # Smooth bend: attack, hold, release
    trajectory: list[float] = []
    steps = 10
    for i in range(steps + 1):
        t = i / steps
        # Smoothstep
        val = t * t * (3 - 2 * t)
        trajectory.append(round(note + (target - note) * val, 4))
    # Brief hold then release
    for _ in range(4):
        trajectory.append(round(target, 4))
    for i in range(steps + 1):
        t = i / steps
        val = t * t * (3 - 2 * t)
        trajectory.append(round(target + (note - target) * val, 4))
    return trajectory


def grace_note(
    target: float,
    approach: Literal["adjacent", "diatonic_above", "diatonic_below"] = "adjacent",
    duration_ms: int = 30,
) -> list[dict]:
    """Universal grace note approaching *target*.

    Returns a list of event dicts ``{"pitch": float, "duration_ms": int}``.
    """
    if approach == "adjacent":
        source = target - 1
    elif approach == "diatonic_above":
        source = target + 2
    else:
        source = target - 2
    return [
        {"pitch": round(source, 2), "duration_ms": duration_ms},
        {"pitch": round(target, 2), "duration_ms": 0},
    ]


def murki(
    notes: list[float],
    speed_ms: int = 80,
) -> list[dict]:
    """Indian turn (*murki*) — rapid alternation between *notes*.

    Returns event dicts ``{"pitch": float, "duration_ms": int}``.
    """
    if len(notes) < 2:
        return [{"pitch": n, "duration_ms": speed_ms} for n in notes]
    result: list[dict] = []
    # Forward and back, twice
    for _ in range(2):
        for n in notes:
            result.append({"pitch": round(n, 2), "duration_ms": speed_ms})
        for n in reversed(notes[1:-1]):
            result.append({"pitch": round(n, 2), "duration_ms": speed_ms})
    return result


def shakes(
    note: float,
    speed: float = 8.0,
    amplitude: float = 0.3,
) -> list[float]:
    """Jazz shake — rapid lip/valve trill around *note*.

    Returns pitch values.
    """
    points = int(speed * 8)  # ~8 samples per oscillation
    result: list[float] = []
    for i in range(points):
        t = i / max(points - 1, 1)
        val = note + amplitude * math.sin(2 * math.pi * speed * t)
        result.append(round(val, 4))
    return result
