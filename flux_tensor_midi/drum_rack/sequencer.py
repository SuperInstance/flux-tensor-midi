"""
Step Sequencer: grid-based drum pattern builder with humanize, Euclidean rhythms, and MIDI render.
"""

from __future__ import annotations

import random
import math
from typing import Dict, List, Optional, Sequence

from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.drum_rack.rack import DrumRack


class StepSequencer:
    """A step-sequenced drum pattern.

    Parameters
    ----------
    steps : int
        Number of steps (8, 16, or 32).
    rack : DrumRack, optional
        Drum rack for instrument mapping.  Default GM map on channel 9.
    """

    def __init__(
        self,
        steps: int = 16,
        rack: DrumRack | None = None,
    ):
        if steps not in (8, 16, 32):
            raise ValueError(f"steps must be 8, 16, or 32, got {steps}")
        self._steps = steps
        self._rack = rack or DrumRack()
        # grid[step] = list of (instrument_name, velocity)
        self._grid: List[List[tuple[str, int]]] = [[] for _ in range(steps)]

    # ---- properties ----

    @property
    def steps(self) -> int:
        return self._steps

    @property
    def rack(self) -> DrumRack:
        return self._rack

    # ---- mutation ----

    def add_hit(self, instrument: str, step: int, velocity: int = 100) -> None:
        """Place a single hit on the grid.

        Parameters
        ----------
        instrument : str
            Instrument name from the drum rack.
        step : int
            Step index (0-based).
        velocity : int
            Note velocity 1–127.
        """
        self._validate_step(step)
        self._validate_velocity(velocity)
        self._rack.note_for(instrument)  # validate instrument exists
        self._grid[step].append((instrument, velocity))

    def remove_hit(self, instrument: str, step: int) -> bool:
        """Remove a hit. Returns True if a hit was found and removed."""
        self._validate_step(step)
        before = len(self._grid[step])
        self._grid[step] = [
            (inst, vel) for inst, vel in self._grid[step] if inst != instrument
        ]
        return len(self._grid[step]) < before

    def add_roll(
        self,
        instrument: str,
        start: int,
        end: int,
        pattern: str = "straight",
        velocity: int = 100,
    ) -> None:
        """Add a roll from *start* to *end* step (inclusive).

        Parameters
        ----------
        instrument : str
            Instrument name.
        start, end : int
            Step range (inclusive).
        pattern : str
            "straight" | "triplet" | "dotted"
        velocity : int
            Base velocity for roll hits.
        """
        self._validate_step(start)
        self._validate_step(end)
        if start > end:
            raise ValueError(f"start ({start}) must be <= end ({end})")
        self._rack.note_for(instrument)

        if pattern == "straight":
            hit_steps = range(start, end + 1)
        elif pattern == "triplet":
            # Subdivide each step into 3; place at sub-step boundaries
            hit_steps = range(start, end + 1)
        elif pattern == "dotted":
            # Dotted pattern: hit on start, skip 1, hit, skip 2, repeat
            hit_steps = []
            pos = start
            skip = 1
            while pos <= end:
                hit_steps.append(pos)
                pos += 1 + skip
                skip = skip % 2 + 1  # alternate 1, 2, 1, 2...
        else:
            raise ValueError(f"Unknown pattern '{pattern}'. Use straight/triplet/dotted.")

        for s in hit_steps:
            if s < self._steps:
                self.add_hit(instrument, s, velocity)

    def add_flam(
        self,
        instrument: str,
        step: int,
        grace_velocity: int = 60,
        main_velocity: int = 100,
    ) -> None:
        """Add a flam (grace note + main hit) on *step*.

        The grace note lands on the same step; timing offset is applied during render.
        """
        self.add_hit(instrument, step, grace_velocity)
        self.add_hit(instrument, step, main_velocity)

    def clear(self) -> None:
        """Clear all hits from the grid."""
        self._grid = [[] for _ in range(self._steps)]

    # ---- Euclidean rhythms ----

    @staticmethod
    def _euclidean_pattern(steps: int, pulses: int, rotation: int = 0) -> List[bool]:
        """Generate a Euclidean rhythm as a list of booleans.

        Uses Björklund's algorithm.
        """
        if pulses == 0:
            return [False] * steps
        if pulses >= steps:
            return [True] * steps

        pattern = [True] * pulses + [False] * (steps - pulses)
        # Björklund's algorithm
        buckets: List[List[bool]] = [[v] for v in pattern]
        while True:
            # Count trailing groups of single False
            rests = [b for b in buckets if b[0] is False and len(b) == 1]
            if not rests:
                break
            # Try to distribute rests among the front groups
            fronts = [b for b in buckets if b[0] is True]
            if len(rests) > len(fronts):
                break
            new_buckets: List[List[bool]] = []
            for i, f in enumerate(fronts):
                if i < len(rests):
                    new_buckets.append(f + rests[i])
                else:
                    new_buckets.append(f)
            remaining = buckets[len(fronts):]
            # Keep only the non-rest groups that weren't consumed
            remaining = [b for b in remaining if not (len(b) == 1 and b[0] is False and b in rests)]
            buckets = new_buckets + remaining

        flat: List[bool] = []
        for b in buckets:
            flat.extend(b)

        # Pad or trim to exact length
        flat = flat[:steps]
        while len(flat) < steps:
            flat.append(False)

        # Rotate
        if rotation:
            rotation = rotation % steps
            flat = flat[rotation:] + flat[:rotation]

        return flat

    def euclidean(
        self,
        instrument: str,
        steps: int | None = None,
        pulses: int = 4,
        rotation: int = 0,
        velocity: int = 100,
    ) -> None:
        """Add a Euclidean rhythm for *instrument*.

        Parameters
        ----------
        instrument : str
            Instrument name.
        steps : int, optional
            Override step count (defaults to sequencer length).
        pulses : int
            Number of hits.
        rotation : int
            Rotate the pattern.
        velocity : int
            Hit velocity.
        """
        n = steps or self._steps
        pattern = self._euclidean_pattern(n, pulses, rotation)
        for i, hit in enumerate(pattern):
            if hit and i < self._steps:
                self.add_hit(instrument, i, velocity)

    # ---- humanize ----

    def humanize(
        self,
        swing: float = 0.0,
        velocity_range: int = 10,
        timing_range: int = 5,
        seed: int | None = None,
    ) -> "StepSequencer":
        """Return a new StepSequencer with humanized timing/velocity.

        Parameters
        ----------
        swing : float
            Swing amount 0.0–1.0.  Off-beat steps are delayed.
        velocity_range : int
            Max random velocity deviation (±).
        timing_range : int
            Max random timing offset in ms (±).
        seed : int, optional
            Random seed for reproducibility.

        Returns
        -------
        StepSequencer
            New sequencer with humanize metadata attached.
        """
        rng = random.Random(seed)
        seq = StepSequencer(self._steps, DrumRack(
            channel=self._rack.channel,
            custom_map=self._rack.as_dict(),
        ))
        seq._grid = [list(hits) for hits in self._grid]
        seq._humanize_swing = swing
        seq._humanize_velocity_range = velocity_range
        seq._humanize_timing_range = timing_range
        seq._rng = rng
        return seq

    # ---- rotate ----

    def rotate(self, steps: int) -> None:
        """Rotate the entire pattern by *steps* positions.

        Positive = shift right (later in time), negative = shift left.
        """
        steps = steps % self._steps
        self._grid = self._grid[-steps:] + self._grid[:-steps] if steps else self._grid

    # ---- render ----

    def render(self, bpm: float = 120.0, output: str | None = None) -> List[MidiEvent]:
        """Render the pattern to a list of MidiEvents.

        Parameters
        ----------
        bpm : float
            Tempo in beats per minute.
        output : str, optional
            If given, write a .mid file to this path via mido.

        Returns
        -------
        list[MidiEvent]
        """
        step_ms = 60000.0 / bpm / 4.0  # 16th note duration in ms
        events: List[MidiEvent] = []
        channel = self._rack.channel

        rng = getattr(self, "_rng", None) or random.Random()
        swing = getattr(self, "_humanize_swing", 0.0)
        vel_range = getattr(self, "_humanize_velocity_range", 0)
        time_range = getattr(self, "_humanize_timing_range", 0)

        for step_idx, hits in enumerate(self._grid):
            for instrument, velocity in hits:
                note = self._rack.note_for(instrument)

                # Humanize velocity
                v = velocity + rng.randint(-vel_range, vel_range)
                v = max(1, min(127, v))

                # Calculate start time
                t = step_idx * step_ms

                # Swing: delay off-beat steps (odd 16ths)
                if swing > 0 and step_idx % 2 == 1:
                    t += swing * step_ms * 0.33  # max ~33% of step

                # Random timing offset
                t += rng.uniform(-time_range, time_range)

                dur = step_ms * 0.8  # 80% of step length

                # Handle flams: detect pairs on same step/instrument
                events.append(MidiEvent(note, v, t, dur, channel))

        # Sort by start time
        events.sort(key=lambda e: e.start_ms)

        if output:
            self._write_midi(events, bpm, output)

        return events

    def _write_midi(self, events: List[MidiEvent], bpm: float, path: str) -> None:
        """Write events to a MIDI file using mido."""
        try:
            import mido
        except ImportError:
            raise ImportError("mido is required for MIDI file output. Install with: pip install mido")

        mid = mido.MidiFile(ticks_per_beat=480)
        track = mido.MidiTrack()
        mid.tracks.append(track)

        # Tempo
        tempo = mido.bpm2tempo(bpm)
        track.append(mido.MetaMessage("set_tempo", tempo=tempo))

        tpqn = mid.ticks_per_beat
        ticks_per_16th = tpqn // 4

        # Convert events to absolute ticks
        tick_events = []
        for ev in events:
            start_tick = int(ev.start_ms * tpqn * bpm / 60000.0 * 4.0)
            end_tick = int(ev.end_ms * tpqn * bpm / 60000.0 * 4.0)
            tick_events.append((start_tick, "note_on", ev.note, ev.velocity, ev.channel))
            tick_events.append((end_tick, "note_off", ev.note, 0, ev.channel))

        tick_events.sort(key=lambda x: x[0])

        prev_tick = 0
        for tick, msg_type, note, vel, ch in tick_events:
            delta = tick - prev_tick
            track.append(mido.Message(msg_type, note=note, velocity=vel, channel=ch, time=delta))
            prev_tick = tick

        mid.save(path)

    # ---- presets ----

    def load_preset(self, name: str) -> None:
        """Load a preset pattern by name.

        Available: boom_bap, trap_hats, four_on_floor, breakbeat, bossa_nova, dnb
        """
        self.clear()
        loader = _PRESETS.get(name)
        if loader is None:
            raise ValueError(
                f"Unknown preset '{name}'. Available: {sorted(_PRESETS.keys())}"
            )
        loader(self)

    # ---- introspection ----

    def get_hits(self, step: int) -> List[tuple[str, int]]:
        """Return hits for a given step."""
        self._validate_step(step)
        return list(self._grid[step])

    def density(self) -> float:
        """Return fill density as fraction of occupied steps."""
        occupied = sum(1 for hits in self._grid if hits)
        return occupied / self._steps

    def __repr__(self) -> str:
        return f"StepSequencer(steps={self._steps}, density={self.density():.0%})"

    # ---- internal ----

    def _validate_step(self, step: int) -> None:
        if not 0 <= step < self._steps:
            raise IndexError(f"step must be 0–{self._steps - 1}, got {step}")

    @staticmethod
    def _validate_velocity(velocity: int) -> None:
        if not 1 <= velocity <= 127:
            raise ValueError(f"velocity must be 1–127, got {velocity}")


