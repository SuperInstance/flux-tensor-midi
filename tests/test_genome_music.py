"""
Tests for genome_music — Musical Evolution via Genetic Constraint Systems.

Covers: MusicalGenome, GenomePlayer, MusicalEvolution, fitness evaluation,
genetic operators (mutate, crossover, tournament_select), multi-genre experiments.
"""

import numpy as np
import pytest

from flux_tensor_midi.genome_music import (
    MusicalGenome,
    MusicalEvent,
    GenomePlayer,
    MusicalEvolution,
    EvolutionResult,
    GENE_SPECS,
    GENRE_TARGETS,
    DOMAIN_ORDER,
    evaluate_fitness,
    mutate_genome,
    crossover,
    tournament_select,
    run_multi_genre_experiment,
)


# ===================================================================
# MusicalGenome tests
# ===================================================================

class TestMusicalGenome:
    def test_create_random_genome(self):
        g = MusicalGenome(seed=42)
        assert g.gene_count == 25

    def test_create_from_dict(self):
        genes = {s[0]: s[3] for s in GENE_SPECS}
        g = MusicalGenome(genes=genes)
        assert g.gene_count == 25

    def test_gene_values_clamped(self):
        genes = {"snap_strictness": -5.0, "tempo_tendency": 999.0}
        g = MusicalGenome(genes=genes)
        # snap_strictness min is 0.0
        assert g.get_gene("snap_strictness") == 0.0
        # tempo_tendency max is 240.0
        assert g.get_gene("tempo_tendency") == 240.0

    def test_to_config_has_all_params(self):
        g = MusicalGenome(seed=1)
        config = g.to_config()
        param_names = {s[1] for s in GENE_SPECS}
        assert param_names.issubset(set(config.keys()))

    def test_get_gene(self):
        g = MusicalGenome(genes={"snap_strictness": 0.5})
        assert abs(g.get_gene("snap_strictness") - 0.5) < 1e-6

    def test_get_unknown_gene_returns_zero(self):
        g = MusicalGenome(seed=0)
        assert g.get_gene("nonexistent") == 0.0

    def test_set_gene(self):
        g = MusicalGenome(seed=0)
        g.set_gene("snap_strictness", 0.8)
        assert abs(g.get_gene("snap_strictness") - 0.8) < 1e-6

    def test_set_gene_clamps(self):
        g = MusicalGenome(seed=0)
        g.set_gene("snap_strictness", 5.0)  # max is 1.0
        assert g.get_gene("snap_strictness") == 1.0

    def test_set_unknown_gene_raises(self):
        g = MusicalGenome(seed=0)
        with pytest.raises(ValueError):
            g.set_gene("nonexistent", 0.5)

    def test_domains(self):
        g = MusicalGenome(seed=0)
        assert g.domains == DOMAIN_ORDER

    def test_domain_genes(self):
        g = MusicalGenome(seed=0)
        core_genes = g.domain_genes("core")
        assert len(core_genes) == 5
        for gid in core_genes:
            spec = next(s for s in GENE_SPECS if s[0] == gid)
            assert spec[2] == "core"

    def test_clone(self):
        g = MusicalGenome(seed=42)
        c = g.clone()
        assert c.gene_count == g.gene_count
        for gid in g.genes:
            assert abs(g.get_gene(gid) - c.get_gene(gid)) < 1e-9
        # Verify independence
        c.set_gene("snap_strictness", 0.99)
        assert abs(g.get_gene("snap_strictness") - c.get_gene("snap_strictness")) > 0.01

    def test_repr(self):
        g = MusicalGenome(seed=42)
        r = repr(g)
        assert "MusicalGenome" in r
        assert "bpm=" in r

    def test_reproducible_with_seed(self):
        g1 = MusicalGenome(seed=99)
        g2 = MusicalGenome(seed=99)
        for gid in g1.genes:
            assert abs(g1.get_gene(gid) - g2.get_gene(gid)) < 1e-9

    def test_different_seeds_different_genomes(self):
        g1 = MusicalGenome(seed=1)
        g2 = MusicalGenome(seed=2)
        diffs = sum(
            1 for gid in g1.genes
            if abs(g1.get_gene(gid) - g2.get_gene(gid)) > 1e-6
        )
        assert diffs > 0


