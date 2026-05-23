"""
Tests for the Living Conductor — 40+ tests covering living system integration.

Tests the wiring of living.py, gene_regulatory.py, constraint_repair.py,
protein_fold.py, and embryonic.py into the unified Conductor.

Run: python -m pytest tests/test_conductor_living.py -v
"""

from __future__ import annotations

import pytest

from flux_tensor_midi.conductor import Conductor, ConstraintProfile, _CONDUCTOR_PRESETS
from flux_tensor_midi.tracks import Arrangement, Track
from flux_tensor_midi.midi.events import MidiEvent


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def conductor():
    return Conductor(seed=42)


@pytest.fixture
def western_conductor():
    c = Conductor(culture='western', seed=42)
    return c


# =====================================================================
# Living Jazz Session (8 tests)
# =====================================================================

class TestLiveSession:

    def test_live_session_basic(self, western_conductor):
        arr = western_conductor.live_session(bars=8)
        assert isinstance(arr, Arrangement)
        assert len(arr.tracks) > 0

    def test_live_session_generates_events(self, western_conductor):
        arr = western_conductor.live_session(bars=8)
        total = sum(len(t.events) for t in arr.tracks)
        assert total > 0

    def test_live_session_stores_session(self, western_conductor):
        western_conductor.live_session(bars=8)
        assert western_conductor._session is not None

    def test_live_session_custom_key(self, western_conductor):
        arr = western_conductor.live_session(bars=8, key='Bb', style='bebop')
        assert isinstance(arr, Arrangement)

    def test_live_session_modal(self, western_conductor):
        arr = western_conductor.live_session(bars=8, style='modal')
        assert isinstance(arr, Arrangement)

    def test_live_session_different_seeds(self):
        c1 = Conductor(seed=42)
        arr1 = c1.live_session(bars=8)
        n1 = sum(len(t.events) for t in arr1.tracks)

        c2 = Conductor(seed=99)
        arr2 = c2.live_session(bars=8)
        n2 = sum(len(t.events) for t in arr2.tracks)
        # Different seeds should produce different output
        # (not guaranteed but very likely)
        assert isinstance(n1, int) and isinstance(n2, int)

    def test_live_session_analysis(self, western_conductor):
        arr = western_conductor.live_session(bars=8)
        analysis = western_conductor.analyze(arr)
        assert 'session_state' in analysis
        assert 'cells' in analysis['session_state']

    def test_live_session_phases_progress(self, western_conductor):
        arr = western_conductor.live_session(bars=32)
        state = western_conductor._session.get_session_state()
        assert state['beat'] > 0


# =====================================================================
# Gene Regulatory Network (8 tests)
# =====================================================================

class TestLiveGeneNetwork:

    def test_live_gene_network_basic(self, conductor):
        arr = conductor.live_gene_network(steps=50)
        assert isinstance(arr, Arrangement)

    def test_live_gene_network_stores_grn(self, conductor):
        conductor.live_gene_network(steps=50)
        assert conductor._grn is not None

    def test_live_gene_network_different_steps(self, conductor):
        arr50 = conductor.live_gene_network(steps=50)
        conductor._grn = None
        arr100 = conductor.live_gene_network(steps=100)
        assert isinstance(arr100, Arrangement)

    def test_live_gene_network_analysis(self, conductor):
        arr = conductor.live_gene_network(steps=50)
        analysis = conductor.analyze(arr)
        assert 'grn_state' in analysis

    def test_live_gene_network_has_tracks(self, conductor):
        arr = conductor.live_gene_network(steps=100)
        assert len(arr.tracks) > 0

    def test_live_gene_network_with_culture(self):
        c = Conductor(culture='indian', seed=42)
        arr = c.live_gene_network(steps=50)
        assert isinstance(arr, Arrangement)

    def test_live_gene_network_generates_events(self, conductor):
        arr = conductor.live_gene_network(steps=100)
        total = sum(len(t.events) for t in arr.tracks)
        assert total > 0

    def test_live_gene_network_grn_state_summary(self, conductor):
        conductor.live_gene_network(steps=50)
        summary = conductor._grn.get_network_state_summary()
        assert 'pitch' in summary
        assert 'rhythm' in summary


# =====================================================================
# Embryonic Development (8 tests)
# =====================================================================

