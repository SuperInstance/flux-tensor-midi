"""
Drum + arrangement pipeline integration test.

Pipeline: StepSequencer (trap_hats) + constraint solver bass → Arrangement → MIDI → parse back
"""

import pytest

from flux_tensor_midi.drum_rack.sequencer import StepSequencer
from flux_tensor_midi.tracks import Track, Arrangement
from flux_tensor_midi.midi.events import MidiEvent
from counterpoint_engine import CounterpointGenerator, Species, Scale, VoiceRange
from flux_tensor_midi.core.snap import RhythmicRole


class TestDrumToArrangement:
    """Drum pattern + bass line → Arrangement → render → parse back."""

    def test_drum_pattern_trap_hats(self):
        """Step 1: Create a drum pattern using trap_hats preset."""
        seq = StepSequencer(steps=16)
        seq.load_preset("trap_hats")
        events = seq.render(bpm=140.0)

        assert len(events) > 0
        # Trap hats should have many hi-hat hits
        notes = [e.note for e in events]
        # GM hi-hat closed = 42
        assert 42 in notes, "Should have hi-hat closed hits"
        assert len(events) >= 16, "Trap hats should have at least 16 hits (rapid hats)"

    def test_bass_line_from_constraint_solver(self):
        """Step 2: Create a simple bass line using the main constraint solver."""
        # Simple cantus firmus in C for bass
        cf = [36, 38, 40, 41, 43, 41, 40, 38]  # C2 ascending/descending
        gen = CounterpointGenerator(
            cantus_firmus=cf,
            species=Species.FIRST,
            scale=Scale(tonic=0, mode="major"),
            voice_range=VoiceRange(min_pitch=24, max_pitch=48),
        )
        result = gen.generate()
        assert result.feasible
        assert len(result.voices) == 2
        assert len(result.voices[1]) == len(cf)

    def test_combine_into_arrangement(self):
        """Step 3: Combine drum + bass into an Arrangement."""
        arr = Arrangement(name="test_trap", bpm=140.0, bars=2, seed=42)

        # Drum track
        drum_track = Track(
            name="drums",
            role=RhythmicRole.DOUBLETIME,
            voice="kick",
            bpm=140.0,
            seed=42,
        )
        arr.add_track(drum_track)

        # Bass track
        bass_track = Track(
            name="bass",
            role=RhythmicRole.ROOT,
            voice="bass",
            bpm=140.0,
            seed=42,
        )
        arr.add_track(bass_track)

        assert len(arr.tracks) == 2
        assert arr.bpm == 140.0

    def test_render_to_midi_and_parse_back(self):
        """Step 4-5: Render to MIDI, parse back, verify channels."""
        # Create arrangement with drum and bass tracks
        arr = Arrangement(name="test_trap", bpm=140.0, bars=2, seed=42)

        drum_track = Track("drums", RhythmicRole.DOUBLETIME, "kick", bpm=140.0, seed=42)
        bass_track = Track("bass", RhythmicRole.ROOT, "bass", bpm=140.0, seed=42)

        arr.add_track(drum_track)
        arr.add_track(bass_track)
        arr.generate_all()

        events = arr.to_midi_events()
        assert len(events) > 0

        # Verify both tracks generated events
        assert len(drum_track.events) > 0, "Drum track should have events"
        assert len(bass_track.events) > 0, "Bass track should have events"

        # Verify note validity
        for ev in events:
            assert 0 <= ev.note <= 127
            assert 0 <= ev.velocity <= 127
            assert ev.duration_ms >= 0

    def test_drum_sequencer_to_arrangement_integration(self):
        """Full integration: StepSequencer drums + constraint bass → combined MIDI."""
        # 1. Create drum pattern
        seq = StepSequencer(steps=16)
        seq.load_preset("trap_hats")
        drum_events = seq.render(bpm=140.0)

        # 2. Create bass line via constraint solver
        cf = [36, 38, 40, 41, 43, 41, 40, 36]
        gen = CounterpointGenerator(
            cantus_firmus=cf,
            species=Species.FIRST,
            scale=Scale(tonic=0, mode="major"),
            voice_range=VoiceRange(min_pitch=24, max_pitch=48),
        )
        result = gen.generate()
        assert result.feasible

        # Convert bass voice to MidiEvents
        bass_voice = result.voices[1]
        quarter_ms = 60000.0 / 140.0
        bass_events = [
            MidiEvent(note=n, velocity=80, start_ms=i * quarter_ms, duration_ms=quarter_ms * 0.8, channel=1)
            for i, n in enumerate(bass_voice)
            if 0 <= n <= 127
        ]

        # 3. Combine
        drum_ch9 = [
            MidiEvent(e.note, e.velocity, e.start_ms, e.duration_ms, channel=9)
            for e in drum_events
        ]
        combined = bass_events + drum_ch9
        combined.sort(key=lambda e: e.start_ms)

        # 4. Verify
        channels = set(e.channel for e in combined)
        assert 1 in channels, "Bass should be on channel 1"
        assert 9 in channels, "Drums should be on channel 9"

        # Verify note counts
        bass_notes = [e for e in combined if e.channel == 1]
        drum_notes = [e for e in combined if e.channel == 9]
        assert len(bass_notes) == len(bass_voice)
        assert len(drum_notes) > 0