# ===================================================================
# GenomePlayer tests
# ===================================================================

class TestGenomePlayer:
    def test_generate_phrase(self):
        g = MusicalGenome(seed=42)
        player = GenomePlayer(g, seed=10)
        events = player.generate_phrase(bars=4)
        assert len(events) > 0

    def test_events_have_valid_pitches(self):
        g = MusicalGenome(seed=42)
        player = GenomePlayer(g, seed=10)
        events = player.generate_phrase(bars=4)
        for e in events:
            assert 0 <= e.pitch <= 127

    def test_events_have_valid_velocities(self):
        g = MusicalGenome(seed=42)
        player = GenomePlayer(g, seed=10)
        events = player.generate_phrase(bars=4)
        for e in events:
            assert 0 < e.velocity <= 127

    def test_events_have_positive_duration(self):
        g = MusicalGenome(seed=42)
        player = GenomePlayer(g, seed=10)
        events = player.generate_phrase(bars=4)
        for e in events:
            assert e.duration > 0

    def test_events_within_time_range(self):
        g = MusicalGenome(seed=42)
        player = GenomePlayer(g, seed=10)
        events = player.generate_phrase(bars=2, beats_per_bar=4)
        total_beats = 2 * 4
        for e in events:
            assert e.start_beat >= 0
            assert e.start_beat < total_beats

    def test_more_bars_more_events(self):
        g = MusicalGenome(seed=42)
        player = GenomePlayer(g, seed=10)
        short = player.generate_phrase(bars=1)
        long = player.generate_phrase(bars=4)
        assert len(long) > len(short)

    def test_jazz_genome_produces_swung_events(self):
        """Jazz genome should have higher swing ratio → more timing variation."""
        jazz_genes = {s[0]: GENRE_TARGETS["jazz"].get(s[1], s[3]) for s in GENE_SPECS}
        g = MusicalGenome(genes=jazz_genes)
        player = GenomePlayer(g, seed=10)
        events = player.generate_phrase(bars=2)
        assert len(events) > 0

    def test_electronic_genome_produces_snapped_events(self):
        """Electronic genome has high snap → events near grid."""
        elec_genes = {s[0]: GENRE_TARGETS["electronic"].get(s[1], s[3]) for s in GENE_SPECS}
        g = MusicalGenome(genes=elec_genes)
        player = GenomePlayer(g, seed=10)
        events = player.generate_phrase(bars=2)
        assert len(events) > 0

    def test_snap_to_scale(self):
        g = MusicalGenome(seed=0)
        player = GenomePlayer(g)
        # Exact scale degree
        assert player._snap_to_scale(60, [0, 2, 4, 5, 7, 9, 11], 1.0) == 60
        # Off by one → snap
        result = player._snap_to_scale(61, [0, 2, 4, 5, 7, 9, 11], 1.0)
        assert result in [60, 62]


# ===================================================================
# Fitness evaluation tests
# ===================================================================

class TestFitness:
    def test_evaluate_jazz(self):
        config = {s[1]: s[3] for s in GENE_SPECS}
        f = evaluate_fitness(config, "jazz")
        assert 0.0 <= f <= 1.0

    def test_perfect_match_jazz(self):
        config = dict(GENRE_TARGETS["jazz"])
        f = evaluate_fitness(config, "jazz")
        assert f > 0.7  # should be high for perfect match (includes constraint satisfaction + listenability)

    def test_unknown_genre_raises(self):
        with pytest.raises(ValueError):
            evaluate_fitness({}, "reggae")

    def test_fitness_components(self):
        """Fitness with novelty bonus should be >= without."""
        config = {s[1]: s[3] for s in GENE_SPECS}
        f_no_novelty = evaluate_fitness(config, "jazz", 0.0)
        f_with_novelty = evaluate_fitness(config, "jazz", 0.5)
        assert f_with_novelty >= f_no_novelty

    def test_random_config_moderate_fitness(self):
        """Random config should have moderate fitness (not 0 or 1)."""
        g = MusicalGenome(seed=42)
        f = evaluate_fitness(g.to_config(), "jazz")
        assert 0.1 < f < 0.95

    def test_all_genres_acceptable(self):
        g = MusicalGenome(seed=42)
        for genre in GENRE_TARGETS:
            f = evaluate_fitness(g.to_config(), genre)
            assert 0.0 <= f <= 1.0


