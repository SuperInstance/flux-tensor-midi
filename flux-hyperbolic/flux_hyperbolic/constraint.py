"""
flux_hyperbolic.constraint — Hyperbolic constraint checking.

Constraints are balls in hyperbolic space: a center point and a radius
(in hyperbolic distance). A point satisfies the constraint if its
hyperbolic distance to the center is within the radius.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np

from flux_hyperbolic.ball import PoincareBall


@dataclass
class HyperbolicCheckResult:
    """Result of checking a point against a hyperbolic constraint."""
    inside: bool
    hyperbolic_distance: float
    center: np.ndarray
    point: np.ndarray
    constraint_radius: float
    margin: float  # radius - distance (positive = inside)

    def to_dict(self) -> dict:
        return {
            "inside": self.inside,
            "hyperbolic_distance": self.hyperbolic_distance,
            "constraint_radius": self.constraint_radius,
            "margin": self.margin,
        }


class HyperbolicConstraint:
    """
    A constraint defined as a ball in hyperbolic space.

    The constraint is: d_hyp(point, center) <= radius
    where d_hyp is hyperbolic distance in the Poincaré ball model.

    This naturally captures hierarchical relationships: constraints deeper
    in the hierarchy are closer to the boundary (higher hyperbolic distance
    from origin) and have smaller radii (more specific).

    Usage:
        ball = PoincareBall(dimension=3)
        hc = HyperbolicConstraint(ball, center=[0.3, -0.2, 0.1], radius=1.5)
        result = hc.check([0.35, -0.15, 0.12])
    """

    def __init__(self, ball: PoincareBall,
                 center: Optional[np.ndarray] = None,
                 radius: float = 1.0):
        self.ball = ball
        if center is None:
            self.center = ball.origin()
        else:
            self.center = ball.project(np.asarray(center, dtype=np.float64))
        self.radius = radius

    def check(self, point: np.ndarray) -> HyperbolicCheckResult:
        """Check if a point satisfies the hyperbolic constraint."""
        point = self.ball.project(np.asarray(point, dtype=np.float64))
        dist = self.ball.distance(self.center, point)
        margin = self.radius - dist
        return HyperbolicCheckResult(
            inside=dist <= self.radius,
            hyperbolic_distance=dist,
            center=self.center,
            point=point,
            constraint_radius=self.radius,
            margin=margin,
        )

    def check_batch(self, points: np.ndarray) -> List[HyperbolicCheckResult]:
        """Check multiple points against this constraint."""
        points = np.asarray(points, dtype=np.float64)
        if points.ndim == 1:
            points = points.reshape(1, -1)
        return [self.check(p) for p in points]

    def __repr__(self) -> str:
        return f"HyperbolicConstraint(ball={self.ball}, radius={self.radius:.3f})"


class HierarchicalConstraintSystem:
    """
    A tree of hyperbolic constraints representing a hierarchy.

    Each level of the hierarchy is a set of hyperbolic constraints.
    Deeper levels correspond to constraints closer to the ball boundary
    (more specific). A point satisfies the system if it satisfies at least
    one constraint at each level.
    """

    def __init__(self, ball: PoincareBall):
        self.ball = ball
        self._levels: Dict[int, List[HyperbolicConstraint]] = {}

    def add_constraint(self, level: int, constraint: HyperbolicConstraint) -> None:
        """Add a constraint at a given hierarchy level (0 = root)."""
        if level not in self._levels:
            self._levels[level] = []
        self._levels[level].append(constraint)

    def check(self, point: np.ndarray) -> dict:
        """Check a point against all levels of the hierarchy.

        Returns dict with:
            satisfied: bool — satisfied at ALL levels
            per_level: {level: bool} — satisfied at each level
            matching_constraints: {level: int} — how many constraints matched per level
            deepest_match: int — deepest level where at least one constraint matched
        """
        point = self.ball.project(np.asarray(point, dtype=np.float64))
        per_level = {}
        matching = {}
        for level in sorted(self._levels.keys()):
            constraints = self._levels[level]
            any_match = False
            n_match = 0
            for c in constraints:
                r = c.check(point)
                if r.inside:
                    any_match = True
                    n_match += 1
            per_level[level] = any_match
            matching[level] = n_match

        all_satisfied = all(per_level.values()) if per_level else False
        deepest = max((l for l, ok in per_level.items() if ok), default=-1)

        return {
            "satisfied": all_satisfied,
            "per_level": per_level,
            "matching_constraints": matching,
            "deepest_match": deepest,
        }

    @property
    def n_levels(self) -> int:
        return len(self._levels)

    def __repr__(self) -> str:
        total = sum(len(cs) for cs in self._levels.values())
        return f"HierarchicalConstraintSystem(levels={self.n_levels}, total_constraints={total})"