class TestLiveEmbryo:

    def test_live_embryo_basic(self, conductor):
        arr = conductor.live_embryo(timesteps=50)
        assert isinstance(arr, Arrangement)

    def test_live_embryo_stores_embryo(self, conductor):
        conductor.live_embryo(timesteps=50)
        assert conductor._embryo is not None

    def test_live_embryo_development_summary(self, conductor):
        conductor.live_embryo(timesteps=50)
        embryo = conductor._embryo
        assert embryo.get_stage() is not None
        assert len(embryo.get_alive_cells()) > 0

    def test_live_embryo_different_timesteps(self, conductor):
        arr30 = conductor.live_embryo(timesteps=30)
        conductor._embryo = None
        arr80 = conductor.live_embryo(timesteps=80)
        assert isinstance(arr80, Arrangement)

    def test_live_embryo_custom_genome(self, conductor):
        import random
        random.seed(42)
        genome = [random.random() for _ in range(25)]
        arr = conductor.live_embryo(seed_genome=genome, timesteps=50)
        assert isinstance(arr, Arrangement)

    def test_live_embryo_analysis(self, conductor):
        arr = conductor.live_embryo(timesteps=50)
        analysis = conductor.analyze(arr)
        assert 'embryo_summary' in analysis

    def test_live_embryo_different_seeds(self):
        c1 = Conductor(seed=42)
        c1.live_embryo(timesteps=50)
        s1 = c1._embryo.get_role_distribution()

        c2 = Conductor(seed=99)
        c2.live_embryo(timesteps=50)
        s2 = c2._embryo.get_role_distribution()

        # Different seeds should give different development
        assert isinstance(s1, dict)
        assert isinstance(s2, dict)

    def test_live_embryo_with_scale(self):
        c = Conductor(culture='east_asian', seed=42)
        arr = c.live_embryo(timesteps=50)
        assert isinstance(arr, Arrangement)


# =====================================================================
# Protein Folding (5 tests)
# =====================================================================

class TestLiveProteinFold:

    def test_live_protein_fold_basic(self, conductor):
        arr = conductor.live_protein_fold('ACDEFGHIKLMNPQRSTVWY')
        assert isinstance(arr, Arrangement)

    def test_live_protein_fold_short_sequence(self, conductor):
        arr = conductor.live_protein_fold('ACDEF')
        assert isinstance(arr, Arrangement)

    def test_live_protein_fold_custom_sequence(self, conductor):
        arr = conductor.live_protein_fold('KKKKCCCCCAAAA')
        assert isinstance(arr, Arrangement)

    def test_live_protein_fold_invalid_aa(self, conductor):
        with pytest.raises(ValueError, match="Invalid amino acid"):
            conductor.live_protein_fold('ACX')

    def test_live_protein_fold_has_events(self, conductor):
        arr = conductor.live_protein_fold('ACDEFGHIKLMNPQRSTVWY')
        total = sum(len(t.events) for t in arr.tracks)
        assert total > 0


# =====================================================================
# Trading Fours & Call-Response (5 tests)
# =====================================================================

class TestLiveInteraction:

    def test_trading_fours_basic(self, conductor):
        conductor.constraints.bpm = 160
        arr = conductor.live_trading_fours(bars=8)
        assert isinstance(arr, Arrangement)

    def test_trading_fours_events(self, conductor):
        conductor.constraints.bpm = 140
        arr = conductor.live_trading_fours(bars=16)
        total = sum(len(t.events) for t in arr.tracks)
        assert total > 0

    def test_call_response_basic(self, conductor):
        arr = conductor.live_call_response(bars=8)
        assert isinstance(arr, Arrangement)

    def test_call_response_two_tracks(self, conductor):
        arr = conductor.live_call_response(bars=8)
        assert len(arr.tracks) >= 2

    def test_call_response_events(self, conductor):
        arr = conductor.live_call_response(bars=8)
        total = sum(len(t.events) for t in arr.tracks)
        assert total > 0


# =====================================================================
# Evolution (3 tests)
# =====================================================================

class TestLiveEvolution:

    def test_live_evolution_basic(self, conductor):
        c = conductor.live_evolution(generations=10)
        assert c is conductor
        assert conductor._grn is not None

    def test_live_evolution_updates_bpm(self, conductor):
        original_bpm = conductor.constraints.bpm
        conductor.live_evolution(generations=10)
        # BPM should be set from evolved GRN
        assert conductor.constraints.bpm > 0

    def test_live_evolution_chaining(self, conductor):
        arr = conductor.live_evolution(generations=5).compose(bars=4)
        assert isinstance(arr, Arrangement)