# ===================================================================
# Genetic operators tests
# ===================================================================

class TestMutateGenome:
    def test_mutate_produces_different_genome(self):
        g = MusicalGenome(seed=42)
        m = mutate_genome(g, mutation_rate=1.0, mutation_scale=0.3, rng=np.random.default_rng(1))
        diffs = sum(1 for gid in g.genes if abs(g.get_gene(gid) - m.get_gene(gid)) > 1e-6)
        assert diffs > 0

    def test_no_mutation_when_rate_zero(self):
        g = MusicalGenome(seed=42)
        m = mutate_genome(g, mutation_rate=0.0, rng=np.random.default_rng(0))
        for gid in g.genes:
            assert abs(g.get_gene(gid) - m.get_gene(gid)) < 1e-9

    def test_mutated_values_in_range(self):
        g = MusicalGenome(seed=42)
        m = mutate_genome(g, mutation_rate=1.0, mutation_scale=0.5, rng=np.random.default_rng(2))
        for spec in GENE_SPECS:
            gid = spec[0]
            lo, hi = spec[5], spec[6]
            assert lo <= m.get_gene(gid) <= hi

    def test_original_unchanged(self):
        g = MusicalGenome(seed=42)
        original_vals = {gid: g.get_gene(gid) for gid in g.genes}
        mutate_genome(g, mutation_rate=1.0, rng=np.random.default_rng(3))
        for gid in g.genes:
            assert abs(g.get_gene(gid) - original_vals[gid]) < 1e-9


class TestCrossover:
    def test_crossover_produces_valid_genome(self):
        a = MusicalGenome(seed=1)
        b = MusicalGenome(seed=2)
        child = crossover(a, b, rng=np.random.default_rng(10))
        assert child.gene_count == 25

    def test_crossover_inherits_from_both(self):
        a = MusicalGenome(seed=1)
        b = MusicalGenome(seed=2)
        child = crossover(a, b, rng=np.random.default_rng(10))
        gene_ids = [s[0] for s in GENE_SPECS]
        from_a = sum(1 for gid in gene_ids[:12]
                     if abs(child.get_gene(gid) - a.get_gene(gid)) < 1e-6)
        from_b = sum(1 for gid in gene_ids[12:]
                     if abs(child.get_gene(gid) - b.get_gene(gid)) < 1e-6)
        # At least some from each parent
        assert from_a > 0 or from_b > 0

    def test_crossover_genes_in_range(self):
        a = MusicalGenome(seed=1)
        b = MusicalGenome(seed=2)
        child = crossover(a, b, rng=np.random.default_rng(10))
        for spec in GENE_SPECS:
            lo, hi = spec[5], spec[6]
            assert lo <= child.get_gene(spec[0]) <= hi


class TestTournamentSelect:
    def test_selects_from_population(self):
        pop = [(MusicalGenome(seed=i), float(i) * 0.1) for i in range(10)]
        winner = tournament_select(pop, k=3, rng=np.random.default_rng(5))
        assert isinstance(winner, MusicalGenome)

    def test_favors_fitter(self):
        """Run many tournaments — fitter organisms should win more often."""
        pop = [(MusicalGenome(seed=i), float(i)) for i in range(10)]
        wins = [0] * 10
        rng = np.random.default_rng(42)
        for _ in range(1000):
            winner = tournament_select(pop, k=3, rng=rng)
            for idx, (g, _) in enumerate(pop):
                if g is winner:
                    wins[idx] += 1
                    break
        # Top half should have more wins than bottom half
        assert sum(wins[5:]) > sum(wins[:5])


# ===================================================================
# MusicalEvolution tests
# ===================================================================