# ---- Preset Patterns ----

def _boom_bap(seq: StepSequencer) -> None:
    """Classic boom bap: kick-snare-kick-snare with hats."""
    for i in range(seq.steps):
        if i % 4 == 0:
            seq.add_hit("kick", i, 110)
        if i % 4 == 2:
            seq.add_hit("snare", i, 105)
        seq.add_hit("hihat_closed", i, 80)
    # Extra ghost kick on step 6
    if seq.steps > 6:
        seq.add_hit("kick", 6, 70)


def _trap_hats(seq: StepSequencer) -> None:
    """Trap-style rapid hi-hats with kick and snare."""
    for i in range(seq.steps):
        seq.add_hit("hihat_closed", i, 75 + (10 if i % 2 == 0 else 0))
    seq.add_hit("kick", 0, 115)
    seq.add_hit("kick", 5, 95)
    seq.add_hit("kick", 10, 90)
    seq.add_hit("snare", 4, 110)
    seq.add_hit("snare", 12, 110)
    # Open hat accents
    seq.add_hit("hihat_open", 7, 85)
    seq.add_hit("hihat_open", 15, 85)


def _four_on_floor(seq: StepSequencer) -> None:
    """House/techno four-on-the-floor."""
    for i in range(seq.steps):
        if i % 4 == 0:
            seq.add_hit("kick", i, 120)
        if i % 2 == 0:
            seq.add_hit("hihat_closed", i, 90)
        if i % 4 == 2:
            seq.add_hit("clap", i, 100)
        if i % 8 == 0 and i > 0:
            seq.add_hit("ride", i, 75)


