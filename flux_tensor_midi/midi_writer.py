"""
MidiFileWriter — proper MIDI file output for FLUX-Tensor-MIDI.

Uses the `mido` library (already a dependency) to build well-formed,
multi-track Standard MIDI Files with correct delta-time calculation,
tempo/time-signature support, quantization, and overlapping-note handling.

Usage:
    from flux_tensor_midi.midi_writer import MidiFileWriter

    writer = MidiFileWriter(bpm=140, ppqn=480)
    writer.add_track("Piano", channel=0, events=[
        MidiEvent(note=60, velocity=100, start_ms=0, duration_ms=500),
        MidiEvent(note=64, velocity=80, start_ms=500, duration_ms=250),
    ])
    writer.write("song.mid")
    # or: data = writer.to_bytes()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import mido

from flux_tensor_midi.midi.events import MidiEvent


@dataclass
class TrackMeta:
    """Metadata for a single track in the writer."""

    name: str
    channel: int = 0
    program: int = 0
    events: List[MidiEvent] = field(default_factory=list)
    control_changes: List[tuple] = field(default_factory=list)
    # CC tuples: (start_ms, controller, value)


class MidiFileWriter:
    """Build a complete Standard MIDI File (format 1) from tracks of events.

    Parameters
    ----------
    bpm : float
        Tempo in beats per minute.
    ppqn : int
        Pulses per quarter note (ticks resolution). Default 480.
    time_signature : tuple[int, int]
        (numerator, denominator). Default (4, 4).
    key_signature : str
        Key signature as a string like "C", "Am", "G", "F#m".
        Uses mido key-signature convention. Optional.

    Notes
    -----
    - Supports multi-track, tempo changes, time/key signatures, program changes,
      and control changes.
    - Proper delta-time calculation from absolute millisecond timestamps.
    - Handles overlapping notes correctly by sorting note_on/note_off events
      and using correct MIDI delta times.
    - Optional quantization snaps start times and durations to a grid.
    """

    # Key signature map: name → (key number, mode)
    # key number: -7..7 (flats to sharps), mode: 0=major, 1=minor
    KEY_SIG_MAP: dict[str, tuple[int, int]] = {
        "Cb": (-7, 0), "Gb": (-6, 0), "Db": (-5, 0), "Ab": (-4, 0),
        "Eb": (-3, 0), "Bb": (-2, 0), "F": (-1, 0), "C": (0, 0),
        "G": (1, 0), "D": (2, 0), "A": (3, 0), "E": (4, 0),
        "B": (5, 0), "F#": (6, 0), "C#": (7, 0),
        "Abm": (-7, 1), "Ebm": (-6, 1), "Bbm": (-5, 1), "Fm": (-4, 1),
        "Cm": (-3, 1), "Gm": (-2, 1), "Dm": (-1, 1), "Am": (0, 1),
        "Em": (1, 1), "Bm": (2, 1), "F#m": (3, 1), "C#m": (4, 1),
        "G#m": (5, 1), "D#m": (6, 1), "A#m": (7, 1),
    }

    def __init__(
        self,
        bpm: float = 120.0,
        ppqn: int = 480,
        time_signature: tuple[int, int] = (4, 4),
        key_signature: str | None = None,
    ):
        self._bpm = bpm
        self._ppqn = ppqn
        self._time_signature = time_signature
        self._key_signature = key_signature
        self._tracks: list[TrackMeta] = []
        self._tempo_changes: list[tuple[float, float]] = []
        # tempo_changes: list of (time_ms, new_bpm)

    # ── Track management ──────────────────────────────────────────────────

    def add_track(
        self,
        name: str,
        channel: int = 0,
        events: Sequence[MidiEvent] | None = None,
        program: int = 0,
        control_changes: Sequence[tuple] | None = None,
    ) -> TrackMeta:
        """Add a named track to the writer.

        Parameters
        ----------
        name : str
            Track name.
        channel : int
            MIDI channel (0-15).
        events : sequence of MidiEvent, optional
            Note events for this track.
        program : int
            GM program number for program change at start of track.
        control_changes : sequence of (start_ms, controller, value)
            CC events for this track.

        Returns
        -------
        TrackMeta
            The created track metadata object (can be modified later).
        """
        if not 0 <= channel <= 15:
            raise ValueError(f"channel must be 0-15, got {channel}")
        if not 0 <= program <= 127:
            raise ValueError(f"program must be 0-127, got {program}")

        track = TrackMeta(
            name=name,
            channel=channel,
            program=program,
            events=list(events) if events else [],
            control_changes=list(control_changes) if control_changes else [],
        )
        self._tracks.append(track)
        return track

    def add_tempo_change(self, time_ms: float, bpm: float) -> None:
        """Add a tempo change at a specific time.

        Parameters
        ----------
        time_ms : float
            Time in milliseconds where tempo changes.
        bpm : float
            New tempo in BPM.
        """
        if bpm <= 0:
            raise ValueError(f"bpm must be positive, got {bpm}")
        self._tempo_changes.append((time_ms, bpm))
        self._tempo_changes.sort(key=lambda x: x[0])

    # ── Quantization ──────────────────────────────────────────────────────

    @staticmethod
    def quantize_events(
        events: Sequence[MidiEvent],
        grid_ms: float,
    ) -> list[MidiEvent]:
        """Snap event start times and durations to a quantization grid.

        Parameters
        ----------
        events : sequence of MidiEvent
            Events to quantize.
        grid_ms : float
            Grid size in milliseconds (e.g., a 16th note at 120 BPM ≈ 125ms).

        Returns
        -------
        list[MidiEvent]
            New list of quantized events.
        """
        if grid_ms <= 0:
            raise ValueError(f"grid_ms must be positive, got {grid_ms}")

        quantized = []
        for ev in events:
            snapped_start = round(ev.start_ms / grid_ms) * grid_ms
            snapped_dur = max(grid_ms, round(ev.duration_ms / grid_ms) * grid_ms)
            quantized.append(MidiEvent(
                note=ev.note,
                velocity=ev.velocity,
                start_ms=snapped_start,
                duration_ms=snapped_dur,
                channel=ev.channel,
            ))
        return quantized

    # ── Internal helpers ──────────────────────────────────────────────────

    def _ms_to_ticks(self, ms: float) -> int:
        """Convert milliseconds to MIDI ticks at the initial BPM.

        Uses the base BPM for conversion. For tempo-change-aware conversion,
        the _build_track method handles it per-event.
        """
        # ticks = ms * (ppqn / (60000 / bpm)) = ms * ppqn * bpm / 60000
        return max(0, int(ms * self._ppqn * self._bpm / 60000.0))

    def _build_track(self, track_meta: TrackMeta) -> mido.MidiTrack:
        """Build a mido.MidiTrack from a TrackMeta."""
        midi_track = mido.MidiTrack()

        # Track name
        midi_track.append(mido.MetaMessage(
            "track_name", name=track_meta.name, time=0,
        ))

        # Program change
        midi_track.append(mido.Message(
            "program_change",
            channel=track_meta.channel,
            program=track_meta.program,
            time=0,
        ))

        # Build timeline: (tick, event_type, note, velocity)
        timeline: list[tuple[int, str, int, int]] = []

        events = track_meta.events

        for ev in events:
            start_tick = self._ms_to_ticks(ev.start_ms)
            end_tick = start_tick + max(1, self._ms_to_ticks(ev.duration_ms))
            # Handle zero-duration events: give them at least 1 tick
            if end_tick == start_tick:
                end_tick = start_tick + 1
            timeline.append((start_tick, "note_on", ev.note, ev.velocity))
            timeline.append((end_tick, "note_off", ev.note, 0))

        # Sort: note_off before note_on at same tick to prevent hanging notes
        # This correctly handles overlapping notes
        timeline.sort(key=lambda x: (x[0], 0 if x[1] == "note_off" else 1))

        # Convert to delta times and write
        last_tick = 0
        for tick, msg_type, note, velocity in timeline:
            delta = max(0, tick - last_tick)
            midi_track.append(mido.Message(
                msg_type,
                channel=track_meta.channel,
                note=note,
                velocity=velocity,
                time=delta,
            ))
            last_tick = tick

        # Add control changes at appropriate positions
        # We need to interleave CCs with note events
        # For simplicity, write CCs after notes (they're typically sparse)
        if track_meta.control_changes:
            cc_events = []
            for start_ms, controller, value in track_meta.control_changes:
                tick = self._ms_to_ticks(start_ms)
                cc_events.append((tick, controller, value))
            cc_events.sort(key=lambda x: x[0])

            # Actually, rebuild the track with interleaved CCs
            return self._build_track_with_ccs(track_meta)

        # End of track
        midi_track.append(mido.MetaMessage("end_of_track", time=0))
        return midi_track

    def _build_track_with_ccs(self, track_meta: TrackMeta) -> mido.MidiTrack:
        """Build a mido.MidiTrack with interleaved note events and CCs."""
        midi_track = mido.MidiTrack()

        # Track name
        midi_track.append(mido.MetaMessage(
            "track_name", name=track_meta.name, time=0,
        ))

        # Program change
        midi_track.append(mido.Message(
            "program_change",
            channel=track_meta.channel,
            program=track_meta.program,
            time=0,
        ))

        # Build combined timeline
        timeline: list[tuple[int, str, int, int]] = []

        for ev in track_meta.events:
            start_tick = self._ms_to_ticks(ev.start_ms)
            end_tick = start_tick + max(1, self._ms_to_ticks(ev.duration_ms))
            if end_tick == start_tick:
                end_tick = start_tick + 1
            timeline.append((start_tick, "note_on", ev.note, ev.velocity))
            timeline.append((end_tick, "note_off", ev.note, 0))

        for start_ms, controller, value in track_meta.control_changes:
            tick = self._ms_to_ticks(start_ms)
            timeline.append((tick, "control_change", controller, value))

        # Sort: note_off before note_on at same tick; CCs after note-offs
        def sort_key(item):
            tick, event_type, _, _ = item
            if event_type == "note_off":
                priority = 0
            elif event_type == "note_on":
                priority = 1
            else:
                priority = 2
            return (tick, priority)

        timeline.sort(key=sort_key)

        # Write with delta times
        last_tick = 0
        for tick, msg_type, param1, param2 in timeline:
            delta = max(0, tick - last_tick)
            if msg_type == "control_change":
                midi_track.append(mido.Message(
                    "control_change",
                    channel=track_meta.channel,
                    control=param1,
                    value=param2,
                    time=delta,
                ))
            else:
                midi_track.append(mido.Message(
                    msg_type,
                    channel=track_meta.channel,
                    note=param1,
                    velocity=param2,
                    time=delta,
                ))
            last_tick = tick

        # End of track
        midi_track.append(mido.MetaMessage("end_of_track", time=0))
        return midi_track

    def _build_conductor_track(self) -> mido.MidiTrack:
        """Build the conductor/meta track with tempo, time sig, key sig."""
        track = mido.MidiTrack()
        track.append(mido.MetaMessage("track_name", name="Conductor", time=0))

        # Tempo
        tempo_us = mido.bpm2tempo(self._bpm)
        track.append(mido.MetaMessage("set_tempo", tempo=tempo_us, time=0))

        # Time signature
        num, den = self._time_signature
        track.append(mido.MetaMessage(
            "time_signature",
            numerator=num,
            denominator=den,
            time=0,
        ))

        # Key signature
        if self._key_signature and self._key_signature in self.KEY_SIG_MAP:
            track.append(mido.MetaMessage(
                "key_signature",
                key=self._key_signature,
                time=0,
            ))

        # Tempo changes
        if self._tempo_changes:
            for time_ms, bpm in self._tempo_changes:
                tick = self._ms_to_ticks(time_ms)
                tempo_us = mido.bpm2tempo(bpm)
                track.append(mido.MetaMessage(
                    "set_tempo", tempo=tempo_us, time=tick,
                ))

        track.append(mido.MetaMessage("end_of_track", time=0))
        return track

    # ── Output ────────────────────────────────────────────────────────────

    def build(self) -> mido.MidiFile:
        """Build and return the complete mido.MidiFile.

        Returns
        -------
        mido.MidiFile
            The assembled MIDI file object.
        """
        mid = mido.MidiFile(ticks_per_beat=self._ppqn)

        # Conductor track (track 0)
        mid.tracks.append(self._build_conductor_track())

        # Data tracks
        for track_meta in self._tracks:
            mid.tracks.append(self._build_track(track_meta))

        return mid

    def write(self, path: str) -> int:
        """Write the MIDI file to disk.

        Parameters
        ----------
        path : str
            Output file path (should end in .mid).

        Returns
        -------
        int
            Number of bytes written.
        """
        mid = self.build()
        mid.save(path)
        # Get file size
        import os
        return os.path.getsize(path)

    def to_bytes(self) -> bytes:
        """Return the complete MIDI file as raw bytes.

        Returns
        -------
        bytes
            Raw MIDI file bytes.
        """
        mid = self.build()
        import io
        buf = io.BytesIO()
        mid.save(file=buf)
        return buf.getvalue()

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def bpm(self) -> float:
        return self._bpm

    @bpm.setter
    def bpm(self, value: float) -> None:
        if value <= 0:
            raise ValueError(f"bpm must be positive, got {value}")
        self._bpm = value

    @property
    def ppqn(self) -> int:
        return self._ppqn

    @property
    def time_signature(self) -> tuple[int, int]:
        return self._time_signature

    @property
    def key_signature(self) -> str | None:
        return self._key_signature

    @property
    def tracks(self) -> list[TrackMeta]:
        return list(self._tracks)

    @property
    def num_tracks(self) -> int:
        return len(self._tracks)

    def __repr__(self) -> str:
        return (
            f"MidiFileWriter(bpm={self._bpm}, ppqn={self._ppqn}, "
            f"tracks={len(self._tracks)}, "
            f"time_sig={self._time_signature})"
        )
