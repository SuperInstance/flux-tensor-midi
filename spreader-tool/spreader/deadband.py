"""DeadbandDetector — is the room struggling?

Takes KPI metric snapshots and determines whether the room has entered the
deadband: the gap between what hardcoded rules handle and what needs
intelligence.

Deadband triggers (from architecture):
  - Task completion rate < 90% sustained for 5+ minutes
  - Average wait time > 30 seconds sustained
  - Energy over baseline > 10% sustained
  - Inference MAE > 10% for 3 consecutive windows
"""

import time
from typing import Dict, List, Optional

from .types import (
    DeadbandConfig,
    DeadbandMetric,
    DeadbandState,
    KPIMetrics,
)


class DeadbandDetector:
    """Stateful deadband detector with hysteresis.

    Call ``update(metrics)`` on every tick.  The detector tracks how long
    each metric has been in breach and whether the room is currently in the
    deadband.  Hysteresis prevents rapid flickering in/out: the exit
    thresholds are relaxed by ``hysteresis_exit_factor``.
    """

    def __init__(self, config: Optional[DeadbandConfig] = None) -> None:
        self._config = config or DeadbandConfig()
        self._state = DeadbandState(in_deadband=False, severity=0.0)
        self._prev_metrics: Optional[KPIMetrics] = None

        # Per-metric breach tracking
        self._breach_start: Dict[DeadbandMetric, float] = {}
        self._mae_consecutive: int = 0

    # ── Public API ───────────────────────────────────────────────────────

    def update(self, metrics: KPIMetrics) -> DeadbandState:
        """Feed a new KPI snapshot; returns current deadband state."""
        now = metrics.timestamp if metrics.timestamp is not None else time.time()
        self._prev_metrics = metrics

        breached: List[DeadbandMetric] = []
        durations: Dict[str, float] = {}

        # ── Completion rate ──────────────────────────────────────────────
        self._check_threshold_metric(
            metric=DeadbandMetric.COMPLETION_RATE,
            value=metrics.task_completion_rate,
            threshold=self._config.completion_rate_threshold,
            min_duration=self._config.completion_rate_duration,
            now=now,
            breached=breached,
            durations=durations,
            below=True,  # bad when below threshold
        )

        # ── Wait time ───────────────────────────────────────────────────
        self._check_threshold_metric(
            metric=DeadbandMetric.WAIT_TIME,
            value=metrics.avg_wait_time,
            threshold=self._config.wait_time_threshold,
            min_duration=self._config.wait_time_duration,
            now=now,
            breached=breached,
            durations=durations,
            below=False,  # bad when above threshold
        )

        # ── Energy over baseline ────────────────────────────────────────
        self._check_threshold_metric(
            metric=DeadbandMetric.ENERGY_OVER_BASELINE,
            value=metrics.energy_over_baseline,
            threshold=self._config.energy_threshold,
            min_duration=self._config.energy_duration,
            now=now,
            breached=breached,
            durations=durations,
            below=False,
        )

        # ── Inference MAE (consecutive windows) ─────────────────────────
        if metrics.inference_mae > self._config.mae_threshold:
            self._mae_consecutive += 1
        else:
            self._mae_consecutive = 0

        if self._mae_consecutive >= self._config.mae_consecutive_windows:
            breached.append(DeadbandMetric.INFERENCE_MAE)
            durations[DeadbandMetric.INFERENCE_MAE.value] = (
                self._mae_consecutive * self._config.tick_interval
            )

        # ── Determine deadband state with hysteresis ────────────────────
        currently_in = self._state.in_deadband
        new_in = len(breached) > 0

        if currently_in and not new_in:
            # Hysteresis check: must recover past threshold to exit
            new_in = not self._all_recovered(metrics)

        # ── Update state ────────────────────────────────────────────────
        if new_in and not currently_in:
            self._state.time_entered = now

        self._state.in_deadband = new_in
        self._state.breached_metrics = breached
        self._state.durations = durations
        self._state.mae_consecutive_count = self._mae_consecutive
        self._state.severity = self._compute_severity(breached, durations, now)

        # Clean up breach starts for metrics no longer breached
        active = set(breached)
        for m in list(self._breach_start):
            if m not in active and m != DeadbandMetric.INFERENCE_MAE:
                del self._breach_start[m]

        return self._state

    def is_in_deadband(self) -> bool:
        return self._state.in_deadband

    def severity(self) -> float:
        return self._state.severity

    def time_in_deadband(self) -> float:
        if not self._state.in_deadband or self._state.time_entered is None:
            return 0.0
        now = (
            self._prev_metrics.timestamp
            if self._prev_metrics and self._prev_metrics.timestamp
            else time.time()
        )
        return max(0.0, now - self._state.time_entered)

    def breached_metrics(self) -> List[DeadbandMetric]:
        return list(self._state.breached_metrics)

    def reset(self) -> None:
        self._state = DeadbandState(in_deadband=False, severity=0.0)
        self._breach_start.clear()
        self._mae_consecutive = 0
        self._prev_metrics = None

    # ── Internal ─────────────────────────────────────────────────────────

    def _check_threshold_metric(
        self,
        metric: DeadbandMetric,
        value: float,
        threshold: float,
        min_duration: float,
        now: float,
        breached: List[DeadbandMetric],
        durations: Dict[str, float],
        below: bool,
    ) -> None:
        is_breached = (value < threshold) if below else (value > threshold)

        if is_breached:
            if metric not in self._breach_start:
                self._breach_start[metric] = now
            elapsed = now - self._breach_start[metric]
            if elapsed >= min_duration:
                breached.append(metric)
                durations[metric.value] = elapsed
        else:
            self._breach_start.pop(metric, None)

    def _all_recovered(self, metrics: KPIMetrics) -> bool:
        """Check whether all metrics have recovered past hysteresis thresholds."""
        factor = self._config.hysteresis_exit_factor
        cfg = self._config

        completion_ok = metrics.task_completion_rate >= cfg.completion_rate_threshold * factor
        wait_ok = metrics.avg_wait_time <= cfg.wait_time_threshold / factor
        energy_ok = metrics.energy_over_baseline <= cfg.energy_threshold / factor
        mae_ok = self._mae_consecutive == 0

        return completion_ok and wait_ok and energy_ok and mae_ok

    def _compute_severity(
        self,
        breached: List[DeadbandMetric],
        durations: Dict[str, float],
        now: float,
    ) -> float:
        if not breached:
            return 0.0

        # Base: fraction of metrics breached
        total_metrics = 4
        breach_fraction = len(breached) / total_metrics

        # Duration factor: ramps from 0.3 to 1.0 over 10 minutes
        max_dur = max(durations.values()) if durations else 0.0
        duration_factor = min(1.0, 0.3 + 0.7 * (max_dur / 600.0))

        return min(1.0, breach_fraction * duration_factor)
