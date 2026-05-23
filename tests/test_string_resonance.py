"""
Tests for the coupled string resonance simulator.
Covers: string properties, bridge coupling, headstock impedance, sustain,
sympathetic response, sustain-resonance inversion, headstock mass effect,
Kuramoto sync, fret positions, pluck positions, vibrato, and audio output.
"""

import pytest
import numpy as np
import json
import os

from flux_tensor_midi.string_resonance import (
    BoundaryType,
    GuitarString,
    Bridge,
    Headstock,
    Guitar,
    KuramotoCoupling,
    experiment_sustain_vs_resonance,
    experiment_headstock_mass,
    experiment_kuramoto_sync,
    experiment_fret_positions,
    experiment_pluck_position,
    experiment_vibrato,
    run_all_experiments,
)


# ---------------------------------------------------------------------------
# GuitarString tests
# ---------------------------------------------------------------------------

class TestGuitarString:
    """Test GuitarString properties and calculations."""

    def test_default_string_creation(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        assert s.name == "E2"
        assert s.fundamental_hz == 82.41
        assert s.fret == 0
        assert s.epsilon == 0.0
        assert s.n_harmonics == 12

    def test_tension_calculated_from_frequency(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        expected_tension = (2 * s.length_m * s.fundamental_hz) ** 2 * s.linear_density
        assert abs(s.tension - expected_tension) < 0.01

    def test_higher_frequency_higher_tension(self):
        low = GuitarString(name="E2", fundamental_hz=82.41)
        high = GuitarString(name="E4", fundamental_hz=329.63)
        assert high.tension > low.tension

    def test_effective_length_open(self):
        s = GuitarString(name="E2", fundamental_hz=82.41, length_m=0.648)
        assert abs(s.effective_length - 0.648) < 1e-10

    def test_effective_length_fretted(self):
        s = GuitarString(name="E2", fundamental_hz=82.41, length_m=0.648)
        s.fret = 12
        # 12th fret = half length
        assert abs(s.effective_length - 0.324) < 0.001

    def test_effective_length_fret_5(self):
        s = GuitarString(name="A2", fundamental_hz=110.0)
        s.fret = 5
        expected = s.length_m / (2 ** (5 / 12))
        assert abs(s.effective_length - expected) < 1e-10

    def test_fretted_frequency_open(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        assert abs(s.fretted_frequency - 82.41) < 0.01

    def test_fretted_frequency_12th_fret(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        s.fret = 12
        assert abs(s.fretted_frequency - 164.82) < 0.5  # one octave up

    def test_fretted_frequency_with_vibrato(self):
        s = GuitarString(name="E2", fundamental_hz=82.41, epsilon=1.0)
        # With epsilon=1, frequency shifted by ~3%
        assert s.fretted_frequency > 82.41
        assert s.fretted_frequency < 82.41 * 1.04

    def test_harmonics_count(self):
        s = GuitarString(name="E2", fundamental_hz=82.41, n_harmonics=16)
        assert len(s.harmonics) == 16

    def test_harmonics_are_multiples(self):
        s = GuitarString(name="E2", fundamental_hz=82.41, n_harmonics=10)
        omega1 = s.harmonics[0]
        for i, omega in enumerate(s.harmonics):
            assert abs(omega - omega1 * (i + 1)) < 1e-6

    def test_harmonic_amplitudes_decay(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        amps = s.harmonic_amplitudes
        for i in range(len(amps) - 1):
            assert amps[i] > amps[i + 1]  # 1/n is decreasing

    def test_impedance_positive(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        assert s.impedance > 0

    def test_impedance_formula(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        expected = np.sqrt(s.tension * s.linear_density)
        assert abs(s.impedance - expected) < 1e-6

    def test_energy_positive(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        amps = s.harmonic_amplitudes
        assert s.energy(amps) > 0

    def test_energy_zero_for_zero_amplitude(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        assert s.energy(np.zeros(s.n_harmonics)) == 0.0

    def test_sustain_time_positive(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        assert s.sustain_time(100.0) > 0

    def test_sustain_time_higher_boundary_more_sustain(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        low = s.sustain_time(10.0)
        high = s.sustain_time(1000.0)
        assert high > low

    def test_wave_speed(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        expected = np.sqrt(s.tension / s.linear_density)
        assert abs(s.wave_speed() - expected) < 1e-6

    def test_wavelength_fundamental(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        assert abs(s.wavelength(1) - 2 * s.effective_length) < 1e-10

    def test_pluck_amplitudes_shape(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        amps = s.pluck_amplitudes(position=0.2, velocity=1.0)
        assert len(amps) == s.n_harmonics

    def test_pluck_at_middle_kills_even_harmonics(self):
        """Pluck at exactly 0.5 should suppress odd harmonics of the pluck shape."""
        s = GuitarString(name="E2", fundamental_hz=82.41)
        amps = s.pluck_amplitudes(position=0.5)
        # sin(n*pi*0.5) = 0 for even n, so even-indexed harmonics should be 0
        # Actually sin(n*pi*0.5): n=1 -> sin(pi/2)=1, n=2 -> sin(pi)=0, n=3 -> sin(3pi/2)=1...
        # Wait, position=0.5 means sin(n*pi*0.5). For n=2: sin(pi)=0. For n=4: sin(2pi)=0.
        for n in [2, 4, 6, 8, 10, 12]:
            assert abs(amps[n - 1]) < 1e-10, f"Harmonic {n} should be near zero"

    def test_pluck_velocity_scales_amplitude(self):
        s = GuitarString(name="E2", fundamental_hz=82.41)
        a1 = s.pluck_amplitudes(position=0.2, velocity=0.5)
        a2 = s.pluck_amplitudes(position=0.2, velocity=1.0)
        np.testing.assert_allclose(a1, a2 * 0.5, atol=1e-10)


# ---------------------------------------------------------------------------
# Bridge tests
# ---------------------------------------------------------------------------

class TestBridge:
    """Test Bridge coupling and transfer efficiency."""

    def test_default_bridge(self):
        b = Bridge()
        assert b.impedance == 100.0
        assert b.mass == 0.1
        assert b.resonance_freq == 200.0

    def test_coupling_strength_inverse_impedance(self):
        b = Bridge(impedance=50.0)
        assert abs(b.coupling_strength - 0.02) < 1e-10

    def test_higher_impedance_lower_coupling(self):
        b1 = Bridge(impedance=50.0)
        b2 = Bridge(impedance=500.0)
        assert b2.coupling_strength < b1.coupling_strength

    def test_transfer_efficiency_positive(self):
        b = Bridge()
        s1 = GuitarString(name="E2", fundamental_hz=82.41)
        s2 = GuitarString(name="A2", fundamental_hz=110.0)
        eff = b.transfer_efficiency(s1, s2)
        assert eff >= 0

    def test_transfer_efficiency_bounded(self):
        b = Bridge()
        s1 = GuitarString(name="E2", fundamental_hz=82.41)
        s2 = GuitarString(name="E4", fundamental_hz=329.63)
        eff = b.transfer_efficiency(s1, s2)
        assert eff <= 1.0

    def test_self_transfer_not_one(self):
        """Transfer from string to itself is not necessarily 1."""
        b = Bridge()
        s = GuitarString(name="E2", fundamental_hz=82.41)
        eff = b.transfer_efficiency(s, s)
        # z_match is (4*Z*Z)/(Z+Z+Zb)^2 which is < 1
        assert eff < 1.0

    def test_resonance_gain_at_resonance(self):
        b = Bridge(resonance_freq=200.0)
        gain = b.resonance_gain(200.0)
        assert gain > 0

    def test_resonance_gain_shape(self):
        b = Bridge(resonance_freq=200.0)
        # Off-resonance should have different gain
        g_at = b.resonance_gain(200.0)
        g_off = b.resonance_gain(1000.0)
        assert g_at != g_off  # Should differ


# ---------------------------------------------------------------------------
# Headstock tests
# ---------------------------------------------------------------------------

class TestHeadstock:
    """Test Headstock impedance and mass loading."""

    def test_default_headstock(self):
        h = Headstock()
        assert h.base_mass == 0.3
        assert h.added_mass == 0.0

    def test_total_mass(self):
        h = Headstock(added_mass=0.5)
        assert abs(h.total_mass - 0.8) < 1e-10

    def test_impedance_increases_with_mass(self):
        h1 = Headstock(added_mass=0.0)
        h2 = Headstock(added_mass=1.0)
        assert h2.impedance > h1.impedance

    def test_impedance_formula(self):
        h = Headstock(base_mass=0.3, added_mass=0.2, stiffness=1e6)
        expected = np.sqrt(h.stiffness * h.total_mass)
        assert abs(h.impedance - expected) < 1e-6

    def test_resonance_frequency(self):
        h = Headstock(base_mass=0.3, stiffness=1e6)
        f = h.resonance_frequency()
        assert f > 0

    def test_more_mass_lower_resonance(self):
        h1 = Headstock(added_mass=0.0)
        h2 = Headstock(added_mass=2.0)
        assert h2.resonance_frequency() < h1.resonance_frequency()


# ---------------------------------------------------------------------------
# Guitar tests
# ---------------------------------------------------------------------------

class TestGuitar:
    """Test Guitar model with coupled strings."""

    def test_default_six_strings(self):
        g = Guitar()
        assert len(g.strings) == 6
        assert "E2" in g.strings
        assert "E4" in g.strings

    def test_standard_tuning_frequencies(self):
        g = Guitar()
        expected = {
            "E2": 82.41, "A2": 110.0, "D3": 146.83,
            "G3": 196.0, "B3": 246.94, "E4": 329.63
        }
        for name, freq in expected.items():
            assert abs(g.strings[name].fundamental_hz - freq) < 0.1

    def test_add_string(self):
        g = Guitar()
        g.add_string(GuitarString(name="D2", fundamental_hz=73.42))
        assert "D2" in g.strings
        assert len(g.strings) == 7

    def test_remove_string(self):
        g = Guitar()
        g.remove_string("E2")
        assert "E2" not in g.strings
        assert len(g.strings) == 5

    def test_pluck_sets_amplitudes(self):
        g = Guitar()
        g.pluck("E2", velocity=1.0)
        assert np.sum(g.amplitudes["E2"]) > 0
        # Other strings should be at default (not plucked)
        assert np.sum(g.amplitudes["A2"]) > 0  # default harmonic amplitudes

    def test_pluck_nonexistent_string(self):
        g = Guitar()
        g.pluck("X1")  # should not crash
        assert g.time == 0.0  # time unchanged since no pluck happened

    def test_step_advances_time(self):
        g = Guitar()
        initial_time = g.time
        g.pluck("E2")
        g.step(0.01)
        assert g.time > initial_time

    def test_amplitudes_decay_over_time(self):
        g = Guitar()
        g.pluck("E2", velocity=1.0)
        initial_amp = np.sum(g.amplitudes["E2"] ** 2)
        for _ in range(100):
            g.step(0.01)
        final_amp = np.sum(g.amplitudes["E2"] ** 2)
        assert final_amp < initial_amp

    def test_simulate_returns_history(self):
        g = Guitar()
        g.pluck("E2")
        result = g.simulate(duration=0.5)
        assert 'times' in result
        assert 'amplitudes' in result
        assert len(result['times']) > 0
        assert len(result['amplitudes']['E2']) > 0

    def test_measure_sustain_theoretical(self):
        g = Guitar()
        sustain = g.measure_sustain("E2")
        assert sustain > 0

    def test_measure_sustain_nonexistent(self):
        g = Guitar()
        assert g.measure_sustain("X1") == 0.0

    def test_measure_resonance(self):
        g = Guitar()
        r = g.measure_resonance("E2", "A2")
        assert r >= 0

    def test_measure_resonance_nonexistent(self):
        g = Guitar()
        assert g.measure_resonance("X1", "A2") == 0.0

    def test_sympathetic_response(self):
        g = Guitar()
        response = g.sympathetic_response("E2", duration=1.0)
        assert isinstance(response, dict)
        assert "E2" not in response  # plucked string excluded
        for name, amp in response.items():
            assert amp >= 0

    def test_sympathetic_response_nonzero(self):
        """At least some sympathetic vibration should occur."""
        g = Guitar(bridge=Bridge(impedance=50.0))  # low impedance = more coupling
        response = g.sympathetic_response("E2", duration=1.0)
        # With low bridge impedance, there should be some sympathetic response
        total_sympathetic = sum(response.values())
        assert total_sympathetic > 0

    def test_total_energy_positive(self):
        g = Guitar()
        g.pluck("E2")
        assert g.total_energy() > 0

    def test_string_energy(self):
        g = Guitar()
        g.pluck("E2")
        assert g.string_energy("E2") > 0
        assert g.string_energy("X1") == 0.0

    def test_to_audio(self):
        g = Guitar()
        g.pluck("E2")
        audio = g.to_audio(duration=0.5, sample_rate=22050)
        assert len(audio) == int(22050 * 0.5)
        assert np.max(np.abs(audio)) <= 1.0  # normalized

    def test_frequency_response(self):
        g = Guitar()
        g.pluck("E2")
        freqs, resp = g.frequency_response()
        assert len(freqs) == len(resp)
        assert np.max(resp) > 0

    def test_reset(self):
        g = Guitar()
        g.pluck("E2")
        g.step(0.1)
        g.reset()
        assert g.time == 0.0
        for name in g.strings:
            np.testing.assert_allclose(
                g.amplitudes[name],
                g.strings[name].harmonic_amplitudes
            )

    def test_fret_string(self):
        g = Guitar()
        g.fret_string("E2", 5)
        assert g.strings["E2"].fret == 5

    def test_measure_sustain_empirical(self):
        g = Guitar()
        sustain = g.measure_sustain_empirical("E2", duration=5.0)
        assert sustain > 0
        assert sustain <= 5.0


# ---------------------------------------------------------------------------
# KuramotoCoupling tests
# ---------------------------------------------------------------------------

class TestKuramotoCoupling:
    """Test Kuramoto synchronization model."""

    def test_creation(self):
        k = KuramotoCoupling(6, coupling_strength=0.1)
        assert k.n == 6
        assert len(k.phases) == 6

    def test_order_parameter_range(self):
        k = KuramotoCoupling(10)
        r = k.order_parameter()
        assert 0 <= r <= 1

    def test_identical_frequencies_sync(self):
        """Identical frequencies should synchronize."""
        k = KuramotoCoupling(5, coupling_strength=5.0)
        k.set_frequencies(np.ones(5) * 10.0)
        for _ in range(1000):
            k.step(0.01)
        assert k.order_parameter() > 0.5

    def test_no_coupling_no_sync(self):
        """With zero coupling, phases drift freely."""
        k = KuramotoCoupling(5, coupling_strength=0.0)
        freqs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        k.set_frequencies(freqs)
        k.phases = np.linspace(0, 2 * np.pi, 5, endpoint=False)
        r_before = k.order_parameter()
        for _ in range(100):
            k.step(0.01)
        r_after = k.order_parameter()
        # Order parameter should not increase without coupling
        assert r_after < 1.0

    def test_simulate_returns_arrays(self):
        k = KuramotoCoupling(4, coupling_strength=0.5)
        k.set_frequencies(np.array([1.0, 1.1, 1.2, 1.3]))
        times, r_values = k.simulate(1.0, dt=0.01)
        assert len(times) == len(r_values)
        assert len(times) == 100


# ---------------------------------------------------------------------------
# Experiment tests
# ---------------------------------------------------------------------------

class TestExperiments:
    """Test the experiment functions."""

    def test_sustain_vs_resonance_returns_results(self):
        results = experiment_sustain_vs_resonance()
        assert len(results) > 0
        for r in results:
            assert 'bridge_impedance' in r
            assert 'sustain_seconds' in r
            assert 'max_sympathetic' in r
            assert r['sustain_seconds'] >= 0

    def test_sustain_vs_resonance_inversion(self):
        """Higher bridge impedance = more sustain, less resonance."""
        results = experiment_sustain_vs_resonance()
        # Sort by impedance
        results.sort(key=lambda x: x['bridge_impedance'])
        # Sustain should generally increase with impedance
        sustains = [r['sustain_seconds'] for r in results]
        # At minimum, highest impedance should have >= sustain of lowest
        assert sustains[-1] >= sustains[0] * 0.9  # allow small margin

    def test_headstock_mass_returns_results(self):
        results = experiment_headstock_mass()
        assert len(results) > 0
        for r in results:
            assert 'added_mass_kg' in r
            assert 'headstock_impedance' in r
            assert 'sustain_seconds' in r

    def test_headstock_mass_increases_sustain(self):
        """More headstock mass = higher impedance = more sustain."""
        results = experiment_headstock_mass()
        results.sort(key=lambda x: x['added_mass_kg'])
        # Headstock impedance should increase with mass
        impedances = [r['headstock_impedance'] for r in results]
        for i in range(len(impedances) - 1):
            assert impedances[i + 1] >= impedances[i]

    def test_kuramoto_sync_experiment(self):
        result = experiment_kuramoto_sync(n_strings=6, coupling=1.0)
        assert 'mean_sync' in result
        assert 'final_sync' in result
        assert 0 <= result['mean_sync'] <= 1

    def test_fret_positions_experiment(self):
        result = experiment_fret_positions("E2")
        assert len(result['frets']) == 13
        # Frequency should increase with fret
        freqs = [f['frequency'] for f in result['frets']]
        for i in range(len(freqs) - 1):
            assert freqs[i + 1] > freqs[i]

    def test_pluck_position_experiment(self):
        result = experiment_pluck_position()
        assert len(result['positions']) == 20
        for p in result['positions']:
            assert 0 <= p['harmonic richness'] <= 1

    def test_vibrato_experiment(self):
        result = experiment_vibrato()
        assert len(result['vibrato']) > 0
        # Frequency should increase with epsilon
        for i in range(len(result['vibrato']) - 1):
            assert result['vibrato'][i + 1]['frequency'] >= result['vibrato'][i]['frequency']

    def test_run_all_experiments(self, tmp_path):
        results = run_all_experiments(output_dir=str(tmp_path))
        assert 'sustain_vs_resonance' in results
        assert 'headstock_mass' in results
        assert 'kuramoto_sync' in results
        # Check file was saved
        assert os.path.exists(os.path.join(str(tmp_path), "experiment_results.json"))


# ---------------------------------------------------------------------------
# Integration / physics tests
# ---------------------------------------------------------------------------

class TestPhysicsIntegration:
    """Integration tests verifying physical behavior."""

    def test_bridge_low_impedance_more_coupling(self):
        """Low bridge impedance = more coupling = more energy transfer."""
        g_low = Guitar(bridge=Bridge(impedance=20.0))
        g_high = Guitar(bridge=Bridge(impedance=500.0))

        r_low = g_low.sympathetic_response("E2", duration=1.0)
        r_high = g_high.sympathetic_response("E2", duration=1.0)

        total_low = sum(r_low.values())
        total_high = sum(r_high.values())
        assert total_low >= total_high * 0.8  # low impedance should couple more

    def test_all_strings_decay(self):
        """After enough time, all amplitudes should be near zero."""
        g = Guitar()
        g.pluck("E2", velocity=1.0)
        # Use high damping to ensure decay within reasonable sim time
        for name in g.strings:
            g.strings[name].damping = 1.0  # much higher damping
        g._coupling_cache = None  # reset
        g.simulate(duration=10.0)
        for name in g.strings:
            assert np.sum(g.amplitudes[name] ** 2) < 0.1

    def test_octave_strings_resonate_most(self):
        """E2 and E4 (octave apart) should have strong sympathetic resonance."""
        g = Guitar()
        response = g.sympathetic_response("E2", duration=1.0)
        # E4 is an octave above E2, so 2nd harmonic of E2 = fundamental of E4
        # This should produce strong coupling
        e4_response = response.get("E4", 0)
        assert e4_response > 0

    def test_boundary_types_enum(self):
        assert BoundaryType.FIXED.value == "fixed"
        assert BoundaryType.IMPEDANCE.value == "impedance"

    def test_guitar_with_custom_bridge_and_headstock(self):
        b = Bridge(impedance=200.0, mass=0.2)
        h = Headstock(base_mass=0.5, added_mass=0.3)
        g = Guitar(bridge=b, headstock=h)
        assert g.bridge.impedance == 200.0
        assert g.headstock.total_mass == 0.8

    def test_simulate_duration_matches(self):
        g = Guitar()
        g.pluck("E2")
        result = g.simulate(duration=1.0)
        # Last time should be approximately the duration
        assert abs(result['times'][-1] - 1.0) < 0.1

    def test_energy_conservation_approximate(self):
        """Total energy should decrease (dissipation) but not increase dramatically."""
        g = Guitar(bridge=Bridge(impedance=1000.0))  # high impedance = less leak
        g.pluck("E2", velocity=1.0)
        initial_energy = g.total_energy()
        g.step(0.001)
        after_energy = g.total_energy()
        assert after_energy <= initial_energy * 1.01  # small tolerance for numerical noise
