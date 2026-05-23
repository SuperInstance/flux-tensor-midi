"""
Constraint Impedance Matching.
Tools for measuring and optimizing the match between constraint strength and system responsiveness.

The core insight: constraints transfer creative energy to a system, but maximum transfer
happens when constraint impedance matches system impedance — just like electrical
impedance matching maximizes power transfer. Mismatched impedance means wasted creative
potential: too strong and the system is crushed, too weak and nothing happens.

This module provides:
- ImpedanceProfile: models a creative system's resistance to change across 5 dimensions
- ConstraintForce: models a constraint's strength across the same dimensions
- Transfer efficiency, resonance, Q-factor calculations
- ConstraintReverb: models how long ideas bounce around in a creative space
- ImpedanceMatcher: manages genre profiles and finds optimal constraints
- Preset genre impedance profiles for common genres
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Callable, Optional, Dict, Tuple


@dataclass
class ImpedanceProfile:
    """The impedance (resistance to change) profile of a creative system.

    Each dimension represents how resistant the system is to changes of that type.
    High impedance = very resistant (rigid, established patterns).
    Low impedance = very responsive (flexible, experimental).

    Dimensions:
        snap_impedance: resistance to pitch/quantization changes (note choices)
        funnel_impedance: resistance to convergence pressure (narrowing options)
        consensus_impedance: resistance to social/structural agreement (harmony rules)
        laman_impedance: resistance to structural deformation (form/arrangement changes)
        tempo_impedance: resistance to tempo/timing changes (rhythmic flexibility)
    """
    name: str
    snap_impedance: float = 1.0
    funnel_impedance: float = 1.0
    consensus_impedance: float = 1.0
    laman_impedance: float = 1.0
    tempo_impedance: float = 1.0

    @property
    def total_impedance(self) -> float:
        """Overall system impedance (Euclidean norm of impedance vector)."""
        return float(np.sqrt(
            self.snap_impedance**2 + self.funnel_impedance**2 +
            self.consensus_impedance**2 + self.laman_impedance**2 +
            self.tempo_impedance**2
        ))

    @property
    def impedance_vector(self) -> np.ndarray:
        """Impedance as a 5D vector."""
        return np.array([
            self.snap_impedance, self.funnel_impedance,
            self.consensus_impedance, self.laman_impedance,
            self.tempo_impedance
        ])

    @property
    def dominant_dimension(self) -> str:
        """Which dimension has the highest impedance."""
        dims = ['snap', 'funnel', 'consensus', 'laman', 'tempo']
        idx = int(np.argmax(self.impedance_vector))
        return dims[idx]

    @property
    def flexibility(self) -> float:
        """Inverse of total impedance — how flexible/responsive the system is."""
        return 1.0 / (self.total_impedance + 1e-10)

    def normalized_vector(self) -> np.ndarray:
        """Impedance vector normalized to unit length."""
        v = self.impedance_vector
        return v / (np.linalg.norm(v) + 1e-10)

    def impedance_ratio(self, dimension: str) -> float:
        """How much of total impedance is in one dimension (0 to 1)."""
        dim_map = {
            'snap': self.snap_impedance,
            'funnel': self.funnel_impedance,
            'consensus': self.consensus_impedance,
            'laman': self.laman_impedance,
            'tempo': self.tempo_impedance,
        }
        val = dim_map.get(dimension, 0.0)
        return val / (self.total_impedance + 1e-10)


@dataclass
class ConstraintForce:
    """A constraint applied to a system.

    Each dimension represents how strongly the constraint pushes in that direction.
    High strength = very forceful constraint (tight quantization, strict harmony).
    Low strength = gentle constraint (loose quantization, open harmony).

    Attributes:
        frequency: how often the constraint is applied — affects resonance with
                   the system's natural frequency.
    """
    name: str
    snap_strength: float = 0.0
    funnel_strength: float = 0.0
    consensus_strength: float = 0.0
    laman_strength: float = 0.0
    tempo_strength: float = 0.0
    frequency: float = 1.0

    @property
    def strength_vector(self) -> np.ndarray:
        """Constraint strength as a 5D vector."""
        return np.array([
            self.snap_strength, self.funnel_strength,
            self.consensus_strength, self.laman_strength,
            self.tempo_strength
        ])

    @property
    def total_strength(self) -> float:
        """Total constraint force magnitude."""
        return float(np.linalg.norm(self.strength_vector))

    def matched_force(self, system: ImpedanceProfile) -> 'ConstraintForce':
        """Return a new force matched to the system's impedance for max transfer."""
        return ConstraintForce(
            name=f"{self.name}_matched_to_{system.name}",
            snap_strength=system.snap_impedance,
            funnel_strength=system.funnel_impedance,
            consensus_strength=system.consensus_impedance,
            laman_strength=system.laman_impedance,
            tempo_strength=system.tempo_impedance,
            frequency=self.frequency,
        )


