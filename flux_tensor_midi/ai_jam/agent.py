"""
AIAgent: An AI musician with personality-driven constraint profiles.

Each agent has:
  - A personality dict controlling interval choices, rhythmic density,
    snap behaviour, and dynamics.
  - A short-term memory of the other agent's recent output.
  - A respond() method that generates the next phrase given context.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Sequence

from flux_tensor_midi.midi.events import MidiEvent


# ---------------------------------------------------------------------------
# Pitch / scale helpers
# ---------------------------------------------------------------------------

# D Dorian = D E F G A B C  (semitone offsets from root)
DORIAN_INTERVALS = [0, 2, 3, 5, 7, 9, 10]
# General major-scale intervals for other roots
MAJOR_INTERVALS = [0, 2, 4, 5, 7, 9, 11]
# Minor pentatonic
MINOR_PENTATONIC = [0, 3, 5, 7, 10]


def _scale_notes(root: int, intervals: Sequence[int], octave_range: tuple[int, int] = (3, 6)) -> list[int]:
    """Build a list of MIDI note numbers for a scale across octaves."""
    notes: list[int] = []
    for octave in range(octave_range[0], octave_range[1] + 1):
        base = root + octave * 12
        for iv in intervals:
            notes.append(base + iv)
    # deduplicate & sort
    return sorted(set(n for n in notes if 0 <= n <= 127))


# Pre-compute D Dorian scale (D=62) across useful range
D_DORIAN_NOTES = _scale_notes(62, DORIAN_INTERVALS, (3, 6))


# Chord tones for the jam progression (D Dorian context)
# Dm7: D F A C, Gm7: G Bb D F, Am7: A C E G
# Using octave-aware MIDI notes
CHORD_TONES: dict[str, list[int]] = {
    "Dm7": sorted(set(n for n in range(0, 128) if n % 12 in (2, 5, 9, 0))),  # D F A C
    "Gm7": sorted(set(n for n in range(0, 128) if n % 12 in (7, 10, 2, 5))),  # G Bb D F
    "Am7": sorted(set(n for n in range(0, 128) if n % 12 in (9, 0, 4, 7))),  # A C E G
    "Em7": sorted(set(n for n in range(0, 128) if n % 12 in (4, 7, 11, 2))),  # E G B D
    "Fmaj7": sorted(set(n for n in range(0, 128) if n % 12 in (5, 9, 0, 4))),  # F A C E
    "Bbmaj7": sorted(set(n for n in range(0, 128) if n % 12 in (10, 2, 5, 9))),  # Bb D F A
    "Cmaj7": sorted(set(n for n in range(0, 128) if n % 12 in (0, 4, 7, 11))),  # C E G B
}


# ---------------------------------------------------------------------------
# Agent personality
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentPersonality:
    """Immutable personality profile that drives constraint weights."""

    name: str
    instrument: str  # e.g. "sax", "trumpet"
    midi_channel: int = 0
    midi_program: int = 0  # GM program number

    # Interval preferences (semitone offsets likely to appear)
    preferred_intervals: tuple[int, ...] = (0, 2, 3, 5, 7)
    # Rhythmic density: notes per beat on average (1.0 = quarter notes)
    note_density: float = 2.0
    # Velocity range (min, max)
    velocity_range: tuple[int, int] = (60, 120)
    # Probability of rest at any given subdivision
    rest_probability: float = 0.1
    # Snap epsilon: how strongly the agent snaps to grid (1.0 = perfect)
    snap_epsilon: float = 0.8
    # Direction change probability (angularity)
    direction_change_prob: float = 0.4
    # Sustain preference: 0=staccato, 1=legato
    sustain_factor: float = 0.5
    # Octave range preference (min, max MIDI octave)
    octave_range: tuple[int, int] = (4, 5)
    # Consensus weight: how strongly this agent follows consensus (0-1)
    consensus_weight: float = 0.7


# ---------------------------------------------------------------------------
# AI Agent
# ---------------------------------------------------------------------------

class AIAgent:
    """An AI musician that generates phrases from constraints."""

    def __init__(
        self,
        personality: AgentPersonality,
        rng: random.Random | None = None,
    ):
        self.personality = personality
        self.rng = rng or random.Random()
        # Short-term memory: last N bars of MidiEvent from the other agent
        self.memory: list[MidiEvent] = []

    # ---- public API ----

    def respond(
        self,
        other_output: list[MidiEvent],
        harmony_context: dict,
        bars: int = 4,
        bpm: float = 140.0,
    ) -> list[MidiEvent]:
        """Generate a phrase responding to the other agent.

        Parameters
        ----------
        other_output : list[MidiEvent]
            The other agent's last phrase.
        harmony_context : dict
            Must contain 'chord_progression': list of (chord_name, bars) tuples.
        bars : int
            How many bars to generate.
        bpm : float
            Tempo.

        Returns
        -------
        list[MidiEvent]
        """
        # Update memory
        self.memory = other_output[-64:]  # keep last 64 events

        p = self.personality
        bar_ms = (60_000.0 / bpm) * 4  # 4/4 time
        subdivision_ms = bar_ms / (p.note_density * 4)
        # Clamp subdivision to at least 16th note
        subdivision_ms = max(subdivision_ms, bar_ms / 16)

        events: list[MidiEvent] = []
        current_pitch = self._pick_starting_pitch(harmony_context)

        chord_progression = harmony_context.get("chord_progression", [("Dm7", 4)])
        total_time = 0.0
        chord_idx = 0
        chord_elapsed = 0.0

        for bar in range(bars):
            # Determine current chord
            accumulated = 0.0
            active_chord = chord_progression[0][0]
            for chord_name, chord_bars in chord_progression:
                chord_dur = chord_bars * bar_ms
                if accumulated <= bar * bar_ms + 1e-6:
                    active_chord = chord_name
                accumulated += chord_dur
                if accumulated > (bar + 1) * bar_ms:
                    break

            bar_start = bar * bar_ms
            step = 0
            direction = self.rng.choice([-1, 1])
            is_bar_boundary = (bar == 0)

            pos = bar_start
            while pos < bar_start + bar_ms - 1e-6:
                # Check if this is near a bar boundary (first beat of a bar)
                near_bar_start = abs(pos - bar_start) < subdivision_ms / 2

                # Consensus: chord tones at bar boundaries
                if near_bar_start and step == 0:
                    pitch = self._consensus_pitch(active_chord, current_pitch)
                else:
                    pitch = self._next_pitch(
                        current_pitch, direction, active_chord
                    )

                # Direction change
                if self.rng.random() < p.direction_change_prob:
                    direction *= -1

                # Rest?
                if self.rng.random() < p.rest_probability:
                    pos += subdivision_ms
                    step += 1
                    continue

                velocity = self.rng.randint(p.velocity_range[0], p.velocity_range[1])
                # Duration: sustain_factor * subdivision with some randomness
                dur = subdivision_ms * (p.sustain_factor + self.rng.uniform(-0.2, 0.3))
                dur = max(subdivision_ms * 0.25, dur)

                # Snap to grid
                if self.rng.random() < p.snap_epsilon:
                    snapped = round(pos / subdivision_ms) * subdivision_ms
                else:
                    snapped = pos + self.rng.uniform(-subdivision_ms * 0.1, subdivision_ms * 0.1)

                events.append(MidiEvent(
                    note=int(pitch),
                    velocity=velocity,
                    start_ms=snapped,
                    duration_ms=dur,
                    channel=p.midi_channel,
                ))

                current_pitch = pitch
                pos += subdivision_ms
                step += 1

        # Ensure consensus at the final bar boundary
        if events:
            last_event = events[-1]
            final_bar_end = bars * bar_ms
            # Add a chord tone landing near the end if the last note
            # doesn't end near the bar boundary
            if abs(last_event.end_ms - final_bar_end) > bar_ms * 0.25:
                final_chord = chord_progression[-1][0]
                consensus_pitch = self._consensus_pitch(final_chord, last_event.note)
                events.append(MidiEvent(
                    note=int(consensus_pitch),
                    velocity=self.rng.randint(p.velocity_range[0], p.velocity_range[1]),
                    start_ms=final_bar_end - subdivision_ms,
                    duration_ms=subdivision_ms,
                    channel=p.midi_channel,
                ))

        return events

    # ---- internal helpers ----

    def _note_range(self) -> tuple[int, int]:
        """Return (lo, hi) MIDI note numbers for this agent's preferred range."""
        # MIDI convention: C4 = 60. octave_range is in this convention.
        lo = self.personality.octave_range[0] * 12 + 12  # C{octave}
        hi = (self.personality.octave_range[1] + 1) * 12 + 11  # B{octave}
        return lo, hi

    def _pick_starting_pitch(self, harmony_context: dict) -> float:
        """Pick a starting note, preferring chord tones."""
        chord_progression = harmony_context.get("chord_progression", [("Dm7", 4)])
        first_chord = chord_progression[0][0]
        tones = CHORD_TONES.get(first_chord, D_DORIAN_NOTES)
        lo, hi = self._note_range()
        valid = [n for n in tones if lo <= n <= hi]
        if not valid:
            valid = [n for n in D_DORIAN_NOTES if lo <= n <= hi]
        if not valid:
            valid = D_DORIAN_NOTES[:5]
        return float(self.rng.choice(valid))

    def _consensus_pitch(self, chord_name: str, current_pitch: float) -> float:
        """Return a chord tone closest to current pitch (consensus constraint)."""
        tones = CHORD_TONES.get(chord_name, D_DORIAN_NOTES)
        lo, hi = self._note_range()
        valid = [n for n in tones if lo <= n <= hi]
        if not valid:
            valid = D_DORIAN_NOTES
        return float(min(valid, key=lambda n: abs(n - current_pitch)))

    def _next_pitch(self, current: float, direction: int, chord_name: str) -> float:
        """Generate the next pitch using preferred intervals."""
        intervals = self.personality.preferred_intervals
        # Pick an interval
        interval = self.rng.choice(intervals)
        step = direction * interval
        candidate = current + step

        # Keep in range
        lo, hi = self._note_range()
        if candidate < lo:
            candidate = current + abs(interval)
        elif candidate > hi:
            candidate = current - abs(interval)

        # Snap toward scale notes
        scale = D_DORIAN_NOTES
        nearest = min(scale, key=lambda n: abs(n - candidate))
        if abs(nearest - candidate) <= 2:
            candidate = float(nearest)

        return max(0.0, min(127.0, candidate))

    def __repr__(self) -> str:
        return f"AIAgent({self.personality.name!r}, instrument={self.personality.instrument!r})"
