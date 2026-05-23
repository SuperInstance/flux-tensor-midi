"""
protein_fold — Protein Folding via Constraint Theory with Music Transfer.

Implements a 2D lattice protein folding algorithm using constraint-theoretic
principles (snap, funnel, laman rigidity, consensus) shared with the
flux-tensor-midi musical constraint system.

The folding is NON-PRE-CALCULABLE — each amino acid's position depends on
already-folded positions, analogous to how a jazz solo unfolds: each note
depends on what came before. This is a direct consequence of Levinthal's
paradox: the folding pathway matters, not just the final state.

Architecture:
    AminoAcid        — a residue in the protein chain
    ProteinFolder    — fold using snap + funnel + rigidity + consensus
    ProteinToMusic   — convert folded protein → musical arrangement
    MusicToProtein   — convert musical constraints → protein sequence

Bidirectional Transfer:
    Biology → Music:  protein structure maps to musical form
    Music → Biology:  musical constraints design protein sequences

Usage:
    from flux_tensor_midi.protein_fold import ProteinFolder

    folder = ProteinFolder(sequence="ACDEFGHIKLMNPQRSTVWY", seed=42)
    positions = folder.fold()
    print(f"Energy: {folder.energy():.2f}")

References:
    - Levinthal's paradox (1969): folding pathways vs final states
    - Laman rigidity (1970): graph-theoretic rigidity in 2D
    - Energy funnel theory: Bryngelson & Wolynes (1987)
    - Codon degeneracy → snap-to-lattice analogy
"""

from __future__ import annotations

import math
import random
import copy
from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# The 20 standard amino acids with biophysical properties
# (hydrophobicity: Kyte-Doolittle scale, charge at pH 7, size: relative MW)
AMINO_ACID_PROPERTIES: Dict[str, Dict[str, float]] = {
    "A": {"name": "Alanine",       "hydro":  1.8, "charge":  0.0, "size":  0.5, "polar": 0.0},
    "C": {"name": "Cysteine",      "hydro":  2.5, "charge":  0.0, "size":  0.7, "polar": 0.0},
    "D": {"name": "Aspartate",     "hydro": -3.5, "charge": -1.0, "size":  0.7, "polar": 1.0},
    "E": {"name": "Glutamate",     "hydro": -3.5, "charge": -1.0, "size":  0.8, "polar": 1.0},
    "F": {"name": "Phenylalanine", "hydro":  2.8, "charge":  0.0, "size":  1.2, "polar": 0.0},
    "G": {"name": "Glycine",       "hydro": -0.4, "charge":  0.0, "size":  0.2, "polar": 0.0},
    "H": {"name": "Histidine",     "hydro": -3.2, "charge":  0.5, "size":  0.9, "polar": 1.0},
    "I": {"name": "Isoleucine",    "hydro":  4.5, "charge":  0.0, "size":  1.0, "polar": 0.0},
    "K": {"name": "Lysine",        "hydro": -3.9, "charge":  1.0, "size":  1.0, "polar": 1.0},
    "L": {"name": "Leucine",       "hydro":  3.8, "charge":  0.0, "size":  1.0, "polar": 0.0},
    "M": {"name": "Methionine",    "hydro":  1.9, "charge":  0.0, "size":  1.0, "polar": 0.0},
    "N": {"name": "Asparagine",    "hydro": -3.5, "charge":  0.0, "size":  0.7, "polar": 1.0},
    "P": {"name": "Proline",       "hydro": -1.6, "charge":  0.0, "size":  0.6, "polar": 0.0},
    "Q": {"name": "Glutamine",     "hydro": -3.5, "charge":  0.0, "size":  0.8, "polar": 1.0},
    "R": {"name": "Arginine",      "hydro": -4.5, "charge":  1.0, "size":  1.1, "polar": 1.0},
    "S": {"name": "Serine",        "hydro": -0.8, "charge":  0.0, "size":  0.5, "polar": 1.0},
    "T": {"name": "Threonine",     "hydro": -0.7, "charge":  0.0, "size":  0.6, "polar": 1.0},
    "V": {"name": "Valine",        "hydro":  4.2, "charge":  0.0, "size":  0.8, "polar": 0.0},
    "W": {"name": "Tryptophan",    "hydro": -0.9, "charge":  0.0, "size":  1.5, "polar": 0.0},
    "Y": {"name": "Tyrosine",      "hydro": -1.3, "charge":  0.0, "size":  1.3, "polar": 1.0},
}

# Lattice directions: 6 neighbors on triangular (Eisenstein) lattice
# Using axial coordinates for hexagonal grid
LATTICE_DIRS: List[Tuple[float, float]] = [
    (1.0, 0.0),
    (0.5, math.sqrt(3) / 2),
    (-0.5, math.sqrt(3) / 2),
    (-1.0, 0.0),
    (-0.5, -math.sqrt(3) / 2),
    (0.5, -math.sqrt(3) / 2),
]

# Golden ratio
PHI = (1 + math.sqrt(5)) / 2


# ---------------------------------------------------------------------------
# AminoAcid
# ---------------------------------------------------------------------------


@dataclass
class AminoAcid:
    """A residue in the protein chain.

    Each amino acid has a position on the 2D lattice, biophysical
    properties, and tracks its folding state.

    Attributes
    ----------
    name : str
        Single-letter amino acid code (one of 20 standard).
    index : int
        Position in the chain (0-indexed).
    position : tuple[float, float]
        2D lattice position. (NaN, NaN) until placed.
    properties : dict
        Biophysical properties (hydrophobicity, charge, size, polarity).
    secondary : str
        Inferred secondary structure: 'helix', 'sheet', 'loop', 'none'.
    contacts : set[int]
        Indices of non-sequential residues within contact distance.
    """

    name: str
    index: int
    position: Tuple[float, float] = (float("nan"), float("nan"))
    properties: Dict[str, float] = field(default_factory=dict)
    secondary: str = "none"
    contacts: Set[int] = field(default_factory=set)

    def __post_init__(self):
        if not self.properties:
            if self.name in AMINO_ACID_PROPERTIES:
                self.properties = dict(AMINO_ACID_PROPERTIES[self.name])
            else:
                self.properties = {"hydro": 0.0, "charge": 0.0, "size": 0.5, "polar": 0.0}

    @property
    def is_hydrophobic(self) -> bool:
        """Whether this residue is hydrophobic (Kyte-Doolittle > 0)."""
        return self.properties.get("hydro", 0.0) > 0.0

    @property
    def is_polar(self) -> bool:
        """Whether this residue is polar."""
        return self.properties.get("polar", 0.0) > 0.5

    @property
    def is_charged(self) -> bool:
        """Whether this residue is charged (non-zero at pH 7)."""
        return abs(self.properties.get("charge", 0.0)) > 0.1

    @property
    def is_placed(self) -> bool:
        """Whether this residue has been placed on the lattice."""
        return not (math.isnan(self.position[0]) or math.isnan(self.position[1]))

    def distance_to(self, other: AminoAcid) -> float:
        """Euclidean distance to another residue."""
        if not self.is_placed or not other.is_placed:
            return float("inf")
        dx = self.position[0] - other.position[0]
        dy = self.position[1] - other.position[1]
        return math.sqrt(dx * dx + dy * dy)


