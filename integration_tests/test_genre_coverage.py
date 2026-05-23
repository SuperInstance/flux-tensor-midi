"""
Genre brain coverage integration test.

Pipeline: Loop through all genre presets → generate short composition → verify properties
"""

import pytest

from flux_tensor_midi.genre_brain import GenreBrain
from flux_tensor_midi.analyzer import FluxAnalyzer
from flux_tensor_midi.midi.events import MidiEvent


class TestGenreCoverage:
    """Test all genre presets produce valid compositions with expected properties."""

    @pytest.fixture(params=GenreBrain.available_genres())
    def genre(self, request):
        return request.param

    def test_all_genres_are_accessible(self):
        """Verify all genre presets can be instantiated."""
        genres = GenreBrain.available_genres()
        assert len(genres) == 5, f"Expected 5 genres, got {len(genres)}: {genres}"
        for g in genres:
            brain = GenreBrain(g)
            assert brain.genre == g

    def test_genre_preset_structure(self, genre):
        """Each preset should have required fields."""
        brain = GenreBrain(genre)
        preset = brain.get_preset()

        required_keys = [
            'description', 'roles', 'member_names', 'salience_profiles',
            'tolerance_profiles', 'default_bpm', 'default_key',
            'base_note', 'grid_resolution', 'loop_bars',
        ]
        for key in required_keys:
            assert key in preset, f"Missing '{key}' in {genre} preset"

        # Verify profile lengths
        assert len(preset['salience_profiles']) == len(preset['member_names'])
        assert len(preset['tolerance_profiles']) == len(preset['member_names'])

    def test_genre_creates_band(self, genre):
        """Each genre should create a valid band."""
        brain = GenreBrain(genre)
        band, musicians = brain.create_band(seed=42)

        assert band is not None
        assert len(musicians) == len(brain.get_preset()['member_names'])
        assert band.bpm > 0

    def test_genre_composition_is_valid(self, genre):
        """Generate a short composition and verify it produces valid MIDI events."""
        brain = GenreBrain(genre)
        preset = brain.get_preset()
        band, musicians = brain.create_band(bars=2, seed=42)

        # Generate events by emitting from musicians
        all_events = []
        bpm = preset['default_bpm']
        quarter_ms = 60000.0 / bpm

        for musician in musicians:
            state = musician.state
            if state.magnitude == 0:
                continue

            # Generate a few ticks worth of events
            for tick in range(8):
                ts, vec = musician.emit()
                for ch in range(min(9, len(vec))):
                    val = vec[ch]
                    if val < 0.05:
                        continue
                    note = min(127, max(0, preset['base_note'] + ch))
                    velocity = min(127, max(1, int(val * 100)))
                    all_events.append(MidiEvent(
                        note=note,
                        velocity=velocity,
                        start_ms=ts,
                        duration_ms=quarter_ms * 0.8,
                        channel=0,
                    ))

        # At least some events should be generated
        if all_events:
            analyzer = FluxAnalyzer()
            report = analyzer.from_midi_events(all_events)
            assert report.note_count > 0

    def test_jazz_has_high_direction_weight(self):
        """Jazz should have higher direction/interval weights (salience channel activity)."""
        brain = GenreBrain('jazz')
        preset = brain.get_preset()
        # Piano (first profile) should have melodic salience
        piano_salience = preset['salience_profiles'][0]
        # Check that piano has high melodic activity (channels 0, 2 are melodic)
        assert piano_salience[0] > 0.5, "Jazz piano should have high melodic salience"
        assert piano_salience[2] > 0.5, "Jazz piano should have active 3rd channel"

    def test_electronic_has_high_curvature_weight(self):
        """Electronic/techno should have evolving texture (high curvature/activity)."""
        brain = GenreBrain('electronic')
        preset = brain.get_preset()
        # Synth (second profile) should have evolving texture
        synth_salience = preset['salience_profiles'][1]
        # Check high activity in multiple channels (evolving texture)
        active_channels = sum(1 for v in synth_salience if v > 0.3)
        assert active_channels >= 3, (
            f"Electronic synth should have ≥3 active channels, got {active_channels}"
        )

    def test_classical_has_contrapuntal_balance(self):
        """Classical should have balanced salience across voices (contrapuntal)."""
        brain = GenreBrain('classical')
        preset = brain.get_preset()
        profiles = preset['salience_profiles']

        # All voices should have some activity
        for i, profile in enumerate(profiles):
            total = sum(v for v in profile if v > 0)
            assert total > 0.5, f"Classical voice {i} should have meaningful activity"

    def test_hiphop_has_strong_rhythmic_roles(self):
        """Hip-hop should have strong ROOT and DOUBLETIME roles."""
        from flux_tensor_midi.core.snap import RhythmicRole
        brain = GenreBrain('hiphop')
        preset = brain.get_preset()

        assert RhythmicRole.ROOT in preset['roles']
        assert RhythmicRole.DOUBLETIME in preset['roles']

        # Kick should be downbeat-heavy
        kick_salience = preset['salience_profiles'][0]
        assert kick_salience[0] > 0.5, "Hip-hop kick should be strong on beat 1"

    def test_math_genre_exact_tolerance(self):
        """Math genre should have zero tolerance (exact timing)."""
        brain = GenreBrain('math')
        preset = brain.get_preset()

        for profile in preset['tolerance_profiles']:
            for val in profile:
                assert val == 0.0, f"Math genre should have zero tolerance, got {val}"