def transfer_efficiency(force: ConstraintForce, system: ImpedanceProfile) -> float:
    """
    Power transfer from constraint to system.

    Based on the maximum power transfer theorem:
    P = 4*Z_C*Z_S / (Z_C + Z_S)^2

    Maximum transfer (1.0) occurs when constraint strength = system impedance
    along each dimension.
    """
    z_c = np.abs(force.strength_vector)
    z_s = system.impedance_vector

    # Per-dimension transfer
    transfers = 4 * z_c * z_s / (z_c + z_s + 1e-10)**2

    # Weighted average (weighted by constraint strength)
    weights = z_c / (np.sum(z_c) + 1e-10)
    return float(np.sum(transfers * weights))


def resonance_score(force: ConstraintForce, system: ImpedanceProfile,
                    system_natural_freq: float = 1.0) -> float:
    """
    How close is the constraint frequency to the system's natural frequency?

    Resonance amplifies constraint effect. Returns a value in [0, 1] where
    1.0 means perfect resonance.
    """
    delta_freq = abs(force.frequency - system_natural_freq)
    bandwidth = system_natural_freq * 0.3  # Q factor ~ 3
    return float(np.exp(-delta_freq**2 / (2 * bandwidth**2)))


def reflection_coefficient(force: ConstraintForce, system: ImpedanceProfile) -> np.ndarray:
    """
    Reflection coefficient per dimension: how much constraint energy bounces back.

    gamma = (Z_S - Z_C) / (Z_S + Z_C)
    """
    z_c = np.abs(force.strength_vector)
    z_s = system.impedance_vector
    return (z_s - z_c) / (z_s + z_c + 1e-10)


def standing_wave_ratio(force: ConstraintForce, system: ImpedanceProfile) -> np.ndarray:
    """
    Standing wave ratio per dimension: measure of impedance mismatch.

    SWR = (1 + |gamma|) / (1 - |gamma|)
    SWR of 1.0 = perfect match, higher = worse mismatch.
    """
    gamma = np.abs(reflection_coefficient(force, system))
    # Clamp gamma to avoid division by zero
    gamma = np.clip(gamma, 0, 0.999)
    return (1 + gamma) / (1 - gamma)


def find_sweet_spot(system: ImpedanceProfile,
                    freq_range: Tuple[float, float] = (0.1, 10.0),
                    strength_range: Tuple[float, float] = (0.1, 5.0),
                    resolution: int = 20) -> Dict:
    """
    Find the optimal constraint parameters for maximum creative transfer.

    Searches over frequency and snap_strength space while matching other
    dimensions to the system's impedance.
    """
    best_efficiency = 0
    best_params = None
    best_resonance = 0

    freqs = np.linspace(freq_range[0], freq_range[1], resolution * 5)
    strengths = np.linspace(strength_range[0], strength_range[1], resolution)

    for freq in freqs:
        for snap in strengths:
            force = ConstraintForce(
                name="optimal",
                snap_strength=snap,
                funnel_strength=system.funnel_impedance,
                consensus_strength=system.consensus_impedance,
                laman_strength=system.laman_impedance,
                tempo_strength=system.tempo_impedance,
                frequency=freq
            )

            eff = transfer_efficiency(force, system)
            res = resonance_score(force, system, freq)
            total = eff * res

            if total > best_efficiency:
                best_efficiency = total
                best_resonance = res
                best_params = force

    return {
        'best_efficiency': best_efficiency,
        'best_resonance': best_resonance,
        'best_constraint': best_params,
        'system_impedance': system.total_impedance,
    }


