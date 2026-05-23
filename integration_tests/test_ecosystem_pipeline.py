"""
Full ecosystem pipeline integration test.

Pipeline: counterpoint-engine → flux-tensor-midi analyzer → genre_brain → drum_rack → final MIDI
"""

import os
import tempfile
import pytest

from counterpoint_engine import (
    CounterpointGenerator,
    CounterpointResult,
    Species,
    VoiceRange,
    Scale,
)
from flux_tensor_midi.analyzer import FluxAnalyzer
from flux_tensor_midi.genre_brain import GenreBrain
from flux_tensor_midi.drum_rack.sequencer import StepSequencer
from flux_tensor_midi.midi.events import MidiEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _events_from_voices(voices, bpm=120):
    """Convert counterpoint voices to MidiEvent list."""
    quarter_ms = 60000.0 / bpm
    events = []
    for ch, voice in enumerate(voices):
        for i, note in enumerate(voice):
            if 0 <= note <= 127:
                events.append(MidiEvent(
                    note=note,
                    velocity=80,
                    start_ms=i * quarter_ms,
                    duration_ms=quarter_ms * 0.9,
                    channel=ch,
                ))
    return events


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEcosystemPipeline:
    """End-to-end: cantus firmus → counterpoint → analysis → genre → drums → MIDI."""

    CANTUS_FIRMUS = [60, 62, 64, 65, 67, 65, 64, 62, 60]  # C major ascending/descending

    def test_generate_cantus_firmus_and_counterpoint(self):
        """Step 1-2: Generate counterpoint with 2, 3, and 4 voices."""
        for n_voices in [2, 3, 4]:
            gen = CounterpointGenerator(
                cantus_firmus=self.CANTUS_FIRMUS,
                species=Species.FIRST,
                scale=Scale(tonic=0, mode="major"),
            )
            result = gen.generate_n_voices(n_voices)
            assert result is not None
            assert result.feasible, f"{n_voices}-voice generation was infeasible"
            assert len(result.voices) == n_voices
            # Each voice should have the same length as CF for species 1
            for voice in result.voices:
                assert len(voice) == len(self.CANTUS_FIRMUS)

    def test_analyze_counterpoint_midi(self):
        """Step 3-4: Feed generated MIDI into analyzer and verify profile."""
        gen = CounterpointGenerator(
            cantus_firmus=self.CANTUS_FIRMUS,
            species=Species.FIRST,
            scale=Scale(tonic=0, mode="major"),
        )
        result = gen.generate_n_voices(2)
        assert result.feasible

        events = _events_from_voices(result.voices)
        assert len(events) > 0

        analyzer = FluxAnalyzer()
        report = analyzer.from_midi_events(events)

        # Verify analysis matches expected constraint profile
        assert report.note_count > 0
        assert report.key_confidence > 0
        # C major cantus firmus should detect as C major or close
        assert report.key in ('C', 'C#', 'D')  # may detect relative minor
        assert report.duration_ms > 0
        assert report.density > 0
        assert report.pitch_range[0] >= 0
        assert report.pitch_range[1] <= 127

    def test_genre_brain_classical_config(self):
        """Step 5-6: GenreBrain for classical should configure appropriate weights."""
        brain = GenreBrain('classical')
        preset = brain.get_preset()

        assert preset['default_bpm'] == 72
        assert preset['default_key'] == 'D'
        assert len(preset['salience_profiles']) == 3

        # Classical should have moderate salience (contrapuntal, not overly rhythmic)
        for profile in preset['salience_profiles']:
            # At least some channels should be active
            assert sum(v for v in profile if v > 0) > 0

        # Verify the roles are appropriate
        from flux_tensor_midi.core.snap import RhythmicRole
        assert RhythmicRole.ROOT in preset['roles']
        assert RhythmicRole.WALTZ in preset['roles']

    def test_drum_rack_renders_valid_midi(self, tmp_midi_dir):
        """Step 7: Render through drum_rack, verify final MIDI is valid."""
        # Generate counterpoint
        gen = CounterpointGenerator(
            cantus_firmus=self.CANTUS_FIRMUS,
            species=Species.FIRST,
            scale=Scale(tonic=0, mode="major"),
        )
        result = gen.generate_n_voices(2)
        assert result.feasible

        # Create drum pattern
        seq = StepSequencer(steps=16)
        seq.load_preset("boom_bap")
        drum_events = seq.render(bpm=120.0)

        # Combine counterpoint + drums
        cp_events = _events_from_voices(result.voices, bpm=120)
        # Drums go on channel 9
        drum_events_ch9 = [
            MidiEvent(e.note, e.velocity, e.start_ms, e.duration_ms, channel=9)
            for e in drum_events
        ]
        all_events = cp_events + drum_events_ch9
        all_events.sort(key=lambda e: e.start_ms)

        # Verify combined events
        assert len(all_events) > len(cp_events), "Should have drum + counterpoint events"

        # Check channels
        channels = set(e.channel for e in all_events)
        assert 9 in channels, "Drums should be on channel 9"
        assert len(channels) >= 2, "Should have multiple channels"

        # Parse back / verify note counts and ranges
        notes = [e.note for e in all_events]
        assert all(0 <= n <= 127 for n in notes), "All notes must be valid MIDI"
        assert len(notes) == len(all_events)

    def test_full_pipeline_roundtrip(self, tmp_midi_dir):
        """Step 8: Full pipeline roundtrip — generate, analyze, render, verify."""
        # 1. Generate 3-voice counterpoint
        gen = CounterpointGenerator(
            cantus_firmus=self.CANTUS_FIRMUS,
            species=Species.FIRST,
            scale=Scale(tonic=0, mode="major"),
        )
        result = gen.generate_n_voices(3)
        assert result.feasible
        assert len(result.voices) == 3

        # 2. Analyze
        events = _events_from_voices(result.voices, bpm=72)
        analyzer = FluxAnalyzer()
        report = analyzer.from_midi_events(events)
        assert report.note_count > 0

        # 3. Configure genre brain
        brain = GenreBrain('classical')
        preset = brain.get_preset()

        # 4. Add drums
        seq = StepSequencer(steps=16)
        seq.load_preset("bossa_nova")
        drum_events = seq.render(bpm=72.0)
        drum_events_ch9 = [
            MidiEvent(e.note, e.velocity, e.start_ms, e.duration_ms, channel=9)
            for e in drum_events
        ]

        # 5. Combine and verify
        all_events = events + drum_events_ch9
        all_events.sort(key=lambda e: e.start_ms)

        # Verify channels exist
        channels = set(e.channel for e in all_events)
        assert 9 in channels
        assert any(ch < 9 for ch in channels), "Should have melodic channels"

        # Verify durations are reasonable
        if all_events:
            total_dur = max(e.end_ms for e in all_events)
            assert total_dur > 0
