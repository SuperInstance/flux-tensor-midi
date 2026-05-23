"""
Constraint Repair: DNA-inspired error correction for musical constraints.

Operational transfer from DNA repair mechanisms to live music correction:

  MismatchRepair         → DNA mismatch repair (MutS/MutL/MutH pathway)
  NucleotideExcisionRepair → NER (UvrABC system)
  HomologousRecombination  → HR (RecA/Rad51-mediated strand exchange)
  SOSResponse              → Bacterial SOS response (LexA/RecA regulon)
  ConstraintRepairSystem   → Orchestrates the full repair pipeline

Each musical event is analogous to a nucleotide.  Constraints (key, scale,
voice-leading rules, rhythmic roles) act as the "complementary strand" —
the template that defines correctness.  Violations are detected and repaired
through layered mechanisms inspired by molecular biology.

Zero external dependencies.  Pure Python 3.10+.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Sequence


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class ConstraintType(Enum):
    """Categories of musical constraints that can be violated."""

    KEY = "key"                     # Note outside current key
    SCALE = "scale"                 # Note outside current scale degrees
    VOICE_LEADING = "voice_leading" # Forbidden parallel motion, etc.
    RHYTHM = "rhythm"               # Rhythmic role violation
    VELOCITY = "velocity"           # Dynamic out of bounds
    RANGE = "range"                 # Pitch out of instrument range
    DENSITY = "density"             # Too many/few events in window
    INTERVAL = "interval"           # Leap exceeds maximum allowed
    RESOLUTION = "resolution"       # Dissonance not resolved
    REGISTER = "register"           # Register imbalance


@dataclass
class Constraint:
    """A musical constraint with type, parameters, and soft/hard mode.

    Parameters
    ----------
    ctype : ConstraintType
        Category of constraint.
    params : dict
        Constraint-specific parameters (e.g., ``{"key": "C", "scale": "major"}``).
    hard : bool
        If True, violations must be repaired.  Soft violations are tolerated
        within ``epsilon``.
    epsilon : float
        Tolerance band for soft constraints (0.0 = exact, 1.0 = anything goes).
    priority : int
        Repair priority — higher values are fixed first.
    """

    ctype: ConstraintType
    params: dict = field(default_factory=dict)
    hard: bool = True
    epsilon: float = 0.0
    priority: int = 0


@dataclass
class MusicalEvent:
    """A single musical event (note / rest / control).

    Parameters
    ----------
    pitch : int | None
        MIDI pitch (0–127).  None for rests.
    velocity : int
        MIDI velocity (0–127).
    start : float
        Onset time in beats.
    duration : float
        Duration in beats.
    channel : int
        MIDI channel (0–15).
    meta : dict
        Extra metadata (finger, string, role, etc.).
    """

    pitch: int | None = None
    velocity: int = 64
    start: float = 0.0
    duration: float = 1.0
    channel: int = 0
    meta: dict = field(default_factory=dict)

    @property
    def is_rest(self) -> bool:
        return self.pitch is None


@dataclass
class Mismatch:
    """Record of a constraint violation detected in a musical event.

    Parameters
    ----------
    event_index : int
        Index of the offending event in the event list.
    constraint : Constraint
        The constraint that was violated.
    severity : float
        How badly the constraint is violated (0.0–1.0).
    suggested_fix : dict | None
        Proposed correction (e.g., ``{"pitch": 60}``).
    """

    event_index: int
    constraint: Constraint
    severity: float = 1.0
    suggested_fix: dict | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Standard scale degree sets (pitch classes relative to root)
_SCALE_DEGREES: dict[str, set[int]] = {
    "major":          {0, 2, 4, 5, 7, 9, 11},
    "natural_minor":  {0, 2, 3, 5, 7, 8, 10},
    "harmonic_minor": {0, 2, 3, 5, 7, 8, 11},
    "melodic_minor":  {0, 2, 3, 5, 7, 9, 11},
    "dorian":         {0, 2, 3, 5, 7, 9, 10},
    "phrygian":       {0, 1, 3, 5, 7, 8, 10},
    "lydian":         {0, 2, 4, 6, 7, 9, 11},
    "mixolydian":     {0, 2, 4, 5, 7, 9, 10},
    "aeolian":        {0, 2, 3, 5, 7, 8, 10},
    "locrian":        {0, 1, 3, 5, 6, 8, 10},
    "pentatonic":     {0, 2, 4, 7, 9},
    "blues":          {0, 3, 5, 6, 7, 10},
    "chromatic":      {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11},
    "whole_tone":     {0, 2, 4, 6, 8, 10},
}


def _pitch_class(pitch: int) -> int:
    """Return pitch class 0–11."""
    return pitch % 12


def _in_scale(pitch: int, root: int, scale: str) -> bool:
    """Check whether *pitch* belongs to *scale* rooted on *root*."""
    degrees = _SCALE_DEGREES.get(scale)
    if degrees is None:
        return True  # Unknown scale → allow everything
    return _pitch_class(pitch - root) in degrees


def _nearest_in_scale(pitch: int, root: int, scale: str) -> int:
    """Return the nearest scale tone to *pitch*."""
    degrees = _SCALE_DEGREES.get(scale, {0, 2, 4, 5, 7, 9, 11})
    pc = _pitch_class(pitch)
    candidates = sorted(degrees, key=lambda d: min(abs(d - pc), 12 - abs(d - pc)))
    best_degree = candidates[0]
    # Find the closest octave
    octave = pitch // 12
    candidates_by_octave = [best_degree + 12 * octave]
    if octave > 0:
        candidates_by_octave.append(best_degree + 12 * (octave - 1))
    candidates_by_octave.append(best_degree + 12 * (octave + 1))
    return min(candidates_by_octave, key=lambda p: abs(p - pitch))


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _interval(pitch_a: int | None, pitch_b: int | None) -> int | None:
    """Absolute semitone distance between two pitches."""
    if pitch_a is None or pitch_b is None:
        return None
    return abs(pitch_a - pitch_b)


def _copy_event(event: MusicalEvent, **overrides) -> MusicalEvent:
    """Shallow-copy a MusicalEvent with optional field overrides."""
    data = {
        "pitch": event.pitch,
        "velocity": event.velocity,
        "start": event.start,
        "duration": event.duration,
        "channel": event.channel,
        "meta": dict(event.meta),
    }
    data.update(overrides)
    return MusicalEvent(**data)


# ---------------------------------------------------------------------------
# MismatchRepair — DNA mismatch repair analogy
# ---------------------------------------------------------------------------

class MismatchRepair:
    """Detect and fix wrong notes — like DNA mismatch repair.

    In molecular biology, the MutS/MutL/MutH complex scans newly replicated
    DNA for mismatched bases, identifies the wrong base on the new strand,
    and replaces it using the parental strand as template.

    Here, the "parental strand" is the set of active constraints.  Each
    generated event is scanned against these constraints; mismatches are
    flagged and corrected by snapping to the nearest compliant value.
    """

    def scan(self, events: list[MusicalEvent], constraints: list[Constraint]) -> list[Mismatch]:
        """Find mismatched events (constraint violations).

        Walks every event × constraint pair and records mismatches.
        Soft constraints are only flagged when the deviation exceeds
        ``epsilon``.

        Parameters
        ----------
        events : list[MusicalEvent]
            The composition to scan.
        constraints : list[Constraint]
            Active constraints (the "template strand").

        Returns
        -------
        list[Mismatch]
            All detected violations, sorted by severity (worst first).
        """
        mismatches: list[Mismatch] = []
        for idx, event in enumerate(events):
            for constraint in constraints:
                m = self._check_event(event, idx, constraint)
                if m is not None:
                    mismatches.append(m)
        mismatches.sort(key=lambda m: m.severity, reverse=True)
        return mismatches

    def repair(
        self,
        events: list[MusicalEvent],
        mismatches: list[Mismatch],
        constraints: list[Constraint],
    ) -> list[MusicalEvent]:
        """Fix mismatches using the constraint template as guide.

        Like using the complementary strand as template, we nudge each
        offending event toward the nearest value that satisfies the
        violated constraint.

        Parameters
        ----------
        events : list[MusicalEvent]
            Original events (not mutated).
        mismatches : list[Mismatch]
            Violations to fix.
        constraints : list[Constraint]
            Active constraints for re-checking.

        Returns
        -------
        list[MusicalEvent]
            Repaired copy of the event list.
        """
        repaired = list(events)  # shallow copy
        applied: set[int] = set()

        # Process by priority (severity already sorted by scan)
        for mm in mismatches:
            idx = mm.event_index
            if idx in applied:
                continue  # Don't double-fix the same event

            event = repaired[idx]
            if mm.suggested_fix:
                fixed = _copy_event(event, **mm.suggested_fix)
                # Re-validate: make sure fix doesn't break other constraints
                ok = all(
                    self._check_event(fixed, idx, c) is None
                    for c in constraints
                    if c.hard
                )
                if ok:
                    repaired[idx] = fixed
                    applied.add(idx)
                    continue

            # Fallback: try generic snap for pitch-based violations
            if event.pitch is not None:
                fixed = self._snap_to_constraints(event, constraints)
                repaired[idx] = fixed
                applied.add(idx)

        return repaired

    def proofread(
        self,
        event: MusicalEvent,
        constraints: list[Constraint],
    ) -> list[Mismatch]:
        """Real-time checking during generation.

        Like DNA polymerase's 3'→5' exonuclease activity, this checks
        each event *as it is generated* and returns any violations
        immediately — enabling real-time correction mid-generation.

        Parameters
        ----------
        event : MusicalEvent
            The event being generated.
        constraints : list[Constraint]
            Active constraints.

        Returns
        -------
        list[Mismatch]
            Violations found (empty if event is clean).
        """
        results: list[Mismatch] = []
        for constraint in constraints:
            m = self._check_event(event, 0, constraint)
            if m is not None:
                results.append(m)
        return results

    # -- internal helpers ---------------------------------------------------

    def _check_event(
        self,
        event: MusicalEvent,
        idx: int,
        constraint: Constraint,
    ) -> Mismatch | None:
        """Check a single event against a single constraint."""
        checker = _CHECKERS.get(constraint.ctype)
        if checker is None:
            return None
        return checker(event, idx, constraint)

    def _snap_to_constraints(
        self,
        event: MusicalEvent,
        constraints: list[Constraint],
    ) -> MusicalEvent:
        """Snap an event to satisfy scale/key constraints."""
        pitch = event.pitch
        for c in constraints:
            if c.ctype == ConstraintType.KEY and pitch is not None:
                root = c.params.get("root", 0)
                scale = c.params.get("scale", "major")
                if not _in_scale(pitch, root, scale):
                    pitch = _nearest_in_scale(pitch, root, scale)
            elif c.ctype == ConstraintType.RANGE and pitch is not None:
                lo = c.params.get("min_pitch", 0)
                hi = c.params.get("max_pitch", 127)
                pitch = int(_clamp(pitch, lo, hi))
            elif c.ctype == ConstraintType.VELOCITY:
                lo = c.params.get("min_velocity", 1)
                hi = c.params.get("max_velocity", 127)
                vel = int(_clamp(event.velocity, lo, hi))
                return _copy_event(event, velocity=vel)

        if pitch != event.pitch:
            return _copy_event(event, pitch=pitch)
        return event


# ---------------------------------------------------------------------------
# Constraint checker functions
# ---------------------------------------------------------------------------

def _check_key(event: MusicalEvent, idx: int, c: Constraint) -> Mismatch | None:
    if event.is_rest:
        return None
    root: int = c.params.get("root", 0)
    scale: str = c.params.get("scale", "major")
    if _in_scale(event.pitch, root, scale):
        return None
    fixed_pitch = _nearest_in_scale(event.pitch, root, scale)
    return Mismatch(
        event_index=idx,
        constraint=c,
        severity=1.0 if c.hard else 0.5,
        suggested_fix={"pitch": fixed_pitch},
    )


def _check_scale(event: MusicalEvent, idx: int, c: Constraint) -> Mismatch | None:
    # Scale check is a subset of key check; reuse logic
    return _check_key(event, idx, c)


def _check_voice_leading(event: MusicalEvent, idx: int, c: Constraint) -> Mismatch | None:
    # This is checked in context (needs previous event); standalone is always ok
    return None


def _check_rhythm(event: MusicalEvent, idx: int, c: Constraint) -> Mismatch | None:
    allowed_durations: list[float] = c.params.get("allowed_durations", [])
    if not allowed_durations:
        return None
    if any(math.isclose(event.duration, d, abs_tol=0.01) for d in allowed_durations):
        return None
    nearest = min(allowed_durations, key=lambda d: abs(d - event.duration))
    return Mismatch(
        event_index=idx,
        constraint=c,
        severity=min(abs(event.duration - nearest) / max(event.duration, 0.01), 1.0),
        suggested_fix={"duration": nearest},
    )


def _check_velocity(event: MusicalEvent, idx: int, c: Constraint) -> Mismatch | None:
    lo: int = c.params.get("min_velocity", 1)
    hi: int = c.params.get("max_velocity", 127)
    if lo <= event.velocity <= hi:
        return None
    fixed = int(_clamp(event.velocity, lo, hi))
    return Mismatch(
        event_index=idx,
        constraint=c,
        severity=min(abs(event.velocity - fixed) / 127.0, 1.0),
        suggested_fix={"velocity": fixed},
    )


def _check_range(event: MusicalEvent, idx: int, c: Constraint) -> Mismatch | None:
    if event.is_rest:
        return None
    lo: int = c.params.get("min_pitch", 0)
    hi: int = c.params.get("max_pitch", 127)
    if lo <= event.pitch <= hi:
        return None
    fixed = int(_clamp(event.pitch, lo, hi))
    return Mismatch(
        event_index=idx,
        constraint=c,
        severity=min(abs(event.pitch - fixed) / 127.0, 1.0),
        suggested_fix={"pitch": fixed},
    )


def _check_density(event: MusicalEvent, idx: int, c: Constraint) -> Mismatch | None:
    # Density is context-dependent; standalone always ok
    return None


def _check_interval(event: MusicalEvent, idx: int, c: Constraint) -> Mismatch | None:
    # Interval is context-dependent; standalone always ok
    return None


def _check_resolution(event: MusicalEvent, idx: int, c: Constraint) -> Mismatch | None:
    # Resolution is context-dependent; standalone always ok
    return None


def _check_register(event: MusicalEvent, idx: int, c: Constraint) -> Mismatch | None:
    if event.is_rest:
        return None
    target_register: int = c.params.get("center_pitch", 60)
    max_deviation: int = c.params.get("max_deviation", 24)
    deviation = abs(event.pitch - target_register)
    if deviation <= max_deviation:
        return None
    direction = 1 if event.pitch > target_register else -1
    fixed = target_register + direction * max_deviation
    return Mismatch(
        event_index=idx,
        constraint=c,
        severity=min(deviation / 127.0, 1.0),
        suggested_fix={"pitch": fixed},
    )


_CHECKERS: dict[ConstraintType, callable] = {
    ConstraintType.KEY: _check_key,
    ConstraintType.SCALE: _check_scale,
    ConstraintType.VOICE_LEADING: _check_voice_leading,
    ConstraintType.RHYTHM: _check_rhythm,
    ConstraintType.VELOCITY: _check_velocity,
    ConstraintType.RANGE: _check_range,
    ConstraintType.DENSITY: _check_density,
    ConstraintType.INTERVAL: _check_interval,
    ConstraintType.RESOLUTION: _check_resolution,
    ConstraintType.REGISTER: _check_register,
}


# ---------------------------------------------------------------------------
# NucleotideExcisionRepair — NER analogy
# ---------------------------------------------------------------------------

class NucleotideExcisionRepair:
    """Remove damaged sections and resynthesize — like cutting out a bad phrase.

    The UvrABC system in bacteria detects bulky lesions (thymine dimers),
    cuts out a ~12-nt oligonucleotide fragment on either side, and DNA
    polymerase I fills the gap using the complementary strand.

    Musically, a "thymine dimer" is a cluster of constraint violations —
    a passage where multiple events break multiple constraints.  The whole
    passage is excised and resynthesized using the surrounding context.
    """

    def detect_damage(
        self,
        events: list[MusicalEvent],
        constraints: list[Constraint],
        window: int = 4,
    ) -> list[tuple[int, int, float]]:
        """Find sections where multiple constraints are violated.

        Slides a window across the event list and scores each window
        by the density of mismatches.  Windows exceeding a threshold
        are flagged as "damaged".

        Parameters
        ----------
        events : list[MusicalEvent]
            The full event list.
        constraints : list[Constraint]
            Active constraints.
        window : int
            Window size in events.

        Returns
        -------
        list[tuple[int, int, float]]
            List of ``(start_idx, end_idx, density)`` tuples for damaged
            regions, sorted by density (worst first).
        """
        if len(events) < window:
            return []

        scanner = MismatchRepair()
        damaged: list[tuple[int, int, float]] = []

        for i in range(len(events) - window + 1):
            segment = events[i : i + window]
            mismatches = scanner.scan(segment, constraints)
            density = len(mismatches) / window if window else 0.0
            if density >= 0.3:
                damaged.append((i, i + window, density))

        # Merge overlapping windows
        damaged = self._merge_regions(damaged)
        damaged.sort(key=lambda r: r[2], reverse=True)
        return damaged

    def excise(
        self,
        events: list[MusicalEvent],
        start: int,
        end: int,
    ) -> tuple[list[MusicalEvent], list[MusicalEvent]]:
        """Remove the damaged section.

        Parameters
        ----------
        events : list[MusicalEvent]
            Full event list.
        start : int
            Start index (inclusive).
        end : int
            End index (exclusive).

        Returns
        -------
        tuple[list[MusicalEvent], list[MusicalEvent]]
            ``(remaining_events, excised_events)``
        """
        excised = events[start:end]
        remaining = events[:start] + events[end:]
        return remaining, excised

    def resynthesize(
        self,
        gap_length: int,
        flanking_left: list[MusicalEvent],
        flanking_right: list[MusicalEvent],
        constraints: list[Constraint],
        creativity: float = 0.3,
    ) -> list[MusicalEvent]:
        """Generate new material to fill the gap, using flanking context.

        Like DNA polymerase filling in using the intact strand, we use
        the events on either side of the gap as stylistic templates.

        Parameters
        ----------
        gap_length : int
            How many events to generate.
        flanking_left : list[MusicalEvent]
            Events immediately before the gap.
        flanking_right : list[MusicalEvent]
            Events immediately after the gap.
        constraints : list[Constraint]
            Active constraints (must be satisfied).
        creativity : float
            How much random variation to inject (0 = clone flanking,
            1 = fully random).

        Returns
        -------
        list[MusicalEvent]
            Newly generated events filling the gap.
        """
        if gap_length <= 0:
            return []

        # Determine template parameters from flanking context
        avg_velocity = 64
        avg_duration = 1.0
        avg_pitch = 60
        channel = 0

        context = flanking_left[-3:] + flanking_right[:3]
        if context:
            non_rests = [e for e in context if not e.is_rest]
            if non_rests:
                avg_velocity = int(sum(e.velocity for e in non_rests) / len(non_rests))
                avg_duration = sum(e.duration for e in context) / len(context)
                avg_pitch = int(sum(e.pitch for e in non_rests) / len(non_rests))
            channel = context[0].channel

        # Extract constraint parameters
        root = 0
        scale = "major"
        min_pitch = 0
        max_pitch = 127
        min_velocity = 1
        max_velocity = 127

        for c in constraints:
            if c.ctype == ConstraintType.KEY:
                root = c.params.get("root", root)
                scale = c.params.get("scale", scale)
            elif c.ctype == ConstraintType.RANGE:
                min_pitch = c.params.get("min_pitch", min_pitch)
                max_pitch = c.params.get("max_pitch", max_pitch)
            elif c.ctype == ConstraintType.VELOCITY:
                min_velocity = c.params.get("min_velocity", min_velocity)
                max_velocity = c.params.get("max_velocity", max_velocity)

        # Determine time span from flanking
        start_time = 0.0
        if flanking_left:
            last = flanking_left[-1]
            start_time = last.start + last.duration
        elif flanking_right:
            start_time = flanking_right[0].start - avg_duration * gap_length

        # Generate events
        new_events: list[MusicalEvent] = []
        current_pitch = avg_pitch
        current_time = start_time

        for i in range(gap_length):
            # Interpolate pitch between left and right context
            if flanking_left and flanking_right:
                left_pitch = flanking_left[-1].pitch if not flanking_left[-1].is_rest else avg_pitch
                right_pitch = flanking_right[0].pitch if not flanking_right[0].is_rest else avg_pitch
                t = (i + 1) / (gap_length + 1)
                target = left_pitch + (right_pitch - left_pitch) * t
            else:
                target = avg_pitch

            # Add creativity noise
            noise = random.gauss(0, creativity * 7)
            pitch = int(_clamp(target + noise, min_pitch, max_pitch))

            # Snap to scale
            if not _in_scale(pitch, root, scale):
                pitch = _nearest_in_scale(pitch, root, scale)

            velocity = int(_clamp(
                avg_velocity + random.gauss(0, creativity * 20),
                min_velocity,
                max_velocity,
            ))
            duration = max(0.25, avg_duration + random.gauss(0, creativity * 0.2))

            event = MusicalEvent(
                pitch=pitch,
                velocity=velocity,
                start=round(current_time, 4),
                duration=round(duration, 4),
                channel=channel,
                meta={"repair": "NER"},
            )
            new_events.append(event)
            current_time += duration

        return new_events

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _merge_regions(
        regions: list[tuple[int, int, float]],
    ) -> list[tuple[int, int, float]]:
        """Merge overlapping or adjacent damaged regions."""
        if not regions:
            return []
        # Sort by start
        regions = sorted(regions, key=lambda r: r[0])
        merged = [regions[0]]
        for start, end, density in regions[1:]:
            prev_start, prev_end, prev_density = merged[-1]
            if start <= prev_end:
                # Overlap: extend and take max density
                new_density = max(prev_density, density)
                merged[-1] = (prev_start, max(prev_end, end), new_density)
            else:
                merged.append((start, end, density))
        return merged


# ---------------------------------------------------------------------------
# HomologousRecombination — HR analogy
# ---------------------------------------------------------------------------

class HomologousRecombination:
    """Fix using a reference template — like fixing a solo using the head.

    In double-strand break repair, RecA/Rad51 coats the broken DNA ends,
    searches for a homologous sequence (sister chromatid), and uses it as
    a template to restore the missing information.

    Musically, the "sister chromatid" is a reference passage (the head,
    a previous chorus, a stock phrase) that shares structure with the
    damaged section.  We find the best-matching template and graft it in.
    """

    def find_homologous(
        self,
        damaged: list[MusicalEvent],
        templates: list[list[MusicalEvent]],
        min_similarity: float = 0.4,
    ) -> list[tuple[list[MusicalEvent], float]]:
        """Find template sections most similar to the damaged passage.

        Parameters
        ----------
        damaged : list[MusicalEvent]
            The damaged events to replace.
        templates : list[list[MusicalEvent]]
            Candidate template passages.
        min_similarity : float
            Minimum similarity score (0–1) to consider a match.

        Returns
        -------
        list[tuple[list[MusicalEvent], float]]
            Matching templates with similarity scores, best first.
        """
        if not damaged or not templates:
            return []

        results: list[tuple[list[MusicalEvent], float]] = []

        for template in templates:
            sim = self._similarity(damaged, template)
            if sim >= min_similarity:
                results.append((template, sim))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def recombine(
        self,
        damaged: list[MusicalEvent],
        template: list[MusicalEvent],
        constraints: list[Constraint],
        crossover_rate: float = 0.7,
    ) -> list[MusicalEvent]:
        """Use template to repair damaged section.

        Performs a "crossover" operation: takes material from both the
        template and the damaged passage, splicing them together while
        ensuring constraints are satisfied.

        Parameters
        ----------
        damaged : list[MusicalEvent]
            Original damaged events.
        template : list[MusicalEvent]
            Homologous template to use as repair guide.
        constraints : list[Constraint]
            Active constraints.
        crossover_rate : float
            Probability of using template material vs keeping original
            at each position.

        Returns
        -------
        list[MusicalEvent]
            Recombined (repaired) events.
        """
        if not damaged:
            return []

        result: list[MusicalEvent] = []
        target_len = len(damaged)

        # Extract constraint info
        root = 0
        scale = "major"
        for c in constraints:
            if c.ctype == ConstraintType.KEY:
                root = c.params.get("root", 0)
                scale = c.params.get("scale", "major")

        for i in range(target_len):
            d_event = damaged[i]
            t_event = template[i] if i < len(template) else None

            if t_event is not None and random.random() < crossover_rate:
                # Use template material, adapted to local timing
                pitch = t_event.pitch
                if pitch is not None and not _in_scale(pitch, root, scale):
                    pitch = _nearest_in_scale(pitch, root, scale)

                new_event = _copy_event(
                    d_event,
                    pitch=pitch,
                    velocity=t_event.velocity if t_event.velocity else d_event.velocity,
                    meta={**d_event.meta, "repair": "HR", "template_idx": i},
                )
            else:
                # Keep damaged event, but ensure constraint compliance
                pitch = d_event.pitch
                if pitch is not None and not _in_scale(pitch, root, scale):
                    pitch = _nearest_in_scale(pitch, root, scale)
                new_event = _copy_event(d_event, pitch=pitch)

            result.append(new_event)

        return result

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _similarity(events_a: list[MusicalEvent], events_b: list[MusicalEvent]) -> float:
        """Compute similarity between two event sequences (0–1).

        Uses pitch-class histograms and average duration ratio.
        """
        if not events_a or not events_b:
            return 0.0

        # Pitch-class histogram similarity (cosine)
        hist_a = [0] * 12
        hist_b = [0] * 12
        for e in events_a:
            if e.pitch is not None:
                hist_a[_pitch_class(e.pitch)] += 1
        for e in events_b:
            if e.pitch is not None:
                hist_b[_pitch_class(e.pitch)] += 1

        dot = sum(a * b for a, b in zip(hist_a, hist_b))
        mag_a = math.sqrt(sum(a * a for a in hist_a))
        mag_b = math.sqrt(sum(b * b for b in hist_b))
        pc_sim = dot / (mag_a * mag_b) if mag_a > 0 and mag_b > 0 else 0.0

        # Duration similarity
        avg_dur_a = sum(e.duration for e in events_a) / len(events_a)
        avg_dur_b = sum(e.duration for e in events_b) / len(events_b)
        dur_sim = 1.0 - min(abs(avg_dur_a - avg_dur_b) / max(avg_dur_a, avg_dur_b, 0.01), 1.0)

        # Length similarity
        len_sim = min(len(events_a), len(events_b)) / max(len(events_a), len(events_b))

        return 0.4 * pc_sim + 0.3 * dur_sim + 0.3 * len_sim


# ---------------------------------------------------------------------------
# SOSResponse — Bacterial SOS response analogy
# ---------------------------------------------------------------------------

@dataclass
class SOSState:
    """Current state of the SOS emergency response system.

    Attributes
    ----------
    active : bool
        Whether SOS mode is currently engaged.
    density : float
        Last computed error density.
    relaxed_epsilon : float
        The epsilon value being used in SOS mode.
    rigidity_factor : float
        Fraction of Laman rigidity being applied (0 = fully relaxed).
    tempo_flex : float
        Tempo flexibility factor (1.0 = normal, >1.0 = more rubato).
    """

    active: bool = False
    density: float = 0.0
    relaxed_epsilon: float = 0.0
    rigidity_factor: float = 1.0
    tempo_flex: float = 1.0


class SOSResponse:
    """Emergency response when too many errors — relax constraints temporarily.

    The bacterial SOS response is triggered when DNA damage is extensive:
    RecA activates, LexA repressor is cleaved, and error-prone polymerases
    (Pol IV, Pol V) are upregulated.  The cell tolerates more mutations
    to survive.

    Musically, when a passage has too many violations to fix individually,
    we "embrace the chaos": relax constraint strictness, increase tempo
    flexibility, and allow looser structure.  Better a creative passage
    than a stilted one.
    """

    def __init__(
        self,
        density_threshold: float = 0.3,
        max_epsilon: float = 0.5,
        min_rigidity: float = 0.2,
        max_tempo_flex: float = 1.3,
    ):
        self.density_threshold = density_threshold
        self.max_epsilon = max_epsilon
        self.min_rigidity = min_rigidity
        self.max_tempo_flex = max_tempo_flex
        self._state = SOSState()

    @property
    def state(self) -> SOSState:
        return self._state

    def error_density(
        self,
        events: list[MusicalEvent],
        constraints: list[Constraint],
    ) -> float:
        """Calculate error rate — violations per event.

        Parameters
        ----------
        events : list[MusicalEvent]
            Events to evaluate.
        constraints : list[Constraint]
            Active constraints.

        Returns
        -------
        float
            Error density (0.0 = no errors, 1.0 = every event violates
            at least one hard constraint).
        """
        if not events:
            return 0.0

        scanner = MismatchRepair()
        mismatches = scanner.scan(events, [c for c in constraints if c.hard])
        # Count unique events with violations
        violated_events = {m.event_index for m in mismatches}
        return len(violated_events) / len(events)

    def activate(self, density: float, threshold: float | None = None) -> SOSState:
        """Check density and potentially enter SOS mode.

        If error density exceeds threshold, enter SOS mode:
        - Increase soft_snap ε (tolerate more deviation)
        - Reduce Laman rigidity (allow looser structure)
        - Increase tempo flexibility (more rubato)

        Basically: when everything goes wrong, embrace the chaos.

        Parameters
        ----------
        density : float
            Current error density.
        threshold : float | None
            Override threshold.  Uses instance default if None.

        Returns
        -------
        SOSState
            Updated state.
        """
        thresh = threshold if threshold is not None else self.density_threshold

        if density >= thresh:
            # Scale relaxation by how far above threshold
            overshoot = min((density - thresh) / (1.0 - thresh), 1.0)
            self._state = SOSState(
                active=True,
                density=density,
                relaxed_epsilon=self.max_epsilon * overshoot,
                rigidity_factor=max(1.0 - overshoot * (1.0 - self.min_rigidity), self.min_rigidity),
                tempo_flex=1.0 + overshoot * (self.max_tempo_flex - 1.0),
            )
        else:
            self._state = SOSState(
                active=False,
                density=density,
            )

        return self._state

    def relax_constraints(
        self,
        constraints: list[Constraint],
    ) -> list[Constraint]:
        """Apply SOS relaxation to constraints.

        Converts hard constraints to soft with increased epsilon,
        proportionally to the SOS activation level.

        Parameters
        ----------
        constraints : list[Constraint]
            Original constraints.

        Returns
        -------
        list[Constraint]
            Relaxed constraints (copies, originals not modified).
        """
        if not self._state.active:
            return list(constraints)

        relaxed: list[Constraint] = []
        for c in constraints:
            new_c = Constraint(
                ctype=c.ctype,
                params=dict(c.params),
                hard=False if self._state.rigidity_factor < 0.5 else c.hard,
                epsilon=max(c.epsilon, self._state.relaxed_epsilon),
                priority=c.priority,
            )
            relaxed.append(new_c)
        return relaxed

    def deactivate(self) -> SOSState:
        """Explicitly exit SOS mode (e.g., after a passage resolves)."""
        self._state = SOSState(active=False, density=self._state.density)
        return self._state


# ---------------------------------------------------------------------------
# ConstraintRepairSystem — full pipeline
# ---------------------------------------------------------------------------

class ConstraintRepairSystem:
    """Full DNA-inspired repair pipeline for live performance.

    Orchestrates all four repair mechanisms in a layered pipeline,
    analogous to how cells deploy multiple repair pathways:

    1. **Proofread** each event as generated (DNA pol exonuclease)
    2. **Scan** for mismatches (MutS/MutL)
    3. **Mismatch repair** — small, targeted fixes
    4. **Excision repair** — remove and resynthesize bad passages (NER)
    5. **Homologous recombination** — use reference templates (HR)
    6. **SOS response** — relax constraints if error rate is too high

    Parameters
    ----------
    constraints : list[Constraint]
        Default constraint set.
    templates : list[list[MusicalEvent]] | None
        Reference passages for homologous recombination.
    sos_threshold : float
        Error density threshold to trigger SOS response.
    excision_window : int
        Window size for damage detection.
    creativity : float
        Randomness in resynthesis (0–1).
    """

    def __init__(
        self,
        constraints: list[Constraint] | None = None,
        templates: list[list[MusicalEvent]] | None = None,
        sos_threshold: float = 0.3,
        excision_window: int = 4,
        creativity: float = 0.3,
    ):
        self.constraints = constraints or []
        self.templates = templates or []
        self.mismatch = MismatchRepair()
        self.excision = NucleotideExcisionRepair()
        self.recombination = HomologousRecombination()
        self.sos = SOSResponse(density_threshold=sos_threshold)
        self._excision_window = excision_window
        self._creativity = creativity
        self._proofread_buffer: list[Mismatch] = []

    def proofread_event(
        self,
        event: MusicalEvent,
        constraints: list[Constraint] | None = None,
    ) -> MusicalEvent:
        """Proofread a single event during generation.

        Like DNA polymerase's real-time exonuclease check.  If the event
        violates a hard constraint, apply a quick snap fix immediately.

        Parameters
        ----------
        event : MusicalEvent
            Event being generated.
        constraints : list[Constraint] | None
            Override constraints.  Uses default if None.

        Returns
        -------
        MusicalEvent
            The (possibly corrected) event.
        """
        cs = constraints or self.constraints
        issues = self.mismatch.proofread(event, cs)
        if not issues:
            return event

        # Try suggested fixes
        for issue in issues:
            if issue.suggested_fix and issue.constraint.hard:
                event = _copy_event(event, **issue.suggested_fix)

        # Verify fix
        remaining = self.mismatch.proofread(event, cs)
        self._proofread_buffer.extend(remaining)
        return event

    def repair(
        self,
        events: list[MusicalEvent],
        constraints: list[Constraint] | None = None,
        templates: list[list[MusicalEvent]] | None = None,
    ) -> list[MusicalEvent]:
        """Full repair pipeline.

        1. Proofread each event as generated
        2. Scan for mismatches
        3. Try mismatch repair (small fixes)
        4. If cluster detected, excise and resynthesize
        5. If available, use homologous recombination
        6. If error rate too high, SOS response

        Parameters
        ----------
        events : list[MusicalEvent]
            Events to repair.
        constraints : list[Constraint] | None
            Override constraints.  Uses default if None.
        templates : list[list[MusicalEvent]] | None
            Override templates.  Uses default if None.

        Returns
        -------
        list[MusicalEvent]
            Repaired events.
        """
        cs = constraints or self.constraints
        tmpl = templates if templates is not None else self.templates

        if not events:
            return events

        # Step 1: Per-event proofreading
        result = [self.proofread_event(e, cs) for e in events]

        # Step 2: Scan for remaining mismatches
        mismatches = self.mismatch.scan(result, cs)

        # Step 3: Mismatch repair
        if mismatches:
            result = self.mismatch.repair(result, mismatches, cs)

        # Step 4: Detect and repair damaged clusters
        damaged = self.excision.detect_damage(result, cs, window=self._excision_window)
        if damaged:
            result = self._excision_repair(result, cs, damaged)

        # Step 5: Homologous recombination (if templates available)
        if tmpl:
            result = self._recombination_repair(result, cs, tmpl)

        # Step 6: SOS check
        density = self.sos.error_density(result, cs)
        self.sos.activate(density)

        if self.sos.state.active:
            # Re-run repair with relaxed constraints
            relaxed = self.sos.relax_constraints(cs)
            mismatches2 = self.mismatch.scan(result, relaxed)
            if mismatches2:
                result = self.mismatch.repair(result, mismatches2, relaxed)

        return result

    def repair_report(
        self,
        events: list[MusicalEvent],
        constraints: list[Constraint] | None = None,
        templates: list[list[MusicalEvent]] | None = None,
    ) -> dict:
        """Run repair and return a diagnostic report.

        Returns
        -------
        dict
            Report with keys:
            - ``original_count``: number of input events
            - ``mismatches_found``: count of initial violations
            - ``damaged_regions``: count of excision-repaired regions
            - ``error_density_before``: error rate before repair
            - ``error_density_after``: error rate after repair
            - ``sos_activated``: whether SOS mode triggered
            - ``repaired_events``: the repaired event list
        """
        cs = constraints or self.constraints
        tmpl = templates if templates is not None else self.templates

        density_before = self.sos.error_density(events, cs)
        mismatches = self.mismatch.scan(events, cs)
        damaged = self.excision.detect_damage(events, cs, window=self._excision_window)

        repaired = self.repair(events, cs, tmpl)
        density_after = self.sos.error_density(repaired, cs)

        return {
            "original_count": len(events),
            "mismatches_found": len(mismatches),
            "damaged_regions": len(damaged),
            "error_density_before": round(density_before, 4),
            "error_density_after": round(density_after, 4),
            "sos_activated": self.sos.state.active,
            "repaired_events": repaired,
        }

    # -- internal helpers ---------------------------------------------------

    def _excision_repair(
        self,
        events: list[MusicalEvent],
        constraints: list[Constraint],
        damaged: list[tuple[int, int, float]],
    ) -> list[MusicalEvent]:
        """Apply excision repair to all damaged regions (back-to-front)."""
        result = list(events)
        # Process back-to-front to preserve indices
        for start, end, _density in sorted(damaged, key=lambda r: r[0], reverse=True):
            remaining, excised = self.excision.excise(result, start, end)
            flanking_left = remaining[:start] if start <= len(remaining) else remaining
            flanking_right = remaining[start:] if start <= len(remaining) else []

            new_events = self.excision.resynthesize(
                gap_length=len(excised),
                flanking_left=flanking_left[-4:],
                flanking_right=flanking_right[:4],
                constraints=constraints,
                creativity=self._creativity,
            )
            result = remaining[:start] + new_events + remaining[start:]
        return result

    def _recombination_repair(
        self,
        events: list[MusicalEvent],
        constraints: list[Constraint],
        templates: list[list[MusicalEvent]],
    ) -> list[MusicalEvent]:
        """Apply homologous recombination to remaining problem spots."""
        mismatches = self.mismatch.scan(events, constraints)
        if not mismatches:
            return events

        # Group mismatches into contiguous regions
        indices = sorted(set(m.event_index for m in mismatches))
        if not indices:
            return events

        regions: list[list[int]] = []
        current: list[int] = [indices[0]]
        for idx in indices[1:]:
            if idx == current[-1] + 1:
                current.append(idx)
            else:
                regions.append(current)
                current = [idx]
        regions.append(current)

        result = list(events)
        for region in regions:
            damaged_section = [result[i] for i in region]
            homologs = self.recombination.find_homologous(damaged_section, templates)
            if homologs:
                best_template, _score = homologs[0]
                repaired_section = self.recombination.recombine(
                    damaged_section, best_template, constraints,
                )
                for i, ev in zip(region, repaired_section):
                    result[i] = ev

        return result