def quality_factor(system: ImpedanceProfile) -> float:
    """
    Q factor: how specialized is this system?

    High Q = responds only to specific constraints (specialist).
    Low Q = responds to many constraints (generalist).

    Q = mean_impedance / bandwidth, where bandwidth ~ std of impedance.
    """
    z = system.impedance_vector
    mean_z = np.mean(z)
    std_z = np.std(z)
    return float(mean_z / (std_z + 1e-10))


def bandwidth(system: ImpedanceProfile) -> float:
    """
    Effective bandwidth of a system — how wide a range of constraints it responds to.

    Inverse of Q factor (proportional).
    """
    return 1.0 / (quality_factor(system) + 1e-10)


def impedance_spectrum(system: ImpedanceProfile, freqs: np.ndarray = None) -> np.ndarray:
    """
    Compute the impedance magnitude spectrum of a system across frequencies.

    Models each dimension as a damped resonator. Returns impedance magnitude
    at each frequency.
    """
    if freqs is None:
        freqs = np.linspace(0.1, 10.0, 200)

    z = system.impedance_vector
    natural_freqs = z / (np.max(z) + 1e-10) * 5.0  # scale to [0, 5]
    damping = 0.3 * np.ones(5)

    spectrum = np.zeros(len(freqs))
    for i in range(5):
        omega = 2 * np.pi * freqs
        omega_0 = 2 * np.pi * natural_freqs[i]
        zeta = damping[i]
        response = z[i] / np.sqrt((1 - (omega/omega_0)**2)**2 + (2*zeta*omega/omega_0)**2 + 1e-10)
        spectrum += response

    return spectrum


@dataclass
class ConstraintReverb:
    """
    Manage creative reverberation — how long ideas bounce around.

    Based on the Sabine equation from room acoustics, applied to creative spaces.
    Longer reverb = ideas persist and interact more.
    Shorter reverb = ideas are quickly absorbed (more controlled).

    Attributes:
        volume: size of creative space (larger = more room for ideas)
        surface_area: number of constraint boundaries
        absorption: how much each boundary absorbs (0 = fully reflective, 1 = fully absorptive)
    """
    volume: float = 1.0
    surface_area: float = 10.0
    absorption: float = 0.3

    @property
    def reverb_time(self) -> float:
        """Sabine equation: T60 = 0.161 * V / (A * alpha)"""
        return 0.161 * self.volume / (self.surface_area * self.absorption + 1e-10)

    @property
    def clarity_index(self) -> float:
        """C50 clarity index: ratio of early to late energy."""
        early_time = 0.05  # 50ms equivalent
        if self.reverb_time < early_time:
            return 10.0  # very clear
        late_ratio = np.exp(-early_time / (self.reverb_time / 6.0))
        return float(10 * np.log10((1 - late_ratio) / (late_ratio + 1e-10)))

    def optimize_for_phase(self, phase: str) -> 'ConstraintReverb':
        """Return optimized reverb for creative phase.

        brainstorm: big space, low absorption (ideas bounce freely)
        develop: moderate space, moderate absorption (some structure)
        edit: small space, high absorption (tight focus)
        """
        if phase == "brainstorm":
            return ConstraintReverb(volume=10.0, surface_area=5.0, absorption=0.1)
        elif phase == "develop":
            return ConstraintReverb(volume=5.0, surface_area=10.0, absorption=0.3)
        elif phase == "edit":
            return ConstraintReverb(volume=2.0, surface_area=20.0, absorption=0.8)
        elif phase == "perform":
            return ConstraintReverb(volume=3.0, surface_area=15.0, absorption=0.5)
        elif phase == "explore":
            return ConstraintReverb(volume=8.0, surface_area=3.0, absorption=0.05)
        return self

    def decay_curve(self, duration: float = 2.0, sample_rate: int = 100) -> np.ndarray:
        """Generate a decay curve for creative energy over time."""
        t = np.linspace(0, duration, int(duration * sample_rate))
        if self.reverb_time <= 0:
            return np.zeros_like(t)
        # Exponential decay: energy drops 60dB over reverb_time
        decay_rate = 6.91 / self.reverb_time  # ln(1000) ≈ 6.91
        return np.exp(-decay_rate * t)

    def echo_density(self) -> float:
        """How many distinct idea reflections per unit time."""
        return self.surface_area / (self.volume + 1e-10)


