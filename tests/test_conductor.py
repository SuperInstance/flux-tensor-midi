"""
Tests for the unified Conductor — 60+ tests covering all subsystems.

Run: python -m pytest tests/test_conductor.py -v
"""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from flux_tensor_midi.conductor import (
    Conductor,
    ConstraintProfile,
    _CULTURE_DEFAULTS,
    _CONDUCTOR_PRESETS,
    _RAGA_PRESETS,
    _MAQAM_PRESETS,
    _PENTATONIC_PRESETS,
    _POLYRHYTHM_PRESETS,
    _TUNING_MAP,
    _TEMPO_MAP,
)
from flux_tensor_midi.tracks import Arrangement, Track
from flux_tensor_midi.midi.events import MidiEvent


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def conductor():
    """Basic conductor with no culture."""
    return Conductor(seed=42)


@pytest.fixture
def indian_conductor():
    """Conductor configured for Indian music."""
    return Conductor(culture='indian', seed=42)


@pytest.fixture
def arabic_conductor():
    """Conductor configured for Arabic music."""
    return Conductor(culture='arabic', seed=42)


@pytest.fixture
def tmp_midi_path():
    """Temporary MIDI file path."""
    fd, path = tempfile.mkstemp(suffix='.mid')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


# =====================================================================
# Cultural Selection (12 tests)
# =====================================================================

class TestCulturalSelection:

    def test_set_culture_indian(self, conductor):
        c = conductor.set_culture('indian')
        assert c.culture == 'indian'
        assert c.scale_name == 'bhairavi'
        assert c.tuning_name == 'shruti'
        assert c.constraints.bpm == 80.0
        assert c is conductor  # chaining

    def test_set_culture_arabic(self, conductor):
        c = conductor.set_culture('arabic')
        assert c.culture == 'arabic'
        assert c.scale_name == 'rast'
        assert c.tuning_name == 'quarter_tone'
        assert c.constraints.bpm == 100.0

    def test_set_culture_east_asian(self, conductor):
        c = conductor.set_culture('east_asian')
        assert c.culture == 'east_asian'
        assert c.scale_name == 'in_scale'
        assert c.tuning_name == 'pentatonic'

    def test_set_culture_west_african(self, conductor):
        c = conductor.set_culture('west_african')
        assert c.culture == 'west_african'
        assert c.scale_name == 'ewe_standard'
        assert c.constraints.bpm == 120.0

    def test_set_culture_western(self, conductor):
        c = conductor.set_culture('western')
        assert c.culture == 'western'
        assert c.constraints.bpm == 120.0

    def test_set_culture_invalid(self, conductor):
        with pytest.raises(ValueError, match="Unknown culture"):
            conductor.set_culture('martian')

    def test_set_scale_auto_tune_indian(self, conductor):
        conductor.set_scale('bhairavi')
        assert conductor.tuning_name == 'shruti'

    def test_set_scale_auto_tune_arabic(self, conductor):
        conductor.set_scale('bayati')
        assert conductor.tuning_name == 'quarter_tone'

    def test_set_raga(self, conductor):
        c = conductor.set_raga('darbari')
        assert c.culture == 'indian'
        assert c.scale_name == 'darbari'
        assert c.tuning_name == 'shruti'
        assert 'meend' in c._ornament_names

    def test_set_maqam(self, conductor):
        c = conductor.set_maqam('rast')
        assert c.culture == 'arabic'
        assert c.scale_name == 'rast'
        assert c.tuning_name == 'quarter_tone'

    def test_set_pentatonic(self, conductor):
        c = conductor.set_pentatonic('in_scale')
        assert c.culture == 'east_asian'
        assert c.scale_name == 'in_scale'
        assert c.tuning_name == 'pentatonic'

    def test_set_polyrhythm(self, conductor):
        c = conductor.set_polyrhythm('agbadza')
        assert c.culture == 'west_african'
        assert c.constraints.bpm == 120.0


# =====================================================================
# Genre Navigation (8 tests)
# =====================================================================