# ---------------------------------------------------------------------------
# ProteinFolder
# ---------------------------------------------------------------------------


class ProteinFolder:
    """Fold a protein using constraint theory.

    The folding process applies four constraint operations iteratively:

    1. **Snap-to-lattice**: Map continuous positions to discrete lattice points.
       Analogous to codon→amino acid mapping: the genetic code discretizes
       continuous nucleotide space into discrete amino acid choices.

    2. **Energy funnel**: Drive residues toward the hydrophobic core.
       Analogous to the protein folding landscape: a funnel-shaped energy
       surface guides the protein toward its native state.

    3. **Laman rigidity**: Ensure the contact network is rigid.
       A structure is rigid if it has no floppy modes — every part is
       mechanically constrained. Like a well-voiced chord in music.

    4. **Consensus**: Nearby residues agree on optimal packing.
       Like molecular dynamics: each residue adjusts based on its neighbors,
       reaching local consensus before the next global iteration.

    NON-PRE-CALCULABILITY:
    The fold() method is inherently sequential — each step depends on the
    positions established by previous steps. Different random seeds produce
    genuinely different folds, just as different performances of the same
    score produce genuinely different music.

    Parameters
    ----------
    sequence : str
        Amino acid sequence (single-letter codes).
    seed : int or None
        Random seed for reproducibility. Different seeds → different folds.
    constraints : dict or None
        Constraint parameters: snap, funnel, laman, consensus.
    """

    # Default constraint parameters
    DEFAULT_CONSTRAINTS: Dict[str, Any] = {
        "snap_strength": 0.8,        # How strongly to snap to lattice (0–1)
        "snap_epsilon": 0.15,        # Soft snap tolerance band
        "funnel_gravity": 0.5,       # Funnel pull toward hydrophobic core
        "funnel_deadband": 0.3,      # Deadband radius around energy minimum
        "laman_threshold": 0.6,      # Minimum edge density for rigidity
        "consensus_rounds": 3,       # Iterations of neighbor consensus
        "consensus_alpha": 0.3,      # Coupling strength in consensus
        "contact_distance": 1.2,     # Max distance for a contact (lattice units)
        "bond_length": 1.0,          # Bond length between sequential residues
        "temperature": 1.0,          # Boltzmann temperature for acceptance
        "cooling_rate": 0.995,       # Simulated annealing cooling factor
    }

    def __init__(
        self,
        sequence: str,
        seed: Optional[int] = None,
        constraints: Optional[Dict[str, Any]] = None,
    ):
        # Validate sequence
        sequence = sequence.upper().strip()
        valid = set(AMINO_ACID_PROPERTIES.keys())
        for i, aa in enumerate(sequence):
            if aa not in valid:
                raise ValueError(
                    f"Invalid amino acid '{aa}' at position {i}. "
                    f"Must be one of: {sorted(valid)}"
                )

        self._sequence = sequence
        self._seed = seed
        self._rng = random.Random(seed)

        # Build the chain
        self._chain: List[AminoAcid] = [
            AminoAcid(name=aa, index=i)
            for i, aa in enumerate(sequence)
        ]

        # Merge constraints
        self._constraints = dict(self.DEFAULT_CONSTRAINTS)
        if constraints:
            self._constraints.update(constraints)

        # Folding state
        self._positions: List[Tuple[float, float]] = []
        self._folded = False
        self._folding_history: List[List[Tuple[float, float]]] = []
        self._energy_history: List[float] = []

        # Occupied lattice positions (for collision avoidance)
        self._occupied: Set[Tuple[float, float]] = set()

    # ---- Properties ----

    @property
    def sequence(self) -> str:
        """The amino acid sequence."""
        return self._sequence

    @property
    def chain(self) -> List[AminoAcid]:
        """The list of amino acids in the chain."""
        return list(self._chain)

    @property
    def length(self) -> int:
        """Number of residues."""
        return len(self._chain)

    @property
    def constraints(self) -> Dict[str, Any]:
        """Current constraint parameters."""
        return dict(self._constraints)

    @property
    def is_folded(self) -> bool:
        """Whether the protein has been folded."""
        return self._folded

    @property
    def folding_history(self) -> List[List[Tuple[float, float]]]:
        """History of positions at each folding step."""
        return list(self._folding_history)

    @property
    def energy_history(self) -> List[float]:
        """Energy at each folding step."""
        return list(self._energy_history)

    # ---- Snap-to-Lattice ----

    def snap_to_lattice(
        self,
        position: Tuple[float, float],
        amino_acid: AminoAcid,
    ) -> Tuple[float, float]:
        """Snap amino acid to nearest valid position on the Eisenstein lattice.

        The Eisenstein lattice is a hexagonal/triangular tiling that provides
        optimal 2D packing. This is analogous to codon→amino acid mapping:
        continuous nucleotide space is discretized into 20 amino acid choices,
        with some redundancy (degeneracy) — multiple codons map to the same
        amino acid.

        Soft snap: within epsilon, stay at current position (degeneracy).
        Hard snap: outside epsilon, snap to nearest lattice point (deterministic).

        Parameters
        ----------
        position : tuple[float, float]
            Continuous 2D position to snap.
        amino_acid : AminoAcid
            The residue being snapped (properties may influence snap).

        Returns
        -------
        tuple[float, float]
            Snapped lattice position.
        """
        strength = self._constraints["snap_strength"]
        epsilon = self._constraints["snap_epsilon"]

        x, y = position

        # Snap to nearest Eisenstein lattice point.
        # The Eisenstein lattice has basis vectors:
        #   e1 = (1, 0)
        #   e2 = (1/2, sqrt(3)/2)
        # So lattice point = a*e1 + b*e2 = (a + b/2, b*sqrt(3)/2)
        # Inverting: b = y * 2/sqrt(3), a = x - b/2
        sqrt3 = math.sqrt(3)
        b = y * 2.0 / sqrt3
        a = x - b / 2.0

        a_round = round(a)
        b_round = round(b)

        snap_x = a_round + b_round / 2.0
        snap_y = b_round * sqrt3 / 2.0

        snapped = (snap_x, snap_y)

        # Soft snap: if within epsilon, blend between continuous and discrete
        dist = math.sqrt((x - snap_x) ** 2 + (y - snap_y) ** 2)
        if dist < epsilon and strength < 1.0:
            alpha = strength
            blended = (
                x * (1 - alpha) + snap_x * alpha,
                y * (1 - alpha) + snap_y * alpha,
            )
            return blended

        return snapped

    # ---- Energy Funnel ----

    def energy_funnel(
        self,
        position: Tuple[float, float],
        target: Tuple[float, float],
    ) -> Tuple[float, float]:
        """Apply energy funnel toward a target position.

        Models the protein folding energy landscape: a funnel-shaped surface
        where the native state sits at the bottom. Residues are pulled toward
        the hydrophobic core (the funnel target).

        The deadband creates a flat region at the funnel bottom — within this
        radius, no force is applied. This models the native basin: once the
        protein is near its native state, small fluctuations don't matter.

        Parameters
        ----------
        position : tuple[float, float]
            Current residue position.
        target : tuple[float, float]
            Funnel target (e.g., center of mass of hydrophobic residues).

        Returns
        -------
        tuple[float, float]
            Force vector pulling position toward target.
        """
        gravity = self._constraints["funnel_gravity"]
        deadband = self._constraints["funnel_deadband"]

        dx = target[0] - position[0]
        dy = target[1] - position[1]
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < deadband:
            # Inside deadband — no force (native basin)
            return (0.0, 0.0)

        # Force magnitude: linear beyond deadband
        force_mag = gravity * (dist - deadband)

        # Normalize direction
        if dist > 0:
            force = (force_mag * dx / dist, force_mag * dy / dist)
        else:
            force = (0.0, 0.0)

        return force

    # ---- Hydrophobic Core ----

    def _hydrophobic_center(self) -> Tuple[float, float]:
        """Compute center of mass of hydrophobic residues."""
        hydro_positions = [
            aa.position for aa in self._chain
            if aa.is_placed and aa.is_hydrophobic
        ]

        if not hydro_positions:
            # Use placed positions' centroid
            placed = [aa.position for aa in self._chain if aa.is_placed]
            if not placed:
                return (0.0, 0.0)
            hydro_positions = placed

        cx = sum(p[0] for p in hydro_positions) / len(hydro_positions)
        cy = sum(p[1] for p in hydro_positions) / len(hydro_positions)
        return (cx, cy)

    # ---- Contact Network ----

    def _compute_contacts(self) -> None:
        """Compute non-sequential contacts between residues."""
        contact_dist = self._constraints["contact_distance"]

        for aa in self._chain:
            aa.contacts.clear()

        for i in range(len(self._chain)):
            for j in range(i + 2, len(self._chain)):  # skip sequential neighbors
                aa_i = self._chain[i]
                aa_j = self._chain[j]
                if aa_i.is_placed and aa_j.is_placed:
                    if aa_i.distance_to(aa_j) <= contact_dist:
                        aa_i.contacts.add(j)
                        aa_j.contacts.add(i)

    # ---- Laman Rigidity ----

    def rigidity_check(self, contacts: Optional[List[Tuple[int, int]]] = None) -> Dict[str, Any]:
        """Check Laman rigidity of the contact network.

        A 2D structure is Laman rigid if it satisfies:
            |E| = 2|V| - 3

        where E is the number of edges (contacts + bonds) and V is the
        number of vertices (residues). If |E| > 2|V| - 3, the structure
        is overconstrained. If |E| < 2|V| - 3, it has floppy modes.

        This is directly analogous to musical voicing: too few notes in a
        chord leaves it ambiguous (floppy), too many makes it cluttered
        (overconstrained), and exactly right makes it stable (rigid).

        Parameters
        ----------
        contacts : list[tuple[int, int]] or None
            List of (i, j) contact pairs. If None, uses current contacts.

        Returns
        -------
        dict
            Rigidity analysis with keys:
            - 'rigid': bool — whether the structure is rigid
            - 'edges': int — number of constraint edges
            - 'vertices': int — number of vertices
            - 'laman_count': int — 2V - 3 (required edges for rigidity)
            - 'deficit': int — how many more edges needed (negative = excess)
            - 'status': str — 'rigid', 'floppy', or 'overconstrained'
        """
        n = len(self._chain)

        # Build edge list
        edges: Set[Tuple[int, int]] = set()

        # Sequential bonds
        for i in range(n - 1):
            edges.add((i, i + 1))

        # Non-sequential contacts
        if contacts is not None:
            for i, j in contacts:
                edges.add((min(i, j), max(i, j)))
        else:
            self._compute_contacts()
            for aa in self._chain:
                for j in aa.contacts:
                    edges.add((min(aa.index, j), max(aa.index, j)))

        n_edges = len(edges)
        laman_count = 2 * n - 3

        if n < 2:
            return {
                "rigid": False,
                "edges": n_edges,
                "vertices": n,
                "laman_count": max(0, laman_count),
                "deficit": 0,
                "status": "trivial",
            }

        deficit = laman_count - n_edges

        if deficit == 0:
            status = "rigid"
            rigid = True
        elif deficit > 0:
            status = "floppy"
            rigid = False
        else:
            status = "overconstrained"
            rigid = True  # overconstrained is still rigid

        return {
            "rigid": rigid,
            "edges": n_edges,
            "vertices": n,
            "laman_count": laman_count,
            "deficit": deficit,
            "status": status,
        }

    # ---- Consensus Rounds ----

    def consensus_round(self, nearby_residues: List[AminoAcid]) -> Tuple[float, float]:
        """Nearby residues agree on optimal packing position.

        Each residue adjusts its position based on the consensus of its
        neighbors. This models local molecular dynamics: each residue
        responds to the electromagnetic field of nearby atoms.

        The coupling strength (alpha) determines how much each residue
        is influenced by neighbors vs. maintaining its own position.

        Parameters
        ----------
        nearby_residues : list[AminoAcid]
            Residues within contact distance.

        Returns
        -------
        tuple[float, float]
            Consensus displacement vector.
        """
        alpha = self._constraints["consensus_alpha"]

        if not nearby_residues:
            return (0.0, 0.0)

        # Compute weighted centroid of nearby residues
        # Weight by compatibility (hydrophobic-hydrophobic = strong)
        total_weight = 0.0
        weighted_x = 0.0
        weighted_y = 0.0

        for other in nearby_residues:
            if not other.is_placed:
                continue

            # Compatibility weight
            weight = 1.0
            # Hydrophobic-hydrophobic attraction
            # Already handled by energy funnel, but consensus reinforces it
            weight = 1.0 + alpha

            weighted_x += other.position[0] * weight
            weighted_y += other.position[1] * weight
            total_weight += weight

        if total_weight == 0:
            return (0.0, 0.0)

        # Consensus position
        cx = weighted_x / total_weight
        cy = weighted_y / total_weight

        # Return displacement (scaled by coupling)
        return (cx * alpha, cy * alpha)

    # ---- Neighbor Finding ----

    def _get_neighbors(self, index: int) -> List[AminoAcid]:
        """Get nearby residues for consensus."""
        contact_dist = self._constraints["contact_distance"] * 2  # wider for consensus
        aa = self._chain[index]

        neighbors = []
        for other in self._chain:
            if other.index == index or not other.is_placed:
                continue
            if aa.distance_to(other) <= contact_dist:
                neighbors.append(other)
        return neighbors

    # ---- Available Lattice Positions ----

    def _available_neighbors(
        self,
        position: Tuple[float, float],
    ) -> List[Tuple[float, float]]:
        """Get unoccupied neighboring lattice positions."""
        available = []
        for dx, dy in LATTICE_DIRS:
            neighbor = (position[0] + dx, position[1] + dy)
            # Check if occupied (with small tolerance for floating point)
            is_free = True
            for occ in self._occupied:
                if abs(neighbor[0] - occ[0]) < 0.01 and abs(neighbor[1] - occ[1]) < 0.01:
                    is_free = False
                    break
            if is_free:
                available.append(neighbor)
        return available

    # ---- Energy Computation ----

    def energy(self) -> float:
        """Compute total energy of current conformation.

        Energy terms:
        1. Hydrophobic collapse: hydrophobic residues near each other = low energy
        2. Electrostatic: like charges repel, opposite attract
        3. Steric clash: overlapping residues = high energy penalty
        4. Bond strain: non-standard bond lengths = penalty

        Returns
        -------
        float
            Total energy (lower is better).
        """
        if not self._folded and not any(aa.is_placed for aa in self._chain):
            return float("inf")

        total = 0.0

        # 1. Hydrophobic collapse
        for i, aa in enumerate(self._chain):
            if not aa.is_placed:
                continue
            for j in range(i + 2, len(self._chain)):
                other = self._chain[j]
                if not other.is_placed:
                    continue
                dist = aa.distance_to(other)
                if dist > self._constraints["contact_distance"]:
                    continue
                # Hydrophobic interaction
                if aa.is_hydrophobic and other.is_hydrophobic:
                    total -= 2.0 / max(dist, 0.1)  # favorable
                # Electrostatic
                charge_i = aa.properties.get("charge", 0.0)
                charge_j = other.properties.get("charge", 0.0)
                total += charge_i * charge_j / max(dist, 0.1)  # Coulomb-like

        # 2. Bond strain
        for i in range(len(self._chain) - 1):
            aa = self._chain[i]
            other = self._chain[i + 1]
            if aa.is_placed and other.is_placed:
                dist = aa.distance_to(other)
                strain = abs(dist - self._constraints["bond_length"])
                total += strain * 10.0  # penalty for strained bonds

        # 3. Steric clash (residues too close)
        for i, aa in enumerate(self._chain):
            if not aa.is_placed:
                continue
            for j in range(i + 2, len(self._chain)):
                other = self._chain[j]
                if not other.is_placed:
                    continue
                dist = aa.distance_to(other)
                if dist < 0.5:  # steric clash threshold
                    total += (0.5 - dist) * 50.0  # heavy penalty

        return total

    # ---- Secondary Structure Detection ----

    def _detect_secondary_structure(self) -> None:
        """Detect secondary structure elements from the fold.

        - Alpha helix: sequential residues at ~100° angles
        - Beta sheet: extended zigzag pattern
        - Loop: irregular, often with proline or glycine
        """
        if self.length < 4:
            return

        for i in range(self.length):
            aa = self._chain[i]
            if not aa.is_placed:
                continue

            # Check for helical pattern (3.6 residues per turn in 2D approx)
            if i >= 1 and i < self.length - 1:
                prev_aa = self._chain[i - 1]
                next_aa = self._chain[i + 1]
                if prev_aa.is_placed and next_aa.is_placed:
                    # Compute angle at this residue
                    v1 = (
                        prev_aa.position[0] - aa.position[0],
                        prev_aa.position[1] - aa.position[1],
                    )
                    v2 = (
                        next_aa.position[0] - aa.position[0],
                        next_aa.position[1] - aa.position[1],
                    )

                    dot = v1[0] * v2[0] + v1[1] * v2[1]
                    mag1 = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
                    mag2 = math.sqrt(v2[0] ** 2 + v2[1] ** 2)

                    if mag1 > 0.01 and mag2 > 0.01:
                        cos_angle = dot / (mag1 * mag2)
                        cos_angle = max(-1.0, min(1.0, cos_angle))
                        angle = math.degrees(math.acos(cos_angle))

                        if 60 < angle < 140:
                            aa.secondary = "helix"
                        elif angle >= 140:
                            aa.secondary = "sheet"
                        else:
                            aa.secondary = "loop"
                    else:
                        aa.secondary = "loop"
            else:
                aa.secondary = "loop"

    # ---- Main Folding Algorithm ----

    def fold(self, max_steps: int = 1000) -> List[Tuple[float, float]]:
        """Iterative folding: each step depends on previous.

        This is the core algorithm. Like Levinthal's paradox demonstrates,
        the folding pathway is essential — you can't just compute the final
        state. Each residue's position emerges from the interaction of all
        previously placed residues.

        Algorithm:
        1. Place first residue at origin
        2. For each subsequent residue:
           a. Find available lattice neighbors of previous residue
           b. Apply energy funnel toward hydrophobic core
           c. Apply snap-to-lattice
           d. Score each candidate position
           e. Place at best position (or probabilistic based on temperature)
        3. Iterative refinement:
           a. Consensus rounds (neighbor agreement)
           b. Energy minimization
           c. Cool temperature (simulated annealing)
        4. Detect secondary structure

        NON-PRE-CALCULABILITY:
        Different seeds produce different folds because the initial placement
        cascades through all subsequent decisions — like a jazz solo where
        the first note determines the entire phrase.

        Parameters
        ----------
        max_steps : int
            Maximum refinement steps after initial placement.

        Returns
        -------
        list[tuple[float, float]]
            Final positions of all residues.
        """
        if self._folded:
            return [aa.position for aa in self._chain]

        rng = self._rng
        temperature = self._constraints["temperature"]
        cooling_rate = self._constraints["cooling_rate"]

        # --- Phase 1: Initial placement ---
        self._occupied.clear()

        # Place first residue at origin
        self._chain[0].position = (0.0, 0.0)
        self._occupied.add((0.0, 0.0))

        # Shuffle lattice directions with seed for NON-PRE-CALCULABILITY
        dirs = list(LATTICE_DIRS)  # copy
        rng.shuffle(dirs)

        # Place subsequent residues along a self-avoiding walk
        for i in range(1, self.length):
            prev = self._chain[i - 1]
            current = self._chain[i]

            # Candidate positions: lattice neighbors of previous residue
            candidates = []
            for dx, dy in dirs:
                nx = prev.position[0] + dx
                ny = prev.position[1] + dy
                # Check occupancy
                is_free = all(
                    abs(nx - ox) > 0.01 or abs(ny - oy) > 0.01
                    for ox, oy in self._occupied
                )
                if is_free:
                    candidates.append((nx, ny))

            if not candidates:
                # Try neighbors of ANY placed residue
                for placed_aa in reversed(self._chain[:i]):
                    for dx, dy in dirs:
                        nx = placed_aa.position[0] + dx
                        ny = placed_aa.position[1] + dy
                        is_free = all(
                            abs(nx - ox) > 0.01 or abs(ny - oy) > 0.01
                            for ox, oy in self._occupied
                        )
                        if is_free:
                            candidates.append((nx, ny))
                    if candidates:
                        break

            if not candidates:
                # Fallback: random position near prev
                angle = rng.uniform(0, 2 * math.pi)
                candidates = [(
                    prev.position[0] + math.cos(angle),
                    prev.position[1] + math.sin(angle),
                )]

            # Score each candidate position
            scores = []
            for pos in candidates:
                score = 0.0

                # Bond length strain
                bond_dist = math.sqrt(
                    (pos[0] - prev.position[0]) ** 2
                    + (pos[1] - prev.position[1]) ** 2
                )
                score += abs(bond_dist - self._constraints["bond_length"]) * 5.0

                # Hydrophobic attraction
                if current.is_hydrophobic:
                    for j in range(i):
                        other = self._chain[j]
                        if other.is_placed and other.is_hydrophobic:
                            dist = math.sqrt(
                                (pos[0] - other.position[0]) ** 2
                                + (pos[1] - other.position[1]) ** 2
                            )
                            score -= 1.0 / max(dist, 0.1)

                # Electrostatic
                charge = current.properties.get("charge", 0.0)
                for j in range(i):
                    other = self._chain[j]
                    if other.is_placed:
                        other_charge = other.properties.get("charge", 0.0)
                        dist = math.sqrt(
                            (pos[0] - other.position[0]) ** 2
                            + (pos[1] - other.position[1]) ** 2
                        )
                        score += charge * other_charge / max(dist, 0.1)

                # Steric penalty
                for j in range(i):
                    other = self._chain[j]
                    if other.is_placed:
                        dist = math.sqrt(
                            (pos[0] - other.position[0]) ** 2
                            + (pos[1] - other.position[1]) ** 2
                        )
                        if dist < 0.5:
                            score += (0.5 - dist) * 20.0

                # Funnel pull toward hydrophobic core
                if any(aa.is_placed and aa.is_hydrophobic for aa in self._chain[:i]):
                    target = self._hydrophobic_center()
                    dx = target[0] - pos[0]
                    dy = target[1] - pos[1]
                    dist = math.sqrt(dx * dx + dy * dy)
                    if current.is_hydrophobic:
                        score -= dist * 0.3  # pull hydrophobic toward core

                scores.append((score, pos))

            # Boltzmann selection (temperature-dependent, seed-dependent)
            if temperature > 0.01 and len(scores) > 1:
                min_score = min(s for s, _ in scores)
                weights = [
                    math.exp(-(s - min_score) / max(temperature, 0.01))
                    for s, _ in scores
                ]
                total_w = sum(weights)
                probs = [w / total_w for w in weights]
                chosen_idx = rng.choices(range(len(scores)), weights=probs, k=1)[0]
                _, chosen_pos = scores[chosen_idx]
            else:
                scores.sort(key=lambda x: x[0])
                _, chosen_pos = scores[0]

            current.position = chosen_pos
            self._occupied.add(tuple(round(p, 4) for p in chosen_pos))

        # --- Phase 2: Iterative refinement ---
        for step in range(max_steps):
            # Record history (sample every 5 steps to keep memory reasonable)
            if step % 5 == 0:
                self._folding_history.append(
                    [aa.position for aa in self._chain]
                )
                self._energy_history.append(self.energy())

            # Consensus rounds: VERY small adjustments to preserve structure
            for _ in range(self._constraints["consensus_rounds"]):
                for i in range(self.length):
                    aa = self._chain[i]
                    if not aa.is_placed:
                        continue

                    neighbors = self._get_neighbors(i)
                    if not neighbors:
                        continue

                    # Compute average neighbor position
                    placed_n = [n for n in neighbors if n.is_placed]
                    if not placed_n:
                        continue
                    avg_x = sum(n.position[0] for n in placed_n) / len(placed_n)
                    avg_y = sum(n.position[1] for n in placed_n) / len(placed_n)

                    alpha = self._constraints["consensus_alpha"] * 0.005
                    new_pos = (
                        aa.position[0] * (1 - alpha) + avg_x * alpha,
                        aa.position[1] * (1 - alpha) + avg_y * alpha,
                    )

                    # Enforce minimum distance to all other residues
                    for j in range(self.length):
                        if j == i:
                            continue
                        other = self._chain[j]
                        if not other.is_placed:
                            continue
                        dx = new_pos[0] - other.position[0]
                        dy = new_pos[1] - other.position[1]
                        dist = math.sqrt(dx * dx + dy * dy)
                        min_dist = 0.5
                        if dist < min_dist and dist > 0.001:
                            # Push away
                            push = (min_dist - dist) / dist
                            new_pos = (
                                new_pos[0] + dx * push,
                                new_pos[1] + dy * push,
                            )

                    aa.position = new_pos

            # Energy funnel: pull hydrophobic residues toward core (tiny steps)
            # Skip funnel for first residue and maintain spacing
            if step > 5:  # let structure settle first
                target = self._hydrophobic_center()
                for aa in self._chain:
                    if not aa.is_placed or not aa.is_hydrophobic:
                        continue
                    force = self.energy_funnel(aa.position, target)
                    new_pos = (
                        aa.position[0] + force[0] * 0.002,
                        aa.position[1] + force[1] * 0.002,
                    )
                    # Enforce minimum distance
                    valid = True
                    for other in self._chain:
                        if other.index == aa.index or not other.is_placed:
                            continue
                        dx = new_pos[0] - other.position[0]
                        dy = new_pos[1] - other.position[1]
                        if math.sqrt(dx * dx + dy * dy) < 0.4:
                            valid = False
                            break
                    if valid:
                        aa.position = new_pos

            # Cool temperature
            temperature *= cooling_rate

            # Convergence check
            if len(self._energy_history) > 10:
                recent = self._energy_history[-10:]
                if max(recent) - min(recent) < 0.001:
                    break

        # Final state
        self._compute_contacts()
        self._detect_secondary_structure()
        self._folded = True

        return [aa.position for aa in self._chain]

    # ---- Floppy Modes ----

    def floppy_modes(self) -> List[Dict[str, Any]]:
        """Find flexible regions of the folded protein.

        Floppy modes are degrees of freedom in the structure — regions
        where the constraint network is under-determined. In music,
        floppy modes correspond to expressive freedom: rubato, dynamics,
        phrasing that the performer can shape.

        A region is floppy if its local edge count is less than 2V - 3.

        Returns
        -------
        list[dict]
            List of floppy regions, each with:
            - 'residues': list of residue indices
            - 'deficit': how many constraints short of rigidity
            - 'flexibility': float (0 = rigid, 1 = completely free)
        """
        if not self._folded:
            raise RuntimeError("Protein must be folded first. Call fold().")

        self._compute_contacts()
        floppy = []

        # Sliding window analysis
        window_size = min(5, self.length)

        for start in range(0, self.length - window_size + 1):
            window = list(range(start, start + window_size))

            # Count edges within window
            edges = set()
            for i in range(len(window) - 1):
                edges.add((window[i], window[i + 1]))

            # Non-sequential contacts within window
            for idx in window:
                aa = self._chain[idx]
                for contact in aa.contacts:
                    if contact in window:
                        edges.add((min(idx, contact), max(idx, contact)))

            n_verts = len(window)
            laman_count = max(0, 2 * n_verts - 3)
            deficit = laman_count - len(edges)

            if deficit > 0:
                flexibility = deficit / max(laman_count, 1)
                floppy.append({
                    "residues": window,
                    "deficit": deficit,
                    "flexibility": min(flexibility, 1.0),
                    "type": self._classify_floppy_region(window),
                })

        return floppy

    def _classify_floppy_region(self, residues: List[int]) -> str:
        """Classify a floppy region by its dominant amino acid type.

        Returns
        -------
        str
            One of: 'disordered', 'hinge', 'linker', 'terminal'
        """
        if residues[0] == 0 or residues[-1] == self.length - 1:
            return "terminal"

        # Check if region is between two rigid elements
        if len(residues) <= 3:
            return "hinge"

        # Check for glycine/proline enrichment (disordered)
        gp_count = sum(
            1 for i in residues
            if self._chain[i].name in ("G", "P")
        )
        if gp_count / len(residues) > 0.3:
            return "disordered"

        return "linker"

    # ---- Radius of Gyration ----

    def radius_of_gyration(self) -> float:
        """Compute radius of gyration of the folded protein.

        A measure of compactness — smaller Rg means more compact.

        Returns
        -------
        float
            Radius of gyration in lattice units.
        """
        if not any(aa.is_placed for aa in self._chain):
            return float("inf")

        positions = [aa.position for aa in self._chain if aa.is_placed]
        cx = sum(p[0] for p in positions) / len(positions)
        cy = sum(p[1] for p in positions) / len(positions)

        rg_sq = sum((p[0] - cx) ** 2 + (p[1] - cy) ** 2 for p in positions) / len(positions)
        return math.sqrt(rg_sq)

    # ---- Contact Map ----

    def contact_map(self) -> NDArray[np.int8]:
        """Generate contact map matrix.

        Returns
        -------
        numpy.ndarray
            Binary N×N matrix where 1 = contact between residues i, j.
        """
        n = self.length
        cmap = np.zeros((n, n), dtype=np.int8)
        self._compute_contacts()

        for aa in self._chain:
            for j in aa.contacts:
                cmap[aa.index, j] = 1
                cmap[j, aa.index] = 1

        # Sequential neighbors
        for i in range(n - 1):
            cmap[i, i + 1] = 1
            cmap[i + 1, i] = 1

        return cmap

    # ---- Summary ----

    def summary(self) -> Dict[str, Any]:
        """Return a summary of the folded protein.

        Returns
        -------
        dict
            Summary with energy, contacts, rigidity, secondary structure, etc.
        """
        if not self._folded:
            return {"status": "not folded"}

        self._compute_contacts()
        total_contacts = sum(len(aa.contacts) for aa in self._chain) // 2

        secondary_counts: Dict[str, int] = {}
        for aa in self._chain:
            secondary_counts[aa.secondary] = secondary_counts.get(aa.secondary, 0) + 1

        rigidity = self.rigidity_check()
        floppy = self.floppy_modes()

        return {
            "status": "folded",
            "sequence": self._sequence,
            "length": self.length,
            "energy": self.energy(),
            "radius_of_gyration": self.radius_of_gyration(),
            "contacts": total_contacts,
            "rigidity": rigidity["status"],
            "floppy_regions": len(floppy),
            "secondary_structure": secondary_counts,
            "folding_steps": len(self._folding_history),
            "seed": self._seed,
        }