class ImpedanceMatcher:
    """Tool for matching constraint impedance to system impedance.

    Manages a registry of genre impedance profiles and provides tools
    for finding optimal constraints, measuring compatibility, and blending genres.
    """

    def __init__(self):
        self.profiles: Dict[str, ImpedanceProfile] = {}
        self.forces: Dict[str, ConstraintForce] = {}

    def register_genre(self, name: str, snap: float, funnel: float,
                       consensus: float, laman: float, tempo: float):
        """Register a genre's impedance profile."""
        self.profiles[name] = ImpedanceProfile(
            name=name,
            snap_impedance=snap,
            funnel_impedance=funnel,
            consensus_impedance=consensus,
            laman_impedance=laman,
            tempo_impedance=tempo
        )

    def register_force(self, name: str, snap: float, funnel: float,
                       consensus: float, laman: float, tempo: float,
                       frequency: float = 1.0):
        """Register a named constraint force."""
        self.forces[name] = ConstraintForce(
            name=name,
            snap_strength=snap,
            funnel_strength=funnel,
            consensus_strength=consensus,
            laman_strength=laman,
            tempo_strength=tempo,
            frequency=frequency
        )

    def best_constraint_for(self, genre: str) -> Optional[Dict]:
        """Find the constraint that transfers most energy to this genre."""
        if genre not in self.profiles:
            return None
        return find_sweet_spot(self.profiles[genre])

    def impedance_mismatch(self, source: str, target: str) -> float:
        """How different are two genres' impedances? Lower = more compatible."""
        if source not in self.profiles or target not in self.profiles:
            return float('inf')
        return float(np.linalg.norm(
            self.profiles[source].impedance_vector -
            self.profiles[target].impedance_vector
        ))

    def compatibility_matrix(self) -> Dict[str, Dict[str, float]]:
        """Full pairwise compatibility matrix. Values are transfer efficiency."""
        genres = list(self.profiles.keys())
        matrix: Dict[str, Dict[str, float]] = {}
        for g1 in genres:
            matrix[g1] = {}
            for g2 in genres:
                # Use g1's impedance matched to g2's impedance
                force = ConstraintForce(
                    name=f"{g1}_to_{g2}",
                    snap_strength=self.profiles[g1].snap_impedance,
                    funnel_strength=self.profiles[g1].funnel_impedance,
                    consensus_strength=self.profiles[g1].consensus_impedance,
                    laman_strength=self.profiles[g1].laman_impedance,
                    tempo_strength=self.profiles[g1].tempo_impedance,
                )
                matrix[g1][g2] = transfer_efficiency(force, self.profiles[g2])
        return matrix

    def genre_blend_impedance(self, genres: List[str],
                              weights: Optional[List[float]] = None) -> ImpedanceProfile:
        """Impedance of a blend of genres, weighted average."""
        if weights is None:
            weights = [1.0] * len(genres)
        vectors = [self.profiles[g].impedance_vector
                   for g in genres if g in self.profiles]
        valid_weights = weights[:len(vectors)]
        if not vectors:
            return ImpedanceProfile(name="empty")
        blended = np.average(vectors, axis=0, weights=valid_weights)
        return ImpedanceProfile(
            name="+".join(genres),
            snap_impedance=float(blended[0]),
            funnel_impedance=float(blended[1]),
            consensus_impedance=float(blended[2]),
            laman_impedance=float(blended[3]),
            tempo_impedance=float(blended[4])
        )

    def most_compatible_pair(self) -> Optional[Tuple[str, str, float]]:
        """Find the two most impedance-matched genres."""
        genres = list(self.profiles.keys())
        if len(genres) < 2:
            return None
        best = (None, None, float('inf'))
        for i, g1 in enumerate(genres):
            for g2 in genres[i+1:]:
                mismatch = self.impedance_mismatch(g1, g2)
                if mismatch < best[2]:
                    best = (g1, g2, mismatch)
        return best

    def least_compatible_pair(self) -> Optional[Tuple[str, str, float]]:
        """Find the two least impedance-matched genres."""
        genres = list(self.profiles.keys())
        if len(genres) < 2:
            return None
        worst = (None, None, -1.0)
        for i, g1 in enumerate(genres):
            for g2 in genres[i+1:]:
                mismatch = self.impedance_mismatch(g1, g2)
                if mismatch > worst[2]:
                    worst = (g1, g2, mismatch)
        return worst

    def load_presets(self):
        """Load preset genre impedances."""
        for name, vals in GENRE_IMPEDANCES.items():
            self.register_genre(name, **vals)


