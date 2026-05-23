"""
genome_music — Musical Evolution via Genetic Constraint Systems.

Connects flux-genome-py (genetic expression) to musical composition through
constraint theory. A MusicalGenome encodes 25 constraint genes across 5
musical domains. MusicalEvolution evolves populations of "musical organisms"
toward genre-specific attractors in constraint space.

Architecture:
    MusicalGenome  — 25-gene musical constraint genome
    GenomePlayer   — generates phrases from genome constraint parameters
    MusicalEvolution — population + fitness + selection + crossover + mutation

Pipeline:
    MusicalGenome → GenomePlayer → phrase (MIDI-like events)
    MusicalEvolution → evolve population toward genre targets

Usage:
    from flux_tensor_midi.genome_music import MusicalEvolution

    evo = MusicalEvolution(target_genre="jazz", population_size=100)
    result = evo.run(generations=50)
    print(f"Best fitness: {result.best_fitness:.4f}")
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PHI = (1 + np.sqrt(5)) / 2

# Musical genome: 25 genes, 5 domains × 5 genes
# (gene_id, param_name, domain, scale, offset, min_val, max_val)
GENE_SPECS: List[Tuple[str, str, str, float, float, float, float]] = [
    # --- CORE (5) ---
    ("snap_strictness",  "snap_strength",       "core", 0.5,  0.0, 0.0, 1.0),
    ("funnel_gravity",   "epsilon_0",            "core", 50.0, 5.0, 1.0, 200.0),
    ("laman_threshold",  "edge_density",         "core", 0.5,  0.2, 0.2, 1.0),
    ("consensus_weight", "coupling_alpha",        "core", 0.4,  0.1, 0.05, 0.95),
    ("tempo_tendency",   "bpm",                  "core", 120.0,40.0,40.0, 240.0),
    # --- PITCH (5) ---
    ("scale_preference", "grid_resolution",      "pitch", 4.0, 1.0, 2.0, 7.0),
    ("pitch_range",      "anomaly_threshold",    "pitch", 100.0,10.0,10.0, 500.0),
    ("contour_shape",    "drift_adaptation",     "pitch", 0.1, 0.01,0.01,0.5),
    ("interval_weights", "snap_tolerance",       "pitch", 0.3, 0.0, 0.0, 1.0),
    ("ornament_density", "reset_rate",           "pitch", 0.2, 0.0, 0.0, 1.0),
    # --- RHYTHM (5) ---
    ("groove_width",     "swing_ratio",          "rhythm", 0.55,0.5,0.5, 0.75),
    ("syncopation",      "snap_phase",           "rhythm", 0.1, 0.0, 0.0, 0.5),
    ("subdivision",      "rubato_extent",        "rhythm", 0.15,0.0, 0.0, 1.0),
    ("swing_feel",       "accel_decel",          "rhythm", 0.1, 0.0, 0.0, 1.0),
    ("accent_pattern",   "groove_depth",         "rhythm", 0.3, 0.0, 0.0, 1.0),
    # --- TIMBRE / ENSEMBLE (5) ---
    ("brightness",       "consensus_threshold",  "timbre", 0.5, 0.0, 0.0, 1.0),
    ("warmth",           "listen_depth",         "timbre", 2.0, 0.5, 0.5, 5.5),
    ("attack",           "correct_rate",         "timbre", 0.4, 0.0, 0.0, 1.0),
    ("decay",            "leader_weight",        "timbre", 0.3, 0.0, 0.0, 1.0),
    ("spatial",          "decay_rate",           "timbre", 0.08,0.01,0.001,0.5),
    # --- FORM (5) ---
    ("phrase_length",    "min_edges",            "form",  4.0, 1.0, 1.0, 10.0),
    ("repetition",       "redundancy",           "form",  0.3, 0.0, 0.0, 1.0),
    ("variation",        "voice_independence",   "form",  0.5, 0.0, 0.0, 1.0),
    ("development",      "coupling_topology",    "form",  1.0, 0.0, 0.0, 2.0),
    ("cadence",          "snap_strength_form",   "form",  0.6, 0.0, 0.0, 1.0),
]

DOMAIN_ORDER = ["core", "pitch", "rhythm", "timbre", "form"]

GENRE_TARGETS: Dict[str, Dict[str, float]] = {
    "jazz": {
        "snap_strength": 0.4, "epsilon_0": 80.0, "edge_density": 0.4,
        "coupling_alpha": 0.3, "bpm": 180.0,
        "grid_resolution": 3.0, "anomaly_threshold": 150.0,
        "drift_adaptation": 0.08, "snap_tolerance": 0.5, "reset_rate": 0.3,
        "swing_ratio": 0.67, "snap_phase": 0.33, "rubato_extent": 0.7,
        "accel_decel": 0.3, "groove_depth": 0.4,
        "consensus_threshold": 0.4, "listen_depth": 2.5,
        "correct_rate": 0.3, "leader_weight": 0.3, "decay_rate": 0.05,
        "min_edges": 3.0, "redundancy": 0.2, "voice_independence": 0.8,
        "coupling_topology": 1.0, "snap_strength_form": 0.4,
    },
    "classical": {
        "snap_strength": 0.7, "epsilon_0": 50.0, "edge_density": 0.7,
        "coupling_alpha": 0.5, "bpm": 72.0,
        "grid_resolution": 2.0, "anomaly_threshold": 100.0,
        "drift_adaptation": 0.04, "snap_tolerance": 0.15, "reset_rate": 0.2,
        "swing_ratio": 0.5, "snap_phase": 0.0, "rubato_extent": 0.3,
        "accel_decel": 0.2, "groove_depth": 0.3,
        "consensus_threshold": 0.6, "listen_depth": 3.0,
        "correct_rate": 0.4, "leader_weight": 0.5, "decay_rate": 0.08,
        "min_edges": 4.0, "redundancy": 0.3, "voice_independence": 0.7,
        "coupling_topology": 1.0, "snap_strength_form": 0.7,
    },
    "electronic": {
        "snap_strength": 0.98, "epsilon_0": 20.0, "edge_density": 0.8,
        "coupling_alpha": 0.9, "bpm": 128.0,
        "grid_resolution": 4.0, "anomaly_threshold": 50.0,
        "drift_adaptation": 0.05, "snap_tolerance": 0.02, "reset_rate": 0.1,
        "swing_ratio": 0.5, "snap_phase": 0.0, "rubato_extent": 0.0,
        "accel_decel": 0.0, "groove_depth": 0.95,
        "consensus_threshold": 0.9, "listen_depth": 3.5,
        "correct_rate": 0.8, "leader_weight": 0.7, "decay_rate": 0.3,
        "min_edges": 5.0, "redundancy": 0.3, "voice_independence": 0.1,
        "coupling_topology": 2.0, "snap_strength_form": 0.98,
    },
    "ambient": {
        "snap_strength": 0.2, "epsilon_0": 150.0, "edge_density": 0.3,
        "coupling_alpha": 0.1, "bpm": 65.0,
        "grid_resolution": 5.0, "anomaly_threshold": 200.0,
        "drift_adaptation": 0.02, "snap_tolerance": 0.8, "reset_rate": 0.05,
        "swing_ratio": 0.5, "snap_phase": 0.1, "rubato_extent": 0.9,
        "accel_decel": 0.5, "groove_depth": 0.1,
        "consensus_threshold": 0.2, "listen_depth": 1.5,
        "correct_rate": 0.1, "leader_weight": 0.1, "decay_rate": 0.01,
        "min_edges": 2.0, "redundancy": 0.6, "voice_independence": 0.9,
        "coupling_topology": 0.5, "snap_strength_form": 0.2,
    },
    "hiphop": {
        "snap_strength": 0.9, "epsilon_0": 40.0, "edge_density": 0.5,
        "coupling_alpha": 0.6, "bpm": 140.0,
        "grid_resolution": 4.0, "anomaly_threshold": 80.0,
        "drift_adaptation": 0.12, "snap_tolerance": 0.1, "reset_rate": 0.2,
        "swing_ratio": 0.6, "snap_phase": 0.05, "rubato_extent": 0.1,
        "accel_decel": 0.05, "groove_depth": 0.8,
        "consensus_threshold": 0.7, "listen_depth": 2.0,
        "correct_rate": 0.5, "leader_weight": 0.8, "decay_rate": 0.15,
        "min_edges": 3.0, "redundancy": 0.1, "voice_independence": 0.3,
        "coupling_topology": 0.0, "snap_strength_form": 0.9,
    },
}


# ---------------------------------------------------------------------------
# MusicalGenome
# ---------------------------------------------------------------------------

class MusicalGenome:
    """A 25-gene musical constraint genome.

    Each gene encodes a constraint parameter via its structure value.
    Genes are organized into 5 domains: core, pitch, rhythm, timbre, form.

    The genome is a FIXED specification — it does not change during
    expression. Evolution creates NEW genomes; expression READS them.
    """

    def __init__(self, genes: Optional[Dict[str, float]] = None, seed: Optional[int] = None):
        """Initialize a musical genome.

        Parameters
        ----------
        genes : dict, optional
            Dict of gene_id → float value (clamped to valid range).
            If None, creates a random genome.
        seed : int, optional
            Random seed for reproducibility (only if genes is None).
        """
        rng = np.random.default_rng(seed)
        self.genes: Dict[str, float] = {}

        for gene_id, param_name, domain, scale, offset, lo, hi in GENE_SPECS:
            if genes and gene_id in genes:
                self.genes[gene_id] = max(lo, min(hi, genes[gene_id]))
            else:
                # Random initialization within valid range
                self.genes[gene_id] = float(rng.uniform(lo, hi))

    def to_config(self) -> Dict[str, float]:
        """Convert genome to constraint configuration dict (param_name → value)."""
        config = {}
        for gene_id, param_name, domain, scale, offset, lo, hi in GENE_SPECS:
            config[param_name] = self.genes.get(gene_id, scale)
        return config

    def get_gene(self, gene_id: str) -> float:
        """Get a gene's value by gene_id."""
        return self.genes.get(gene_id, 0.0)

    def set_gene(self, gene_id: str, value: float) -> None:
        """Set a gene's value, clamping to valid range."""
        for gid, param_name, domain, scale, offset, lo, hi in GENE_SPECS:
            if gid == gene_id:
                self.genes[gene_id] = max(lo, min(hi, value))
                return
        raise ValueError(f"Unknown gene: {gene_id}")

    @property
    def gene_count(self) -> int:
        return len(self.genes)

    @property
    def domains(self) -> List[str]:
        return DOMAIN_ORDER

    def domain_genes(self, domain: str) -> Dict[str, float]:
        """Return all genes for a given domain."""
        return {
            gid: val for gid, val in self.genes.items()
            if any(s[0] == gid and s[2] == domain for s in GENE_SPECS)
        }

    def clone(self) -> "MusicalGenome":
        """Return a deep copy."""
        return MusicalGenome(genes=dict(self.genes))

    def __repr__(self) -> str:
        bpm = self.genes.get("tempo_tendency", 0)
        snap = self.genes.get("snap_strictness", 0)
        return f"MusicalGenome(bpm={bpm:.1f}, snap={snap:.2f})"