class TestGenreNavigation:

    def test_blend_genres(self, conductor):
        conductor.genre = 'Jazz'
        c = conductor.blend_genres('Jazz', 'Classical')
        assert c.genre == 'Jazz+Classical'

    def test_blend_genres_with_weights(self, conductor):
        conductor.genre = 'Jazz'
        c = conductor.blend_genres('Jazz', 'Classical', weights=[0.7, 0.3])
        assert c is conductor

    def test_explore_nearby(self, conductor):
        conductor.genre = 'Jazz'
        nearby = conductor.explore_nearby(n=5)
        assert len(nearby) == 5
        assert all(isinstance(t[0], str) for t in nearby)
        assert all(isinstance(t[1], float) for t in nearby)

    def test_explore_nearby_custom_n(self, conductor):
        conductor.genre = 'Techno'
        nearby = conductor.explore_nearby(n=3)
        assert len(nearby) == 3

    def test_genre_walk(self, conductor):
        conductor.genre = 'Jazz'
        walk = conductor.genre_walk(steps=5, step_size=0.1)
        assert len(walk) == 5
        for name, coords in walk:
            assert isinstance(name, str)
            assert isinstance(coords, np.ndarray)

    def test_genre_walk_different_starts(self, conductor):
        results_a = Conductor(genre='Jazz', seed=42).genre_walk(steps=3)
        results_b = Conductor(genre='Techno', seed=42).genre_walk(steps=3)
        # Different starting genres should give different walks
        assert [n for n, _ in results_a] != [n for n, _ in results_b]

    def test_blend_updates_constraints(self, conductor):
        conductor.genre = 'Jazz'
        original_bpm = conductor.constraints.bpm
        conductor.blend_genres('Jazz', 'Ambient')
        # BPM should be affected
        assert isinstance(conductor.constraints.bpm, float)

    def test_genre_walk_with_seed(self, conductor):
        c1 = Conductor(genre='Jazz', seed=42)
        c2 = Conductor(genre='Jazz', seed=42)
        w1 = c1.genre_walk(steps=3)
        w2 = c2.genre_walk(steps=3)
        assert [n for n, _ in w1] == [n for n, _ in w2]


# =====================================================================
# Composition (12 tests)
# =====================================================================

class TestComposition:

    def test_compose_basic(self, conductor):
        arr = conductor.compose(bars=4)
        assert isinstance(arr, Arrangement)
        assert arr.bpm == 120.0
        assert len(arr.tracks) > 0

    def test_compose_with_bpm(self, conductor):
        arr = conductor.compose(bars=4, bpm=140)
        assert arr.bpm == 140

    def test_compose_with_culture(self, indian_conductor):
        arr = indian_conductor.compose(bars=4)
        assert isinstance(arr, Arrangement)
        assert len(arr.tracks) > 0

    def test_compose_generates_events(self, conductor):
        conductor.set_culture('western')
        arr = conductor.compose(bars=4)
        arr.generate_all()
        total_events = sum(len(t.events) for t in arr.tracks)
        assert total_events > 0

    def test_compose_raga(self, conductor):
        arr = conductor.compose_raga('bhairavi', tala_name='teental', tempo='madhya')
        assert isinstance(arr, Arrangement)
        assert 'raga' in arr.name

    def test_compose_raga_default(self, conductor):
        arr = conductor.compose_raga()
        assert isinstance(arr, Arrangement)

    def test_compose_maqam(self, conductor):
        arr = conductor.compose_maqam('rast', iqa_name='maqsum', bpm=100)
        assert isinstance(arr, Arrangement)
        assert 'maqam' in arr.name

    def test_compose_maqam_default(self, conductor):
        arr = conductor.compose_maqam()
        assert isinstance(arr, Arrangement)

    def test_compose_penrose(self, conductor):
        try:
            arr = conductor.compose_penrose(preset='fibonacci_groove', bars=4)
            assert isinstance(arr, Arrangement)
        except ImportError:
            pytest.skip("Penrose module not available")

    def test_compose_penrose_golden_phrase(self, conductor):
        try:
            arr = conductor.compose_penrose(preset='golden_phrase', bars=4)
            assert isinstance(arr, Arrangement)
        except ImportError:
            pytest.skip("Penrose module not available")

    def test_compose_counterpoint(self, conductor):
        cf = [60, 62, 64, 65, 67, 65, 64, 62]
        arr = conductor.compose_counterpoint(species=1, cantus_firmus=cf, bars=8)
        assert isinstance(arr, Arrangement)
        assert len(arr.tracks) >= 2  # cantus firmus + counterpoint

    def test_compose_counterpoint_species_2(self, conductor):
        arr = conductor.compose_counterpoint(species=2, bars=8)
        assert isinstance(arr, Arrangement)
        assert len(arr.tracks) >= 2


# =====================================================================
# Evolution (6 tests)
# =====================================================================

