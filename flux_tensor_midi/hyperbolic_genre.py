"""
Hyperbolic Genre Space — genres live on a Poincaré ball.

Connects flux-hyperbolic-py geometry to musical genre taxonomy:
  - Genres are points on an 8D Poincaré ball
  - Hyperbolic distance = genre dissimilarity
  - Fréchet mean = genre blending
  - Random walk = genre exploration
  - Cultural distance = cross-tradition similarity

Depends on: flux_hyperbolic (PoincareBall, FrechetMean)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from flux_hyperbolic.geometry import PoincareBall
    from flux_hyperbolic.consensus import FrechetMean
except ImportError:
    raise ImportError(
        "flux_hyperbolic is required. Install flux-hyperbolic-py first."
    )

# ---------------------------------------------------------------------------
# Embedding dimension and axis labels
# ---------------------------------------------------------------------------
GENRE_DIM = 8
AXIS_LABELS = [
    "chromatic_density",   # 0: pitch class diversity
    "rhythmic_intensity",  # 1: note density / speed
    "dynamic_range",       # 2: loudness variation
    "spaciousness",        # 3: rest / silence proportion
    "timing_tightness",    # 4: quantization / grid snap
    "angularity",          # 5: direction change probability
    "sustain",             # 6: note length / legato factor
    "consensus",           # 7: agreement / formality
]


# ---------------------------------------------------------------------------
# Genre data: (name, parent, raw 8D vector, norm_hint)
# ---------------------------------------------------------------------------
# raw vectors are direction components; they get normalised and scaled.

_GENRE_DEFS: List[Tuple[str, Optional[str], List[float], float]] = [
    # --- Level 0: Root ---
    ("Music", None, [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5], 0.01),

    # --- Level 1: Major Traditions ---
    ("Western", "Music", [0.6, 0.5, 0.6, 0.3, 0.7, 0.3, 0.5, 0.7], 0.28),
    ("Eastern", "Music", [0.9, 0.4, 0.4, 0.5, 0.3, 0.5, 0.7, 0.5], 0.28),
    ("African", "Music", [0.5, 0.9, 0.6, 0.2, 0.3, 0.6, 0.4, 0.6], 0.28),
    ("Electronic", "Music", [0.4, 0.8, 0.3, 0.3, 0.95, 0.3, 0.6, 0.4], 0.28),

    # --- Level 2: Primary Genres ---
    ("Classical", "Western", [0.7, 0.4, 0.8, 0.4, 0.7, 0.2, 0.7, 0.9], 0.35),
    ("Jazz", "Western", [0.9, 0.7, 0.6, 0.3, 0.2, 0.8, 0.4, 0.4], 0.38),
    ("Rock", "Western", [0.5, 0.7, 0.7, 0.2, 0.6, 0.5, 0.4, 0.5], 0.36),
    ("Hip-hop", "Western", [0.4, 0.8, 0.5, 0.2, 0.3, 0.7, 0.3, 0.3], 0.37),
    ("Blues", "Western", [0.6, 0.4, 0.6, 0.3, 0.2, 0.4, 0.5, 0.5], 0.34),
    ("Country", "Western", [0.3, 0.5, 0.4, 0.3, 0.5, 0.3, 0.4, 0.6], 0.32),

    ("Raga", "Eastern", [0.95, 0.4, 0.5, 0.5, 0.2, 0.5, 0.9, 0.4], 0.40),
    ("Maqam", "Eastern", [0.9, 0.4, 0.4, 0.4, 0.3, 0.5, 0.7, 0.7], 0.38),
    ("Gagaku", "Eastern", [0.5, 0.2, 0.3, 0.7, 0.6, 0.2, 0.9, 0.8], 0.37),

    ("Polyrhythm", "African", [0.4, 0.95, 0.7, 0.1, 0.3, 0.7, 0.3, 0.7], 0.40),
    ("Afrobeat", "African", [0.6, 0.9, 0.6, 0.2, 0.3, 0.6, 0.5, 0.5], 0.38),
    ("Griot", "African", [0.5, 0.6, 0.5, 0.4, 0.2, 0.5, 0.6, 0.6], 0.35),

    ("Techno", "Electronic", [0.3, 0.9, 0.2, 0.1, 0.95, 0.2, 0.5, 0.3], 0.42),
    ("Ambient", "Electronic", [0.4, 0.2, 0.3, 0.9, 0.7, 0.1, 0.95, 0.5], 0.40),
    ("House", "Electronic", [0.3, 0.7, 0.3, 0.2, 0.9, 0.2, 0.5, 0.4], 0.38),
    ("Drum and Bass", "Electronic", [0.4, 0.95, 0.4, 0.1, 0.85, 0.4, 0.3, 0.3], 0.43),
    ("IDM", "Electronic", [0.6, 0.7, 0.5, 0.3, 0.8, 0.6, 0.4, 0.2], 0.40),

    # --- Level 3: Sub-genres ---
    ("Baroque", "Classical", [0.8, 0.5, 0.3, 0.2, 0.8, 0.3, 0.4, 0.95], 0.58),
    ("Romantic", "Classical", [0.7, 0.5, 0.9, 0.3, 0.5, 0.4, 0.8, 0.7], 0.58),
    ("Minimalism", "Classical", [0.3, 0.4, 0.3, 0.5, 0.7, 0.1, 0.7, 0.8], 0.56),

    ("Bebop", "Jazz", [0.95, 0.85, 0.6, 0.2, 0.1, 0.9, 0.3, 0.3], 0.62),
    ("Modal Jazz", "Jazz", [0.8, 0.5, 0.5, 0.4, 0.2, 0.5, 0.6, 0.5], 0.58),
    ("Free Jazz", "Jazz", [0.95, 0.8, 0.8, 0.3, 0.05, 0.95, 0.3, 0.1], 0.65),
    ("Swing", "Jazz", [0.7, 0.7, 0.5, 0.3, 0.4, 0.4, 0.5, 0.6], 0.56),

    ("Punk", "Rock", [0.3, 0.9, 0.8, 0.1, 0.6, 0.7, 0.2, 0.2], 0.60),
    ("Metal", "Rock", [0.5, 0.9, 0.7, 0.05, 0.7, 0.6, 0.3, 0.3], 0.62),
    ("Shoegaze", "Rock", [0.5, 0.3, 0.4, 0.6, 0.5, 0.2, 0.8, 0.3], 0.58),

    ("Trap", "Hip-hop", [0.4, 0.85, 0.4, 0.2, 0.2, 0.8, 0.2, 0.2], 0.62),
    ("Lo-fi Hip-hop", "Hip-hop", [0.5, 0.4, 0.3, 0.5, 0.3, 0.3, 0.6, 0.4], 0.58),

    ("Detroit Techno", "Techno", [0.3, 0.85, 0.3, 0.15, 0.95, 0.3, 0.5, 0.4], 0.65),
    ("Dub Techno", "Techno", [0.3, 0.5, 0.2, 0.8, 0.9, 0.1, 0.8, 0.3], 0.63),

    ("Dhrupad", "Raga", [0.95, 0.2, 0.4, 0.7, 0.1, 0.2, 0.98, 0.5], 0.70),
    ("Carnatic", "Raga", [0.9, 0.6, 0.5, 0.3, 0.2, 0.6, 0.6, 0.6], 0.65),

    # --- Level 4: Specific Styles ---
    ("Bach-style", "Baroque", [0.85, 0.6, 0.3, 0.2, 0.85, 0.35, 0.4, 0.98], 0.82),
    ("Coltrane-style", "Bebop", [0.98, 0.9, 0.7, 0.15, 0.05, 0.95, 0.3, 0.15], 0.88),
    ("Dilla-style", "Hip-hop", [0.5, 0.75, 0.4, 0.3, 0.15, 0.6, 0.5, 0.3], 0.80),
    ("Basic Channel-style", "Dub Techno", [0.25, 0.4, 0.15, 0.85, 0.92, 0.05, 0.9, 0.25], 0.85),
    ("Mbalax", "Afrobeat", [0.5, 0.95, 0.6, 0.1, 0.2, 0.8, 0.3, 0.6], 0.80),
]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def poincare_distance(u: np.ndarray, v: np.ndarray) -> float:
    """Hyperbolic distance between two points on the Poincaré ball."""
    return PoincareBall.distance(u, v)


def frechet_mean(
    points: List[np.ndarray],
    weights: Optional[np.ndarray] = None,
) -> np.ndarray:
    """Weighted Fréchet mean of points on the Poincaré ball."""
    return FrechetMean.compute(points, weights)


def _embed_raw(raw: List[float], norm_hint: float) -> np.ndarray:
    """Normalise a raw direction vector and scale by norm_hint."""
    v = np.array(raw, dtype=np.float64)
    n = np.linalg.norm(v)
    if n < 1e-10:
        return PoincareBall.project(np.zeros(GENRE_DIM))
    direction = v / n
    return PoincareBall.project(direction * norm_hint)


# ---------------------------------------------------------------------------
# HyperbolicGenreMap
# ---------------------------------------------------------------------------

@dataclass
class GenrePoint:
    """A genre embedded on the Poincaré ball."""
    name: str
    parent: Optional[str]
    coords: np.ndarray
    level: int = 0

    @property
    def norm(self) -> float:
        return float(np.linalg.norm(self.coords))

    def distance_to(self, other: "GenrePoint") -> float:
        return poincare_distance(self.coords, other.coords)


class HyperbolicGenreMap:
    """Map of musical genres on an 8D Poincaré ball.

    Genres are placed hierarchically:
      - Root (Music) near the centre
      - Major traditions at moderate norm
      - Primary genres further out
      - Sub-genres and styles near the boundary

    Supports blending, nearest-neighbour lookup, random walks,
    and cultural distance measurement.
    """

    def __init__(self) -> None:
        self.genres: Dict[str, GenrePoint] = {}
        self._build_default_genres()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_default_genres(self) -> None:
        """Populate from the built-in genre definitions."""
        for name, parent, raw, norm_hint in _GENRE_DEFS:
            coords = _embed_raw(raw, norm_hint)
            level = self._infer_level(name, parent)
            self.genres[name] = GenrePoint(
                name=name, parent=parent, coords=coords, level=level
            )

    def _infer_level(self, name: str, parent: Optional[str]) -> int:
        """Count depth from root."""
        if parent is None:
            return 0
        level = 1
        current = parent
        while current is not None and current in self.genres:
            current = self.genres[current].parent
            if current is not None:
                level += 1
        return level

    def add_genre(
        self,
        name: str,
        parent: Optional[str],
        raw_vector: List[float],
        norm_hint: float,
    ) -> GenrePoint:
        """Add a custom genre to the map."""
        coords = _embed_raw(raw_vector, norm_hint)
        level = self._infer_level(name, parent)
        gp = GenrePoint(name=name, parent=parent, coords=coords, level=level)
        self.genres[name] = gp
        return gp

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def distance(self, name_a: str, name_b: str) -> float:
        """Hyperbolic distance between two genres."""
        return poincare_distance(
            self.genres[name_a].coords, self.genres[name_b].coords
        )

    def genre_blend(
        self,
        name_a: str,
        name_b: str,
        weight_a: float = 0.5,
    ) -> np.ndarray:
        """Blend two genres via Fréchet mean.

        weight_a=1.0 → pure name_a; weight_a=0.0 → pure name_b.
        """
        w = weight_a
        points = [self.genres[name_a].coords, self.genres[name_b].coords]
        weights = np.array([w, 1.0 - w], dtype=np.float64)
        return frechet_mean(points, weights)

    def multi_blend(
        self,
        names: List[str],
        weights: Optional[List[float]] = None,
    ) -> np.ndarray:
        """Blend multiple genres via weighted Fréchet mean."""
        if weights is None:
            weights = [1.0 / len(names)] * len(names)
        pts = [self.genres[n].coords for n in names]
        w = np.array(weights, dtype=np.float64)
        return frechet_mean(pts, w)

    def nearest_genres(
        self,
        target: np.ndarray | str,
        n: int = 5,
    ) -> List[Tuple[str, float]]:
        """Find the n closest genres to a point (or named genre)."""
        if isinstance(target, str):
            target = self.genres[target].coords
        target = PoincareBall.project(np.asarray(target, dtype=np.float64))
        dists = [
            (name, poincare_distance(target, gp.coords))
            for name, gp in self.genres.items()
        ]
        dists.sort(key=lambda x: x[1])
        return dists[:n]

    def genre_walk(
        self,
        start: str | np.ndarray,
        step_size: float = 0.3,
        rng: Optional[np.random.Generator] = None,
    ) -> Tuple[np.ndarray, str]:
        """Random walk on the Poincaré ball from a genre.

        Returns (new_point, nearest_genre_name).
        """
        if rng is None:
            rng = np.random.default_rng()
        if isinstance(start, str):
            origin = self.genres[start].coords.copy()
        else:
            origin = np.asarray(start, dtype=np.float64).copy()

        # Random tangent direction
        tangent = rng.standard_normal(GENRE_DIM)
        tangent = tangent / (np.linalg.norm(tangent) + 1e-10) * step_size

        # Exponential map
        new_point = PoincareBall.expmap(origin, tangent)
        new_point = PoincareBall.project(new_point)

        # Find nearest genre
        nearest = self.nearest_genres(new_point, n=1)
        return new_point, nearest[0][0]

    def cultural_distance(
        self,
        tradition_a: str,
        tradition_b: str,
    ) -> float:
        """Distance between two cultural music traditions.

        This is the hyperbolic distance between the two top-level
        tradition genres, which captures broad cultural dissimilarity.
        """
        # Resolve to level-1 ancestor if given a sub-genre
        a_root = self._tradition_root(tradition_a)
        b_root = self._tradition_root(tradition_b)
        return self.distance(a_root, b_root)

    def _tradition_root(self, name: str) -> str:
        """Walk up to the level-1 ancestor (or the genre itself)."""
        if name not in self.genres:
            raise KeyError(f"Unknown genre: {name}")
        gp = self.genres[name]
        while gp.parent is not None and gp.parent in self.genres:
            parent_gp = self.genres[gp.parent]
            if parent_gp.level <= 1:
                return gp.name if gp.level == 1 else parent_gp.name
            gp = parent_gp
        return gp.name

    # ------------------------------------------------------------------
    # Encoding / Decoding
    # ------------------------------------------------------------------

    def decode_to_constraints(self, point: np.ndarray) -> Dict[str, float]:
        """Decode a Poincaré ball point to a constraint dictionary."""
        point = np.asarray(point, dtype=np.float64)
        norm = np.linalg.norm(point)
        if norm < 1e-10:
            return {label: 0.5 for label in AXIS_LABELS}

        direction = point / norm
        # Use both norm and direction to recover constraint values
        scale = min(norm / 0.9, 1.0)
        result = {}
        for i, label in enumerate(AXIS_LABELS):
            # Map from [-1, 1] direction component to [0, 1] constraint
            val = (direction[i] + 1.0) / 2.0
            # Push extremes based on norm
            val = 0.5 + (val - 0.5) * (1.0 + 0.5 * scale)
            result[label] = max(0.0, min(1.0, val))
        return result

    def encode_genre(self, constraints: Dict[str, float]) -> np.ndarray:
        """Encode a constraint dictionary as a point on the Poincaré ball."""
        raw = np.array(
            [constraints.get(label, 0.5) for label in AXIS_LABELS],
            dtype=np.float64,
        )
        # Use constraint spread to determine specialization norm
        spread = np.std(raw)
        norm_hint = 0.1 + 0.8 * min(spread / 0.25, 1.0)
        return _embed_raw(raw.tolist(), norm_hint)

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def genre_info(self, name: str) -> Dict[str, Any]:
        """Return full info about a genre."""
        gp = self.genres[name]
        return {
            "name": gp.name,
            "parent": gp.parent,
            "level": gp.level,
            "norm": gp.norm,
            "coords": gp.coords.tolist(),
            "constraints": self.decode_to_constraints(gp.coords),
        }

    def children(self, name: str) -> List[str]:
        """Return direct children of a genre."""
        return [g.name for g in self.genres.values() if g.parent == name]

    def siblings(self, name: str) -> List[str]:
        """Return siblings (same parent) of a genre."""
        parent = self.genres[name].parent
        if parent is None:
            return []
        return [
            g.name for g in self.genres.values()
            if g.parent == parent and g.name != name
        ]

    def all_distances(self) -> Dict[Tuple[str, str], float]:
        """Compute all pairwise distances (expensive for large maps)."""
        names = sorted(self.genres.keys())
        result: Dict[Tuple[str, str], float] = {}
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                result[(a, b)] = self.distance(a, b)
        return result

    @property
    def genre_count(self) -> int:
        return len(self.genres)

    @property
    def genre_names(self) -> List[str]:
        return sorted(self.genres.keys())