# ---------------------------------------------------------------------------
# MusicalEvent
# ---------------------------------------------------------------------------

@dataclass
class MusicalEvent:
    """A single musical event (note)."""
    pitch: int          # MIDI pitch (0-127)
    velocity: int       # MIDI velocity (0-127)
    start_beat: float   # Start time in beats
    duration: float     # Duration in beats
    channel: int = 0    # MIDI channel


# ---------------------------------------------------------------------------
# GenomePlayer
# ---------------------------------------------------------------------------

class GenomePlayer:
    """Generates musical phrases from a MusicalGenome.

    The genome encodes constraint parameters. The player interprets those
    constraints to generate a sequence of MusicalEvents.

    The pipeline:
    1. Read genome → constraint configuration
    2. Use constraint parameters to build a phrase generator
    3. Generate events within the constraint envelope
    """

    # Chromatic scale degrees (semitone offsets from root)
    SCALES = {
        2: [0, 2, 4, 5, 7, 9, 11],       # diatonic (major)
        3: [0, 2, 3, 5, 7, 8, 10],        # minor
        4: [0, 2, 4, 5, 7, 9, 11],        # major (default)
        5: [0, 1, 3, 5, 6, 8, 10, 11],    # octatonic-ish
        6: [0, 2, 4, 6, 8, 10],           # whole tone
        7: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],  # chromatic
    }

    def __init__(self, genome: MusicalGenome, root: int = 60, seed: Optional[int] = None):
        self.genome = genome
        self.root = root  # MIDI pitch of tonal center
        self.rng = np.random.default_rng(seed)

    def generate_phrase(self, bars: int = 4, beats_per_bar: int = 4) -> List[MusicalEvent]:
        """Generate a phrase from the genome's constraint parameters.

        Parameters
        ----------
        bars : int
            Number of bars to generate.
        beats_per_bar : int
            Beats per bar.

        Returns
        -------
        List of MusicalEvent.
        """
        config = self.genome.to_config()
        total_beats = bars * beats_per_bar

        # Extract constraint parameters
        bpm = config.get("bpm", 120.0)
        snap_strength = config.get("snap_strength", 0.5)
        snap_tolerance = config.get("snap_tolerance", 0.3)
        swing_ratio = config.get("swing_ratio", 0.5)
        rubato = config.get("rubato_extent", 0.0)
        groove_depth = config.get("groove_depth", 0.3)
        grid_res = config.get("grid_resolution", 4.0)
        pitch_range_cents = config.get("anomaly_threshold", 100.0)
        drift_adapt = config.get("drift_adaptation", 0.1)
        coupling = config.get("coupling_alpha", 0.4)
        voice_indep = config.get("voice_independence", 0.5)
        redundancy = config.get("redundancy", 0.3)
        decay_rate = config.get("decay_rate", 0.05)

        # Select scale from grid_resolution
        scale_degrees = self.SCALES.get(int(round(grid_res)), self.SCALES[4])

        # Max pitch deviation in semitones from pitch_range (cents → semitones)
        max_semitone_dev = int(pitch_range_cents / 100)

        # Generate note events
        events: List[MusicalEvent] = []
        current_beat = 0.0
        current_pitch_offset = 0  # semitones from root

        subdivision = max(grid_res, 2.0)

        while current_beat < total_beats:
            # Duration: pick from grid subdivisions
            dur_options = [4.0 / subdivision, 2.0 / subdivision,
                           1.0 / subdivision, 0.5 / subdivision]
            dur_weights = [0.1, 0.3, 0.4, 0.2]
            # Shorter durations when groove is deep
            if groove_depth > 0.6:
                dur_weights = [0.05, 0.2, 0.3, 0.45]
            dur_idx = self.rng.choice(len(dur_options), p=dur_weights)
            duration = float(dur_options[dur_idx])

            # Apply swing
            if current_beat % 1.0 >= 0.5:
                swing_offset = (swing_ratio - 0.5) * duration
            else:
                swing_offset = 0.0

            # Apply rubato
            rubato_offset = float(self.rng.normal(0, rubato * 0.1))

            # Start time with constraints
            start = current_beat + swing_offset + rubato_offset
            # Snap to grid
            if snap_strength > 0:
                grid_pos = round(start * subdivision) / subdivision
                start = start * (1 - snap_strength) + grid_pos * snap_strength

            start = max(0.0, min(start, total_beats - 0.01))

            # Pitch selection
            # Choose a scale degree with drift
            drift = float(self.rng.normal(0, drift_adapt * 3))
            current_pitch_offset += drift
            # Pull back toward center (funnel gravity)
            current_pitch_offset *= (1.0 - config.get("epsilon_0", 50.0) / 500.0)
            # Clamp to range
            current_pitch_offset = max(-max_semitone_dev,
                                       min(max_semitone_dev, current_pitch_offset))

            # Quantize to scale
            target_pitch = self.root + current_pitch_offset
            pitch = self._snap_to_scale(target_pitch, scale_degrees, snap_strength)

            # Velocity with variation
            base_vel = 80
            vel_variation = int(self.rng.normal(0, 15))
            velocity = max(30, min(127, base_vel + vel_variation))

            # Accent pattern from groove
            beat_in_bar = current_beat % beats_per_bar
            if groove_depth > 0.5 and beat_in_bar == 0:
                velocity = min(127, velocity + 20)

            event = MusicalEvent(
                pitch=max(0, min(127, pitch)),
                velocity=velocity,
                start_beat=round(start, 4),
                duration=round(max(0.05, duration), 4),
            )
            events.append(event)

            # Advance beat
            current_beat += duration

            # Rest probability (inversely related to redundancy)
            if self.rng.random() > redundancy * 0.8 + 0.2:
                rest_dur = float(dur_options[self.rng.choice(len(dur_options))])
                current_beat += rest_dur * 0.5

        return events

    def _snap_to_scale(self, target_pitch: float, scale_degrees: List[int],
                       snap_strength: float) -> int:
        """Snap a pitch to the nearest scale degree."""
        octave = int(target_pitch // 12)
        pitch_class = target_pitch - octave * 12

        # Find nearest scale degree
        best = min(scale_degrees, key=lambda d: abs(d - pitch_class))
        snapped = octave * 12 + best

        # Blend between snapped and free
        result = target_pitch * (1 - snap_strength) + snapped * snap_strength
        return int(round(result))


# ---------------------------------------------------------------------------
# Fitness Evaluation
# ---------------------------------------------------------------------------

def evaluate_fitness(
    config: Dict[str, float],
    target_genre: str,
    novelty_bonus: float = 0.0,
) -> float:
    """Score a constraint configuration against a target genre.

    Fitness = 0.40*genre_match + 0.25*constraint_satisfaction
            + 0.20*listenability + 0.15*novelty

    Returns float in [0, 1].
    """
    if target_genre not in GENRE_TARGETS:
        raise ValueError(f"Unknown genre '{target_genre}'. "
                         f"Available: {list(GENRE_TARGETS.keys())}")

    target = GENRE_TARGETS[target_genre]

    # --- Genre match (cosine similarity) ---
    keys = list(target.keys())
    vec_a = np.array([config.get(k, 0.0) for k in keys])
    vec_b = np.array([target[k] for k in keys])

    # Normalize to [0,1] per dimension
    for i, key in enumerate(keys):
        spec = next((s for s in GENE_SPECS if s[1] == key), None)
        if spec:
            lo, hi = spec[5], spec[6]
            if hi > lo:
                vec_a[i] = (vec_a[i] - lo) / (hi - lo)
                vec_b[i] = (vec_b[i] - lo) / (hi - lo)

    dot = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    genre_score = dot / max(norm_a * norm_b, 1e-8)
    genre_score = max(0.0, min(1.0, genre_score))

    # --- Constraint satisfaction (internal consistency) ---
    tol = config.get("snap_tolerance", 0.5)
    strength = config.get("snap_strength", 0.5)
    if tol < 0.1 and strength > 0.8:
        cs1 = 1.0
    elif tol > 0.3 and strength < 0.6:
        cs1 = 1.0
    else:
        cs1 = 0.5

    coupling = config.get("coupling_alpha", 0.5)
    density = config.get("edge_density", 0.5)
    cs2 = 1.0 - abs(coupling - density)

    rubato = config.get("rubato_extent", 0.0)
    cs3 = 1.0 - abs(rubato + (1.0 - strength) - 1.0)
    cs_score = (cs1 + cs2 + cs3) / 3.0

    # --- Listenability heuristic ---
    listen = 0.5
    bpm = config.get("bpm", 120.0)
    if 40 <= bpm <= 200:
        listen += 0.2
    swing = config.get("swing_ratio", 0.5)
    if 0.5 <= swing <= 0.67:
        listen += 0.15
    groove = config.get("groove_depth", 0.5)
    if 0.1 <= groove <= 0.9:
        listen += 0.15
    listen = min(1.0, listen)

    # --- Combined ---
    fitness = (
        0.40 * genre_score +
        0.25 * cs_score +
        0.20 * listen +
        0.15 * min(1.0, novelty_bonus)
    )
    return round(float(fitness), 6)


# ---------------------------------------------------------------------------
# Genetic Operators
# ---------------------------------------------------------------------------

def mutate_genome(
    genome: MusicalGenome,
    mutation_rate: float = 0.15,
    mutation_scale: float = 0.2,
    rng: Optional[np.random.Generator] = None,
) -> MusicalGenome:
    """Mutate a genome by perturbing gene values. Returns a new genome."""
    rng = rng or np.random.default_rng()
    new_genes = {}
    for gene_id, param_name, domain, scale, offset, lo, hi in GENE_SPECS:
        val = genome.get_gene(gene_id)
        if rng.random() < mutation_rate:
            range_size = hi - lo
            perturbation = rng.normal(0, mutation_scale * range_size)
            val = max(lo, min(hi, val + perturbation))
        new_genes[gene_id] = val
    return MusicalGenome(genes=new_genes)


def crossover(parent_a: MusicalGenome, parent_b: MusicalGenome,
              rng: Optional[np.random.Generator] = None) -> MusicalGenome:
    """Single-point crossover between two genomes."""
    rng = rng or np.random.default_rng()
    gene_ids = [s[0] for s in GENE_SPECS]
    if len(gene_ids) < 2:
        return parent_a.clone()

    point = int(rng.integers(1, len(gene_ids) - 1))
    child_genes = {}
    for i, gid in enumerate(gene_ids):
        source = parent_a if i < point else parent_b
        child_genes[gid] = source.get_gene(gid)
    return MusicalGenome(genes=child_genes)


def tournament_select(
    population: List[Tuple[MusicalGenome, float]],
    k: int = 3,
    rng: Optional[np.random.Generator] = None,
) -> MusicalGenome:
    """Tournament selection: pick k random, return the fittest."""
    rng = rng or np.random.default_rng()
    contestants = rng.choice(len(population), size=min(k, len(population)), replace=False)
    best = max(contestants, key=lambda idx: population[idx][1])
    return population[best][0]


# ---------------------------------------------------------------------------
# EvolutionResult
# ---------------------------------------------------------------------------

@dataclass
class EvolutionResult:
    """Result of an evolutionary run."""
    best_genome: MusicalGenome
    best_fitness: float
    best_config: Dict[str, float]
    history: List[Dict[str, Any]] = field(default_factory=list)
    final_population: List[Tuple[MusicalGenome, float]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# MusicalEvolution
# ---------------------------------------------------------------------------

class MusicalEvolution:
    """Evolve a population of musical genomes toward a genre target.

    Parameters
    ----------
    target_genre : str
        One of: jazz, classical, electronic, ambient, hiphop.
    population_size : int
        Number of organisms per generation.
    mutation_rate : float
        Per-gene mutation probability.
    mutation_scale : float
        Mutation perturbation scale (fraction of gene range).
    elitism : int
        Number of top organisms carried forward unchanged.
    seed : int, optional
        Random seed for reproducibility.
    """

    def __init__(
        self,
        target_genre: str = "jazz",
        population_size: int = 100,
        mutation_rate: float = 0.15,
        mutation_scale: float = 0.2,
        elitism: int = 2,
        seed: Optional[int] = None,
    ):
        if target_genre not in GENRE_TARGETS:
            raise ValueError(f"Unknown genre '{target_genre}'. "
                             f"Available: {list(GENRE_TARGETS.keys())}")
        self.target_genre = target_genre
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.mutation_scale = mutation_scale
        self.elitism = elitism
        self.rng = np.random.default_rng(seed)
        self.seed = seed

    def _init_population(self) -> List[Tuple[MusicalGenome, float]]:
        """Create initial population with random genomes."""
        population = []
        for _ in range(self.population_size):
            g = MusicalGenome(seed=int(self.rng.integers(0, 2**31)))
            config = g.to_config()
            fitness = evaluate_fitness(config, self.target_genre)
            population.append((g, fitness))
        return population

    def _compute_diversity(self, population: List[Tuple[MusicalGenome, float]]) -> float:
        """Compute population diversity as avg pairwise distance."""
        target = GENRE_TARGETS[self.target_genre]
        keys = list(target.keys())
        vectors = np.array([
            [g.to_config().get(k, 0.0) for k in keys]
            for g, _ in population
        ])
        if len(vectors) <= 1:
            return 0.0
        n = min(len(vectors), 15)
        pairwise = 0.0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                pairwise += float(np.linalg.norm(vectors[i] - vectors[j]))
                count += 1
        return pairwise / max(count, 1)

    def run(self, generations: int = 50) -> EvolutionResult:
        """Run the evolutionary algorithm.

        Parameters
        ----------
        generations : int
            Number of generations to evolve.

        Returns
        -------
        EvolutionResult with best genome, fitness, config, and history.
        """
        population = self._init_population()
        history: List[Dict[str, Any]] = []

        for gen in range(generations):
            population.sort(key=lambda x: x[1], reverse=True)

            best_genome, best_fitness = population[0]
            avg_fitness = float(np.mean([f for _, f in population]))
            worst_fitness = population[-1][1]
            diversity = self._compute_diversity(population)

            history.append({
                "generation": gen,
                "best_fitness": best_fitness,
                "avg_fitness": round(avg_fitness, 4),
                "worst_fitness": worst_fitness,
                "diversity": round(diversity, 4),
            })

            # Build next generation
            new_pop: List[Tuple[MusicalGenome, float]] = []

            # Elitism
            for i in range(min(self.elitism, len(population))):
                new_pop.append(population[i])

            # Fill rest with crossover + mutation
            while len(new_pop) < self.population_size:
                parent_a = tournament_select(population, k=3, rng=self.rng)
                parent_b = tournament_select(population, k=3, rng=self.rng)
                child = crossover(parent_a, parent_b, rng=self.rng)
                child = mutate_genome(child, self.mutation_rate,
                                      self.mutation_scale, rng=self.rng)
                config = child.to_config()
                novelty = diversity / 100.0
                fitness = evaluate_fitness(config, self.target_genre, novelty)
                new_pop.append((child, fitness))

            population = new_pop

        # Final sort
        population.sort(key=lambda x: x[1], reverse=True)
        best_genome, best_fitness = population[0]
        best_config = best_genome.to_config()

        return EvolutionResult(
            best_genome=best_genome,
            best_fitness=best_fitness,
            best_config=best_config,
            history=history,
            final_population=population,
        )


# ---------------------------------------------------------------------------
# Multi-genre experiment
# ---------------------------------------------------------------------------

def run_multi_genre_experiment(
    genres: Optional[List[str]] = None,
    population_size: int = 100,
    generations: int = 50,
    seed: int = 42,
) -> Dict[str, EvolutionResult]:
    """Run evolution for multiple genres and return results."""
    genres = genres or list(GENRE_TARGETS.keys())
    results = {}
    for genre in genres:
        evo = MusicalEvolution(
            target_genre=genre,
            population_size=population_size,
            seed=seed,
        )
        results[genre] = evo.run(generations=generations)
    return results


# ---------------------------------------------------------------------------
# Main: demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Musical Genome Evolution")
    print("=" * 60)

    for genre in ["jazz", "classical", "electronic", "ambient"]:
        print(f"\n--- Evolving toward {genre} ---")
        evo = MusicalEvolution(target_genre=genre, population_size=100, seed=42)
        result = evo.run(generations=50)

        print(f"  Best fitness: {result.best_fitness:.4f}")
        print(f"  Evolved BPM: {result.best_config.get('bpm', 0):.1f}")
        print(f"  Snap strength: {result.best_config.get('snap_strength', 0):.3f}")
        print(f"  Swing ratio: {result.best_config.get('swing_ratio', 0):.3f}")
        print(f"  Coupling: {result.best_config.get('coupling_alpha', 0):.3f}")

        # Show evolution trajectory
        if len(result.history) > 0:
            first = result.history[0]
            last = result.history[-1]
            print(f"  Fitness: {first['best_fitness']:.4f} → {last['best_fitness']:.4f}")
            print(f"  Diversity: {first['diversity']:.2f} → {last['diversity']:.2f}")

    print("\n" + "=" * 60)
    print("Done. Musical genomes evolved to genre-specific attractors.")
    print("=" * 60)