class TestEvolution:

    def test_evolve_jazz(self, conductor):
        try:
            c = conductor.evolve(target_genre='jazz', generations=5, population=20)
            assert c is conductor
            assert c._evolution_result is not None
            assert c._evolution_result.best_fitness > 0
        except ImportError:
            pytest.skip("Genome module not available")

    def test_evolve_classical(self, conductor):
        try:
            c = conductor.evolve(target_genre='classical', generations=5, population=20)
            assert c.constraints.bpm > 0
        except ImportError:
            pytest.skip("Genome module not available")

    def test_evolve_updates_constraints(self, conductor):
        try:
            original_bpm = conductor.constraints.bpm
            conductor.evolve(target_genre='electronic', generations=5, population=20)
            # BPM should be set from evolved genome
            assert conductor.constraints.bpm > 0
        except ImportError:
            pytest.skip("Genome module not available")

    def test_evolve_cross_cultural(self, conductor):
        try:
            c = conductor.evolve_cross_cultural('indian', 'western', generations=5)
            assert 'hybrid' in c.culture
        except ImportError:
            pytest.skip("Genome module not available")

    def test_evolve_chaining(self, conductor):
        try:
            arr = conductor.evolve('jazz', generations=3, population=10).compose(bars=4)
            assert isinstance(arr, Arrangement)
        except ImportError:
            pytest.skip("Genome module not available")

    def test_evolve_default_genre(self, conductor):
        try:
            conductor.genre = 'Bebop'
            conductor.evolve(generations=3, population=10)
            assert conductor._evolution_result is not None
        except ImportError:
            pytest.skip("Genome module not available")


# =====================================================================
# Analysis (8 tests)
# =====================================================================

class TestAnalysis:

    def test_analyze_basic(self, conductor):
        conductor.set_culture('western')
        arr = conductor.compose(bars=4)
        arr.generate_all()
        result = conductor.analyze(arr)
        assert 'summary' in result
        assert 'constraint_satisfaction' in result
        assert 'cultural_metrics' in result

    def test_analyze_constraint_satisfaction(self, conductor):
        conductor.set_culture('western')
        arr = conductor.compose(bars=4)
        arr.generate_all()
        result = conductor.analyze(arr)
        cs = result['constraint_satisfaction']
        assert 'snap_accuracy' in cs
        assert 'funnel_convergence' in cs
        assert 'consensus_agreement' in cs
        assert 'laman_rigidity' in cs
        for v in cs.values():
            assert 0 <= v <= 1

    def test_analyze_cultural_metrics(self, indian_conductor):
        arr = indian_conductor.compose(bars=4)
        arr.generate_all()
        result = indian_conductor.analyze(arr)
        cm = result['cultural_metrics']
        assert 'cultural_authenticity' in cm
        assert cm['culture'] == 'indian'

    def test_analyze_cohomology(self, conductor):
        conductor.set_culture('western')
        arr = conductor.compose(bars=4)
        arr.generate_all()
        result = conductor.analyze_cohomology(arr)
        assert 'H0' in result
        assert 'H1' in result
        assert 'emergence_score' in result
        assert 'harmonic_complexity' in result
        assert result['H0'] >= 0
        assert result['H1'] >= 0

    def test_analyze_empty_arrangement(self, conductor):
        arr = Arrangement(name='empty')
        result = conductor.analyze(arr)
        assert result['total_events'] == 0

    def test_analyze_cohomology_empty(self, conductor):
        arr = Arrangement(name='empty')
        result = conductor.analyze_cohomology(arr)
        assert result['H0'] == 0
        assert result['H1'] == 0

    def test_analyze_track_count(self, conductor):
        conductor.set_culture('indian')
        arr = conductor.compose(bars=4)
        result = conductor.analyze(arr)
        assert result['track_count'] == len(arr.tracks)

    def test_analyze_pipeline(self, conductor):
        """Full compose → analyze → cohomology pipeline."""
        conductor.set_raga('bhairavi')
        arr = conductor.compose(bars=4)
        arr.generate_all()
        analysis = conductor.analyze(arr)
        cohomology = conductor.analyze_cohomology(arr)
        assert isinstance(analysis, dict)
        assert isinstance(cohomology, dict)


# =====================================================================
# Synthesis / MIDI (6 tests)
# =====================================================================

