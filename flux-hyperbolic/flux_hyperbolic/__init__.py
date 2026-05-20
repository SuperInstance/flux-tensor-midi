"""
flux_hyperbolic — Hyperbolic geometry constraints via Poincaré ball model.

For hierarchical constraint systems where Euclidean geometry distorts relationships.
"""

from flux_hyperbolic.ball import PoincareBall
from flux_hyperbolic.constraint import HyperbolicConstraint, HyperbolicCheckResult
from flux_hyperbolic.gyro import mobius_add, mobius_multiply, gyro_distance

__all__ = [
    "PoincareBall",
    "HyperbolicConstraint",
    "HyperbolicCheckResult",
    "mobius_add",
    "mobius_multiply",
    "gyro_distance",
]
__version__ = "0.1.0"
