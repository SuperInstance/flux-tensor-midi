"""
Musical Ecosystem — ecological dynamics mapped to music.

Species (genres) compete for finite resources:
- Listener attention
- Harmonic space (frequency bands)
- Temporal space (rhythmic niches)
- Emotional bandwidth (affect categories)

Ecological dynamics:
- Competition: similar genres compete (jazz vs smooth jazz)
- Mutualism: complementary genres help each other (drums + bass)
- Predation: dominant genres "eat" weaker ones (pop displaces folk)
- Parasitism: genres that take without giving (earworms)
- Symbiosis: genres that merge (jazz + rock = fusion)

NON-PRE-CALCULABLE: the ecosystem evolves based on ALL species' interactions.
You cannot predict the outcome from any single species alone.
"""

from __future__ import annotations

import copy
import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums & type helpers
# ---------------------------------------------------------------------------

class Niche(Enum):
    """Ecological niches in the musical ecosystem."""
    RHYTHM = "rhythm"
    BASS = "bass"
    HARMONY = "harmony"
    MELODY = "melody"
    TEXTURE = "texture"
    PERCUSSION = "percussion"
    AMBIENT = "ambient"
    VOCAL = "vocal"


class ResourceType(Enum):
    """Finite resources species compete for."""
    ATTENTION = "attention"
    HARMONIC_SPACE = "harmonic_space"
    TEMPORAL_SPACE = "temporal_space"
    EMOTIONAL_BANDWIDTH = "emotional_bandwidth"


class InteractionType(Enum):
    """Types of ecological interaction."""
    COMPETITION = "competition"
    MUTUALISM = "mutualism"
    PREDATION = "predation"
    PARASITISM = "parasitism"
    COMMENSALISM = "commensalism"
    NEUTRAL = "neutral"


@dataclass
class Resources:
    """What a species needs to survive."""
    attention: float = 0.25
    harmonic_space: float = 0.25
    temporal_space: float = 0.25
    emotional_bandwidth: float = 0.25

    def total(self) -> float:
        return self.attention + self.harmonic_space + self.temporal_space + self.emotional_bandwidth

    def to_dict(self) -> dict[str, float]:
        return {
            "attention": self.attention,
            "harmonic_space": self.harmonic_space,
            "temporal_space": self.temporal_space,
            "emotional_bandwidth": self.emotional_bandwidth,
        }

    @staticmethod
    def from_dict(d: dict[str, float]) -> Resources:
        return Resources(
            attention=d.get("attention", 0.25),
            harmonic_space=d.get("harmonic_space", 0.25),
            temporal_space=d.get("temporal_space", 0.25),
            emotional_bandwidth=d.get("emotional_bandwidth", 0.25),
        )


@dataclass
class Interaction:
    """Record of an interaction between two species."""
    species_a: str
    species_b: str
    interaction_type: InteractionType
    strength: float
    timestep: int


# ---------------------------------------------------------------------------
# Genome utilities
# ---------------------------------------------------------------------------

GENOME_SIZE = 25
MUTATION_RATE = 0.15
MUTATION_MAGNITUDE = 0.1


def _random_genome() -> list[float]:
    """Generate a random genome of GENOME_SIZE values in [0, 1]."""
    return [random.random() for _ in range(GENOME_SIZE)]