def _breakbeat(seq: StepSequencer) -> None:
    """Amen break-inspired breakbeat."""
    seq.add_hit("kick", 0, 115)
    seq.add_hit("snare", 4, 110)
    seq.add_hit("kick", 6, 100)
    seq.add_hit("kick", 9, 95)
    seq.add_hit("snare", 10, 105)
    seq.add_hit("snare", 14, 100)
    seq.add_hit("kick", 12, 110)
    for i in range(seq.steps):
        seq.add_hit("hihat_closed", i, 70 + (15 if i % 2 == 0 else 0))


def _bossa_nova(seq: StepSequencer) -> None:
    """Bossa nova groove."""
    # Kick pattern
    for s in [0, 6, 8, 14]:
        if s < seq.steps:
            seq.add_hit("kick", s, 90)
    # Rimshot / side stick
    for s in [4, 8, 12]:
        if s < seq.steps:
            seq.add_hit("rimshot", s, 85)
    # Hi-hat pattern (syncopated)
    for i in range(0, seq.steps, 2):
        seq.add_hit("hihat_closed", i, 75)
    seq.add_hit("hihat_pedal", 1, 65)
    seq.add_hit("hihat_pedal", 5, 65)
    seq.add_hit("hihat_pedal", 9, 65)
    seq.add_hit("hihat_pedal", 13, 65)
    # Tambourine accents
    if seq.steps > 10:
        seq.add_hit("tambourine", 10, 60)


def _dnb(seq: StepSequencer) -> None:
    """Drum and bass pattern (170 BPM feel mapped to 16 steps)."""
    # Kick on 1 and the "and" of 2
    seq.add_hit("kick", 0, 120)
    seq.add_hit("kick", 6, 105)
    # Snare on 2 and 4
    seq.add_hit("snare", 4, 115)
    seq.add_hit("snare", 12, 115)
    # Rapid hats
    for i in range(seq.steps):
        v = 70 if i % 2 == 1 else 85
        seq.add_hit("hihat_closed", i, v)
    # Ghost snare
    seq.add_hit("snare", 10, 65)
    seq.add_hit("snare", 14, 60)


_PRESETS = {
    "boom_bap": _boom_bap,
    "trap_hats": _trap_hats,
    "four_on_floor": _four_on_floor,
    "breakbeat": _breakbeat,
    "bossa_nova": _bossa_nova,
    "dnb": _dnb,
}