# Preset genre impedances
GENRE_IMPEDANCES = {
    'jazz':       {'snap': 2.0, 'funnel': 3.0, 'consensus': 4.0, 'laman': 2.0, 'tempo': 3.0},
    'classical':  {'snap': 4.0, 'funnel': 5.0, 'consensus': 5.0, 'laman': 5.0, 'tempo': 4.0},
    'blues':      {'snap': 1.5, 'funnel': 2.0, 'consensus': 2.0, 'laman': 1.5, 'tempo': 2.5},
    'rock':       {'snap': 3.0, 'funnel': 2.5, 'consensus': 3.0, 'laman': 3.0, 'tempo': 4.0},
    'hiphop':     {'snap': 4.0, 'funnel': 1.5, 'consensus': 3.5, 'laman': 2.0, 'tempo': 5.0},
    'electronic': {'snap': 5.0, 'funnel': 2.0, 'consensus': 2.0, 'laman': 4.0, 'tempo': 5.0},
    'folk':       {'snap': 1.5, 'funnel': 3.0, 'consensus': 2.5, 'laman': 2.0, 'tempo': 1.5},
    'metal':      {'snap': 5.0, 'funnel': 2.0, 'consensus': 4.0, 'laman': 5.0, 'tempo': 5.0},
    'ambient':    {'snap': 1.0, 'funnel': 4.0, 'consensus': 1.5, 'laman': 1.0, 'tempo': 1.0},
    'country':    {'snap': 3.0, 'funnel': 2.5, 'consensus': 3.0, 'laman': 2.5, 'tempo': 2.5},
}


def analyze_all_genres() -> Dict:
    """
    Run a full impedance analysis on all preset genres.

    Returns a dict with per-genre analysis and cross-genre compatibility.
    """
    matcher = ImpedanceMatcher()
    matcher.load_presets()

    genre_analysis = {}
    for name, profile in matcher.profiles.items():
        sweet = find_sweet_spot(profile)
        genre_analysis[name] = {
            'total_impedance': profile.total_impedance,
            'dominant_dimension': profile.dominant_dimension,
            'quality_factor': quality_factor(profile),
            'bandwidth': bandwidth(profile),
            'flexibility': profile.flexibility,
            'impedance_vector': profile.impedance_vector.tolist(),
            'sweet_spot_efficiency': sweet['best_efficiency'],
            'sweet_spot_resonance': sweet['best_resonance'],
        }

    # Cross-genre compatibility
    compatibility = {}
    genres = list(matcher.profiles.keys())
    for g1 in genres:
        for g2 in genres:
            if g1 >= g2:
                continue
            mismatch = matcher.impedance_mismatch(g1, g2)
            # Transfer efficiency from g1's force to g2's system
            force = ConstraintForce(
                name=f"{g1}_force",
                snap_strength=matcher.profiles[g1].snap_impedance,
                funnel_strength=matcher.profiles[g1].funnel_impedance,
                consensus_strength=matcher.profiles[g1].consensus_impedance,
                laman_strength=matcher.profiles[g1].laman_impedance,
                tempo_strength=matcher.profiles[g1].tempo_impedance,
            )
            eff = transfer_efficiency(force, matcher.profiles[g2])
            compatibility[f"{g1}<->{g2}"] = {
                'mismatch': mismatch,
                'transfer_efficiency': eff,
            }

    most = matcher.most_compatible_pair()
    least = matcher.least_compatible_pair()

    # Genre rankings
    by_impedance = sorted(genres, key=lambda g: matcher.profiles[g].total_impedance)
    by_flexibility = sorted(genres, key=lambda g: matcher.profiles[g].flexibility, reverse=True)
    by_q = sorted(genres, key=lambda g: quality_factor(matcher.profiles[g]))

    return {
        'genre_analysis': genre_analysis,
        'compatibility': compatibility,
        'most_compatible': {'genres': (most[0], most[1]), 'mismatch': most[2]} if most else None,
        'least_compatible': {'genres': (least[0], least[1]), 'mismatch': least[2]} if least else None,
        'rankings': {
            'by_impedance_low_to_high': by_impedance,
            'by_flexibility_high_to_low': by_flexibility,
            'by_q_specialist_to_generalist': by_q,
        },
    }