def _genome_distance(a: list[float], b: list[float]) -> float:
    """Euclidean distance between two genomes."""
    if len(a) != len(b):
        raise ValueError("Genomes must be the same length")
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _genome_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two genomes."""
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# MusicalSpecies
# ---------------------------------------------------------------------------

class MusicalSpecies:
    """A genre/system that competes in the ecosystem.

    Each species has a genome of 25 constraint genes that determine its
    ecological characteristics: resource needs, competitiveness, niche
    specialization, etc.
    """

    def __init__(
        self,
        name: str,
        genome: Optional[list[float]] = None,
        niche: Niche = Niche.MELODY,
        population: int = 100,
        fitness: float = 0.5,
        resources: Optional[Resources] = None,
        uid: Optional[str] = None,
    ):
        self.name = name
        self.genome: list[float] = genome if genome is not None else _random_genome()
        if len(self.genome) != GENOME_SIZE:
            raise ValueError(f"Genome must have {GENOME_SIZE} genes, got {len(self.genome)}")
        self.niche = niche
        self.population = max(0, population)
        self.fitness = _clamp(fitness)
        self.resources = resources if resources is not None else Resources()
        self.uid = uid or str(uuid.uuid4())[:8]
        self.age = 0
        self.generation = 0
        self.extinct = False

    # -- genome-derived traits -----------------------------------------------

    @property
    def competitiveness(self) -> float:
        """How aggressive this species is in competing."""
        return self.genome[0]

    @property
    def cooperation_tendency(self) -> float:
        """How likely to cooperate with others."""
        return self.genome[1]

    @property
    def niche_specialization(self) -> float:
        """How tightly adapted to its niche (0=generalist, 1=specialist)."""
        return self.genome[2]

    @property
    def adaptability(self) -> float:
        """How well it adapts to changing environments."""
        return self.genome[3]

    @property
    def reproduction_rate(self) -> float:
        """Base reproduction rate."""
        return 0.3 + 0.7 * self.genome[4]

    @property
    def dispersal(self) -> float:
        """How far this species can spread."""
        return self.genome[5]

    @property
    def predation_strength(self) -> float:
        """How strongly it preys on weaker species."""
        return self.genome[6]

    @property
    def parasitism_tendency(self) -> float:
        """Tendency toward parasitic behavior."""
        return self.genome[7]

    @property
    def resilience(self) -> float:
        """Ability to survive resource scarcity."""
        return self.genome[8]

    @property
    def keystone_factor(self) -> float:
        """How critical this species is to ecosystem stability."""
        return self.genome[9]

    @property
    def resource_efficiency(self) -> float:
        """How efficiently it uses resources."""
        return 0.2 + 0.8 * self.genome[10]

    @property
    def cultural_momentum(self) -> float:
        """How much momentum/popularity this species has."""
        return self.genome[11]

    @property
    def harmonic_affinity(self) -> float:
        """Preference for harmonic resources."""
        return self.genome[12]

    @property
    def rhythmic_affinity(self) -> float:
        """Preference for temporal/rhythmic resources."""
        return self.genome[13]

    @property
    def emotional_depth(self) -> float:
        """How much emotional bandwidth it uses."""
        return self.genome[14]

    @property
    def innovation(self) -> float:
        """Tendency toward novel mutations."""
        return self.genome[15]

    @property
    def stealth(self) -> float:
        """How well it avoids predation."""
        return self.genome[16]

    # -- ecological interactions ---------------------------------------------

    def compete(self, other: MusicalSpecies) -> float:
        """Lotka-Volterra competition: how much does *other* reduce fitness?

        Competition is stronger when species are similar (niche overlap)
        and when both have high competitiveness.
        Returns a value in [0, 1]: 0=no competition, 1=max competition.
        """
        if self.extinct or other.extinct:
            return 0.0

        # Niche overlap
        niche_overlap = 1.0 if self.niche == other.niche else (
            0.3 * _genome_similarity(self.genome, other.genome)
        )

        # Competitive effect proportional to other's competitiveness and similarity
        effect = other.competitiveness * niche_overlap * other.fitness
        return _clamp(effect)

    def cooperate(self, other: MusicalSpecies) -> float:
        """Mutualism: how much does *other* increase fitness?

        Cooperation is stronger when species are in complementary niches
        and both have high cooperation tendency.
        """
        if self.extinct or other.extinct:
            return 0.0

        # Complementary niches cooperate more
        niche_bonus = 0.0
        complementary_pairs = {
            (Niche.BASS, Niche.RHYTHM), (Niche.RHYTHM, Niche.BASS),
            (Niche.HARMONY, Niche.MELODY), (Niche.MELODY, Niche.HARMONY),
            (Niche.PERCUSSION, Niche.BASS), (Niche.BASS, Niche.PERCUSSION),
            (Niche.AMBIENT, Niche.MELODY), (Niche.MELODY, Niche.AMBIENT),
            (Niche.VOCAL, Niche.HARMONY), (Niche.HARMONY, Niche.VOCAL),
            (Niche.TEXTURE, Niche.AMBIENT), (Niche.AMBIENT, Niche.TEXTURE),
            (Niche.RHYTHM, Niche.MELODY), (Niche.MELODY, Niche.RHYTHM),
        }
        if (self.niche, other.niche) in complementary_pairs:
            niche_bonus = 0.5

        # Cooperation from both sides
        coop = (self.cooperation_tendency + other.cooperation_tendency) / 2
        effect = coop * (0.3 + niche_bonus) * other.fitness
        return _clamp(effect)

    def prey_upon(self, other: MusicalSpecies) -> float:
        """Predation: how much does this species exploit *other*.

        Predation is stronger when this species is a generalist
        (low specialization) and the other is a specialist (high specialization).
        """
        if self.extinct or other.extinct:
            return 0.0

        # Generalists prey on specialists
        generalist_factor = 1.0 - self.niche_specialization
        specialist_vulnerability = other.niche_specialization

        effect = self.predation_strength * generalist_factor * specialist_vulnerability * self.fitness
        return _clamp(effect)

    def parasitize(self, other: MusicalSpecies) -> float:
        """Parasitism: extract resources from *other* without reciprocating.

        Like an earworm: catchy, extracts attention, gives little back.
        """
        if self.extinct or other.extinct:
            return 0.0

        effect = self.parasitism_tendency * self.cultural_momentum * other.fitness
        return _clamp(effect)

    def determine_interaction(self, other: MusicalSpecies) -> InteractionType:
        """Classify the interaction type with another species."""
        if self.extinct or other.extinct:
            return InteractionType.NEUTRAL

        competition = self.competete_raw(other)
        cooperation = self.cooperate_raw(other)
        predation = self.prey_upon_raw(other)
        parasitism = self.parasitize_raw(other)

        scores = {
            InteractionType.COMPETITION: competition,
            InteractionType.MUTUALISM: cooperation,
            InteractionType.PREDATION: predation,
            InteractionType.PARASITISM: parasitism,
        }

        best = max(scores, key=scores.get)  # type: ignore[arg-type]
        if scores[best] < 0.05:
            return InteractionType.NEUTRAL
        return best

    # raw versions that don't check extinct (for internal use)
    def competete_raw(self, other: MusicalSpecies) -> float:
        niche_overlap = 1.0 if self.niche == other.niche else (
            0.3 * _genome_similarity(self.genome, other.genome)
        )
        return other.competitiveness * niche_overlap * other.fitness

    def cooperate_raw(self, other: MusicalSpecies) -> float:
        niche_bonus = 0.0
        complementary_pairs = {
            (Niche.BASS, Niche.RHYTHM), (Niche.RHYTHM, Niche.BASS),
            (Niche.HARMONY, Niche.MELODY), (Niche.MELODY, Niche.HARMONY),
            (Niche.PERCUSSION, Niche.BASS), (Niche.BASS, Niche.PERCUSSION),
            (Niche.AMBIENT, Niche.MELODY), (Niche.MELODY, Niche.AMBIENT),
            (Niche.VOCAL, Niche.HARMONY), (Niche.HARMONY, Niche.VOCAL),
            (Niche.TEXTURE, Niche.AMBIENT), (Niche.AMBIENT, Niche.TEXTURE),
            (Niche.RHYTHM, Niche.MELODY), (Niche.MELODY, Niche.RHYTHM),
        }
        if (self.niche, other.niche) in complementary_pairs:
            niche_bonus = 0.5
        coop = (self.cooperation_tendency + other.cooperation_tendency) / 2
        return coop * (0.3 + niche_bonus) * other.fitness

    def prey_upon_raw(self, other: MusicalSpecies) -> float:
        generalist_factor = 1.0 - self.niche_specialization
        specialist_vulnerability = other.niche_specialization
        return self.predation_strength * generalist_factor * specialist_vulnerability * self.fitness

    def parasitize_raw(self, other: MusicalSpecies) -> float:
        return self.parasitism_tendency * self.cultural_momentum * other.fitness

    # -- evolution -----------------------------------------------------------

    def mutate(self, mutation_rate: float = MUTATION_RATE,
               magnitude: float = MUTATION_MAGNITUDE) -> MusicalSpecies:
        """Speciation: create a new species from mutation."""
        new_genome = []
        for gene in self.genome:
            if random.random() < mutation_rate * (1.0 + self.innovation):
                delta = random.gauss(0, magnitude)
                new_genome.append(_clamp(gene + delta))
            else:
                new_genome.append(gene)

        # Possibly shift niche
        niches = list(Niche)
        new_niche = self.niche
        if random.random() < 0.1 * self.dispersal:
            new_niche = random.choice(niches)

        child = MusicalSpecies(
            name=f"{self.name}_offspring_{self.uid[:4]}",
            genome=new_genome,
            niche=new_niche,
            population=max(1, self.population // 4),
            fitness=self.fitness * random.uniform(0.8, 1.2),
            resources=Resources(
                attention=_clamp(self.resources.attention * random.uniform(0.7, 1.3)),
                harmonic_space=_clamp(self.resources.harmonic_space * random.uniform(0.7, 1.3)),
                temporal_space=_clamp(self.resources.temporal_space * random.uniform(0.7, 1.3)),
                emotional_bandwidth=_clamp(self.resources.emotional_bandwidth * random.uniform(0.7, 1.3)),
            ),
        )
        child.generation = self.generation + 1
        return child

    def effective_fitness(self) -> float:
        """Fitness adjusted for age and resource efficiency."""
        age_penalty = max(0, 1.0 - 0.01 * self.age)
        efficiency = self.resource_efficiency
        return self.fitness * age_penalty * efficiency

    def resource_need(self) -> float:
        """Total resource need of this species."""
        return self.resources.total() * self.population / 100.0

    def is_viable(self) -> bool:
        """Is this species still viable?"""
        return not self.extinct and self.population > 0 and self.fitness > 0.01

    def kill(self):
        """Mark this species as extinct."""
        self.extinct = True
        self.population = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "uid": self.uid,
            "genome": self.genome,
            "niche": self.niche.value,
            "population": self.population,
            "fitness": self.fitness,
            "resources": self.resources.to_dict(),
            "age": self.age,
            "generation": self.generation,
            "extinct": self.extinct,
            "effective_fitness": self.effective_fitness(),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> MusicalSpecies:
        s = MusicalSpecies(
            name=d["name"],
            genome=d["genome"],
            niche=Niche(d.get("niche", "melody")),
            population=d.get("population", 100),
            fitness=d.get("fitness", 0.5),
            resources=Resources.from_dict(d.get("resources", {})),
            uid=d.get("uid"),
        )
        s.age = d.get("age", 0)
        s.generation = d.get("generation", 0)
        s.extinct = d.get("extinct", False)
        return s

    def __repr__(self) -> str:
        status = "💀" if self.extinct else "🎵"
        return f"{status} {self.name} (pop={self.population}, fit={self.fitness:.3f}, niche={self.niche.value})"


# ---------------------------------------------------------------------------
# MusicalEcosystem
# ---------------------------------------------------------------------------

class MusicalEcosystem:
    """An ecosystem of musical species.

    Species (genres) compete for:
    - Listener attention (finite resource)
    - Harmonic space (frequency bands)
    - Temporal space (rhythmic niches)
    - Emotional bandwidth (affect categories)

    NON-PRE-CALCULABLE: the ecosystem evolves based on ALL species' interactions.
    """

    def __init__(
        self,
        species: Optional[list[MusicalSpecies]] = None,
        total_attention: float = 1.0,
        total_harmonic_space: float = 1.0,
        total_temporal_space: float = 1.0,
        total_emotional_bandwidth: float = 1.0,
        carrying_capacity: int = 20,
        migration_rate: float = 0.05,
        extinction_threshold: float = 5,
        speciation_threshold: float = 0.7,
        seed: Optional[int] = None,
        epsilon: float = 0.5,
        immigration_rate: float = 0.1,
        kill_the_winner_strength: float = 0.15,
    ):
        if seed is not None:
            random.seed(seed)

        self.species: list[MusicalSpecies] = species or []
        self.environment: dict[str, float] = {
            "attention": total_attention,
            "harmonic_space": total_harmonic_space,
            "temporal_space": total_temporal_space,
            "emotional_bandwidth": total_emotional_bandwidth,
        }
        self.carrying_capacity = carrying_capacity
        self.migration_rate = migration_rate
        self.extinction_threshold = extinction_threshold
        self.speciation_threshold = speciation_threshold
        self.epsilon = _clamp(epsilon, 0.0, 1.0)
        self.immigration_rate = immigration_rate
        self.kill_the_winner_strength = kill_the_winner_strength
        self.time = 0
        self.history: list[dict[str, Any]] = []
        self.interactions: list[Interaction] = []

    # -- niche partitioning --------------------------------------------------

    @staticmethod
    def niche_overlap(s1: MusicalSpecies, s2: MusicalSpecies) -> float:
        """Compute genome-based niche overlap between two species.

        Returns a value in [0, 1]:
        - 0 = completely different niches, no competition
        - 1 = identical niche, direct competition

        Uses cosine similarity of genomes to measure how much
        ecological overlap exists.
        """
        if s1.extinct or s2.extinct:
            return 0.0
        return _genome_similarity(s1.genome, s2.genome)

    # -- resource management -------------------------------------------------

    def available_resources(self) -> dict[str, float]:
        """Resources remaining after current consumption."""
        consumed = {
            "attention": 0.0,
            "harmonic_space": 0.0,
            "temporal_space": 0.0,
            "emotional_bandwidth": 0.0,
        }
        for s in self.living_species():
            pop_factor = s.population / 100.0
            consumed["attention"] += s.resources.attention * pop_factor * s.resource_efficiency
            consumed["harmonic_space"] += s.resources.harmonic_space * pop_factor
            consumed["temporal_space"] += s.resources.temporal_space * pop_factor
            consumed["emotional_bandwidth"] += s.resources.emotional_bandwidth * pop_factor

        available = {}
        for key in self.environment:
            available[key] = max(0, self.environment[key] - consumed.get(key, 0))
        return available

    def resource_pressure(self) -> float:
        """Overall resource pressure (0=abundant, 1=scarce)."""
        avail = self.available_resources()
        total_avail = sum(avail.values())
        total_env = sum(self.environment.values())
        if total_env == 0:
            return 1.0
        return 1.0 - (total_avail / total_env)

    # -- species queries -----------------------------------------------------

    def living_species(self) -> list[MusicalSpecies]:
        return [s for s in self.species if not s.extinct and s.population > 0]

    def extinct_species(self) -> list[MusicalSpecies]:
        return [s for s in self.species if s.extinct or s.population <= 0]

    def species_by_niche(self, niche: Niche) -> list[MusicalSpecies]:
        return [s for s in self.living_species() if s.niche == niche]

    def species_by_name(self, name: str) -> Optional[MusicalSpecies]:
        for s in self.living_species():
            if s.name == name:
                return s
        return None

    def dominant_species(self) -> Optional[MusicalSpecies]:
        """Species with highest effective fitness × population."""
        living = self.living_species()
        if not living:
            return None
        return max(living, key=lambda s: s.effective_fitness() * s.population)

    # -- ecological dynamics -------------------------------------------------

    def _competition_phase(self) -> dict[str, float]:
        """Lotka-Volterra competition with niche partitioning and ε control."""
        fitness_changes: dict[str, float] = {}
        living = self.living_species()

        for i, sp_a in enumerate(living):
            delta = 0.0
            for j, sp_b in enumerate(living):
                if i == j:
                    continue

                # Niche-aware competition with ε scaling
                raw_competition = sp_a.compete(sp_b)
                overlap = self.niche_overlap(sp_a, sp_b)
                # ε controls how much niche overlap matters:
                # ε=0: strict partitioning, competition suppressed when overlap is low
                # ε=1: free-for-all, full competition regardless of niche
                partitioning_factor = self.epsilon + (1.0 - self.epsilon) * overlap
                competition = raw_competition * partitioning_factor
                delta -= competition * 0.1

                # Cooperation increases fitness
                cooperation = sp_a.cooperate(sp_b)
                delta += cooperation * 0.05

                # Predation
                if sp_a.prey_upon(sp_b) > sp_b.prey_upon(sp_a):
                    delta += sp_a.prey_upon(sp_b) * 0.08
                else:
                    delta -= sp_b.prey_upon(sp_a) * 0.08

                # Parasitism
                delta -= sp_b.parasitize(sp_a) * 0.05
                delta += sp_a.parasitize(sp_b) * 0.03

            fitness_changes[sp_a.uid] = delta
        return fitness_changes

    def _resource_allocation(self):
        """Allocate resources proportional to fitness and population."""
        living = self.living_species()
        if not living:
            return

        avail = self.available_resources()
        total_fitness = sum(s.effective_fitness() * s.population for s in living)
        if total_fitness == 0:
            return

        for s in living:
            share = (s.effective_fitness() * s.population) / total_fitness
            # Species that get more resources have higher fitness
            resource_bonus = share * 0.02
            s.fitness = _clamp(s.fitness + resource_bonus)

    def _fitness_evaluation(self, fitness_changes: dict[str, float]):
        """Update fitness based on interactions and environmental pressure."""
        pressure = self.resource_pressure()

        for s in self.living_species():
            delta = fitness_changes.get(s.uid, 0.0)

            # Environmental pressure reduces fitness
            delta -= pressure * 0.05 * (1.0 - s.resilience)

            # Niche specialists do better when pressure is high
            if pressure > 0.5:
                delta += s.niche_specialization * 0.02

            # Cultural momentum provides stability
            delta += s.cultural_momentum * 0.01

            s.fitness = _clamp(s.fitness + delta)
            s.age += 1

    def _selection(self):
        """Weak species die. Strong species thrive.

        Tuned to be less aggressive than pure competitive exclusion:
        species decline gradually, and resilience helps them hold on.
        """
        for s in self.living_species():
            # Population dynamics
            effective = s.effective_fitness()

            # Population growth/decline
            if effective > 0.3:
                growth = int(s.population * s.reproduction_rate * effective * 0.1)
                s.population += max(1, growth)
            else:
                decline = int(s.population * (1.0 - effective) * 0.1)  # reduced from 0.2
                s.population -= max(1, decline)

            # Resource scarcity penalty (reduced severity)
            avail = self.available_resources()
            for key in ["attention", "harmonic_space", "temporal_space", "emotional_bandwidth"]:
                need = getattr(s.resources, key) * s.population / 100.0
                if avail.get(key, 0) < need * 0.5:
                    s.population -= max(1, int(s.population * 0.03 * (1.0 - s.resilience)))  # reduced from 0.05

            # Extinction
            if s.population <= self.extinction_threshold or s.fitness < 0.01:
                s.kill()

            # Cap population
            s.population = min(s.population, 10000)

    def _speciation(self):
        """Strong species diversify into new species."""
        living = self.living_species()
        if len(living) >= self.carrying_capacity:
            return

        for s in living:
            if s.fitness > self.speciation_threshold and s.population > 200:
                if random.random() < 0.1 * s.innovation:
                    child = s.mutate()
                    # Parent loses some population
                    s.population = int(s.population * 0.8)
                    self.species.append(child)
                    if len(self.living_species()) >= self.carrying_capacity:
                        return

    def _keystone_predation(self):
        """Kill the winner: dominant species attract predators/parasites.

        This is the 'kill the winner' mechanism from ocean ecology:
        the most abundant species attracts more predation pressure,
        preventing competitive exclusion and maintaining biodiversity.
        """
        living = self.living_species()
        if len(living) < 2:
            return

        total_pop = sum(s.population for s in living)
        if total_pop == 0:
            return

        for s in living:
            # Fraction of total population this species holds
            dominance = s.population / total_pop
            # Predation pressure scales with dominance squared
            # (more dominant = exponentially more pressure)
            pressure = self.kill_the_winner_strength * (dominance ** 2) * len(living)
            # Reduce population proportionally
            loss = int(s.population * pressure)
            s.population = max(1, s.population - loss)
            # Also slightly reduce fitness
            s.fitness = _clamp(s.fitness - pressure * 0.02)

    def _immigration(self):
        """Immigration: new species arrive from outside after extinctions.

        Unlike migration (which just adds random species), immigration
        is triggered by low species counts and fills empty niches.
        This prevents permanent monoculture.
        """
        living = self.living_species()
        living_count = len(living)

        # Only immigrate when diversity is low
        if living_count >= self.carrying_capacity // 2:
            return

        # Probability increases as fewer species remain
        if random.random() > self.immigration_rate * (1.0 - living_count / max(1, self.carrying_capacity)):
            return

        # Find unoccupied niches
        occupied_niches = {s.niche for s in living}
        all_niches = set(Niche)
        empty_niches = all_niches - occupied_niches

        # Prefer empty niches but allow any
        if empty_niches:
            target_niche = random.choice(list(empty_niches))
        else:
            target_niche = random.choice(list(all_niches))

        # Create immigrant with moderate fitness (not too strong, not too weak)
        immigrant = MusicalSpecies(
            name=f"Immigrant_{target_niche.value}_{self.time}",
            niche=target_niche,
            population=random.randint(30, 80),
            fitness=random.uniform(0.3, 0.6),
        )
        self.species.append(immigrant)

    def _migration(self):
        """New species arrive from outside the ecosystem."""
        if random.random() > self.migration_rate:
            return

        living = self.living_species()
        if len(living) >= self.carrying_capacity:
            return

        genres = [
            ("Jazz", Niche.HARMONY), ("Rock", Niche.RHYTHM),
            ("Electronic", Niche.TEXTURE), ("Classical", Niche.MELODY),
            ("Folk", Niche.VOCAL), ("HipHop", Niche.RHYTHM),
            ("Ambient", Niche.AMBIENT), ("Blues", Niche.BASS),
            ("Reggae", Niche.BASS), ("Metal", Niche.PERCUSSION),
            ("Pop", Niche.MELODY), ("Country", Niche.VOCAL),
            ("Techno", Niche.PERCUSSION), ("Soul", Niche.VOCAL),
            ("Punk", Niche.RHYTHM), ("Funk", Niche.BASS),
        ]

        existing_names = {s.name for s in living}
        available = [(n, nc) for n, nc in genres if n not in existing_names]
        if not available:
            return

        name, niche = random.choice(available)
        newcomer = MusicalSpecies(
            name=name,
            niche=niche,
            population=random.randint(20, 80),
            fitness=random.uniform(0.2, 0.6),
        )
        self.species.append(newcomer)

    # -- main simulation loop ------------------------------------------------

    def tick(self) -> dict[str, Any]:
        """One ecological timestep.

        1. Competition (Lotka-Volterra)
        2. Resource allocation
        3. Fitness evaluation
        4. Selection (weak species die)
        5. Speciation (strong species diversify)
        6. Migration (new species arrive)
        """
        self.time += 1

        # Phase 1: Competition
        fitness_changes = self._competition_phase()

        # Phase 2: Resource allocation
        self._resource_allocation()

        # Phase 3: Fitness evaluation
        self._fitness_evaluation(fitness_changes)

        # Phase 4: Selection
        self._selection()

        # Phase 4.5: Kill the winner (keystone predation)
        self._keystone_predation()

        # Phase 5: Speciation
        self._speciation()

        # Phase 6: Migration
        self._migration()

        # Phase 6.5: Immigration after extinction events
        self._immigration()

        # Record history
        snapshot = self._snapshot()
        self.history.append(snapshot)
        return snapshot

    def _snapshot(self) -> dict[str, Any]:
        living = self.living_species()
        return {
            "time": self.time,
            "num_species": len(living),
            "total_population": sum(s.population for s in living),
            "biodiversity": self.biodiversity(),
            "dominant": self.dominant_species().name if self.dominant_species() else None,
            "resource_pressure": self.resource_pressure(),
            "species": [s.to_dict() for s in living],
        }

    def evolve(self, timesteps: int = 100) -> list[dict[str, Any]]:
        """Run ecosystem for N timesteps. Returns population dynamics."""
        results = []
        for _ in range(timesteps):
            snapshot = self.tick()
            results.append(snapshot)
        return results

    # -- ecological metrics --------------------------------------------------

    def biodiversity(self) -> float:
        """Shannon entropy of species distribution.

        High biodiversity = many genres coexisting.
        Low = monoculture (everything sounds the same).
        """
        living = self.living_species()
        if len(living) <= 1:
            return 0.0

        total_pop = sum(s.population for s in living)
        if total_pop == 0:
            return 0.0

        entropy = 0.0
        for s in living:
            if s.population > 0:
                p = s.population / total_pop
                entropy -= p * math.log2(p)
        return entropy

    def keystone_species(self) -> list[MusicalSpecies]:
        """Which species are critical? Remove them and ecosystem collapses.

        A keystone species is one whose removal would cause
        a significant drop in biodiversity.
        """
        living = self.living_species()
        if len(living) <= 1:
            return living.copy()

        current_biodiversity = self.biodiversity()
        keystones = []

        for s in living:
            # Temporarily remove species
            original_pop = s.population
            original_extinct = s.extinct
            s.population = 0
            s.extinct = True

            new_biodiversity = self.biodiversity()

            # Restore
            s.population = original_pop
            s.extinct = original_extinct

            # If biodiversity drops significantly, it's a keystone
            drop = current_biodiversity - new_biodiversity
            if drop > 0.1 or (current_biodiversity > 0 and new_biodiversity == 0):
                keystones.append(s)

        return keystones

    def invasive_species(self, newcomer: MusicalSpecies) -> dict[str, Any]:
        """What happens when a new genre enters?

        Like zebra mussels: can it establish? Or is it outcompeted?
        """
        # Take snapshot before
        before = self._snapshot()

        # Add newcomer
        self.species.append(newcomer)

        # Run a few timesteps to see what happens
        for _ in range(10):
            self.tick()

        after = self._snapshot()

        # Check if newcomer survived
        survived = newcomer in self.living_species()

        return {
            "survived": survived,
            "newcomer_population": newcomer.population if survived else 0,
            "before_species": before["num_species"],
            "after_species": after["num_species"],
            "before_biodiversity": before["biodiversity"],
            "after_biodiversity": after["biodiversity"],
            "displaced": before["num_species"] - after["num_species"] + (1 if survived else 0),
        }

    def extinction_event(self, threshold: float = 0.1) -> dict[str, Any]:
        """Remove all species below threshold. Like mass extinction.

        What survives? What fills the empty niches?
        """
        before = self._snapshot()
        survivors = []
        casualties = []

        for s in self.living_species():
            if s.fitness < threshold:
                s.kill()
                casualties.append(s.name)
            else:
                # Survivors take damage too
                s.population = int(s.population * random.uniform(0.3, 0.7))
                s.fitness *= random.uniform(0.5, 0.9)
                survivors.append(s.name)

        after = self._snapshot()

        return {
            "before": before,
            "after": after,
            "survivors": survivors,
            "casualties": casualties,
            "extinction_rate": len(casualties) / max(1, before["num_species"]),
        }

    def succession(self, timesteps: int = 50) -> list[str]:
        """Ecological succession: how the ecosystem recovers after disturbance.

        Pioneer species → intermediate → climax community.
        In music: silence → simple → complex → stable genre.
        """
        stages = []

        for i in range(timesteps):
            self.tick()
            living = self.living_species()
            bio = self.biodiversity()
            pressure = self.resource_pressure()

            if len(living) == 0:
                stage = "barren"
            elif len(living) <= 2 or bio < 0.5:
                stage = "pioneer"
            elif bio < 1.5:
                stage = "intermediate"
            elif pressure < 0.3:
                stage = "climax"
            else:
                stage = "competitive"

            stages.append(stage)

        return stages

    def food_web(self) -> dict[str, list[str]]:
        """Build a food web of predator-prey relationships."""
        living = self.living_species()
        web: dict[str, list[str]] = {s.name: [] for s in living}

        for s in living:
            for other in living:
                if s.name == other.name:
                    continue
                interaction = s.determine_interaction(other)
                if interaction in (InteractionType.PREDATION, InteractionType.PARASITISM):
                    web[s.name].append(other.name)

        return web

    def symbiosis(self, species_a: MusicalSpecies, species_b: MusicalSpecies) -> Optional[MusicalSpecies]:
        """Merge two cooperating species into a new hybrid species.

        Like jazz + rock = fusion.
        """
        if species_a.extinct or species_b.extinct:
            return None

        cooperation = species_a.cooperate(species_b)
        if cooperation < 0.1:
            return None

        # Blend genomes
        new_genome = [
            (g1 + g2) / 2 + random.gauss(0, 0.05)
            for g1, g2 in zip(species_a.genome, species_b.genome)
        ]
        new_genome = [_clamp(g) for g in new_genome]

        hybrid = MusicalSpecies(
            name=f"{species_a.name}×{species_b.name}",
            genome=new_genome,
            niche=species_a.niche if species_a.fitness > species_b.fitness else species_b.niche,
            population=(species_a.population + species_b.population) // 2,
            fitness=max(species_a.fitness, species_b.fitness) * 1.1,
            resources=Resources(
                attention=_clamp((species_a.resources.attention + species_b.resources.attention) / 2),
                harmonic_space=_clamp((species_a.resources.harmonic_space + species_b.resources.harmonic_space) / 2),
                temporal_space=_clamp((species_a.resources.temporal_space + species_b.resources.temporal_space) / 2),
                emotional_bandwidth=_clamp(
                    (species_a.resources.emotional_bandwidth + species_b.resources.emotional_bandwidth) / 2
                ),
            ),
        )
        hybrid.generation = max(species_a.generation, species_b.generation) + 1
        return hybrid

    # -- music conversion ----------------------------------------------------

    def to_music(self, dynamics: Optional[list[dict]] = None) -> Arrangement:
        """Convert ecosystem dynamics to music.

        - Population sizes → number of voices
        - Competition → dissonance
        - Cooperation → harmony
        - Extinction → silence
        - Speciation → new themes
        """
        if dynamics is None:
            dynamics = self.history[-1:] if self.history else [self._snapshot()]

        arrangement = Arrangement()

        for step in dynamics:
            species_data = step.get("species", [])
            for sd in species_data:
                pop = sd.get("population", 0)
                fitness = sd.get("fitness", 0)
                niche_str = sd.get("niche", "melody")

                try:
                    niche = Niche(niche_str)
                except ValueError:
                    niche = Niche.MELODY

                voice = Voice(
                    name=sd.get("name", "unknown"),
                    niche=niche,
                    population=pop,
                    fitness=fitness,
                    num_voices=min(8, max(1, pop // 100)),
                    dissonance=max(0, 1.0 - fitness),
                    consonance=fitness,
                    velocity=min(127, max(30, int(fitness * 127))),
                    generation=sd.get("generation", 0),
                )
                arrangement.voices.append(voice)

            # Ecosystem-wide properties
            arrangement.dissonance.append(max(0, step.get("resource_pressure", 0)))
            arrangement.biodiversity.append(step.get("biodiversity", 0))

        return arrangement

    # -- utilities -----------------------------------------------------------

    def add_species(self, species: MusicalSpecies):
        """Add a species to the ecosystem."""
        self.species.append(species)

    def remove_species(self, name: str) -> bool:
        """Remove a species by name."""
        for s in self.species:
            if s.name == name:
                s.kill()
                return True
        return False

    def reset(self):
        """Reset the ecosystem to initial state."""
        self.species.clear()
        self.history.clear()
        self.interactions.clear()
        self.time = 0

    def summary(self) -> dict[str, Any]:
        living = self.living_species()
        return {
            "time": self.time,
            "living_species": len(living),
            "extinct_species": len(self.extinct_species()),
            "total_population": sum(s.population for s in living),
            "biodiversity": self.biodiversity(),
            "resource_pressure": self.resource_pressure(),
            "dominant": self.dominant_species().name if self.dominant_species() else None,
            "niches_occupied": list(set(s.niche.value for s in living)),
            "epsilon": self.epsilon,
        }

    def __repr__(self) -> str:
        living = self.living_species()
        return (
            f"MusicalEcosystem(t={self.time}, species={len(living)}, "
            f"bio={self.biodiversity():.2f})"
        )


# ---------------------------------------------------------------------------
# Arrangement (music output)
# ---------------------------------------------------------------------------

@dataclass
class Voice:
    """A musical voice derived from a species."""
    name: str
    niche: Niche
    population: int
    fitness: float
    num_voices: int = 1
    dissonance: float = 0.0
    consonance: float = 1.0
    velocity: int = 100
    generation: int = 0

    def to_midi_channel(self) -> int:
        """Map niche to MIDI channel."""
        mapping = {
            Niche.RHYTHM: 0,
            Niche.BASS: 1,
            Niche.HARMONY: 2,
            Niche.MELODY: 3,
            Niche.TEXTURE: 4,
            Niche.PERCUSSION: 9,
            Niche.AMBIENT: 5,
            Niche.VOCAL: 6,
        }
        return mapping.get(self.niche, 7)

    def suggested_octave(self) -> int:
        """Map niche to suggested octave."""
        mapping = {
            Niche.BASS: 2,
            Niche.RHYTHM: 4,
            Niche.HARMONY: 4,
            Niche.MELODY: 5,
            Niche.TEXTURE: 5,
            Niche.PERCUSSION: 3,
            Niche.AMBIENT: 3,
            Niche.VOCAL: 4,
        }
        return mapping.get(self.niche, 4)


@dataclass
class Arrangement:
    """A musical arrangement derived from ecosystem dynamics."""
    voices: list[Voice] = field(default_factory=list)
    dissonance: list[float] = field(default_factory=list)
    biodiversity: list[float] = field(default_factory=list)
    tempo: int = 120

    @property
    def total_voices(self) -> int:
        return sum(v.num_voices for v in self.voices)

    @property
    def average_dissonance(self) -> float:
        return sum(self.dissonance) / len(self.dissonance) if self.dissonance else 0.0

    @property
    def average_biodiversity(self) -> float:
        return sum(self.biodiversity) / len(self.biodiversity) if self.biodiversity else 0.0

    def species_voice_map(self) -> dict[str, int]:
        """Map species names to their voice count."""
        return {v.name: v.num_voices for v in self.voices}

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_voices": self.total_voices,
            "num_species": len(self.voices),
            "average_dissonance": self.average_dissonance,
            "average_biodiversity": self.average_biodiversity,
            "voices": [
                {
                    "name": v.name,
                    "niche": v.niche.value,
                    "voices": v.num_voices,
                    "dissonance": v.dissonance,
                    "velocity": v.velocity,
                    "channel": v.to_midi_channel(),
                    "octave": v.suggested_octave(),
                }
                for v in self.voices
            ],
        }


# ---------------------------------------------------------------------------
# Preset ecosystems
# ---------------------------------------------------------------------------

def create_classical_ecosystem() -> MusicalEcosystem:
    """Create a classical music ecosystem."""
    ecosystem = MusicalEcosystem(total_attention=1.0, carrying_capacity=15)

    strings = MusicalSpecies(
        name="Strings", niche=Niche.MELODY, population=300, fitness=0.7,
        resources=Resources(attention=0.3, harmonic_space=0.3, temporal_space=0.2, emotional_bandwidth=0.3),
    )
    strings.genome[0] = 0.3  # low competitiveness
    strings.genome[1] = 0.7  # high cooperation

    brass = MusicalSpecies(
        name="Brass", niche=Niche.HARMONY, population=150, fitness=0.5,
        resources=Resources(attention=0.2, harmonic_space=0.25, temporal_space=0.2, emotional_bandwidth=0.2),
    )
    brass.genome[0] = 0.5
    brass.genome[1] = 0.5

    woodwinds = MusicalSpecies(
        name="Woodwinds", niche=Niche.MELODY, population=200, fitness=0.6,
        resources=Resources(attention=0.15, harmonic_space=0.2, temporal_space=0.15, emotional_bandwidth=0.25),
    )
    woodwinds.genome[0] = 0.2
    woodwinds.genome[1] = 0.8

    percussion = MusicalSpecies(
        name="Timpani", niche=Niche.PERCUSSION, population=80, fitness=0.4,
        resources=Resources(attention=0.1, harmonic_space=0.05, temporal_space=0.3, emotional_bandwidth=0.1),
    )
    percussion.genome[9] = 0.8  # keystone factor

    bass = MusicalSpecies(
        name="Bass", niche=Niche.BASS, population=120, fitness=0.5,
        resources=Resources(attention=0.1, harmonic_space=0.2, temporal_space=0.3, emotional_bandwidth=0.1),
    )
    bass.genome[9] = 0.7  # keystone

    ecosystem.add_species(strings)
    ecosystem.add_species(brass)
    ecosystem.add_species(woodwinds)
    ecosystem.add_species(percussion)
    ecosystem.add_species(bass)
    return ecosystem


def create_modern_ecosystem() -> MusicalEcosystem:
    """Create a modern genre ecosystem."""
    ecosystem = MusicalEcosystem(total_attention=1.0, carrying_capacity=20)

    pop = MusicalSpecies(
        name="Pop", niche=Niche.MELODY, population=500, fitness=0.8,
        resources=Resources(attention=0.4, harmonic_space=0.2, temporal_space=0.15, emotional_bandwidth=0.3),
    )
    pop.genome[0] = 0.8  # competitive
    pop.genome[11] = 0.9  # cultural momentum
    pop.genome[7] = 0.7  # parasitism (earworms)

    rock = MusicalSpecies(
        name="Rock", niche=Niche.RHYTHM, population=350, fitness=0.65,
        resources=Resources(attention=0.3, harmonic_space=0.25, temporal_space=0.3, emotional_bandwidth=0.25),
    )
    rock.genome[0] = 0.6
    rock.genome[6] = 0.5  # predation

    electronic = MusicalSpecies(
        name="Electronic", niche=Niche.TEXTURE, population=280, fitness=0.6,
        resources=Resources(attention=0.2, harmonic_space=0.3, temporal_space=0.25, emotional_bandwidth=0.15),
    )
    electronic.genome[15] = 0.9  # innovation
    electronic.genome[3] = 0.8  # adaptability

    hip_hop = MusicalSpecies(
        name="HipHop", niche=Niche.RHYTHM, population=320, fitness=0.7,
        resources=Resources(attention=0.25, harmonic_space=0.15, temporal_space=0.35, emotional_bandwidth=0.25),
    )
    hip_hop.genome[0] = 0.7
    hip_hop.genome[15] = 0.8

    ambient = MusicalSpecies(
        name="Ambient", niche=Niche.AMBIENT, population=150, fitness=0.45,
        resources=Resources(attention=0.1, harmonic_space=0.2, temporal_space=0.1, emotional_bandwidth=0.2),
    )
    ambient.genome[1] = 0.6
    ambient.genome[8] = 0.7  # resilience

    ecosystem.add_species(pop)
    ecosystem.add_species(rock)
    ecosystem.add_species(electronic)
    ecosystem.add_species(hip_hop)
    ecosystem.add_species(ambient)
    return ecosystem


def create_minimal_ecosystem() -> MusicalEcosystem:
    """Create a minimal ecosystem for testing."""
    ecosystem = MusicalEcosystem(total_attention=0.5, carrying_capacity=5)
    a = MusicalSpecies(name="A", niche=Niche.BASS, population=100, fitness=0.5)
    b = MusicalSpecies(name="B", niche=Niche.MELODY, population=100, fitness=0.5)
    ecosystem.add_species(a)
    ecosystem.add_species(b)
    return ecosystem