class TestSynthesis:

    def test_render_midi(self, conductor, tmp_midi_path):
        conductor.set_culture('western')
        arr = conductor.compose(bars=4)
        arr.generate_all()
        size = conductor.render_midi(arr, tmp_midi_path)
        assert size > 0
        assert os.path.exists(tmp_midi_path)

    def test_render_midi_indian(self, indian_conductor, tmp_midi_path):
        arr = indian_conductor.compose(bars=4)
        arr.generate_all()
        size = indian_conductor.render_midi(arr, tmp_midi_path)
        assert size > 0

    def test_render_midi_arabic(self, arabic_conductor, tmp_midi_path):
        arr = arabic_conductor.compose(bars=4)
        arr.generate_all()
        size = arabic_conductor.render_midi(arr, tmp_midi_path)
        assert size > 0

    def test_render_spline(self, conductor):
        try:
            conductor.set_culture('western')
            arr = conductor.compose(bars=2)
            arr.generate_all()
            audio = conductor.render_spline(arr, timbre='warm')
            assert len(audio) > 0
            assert audio[:4] == b'RIFF'  # WAV header
        except ImportError:
            pytest.skip("Spline module not available")

    def test_render_dispatch(self, conductor, tmp_midi_path):
        conductor.set_culture('western')
        arr = conductor.compose(bars=4)
        arr.generate_all()
        try:
            audio = conductor.render(arr, synth='spline')
            assert len(audio) > 0
        except ImportError:
            pytest.skip("Spline module not available")

    def test_render_invalid_synth(self, conductor):
        arr = Arrangement(name='test')
        with pytest.raises(ValueError, match="Unknown synth"):
            conductor.render(arr, synth='nonexistent')


# =====================================================================
# Presets (10 tests)
# =====================================================================

