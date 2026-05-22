"""
Score: A written record of a performance.

Records events from all musicians over time and provides
playback/analysis capabilities.
"""

from __future__ import annotations
from typing import Any
import mido
from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.harmony.chord import HarmonyState
from flux_tensor_midi.harmony.spectrum import spectral_flux


class Score:
    """A recorded performance score.

    Stores timestamped events from multiple musicians and
    provides analysis and export utilities.

    Parameters
    ----------
    title : str, default="Untitled"
        Score title.
    """

    def __init__(self, title: str = "Untitled"):
        self._title = title
        self._events: dict[str, list[tuple[float, FluxVector]]] = {}
        self._side_channels: dict[str, dict[str, list[float]]] = {}

    @property
    def title(self) -> str:
        """Score title."""
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        """Set the score title."""
        if not isinstance(value, str):
            raise TypeError(f"title must be str, got {type(value).__name__}")
        self._title = value

    @property
    def musician_names(self) -> list[str]:
        """List of all musician names that have recorded events."""
        return list(self._events.keys())

    # ---- recording ----

    def record_event(self, musician: str, timestamp: float, vector: FluxVector) -> None:
        """Record an event from a musician.

        Parameters
        ----------
        musician : str
            Musician name.
        timestamp : float
            Event timestamp in milliseconds.
        vector : FluxVector
            The event vector.
        """
        if musician not in self._events:
            self._events[musician] = []
        self._events[musician].append((timestamp, vector))

    def record_side_channel(self, musician: str, channel: str, timestamp: float) -> None:
        """Record a side-channel event.

        Parameters
        ----------
        musician : str
            Musician name.
        channel : str
            Side-channel type (e.g., "nod", "smile", "frown").
        timestamp : float
            Event timestamp.
        """
        if musician not in self._side_channels:
            self._side_channels[musician] = {}
        if channel not in self._side_channels[musician]:
            self._side_channels[musician][channel] = []
        self._side_channels[musician][channel].append(timestamp)

    # ---- access ----

    def events_for(self, musician: str) -> list[tuple[float, FluxVector]]:
        """Get all events for a musician.

        Parameters
        ----------
        musician : str
            Musician name.

        Returns
        -------
        list[tuple[float, FluxVector]]
            All recorded events for that musician.
        """
        return list(self._events.get(musician, []))

    def vectors_for(self, musician: str) -> list[FluxVector]:
        """Get all FluxVectors for a musician.

        Parameters
        ----------
        musician : str
            Musician name.

        Returns
        -------
        list[FluxVector]
            All vectors recorded for that musician.
        """
        return [v for _, v in self._events.get(musician, [])]

    def all_events(self) -> list[tuple[str, float, FluxVector]]:
        """Get all events across all musicians, sorted by timestamp.

        Returns
        -------
        list[tuple[str, float, FluxVector]]
            [(musician, timestamp, vector), ...] sorted by timestamp.
        """
        flat: list[tuple[str, float, FluxVector]] = []
        for musician, events in self._events.items():
            for ts, vec in events:
                flat.append((musician, ts, vec))
        flat.sort(key=lambda x: x[1])
        return flat

    # ---- analysis ----

    def total_events(self) -> int:
        """Total number of events across all musicians.

        Returns
        -------
        int
            Total event count.
        """
        return sum(len(events) for events in self._events.values())

    def duration_ms(self) -> float:
        """Total duration (last timestamp - first timestamp) in ms.

        Returns
        -------
        float
            Duration in milliseconds. Returns 0.0 if no events.
        """
        all_events = self.all_events()
        if not all_events:
            return 0.0
        return all_events[-1][1] - all_events[0][1]

    def spectral_flux(self, musician: str) -> float:
        """Spectral flux for a specific musician.

        Parameters
        ----------
        musician : str
            Musician name.

        Returns
        -------
        float
            Average rate of harmonic change.
        """
        vecs = self.vectors_for(musician)
        return spectral_flux(vecs)

    def harmony_at(self, timestamp: float, window_ms: float = 100.0) -> HarmonyState | None:
        """Get the harmonic state near a given timestamp.

        Collects the nearest event from each musician within window_ms.

        Parameters
        ----------
        timestamp : float
            Target timestamp in milliseconds.
        window_ms : float, default=100.0
            Search window radius.

        Returns
        -------
        HarmonyState | None
            Harmonic state if any events are found, else None.
        """
        if not self._events:
            return None

        nearest: list[FluxVector] = []
        for musician, events in self._events.items():
            best_vec = None
            best_dist = window_ms
            for ts, vec in events:
                dist = abs(ts - timestamp)
                if dist < best_dist:
                    best_dist = dist
                    best_vec = vec
            if best_vec is not None:
                nearest.append(best_vec)

        if not nearest:
            return None

        return HarmonyState(nearest)

    # ---- export ----

    def to_midi_events(self, velocity_scale: int = 100) -> list[MidiEvent]:
        """Convert the score to a flat list of MIDI events.

        Each FluxVector channel becomes a note.

        Parameters
        ----------
        velocity_scale : int, default=100
            Scaling factor for note velocities.

        Returns
        -------
        list[MidiEvent]
            Sorted list of MIDI events.
        """
        midi_events: list[MidiEvent] = []
        for musician, events in self._events.items():
            # Simple: use a consistent channel offset per musician
            ch_idx = min(self.musician_names.index(musician), 15)
            for ts, vec in events:
                midi_events.extend(
                    MidiEvent.from_flux(
                        vec.values,
                        start_ms=ts,
                        duration_ms=250.0,  # quarter note default
                        channel=ch_idx,
                        velocity_scale=velocity_scale,
                    )
                )
        midi_events.sort(key=lambda e: e.start_ms)
        return midi_events

    def to_midi(self, bpm: float | None = None, ppqn: int = 480, velocity_scale: int = 100) -> mido.MidiFile:
        """Convert the score to a mido.MidiFile.

        Parameters
        ----------
        bpm : float | None
            Tempo for the MIDI file. Defaults to 120.
        ppqn : int, default=480
            Pulses per quarter note.
        velocity_scale : int, default=100
            Scaling factor for note velocities.

        Returns
        -------
        mido.MidiFile
            A standard MIDI file object.
        """
        midi_events = self.to_midi_events(velocity_scale=velocity_scale)
        tempo_bpm = bpm or 120.0

        mid = mido.MidiFile(ticks_per_beat=ppqn)
        tempo_us = mido.bpm2tempo(tempo_bpm)

        # Group events by MIDI channel
        channels: dict[int, list[MidiEvent]] = {}
        for ev in midi_events:
            channels.setdefault(ev.channel, []).append(ev)

        # Always create a tempo track
        tempo_track = mido.MidiTrack()
        tempo_track.append(mido.MetaMessage("set_tempo", tempo=tempo_us, time=0))
        tempo_track.append(mido.MetaMessage("track_name", name=self._title, time=0))
        mid.tracks.append(tempo_track)

        # Create one track per channel
        for ch, events in sorted(channels.items()):
            track = mido.MidiTrack()
            track.append(mido.MetaMessage("track_name", name=f"Channel {ch}", time=0))

            # Sort events by start time
            events.sort(key=lambda e: e.start_ms)

            # Convert ms to ticks
            ms_per_tick = tempo_us / (ppqn * 1000.0)

            # Build a timeline of note_on / note_off absolute tick positions
            timeline: list[tuple[int, str, int, int]] = []  # (abs_tick, type, note, velocity)
            for ev in events:
                start_tick = round(ev.start_ms / ms_per_tick)
                end_tick = round(ev.end_ms / ms_per_tick)
                timeline.append((start_tick, "note_on", ev.note, ev.velocity))
                timeline.append((end_tick, "note_off", ev.note, 0))

            # Sort: note_off before note_on at same tick
            timeline.sort(key=lambda x: (x[0], 0 if x[1] == "note_off" else 1))

            # Convert to delta ticks and append
            prev_tick = 0
            for abs_tick, msg_type, note, vel in timeline:
                delta = max(0, abs_tick - prev_tick)
                track.append(mido.Message(msg_type, channel=ch, note=note, velocity=vel, time=delta))
                prev_tick = abs_tick

            mid.tracks.append(track)

        return mid

    def to_midi_file(self, filename: str, bpm: float | None = None, ppqn: int = 480, velocity_scale: int = 100) -> None:
        """Write the score to a .mid file.

        Parameters
        ----------
        filename : str
            Output file path.
        bpm : float | None
            Tempo for the MIDI file. Defaults to 120.
        ppqn : int, default=480
            Pulses per quarter note.
        velocity_scale : int, default=100
            Scaling factor for note velocities.
        """
        mid = self.to_midi(bpm=bpm, ppqn=ppqn, velocity_scale=velocity_scale)
        mid.save(filename)

    def summary(self) -> dict[str, Any]:
        """Get a summary dict for the score.

        Returns
        -------
        dict[str, Any]
            Summary statistics.
        """
        return {
            "title": self._title,
            "musicians": len(self._events),
            "total_events": self.total_events(),
            "duration_ms": self.duration_ms(),
            "events_per_musician": {
                name: len(events) for name, events in self._events.items()
            },
        }

    def __repr__(self) -> str:
        return (
            f"Score(title={self._title!r}, "
            f"musicians={len(self._events)}, "
            f"events={self.total_events()})"
        )


__all__ = ["Score"]
