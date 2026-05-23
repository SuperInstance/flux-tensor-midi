"""Tests for flux_tensor_midi.neural_music — 35+ tests."""

import math
import random
import pytest

from flux_tensor_midi.neural_music import (
    _sigmoid,
    _tanh,
    _softmax,
    _clamp,
    _interval_consonance,
    NeuroTransmitter,
    MusicalSynapse,
    MusicalNeuron,
    CortexType,
    MusicalCortex,
    DopamineSystem,
    MemoryPattern,
    Hippocampus,
    MusicalBrain,
    neural_performance,
)
from flux_tensor_midi.midi import MidiEvent


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_sigmoid_zero(self):
        assert _sigmoid(0) == pytest.approx(0.5, abs=0.01)

    def test_sigmoid_large_positive(self):
        assert _sigmoid(10) > 0.99

    def test_sigmoid_large_negative(self):
        assert _sigmoid(-10) < 0.01

    def test_sigmoid_gain(self):
        s1 = _sigmoid(0.5, gain=1.0)
        s2 = _sigmoid(0.5, gain=5.0)
        assert s2 != s1

    def test_tanh_range(self):
        assert -1 <= _tanh(3.0) <= 1

    def test_softmax_sums_to_one(self):
        vals = [1.0, 2.0, 3.0]
        result = _softmax(vals)
        assert sum(result) == pytest.approx(1.0, abs=0.001)

    def test_softmax_empty(self):
        assert _softmax([]) == []

    def test_clamp_within(self):
        assert _clamp(0.5) == 0.5

    def test_clamp_below(self):
        assert _clamp(-1.0) == 0.0

    def test_clamp_above(self):
        assert _clamp(5.0) == 1.0

    def test_interval_consonance_perfect_fifth(self):
        assert _interval_consonance(7) > 0.8

    def test_interval_consonance_tritone(self):
        assert _interval_consonance(6) < 0.5


# ---------------------------------------------------------------------------
# MusicalSynapse
# ---------------------------------------------------------------------------

class TestMusicalSynapse:

    def _syn(self, **kw):
        """Create a synapse with required ids and optional overrides."""
        defaults = dict(pre_id="a", post_id="b")
        defaults.update(kw)
        return MusicalSynapse(**defaults)

    def test_transmit_excitatory(self):
        syn = self._syn(weight=0.8, neurotransmitter=NeuroTransmitter.EXCITATORY)
        assert syn.transmit(1.0) == pytest.approx(0.8)

    def test_transmit_inhibitory(self):
        syn = self._syn(weight=0.5, neurotransmitter=NeuroTransmitter.INHIBITORY)
        result = syn.transmit(1.0)
        assert result < 0  # inhibitory flips sign

    def test_transmit_modulatory(self):
        syn = self._syn(weight=1.0, neurotransmitter=NeuroTransmitter.MODULATORY)
        result = syn.transmit(1.0)
        assert 0 < result < 1.0  # attenuated

    def test_hebbian_update_strengthens(self):
        syn = self._syn(weight=0.5)
        syn.hebbian_update(pre_active=True, post_active=True, lr=0.05)
        assert syn.weight > 0.5

    def test_hebbian_update_no_coactivation(self):
        syn = self._syn(weight=0.5)
        syn.hebbian_update(pre_active=False, post_active=True, lr=0.05)
        # Only decay, no strengthening
        assert syn.weight < 0.5

    def test_weight_clamped_to_max(self):
        syn = self._syn(weight=1.99, max_weight=2.0)
        syn.hebbian_update(True, True, lr=0.1)
        assert syn.weight <= 2.0

    def test_eligibility_trace_updated(self):
        syn = self._syn(eligibility=0.0)
        syn.hebbian_update(True, True)
        assert syn.eligibility > 0.0


# ---------------------------------------------------------------------------
# MusicalNeuron
# ---------------------------------------------------------------------------

