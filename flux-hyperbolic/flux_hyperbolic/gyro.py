"""
flux_hyperbolic.gyro — Gyrovector operations for hyperbolic constraint composition.

Möbius addition, scalar multiplication, and gyration for the Poincaré ball.
These are the hyperbolic analogs of vector addition and scaling.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np


def mobius_add(x: np.ndarray, y: np.ndarray, c: float = 1.0) -> np.ndarray:
    """Möbius addition in the Poincaré ball with curvature c.

    x ⊕_c y = ((1 + 2c<x,y> + c||y||²)x + (1 - c||x||²)y) / (1 + 2c<x,y> + c²||x||²||y||²)

    This is NOT commutative: x ⊕ y ≠ y ⊕ x in general.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    x_sq = float(np.dot(x, x))
    y_sq = float(np.dot(y, y))
    xy = float(np.dot(x, y))

    denom = 1.0 + 2.0 * c * xy + c * c * x_sq * y_sq
    if abs(denom) < 1e-15:
        return np.zeros_like(x)

    numerator = (1.0 + 2.0 * c * xy + c * y_sq) * x + (1.0 - c * x_sq) * y
    result = numerator / denom

    # Project back inside ball
    norm = float(np.linalg.norm(result))
    max_norm = 0.999 / math.sqrt(c) if c > 0 else 0.999
    if norm > max_norm:
        result = result * (max_norm / norm)

    return result


def mobius_multiply(r: float, x: np.ndarray, c: float = 1.0) -> np.ndarray:
    """Möbius scalar multiplication in the Poincaré ball.

    r ⊗_c x = (1/√c) * tanh(r * arctanh(√c * ||x||)) * (x / ||x||)
    """
    x = np.asarray(x, dtype=np.float64)
    if r == 0:
        return np.zeros_like(x)

    norm = float(np.linalg.norm(x))
    if norm < 1e-10:
        return np.zeros_like(x)

    sqrt_c = math.sqrt(c)
    arg = sqrt_c * norm
    arg = min(arg, 1.0 - 1e-7)

    scalar = (1.0 / sqrt_c) * math.tanh(r * math.atanh(arg)) / norm
    result = scalar * x

    # Safety clamp
    result_norm = float(np.linalg.norm(result))
    max_norm = 0.999 / sqrt_c
    if result_norm > max_norm:
        result = result * (max_norm / result_norm)

    return result


def gyro_distance(x: np.ndarray, y: np.ndarray, c: float = 1.0) -> float:
    """Hyperbolic distance via gyrolines.

    d(x,y) = (2/√c) * arctanh(√c * ||(-x) ⊕ y||)

    Equivalent to PoincareBall.distance() but using Möbius addition directly.
    """
    neg_x = -np.asarray(x, dtype=np.float64)
    diff = mobius_add(neg_x, y, c)
    norm = float(np.linalg.norm(diff))

    sqrt_c = math.sqrt(c)
    arg = sqrt_c * norm
    arg = min(arg, 1.0 - 1e-7)

    if arg < 1e-15:
        return 0.0
    return (2.0 / sqrt_c) * math.atanh(arg)
