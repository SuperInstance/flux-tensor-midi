"""
flux_hyperbolic.ball — Poincaré ball model for hyperbolic constraint spaces.

The Poincaré ball maps the entire hyperbolic plane into the unit ball.
Points near the boundary represent increasingly distant/fine-grained constraints.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence

import numpy as np


class PoincareBall:
    """
    Poincaré ball model of n-dimensional hyperbolic space.

    All points lie strictly inside the unit ball (||x|| < 1).
    The boundary (||x|| = 1) represents "infinity" in hyperbolic space.

    Args:
        dimension: Dimensionality of the embedding space.
        curvature: Negative curvature parameter c > 0.
            Higher c = more curved = hierarchy fits in fewer dimensions.
    """

    def __init__(self, dimension: int = 2, curvature: float = 1.0):
        if dimension < 1:
            raise ValueError("dimension must be >= 1")
        if curvature <= 0:
            raise ValueError("curvature must be positive")
        self.dimension = dimension
        self.c = curvature
        self._sqrt_c = math.sqrt(curvature)

    def conformal_factor(self, x: np.ndarray) -> float:
        """Conformal factor λ_x = 2 / (1 - c||x||²)."""
        x = np.asarray(x, dtype=np.float64)
        norm_sq = float(np.dot(x, x))
        denom = 1.0 - self.c * norm_sq
        if denom <= 0:
            raise ValueError(f"Point outside ball: ||x||²={norm_sq}, max={1/self.c}")
        return 2.0 / denom

    def distance(self, x: np.ndarray, y: np.ndarray) -> float:
        """Hyperbolic distance between two points in the ball.

        d(x,y) = (2/√c) * arctanh(√c * ||(-x)⊕y||)
        where ⊕ is Möbius addition.
        """
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)

        x_norm_sq = float(np.dot(x, x))
        y_norm_sq = float(np.dot(y, y))
        xy = float(np.dot(x, y))

        # Mobius difference norm squared: ||(-x) ⊕ y||²
        # = ||x||² + ||y||² - 2<x,y> / (1 + c||x||²||y||² - 2c<x,y>)
        denom = 1.0 + self.c * x_norm_sq * y_norm_sq - 2.0 * self.c * xy
        if denom <= 0:
            return float('inf')

        diff_norm_sq = (x_norm_sq + y_norm_sq - 2.0 * xy) / denom

        if diff_norm_sq < 0:
            diff_norm_sq = 0.0
        diff_norm = math.sqrt(diff_norm_sq)

        # Clamp to avoid numerical issues with arctanh
        arg = self._sqrt_c * diff_norm
        arg = min(arg, 1.0 - 1e-7)

        return (2.0 / self._sqrt_c) * math.atanh(arg)

    def project(self, x: np.ndarray, max_norm: float = 0.999) -> np.ndarray:
        """Project point back inside the ball if it escaped."""
        x = np.asarray(x, dtype=np.float64)
        norm = float(np.linalg.norm(x))
        max_n = max_norm / self._sqrt_c
        if norm > max_n:
            return x * (max_n / norm)
        return x.copy()

    def origin(self) -> np.ndarray:
        """Return the origin of the ball (zero vector)."""
        return np.zeros(self.dimension, dtype=np.float64)

    def random_point(self, rng: Optional[np.random.Generator] = None,
                     max_radius: float = 0.9) -> np.ndarray:
        """Generate a random point uniformly inside the ball."""
        if rng is None:
            rng = np.random.default_rng()
        direction = rng.standard_normal(self.dimension)
        direction = direction / (np.linalg.norm(direction) + 1e-10)
        radius = rng.uniform(0, max_radius / self._sqrt_c)
        return direction * radius

    def exp_map(self, v: np.ndarray, base: Optional[np.ndarray] = None) -> np.ndarray:
        """Exponential map: tangent vector → point on the manifold.

        Maps a tangent vector at `base` to a point in the ball.
        """
        if base is None:
            base = self.origin()
        base = np.asarray(base, dtype=np.float64)
        v = np.asarray(v, dtype=np.float64)

        lam = self.conformal_factor(base)
        v_norm = float(np.linalg.norm(v))
        if v_norm < 1e-10:
            return base.copy()

        sqrt_c = self._sqrt_c
        scalar = math.tanh(sqrt_c * lam * v_norm / 2.0) / (sqrt_c * v_norm)
        return self.project(base + scalar * v)

    def log_map(self, x: np.ndarray, base: Optional[np.ndarray] = None) -> np.ndarray:
        """Logarithmic map: point on manifold → tangent vector at base."""
        if base is None:
            base = self.origin()
        base = np.asarray(base, dtype=np.float64)
        x = np.asarray(x, dtype=np.float64)

        diff = x - base
        diff_norm = float(np.linalg.norm(diff))
        if diff_norm < 1e-10:
            return np.zeros_like(x)

        lam = self.conformal_factor(base)
        sqrt_c = self._sqrt_c
        scalar = 2.0 / (lam * sqrt_c) * math.atanh(sqrt_c * diff_norm)
        return scalar * (diff / diff_norm)

    def __repr__(self) -> str:
        return f"PoincareBall(dimension={self.dimension}, curvature={self.c})"