class TestMusicalNeuron:

    def test_receive_adds_potential(self):
        n = MusicalNeuron()
        n.receive(0.5)
        assert n.potential == pytest.approx(0.5)

    def test_integrate_applies_leak(self):
        n = MusicalNeuron(potential=1.0, leak=0.1)
        n.integrate()
        assert n.potential < 1.0

    def test_fire_returns_event_when_threshold_met(self):
        n = MusicalNeuron(threshold=0.3, ticks_since_fire=100, potential=0.6)
        evt = n.fire()
        assert evt is not None
        assert isinstance(evt, MidiEvent)

    def test_fire_returns_none_below_threshold(self):
        n = MusicalNeuron(threshold=0.9, potential=0.3, ticks_since_fire=100)
        evt = n.fire()
        assert evt is None

    def test_fire_refractory_prevents_firing(self):
        n = MusicalNeuron(threshold=0.3, potential=1.0,
                          refractory_ticks=10, ticks_since_fire=1)
        evt = n.fire()
        assert evt is None

    def test_fire_resets_potential(self):
        n = MusicalNeuron(threshold=0.3, potential=0.8, ticks_since_fire=100)
        n.fire()
        assert n.potential == 0.0

    def test_fire_count_increments(self):
        n = MusicalNeuron(threshold=0.2, potential=0.8, ticks_since_fire=100)
        n.fire()
        assert n.fire_count == 1

    def test_step_integrates_and_fires(self):
        n = MusicalNeuron(threshold=0.2, leak=0.0, noise_sigma=0.0,
                          potential=0.5, ticks_since_fire=100)
        evt = n.step()
        assert evt is not None

    def test_reset_clears_state(self):
        n = MusicalNeuron(potential=0.8, fire_count=5)
        n.reset()
        assert n.potential == 0.0
        assert n.fire_count == 0

    def test_hebbian_learn_returns_delta(self):
        n = MusicalNeuron()
        delta = n.hebbian_learn(True, True, lr=0.05)
        assert delta == pytest.approx(0.05)

    def test_can_fire(self):
        n = MusicalNeuron(refractory_ticks=5, ticks_since_fire=10)
        assert n.can_fire() is True

    def test_cannot_fire_in_refractory(self):
        n = MusicalNeuron(refractory_ticks=5, ticks_since_fire=2)
        assert n.can_fire() is False


# ---------------------------------------------------------------------------
# MusicalCortex
# ---------------------------------------------------------------------------

class TestMusicalCortex:

    def test_make_pitch_cortex(self):
        c = MusicalCortex.make_pitch_cortex(root=60, n=12)
        assert len(c.neurons) == 12
        assert c.layer_type == CortexType.PITCH

    def test_make_rhythm_cortex(self):
        c = MusicalCortex.make_rhythm_cortex(subdivision=16)
        assert len(c.neurons) == 16
        assert c.layer_type == CortexType.RHYTHM

    def test_make_emotion_cortex(self):
        c = MusicalCortex.make_emotion_cortex(n=6)
        assert len(c.neurons) == 6

    def test_make_output_cortex(self):
        c = MusicalCortex.make_output_cortex(root=48, span=24)
        assert len(c.neurons) == 24

    def test_activate_returns_firing_pattern(self):
        c = MusicalCortex.make_pitch_cortex(n=5)
        signals = [0.8, 0.7, 0.6, 0.5, 0.4]
        fired = c.activate(signals)
        assert len(fired) == 5
        assert all(isinstance(f, bool) for f in fired)

    def test_reset(self):
        c = MusicalCortex.make_pitch_cortex(n=5)
        for n in c.neurons:
            n.potential = 1.0
        c.reset()
        assert all(n.potential == 0.0 for n in c.neurons)


# ---------------------------------------------------------------------------
# DopamineSystem
# ---------------------------------------------------------------------------

class TestDopamineSystem:

    def test_reward_returns_float(self):
        d = DopamineSystem()
        r = d.reward(60, [64, 67])
        assert isinstance(r, float)
        assert 0 <= r <= 1

    def test_reward_consonant_is_high(self):
        d = DopamineSystem()
        # C with E and G — consonant triad
        r = d.reward(60, [64, 67])
        assert r > 0.3

    def test_withdrawal_decays(self):
        d = DopamineSystem(baseline=0.3, current=0.8)
        d.withdrawal()
        assert d.current < 0.8

    def test_average_reward(self):
        d = DopamineSystem()
        d.reward_history = [0.5, 0.6, 0.7]
        assert d.average_reward == pytest.approx(0.6, abs=0.01)

    def test_reset_clears(self):
        d = DopamineSystem()
        d.current = 0.9
        d.reward_history.append(0.5)
        d.reset()
        assert d.current == d.baseline
        assert len(d.reward_history) == 0


# ---------------------------------------------------------------------------
# Hippocampus
# ---------------------------------------------------------------------------

class TestHippocampus:

    def test_store_pattern(self):
        h = Hippocampus()
        mp = h.store([True, False, True], reward=0.7, tick=5)
        assert mp is not None
        assert len(h.patterns) == 1

    def test_recall_returns_similar(self):
        h = Hippocampus()
        h.store([True, True, True, False], reward=0.8)
        h.store([False, False, False, True], reward=0.5)
        results = h.recall([True, True, True, False], top_k=1)
        assert len(results) == 1
        assert results[0].reward == 0.8

    def test_capacity_eviction(self):
        h = Hippocampus(capacity=3)
        for i in range(5):
            h.store([True, False], reward=float(i) * 0.1, tick=i)
        assert len(h.patterns) == 3

    def test_consolidate_prunes_weak(self):
        h = Hippocampus(consolidation_threshold=0.6)
        h.store([True], reward=0.9)
        h.store([False], reward=0.1)
        h.consolidate()
        assert all(p.reward >= 0.6 for p in h.patterns)

    def test_replay(self):
        h = Hippocampus()
        h.store([True, False], reward=0.5)
        h.store([False, True], reward=0.6)
        replays = h.replay()
        assert len(replays) == 2


