"""Module 7: CostTracker — intelligence cost measurement and refinement gradient.

Measures the computational cost of intelligence (seeds + context windows)
and computes the refinement gradient: how much coverage gain per unit of cost.

A positive gradient means intelligence is paying for itself.
"""

from __future__ import annotations

from typing import List

from .types import FrozenContextWindow, Seed


# ── Normalization constants ─────────────────────────────────────────────────
# These anchor the 0-1 normalization range.  Values beyond these just clamp.

_MAX_CONTEXT_WINDOWS: int = 100  # normalization ceiling for FCW count
_MAX_EXTENSIONS_KEYS: int = 50   # normalization ceiling for extension keys


class CostTracker:
    """Track and measure the cost of intelligence artifacts."""

    def __init__(self) -> None:
        pass

    # ── Cost metrics ─────────────────────────────────────────────────────

    def model_cost(self, seed: Seed) -> float:
        """Normalized cost of a seed (0–1).

        Cost proxy: number of context windows linked to the seed,
        normalized against a reasonable ceiling.
        """
        n_windows = len(seed.context_window_ids)
        return min(1.0, n_windows / _MAX_CONTEXT_WINDOWS)

    def context_cost(self, fcw: FrozenContextWindow) -> float:
        """Normalized cost of a single FCW (0–1).

        Cost proxy: number of extension keys (richer context = more cost),
        plus a base cost of 1 unit for the FCW itself.
        """
        n_ext = len(fcw.extensions)
        raw = 1 + n_ext
        ceiling = 1 + _MAX_EXTENSIONS_KEYS
        return min(1.0, raw / ceiling)

    def total_cost(
        self,
        seed: Seed,
        fcws: List[FrozenContextWindow],
    ) -> float:
        """Combined cost of a seed and its associated FCWs (0–1).

        Sums model_cost + all context_costs, then clamps to 1.0.
        """
        cost = self.model_cost(seed)
        for fcw in fcws:
            cost += self.context_cost(fcw)
        return min(1.0, cost)

    # ── Refinement gradient ──────────────────────────────────────────────

    @staticmethod
    def refinement_gradient(
        before_cost: float,
        after_cost: float,
        before_coverage: float,
        after_coverage: float,
    ) -> float:
        """Compute G = Δcoverage / Δcost.

        Returns:
            Positive → intelligence is paying for itself.
            Negative → cost increased faster than coverage.
            Zero     → no change in cost.
        """
        delta_cost = after_cost - before_cost
        delta_coverage = after_coverage - before_coverage

        if delta_cost == 0.0:
            # No cost change: positive if coverage improved, zero otherwise
            return float("inf") if delta_coverage > 0 else 0.0

        return delta_coverage / delta_cost

    @staticmethod
    def is_worth_it(gradient: float) -> bool:
        """A positive gradient means intelligence is paying for itself."""
        return gradient > 0
