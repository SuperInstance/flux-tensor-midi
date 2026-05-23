"""
JamSession: Orchestrates two AI agents trading phrases over shared harmony.

A turn-based jam where agents alternate, each responding to the other's
output while respecting a consensus constraint (chord tones at boundaries).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.ai_jam.agent import AIAgent, AgentPersonality


# Default progression: D Dorian jam
DEFAULT_PROGRESSION = [
    ("Dm7", 4),
    ("Gm7", 4),
    ("Am7", 4),
    ("Dm7", 4),
]


@dataclass
class JamSession:
    """A jam session between two AI agents.

    Parameters
    ----------
    agent1 : AIAgent
        First musician (opens the session).
    agent2 : AIAgent
        Second musician (responds).
    bpm : float
        Tempo in beats per minute.
    total_bars : int
        Total session length in bars.
    progression : list[tuple[str, int]]
        Chord progression: list of (chord_name, bars) tuples.
    phrase_bars : int
        How many bars each agent plays per turn (2-4).
    """

    agent1: AIAgent
    agent2: AIAgent
    bpm: float = 140.0
    total_bars: int = 32
    progression: list[tuple[str, int]] = field(default_factory=lambda: list(DEFAULT_PROGRESSION))
    phrase_bars: int = 4

    def run(self) -> list[MidiEvent]:
        """Run the jam session and return all events.

        Returns
        -------
        list[MidiEvent]
            All MIDI events from both agents, with correct timing.
        """
        all_events: list[MidiEvent] = []
        bar_ms = (60_000.0 / self.bpm) * 4

        # Calculate total progression duration
        prog_bars = sum(bars for _, bars in self.progression)
        # Repeat progression to fill total_bars
        repeats_needed = max(1, (self.total_bars + prog_bars - 1) // prog_bars)
        full_progression = self.progression * repeats_needed

        # Build harmony context
        harmony_context = {"chord_progression": full_progression}

        # Determine how many turns each agent gets
        # Agents alternate: agent1 plays phrase_bars, agent2 responds phrase_bars
        turn_bars = self.phrase_bars * 2
        num_turns = max(1, self.total_bars // turn_bars)

        last_agent1_output: list[MidiEvent] = []
        last_agent2_output: list[MidiEvent] = []
        time_offset = 0.0

        for turn in range(num_turns):
            # Sub-progressions for this turn's phrases
            start_bar = turn * turn_bars
            a1_start_bar = start_bar
            a2_start_bar = start_bar + self.phrase_bars

            # Agent 1 plays
            a1_context = self._sub_context(full_progression, a1_start_bar, self.phrase_bars, bar_ms)
            a1_events = self.agent1.respond(
                other_output=last_agent2_output,
                harmony_context=a1_context,
                bars=self.phrase_bars,
                bpm=self.bpm,
            )
            # Offset timing
            for ev in a1_events:
                all_events.append(MidiEvent(
                    note=ev.note,
                    velocity=ev.velocity,
                    start_ms=ev.start_ms + time_offset,
                    duration_ms=ev.duration_ms,
                    channel=ev.channel,
                ))
            last_agent1_output = a1_events

            # Agent 2 responds
            a2_offset = time_offset + self.phrase_bars * bar_ms
            a2_context = self._sub_context(full_progression, a2_start_bar, self.phrase_bars, bar_ms)
            a2_events = self.agent2.respond(
                other_output=last_agent1_output,
                harmony_context=a2_context,
                bars=self.phrase_bars,
                bpm=self.bpm,
            )
            for ev in a2_events:
                all_events.append(MidiEvent(
                    note=ev.note,
                    velocity=ev.velocity,
                    start_ms=ev.start_ms + a2_offset,
                    duration_ms=ev.duration_ms,
                    channel=ev.channel,
                ))
            last_agent2_output = a2_events

            time_offset += turn_bars * bar_ms

        # Handle remaining bars if total_bars isn't evenly divisible
        remaining = self.total_bars - num_turns * turn_bars
        if remaining > 0:
            extra_start_bar = num_turns * turn_bars
            a1_bars = min(remaining, self.phrase_bars)
            a1_context = self._sub_context(full_progression, extra_start_bar, a1_bars, bar_ms)
            a1_events = self.agent1.respond(
                other_output=last_agent2_output,
                harmony_context=a1_context,
                bars=a1_bars,
                bpm=self.bpm,
            )
            for ev in a1_events:
                all_events.append(MidiEvent(
                    note=ev.note,
                    velocity=ev.velocity,
                    start_ms=ev.start_ms + time_offset,
                    duration_ms=ev.duration_ms,
                    channel=ev.channel,
                ))

            if remaining > self.phrase_bars:
                a2_bars = remaining - self.phrase_bars
                a2_offset = time_offset + a1_bars * bar_ms
                a2_context = self._sub_context(
                    full_progression, extra_start_bar + a1_bars, a2_bars, bar_ms
                )
                a2_events = self.agent2.respond(
                    other_output=a1_events,
                    harmony_context=a2_context,
                    bars=a2_bars,
                    bpm=self.bpm,
                )
                for ev in a2_events:
                    all_events.append(MidiEvent(
                        note=ev.note,
                        velocity=ev.velocity,
                        start_ms=ev.start_ms + a2_offset,
                        duration_ms=ev.duration_ms,
                        channel=ev.channel,
                    ))

        return sorted(all_events, key=lambda e: e.start_ms)

    def to_midi_file(self, output_path: str) -> str:
        """Run the jam and write a multi-track MIDI file.

        Each agent gets its own track with its GM program.

        Returns the output path.
        """
        import mido

        events = self.run()
        bar_ms = (60_000.0 / self.bpm) * 4

        mid = mido.MidiFile(ticks_per_beat=480)
        tick_scale = 480.0 / (bar_ms / 4)  # ticks per ms

        # Create tracks for each agent
        track1 = mido.MidiTrack()
        track2 = mido.MidiTrack()

        # Tempo meta event
        tempo = mido.bpm2tempo(self.bpm)
        for track in [track1, track2]:
            track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
            track.append(mido.MetaMessage(
                "track_name",
                name=self.agent1.personality.name if track is track1 else self.agent2.personality.name,
                time=0,
            ))

        # Program change
        track1.append(mido.Message(
            "program_change",
            program=self.agent1.personality.midi_program,
            channel=self.agent1.personality.midi_channel,
            time=0,
        ))
        track2.append(mido.Message(
            "program_change",
            program=self.agent2.personality.midi_program,
            channel=self.agent2.personality.midi_channel,
            time=0,
        ))

        # Sort events by agent
        ch1 = self.agent1.personality.midi_channel
        ch2 = self.agent2.personality.midi_channel

        track1_events = sorted(
            [e for e in events if e.channel == ch1],
            key=lambda e: e.start_ms,
        )
        track2_events = sorted(
            [e for e in events if e.channel == ch2],
            key=lambda e: e.start_ms,
        )

        self._write_events_to_track(track1, track1_events, tick_scale, ch1)
        self._write_events_to_track(track2, track2_events, tick_scale, ch2)

        mid.tracks.append(track1)
        mid.tracks.append(track2)
        mid.save(output_path)
        return output_path

    @staticmethod
    def _write_events_to_track(
        track: "mido.MidiTrack",
        events: list[MidiEvent],
        tick_scale: float,
        channel: int,
    ) -> None:
        """Write MidiEvents as note_on/note_off pairs with delta times."""
        import mido

        # Build a timeline of (tick, type, note, velocity)
        timeline: list[tuple[int, str, int, int]] = []
        for ev in events:
            start_tick = max(0, int(ev.start_ms * tick_scale))
            end_tick = start_tick + max(1, int(ev.duration_ms * tick_scale))
            timeline.append((start_tick, "note_on", ev.note, ev.velocity))
            timeline.append((end_tick, "note_off", ev.note, 0))

        timeline.sort(key=lambda x: (x[0], 0 if x[1] == "note_off" else 1))

        last_tick = 0
        for tick, msg_type, note, velocity in timeline:
            delta = max(0, tick - last_tick)
            track.append(mido.Message(
                msg_type,
                channel=channel,
                note=note,
                velocity=velocity,
                time=delta,
            ))
            last_tick = tick

    @staticmethod
    def _sub_context(
        full_progression: list[tuple[str, int]],
        start_bar: int,
        bars: int,
        bar_ms: float,
    ) -> dict:
        """Extract the chord sub-progression for a phrase."""
        # Walk through the progression to find the chords for start_bar..start_bar+bars
        accumulated = 0
        sub_prog: list[tuple[str, int]] = []
        for chord_name, chord_bars in full_progression:
            chord_end = accumulated + chord_bars
            # Does this chord overlap with our range?
            phrase_start = start_bar
            phrase_end = start_bar + bars
            if chord_end > phrase_start and accumulated < phrase_end:
                overlap_start = max(accumulated, phrase_start)
                overlap_end = min(chord_end, phrase_end)
                overlap_bars = overlap_end - overlap_start
                if overlap_bars > 0:
                    sub_prog.append((chord_name, overlap_bars))
            accumulated = chord_end
            if accumulated >= start_bar + bars:
                break

        if not sub_prog:
            sub_prog = [("Dm7", bars)]

        return {"chord_progression": sub_prog}
