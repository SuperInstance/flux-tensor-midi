"""Tests for constraint_impedance module — 25+ tests."""

import pytest
import numpy as np
from flux_tensor_midi.constraint_impedance import (
    ImpedanceProfile, ConstraintForce, ConstraintReverb, ImpedanceMatcher,
    transfer_efficiency, resonance_score, reflection_coefficient,
    standing_wave_ratio, find_sweet_spot, quality_factor, bandwidth,
    impedance_spectrum, analyze_all_genres, GENRE_IMPEDANCES,
)


# ── ImpedanceProfile tests ──

class TestImpedanceProfile:
    def test_total_impedance_default(self):
        p = ImpedanceProfile(name="test")
        assert p.total_impedance == pytest.approx(np.sqrt(5), rel=1e-6)

    def test_impedance_vector_length(self):
        p = ImpedanceProfile(name="test", snap_impedance=2, funnel_impedance=3)
        assert len(p.impedance_vector) == 5
        assert p.impedance_vector[0] == 2.0
        assert p.impedance_vector[1] == 3.0

    def test_dominant_dimension(self):
        p = ImpedanceProfile(name="test", tempo_impedance=10.0)
        assert p.dominant_dimension == 'tempo'

    def test_flexibility_inverse(self):
        p = ImpedanceProfile(name="test", snap_impedance=1, funnel_impedance=0,
                              consensus_impedance=0, laman_impedance=0, tempo_impedance=0)
        assert p.flexibility == pytest.approx(1.0, rel=1e-6)

    def test_normalized_vector(self):
        p = ImpedanceProfile(name="test", snap_impedance=3, funnel_impedance=4)
        norm = np.linalg.norm(p.normalized_vector())
        assert norm == pytest.approx(1.0, rel=1e-6)

    def test_impedance_ratio(self):
        p = ImpedanceProfile(name="test", snap_impedance=1, funnel_impedance=1,
                              consensus_impedance=1, laman_impedance=1, tempo_impedance=1)
        assert p.impedance_ratio('snap') == pytest.approx(1.0 / np.sqrt(5), rel=1e-4)


# ── ConstraintForce tests ──

class TestConstraintForce:
    def test_strength_vector(self):
        f = ConstraintForce(name="test", snap_strength=2, tempo_strength=3)
        assert f.strength_vector[0] == 2.0
        assert f.strength_vector[4] == 3.0

    def test_total_strength(self):
        f = ConstraintForce(name="test", snap_strength=3, funnel_strength=4)
        assert f.total_strength == pytest.approx(5.0, rel=1e-6)

    def test_matched_force(self):
        f = ConstraintForce(name="orig", snap_strength=1.0, frequency=2.0)
        s = ImpedanceProfile(name="sys", snap_impedance=5, funnel_impedance=3,
                              consensus_impedance=2, laman_impedance=4, tempo_impedance=1)
        matched = f.matched_force(s)
        assert matched.snap_strength == 5.0
        assert matched.funnel_strength == 3.0
        assert matched.frequency == 2.0


# ── Transfer efficiency tests ──

class TestTransferEfficiency:
    def test_perfect_match(self):
        """When constraint strength = system impedance, transfer should be max (1.0)."""
        f = ConstraintForce(name="perfect", snap_strength=2, funnel_strength=3,
                             consensus_strength=1, laman_strength=4, tempo_strength=5)
        s = ImpedanceProfile(name="matched", snap_impedance=2, funnel_impedance=3,
                              consensus_impedance=1, laman_impedance=4, tempo_impedance=5)
        assert transfer_efficiency(f, s) == pytest.approx(1.0, rel=1e-6)

    def test_zero_force(self):
        """Zero constraint = zero transfer."""
        f = ConstraintForce(name="zero")
        s = ImpedanceProfile(name="any", snap_impedance=5)
        assert transfer_efficiency(f, s) == pytest.approx(0.0, abs=1e-6)

    def test_mismatch_reduces_efficiency(self):
        """Mismatched impedance should reduce efficiency below 1.0."""
        f = ConstraintForce(name="weak", snap_strength=0.1)
        s = ImpedanceProfile(name="rigid", snap_impedance=10.0)
        eff = transfer_efficiency(f, s)
        assert 0 < eff < 1.0


