"""
Embryonic music development — a musical organism that GROWS from a single
cell through cell division, differentiation, and morphogenesis.

Maps the deepest biology→music transfer:
  - Zygote: single stem cell (initial musical idea)
  - Cleavage: rapid cell division (piece gets bigger)
  - Morphogen gradients: patterning signals (spatial character)
  - Differentiation: cells become bass/drums/melody/harmony
  - Gastrulation: cell layers form (musical sections)
  - Organogenesis: organs develop (arrangement structure)
  - Apoptosis: weak cells die (pruning weak material)
  - Homeobox genes: body-plan control (form/structure)

NON-PRE-CALCULABLE: the final composition depends on the ENTIRE developmental
trajectory — morphogen timing, division order, stochastic differentiation.
Same zygote genome with different morphogen timing produces a completely
different composition, just as identical genomes can produce different
phenotypes under different developmental conditions.

Usage:
    from flux_tensor_midi.embryonic import MusicalEmbryo
    embryo = MusicalEmbryo(seed_genome=[0.5]*25)
    arrangement = embryo.develop(timesteps=120)
    events = arrangement.to_midi_events()
"""

from __future__ import annotations

import math
import random
import copy
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable, Set

from flux_tensor_midi.tracks import Arrangement, Track


# ── Constants ────────────────────────────────────────────────────────────────

GENOME_SIZE = 25

# Gene index constants
GENE_CONSENSUS = 0
GENE_GRAVITY = 1
GENE_BRIGHTNESS = 2
GENE_RHYTHM = 3
GENE_MELODY = 4
GENE_HARMONY = 5
GENE_DENSITY = 6
GENE_VELOCITY = 7
GENE_DURATION = 8
GENE_SILENCE = 9
GENE_DISSONANCE = 10
GENE_REPETITION = 11
GENE_TRANSPOSITION = 12
GENE_INVERSION = 13
GENE_RETROGRADE = 14
GENE_REGISTER = 15
GENE_INTERVAL = 16
GENE_TENSION = 17
GENE_RELEASE = 18
GENE_ARTICULATION = 19
GENE_TIMBRE = 20
GENE_SPACE = 21
GENE_GROWTH = 22
GENE_ADHESION = 23
GENE_APOPTOSIS = 24

# Morphogen names
MORPHOGEN_GRAVITY = "gravity"
MORPHOGEN_BRIGHTNESS = "brightness"
MORPHOGEN_RHYTHM = "rhythm"
MORPHOGEN_MELODY = "melody"
MORPHOGEN_HARMONY = "harmony"
MORPHOGEN_GROWTH = "growth"
MORPHOGEN_DEATH = "death"

# Cell roles
ROLE_UNDIFFERENTIATED = "undifferentiated"
ROLE_BASS = "bass"
ROLE_TREBLE = "treble"
ROLE_PERCUSSION = "percussion"
ROLE_LEAD = "lead"
ROLE_HARMONY_ROLE = "harmony"
ROLE_PAD = "pad"
ROLE_ARPEGGIO = "arpeggio"

# Developmental stages
STAGE_ZYGOTE = "zygote"
STAGE_CLEAVAGE = "cleavage"
STAGE_BLASTULA = "blastula"
STAGE_GASTRULATION = "gastrulation"
STAGE_ORGANOGENESIS = "organogenesis"
STAGE_MATURE = "mature"

# HOX gene regions
HOX_A = "HOX-A"
HOX_B = "HOX-B"
HOX_C = "HOX-C"
HOX_D = "HOX-D"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sigmoid(x: float, k: float = 1.0, midpoint: float = 0.5) -> float:
    arg = -k * (x - midpoint)
    arg = max(-50.0, min(50.0, arg))
    return 1.0 / (1.0 + math.exp(arg))


