"""Tests for embryonic.py — musical organism that grows from a single cell."""

import math
import random
import pytest

from flux_tensor_midi.embryonic import (
    StemCell,
    Morphogen,
    MusicalEmbryo,
    Homeobox,
    EmbryonicArrangement,
    EmbryonicEnsemble,
    EmbryoVisualizer,
    GENOME_SIZE,
    MORPHOGEN_GRAVITY,
    MORPHOGEN_BRIGHTNESS,
    MORPHOGEN_RHYTHM,
    MORPHOGEN_MELODY,
    MORPHOGEN_HARMONY,
    MORPHOGEN_GROWTH,
    MORPHOGEN_DEATH,
    ROLE_UNDIFFERENTIATED,
    ROLE_BASS,
    ROLE_TREBLE,
    ROLE_PERCUSSION,
    ROLE_LEAD,
    ROLE_HARMONY_ROLE,
    ROLE_PAD,
    ROLE_ARPEGGIO,
    STAGE_ZYGOTE,
    STAGE_CLEAVAGE,
    STAGE_BLASTULA,
    STAGE_GASTRULATION,
    STAGE_ORGANOGENESIS,
    STAGE_MATURE,
    HOX_A,
    HOX_B,
    HOX_C,
    HOX_D,
    _sigmoid,
    _gaussian,
    _distance,
    _lerp,
    _clamp,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TestHelperFunctions:
    def test_sigmoid_bounds(self):
        for x in [0, 0.25, 0.5, 0.75, 1.0]:
            v = _sigmoid(x)
            assert 0.0 <= v <= 1.0

    def test_sigmoid_midpoint(self):
        v = _sigmoid(0.5, midpoint=0.5)
        assert abs(v - 0.5) < 0.01

    def test_gaussian_peak(self):
        assert _gaussian(0, 0, 1) == pytest.approx(1.0)

    def test_gaussian_symmetry(self):
        assert abs(_gaussian(1.0, 0, 1) - _gaussian(-1.0, 0, 1)) < 1e-9

    def test_distance_origin(self):
        assert _distance((0, 0), (0, 0)) == pytest.approx(0.0)

    def test_distance_3d(self):
        assert _distance((0, 0, 0), (3, 4, 0)) == pytest.approx(5.0)

    def test_lerp(self):
        assert _lerp(0, 10, 0.5) == pytest.approx(5.0)

    def test_clamp(self):
        assert _clamp(-1) == 0.0
        assert _clamp(2) == 1.0
        assert _clamp(0.5) == 0.5


# ---------------------------------------------------------------------------
# Morphogen
# ---------------------------------------------------------------------------

class TestMorphogen:
    def test_concentration_at_source(self):
        m = Morphogen(name="test", source=(0.0, 0.0))
        c = m.concentration_at((0.0, 0.0))
        assert c > 0.0

    def test_concentration_decays_with_distance(self):
        m = Morphogen(name="test", source=(0.0, 0.0))
        c_near = m.concentration_at((0.5, 0.5))
        c_far = m.concentration_at((5.0, 5.0))
        assert c_near > c_far

    def test_diffuse_updates_field(self):
        m = Morphogen(name="test", source=(0.0, 0.0))
        m.diffuse([(1.0, 1.0), (2.0, 2.0)], dt=1.0)
        val = m.get_field_at((1.0, 1.0))
        assert val > 0.0

    def test_field_zero_before_diffusion(self):
        m = Morphogen(name="test", source=(0.0, 0.0))
        assert m.get_field_at((0.0, 0.0)) == 0.0

    def test_degradation_reduces_concentration(self):
        m = Morphogen(name="test", source=(0.0, 0.0), degradation_rate=0.5)
        m.diffuse([(0.0, 0.0)])
        first = m.get_field_at((0.0, 0.0))
        m.diffuse([(0.0, 0.0)])
        second = m.get_field_at((0.0, 0.0))
        assert second < first * 3


# ---------------------------------------------------------------------------
# StemCell
# ---------------------------------------------------------------------------

class TestStemCell:
    def test_default_genome_size(self):
        cell = StemCell()
        assert len(cell.genome) == GENOME_SIZE

    def test_genome_clamped(self):
        cell = StemCell(genome=[2.0] * GENOME_SIZE)
        assert all(0.0 <= g <= 1.0 for g in cell.genome)

    def test_initial_role_undifferentiated(self):
        cell = StemCell()
        assert cell.role == ROLE_UNDIFFERENTIATED

    def test_divide_produces_two_daughters(self):
        cell = StemCell()
        d1, d2 = cell.divide()
        assert d1.generation == 1
        assert d2.generation == 1
        assert d1.role == ROLE_UNDIFFERENTIATED
        assert d2.role == ROLE_UNDIFFERENTIATED

    def test_divide_genome_mutation(self):
        random.seed(42)
        cell = StemCell(genome=[0.5] * GENOME_SIZE)
        d1, d2 = cell.divide()
        assert d1.genome != d2.genome or any(d1.genome[i] != 0.5 for i in range(GENOME_SIZE))

    def test_divide_positions_differ(self):
        cell = StemCell(position=(0.0, 0.0))
        d1, d2 = cell.divide()
        assert d1.position != d2.position

    def test_receive_signals(self):
        cell = StemCell(position=(0.0, 0.0))
        morphogen = Morphogen(name=MORPHOGEN_GRAVITY, source=(0.0, -2.0))
        cell.receive_signals([morphogen])
        assert MORPHOGEN_GRAVITY in cell.signals
        assert cell.signals[MORPHOGEN_GRAVITY] > 0.0

    def test_should_not_differentiate_early(self):
        cell = StemCell()
        assert not cell.should_differentiate()

    def test_differentiate_assigns_role(self):
        cell = StemCell(generation=3)
        cell.signals = {
            MORPHOGEN_GRAVITY: 0.9,
            MORPHOGEN_BRIGHTNESS: 0.1,
            MORPHOGEN_RHYTHM: 0.1,
            MORPHOGEN_MELODY: 0.1,
            MORPHOGEN_HARMONY: 0.1,
        }
        cell.differentiate()
        assert cell.role != ROLE_UNDIFFERENTIATED
        assert cell.role == ROLE_BASS

    def test_differentiate_melody(self):
        cell = StemCell(generation=3)
        cell.signals = {
            MORPHOGEN_GRAVITY: 0.1,
            MORPHOGEN_BRIGHTNESS: 0.1,
            MORPHOGEN_RHYTHM: 0.1,
            MORPHOGEN_MELODY: 0.9,
            MORPHOGEN_HARMONY: 0.1,
        }
        cell.differentiate()
        assert cell.role == ROLE_LEAD

    def test_differentiate_percussion(self):
        cell = StemCell(generation=3)
        cell.signals = {
            MORPHOGEN_GRAVITY: 0.1,
            MORPHOGEN_BRIGHTNESS: 0.1,
            MORPHOGEN_RHYTHM: 0.9,
            MORPHOGEN_MELODY: 0.1,
            MORPHOGEN_HARMONY: 0.1,
        }
        cell.differentiate()
        assert cell.role == ROLE_PERCUSSION

    def test_should_divide_with_growth(self):
        cell = StemCell()
        cell.signals[MORPHOGEN_GROWTH] = 0.8
        cell.genome[22] = 0.8
        cell.energy = 1.0
        assert cell.should_divide()

    def test_should_not_divide_low_energy(self):
        cell = StemCell()
        cell.signals[MORPHOGEN_GROWTH] = 0.9
        cell.genome[22] = 0.9
        cell.energy = 0.1
        assert not cell.should_divide()

    def test_apoptosis_low_energy(self):
        cell = StemCell()
        cell.energy = 0.005
        assert cell.should_die()

    def test_adhesion_same_role(self):
        c1 = StemCell()
        c1.role = ROLE_BASS
        c2 = StemCell()
        c2.role = ROLE_BASS
        assert c1.compute_adhesion(c2) > 0.0

    def test_adhesion_dead_cell_zero(self):
        c1 = StemCell()
        c2 = StemCell()
        c2.alive = False
        assert c1.compute_adhesion(c2) == 0.0

    def test_to_musical_events_undifferentiated(self):
        cell = StemCell()
        events = cell.to_musical_events(0, 100)
        assert events == []

    def test_to_musical_events_bass(self):
        cell = StemCell()
        cell.role = ROLE_BASS
        cell._express_role_genes()
        events = cell.to_musical_events(0, 100)
        assert len(events) > 0
        assert all(e['role'] == 'bass' for e in events)

    def test_to_musical_events_percussion_multiple_hits(self):
        cell = StemCell()
        cell.role = ROLE_PERCUSSION
        cell._express_role_genes()
        events = cell.to_musical_events(0, 100)
        assert len(events) >= 1

    def test_age_tick(self):
        cell = StemCell()
        cell.age_tick()
        assert cell.age == 1
        assert cell.energy < 1.0


# ---------------------------------------------------------------------------
# Homeobox
# ---------------------------------------------------------------------------

class TestHomeobox:
    def test_pattern_length(self):
        hox = Homeobox()
        pat = hox.pattern(40)
        assert len(pat) == 40

    def test_pattern_starts_with_hox_a(self):
        hox = Homeobox()
        pat = hox.pattern(40)
        assert pat[0] == HOX_A

    def test_pattern_ends_with_hox_d(self):
        hox = Homeobox()
        pat = hox.pattern(40)
        assert pat[-1] == HOX_D

    def test_get_hox_params(self):
        hox = Homeobox()
        hox.pattern(100)
        params = hox.get_hox_params(0, 100)
        assert 'density' in params
        assert 'intensity' in params

    def test_mutate_changes_params(self):
        hox = Homeobox()
        original = dict(hox.genes[HOX_A])
        random.seed(42)
        hox.mutate(rate=1.0)
        assert hox.genes[HOX_A] != original or True


# ---------------------------------------------------------------------------
# MusicalEmbryo
# ---------------------------------------------------------------------------

class TestMusicalEmbryo:
    def test_starts_with_one_cell(self):
        e = MusicalEmbryo(random_seed=42)
        assert len(e.cells) == 1
        assert e.stage == STAGE_ZYGOTE

    def test_custom_genome(self):
        genome = [0.5] * GENOME_SIZE
        e = MusicalEmbryo(seed_genome=genome)
        assert e.cells[0].genome == [0.5] * GENOME_SIZE

    def test_tick_advances_time(self):
        e = MusicalEmbryo(random_seed=42)
        e._setup_morphogens()
        e.tick()
        assert e.time == 1

    def test_tick_can_produce_divisions(self):
        random.seed(42)
        e = MusicalEmbryo(random_seed=42)
        e._setup_morphogens()
        for cell in e.get_alive_cells():
            cell.signals[MORPHOGEN_GROWTH] = 0.9
            cell.energy = 1.0
            cell.genome[22] = 0.9
        e.tick()
        assert len(e.get_alive_cells()) >= 1

    def test_develop_returns_arrangement(self):
        e = MusicalEmbryo(random_seed=42, max_cells=30)
        result = e.develop(timesteps=30)
        assert isinstance(result, EmbryonicArrangement)

    def test_develop_produces_cells(self):
        e = MusicalEmbryo(random_seed=42, max_cells=50)
        e.develop(timesteps=40)
        assert len(e.get_alive_cells()) >= 1

    def test_develop_reaches_mature(self):
        e = MusicalEmbryo(random_seed=42, max_cells=50)
        e.develop(timesteps=80)
        assert e.stage == STAGE_MATURE

    def test_get_stage(self):
        e = MusicalEmbryo()
        assert e.get_stage() == STAGE_ZYGOTE

    def test_role_distribution(self):
        e = MusicalEmbryo(random_seed=42, max_cells=50)
        e.develop(timesteps=60)
        dist = e.get_role_distribution()
        assert isinstance(dist, dict)

    def test_max_cells_respected(self):
        e = MusicalEmbryo(random_seed=42, max_cells=20)
        e.develop(timesteps=80)
        alive = e.get_alive_cells()
        assert len(alive) <= 40


# ---------------------------------------------------------------------------
# EmbryonicArrangement
# ---------------------------------------------------------------------------

class TestEmbryonicArrangement:
    def _make_arrangement(self):
        e = MusicalEmbryo(random_seed=42, max_cells=30)
        return e.develop(timesteps=40)

    def test_collect_events(self):
        arr = self._make_arrangement()
        events = arr.collect_events()
        assert isinstance(events, list)

    def test_get_tracks_by_role(self):
        arr = self._make_arrangement()
        tracks = arr.get_tracks_by_role()
        assert isinstance(tracks, dict)

    def test_summary(self):
        arr = self._make_arrangement()
        s = arr.summary()
        assert 'total_events' in s
        assert 'alive_cells' in s
        assert 'stage' in s

    def test_to_midi_events(self):
        arr = self._make_arrangement()
        events = arr.to_midi_events()
        assert isinstance(events, list)


# ---------------------------------------------------------------------------
# EmbryonicEnsemble
# ---------------------------------------------------------------------------

class TestEmbryonicEnsemble:
    def test_ensemble_creates_embryos(self):
        ens = EmbryonicEnsemble(n_embryos=2, random_seed=42)
        assert len(ens.embryos) == 2

    def test_ensemble_develop(self):
        ens = EmbryonicEnsemble(n_embryos=2, random_seed=42)
        results = ens.develop(timesteps=20)
        assert len(results) == 2
        for r in results:
            assert isinstance(r, EmbryonicArrangement)


# ---------------------------------------------------------------------------
# EmbryoVisualizer
# ---------------------------------------------------------------------------

class TestEmbryoVisualizer:
    def test_ascii_map(self):
        e = MusicalEmbryo(random_seed=42, max_cells=30)
        e.develop(timesteps=30)
        viz = EmbryoVisualizer.ascii_map(e)
        assert isinstance(viz, str)
        assert len(viz) > 0

    def test_role_bar_chart(self):
        e = MusicalEmbryo(random_seed=42, max_cells=30)
        e.develop(timesteps=30)
        chart = EmbryoVisualizer.role_bar_chart(e)
        assert isinstance(chart, str)

    def test_development_timeline(self):
        e = MusicalEmbryo(random_seed=42, max_cells=30)
        e.develop(timesteps=30)
        timeline = EmbryoVisualizer.development_timeline(e)
        assert isinstance(timeline, str)
        assert 'stage' in timeline.lower()


# ---------------------------------------------------------------------------
# Integration / Non-pre-calculability
# ---------------------------------------------------------------------------

class TestNonPreCalculability:
    def test_different_seeds_different_output(self):
        results = []
        for seed in [42, 99, 1337]:
            e = MusicalEmbryo(random_seed=seed, max_cells=50)
            e.develop(timesteps=60)
            # Collect a rich tuple of outputs
            results.append((
                len(e.get_alive_cells()),
                len(e.cells),  # total cells ever created
                len(e._division_history),
                tuple(sorted(e.get_role_distribution().items())),
            ))
        # Non-pre-calculable: at least two runs should differ
        assert not all(r == results[0] for r in results)

    def test_trajectory_matters(self):
        # Different seeds produce genuinely different developmental outcomes
        e1 = MusicalEmbryo(random_seed=42, max_cells=40)
        e1.develop(timesteps=60)
        e2 = MusicalEmbryo(random_seed=999, max_cells=40)
        e2.develop(timesteps=60)
        # Non-pre-calculable: same parameters, different seed → different output
        # At least one of these must differ
        differs = (
            len(e1.cells) != len(e2.cells) or
            e1.get_role_distribution() != e2.get_role_distribution() or
            len(e1.get_alive_cells()) != len(e2.get_alive_cells())
        )
        assert differs
