"""Tests for hyperbolic_genre module."""

import math
import numpy as np
import pytest

from flux_tensor_midi.hyperbolic_genre import (
    HyperbolicGenreMap,
    GenrePoint,
    poincare_distance,
    frechet_mean,
    GENRE_DIM,
    AXIS_LABELS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def gmap() -> HyperbolicGenreMap:
    return HyperbolicGenreMap()


# ---------------------------------------------------------------------------
# Genre placement validity
# ---------------------------------------------------------------------------

class TestGenrePlacement:
    """All predefined genres must be valid Poincaré ball points."""

    def test_all_inside_ball(self, gmap: HyperbolicGenreMap):
        for name, gp in gmap.genres.items():
            norm = np.linalg.norm(gp.coords)
            assert norm < 1.0, f"{name} has norm {norm} >= 1.0"

    def test_all_finite(self, gmap: HyperbolicGenreMap):
        for name, gp in gmap.genres.items():
            assert np.all(np.isfinite(gp.coords)), f"{name} has non-finite coords"

    def test_all_correct_dimension(self, gmap: HyperbolicGenreMap):
        for name, gp in gmap.genres.items():
            assert gp.coords.shape == (GENRE_DIM,), f"{name} wrong shape"

    def test_genre_count(self, gmap: HyperbolicGenreMap):
        assert gmap.genre_count >= 30

    def test_root_near_origin(self, gmap: HyperbolicGenreMap):
        music = gmap.genres["Music"]
        assert music.norm < 0.05

    def test_level4_near_boundary(self, gmap: HyperbolicGenreMap):
        coltrane = gmap.genres["Coltrane-style"]
        assert coltrane.norm > 0.7

    def test_hierarchy_levels(self, gmap: HyperbolicGenreMap):
        assert gmap.genres["Music"].level == 0
        assert gmap.genres["Western"].level == 1
        assert gmap.genres["Jazz"].level == 2
        assert gmap.genres["Bebop"].level == 3
        assert gmap.genres["Coltrane-style"].level == 4


# ---------------------------------------------------------------------------
# Distance properties
# ---------------------------------------------------------------------------

class TestDistance:
    def test_distance_symmetry(self, gmap: HyperbolicGenreMap):
        d_ab = gmap.distance("Jazz", "Classical")
        d_ba = gmap.distance("Classical", "Jazz")
        assert abs(d_ab - d_ba) < 1e-10

    def test_distance_nonneg(self, gmap: HyperbolicGenreMap):
        for a in ["Jazz", "Classical", "Techno", "Raga"]:
            for b in ["Blues", "Ambient", "Polyrhythm", "Metal"]:
                assert gmap.distance(a, b) >= 0.0

    def test_distance_zero_self(self, gmap: HyperbolicGenreMap):
        d = gmap.distance("Jazz", "Jazz")
        assert d < 1e-6

    def test_triangle_inequality(self, gmap: HyperbolicGenreMap):
        d_ac = gmap.distance("Jazz", "Classical")
        d_ab = gmap.distance("Jazz", "Blues")
        d_bc = gmap.distance("Blues", "Classical")
        assert d_ac <= d_ab + d_bc + 1e-8

    def test_siblings_closer_than_cousins(self, gmap: HyperbolicGenreMap):
        """Bebop and Modal Jazz (siblings) should be closer than Bebop and Baroque (cousins)."""
        d_siblings = gmap.distance("Bebop", "Modal Jazz")
        d_cousins = gmap.distance("Bebop", "Baroque")
        assert d_siblings < d_cousins


# ---------------------------------------------------------------------------
# Fréchet mean and blending
# ---------------------------------------------------------------------------

class TestBlending:
    def test_blend_midpoint_interior(self, gmap: HyperbolicGenreMap):
        blend = gmap.genre_blend("Jazz", "Classical", weight_a=0.5)
        norm = np.linalg.norm(blend)
        assert 0.0 < norm < 1.0
        assert np.all(np.isfinite(blend))

    def test_blend_weight_extremes(self, gmap: HyperbolicGenreMap):
        near_jazz = gmap.genre_blend("Jazz", "Classical", weight_a=0.99)
        d_jazz = poincare_distance(near_jazz, gmap.genres["Jazz"].coords)
        d_classical = poincare_distance(near_jazz, gmap.genres["Classical"].coords)
        assert d_jazz < d_classical

    def test_blend_symmetry(self, gmap: HyperbolicGenreMap):
        """Blend 50/50 should produce same result either direction."""
        b1 = gmap.genre_blend("Jazz", "Classical", weight_a=0.5)
        b2 = gmap.genre_blend("Classical", "Jazz", weight_a=0.5)
        assert np.allclose(b1, b2, atol=1e-6)

    def test_multi_blend(self, gmap: HyperbolicGenreMap):
        blend = gmap.multi_blend(["Jazz", "Blues", "Rock"])
        assert np.linalg.norm(blend) < 1.0
        assert np.all(np.isfinite(blend))

    def test_frechet_mean_converges(self):
        pts = [np.array([0.3, 0.0]), np.array([0.0, 0.3]), np.array([-0.3, 0.0])]
        mean = frechet_mean(pts)
        assert np.linalg.norm(mean) < 1.0
        assert np.all(np.isfinite(mean))


# ---------------------------------------------------------------------------
# Nearest genres
# ---------------------------------------------------------------------------

class TestNearestGenres:
    def test_nearest_to_self(self, gmap: HyperbolicGenreMap):
        nearest = gmap.nearest_genres("Bebop", n=1)
        assert nearest[0][0] == "Bebop"
        assert nearest[0][1] < 1e-6

    def test_nearest_respects_hierarchy(self, gmap: HyperbolicGenreMap):
        """Nearest genres to Bebop should be other jazz sub-genres."""
        nearest = gmap.nearest_genres("Bebop", n=5)
        names = [n for n, _ in nearest]
        # At least one other jazz sub-genre in top 5
        jazz_subs = {"Swing", "Modal Jazz", "Free Jazz", "Jazz"}
        assert bool(set(names) & jazz_subs), f"No jazz neighbors: {names}"

    def test_nearest_from_point(self, gmap: HyperbolicGenreMap):
        pt = gmap.genres["Jazz"].coords
        nearest = gmap.nearest_genres(pt, n=3)
        assert nearest[0][0] == "Jazz"


# ---------------------------------------------------------------------------
# Random walk
# ---------------------------------------------------------------------------

class TestGenreWalk:
    def test_walk_stays_inside_ball(self, gmap: HyperbolicGenreMap):
        rng = np.random.default_rng(42)
        for _ in range(20):
            pt, name = gmap.genre_walk("Jazz", step_size=0.3, rng=rng)
            assert np.linalg.norm(pt) < 1.0
            assert name in gmap.genres

    def test_walk_step_size_matters(self, gmap: HyperbolicGenreMap):
        rng = np.random.default_rng(42)
        pt_small, _ = gmap.genre_walk("Jazz", step_size=0.1, rng=rng)
        rng2 = np.random.default_rng(42)
        pt_large, _ = gmap.genre_walk("Jazz", step_size=0.8, rng=rng2)
        # Larger step should (generally) produce more displacement
        d_small = poincare_distance(pt_small, gmap.genres["Jazz"].coords)
        d_large = poincare_distance(pt_large, gmap.genres["Jazz"].coords)
        assert d_large > d_small


# ---------------------------------------------------------------------------
# Cultural distance
# ---------------------------------------------------------------------------

class TestCulturalDistance:
    def test_western_eastern_far(self, gmap: HyperbolicGenreMap):
        d = gmap.cultural_distance("Western", "Eastern")
        assert d > 0.1

    def test_same_tradition_close(self, gmap: HyperbolicGenreMap):
        d = gmap.cultural_distance("Jazz", "Classical")
        # Both Western
        assert d < 3.0

    def test_unknown_genre_raises(self, gmap: HyperbolicGenreMap):
        with pytest.raises(KeyError):
            gmap.cultural_distance("Nonexistent", "Jazz")


# ---------------------------------------------------------------------------
# Encode / Decode
# ---------------------------------------------------------------------------

class TestEncodeDecode:
    def test_decode_returns_all_axes(self, gmap: HyperbolicGenreMap):
        constraints = gmap.decode_to_constraints(gmap.genres["Jazz"].coords)
        assert set(constraints.keys()) == set(AXIS_LABELS)

    def test_decode_values_bounded(self, gmap: HyperbolicGenreMap):
        for name in ["Jazz", "Classical", "Techno", "Raga"]:
            constraints = gmap.decode_to_constraints(gmap.genres[name].coords)
            for val in constraints.values():
                assert 0.0 <= val <= 1.0, f"{name}: {val} out of bounds"

    def test_encode_produces_valid_point(self, gmap: HyperbolicGenreMap):
        constraints = {"chromatic_density": 0.9, "rhythmic_intensity": 0.7}
        pt = gmap.encode_genre(constraints)
        assert np.linalg.norm(pt) < 1.0
        assert pt.shape == (GENRE_DIM,)

    def test_roundtrip_approximate(self, gmap: HyperbolicGenreMap):
        """Encode → decode should approximately recover high-signal dimensions."""
        orig = {"chromatic_density": 0.9, "rhythmic_intensity": 0.1}
        pt = gmap.encode_genre(orig)
        recovered = gmap.decode_to_constraints(pt)
        # Chromatic should still be high, rhythmic low
        assert recovered["chromatic_density"] > 0.5
        assert recovered["rhythmic_intensity"] < 0.6


# ---------------------------------------------------------------------------
# GenrePoint
# ---------------------------------------------------------------------------

class TestGenrePoint:
    def test_genre_point_norm(self, gmap: HyperbolicGenreMap):
        gp = gmap.genres["Jazz"]
        assert abs(gp.norm - np.linalg.norm(gp.coords)) < 1e-10

    def test_genre_point_distance(self, gmap: HyperbolicGenreMap):
        a = gmap.genres["Jazz"]
        b = gmap.genres["Blues"]
        d = a.distance_to(b)
        assert d > 0
        assert d == pytest.approx(gmap.distance("Jazz", "Blues"))


# ---------------------------------------------------------------------------
# Hierarchy queries
# ---------------------------------------------------------------------------

class TestHierarchy:
    def test_children(self, gmap: HyperbolicGenreMap):
        children = gmap.children("Jazz")
        assert "Bebop" in children
        assert "Modal Jazz" in children

    def test_siblings(self, gmap: HyperbolicGenreMap):
        sibs = gmap.siblings("Bebop")
        assert "Modal Jazz" in sibs
        assert "Bebop" not in sibs

    def test_root_has_no_parent(self, gmap: HyperbolicGenreMap):
        assert gmap.genres["Music"].parent is None

    def test_add_custom_genre(self, gmap: HyperbolicGenreMap):
        gmap.add_genre("Hyperpop", "Electronic", [0.7, 0.9, 0.5, 0.2, 0.4, 0.8, 0.3, 0.1], 0.65)
        assert "Hyperpop" in gmap.genres
        assert gmap.genres["Hyperpop"].parent == "Electronic"
        assert np.linalg.norm(gmap.genres["Hyperpop"].coords) < 1.0