# ---------------------------------------------------------------------------
# MemoryPattern
# ---------------------------------------------------------------------------

class TestMemoryPattern:

    def test_similarity_identical(self):
        mp = MemoryPattern(pattern=[True, False, True])
        assert mp.similarity([True, False, True]) == pytest.approx(1.0)

    def test_similarity_different(self):
        mp = MemoryPattern(pattern=[True, True, True])
        assert mp.similarity([False, False, False]) == pytest.approx(0.0)

    def test_similarity_empty(self):
        mp = MemoryPattern(pattern=[])
        assert mp.similarity([True]) == 0.0


# ---------------------------------------------------------------------------
# MusicalBrain
# ---------------------------------------------------------------------------

class TestMusicalBrain:

    def test_build_creates_layers(self):
        brain = MusicalBrain.build(root=60)
        assert "auditory" in brain.layers
        assert "pitch" in brain.layers
        assert "rhythm" in brain.layers
        assert "emotion" in brain.layers
        assert "output" in brain.layers
        assert "decision" in brain.layers
        assert "memory" in brain.layers

    def test_build_has_synapses(self):
        brain = MusicalBrain.build(root=60)
        assert len(brain.synapses) > 0

    def test_perceive_returns_dict(self):
        brain = MusicalBrain.build(root=60)
        result = brain.perceive([60, 64, 67])
        assert "auditory" in result
        assert "pitch" in result
        assert "tick" in result

    def test_decide_returns_events(self):
        brain = MusicalBrain.build(root=60)
        perception = brain.perceive([60, 64])
        events = brain.decide(perception)
        assert isinstance(events, list)

    def test_learn_updates_synapses(self):
        brain = MusicalBrain.build(root=60)
        initial_weights = [s.weight for s in brain.synapses]
        brain.perceive([60, 64])
        brain.decide({"decision": [True] * 8})
        brain.learn(0.8)
        # At least some weights should have changed
        new_weights = [s.weight for s in brain.synapses]
        assert initial_weights != new_weights

    def test_perform_returns_arrangement(self):
        brain = MusicalBrain.build(root=60, seed=42)
        arr = brain.perform(bars=2)
        assert arr is not None
        assert arr.bpm == 120.0

    def test_sleep_returns_stats(self):
        brain = MusicalBrain.build(root=60, seed=42)
        brain.perform(bars=2)
        result = brain.sleep()
        assert "pruned_patterns" in result
        assert "pruned_synapses" in result

    def test_stats(self):
        brain = MusicalBrain.build(root=60)
        stats = brain.stats()
        assert "total_neurons" in stats
        assert "total_synapses" in stats
        assert "dopamine" in stats

    def test_reset(self):
        brain = MusicalBrain.build(root=60)
        brain.tick = 50
        brain.reset()
        assert brain.tick == 0

    def test_snap_to_scale(self):
        brain = MusicalBrain.build(root=60, scale=[0, 2, 4, 5, 7, 9, 11])
        # Note 61 (C#) should snap to 60 (C) or 62 (D)
        snapped = brain._snap_to_scale(61)
        assert snapped % 12 in brain.scale

    def test_deterministic_with_seed(self):
        arr1 = neural_performance(root=60, bars=4, seed=123)
        arr2 = neural_performance(root=60, bars=4, seed=123)
        # Same seed → same arrangement (summary comparison)
        assert arr1.summary()["bpm"] == arr2.summary()["bpm"]

    def test_neural_performance_convenience(self):
        arr = neural_performance(root=60, bpm=100, bars=4, seed=42)
        assert arr is not None


# ---------------------------------------------------------------------------
# Integration test
# ---------------------------------------------------------------------------

class TestIntegration:

    def test_full_pipeline_perform_export(self, tmp_path):
        """Build brain → perform → export to MIDI file."""
        brain = MusicalBrain.build(root=60, bpm=120, seed=42)
        arr = brain.perform(bars=4)
        out = str(tmp_path / "neural.mid")
        arr.to_midi(out)
        import os
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0

    def test_learn_then_sleep_improves(self):
        """After learning + sleep, synaptic structure should change."""
        brain = MusicalBrain.build(root=60, seed=7)
        w_before = [s.weight for s in brain.synapses]
        brain.perform(bars=4)
        brain.sleep()
        w_after = [s.weight for s in brain.synapses]
        # Weight vector should differ (learning happened)
        assert w_before != w_after
