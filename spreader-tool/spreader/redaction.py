"""Module 8: RedactionEngine — intelligence pruning.

Removes redundant or low-value FCWs while maintaining coverage above a
configurable threshold.  Each FCW's value is assessed by its marginal
coverage contribution; redundancy is measured by KPI-space overlap with
nearby entries.

Coverage model (MVP): an FCW "covers" a region of KPI space defined by
its kpi_snapshot.  Two FCWs with similar KPI snapshots are partially
redundant.  Coverage of a set is the union of all individual regions,
approximated by a pairwise distinctness metric.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from .types import FrozenContextWindow, KPIMetrics


class RedactionEngine:
    """Prune FCWs while preserving KPI-space coverage."""

    def __init__(self, coverage_threshold: float = 0.95) -> None:
        if not 0.0 <= coverage_threshold <= 1.0:
            raise ValueError("coverage_threshold must be in [0, 1]")
        self._threshold = coverage_threshold

    # ── KPI-space distance ───────────────────────────────────────────────

    @staticmethod
    def _kpi_distance(a: KPIMetrics, b: KPIMetrics) -> float:
        """Euclidean distance between two KPI snapshots, normalized to 0–1.

        Each axis is normalized to roughly [0, 1]:
          - task_completion_rate: /100
          - avg_wait_time: /60  (1 min = full scale)
          - energy_over_baseline: /50
          - inference_mae: /50
        """
        d_completion = (a.task_completion_rate - b.task_completion_rate) / 100.0
        d_wait = (a.avg_wait_time - b.avg_wait_time) / 60.0
        d_energy = (a.energy_over_baseline - b.energy_over_baseline) / 50.0
        d_mae = (a.inference_mae - b.inference_mae) / 50.0

        raw = math.sqrt(
            d_completion ** 2 + d_wait ** 2 + d_energy ** 2 + d_mae ** 2
        )
        # Max possible distance = sqrt(1 + 1 + 1 + 1) = 2.0
        return min(1.0, raw / 2.0)

    # ── Scoring ──────────────────────────────────────────────────────────

    def value_score(
        self,
        fcw: FrozenContextWindow,
        all_fcws: List[FrozenContextWindow],
    ) -> float:
        """Marginal coverage contribution of *fcw* within *all_fcws*.

        High value → this FCW covers KPI space that others don't.
        Low value  → other FCWs already cover this region.

        Computed as average distance to nearest neighbours.  Unique FCWs
        are far from everyone else → high score.  Redundant ones cluster
        → low score.
        """
        if not all_fcws:
            return 1.0

        others = [f for f in all_fcws if f.fcw_id != fcw.fcw_id]
        if not others:
            return 1.0  # sole entry is maximally valuable

        distances = [
            self._kpi_distance(fcw.kpi_snapshot, f.kpi_snapshot)
            for f in others
        ]
        return sum(distances) / len(distances)

    def redundancy_score(
        self,
        fcw: FrozenContextWindow,
        all_fcws: List[FrozenContextWindow],
    ) -> float:
        """How similar *fcw* is to its nearest neighbour (0 = unique, 1 = duplicate).

        1 - min_distance_to_any_other.
        """
        others = [f for f in all_fcws if f.fcw_id != fcw.fcw_id]
        if not others:
            return 0.0  # unique by definition

        min_dist = min(
            self._kpi_distance(fcw.kpi_snapshot, f.kpi_snapshot)
            for f in others
        )
        return 1.0 - min_dist

    # ── Ranking ──────────────────────────────────────────────────────────

    def rank_for_pruning(
        self,
        fcws: List[FrozenContextWindow],
    ) -> List[Tuple[str, float]]:
        """Return (fcw_id, score) sorted lowest-value first.

        The pruning score combines value (want to keep) and redundancy
        (want to remove).  Lower combined score = better pruning candidate.

        score = value * (1 - redundancy)
        High value + low redundancy → keep (high score).
        Low value + high redundancy → prune first (low score).
        """
        scored: List[Tuple[str, float]] = []
        for fcw in fcws:
            v = self.value_score(fcw, fcws)
            r = self.redundancy_score(fcw, fcws)
            # Combined: how much unique value does this contribute?
            combined = v * (1.0 - r)
            scored.append((fcw.fcw_id, combined))
        scored.sort(key=lambda pair: pair[1])
        return scored

    # ── Pruning ──────────────────────────────────────────────────────────

    def prune(
        self,
        fcws: List[FrozenContextWindow],
        target_reduction: float = 0.1,
    ) -> List[FrozenContextWindow]:
        """Remove lowest-value entries until *target_reduction* fraction removed.

        Stops early if coverage would drop below the configured threshold.
        """
        if not fcws or target_reduction <= 0.0:
            return list(fcws)

        target_count = max(1, int(len(fcws) * (1.0 - target_reduction)))
        ranked = self.rank_for_pruning(fcws)

        # ranked is lowest-value first → keep the LAST entries (highest value)
        keep_ids: set = {fcw_id for fcw_id, _ in ranked[-target_count:]}

        remaining = [f for f in fcws if f.fcw_id in keep_ids]

        # Coverage guard: if coverage dropped below threshold, keep more
        if remaining and self.coverage(remaining, fcws) < self._threshold:
            # Walk back: add next-highest-value entries until coverage ok
            remaining_ids = {f.fcw_id for f in remaining}
            for fcw_id, _ in reversed(ranked):
                if fcw_id in remaining_ids:
                    continue
                fcw_obj = next(f for f in fcws if f.fcw_id == fcw_id)
                remaining.append(fcw_obj)
                remaining_ids.add(fcw_id)
                if self.coverage(remaining, fcws) >= self._threshold:
                    break

        return remaining

    # ── Coverage ─────────────────────────────────────────────────────────

    def coverage(
        self,
        remaining: List[FrozenContextWindow],
        original: List[FrozenContextWindow],
    ) -> float:
        """What fraction of the original KPI-space is still covered.

        For each original FCW, we check whether at least one remaining FCW
        is within a distance threshold (0.25 in normalized KPI space).
        Coverage = fraction of originals that have a nearby remaining FCW.
        """
        if not original:
            return 1.0
        if not remaining:
            return 0.0

        proximity_threshold = 0.25

        covered = 0
        for orig in original:
            for rem in remaining:
                if self._kpi_distance(orig.kpi_snapshot, rem.kpi_snapshot) <= proximity_threshold:
                    covered += 1
                    break

        return covered / len(original)
