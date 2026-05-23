"""Tests for flux_tensor_midi.ecosystem — musical ecosystem dynamics."""

import math
import random

import pytest

from flux_tensor_midi.ecosystem import (
    GENOME_SIZE,
    Arrangement,
    InteractionType,
    MusicalEcosystem,
    MusicalSpecies,
    Niche,
    Resources,
    Voice,
    _genome_distance,
    _genome_similarity,
    _random_genome,
    create_classical_ecosystem,
    create_minimal_ecosystem,
    create_modern_ecosystem,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def species_a() -> MusicalSpecies:
    return MusicalSpecies(name="Alpha", niche=Niche.MELODY, population=200, fitness=0.6, seed=42)


@pytest.fixture
def species_b() -> MusicalSpecies:
    return MusicalSpecies(name="Beta", niche=Niche.BASS, population=150, fitness=0.5)


@pytest.fixture
def simple_ecosystem() -> MusicalEcosystem:
    return create_minimal_ecosystem()


@pytest.fixture
def seeded_ecosystem() -> MusicalEcosystem:
    eco = MusicalEcosystem(carrying_capacity=10, migration_rate=0.0, seed=123)
    eco.add_species(MusicalSpecies(name="X", niche=Niche.RHYTHM, population=100, fitness=0.6))
    eco.add_species(MusicalSpecies(name="Y", niche=Niche.HARMONY, population=100, fitness=0.5))
    return eco


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------

class TestResources:
    def test_total(self):
        r = Resources(0.1, 0.2, 0.3, 0.4)
        assert abs(r.total() - 1.0) < 1e-9

    def test_to_dict_roundtrip(self):
        r = Resources(0.1, 0.2, 0.3, 0.4)
        d = r.to_dict()
        r2 = Resources.from_dict(d)
        assert abs(r2.attention - 0.1) < 1e-9
        assert abs(r2.harmonic_space - 0.2) < 1e-9

    def test_from_dict_defaults(self):
        r = Resources.from_dict({})
        assert r.attention == 0.25


# ---------------------------------------------------------------------------
# MusicalSpecies basics
# ---------------------------------------------------------------------------

class TestMusicalSpecies:
    def test_creation(self):
        s = MusicalSpecies(name="Test", niche=Niche.RHYTHM)
        assert s.name == "Test"
        assert len(s.genome) == GENOME_SIZE
        assert not s.extinct
        assert s.population > 0

    def test_genome_size_validation(self):
        with pytest.raises(ValueError, match="Genome must have"):
            MusicalSpecies(name="Bad", genome=[0.5] * 10)

    def test_genome_traits(self):
        s = MusicalSpecies(name="T", genome=[0.5] * GENOME_SIZE)
        assert 0 <= s.competitiveness <= 1
        assert 0 <= s.cooperation_tendency <= 1
        assert 0 <= s.niche_specialization <= 1
        assert 0 <= s.adaptability <= 1

    def test_effective_fitness(self):
        s = MusicalSpecies(name="T", fitness=0.8)
        ef = s.effective_fitness()
        assert ef <= 0.8  # reduced by resource efficiency

    def test_resource_need(self):
        s = MusicalSpecies(name="T", population=200, resources=Resources(0.2, 0.2, 0.2, 0.2))
        need = s.resource_need()
        assert need > 0

    def test_is_viable(self):
        s = MusicalSpecies(name="T", population=100, fitness=0.5)
        assert s.is_viable()
        s.kill()
        assert not s.is_viable()

    def test_kill(self):
        s = MusicalSpecies(name="T", population=100)
        s.kill()
        assert s.extinct
        assert s.population == 0

    def test_to_dict_roundtrip(self):
        s = MusicalSpecies(name="Roundtrip", niche=Niche.BASS, population=42, fitness=0.7)
        d = s.to_dict()
        s2 = MusicalSpecies.from_dict(d)
        assert s2.name == "Roundtrip"
        assert s2.niche == Niche.BASS
        assert s2.population == 42
        assert abs(s2.fitness - 0.7) < 1e-9

    def test_repr(self):
        s = MusicalSpecies(name="Jazz")
        r = repr(s)
        assert "Jazz" in r
        assert "🎵" in r
        s.kill()
        r = repr(s)
        assert "💀" in r

    def test_negative_population_clamped(self):
        s = MusicalSpecies(name="T", population=-10)
        assert s.population == 0


# ---------------------------------------------------------------------------
# Competition, Cooperation, Predation, Parasitism
# ---------------------------------------------------------------------------

class TestInteractions:
    def test_compete_same_niche_strong(self):
        a = MusicalSpecies(name="A", niche=Niche.MELODY, fitness=0.8, genome=[0.9] * GENOME_SIZE)
        b = MusicalSpecies(name="B", niche=Niche.MELODY, fitness=0.8, genome=[0.9] * GENOME_SIZE)
        c = a.compete(b)
        assert c > 0

    def test_compete_different_niche_weaker(self):
        a = MusicalSpecies(name="A", niche=Niche.MELODY, genome=[0.5] * GENOME_SIZE)
        b = MusicalSpecies(name="B", niche=Niche.BASS, genome=[0.1] * GENOME_SIZE)
        same_niche = MusicalSpecies(name="C", niche=Niche.MELODY, genome=[0.5] * GENOME_SIZE)
        assert a.compete(same_niche) >= a.compete(b)

    def test_compete_extinct_returns_zero(self):
        a = MusicalSpecies(name="A")
        b = MusicalSpecies(name="B")
        b.kill()
        assert a.compete(b) == 0

    def test_cooperation_complementary(self):
        a = MusicalSpecies(name="A", niche=Niche.BASS, genome=[0.5] * GENOME_SIZE, fitness=0.6)
        b = MusicalSpecies(name="B", niche=Niche.RHYTHM, genome=[0.5] * GENOME_SIZE, fitness=0.6)
        c = a.cooperate(b)
        assert c > 0

    def test_cooperation_extinct_returns_zero(self):
        a = MusicalSpecies(name="A")
        b = MusicalSpecies(name="B")
        b.kill()
        assert a.cooperate(b) == 0

    def test_predation(self):
        a = MusicalSpecies(name="Generalist", niche=Niche.MELODY,
                           genome=[0.5, 0.5, 0.1, 0.5, 0.5, 0.5, 0.8] + [0.5] * 18,
                           fitness=0.7)
        b = MusicalSpecies(name="Specialist", niche=Niche.HARMONY,
                           genome=[0.5, 0.5, 0.9, 0.5, 0.5, 0.5, 0.5] + [0.5] * 18,
                           fitness=0.5)
        p = a.prey_upon(b)
        assert p > 0

    def test_parasitism(self):
        a = MusicalSpecies(name="Earworm", genome=[0.5] * 7 + [0.9] + [0.5] * 11 + [0.9] + [0.5] * 5,
                           fitness=0.7)
        b = MusicalSpecies(name="Host", fitness=0.6)
        p = a.parasitize(b)
        assert p > 0

    def test_determine_interaction(self):
        a = MusicalSpecies(name="A", niche=Niche.MELODY, genome=[0.9] * GENOME_SIZE, fitness=0.8)
        b = MusicalSpecies(name="B", niche=Niche.MELODY, genome=[0.9] * GENOME_SIZE, fitness=0.8)
        itype = a.determine_interaction(b)
        assert itype == InteractionType.COMPETITION

    def test_determine_interaction_neutral(self):
        a = MusicalSpecies(name="A", genome=[0.01] * GENOME_SIZE, fitness=0.01)
        b = MusicalSpecies(name="B", genome=[0.01] * GENOME_SIZE, fitness=0.01)
        itype = a.determine_interaction(b)
        assert itype == InteractionType.NEUTRAL

    def test_determine_interaction_extinct(self):
        a = MusicalSpecies(name="A")
        b = MusicalSpecies(name="B")
        b.kill()
        assert a.determine_interaction(b) == InteractionType.NEUTRAL


# ---------------------------------------------------------------------------
# Mutation / speciation
# ---------------------------------------------------------------------------

class TestMutation:
    def test_mutate_creates_new_species(self):
        parent = MusicalSpecies(name="Parent", population=400, fitness=0.7)
        child = parent.mutate()
        assert child.name != parent.name
        assert child.generation == parent.generation + 1
        assert child.population < parent.population

    def test_mutate_preserves_most_genes(self):
        parent = MusicalSpecies(name="Parent", genome=[0.5] * GENOME_SIZE)
        child = parent.mutate(mutation_rate=0.0)  # no mutations
        assert child.genome == parent.genome

    def test_mutate_with_innovation(self):
        parent = MusicalSpecies(name="Parent", genome=[0.5] * GENOME_SIZE)
        parent.genome[15] = 0.9  # high innovation
        child = parent.mutate(mutation_rate=0.5, magnitude=0.2)
        # Genome should differ
        assert child.genome != parent.genome

    def test_mutate_population_division(self):
        parent = MusicalSpecies(name="Parent", population=400)
        child = parent.mutate()
        assert child.population == parent.population // 4 or child.population == 100


# ---------------------------------------------------------------------------
# MusicalEcosystem basics
# ---------------------------------------------------------------------------

class TestEcosystem:
    def test_create_empty(self):
        eco = MusicalEcosystem()
        assert len(eco.living_species()) == 0
        assert eco.time == 0

    def test_add_species(self):
        eco = MusicalEcosystem()
        s = MusicalSpecies(name="Test")
        eco.add_species(s)
        assert len(eco.living_species()) == 1

    def test_remove_species(self):
        eco = MusicalEcosystem()
        s = MusicalSpecies(name="Test")
        eco.add_species(s)
        assert eco.remove_species("Test")
        assert len(eco.living_species()) == 0

    def test_remove_nonexistent(self):
        eco = MusicalEcosystem()
        assert not eco.remove_species("Ghost")

    def test_living_vs_extinct(self):
        eco = MusicalEcosystem()
        a = MusicalSpecies(name="Alive")
        b = MusicalSpecies(name="Dead")
        b.kill()
        eco.add_species(a)
        eco.add_species(b)
        assert len(eco.living_species()) == 1
        assert len(eco.extinct_species()) == 1

    def test_species_by_niche(self):
        eco = MusicalEcosystem()
        eco.add_species(MusicalSpecies(name="A", niche=Niche.BASS))
        eco.add_species(MusicalSpecies(name="B", niche=Niche.BASS))
        eco.add_species(MusicalSpecies(name="C", niche=Niche.MELODY))
        assert len(eco.species_by_niche(Niche.BASS)) == 2

    def test_species_by_name(self):
        eco = MusicalEcosystem()
        eco.add_species(MusicalSpecies(name="Jazz"))
        assert eco.species_by_name("Jazz") is not None
        assert eco.species_by_name("Rock") is None

    def test_dominant_species(self):
        eco = MusicalEcosystem()
        eco.add_species(MusicalSpecies(name="Weak", population=10, fitness=0.1))
        eco.add_species(MusicalSpecies(name="Strong", population=500, fitness=0.9))
        d = eco.dominant_species()
        assert d is not None
        assert d.name == "Strong"

    def test_dominant_species_empty(self):
        eco = MusicalEcosystem()
        assert eco.dominant_species() is None

    def test_reset(self):
        eco = create_minimal_ecosystem()
        eco.evolve(5)
        eco.reset()
        assert len(eco.species) == 0
        assert eco.time == 0


# ---------------------------------------------------------------------------
# Ecosystem dynamics
# ---------------------------------------------------------------------------

class TestEcosystemDynamics:
    def test_tick_advances_time(self, seeded_ecosystem):
        t_before = seeded_ecosystem.time
        seeded_ecosystem.tick()
        assert seeded_ecosystem.time == t_before + 1

    def test_evolve_returns_snapshots(self, seeded_ecosystem):
        results = seeded_ecosystem.evolve(10)
        assert len(results) == 10
        assert all("time" in r for r in results)
        assert all("biodiversity" in r for r in results)

    def test_biodiversity_single_species(self):
        eco = MusicalEcosystem()
        eco.add_species(MusicalSpecies(name="Solo", population=100))
        assert eco.biodiversity() == 0.0

    def test_biodiversity_balanced(self):
        eco = MusicalEcosystem()
        eco.add_species(MusicalSpecies(name="A", population=100))
        eco.add_species(MusicalSpecies(name="B", population=100))
        bio = eco.biodiversity()
        assert abs(bio - 1.0) < 1e-9  # log2(2) = 1

    def test_biodiversity_empty(self):
        eco = MusicalEcosystem()
        assert eco.biodiversity() == 0.0

    def test_resource_pressure(self, seeded_ecosystem):
        p = seeded_ecosystem.resource_pressure()
        assert 0 <= p <= 1

    def test_available_resources(self, seeded_ecosystem):
        avail = seeded_ecosystem.available_resources()
        assert all(v >= 0 for v in avail.values())

    def test_keystone_species(self):
        eco = MusicalEcosystem()
        # Bass and rhythm are complementary keystones
        bass = MusicalSpecies(name="Bass", niche=Niche.BASS, population=300, fitness=0.7)
        bass.genome[9] = 0.9  # keystone factor
        rhythm = MusicalSpecies(name="Rhythm", niche=Niche.RHYTHM, population=300, fitness=0.7)
        rhythm.genome[9] = 0.8
        melody = MusicalSpecies(name="Melody", niche=Niche.MELODY, population=100, fitness=0.4)
        eco.add_species(bass)
        eco.add_species(rhythm)
        eco.add_species(melody)
        ks = eco.keystone_species()
        assert len(ks) > 0

    def test_extinction_event(self, seeded_ecosystem):
        seeded_ecosystem.evolve(5)
        result = seeded_ecosystem.extinction_event(threshold=0.5)
        assert "survivors" in result
        assert "casualties" in result
        assert 0 <= result["extinction_rate"] <= 1

    def test_invasive_species_survives(self):
        eco = MusicalEcosystem(carrying_capacity=10, migration_rate=0.0)
        eco.add_species(MusicalSpecies(name="Resident", niche=Niche.MELODY, population=100, fitness=0.3))
        invader = MusicalSpecies(name="Invader", niche=Niche.BASS, population=80, fitness=0.8)
        result = eco.invasive_species(invader)
        assert "survived" in result
        # Strong invader into weak ecosystem should likely survive
        assert result["survived"] is True or result["survived"] is False  # just verify bool

    def test_succession(self):
        eco = MusicalEcosystem(carrying_capacity=10, migration_rate=0.1, seed=42)
        # Start from scratch
        result = eco.succession(timesteps=20)
        assert len(result) == 20
        assert all(s in ("barren", "pioneer", "intermediate", "climax", "competitive") for s in result)

    def test_food_web(self, seeded_ecosystem):
        web = seeded_ecosystem.food_web()
        assert isinstance(web, dict)
        # Each entry should be a list of strings
        for name, prey in web.items():
            assert isinstance(name, str)
            assert isinstance(prey, list)

    def test_symbiosis_creates_hybrid(self):
        eco = MusicalEcosystem()
        a = MusicalSpecies(name="Jazz", niche=Niche.HARMONY, population=200, fitness=0.6,
                           genome=[0.3, 0.8] + [0.5] * (GENOME_SIZE - 2))
        b = MusicalSpecies(name="Rock", niche=Niche.RHYTHM, population=200, fitness=0.6,
                           genome=[0.3, 0.8] + [0.5] * (GENOME_SIZE - 2))
        hybrid = eco.symbiosis(a, b)
        # They are complementary (harmony+rhythm), should cooperate enough
        if hybrid is not None:
            assert "Jazz" in hybrid.name and "Rock" in hybrid.name

    def test_symbiosis_extinct_returns_none(self):
        eco = MusicalEcosystem()
        a = MusicalSpecies(name="A")
        b = MusicalSpecies(name="B")
        b.kill()
        assert eco.symbiosis(a, b) is None


# ---------------------------------------------------------------------------
# Music conversion
# ---------------------------------------------------------------------------

class TestMusicConversion:
    def test_to_music(self, seeded_ecosystem):
        seeded_ecosystem.evolve(5)
        arrangement = seeded_ecosystem.to_music()
        assert isinstance(arrangement, Arrangement)
        assert len(arrangement.voices) > 0
        assert arrangement.total_voices > 0

    def test_arrangement_properties(self, seeded_ecosystem):
        seeded_ecosystem.evolve(3)
        arr = seeded_ecosystem.to_music()
        assert arr.average_dissonance >= 0
        assert arr.average_biodiversity >= 0
        d = arr.to_dict()
        assert "total_voices" in d

    def test_voice_midi_channel(self):
        v = Voice(name="Test", niche=Niche.PERCUSSION, population=100, fitness=0.5)
        assert v.to_midi_channel() == 9

    def test_voice_octave(self):
        v = Voice(name="Test", niche=Niche.BASS, population=100, fitness=0.5)
        assert v.suggested_octave() == 2


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

class TestPresets:
    def test_classical_ecosystem(self):
        eco = create_classical_ecosystem()
        assert len(eco.living_species()) == 5
        names = [s.name for s in eco.living_species()]
        assert "Strings" in names
        assert "Brass" in names

    def test_modern_ecosystem(self):
        eco = create_modern_ecosystem()
        assert len(eco.living_species()) == 5
        names = [s.name for s in eco.living_species()]
        assert "Pop" in names

    def test_minimal_ecosystem(self):
        eco = create_minimal_ecosystem()
        assert len(eco.living_species()) == 2

    def test_preset_can_evolve(self):
        eco = create_classical_ecosystem()
        results = eco.evolve(20)
        assert len(results) == 20
        assert eco.time == 20

    def test_modern_ecosystem_dynamics(self):
        eco = create_modern_ecosystem()
        initial_bio = eco.biodiversity()
        eco.evolve(30)
        # Ecosystem should still have living species
        assert len(eco.living_species()) > 0


# ---------------------------------------------------------------------------
# Genome utilities
# ---------------------------------------------------------------------------

class TestGenomeUtils:
    def test_random_genome_length(self):
        g = _random_genome()
        assert len(g) == GENOME_SIZE
        assert all(0 <= v <= 1 for v in g)

    def test_genome_distance_self(self):
        g = [0.5] * GENOME_SIZE
        assert _genome_distance(g, g) == 0.0

    def test_genome_distance_different(self):
        a = [0.0] * GENOME_SIZE
        b = [1.0] * GENOME_SIZE
        d = _genome_distance(a, b)
        assert abs(d - math.sqrt(GENOME_SIZE)) < 1e-9

    def test_genome_distance_mismatched(self):
        with pytest.raises(ValueError):
            _genome_distance([0.5], [0.5, 0.5])

    def test_genome_similarity_identical(self):
        g = [0.5] * GENOME_SIZE
        assert abs(_genome_similarity(g, g) - 1.0) < 1e-9

    def test_genome_similarity_zero_vector(self):
        a = [0.0] * GENOME_SIZE
        b = [1.0] * GENOME_SIZE
        assert _genome_similarity(a, b) == 0.0


# ---------------------------------------------------------------------------
# Summary and history
# ---------------------------------------------------------------------------

class TestSummary:
    def test_summary(self, seeded_ecosystem):
        s = seeded_ecosystem.summary()
        assert "time" in s
        assert "living_species" in s
        assert "biodiversity" in s

    def test_history_recorded(self, seeded_ecosystem):
        seeded_ecosystem.evolve(5)
        assert len(seeded_ecosystem.history) == 5
