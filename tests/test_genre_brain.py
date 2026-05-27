"""Tests for the genre_brain module."""

from __future__ import annotations

import pytest

from flux_tensor_midi.genre_brain import GenreBrain
from flux_tensor_midi.core.snap import RhythmicRole


class TestGenreBrainInit:
    def test_known_genre_jazz(self):
        brain = GenreBrain('jazz')
        assert brain.genre == 'jazz'

    def test_case_insensitive(self):
        brain = GenreBrain('Jazz')
        assert brain.genre == 'jazz'

    def test_unknown_genre_raises(self):
        with pytest.raises(ValueError, match="Unknown genre"):
            GenreBrain('polka')

    def test_all_presets_loadable(self):
        for name in GenreBrain.available_genres():
            brain = GenreBrain(name)
            assert brain.genre == name


class TestGenreBrainPresets:
    def test_available_genres(self):
        genres = GenreBrain.available_genres()
        assert 'jazz' in genres
        assert 'hiphop' in genres
        assert 'electronic' in genres
        assert 'classical' in genres
        assert 'math' in genres
        assert genres == sorted(genres)

    def test_get_preset_returns_dict(self):
        brain = GenreBrain('jazz')
        preset = brain.get_preset()
        assert isinstance(preset, dict)
        assert 'description' in preset
        assert 'roles' in preset
        assert 'member_names' in preset
        assert 'salience_profiles' in preset
        assert 'tolerance_profiles' in preset
        assert 'default_bpm' in preset

    def test_preset_not_mutable(self):
        brain = GenreBrain('jazz')
        p1 = brain.get_preset()
        p1['description'] = 'mutated'
        p2 = brain.get_preset()
        assert p2['description'] != 'mutated'

    def test_description(self):
        brain = GenreBrain('hiphop')
        assert isinstance(brain.description, str)
        assert len(brain.description) > 0

    def test_jazz_preset_roles(self):
        brain = GenreBrain('jazz')
        preset = brain.get_preset()
        assert RhythmicRole.ROOT in preset['roles']
        assert len(preset['roles']) == 3

    def test_jazz_preset_members(self):
        brain = GenreBrain('jazz')
        preset = brain.get_preset()
        assert preset['member_names'] == ['piano', 'bass', 'drums']

    def test_math_preset_zero_tolerance(self):
        brain = GenreBrain('math')
        preset = brain.get_preset()
        for tol in preset['tolerance_profiles']:
            assert all(t == 0.0 for t in tol)


class TestGenreBrainCreateBand:
    def test_create_band_jazz(self):
        brain = GenreBrain('jazz')
        band, musicians = brain.create_band(bpm=120, bars=4)
        assert band is not None
        assert len(musicians) == 3
        assert band.bpm == 120.0

    def test_create_band_with_seed(self):
        brain = GenreBrain('electronic')
        band1, mus1 = brain.create_band(seed=42)
        band2, mus2 = brain.create_band(seed=42)
        # Same seed should produce same band name
        assert band1.name == band2.name

    def test_create_band_default_bpm(self):
        brain = GenreBrain('jazz')
        band, _ = brain.create_band()
        assert band.bpm == 180.0  # jazz default

    def test_create_band_custom_bpm(self):
        brain = GenreBrain('jazz')
        band, _ = brain.create_band(bpm=200)
        assert band.bpm == 200.0

    def test_create_band_everyone_listens(self):
        brain = GenreBrain('jazz')
        band, _ = brain.create_band()
        # jazz has listen_matrix='everyone' — conductor + 3 musicians = 4 members
        assert band.member_count >= 4

    def test_create_band_conductor_listens(self):
        brain = GenreBrain('hiphop')
        band, musicians = brain.create_band()
        assert len(musicians) == 3
        assert band is not None


class TestGenreBrainConfigureBand:
    def test_configure_existing_band(self):
        brain = GenreBrain('jazz')
        band, musicians = brain.create_band(bpm=120)
        # Reconfigure
        brain.configure_band(band, musicians)
        # Should not raise

    def test_configure_shorter_musicians_list(self):
        brain = GenreBrain('jazz')
        band, musicians = brain.create_band()
        # Should handle fewer musicians without error
        brain.configure_band(band, musicians[:1])


class TestGenreBrainRepr:
    def test_repr(self):
        brain = GenreBrain('jazz')
        r = repr(brain)
        assert 'GenreBrain' in r
        assert 'jazz' in r

    def test_repr_contains_description(self):
        brain = GenreBrain('jazz')
        r = repr(brain)
        assert 'Bebop' in r