# ── Resonance tests ──

class TestResonance:
    def test_perfect_resonance(self):
        f = ConstraintForce(name="res", frequency=1.0)
        s = ImpedanceProfile(name="sys")
        assert resonance_score(f, s, system_natural_freq=1.0) == pytest.approx(1.0, rel=1e-6)

    def test_off_resonance(self):
        f = ConstraintForce(name="off", frequency=100.0)
        s = ImpedanceProfile(name="sys")
        score = resonance_score(f, s, system_natural_freq=1.0)
        assert score < 0.01


# ── Reflection and SWR tests ──

class TestReflectionAndSWR:
    def test_matched_reflection_zero(self):
        f = ConstraintForce(name="m", snap_strength=3)
        s = ImpedanceProfile(name="m", snap_impedance=3)
        gamma = reflection_coefficient(f, s)
        assert gamma[0] == pytest.approx(0.0, abs=1e-6)

    def test_swr_perfect_match(self):
        f = ConstraintForce(name="m", snap_strength=2, funnel_strength=2,
                             consensus_strength=2, laman_strength=2, tempo_strength=2)
        s = ImpedanceProfile(name="m", snap_impedance=2, funnel_impedance=2,
                              consensus_impedance=2, laman_impedance=2, tempo_impedance=2)
        swr = standing_wave_ratio(f, s)
        assert np.allclose(swr, 1.0, rtol=1e-3)

    def test_mismatched_swr_high(self):
        f = ConstraintForce(name="weak", snap_strength=0.01)
        s = ImpedanceProfile(name="rigid", snap_impedance=10.0)
        swr = standing_wave_ratio(f, s)
        assert swr[0] > 1.0


# ── Quality factor tests ──

class TestQualityFactor:
    def test_uniform_high_q(self):
        """Uniform impedance = high Q (specialist)."""
        p = ImpedanceProfile(name="uniform", snap_impedance=5, funnel_impedance=5,
                              consensus_impedance=5, laman_impedance=5, tempo_impedance=5)
        q = quality_factor(p)
        assert q > 100  # near-infinite Q for perfectly uniform

    def test_varied_low_q(self):
        """Varied impedance = lower Q (generalist)."""
        p = ImpedanceProfile(name="varied", snap_impedance=1, funnel_impedance=5,
                              consensus_impedance=1, laman_impedance=5, tempo_impedance=1)
        q = quality_factor(p)
        assert q < 10

    def test_bandwidth_inverse_q(self):
        p = ImpedanceProfile(name="t", snap_impedance=3, funnel_impedance=1)
        q = quality_factor(p)
        bw = bandwidth(p)
        assert bw == pytest.approx(1.0 / q, rel=1e-6)


# ── Sweet spot tests ──

class TestSweetSpot:
    def test_finds_nonzero_efficiency(self):
        s = ImpedanceProfile(name="jazz", snap_impedance=2, funnel_impedance=3,
                              consensus_impedance=4, laman_impedance=2, tempo_impedance=3)
        result = find_sweet_spot(s)
        assert result['best_efficiency'] > 0
        assert result['best_constraint'] is not None

    def test_sweet_spot_has_system_impedance(self):
        s = ImpedanceProfile(name="t")
        result = find_sweet_spot(s)
        assert result['system_impedance'] == s.total_impedance


# ── ConstraintReverb tests ──

class TestConstraintReverb:
    def test_reverb_time_sabine(self):
        r = ConstraintReverb(volume=10.0, surface_area=10.0, absorption=0.5)
        expected = 0.161 * 10.0 / (10.0 * 0.5)
        assert r.reverb_time == pytest.approx(expected, rel=1e-4)

    def test_brainstorm_high_reverb(self):
        r = ConstraintReverb().optimize_for_phase("brainstorm")
        assert r.reverb_time > 1.0  # ideas bounce a lot

    def test_edit_low_reverb(self):
        r = ConstraintReverb().optimize_for_phase("edit")
        assert r.reverb_time < 0.5  # tight control

    def test_decay_curve_shape(self):
        r = ConstraintReverb(volume=5.0, surface_area=10.0, absorption=0.3)
        curve = r.decay_curve(duration=2.0)
        assert len(curve) == 200
        assert curve[0] == pytest.approx(1.0, rel=1e-4)
        assert curve[-1] < curve[0]  # decays over time

    def test_echo_density(self):
        r = ConstraintReverb(volume=5.0, surface_area=10.0)
        density = r.echo_density()
        assert density == pytest.approx(2.0, rel=1e-4)