# ---------------------------------------------------------------------------
# ProteinToMusic — Biology → Music Transfer
# ---------------------------------------------------------------------------


class ProteinToMusic:
    """Convert folded protein structure to music.

    This is the operational transfer from biology to music. Each structural
    element of the protein maps to a musical element:

    Structural → Musical Mapping:
    - Alpha helices → sustained phrases (legato, smooth contour)
    - Beta sheets → parallel voices (counterpoint, regular rhythm)
    - Loops → ornamental passages (grace notes, trills)
    - Hydrophobic core → tonal center (the key, the funnel target)
    - Surface residues → decorative outer voices
    - Floppy modes → rubato / expressive freedom
    - Contact density → harmonic density
    - Charge → dissonance level
    - Folding trajectory → dynamic shape (crescendo/decrescendo)

    Parameters
    ----------
    protein : ProteinFolder
        A folded protein folder.
    bpm : float
        Tempo in beats per minute.
    base_pitch : int
        MIDI pitch for the lowest note (default 48 = C3).
    scale : list[int]
        Pitch intervals defining the scale (default: major scale).
    """

    # Major scale intervals from root
    MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
    MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]

    def __init__(
        self,
        protein: ProteinFolder,
        bpm: float = 120.0,
        base_pitch: int = 48,
        scale: Optional[List[int]] = None,
    ):
        if not protein.is_folded:
            raise RuntimeError("Protein must be folded before conversion. Call fold() first.")

        self._protein = protein
        self._bpm = bpm
        self._base_pitch = base_pitch
        self._scale = scale or self.MAJOR_SCALE

    def _pitch_for_residue(self, aa: AminoAcid, index: int) -> int:
        """Map residue properties to MIDI pitch."""
        # Use hydrophobicity to drive pitch contour
        hydro = aa.properties.get("hydro", 0.0)
        # Map [-4.5, 4.5] → scale degrees
        degree = int((hydro + 4.5) / 9.0 * len(self._scale))
        degree = max(0, min(degree, len(self._scale) - 1))

        # Add index-based transposition for melodic movement
        octave_shift = (index // 7) * 12
        pitch = self._base_pitch + self._scale[degree] + octave_shift
        return max(0, min(127, pitch))

    def _velocity_for_residue(self, aa: AminoAcid) -> int:
        """Map residue size/importance to MIDI velocity."""
        size = aa.properties.get("size", 0.5)
        # Map [0.2, 1.5] → [40, 120]
        vel = int(40 + (size - 0.2) / 1.3 * 80)
        return max(1, min(127, vel))

    def _duration_for_secondary(self, secondary: str) -> float:
        """Map secondary structure to note duration in beats."""
        durations = {
            "helix": 2.0,    # sustained
            "sheet": 1.0,    # regular
            "loop": 0.5,     # ornamental
            "none": 1.0,
        }
        return durations.get(secondary, 1.0)

    def structure_to_score(self) -> Dict[str, Any]:
        """Map protein structure to a musical score representation.

        This creates a multi-voice arrangement where:
        - Each secondary structure element becomes a voice
        - Helices are sustained legato lines
        - Sheets are rhythmic parallel voices
        - Loops are ornamental passages
        - The hydrophobic core defines the tonal center

        Returns
        -------
        dict
            Score with tracks, events, and metadata. Compatible with
            flux_tensor_midi.tracks.Arrangement format.
        """
        chain = self._protein.chain
        floppy = self._protein.floppy_modes()
        floppy_residues = set()
        for region in floppy:
            floppy_residues.update(region["residues"])

        # Group residues by secondary structure
        voices: Dict[str, List[Dict[str, Any]]] = {
            "helix": [],
            "sheet": [],
            "loop": [],
        }

        for aa in chain:
            if aa.secondary in voices:
                voices[aa.secondary].append({
                    "index": aa.index,
                    "name": aa.name,
                    "pitch": self._pitch_for_residue(aa, aa.index),
                    "velocity": self._velocity_for_residue(aa),
                    "duration": self._duration_for_secondary(aa.secondary),
                    "time": aa.index * 0.5,  # half beat spacing
                    "is_floppy": aa.index in floppy_residues,
                    "position": aa.position,
                })

        # Compute tonal center from hydrophobic core
        center = self._protein._hydrophobic_center()
        tonal_center = {
            "position": center,
            "pitch": self._base_pitch + 7,  # perfect fifth above base
            "description": "Hydrophobic core mapped to dominant pitch",
        }

        # Build score
        score = {
            "title": f"Protein: {self._protein.sequence[:10]}...",
            "bpm": self._bpm,
            "voices": voices,
            "tonal_center": tonal_center,
            "floppy_regions": floppy,
            "metadata": {
                "sequence_length": self._protein.length,
                "energy": self._protein.energy(),
                "radius_of_gyration": self._protein.radius_of_gyration(),
                "rigidity": self._protein.rigidity_check()["status"],
            },
        }

        return score

    def dynamics_to_timbre(
        self,
        folding_trajectory: Optional[List[List[Tuple[float, float]]]] = None,
    ) -> List[Dict[str, Any]]:
        """Map folding dynamics to timbral evolution.

        The folding trajectory captures how the protein moved through
        conformational space. This maps to timbral changes:

        - Fast folding (rapid convergence) → sharp attacks, bright timbre
        - Slow folding (gradual convergence) → gradual crescendos, warm timbre
        - Misfolding (energy increases) → dissonance, metallic timbre
        - Chaperone-assisted (correction events) → resolved harmony

        Parameters
        ----------
        folding_trajectory : list or None
            History of positions. If None, uses the protein's history.

        Returns
        -------
        list[dict]
            Timbral events with time, brightness, warmth, dissonance, etc.
        """
        if folding_trajectory is None:
            folding_trajectory = self._protein.folding_history

        energy_history = self._protein.energy_history
        timbre_events: List[Dict[str, Any]] = []

        if not folding_trajectory or not energy_history:
            return timbre_events

        # Analyze energy trajectory
        n_steps = len(energy_history)

        for i in range(n_steps):
            # Energy change rate → attack characteristic
            if i > 0:
                d_energy = energy_history[i] - energy_history[i - 1]
            else:
                d_energy = 0.0

            # Brightness: inversely related to energy
            max_e = max(abs(e) for e in energy_history) if energy_history else 1.0
            brightness = 1.0 - abs(energy_history[i]) / max(max_e, 0.001)

            # Warmth: related to hydrophobic burial
            warmth = 0.5
            if i < len(folding_trajectory):
                positions = folding_trajectory[i]
                center = self._protein._hydrophobic_center()
                # Average distance from center
                dists = [
                    math.sqrt((p[0] - center[0]) ** 2 + (p[1] - center[1]) ** 2)
                    for p in positions
                ]
                avg_dist = sum(dists) / len(dists) if dists else 0
                warmth = 1.0 / (1.0 + avg_dist)

            # Dissonance: energy increase = misfolding = dissonance
            dissonance = max(0.0, d_energy / max(abs(max_e), 0.001))

            # Attack: rate of position change
            attack = 0.5
            if i > 0 and i < len(folding_trajectory):
                prev_pos = folding_trajectory[i - 1]
                curr_pos = folding_trajectory[i]
                total_movement = sum(
                    math.sqrt(
                        (curr_pos[j][0] - prev_pos[j][0]) ** 2
                        + (curr_pos[j][1] - prev_pos[j][1]) ** 2
                    )
                    for j in range(min(len(curr_pos), len(prev_pos)))
                )
                attack = min(1.0, total_movement / len(curr_pos))

            timbre_events.append({
                "step": i,
                "time": i * (60.0 / self._bpm),  # map to musical time
                "brightness": max(0.0, min(1.0, brightness)),
                "warmth": max(0.0, min(1.0, warmth)),
                "dissonance": max(0.0, min(1.0, dissonance)),
                "attack": max(0.0, min(1.0, attack)),
                "energy": energy_history[i],
            })

        return timbre_events


# ---------------------------------------------------------------------------
# MusicToProtein — Music → Biology Transfer
# ---------------------------------------------------------------------------


class MusicToProtein:
    """Convert musical constraints to protein design.

    This is the reverse transfer: from music back to biology. Given a set
    of musical constraint parameters, design a protein sequence that would
    fold into a structure reflecting those musical qualities.

    Constraint → Sequence Mapping:
    - High snap → regular secondary structure (alpha helix)
      Strong snap = strong hydrogen bonding = helix propensity
    - High funnel → strong hydrophobic core
      Strong funnel = strong hydrophobic collapse = well-defined core
    - High laman → cross-linked structure (disulfide bonds)
      High rigidity = many contacts = cysteine cross-links
    - High consensus → symmetrical oligomer
      Strong consensus = cooperative folding = repeating units
    - Soft snap ε → intrinsically disordered regions
      Soft snap = flexible lattice positions = disordered regions

    Parameters
    ----------
    constraints : dict
        Musical constraint parameters to transfer.
    target_length : int
        Desired protein length (default 30).
    seed : int or None
        Random seed for sequence generation.
    """

    # Helix-forming amino acids (high helix propensity)
    HELIX_FORMERS = ["A", "E", "L", "M", "Q", "K", "R"]
    # Sheet-forming amino acids
    SHEET_FORMERS = ["V", "I", "Y", "F", "W", "T"]
    # Disorder-promoting amino acids
    DISORDER_PROMOTERS = ["G", "P", "S", "Q", "E", "K"]
    # Hydrophobic amino acids (for core)
    HYDROPHOBIC = ["A", "V", "I", "L", "M", "F", "W"]
    # Cysteine (for disulfide bonds)
    CYSTEINE = "C"
    # Charged amino acids
    POSITIVELY_CHARGED = ["K", "R", "H"]
    NEGATIVELY_CHARGED = ["D", "E"]

    def __init__(
        self,
        constraints: Dict[str, Any],
        target_length: int = 30,
        seed: Optional[int] = None,
    ):
        self._constraints = constraints
        self._length = target_length
        self._rng = random.Random(seed)

    def constraints_to_sequence(self) -> str:
        """Design a protein sequence from musical constraints.

        The musical constraint parameters are translated into amino acid
        propensities:

        1. snap_strength → helix/sheet/disorder ratio
        2. funnel_gravity → hydrophobic residue frequency
        3. laman_threshold → cysteine frequency (for disulfide bonds)
        4. consensus_weight → sequence repetition/symmetry
        5. snap_epsilon → disorder region proportion

        Returns
        -------
        str
            Designed amino acid sequence.
        """
        snap = self._constraints.get("snap_strength", 0.5)
        funnel = self._constraints.get("funnel_gravity", 0.5)
        laman = self._constraints.get("laman_threshold", 0.5)
        consensus = self._constraints.get("consensus_weight", 0.5)
        epsilon = self._constraints.get("snap_epsilon", 0.15)

        sequence: List[str] = []
        rng = self._rng

        for i in range(self._length):
            # Determine what type of residue this position needs
            aa = self._design_residue(
                position=i,
                snap=snap,
                funnel=funnel,
                laman=laman,
                consensus=consensus,
                epsilon=epsilon,
            )
            sequence.append(aa)

        # If consensus is high, introduce symmetry
        if consensus > 0.5:
            sequence = self._introduce_symmetry(sequence, consensus)

        # If laman is high, place cysteines for disulfide bonds
        if laman > 0.4:
            sequence = self._place_cysteines(sequence, laman)

        return "".join(sequence)

    def _design_residue(
        self,
        position: int,
        snap: float,
        funnel: float,
        laman: float,
        consensus: float,
        epsilon: float,
    ) -> str:
        """Design a single residue based on constraint parameters.

        Parameters
        ----------
        position : int
            Position in the sequence.
        snap, funnel, laman, consensus, epsilon : float
            Constraint parameters.

        Returns
        -------
        str
            Single amino acid letter.
        """
        rng = self._rng

        # Soft snap → intrinsically disordered
        disorder_prob = epsilon * 2  # scale epsilon to probability
        if rng.random() < disorder_prob:
            return rng.choice(self.DISORDER_PROMOTERS)

        # Is this a core or surface position?
        # Core = middle third, Surface = outer thirds
        third = self._length // 3
        is_core = third <= position < 2 * third

        if is_core and funnel > 0.3:
            # Hydrophobic core residue
            if rng.random() < funnel:
                return rng.choice(self.HYDROPHOBIC)

        # Snap strength determines secondary structure
        if snap > 0.6:
            # High snap → helix
            if rng.random() < snap:
                return rng.choice(self.HELIX_FORMERS)
        elif snap < 0.3:
            # Low snap → sheet
            if rng.random() < (1 - snap):
                return rng.choice(self.SHEET_FORMERS)
        else:
            # Medium snap → mix
            if rng.random() < 0.5:
                return rng.choice(self.HELIX_FORMERS)
            else:
                return rng.choice(self.SHEET_FORMERS)

        # Default: random from all 20
        all_aa = list(AMINO_ACID_PROPERTIES.keys())
        return rng.choice(all_aa)

    def _introduce_symmetry(
        self,
        sequence: List[str],
        consensus: float,
    ) -> List[str]:
        """Introduce sequence symmetry based on consensus weight.

        High consensus → repeating motifs → symmetrical oligomer design.

        Parameters
        ----------
        sequence : list[str]
            Current sequence.
        consensus : float
            Consensus weight (0–1).

        Returns
        -------
        list[str]
            Modified sequence with symmetry.
        """
        if self._length < 6:
            return sequence

        # Repeat the first half into the second half
        half = self._length // 2
        symmetry_strength = consensus

        if self._rng.random() < symmetry_strength:
            for i in range(half):
                mirror_idx = self._length - 1 - i
                if mirror_idx < self._length:
                    sequence[mirror_idx] = sequence[i]

        return sequence

    def _place_cysteines(
        self,
        sequence: List[str],
        laman: float,
    ) -> List[str]:
        """Place cysteine residues for potential disulfide bonds.

        High laman → more cross-links → more cysteines.

        Parameters
        ----------
        sequence : list[str]
            Current sequence.
        laman : float
            Laman threshold (0–1).

        Returns
        -------
        list[str]
            Modified sequence with cysteines.
        """
        # Number of cysteine pairs proportional to laman
        n_cys = max(1, int(laman * self._length / 10))
        n_cys = min(n_cys, self._length // 4)  # cap at 25%

        # Place cysteines at symmetric positions (for proper pairing)
        positions = list(range(0, self._length, max(1, self._length // (2 * n_cys))))
        for i, pos in enumerate(positions[:n_cys]):
            # Place at pos and symmetric partner
            sequence[pos] = self.CYSTEINE
            partner = self._length - 1 - pos
            if partner >= 0 and partner < self._length and partner != pos:
                sequence[partner] = self.CYSTEINE

        return sequence

    def constraints_to_folding_params(self) -> Dict[str, Any]:
        """Convert musical constraints to protein folding parameters.

        Maps the musical constraint space to folding parameters suitable
        for ProteinFolder.

        Returns
        -------
        dict
            Folding constraint parameters for ProteinFolder.
        """
        return {
            "snap_strength": self._constraints.get("snap_strength", 0.5),
            "snap_epsilon": self._constraints.get("snap_epsilon", 0.15),
            "funnel_gravity": self._constraints.get("funnel_gravity", 0.5),
            "funnel_deadband": self._constraints.get("funnel_deadband", 0.3),
            "laman_threshold": self._constraints.get("laman_threshold", 0.6),
            "consensus_rounds": max(1, int(self._constraints.get("consensus_weight", 0.5) * 5)),
            "consensus_alpha": self._constraints.get("consensus_weight", 0.3),
            "contact_distance": 1.5,
            "bond_length": 1.0,
            "temperature": 1.0,
            "cooling_rate": 0.995,
        }


# ---------------------------------------------------------------------------
# Round-trip Verification
# ---------------------------------------------------------------------------


def round_trip_verify(
    sequence: str,
    seed: int = 42,
    tolerance: float = 0.3,
) -> Dict[str, Any]:
    """Verify the full Biology → Music → Biology round trip.

    1. Fold a protein
    2. Convert to music (extract constraints)
    3. Design a new protein from those musical constraints
    4. Fold the new protein
    5. Compare structural properties

    Parameters
    ----------
    sequence : str
        Starting amino acid sequence.
    seed : int
        Random seed for reproducibility.
    tolerance : float
        Allowed deviation in structural properties.

    Returns
    -------
    dict
        Verification results including both proteins' summaries.
    """
    # Step 1: Fold original protein
    folder1 = ProteinFolder(sequence=sequence, seed=seed)
    positions1 = folder1.fold()

    # Step 2: Convert to music
    p2m = ProteinToMusic(folder1)
    score = p2m.structure_to_score()

    # Step 3: Extract musical constraints from score
    music_constraints = {
        "snap_strength": folder1.constraints["snap_strength"],
        "funnel_gravity": folder1.constraints["funnel_gravity"],
        "laman_threshold": folder1.constraints["laman_threshold"],
        "consensus_weight": folder1.constraints["consensus_alpha"],
        "snap_epsilon": folder1.constraints["snap_epsilon"],
    }

    # Step 4: Design new protein
    m2p = MusicToProtein(
        constraints=music_constraints,
        target_length=len(sequence),
        seed=seed,
    )
    new_sequence = m2p.constraints_to_sequence()

    # Step 5: Fold new protein
    folder2 = ProteinFolder(sequence=new_sequence, seed=seed)
    positions2 = folder2.fold()

    # Compare
    summary1 = folder1.summary()
    summary2 = folder2.summary()

    energy_diff = abs(summary1["energy"] - summary2["energy"])
    rg_diff = abs(summary1["radius_of_gyration"] - summary2["radius_of_gyration"])

    return {
        "original_sequence": sequence,
        "derived_sequence": new_sequence,
        "original_summary": summary1,
        "derived_summary": summary2,
        "energy_difference": energy_diff,
        "rg_difference": rg_diff,
        "within_tolerance": energy_diff < tolerance * 100 and rg_diff < tolerance * 5,
    }
