"""
Multi-track arrangements and looping — what producers actually need.

Electronic, hip-hop, jazz — real music has multiple instruments playing
together, and those patterns loop with variation. This module provides:

- Track: A single musician track with its own role, state, and clock
- Arrangement: Multiple tracks playing together, with looping and variation
- Presets: trap_beat, techno_loop, jazz_combo — ready to go

Usage:
    from flux_tensor_midi.tracks import Arrangement, trap_beat
    beat = trap_beat(bpm=140, bars=8)
    beat.generate_all()
    events = beat.to_midi_events()
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.snap import RhythmicRole, EisensteinSnap
from flux_tensor_midi.core.clock import TZeroClock
from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.ensemble.band import Band
from flux_tensor_midi.ensemble.score import Score


class Track:
    """A single musician track with its own role, state, and clock.

    Each track wraps a RoomMusician and adds track-level features
    like quantization, voice assignment, and note range.
    """

    VOICE_RANGES: Dict[str, Tuple[int, int]] = {
        'piano': (48, 84),
        'bass': (24, 48),
        'synth': (60, 96),
        'hat': (60, 72),
        'snare': (40, 50),
        'kick': (24, 36),
        'pad': (48, 72),
        'lead': (60, 96),
        'arp': (60, 96),
        'strings': (48, 84),
        'sax': (54, 78),
        'drums': (24, 60),
        'violin': (55, 84),
        'viola': (48, 72),
        'cello': (36, 60),
    }

    def __init__(
        self,
        name: str,
        role: RhythmicRole = RhythmicRole.ROOT,
        voice: str = 'piano',
        bpm: float = 120.0,
        seed: Optional[int] = None,
    ):
        self._name = name
        self._role = role
        self._voice = voice
        self._bpm = bpm
        self._seed = seed

        clock = TZeroClock(bpm=bpm)
        self._musician = RoomMusician(name=name, role=role, clock=clock)

        # Note range for this voice
        lo, hi = self.VOICE_RANGES.get(voice, (48, 84))
        self._note_lo = lo
        self._note_hi = hi

        # Generated events
        self._events: List[MidiEvent] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def role(self) -> RhythmicRole:
        return self._role

    @property
    def voice(self) -> str:
        return self._voice

    @property
    def musician(self) -> RoomMusician:
        return self._musician

    @property
    def events(self) -> List[MidiEvent]:
        return list(self._events)

    def generate(self, bars: int = 4, ticks_per_bar: int = 16) -> None:
        """Generate MIDI events for this track.

        Each tick advances the room's clock and converts the
        FluxVector state to MIDI events. If the state is all zeros,
        generates a pattern based on the voice and role.
        """
        self._events.clear()

        import numpy as np
        rng = np.random.RandomState(self._seed) if self._seed is not None else np.random

        quarter_note_ms = 60000.0 / self._bpm
        sixteenth_ms = quarter_note_ms / 4.0

        total_ticks = bars * ticks_per_bar
        state = self._musician.state

        # If state is all zeros, generate a role-appropriate pattern
        if state.magnitude == 0:
            # Create a default pattern based on role
            pattern = self._default_pattern()
            state = FluxVector(
                pattern,
                salience=[1.0] * 9,
                tolerance=[0.1] * 9,
            )
            self._musician.update_state(state)

        for tick in range(total_ticks):
            ts, vec = self._musician.emit()

            # Generate notes from active FluxVector channels
            for ch in range(9):
                val = vec[ch] if ch < len(vec) else 0.0
                if val < 0.05:
                    continue

                # Map channel to a note within voice range
                note_range = self._note_hi - self._note_lo
                note = self._note_lo + (ch * note_range // 9)
                # Add small random variation
                note = min(127, max(0, note + rng.randint(-2, 3)))

                velocity = min(127, max(1, int(val * 120)))
                duration = sixteenth_ms * rng.choice([1, 2, 3, 4])

                self._events.append(MidiEvent(
                    note=note,
                    velocity=velocity,
                    start_ms=ts,
                    duration_ms=float(duration),
                    channel=0,
                ))

    def _default_pattern(self) -> list:
        """Generate a default salience pattern based on role."""
        from flux_tensor_midi.core.snap import RhythmicRole
        if self._role == RhythmicRole.ROOT:
            return [0.8, 0.0, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0]  # beats 1,4
        elif self._role == RhythmicRole.HALFTIME:
            return [0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # beat 1 only
        elif self._role == RhythmicRole.DOUBLETIME:
            return [0.4, 0.3, 0.4, 0.3, 0.4, 0.3, 0.0, 0.0, 0.0]  # every tick
        elif self._role == RhythmicRole.TRIPLET:
            return [0.5, 0.0, 0.5, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0]  # triplet feel
        elif self._role == RhythmicRole.OFFSET:
            return [0.0, 0.0, 0.5, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0]  # offbeats
        else:
            return [0.5, 0.3, 0.5, 0.3, 0.5, 0.3, 0.0, 0.0, 0.0]  # generic active

    def __repr__(self) -> str:
        return (
            f"Track(name={self._name!r}, role={self._role.name}, "
            f"voice={self._voice!r}, events={len(self._events)})"
        )


class Arrangement:
    """Multiple tracks playing together with looping and variation.

    An arrangement wraps a Band and provides high-level operations:
    generate all tracks, loop with variation, export as MIDI.
    """

    def __init__(
        self,
        name: str = 'arrangement',
        bpm: float = 120.0,
        bars: int = 4,
        seed: Optional[int] = None,
    ):
        self._name = name
        self._bpm = bpm
        self._bars = bars
        self._seed = seed
        self._tracks: List[Track] = []
        self._score = Score(title=name)
        self._loop_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def bpm(self) -> float:
        return self._bpm

    @property
    def tracks(self) -> List[Track]:
        return list(self._tracks)

    def add_track(self, track: Track) -> None:
        """Add a track to the arrangement."""
        self._tracks.append(track)

    def generate_all(self) -> None:
        """Generate events for all tracks."""
        for track in self._tracks:
            track.generate(bars=self._bars)

    def loop(self, times: int = 2) -> None:
        """Repeat the arrangement with time offsets.

        Each repetition gets time-shifted by the arrangement duration.
        """
        self._loop_count = times

    def to_midi_events(self) -> List[MidiEvent]:
        """Collect all MIDI events from all tracks."""
        all_events: List[MidiEvent] = []

        for track in self._tracks:
            events = track.events
            duration_ms = max((e.end_ms for e in events), default=0.0) if events else 0.0

            for loop in range(self._loop_count + 1):
                offset = loop * duration_ms
                for ev in events:
                    all_events.append(MidiEvent(
                        note=ev.note,
                        velocity=ev.velocity,
                        start_ms=ev.start_ms + offset,
                        duration_ms=ev.duration_ms,
                        channel=ev.channel,
                    ))

        all_events.sort(key=lambda e: e.start_ms)
        return all_events

    def summary(self) -> dict:
        """Return a summary dict."""
        total_events = sum(len(t.events) for t in self._tracks)
        return {
            'name': self._name,
            'bpm': self._bpm,
            'bars': self._bars,
            'tracks': len(self._tracks),
            'total_events': total_events,
            'loop_count': self._loop_count,
        }

    def __repr__(self) -> str:
        return (
            f"Arrangement(name={self._name!r}, tracks={len(self._tracks)}, "
            f"bpm={self._bpm}, bars={self._bars})"
        )


# ── Presets ──────────────────────────────────────────────────────────────────

def trap_beat(bpm: int = 140, bars: int = 8, seed: Optional[int] = None) -> Arrangement:
    """Create a trap beat arrangement."""
    arr = Arrangement(name='trap_beat', bpm=float(bpm), bars=bars, seed=seed)
    arr.add_track(Track('kick', RhythmicRole.ROOT, 'kick', bpm=float(bpm), seed=seed))
    arr.add_track(Track('hat', RhythmicRole.DOUBLETIME, 'hat', bpm=float(bpm), seed=seed))
    arr.add_track(Track('bass', RhythmicRole.HALFTIME, 'bass', bpm=float(bpm), seed=seed))
    return arr


def techno_loop(bpm: int = 128, bars: int = 16, seed: Optional[int] = None) -> Arrangement:
    """Create a techno loop arrangement."""
    arr = Arrangement(name='techno_loop', bpm=float(bpm), bars=bars, seed=seed)
    arr.add_track(Track('kick', RhythmicRole.ROOT, 'kick', bpm=float(bpm), seed=seed))
    arr.add_track(Track('synth', RhythmicRole.OFFSET, 'synth', bpm=float(bpm), seed=seed))
    arr.add_track(Track('arp', RhythmicRole.DOUBLETIME, 'arp', bpm=float(bpm), seed=seed))
    return arr


def jazz_combo(bpm: int = 180, bars: int = 12, seed: Optional[int] = None) -> Arrangement:
    """Create a jazz combo arrangement."""
    arr = Arrangement(name='jazz_combo', bpm=float(bpm), bars=bars, seed=seed)
    arr.add_track(Track('piano', RhythmicRole.ROOT, 'piano', bpm=float(bpm), seed=seed))
    arr.add_track(Track('bass', RhythmicRole.HALFTIME, 'bass', bpm=float(bpm), seed=seed))
    arr.add_track(Track('drums', RhythmicRole.TRIPLET, 'drums', bpm=float(bpm), seed=seed))
    return arr