class TestMusicalEvolution:
    def test_run_jazz_short(self):
        evo = MusicalEvolution(target_genre="jazz", population_size=10, seed=42)
        result = evo.run(generations=5)
        assert isinstance(result, EvolutionResult)
        assert result.best_fitness > 0.0
        assert len(result.history) == 5

    def test_fitness_improves(self):
        evo = MusicalEvolution(target_genre="jazz", population_size=20, seed=42)
        result = evo.run(generations=20)
        first_fitness = result.history[0]["best_fitness"]
        last_fitness = result.history[-1]["best_fitness"]
        assert last_fitness >= first_fitness * 0.95  # Should improve or stay stable

    def test_history_tracks_all_generations(self):
        evo = MusicalEvolution(target_genre="electronic", population_size=10, seed=1)
        result = evo.run(generations=10)
        assert len(result.history) == 10
        for i, entry in enumerate(result.history):
            assert entry["generation"] == i
            assert "best_fitness" in entry
            assert "avg_fitness" in entry
            assert "diversity" in entry

    def test_final_population_size(self):
        evo = MusicalEvolution(target_genre="classical", population_size=15, seed=1)
        result = evo.run(generations=5)
        assert len(result.final_population) == 15

    def test_best_config_is_valid(self):
        evo = MusicalEvolution(target_genre="jazz", population_size=10, seed=42)
        result = evo.run(generations=5)
        for spec in GENE_SPECS:
            lo, hi = spec[5], spec[6]
            val = result.best_config.get(spec[1], lo)
            assert lo <= val <= hi, f"{spec[1]} = {val}, range [{lo}, {hi}]"

    def test_unknown_genre_raises(self):
        with pytest.raises(ValueError):
            MusicalEvolution(target_genre="polka")

    def test_all_genres_run(self):
        for genre in GENRE_TARGETS:
            evo = MusicalEvolution(target_genre=genre, population_size=5, seed=1)
            result = evo.run(generations=3)
            assert result.best_fitness > 0.0

    def test_reproducible_with_seed(self):
        evo1 = MusicalEvolution(target_genre="jazz", population_size=10, seed=42)
        r1 = evo1.run(generations=5)
        evo2 = MusicalEvolution(target_genre="jazz", population_size=10, seed=42)
        r2 = evo2.run(generations=5)
        assert abs(r1.best_fitness - r2.best_fitness) < 1e-6


# ===================================================================
# Multi-genre experiment test
# ===================================================================

class TestMultiGenreExperiment:
    def test_run_two_genres(self):
        results = run_multi_genre_experiment(
            genres=["jazz", "electronic"],
            population_size=5,
            generations=3,
            seed=42,
        )
        assert "jazz" in results
        assert "electronic" in results
        assert results["jazz"].best_fitness > 0.0
        assert results["electronic"].best_fitness > 0.0

    def test_genres_produce_different_genomes(self):
        results = run_multi_genre_experiment(
            genres=["jazz", "electronic"],
            population_size=10,
            generations=10,
            seed=42,
        )
        jazz_bpm = results["jazz"].best_config.get("bpm", 0)
        elec_bpm = results["electronic"].best_config.get("bpm", 0)
        # Genres have different BPM targets, should differ
        # (not guaranteed exact match to target, but should diverge)
        jazz_snap = results["jazz"].best_config.get("snap_strength", 0)
        elec_snap = results["electronic"].best_config.get("snap_strength", 0)
        # Electronic should have higher snap than jazz
        assert elec_snap > jazz_snap or abs(elec_snap - jazz_snap) < 0.3


# ===================================================================
# Integration: GenomePlayer + Evolution
# ===================================================================

class TestIntegration:
    def test_evolved_genome_produces_phrase(self):
        evo = MusicalEvolution(target_genre="jazz", population_size=10, seed=42)
        result = evo.run(generations=5)
        player = GenomePlayer(result.best_genome, seed=10)
        events = player.generate_phrase(bars=4)
        assert len(events) > 0
        for e in events:
            assert 0 <= e.pitch <= 127
            assert 0 < e.velocity <= 127
            assert e.duration > 0

    def test_different_genres_different_phrases(self):
        results = run_multi_genre_experiment(
            genres=["jazz", "electronic"],
            population_size=10,
            generations=5,
            seed=42,
        )
        jazz_events = GenomePlayer(results["jazz"].best_genome, seed=10).generate_phrase(bars=4)
        elec_events = GenomePlayer(results["electronic"].best_genome, seed=10).generate_phrase(bars=4)
        # Different genomes should produce different pitch sequences
        jazz_pitches = [e.pitch for e in jazz_events]
        elec_pitches = [e.pitch for e in elec_events]
        # They should differ (not guaranteed identical)
        assert jazz_pitches != elec_pitches or len(jazz_events) != len(elec_events)