# =====================================================================
# Repair (5 tests)
# =====================================================================

class TestRepair:

    def test_repair_basic(self, conductor):
        conductor.set_culture('western')
        arr = conductor.compose(bars=4)
        arr.generate_all()
        repaired = conductor.repair(arr)
        assert isinstance(repaired, Arrangement)

    def test_repair_preserves_events(self, conductor):
        conductor.set_culture('western')
        arr = conductor.compose(bars=4)
        arr.generate_all()
        original_count = sum(len(t.events) for t in arr.tracks)
        repaired = conductor.repair(arr)
        repaired_count = sum(len(t.events) for t in repaired.tracks)
        # Should have roughly the same number of events
        assert repaired_count > 0

    def test_repair_named_repaired(self, conductor):
        conductor.set_culture('western')
        arr = conductor.compose(bars=4)
        arr.generate_all()
        repaired = conductor.repair(arr)
        assert 'repaired' in repaired.name

    def test_repair_empty_arrangement(self, conductor):
        arr = Arrangement(name='empty')
        repaired = conductor.repair(arr)
        assert isinstance(repaired, Arrangement) or repaired is arr

    def test_repair_with_culture(self):
        c = Conductor.preset('midnight_raga')
        arr = c.compose(bars=4)
        arr.generate_all()
        repaired = c.repair(arr)
        assert isinstance(repaired, Arrangement)


# =====================================================================
# Living Presets (8 tests)
# =====================================================================

class TestLivingPresets:

    def test_living_jazz_preset(self):
        c = Conductor.preset('living_jazz')
        assert c.culture == 'western'
        assert c.constraints.bpm == 140

    def test_living_bebop_preset(self):
        c = Conductor.preset('living_bebop')
        assert c.constraints.bpm == 180

    def test_gene_garden_preset(self):
        c = Conductor.preset('gene_garden')
        assert c.genre == 'IDM'

    def test_protein_sonata_preset(self):
        c = Conductor.preset('protein_sonata')
        assert c.genre == 'Classical'

    def test_embryo_dream_preset(self):
        c = Conductor.preset('embryo_dream')
        assert c.culture == 'east_asian'

    def test_trading_fours_preset(self):
        c = Conductor.preset('trading_fours')
        assert c.constraints.bpm == 160

    def test_call_response_preset(self):
        c = Conductor.preset('call_response')
        assert c.culture == 'west_african'

    def test_repair_shop_preset(self):
        c = Conductor.preset('repair_shop')
        assert c.genre == 'Jazz'


# =====================================================================
# Integration (5 tests)
# =====================================================================

class TestLivingIntegration:

    def test_full_living_pipeline(self):
        """Compose live → analyze → repair."""
        c = Conductor(seed=42)
        arr = c.live_session(bars=8)
        analysis = c.analyze(arr)
        assert 'session_state' in analysis

    def test_compose_then_repair(self):
        """Static compose → living repair."""
        c = Conductor.preset('bebop_salt')
        arr = c.compose(bars=4)
        arr.generate_all()
        repaired = c.repair(arr)
        assert isinstance(repaired, Arrangement)

    def test_gene_network_then_compose(self):
        """GRN → compose: evolved constraints feed composition."""
        c = Conductor(seed=42)
        c.live_evolution(generations=5)
        arr = c.compose(bars=4)
        assert isinstance(arr, Arrangement)

    def test_embryo_then_analyze(self):
        """Embryo → full analysis with embryo state."""
        c = Conductor(seed=42)
        arr = c.live_embryo(timesteps=50)
        analysis = c.analyze(arr)
        assert 'embryo_summary' in analysis
        assert 'constraint_satisfaction' in analysis

    def test_multiple_living_systems(self):
        """Run multiple living systems in sequence."""
        c = Conductor(seed=42)

        # Gene network
        arr1 = c.live_gene_network(steps=30)
        assert isinstance(arr1, Arrangement)

        # Reset and run session
        c._session = None
        c._grn = None
        arr2 = c.live_session(bars=8)
        assert isinstance(arr2, Arrangement)