# ── ImpedanceMatcher tests ──

class TestImpedanceMatcher:
    def test_register_and_retrieve(self):
        m = ImpedanceMatcher()
        m.register_genre("test", 1, 2, 3, 4, 5)
        assert "test" in m.profiles
        assert m.profiles["test"].snap_impedance == 1

    def test_impedance_mismatch(self):
        m = ImpedanceMatcher()
        m.register_genre("a", 1, 1, 1, 1, 1)
        m.register_genre("b", 1, 1, 1, 1, 1)
        assert m.impedance_mismatch("a", "b") == pytest.approx(0.0, abs=1e-6)

    def test_impedance_mismatch_different(self):
        m = ImpedanceMatcher()
        m.register_genre("a", 1, 1, 1, 1, 1)
        m.register_genre("b", 5, 5, 5, 5, 5)
        mismatch = m.impedance_mismatch("a", "b")
        assert mismatch > 0

    def test_best_constraint_returns_dict(self):
        m = ImpedanceMatcher()
        m.register_genre("jazz", 2, 3, 4, 2, 3)
        result = m.best_constraint_for("jazz")
        assert result is not None
        assert 'best_efficiency' in result

    def test_best_constraint_unknown_returns_none(self):
        m = ImpedanceMatcher()
        assert m.best_constraint_for("nonexistent") is None

    def test_genre_blend(self):
        m = ImpedanceMatcher()
        m.register_genre("a", 2, 2, 2, 2, 2)
        m.register_genre("b", 4, 4, 4, 4, 4)
        blend = m.genre_blend_impedance(["a", "b"], [1, 1])
        expected = 3.0
        assert blend.snap_impedance == pytest.approx(expected, rel=1e-6)

    def test_most_compatible(self):
        m = ImpedanceMatcher()
        m.register_genre("a", 2, 2, 2, 2, 2)
        m.register_genre("b", 2.1, 2.1, 2.1, 2.1, 2.1)
        m.register_genre("c", 10, 10, 10, 10, 10)
        pair = m.most_compatible_pair()
        assert pair is not None
        assert set([pair[0], pair[1]]) == {"a", "b"}

    def test_least_compatible(self):
        m = ImpedanceMatcher()
        m.register_genre("a", 1, 1, 1, 1, 1)
        m.register_genre("b", 1, 1, 1, 1, 1)
        m.register_genre("c", 10, 10, 10, 10, 10)
        pair = m.least_compatible_pair()
        assert pair is not None
        assert "c" in (pair[0], pair[1])

    def test_load_presets(self):
        m = ImpedanceMatcher()
        m.load_presets()
        assert len(m.profiles) == len(GENRE_IMPEDANCES)


# ── Impedance spectrum tests ──

class TestImpedanceSpectrum:
    def test_spectrum_returns_array(self):
        p = ImpedanceProfile(name="t", snap_impedance=2)
        freqs = np.array([0.5, 1.0, 2.0])
        spec = impedance_spectrum(p, freqs)
        assert len(spec) == 3
        assert all(s >= 0 for s in spec)


# ── Full analysis integration test ──

class TestAnalysis:
    def test_analyze_all_genres(self):
        result = analyze_all_genres()
        assert 'genre_analysis' in result
        assert 'compatibility' in result
        assert 'most_compatible' in result
        assert 'least_compatible' in result
        assert len(result['genre_analysis']) == len(GENRE_IMPEDANCES)

    def test_most_compatible_are_close(self):
        result = analyze_all_genres()
        mc = result['most_compatible']
        lc = result['least_compatible']
        assert mc['mismatch'] < lc['mismatch']

    def test_genre_analysis_has_required_fields(self):
        result = analyze_all_genres()
        for genre, analysis in result['genre_analysis'].items():
            assert 'total_impedance' in analysis
            assert 'dominant_dimension' in analysis
            assert 'quality_factor' in analysis
            assert 'flexibility' in analysis
            assert 'sweet_spot_efficiency' in analysis