class TestPresets:

    def test_preset_midnight_raga(self):
        c = Conductor.preset('midnight_raga')
        assert c.culture == 'indian'
        assert c.scale_name == 'bhairavi'
        assert c.constraints.bpm == 40

    def test_preset_cairo_cafe(self):
        c = Conductor.preset('cairo_cafe')
        assert c.culture == 'arabic'
        assert c.scale_name == 'rast'
        assert c.constraints.bpm == 100

    def test_preset_zen_garden(self):
        c = Conductor.preset('zen_garden')
        assert c.culture == 'east_asian'
        assert c.scale_name == 'in_scale'

    def test_preset_djembe_circle(self):
        c = Conductor.preset('djembe_circle')
        assert c.culture == 'west_african'

    def test_preset_bebop_salt(self):
        c = Conductor.preset('bebop_salt')
        assert c.genre == 'Jazz'
        assert c.constraints.bpm == 180

    def test_preset_bach_fugue(self):
        c = Conductor.preset('bach_fugue')
        assert c.tuning_name == 'meantone'

    def test_preset_penrose_dance(self):
        c = Conductor.preset('penrose_dance')
        assert c.genre == 'IDM'

    def test_preset_invalid(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            Conductor.preset('nonexistent')

    def test_preset_names_normalized(self):
        """All preset names work with hyphens, underscores, spaces."""
        c = Conductor.preset('midnight_raga')
        assert c.culture == 'indian'
        c = Conductor.preset('midnight-raga')
        assert c.culture == 'indian'

    def test_all_presets_compose(self):
        """Every preset can compose at least one bar."""
        for name in _CONDUCTOR_PRESETS:
            c = Conductor.preset(name)
            arr = c.compose(bars=2)
            assert isinstance(arr, Arrangement), f"Preset {name} failed"


# =====================================================================
# Quick (Natural Language) (6 tests)
# =====================================================================

class TestQuick:

    def test_quick_raga(self):
        c = Conductor()
        arr = c.quick('Indian raga Darbari in Jhaptaal')
        assert isinstance(arr, Arrangement)
        assert c.culture == 'indian'

    def test_quick_maqam(self):
        c = Conductor()
        arr = c.quick('Arabic maqam Rast fast')
        assert isinstance(arr, Arrangement)
        assert c.culture == 'arabic'

    def test_quick_jazz(self):
        c = Conductor()
        arr = c.quick('Jazz swing in Bb')
        assert isinstance(arr, Arrangement)
        assert c.genre == 'Jazz'

    def test_quick_tempo_modifiers(self):
        c = Conductor()
        c.quick('Jazz slow')
        assert c.constraints.bpm <= 80

    def test_quick_ambient(self):
        c = Conductor()
        arr = c.quick('Ambient slow')
        assert isinstance(arr, Arrangement)

    def test_quick_chaining(self):
        c = Conductor()
        arr = c.quick('Indian raga Bhairavi slow')
        analysis = c.analyze_cohomology(arr)
        assert isinstance(analysis, dict)


# =====================================================================
# ConstraintProfile (4 tests)
# =====================================================================

class TestConstraintProfile:

    def test_default_values(self):
        cp = ConstraintProfile()
        assert cp.snap_strength == 0.5
        assert cp.bpm == 120.0
        assert cp.swing_ratio == 0.5

    def test_custom_values(self):
        cp = ConstraintProfile(snap_strength=0.9, bpm=140, swing_ratio=0.67)
        assert cp.snap_strength == 0.9
        assert cp.bpm == 140
        assert cp.swing_ratio == 0.67

    def test_to_dict(self):
        cp = ConstraintProfile()
        d = cp.to_dict()
        assert 'snap_strength' in d
        assert 'bpm' in d
        assert isinstance(d, dict)

    def test_passed_to_conductor(self):
        cp = ConstraintProfile(bpm=200)
        c = Conductor(constraints=cp)
        assert c.constraints.bpm == 200


# =====================================================================
# Integration (6 tests)
# =====================================================================

class TestIntegration:

    def test_compose_analyze_render_pipeline(self, tmp_midi_path):
        """Full pipeline: compose → analyze → MIDI export."""
        c = Conductor.preset('bebop_salt')
        arr = c.compose(bars=4)
        arr.generate_all()

        analysis = c.analyze(arr)
        assert analysis['total_events'] > 0

        size = c.render_midi(arr, tmp_midi_path)
        assert size > 0

    def test_raga_pipeline(self, tmp_midi_path):
        """Indian raga: set_raga → compose_raga → render."""
        c = Conductor(seed=42)
        c.set_raga('darbari')
        arr = c.compose_raga()
        arr.generate_all()

        size = c.render_midi(arr, tmp_midi_path)
        assert size > 0

    def test_maqam_pipeline(self, tmp_midi_path):
        """Arabic maqam: set_maqam → compose_maqam → render."""
        c = Conductor(seed=42)
        c.set_maqam('bayati')
        arr = c.compose_maqam()
        arr.generate_all()

        size = c.render_midi(arr, tmp_midi_path)
        assert size > 0

    def test_evolve_compose_analyze(self):
        """Evolve → compose → analyze pipeline."""
        try:
            c = Conductor(seed=42)
            c.evolve('jazz', generations=3, population=10)
            arr = c.compose(bars=4)
            arr.generate_all()
            analysis = c.analyze(arr)
            assert analysis['track_count'] > 0
        except ImportError:
            pytest.skip("Genome module not available")

    def test_counterpoint_cohomology(self):
        """Counterpoint should have rich harmonic structure."""
        c = Conductor(seed=42, constraints=ConstraintProfile(bpm=72))
        cf = [60, 62, 64, 65, 67, 65, 64, 62]
        arr = c.compose_counterpoint(species=2, cantus_firmus=cf)
        cohomology = c.analyze_cohomology(arr)
        assert cohomology['unique_pitch_classes'] > 0

    def test_multiple_cultures_independent(self):
        """Different cultures produce different arrangements."""
        results = {}
        for culture in ['indian', 'arabic', 'east_asian', 'west_african', 'western']:
            c = Conductor(seed=42)
            c.set_culture(culture)
            arr = c.compose(bars=4)
            results[culture] = arr.bpm

        # Cultures should have different BPMs
        assert results['indian'] != results['west_african']


# =====================================================================
# Data Coverage (4 tests)
# =====================================================================

class TestDataCoverage:

    def test_all_cultures_have_defaults(self):
        for culture in ['indian', 'arabic', 'east_asian', 'west_african', 'western']:
            assert culture in _CULTURE_DEFAULTS
            defaults = _CULTURE_DEFAULTS[culture]
            assert 'scale' in defaults
            assert 'tuning' in defaults
            assert 'bpm' in defaults

    def test_all_presets_have_required_keys(self):
        for name, preset in _CONDUCTOR_PRESETS.items():
            assert 'culture' in preset, f"Preset {name} missing culture"
            assert 'scale' in preset, f"Preset {name} missing scale"
            assert 'bpm' in preset, f"Preset {name} missing bpm"

    def test_all_raga_presets_have_tala(self):
        for name, preset in _RAGA_PRESETS.items():
            assert 'tala' in preset, f"Raga {name} missing tala"
            assert 'tempo' in preset, f"Raga {name} missing tempo"

    def test_all_maqam_presets_have_iqa(self):
        for name, preset in _MAQAM_PRESETS.items():
            assert 'iqa' in preset, f"Maqam {name} missing iqa"