def _gaussian(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    return math.exp(-0.5 * ((x - mu) / max(sigma, 1e-9)) ** 2)


def _distance(p1: Tuple[float, ...], p2: Tuple[float, ...]) -> float:
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * max(0.0, min(1.0, t))


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Morphogen
# ---------------------------------------------------------------------------

@dataclass
class Morphogen:
    """Chemical gradient that patterns the embryo."""
    name: str
    source: Tuple[float, ...]
    diffusion_rate: float = 0.1
    degradation_rate: float = 0.02
    initial_concentration: float = 1.0
    _concentration_field: Optional[Dict[Tuple[float, ...], float]] = field(default=None, repr=False)

    def concentration_at(self, position: Tuple[float, ...]) -> float:
        dist = _distance(self.source, position)
        conc = self.initial_concentration * math.exp(-dist * (1.0 - self.diffusion_rate))
        conc *= (1.0 - self.degradation_rate)
        return max(0.0, conc)

    def diffuse(self, positions: List[Tuple[float, ...]], dt: float = 1.0):
        if self._concentration_field is None:
            self._concentration_field = {}
        for pos in positions:
            current = self._concentration_field.get(pos, 0.0)
            source_contribution = self.concentration_at(pos) * dt * self.diffusion_rate
            decay = current * self.degradation_rate * dt
            self._concentration_field[pos] = max(0.0, current + source_contribution - decay)

    def get_field_at(self, position: Tuple[float, ...]) -> float:
        if self._concentration_field is None:
            return 0.0
        return self._concentration_field.get(position, 0.0)


# ---------------------------------------------------------------------------
# StemCell
# ---------------------------------------------------------------------------

@dataclass
class StemCell:
    """Undifferentiated musical cell — can become any musical role."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    genome: List[float] = field(default_factory=lambda: [random.gauss(0.5, 0.1) for _ in range(GENOME_SIZE)])
    signals: Dict[str, float] = field(default_factory=dict)
    neighbors: List[str] = field(default_factory=list)
    position: Tuple[float, ...] = (0.0, 0.0)
    generation: int = 0
    role: str = ROLE_UNDIFFERENTIATED
    age: int = 0
    energy: float = 1.0
    alive: bool = True
    differentiation_threshold: float = 0.6
    _expressed_genes: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        self.genome = [_clamp(g) for g in self.genome]

    def divide(self, orientation: str = 'random') -> Tuple['StemCell', 'StemCell']:
        daughter_genome_1 = [_clamp(g + random.gauss(0, 0.02)) for g in self.genome]
        daughter_genome_2 = [_clamp(g + random.gauss(0, 0.02)) for g in self.genome]
        offset = self._division_offset(orientation)
        pos1 = tuple(p + o * 0.5 for p, o in zip(self.position, offset))
        pos2 = tuple(p - o * 0.5 for p, o in zip(self.position, offset))
        daughter1 = StemCell(genome=daughter_genome_1, position=pos1,
                             generation=self.generation + 1,
                             differentiation_threshold=self.differentiation_threshold,
                             energy=max(self.energy * 0.8, 0.3))
        daughter2 = StemCell(genome=daughter_genome_2, position=pos2,
                             generation=self.generation + 1,
                             differentiation_threshold=self.differentiation_threshold,
                             energy=max(self.energy * 0.8, 0.3))
        return daughter1, daughter2

    def _division_offset(self, orientation: str) -> Tuple[float, ...]:
        dims = len(self.position)
        if orientation == 'random':
            angle = random.uniform(0, 2 * math.pi)
            if dims >= 2:
                return (math.cos(angle) * 0.3, math.sin(angle) * 0.3)
            return tuple(random.gauss(0, 0.15) for _ in range(dims))
        elif orientation == 'horizontal':
            return tuple(0.3 if i == 0 else 0.0 for i in range(dims))
        elif orientation == 'vertical':
            return tuple(0.3 if i == 1 else 0.0 for i in range(dims))
        return tuple(random.gauss(0, 0.15) for _ in range(dims))

    def receive_signals(self, morphogens: List[Morphogen]):
        self.signals = {}
        for morphogen in morphogens:
            direct = morphogen.concentration_at(self.position)
            field_val = morphogen.get_field_at(self.position)
            self.signals[morphogen.name] = max(direct, field_val)

    def should_differentiate(self) -> bool:
        if self.role != ROLE_UNDIFFERENTIATED:
            return False
        if not self.signals:
            return False
        max_signal = max(self.signals.values())
        return max_signal >= self.differentiation_threshold and self.generation >= 2

    def differentiate(self, morphogens: Optional[List[Morphogen]] = None):
        if self.role != ROLE_UNDIFFERENTIATED:
            return
        role_scores = self._compute_role_scores()
        if not role_scores:
            self._genome_differentiation()
            return
        best_role = max(role_scores, key=role_scores.get)
        self.role = best_role
        self._express_role_genes()

    def _compute_role_scores(self) -> Dict[str, float]:
        scores = {}
        grav = self.signals.get(MORPHOGEN_GRAVITY, 0.0)
        bright = self.signals.get(MORPHOGEN_BRIGHTNESS, 0.0)
        rhythm = self.signals.get(MORPHOGEN_RHYTHM, 0.0)
        melody = self.signals.get(MORPHOGEN_MELODY, 0.0)
        harmony = self.signals.get(MORPHOGEN_HARMONY, 0.0)
        scores[ROLE_BASS] = grav * (0.6 + 0.4 * self.genome[GENE_GRAVITY])
        scores[ROLE_TREBLE] = bright * (0.6 + 0.4 * self.genome[GENE_BRIGHTNESS])
        scores[ROLE_PERCUSSION] = rhythm * (0.6 + 0.4 * self.genome[GENE_RHYTHM])
        scores[ROLE_LEAD] = melody * (0.6 + 0.4 * self.genome[GENE_MELODY])
        scores[ROLE_HARMONY_ROLE] = harmony * (0.6 + 0.4 * self.genome[GENE_HARMONY])
        scores[ROLE_PAD] = harmony * 0.5 + (1.0 - rhythm) * 0.3
        scores[ROLE_ARPEGGIO] = melody * 0.4 + rhythm * 0.3 + harmony * 0.2
        return scores

    def _genome_differentiation(self):
        gene_max_idx = max(range(GENOME_SIZE), key=lambda i: self.genome[i])
        role_map = {
            GENE_GRAVITY: ROLE_BASS, GENE_BRIGHTNESS: ROLE_TREBLE,
            GENE_RHYTHM: ROLE_PERCUSSION, GENE_MELODY: ROLE_LEAD,
            GENE_HARMONY: ROLE_HARMONY_ROLE, GENE_DENSITY: ROLE_ARPEGGIO,
            GENE_DURATION: ROLE_PAD,
        }
        self.role = role_map.get(gene_max_idx, random.choice(
            [ROLE_BASS, ROLE_TREBLE, ROLE_PERCUSSION, ROLE_LEAD, ROLE_HARMONY_ROLE]))
        self._express_role_genes()

    def _express_role_genes(self):
        self._expressed_genes = {}
        role = self.role
        if role == ROLE_BASS:
            self._expressed_genes = {
                'register_low': self.genome[GENE_GRAVITY],
                'density': self.genome[GENE_DENSITY] * 0.6,
                'velocity': self.genome[GENE_VELOCITY] * 0.9,
            }
        elif role == ROLE_TREBLE:
            self._expressed_genes = {
                'register_high': self.genome[GENE_BRIGHTNESS],
                'density': self.genome[GENE_DENSITY] * 0.8,
                'velocity': self.genome[GENE_VELOCITY] * 0.7,
            }
        elif role == ROLE_PERCUSSION:
            self._expressed_genes = {
                'rhythmic_density': self.genome[GENE_RHYTHM],
                'velocity': self.genome[GENE_VELOCITY],
                'timbre': self.genome[GENE_TIMBRE],
            }
        elif role == ROLE_LEAD:
            self._expressed_genes = {
                'melodic_interval': self.genome[GENE_INTERVAL],
                'velocity': self.genome[GENE_VELOCITY] * 0.8,
                'articulation': self.genome[GENE_ARTICULATION],
            }
        elif role == ROLE_HARMONY_ROLE:
            self._expressed_genes = {
                'harmonic_richness': self.genome[GENE_HARMONY],
                'density': self.genome[GENE_DENSITY] * 0.7,
                'dissonance': self.genome[GENE_DISSONANCE],
            }
        elif role == ROLE_PAD:
            self._expressed_genes = {
                'sustain': self.genome[GENE_DURATION],
                'harmonic_richness': self.genome[GENE_HARMONY] * 0.8,
                'velocity': self.genome[GENE_VELOCITY] * 0.5,
            }
        elif role == ROLE_ARPEGGIO:
            self._expressed_genes = {
                'rhythmic_density': self.genome[GENE_RHYTHM] * 0.7,
                'melodic_interval': self.genome[GENE_INTERVAL] * 0.6,
                'velocity': self.genome[GENE_VELOCITY] * 0.6,
            }

    def should_divide(self) -> bool:
        growth_signal = self.signals.get(MORPHOGEN_GROWTH, 0.0)
        return (growth_signal * self.genome[GENE_GROWTH] > 0.3) and self.energy > 0.4

    def should_die(self) -> bool:
        death_signal = self.signals.get(MORPHOGEN_DEATH, 0.0)
        apoptosis_threshold = 1.0 - self.genome[GENE_APOPTOSIS]
        if self.energy < 0.01:
            return True
        if death_signal > apoptosis_threshold and self.age > 5:
            return True
        return False

    def age_tick(self):
        self.age += 1
        self.energy = max(0.0, self.energy - 0.002)

    def compute_adhesion(self, other: 'StemCell') -> float:
        if not other.alive:
            return 0.0
        base = self.genome[GENE_ADHESION] * other.genome[GENE_ADHESION]
        if self.role == other.role and self.role != ROLE_UNDIFFERENTIATED:
            base *= 2.0
        return base

    def to_musical_events(self, tick: int, total_ticks: int) -> List[Dict]:
        if not self.alive or self.role == ROLE_UNDIFFERENTIATED:
            return []
        events = []
        expressed = self._expressed_genes
        if not expressed:
            return []
        time_pos = tick + int(self.position[0] * 8) if len(self.position) > 0 else tick

        if self.role == ROLE_BASS:
            pitch = int(24 + expressed.get('register_low', 0.5) * 24)
            vel = int(60 + expressed.get('velocity', 0.5) * 60)
            dur = max(1, int(expressed.get('density', 0.5) * 4))
            events.append({'pitch': pitch, 'velocity': vel, 'duration': dur, 'start': time_pos, 'role': 'bass'})
        elif self.role == ROLE_TREBLE:
            pitch = int(72 + expressed.get('register_high', 0.5) * 24)
            vel = int(40 + expressed.get('velocity', 0.5) * 60)
            dur = max(1, int(expressed.get('density', 0.5) * 3))
            events.append({'pitch': pitch, 'velocity': vel, 'duration': dur, 'start': time_pos, 'role': 'treble'})
        elif self.role == ROLE_PERCUSSION:
            vel = int(50 + expressed.get('velocity', 0.5) * 70)
            n_hits = max(1, int(expressed.get('rhythmic_density', 0.5) * 4))
            for i in range(n_hits):
                pitch = 36 + (i % 3) * 8
                events.append({'pitch': pitch, 'velocity': vel, 'duration': 1, 'start': time_pos + i, 'role': 'percussion'})
        elif self.role == ROLE_LEAD:
            pitch = int(60 + expressed.get('melodic_interval', 0.5) * 24)
            vel = int(50 + expressed.get('velocity', 0.5) * 60)
            dur = max(1, int(expressed.get('articulation', 0.5) * 4))
            events.append({'pitch': pitch, 'velocity': vel, 'duration': dur, 'start': time_pos, 'role': 'lead'})
        elif self.role == ROLE_HARMONY_ROLE:
            richness = expressed.get('harmonic_richness', 0.5)
            n_notes = max(2, int(richness * 5))
            base_pitch = int(48 + (self.position[0] * 12 if len(self.position) > 0 else 0))
            vel = int(40 + expressed.get('velocity', 0.5) * 50)
            dur = max(2, int(expressed.get('density', 0.5) * 6))
            for i in range(n_notes):
                events.append({'pitch': base_pitch + i * 4, 'velocity': vel, 'duration': dur, 'start': time_pos, 'role': 'harmony'})
        elif self.role == ROLE_PAD:
            vel = int(30 + expressed.get('velocity', 0.5) * 40)
            dur = max(4, int(expressed.get('sustain', 0.5) * 8))
            base_pitch = int(48 + (self.position[0] * 8 if len(self.position) > 0 else 0))
            for offset in [0, 4, 7]:
                events.append({'pitch': base_pitch + offset, 'velocity': vel, 'duration': dur, 'start': time_pos, 'role': 'pad'})
        elif self.role == ROLE_ARPEGGIO:
            n_notes = max(2, int(expressed.get('rhythmic_density', 0.5) * 6))
            vel = int(40 + expressed.get('velocity', 0.5) * 50)
            base_pitch = int(60 + (self.position[0] * 8 if len(self.position) > 0 else 0))
            pattern = [0, 4, 7, 12, 7, 4]
            for i in range(n_notes):
                events.append({'pitch': base_pitch + pattern[i % len(pattern)], 'velocity': vel, 'duration': 1, 'start': time_pos + i, 'role': 'arpeggio'})
        return events


# ---------------------------------------------------------------------------
# Homeobox
# ---------------------------------------------------------------------------

class Homeobox:
    """Homeobox genes control body plan — which sections develop where."""

    def __init__(self):
        self.genes = {
            HOX_A: {'density': 0.3, 'intensity': 0.3, 'growth': 0.5, 'death': 0.2},
            HOX_B: {'density': 0.6, 'intensity': 0.5, 'growth': 0.7, 'death': 0.1},
            HOX_C: {'density': 0.9, 'intensity': 0.9, 'growth': 0.8, 'death': 0.05},
            HOX_D: {'density': 0.3, 'intensity': 0.4, 'growth': 0.2, 'death': 0.4},
        }
        self.expression_pattern: List[str] = []

    def pattern(self, length: int) -> List[str]:
        self.expression_pattern = []
        quarter = max(1, length // 4)
        for i in range(length):
            if i < quarter:
                self.expression_pattern.append(HOX_A)
            elif i < quarter * 2:
                self.expression_pattern.append(HOX_B)
            elif i < quarter * 3:
                self.expression_pattern.append(HOX_C)
            else:
                self.expression_pattern.append(HOX_D)
        return self.expression_pattern

    def get_hox_params(self, position: int, total: int) -> Dict[str, float]:
        if not self.expression_pattern:
            self.pattern(total)
        position = max(0, min(len(self.expression_pattern) - 1, position))
        hox_gene = self.expression_pattern[position]
        return dict(self.genes[hox_gene])

    def mutate(self, rate: float = 0.05):
        for params in self.genes.values():
            for key in params:
                if random.random() < rate:
                    params[key] = _clamp(params[key] + random.gauss(0, 0.1))


# ---------------------------------------------------------------------------
# MusicalEmbryo
# ---------------------------------------------------------------------------

class MusicalEmbryo:
    """A musical composition that GROWS from a single cell."""

    def __init__(self, seed_genome: Optional[List[float]] = None,
                 dimensions: int = 2, max_cells: int = 200,
                 random_seed: Optional[int] = None):
        if random_seed is not None:
            random.seed(random_seed)
        self.dimensions = dimensions
        self.max_cells = max_cells
        genome = seed_genome if seed_genome else [random.gauss(0.5, 0.15) for _ in range(GENOME_SIZE)]
        zygote = StemCell(genome=genome, position=tuple(0.0 for _ in range(dimensions)))
        self.cells: List[StemCell] = [zygote]
        self.cell_index: Dict[str, StemCell] = {zygote.id: zygote}
        self.morphogens: List[Morphogen] = []
        self.time: int = 0
        self.stage: str = STAGE_ZYGOTE
        self.homeobox = Homeobox()
        self._event_log: List[Dict] = []
        self._division_history: List[Tuple[int, str]] = []

    def _setup_morphogens(self):
        self.morphogens = []
        dims = self.dimensions
        self.morphogens.append(Morphogen(name=MORPHOGEN_GRAVITY,
            source=tuple(0.0 if i == 1 else -2.0 for i in range(dims)),
            diffusion_rate=0.15, degradation_rate=0.01))
        self.morphogens.append(Morphogen(name=MORPHOGEN_BRIGHTNESS,
            source=tuple(0.0 if i == 1 else 2.0 for i in range(dims)),
            diffusion_rate=0.15, degradation_rate=0.01))
        self.morphogens.append(Morphogen(name=MORPHOGEN_RHYTHM,
            source=tuple(0.0 for _ in range(dims)),
            diffusion_rate=0.2, degradation_rate=0.03))
        self.morphogens.append(Morphogen(name=MORPHOGEN_MELODY,
            source=tuple(1.0 if i == 0 else 0.5 for i in range(dims)),
            diffusion_rate=0.12, degradation_rate=0.02))
        self.morphogens.append(Morphogen(name=MORPHOGEN_HARMONY,
            source=tuple(-1.0 if i == 0 else 0.5 for i in range(dims)),
            diffusion_rate=0.12, degradation_rate=0.02))

    def tick(self):
        self.time += 1
        alive_cells = [c for c in self.cells if c.alive]
        positions = [c.position for c in alive_cells]

        for morphogen in self.morphogens:
            morphogen.diffuse(positions, dt=1.0)

        for cell in alive_cells:
            cell.receive_signals(self.morphogens)
            cell.age_tick()
            if self.dimensions >= 1:
                hox_pos = int((cell.position[0] + 3.0) / 6.0 * 100)
                hox_pos = max(0, min(99, hox_pos))
            else:
                hox_pos = 50
            hox_params = self.homeobox.get_hox_params(hox_pos, 100)
            cell.signals[MORPHOGEN_GROWTH] = hox_params.get('growth', 0.5)
            cell.signals[MORPHOGEN_DEATH] = hox_params.get('death', 0.1)

        for cell in alive_cells:
            if cell.should_differentiate():
                cell.differentiate(self.morphogens)

        new_cells: List[StemCell] = []
        for cell in alive_cells:
            if cell.should_divide() and len(self.cells) + len(new_cells) < self.max_cells:
                d1, d2 = cell.divide()
                new_cells.extend([d1, d2])
                cell.alive = False
                self._division_history.append((self.time, cell.id))

        self.cells.extend(new_cells)
        for nc in new_cells:
            self.cell_index[nc.id] = nc

        self._move_cells(alive_cells)

        for cell in [c for c in self.cells if c.alive]:
            if cell.should_die():
                cell.alive = False

        self._update_neighbors()
        self._update_stage()

    def _move_cells(self, cells: List[StemCell]):
        alive = [c for c in cells if c.alive]
        for cell in alive:
            if cell.role == ROLE_UNDIFFERENTIATED:
                continue
            fx, fy = 0.0, 0.0
            for other in alive:
                if other.id == cell.id or not other.alive:
                    continue
                dx = other.position[0] - cell.position[0]
                dy = other.position[1] - cell.position[1] if len(cell.position) > 1 else 0.0
                dist = math.sqrt(dx * dx + dy * dy) + 1e-9
                adhesion = cell.compute_adhesion(other)
                force = adhesion / (dist + 0.1) * 0.01
                fx += dx / dist * force
                fy += dy / dist * force
            fx += random.gauss(0, 0.02)
            fy += random.gauss(0, 0.02)
            new_pos = list(cell.position)
            new_pos[0] = _clamp(new_pos[0] + fx, -5.0, 5.0)
            if len(new_pos) > 1:
                new_pos[1] = _clamp(new_pos[1] + fy, -5.0, 5.0)
            cell.position = tuple(new_pos)

    def _update_neighbors(self):
        alive = [c for c in self.cells if c.alive]
        neighbor_radius = 1.0
        for cell in alive:
            cell.neighbors = []
            for other in alive:
                if other.id == cell.id:
                    continue
                if _distance(cell.position, other.position) < neighbor_radius:
                    cell.neighbors.append(other.id)

    def _update_stage(self):
        alive = [c for c in self.cells if c.alive]
        n = len(alive)
        differentiated = sum(1 for c in alive if c.role != ROLE_UNDIFFERENTIATED)
        if n <= 1:
            self.stage = STAGE_ZYGOTE
        elif n <= 8:
            self.stage = STAGE_CLEAVAGE
        elif n <= 32 and differentiated < n * 0.3:
            self.stage = STAGE_BLASTULA
        elif differentiated >= n * 0.3 and differentiated < n * 0.7:
            self.stage = STAGE_GASTRULATION
        elif differentiated >= n * 0.7:
            self.stage = STAGE_ORGANOGENESIS

    def get_stage(self) -> str:
        return self.stage

    def get_alive_cells(self) -> List[StemCell]:
        return [c for c in self.cells if c.alive]

    def get_differentiated_cells(self) -> List[StemCell]:
        return [c for c in self.cells if c.alive and c.role != ROLE_UNDIFFERENTIATED]

    def get_role_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for cell in self.get_alive_cells():
            dist[cell.role] = dist.get(cell.role, 0) + 1
        return dist

    def develop(self, timesteps: int = 100) -> 'EmbryonicArrangement':
        self._setup_morphogens()
        for step in range(timesteps):
            if step < 5 and self.stage in (STAGE_ZYGOTE, STAGE_CLEAVAGE):
                for cell in self.get_alive_cells():
                    cell.signals[MORPHOGEN_GROWTH] = 0.9
                    cell.energy = 1.0
            self.tick()
            self._evolve_morphogen_sources(step, timesteps)
        self.stage = STAGE_MATURE
        return self._to_arrangement()

    def _evolve_morphogen_sources(self, step: int, total: int):
        progress = step / max(total, 1)
        for morphogen in self.morphogens:
            if morphogen.name == MORPHOGEN_RHYTHM:
                morphogen.initial_concentration = 0.5 + 0.5 * math.sin(step * 0.3)
            elif morphogen.name == MORPHOGEN_GRAVITY:
                morphogen.initial_concentration = 0.3 + 0.7 * progress
            elif morphogen.name == MORPHOGEN_BRIGHTNESS:
                morphogen.initial_concentration = _gaussian(progress, 0.7, 0.2)

    def _to_arrangement(self) -> 'EmbryonicArrangement':
        return EmbryonicArrangement(self)

    def get_development_log(self) -> List[Dict]:
        return list(self._event_log)


# ---------------------------------------------------------------------------
# EmbryonicArrangement
# ---------------------------------------------------------------------------

class EmbryonicArrangement:
    def __init__(self, embryo: MusicalEmbryo):
        self.embryo = embryo
        self._events: Optional[List[Dict]] = None

    def collect_events(self) -> List[Dict]:
        if self._events is not None:
            return self._events
        events = []
        for cell in self.embryo.get_differentiated_cells():
            events.extend(cell.to_musical_events(0, self.embryo.time))
        events.sort(key=lambda e: e.get('start', 0))
        self._events = events
        return events

    def to_midi_events(self) -> list:
        return self.collect_events()

    def get_tracks_by_role(self) -> Dict[str, List[Dict]]:
        tracks: Dict[str, List[Dict]] = {}
        for ev in self.collect_events():
            role = ev.get('role', 'unknown')
            tracks.setdefault(role, []).append(ev)
        return tracks

    def summary(self) -> Dict:
        events = self.collect_events()
        return {
            'total_events': len(events),
            'alive_cells': len(self.embryo.get_alive_cells()),
            'differentiated_cells': len(self.embryo.get_differentiated_cells()),
            'role_distribution': self.embryo.get_role_distribution(),
            'developmental_time': self.embryo.time,
            'stage': self.embryo.stage,
            'total_divisions': len(self.embryo._division_history),
        }

    def to_arrangement(self) -> Optional[Arrangement]:
        try:
            arrangement = Arrangement(name="embryonic", bpm=120)
            return arrangement
        except Exception:
            return None


# ---------------------------------------------------------------------------
# EmbryonicEnsemble
# ---------------------------------------------------------------------------

class EmbryonicEnsemble:
    """Multiple embryos developing together with inter-embryo signaling."""

    def __init__(self, n_embryos: int = 3, random_seed: Optional[int] = None):
        if random_seed is not None:
            random.seed(random_seed)
        self.embryos: List[MusicalEmbryo] = []
        for i in range(n_embryos):
            genome = [random.gauss(0.5, 0.15) for _ in range(GENOME_SIZE)]
            self.embryos.append(MusicalEmbryo(seed_genome=genome))

    def develop(self, timesteps: int = 100) -> List[EmbryonicArrangement]:
        for embryo in self.embryos:
            embryo._setup_morphogens()
        for step in range(timesteps):
            for embryo in self.embryos:
                embryo.tick()
            if step % 5 == 0:
                self._cross_signal()
        for embryo in self.embryos:
            embryo.stage = STAGE_MATURE
        return [e._to_arrangement() for e in self.embryos]

    def _cross_signal(self):
        for i, ea in enumerate(self.embryos):
            for j, eb in enumerate(self.embryos):
                if i == j:
                    continue
                alive_a = ea.get_alive_cells()
                if not alive_a:
                    continue
                mean_pos = tuple(
                    sum(c.position[k] for c in alive_a) / len(alive_a)
                    for k in range(ea.dimensions))
                for morphogen in eb.morphogens:
                    morphogen.diffuse([mean_pos], dt=0.3)


# ---------------------------------------------------------------------------
# EmbryoVisualizer
# ---------------------------------------------------------------------------

class EmbryoVisualizer:
    @staticmethod
    def ascii_map(embryo: MusicalEmbryo, width: int = 40, height: int = 20) -> str:
        grid = [[' ' for _ in range(width)] for _ in range(height)]
        role_chars = {
            ROLE_UNDIFFERENTIATED: '.', ROLE_BASS: 'B', ROLE_TREBLE: 'T',
            ROLE_PERCUSSION: 'X', ROLE_LEAD: 'L', ROLE_HARMONY_ROLE: 'H',
            ROLE_PAD: 'P', ROLE_ARPEGGIO: 'A',
        }
        for cell in embryo.get_alive_cells():
            x = int((cell.position[0] + 5.0) / 10.0 * (width - 1)) if len(cell.position) > 0 else width // 2
            y = int((cell.position[1] + 5.0) / 10.0 * (height - 1)) if len(cell.position) > 1 else height // 2
            x = max(0, min(width - 1, x))
            y = max(0, min(height - 1, y))
            grid[y][x] = role_chars.get(cell.role, '?')
        lines = ['+' + '-' * width + '+']
        for row in grid:
            lines.append('|' + ''.join(row) + '|')
        lines.append('+' + '-' * width + '+')
        lines.append(f"Stage: {embryo.stage} | Cells: {len(embryo.get_alive_cells())} | Time: {embryo.time}")
        return '\n'.join(lines)

    @staticmethod
    def role_bar_chart(embryo: MusicalEmbryo, width: int = 30) -> str:
        dist = embryo.get_role_distribution()
        lines = []
        max_count = max(dist.values()) if dist else 1
        for role in [ROLE_BASS, ROLE_TREBLE, ROLE_PERCUSSION, ROLE_LEAD,
                     ROLE_HARMONY_ROLE, ROLE_PAD, ROLE_ARPEGGIO, ROLE_UNDIFFERENTIATED]:
            count = dist.get(role, 0)
            bar_len = int(count / max(max_count, 1) * width)
            lines.append(f"{role[:5]:5s} |{'#' * bar_len}{' ' * (width - bar_len)}| {count}")
        return '\n'.join(lines)

    @staticmethod
    def development_timeline(embryo: MusicalEmbryo) -> str:
        return (
            f"Development Timeline\n"
            f"  Final stage: {embryo.stage}\n"
            f"  Total timesteps: {embryo.time}\n"
            f"  Total divisions: {len(embryo._division_history)}\n"
            f"  Alive cells: {len(embryo.get_alive_cells())}\n"
            f"  Differentiated: {len(embryo.get_differentiated_cells())}\n"
            f"  Roles: {embryo.get_role_distribution()}"
        )
