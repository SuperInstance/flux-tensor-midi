"""Tests for DeadbandDetector."""

import time

import pytest

from spreader.deadband import DeadbandDetector
from spreader.types import DeadbandConfig, DeadbandMetric, KPIMetrics


# ── Helpers ─────────────────────────────────────────────────────────────────

def good_metrics(ts=None):
    return KPIMetrics(
        task_completion_rate=95.0,
        avg_wait_time=10.0,
        energy_over_baseline=5.0,
        inference_mae=3.0,
        timestamp=ts,
    )


def bad_completion(ts=None):
    return KPIMetrics(
        task_completion_rate=80.0,   # below 90%
        avg_wait_time=10.0,
        energy_over_baseline=5.0,
        inference_mae=3.0,
        timestamp=ts,
    )


def bad_wait(ts=None):
    return KPIMetrics(
        task_completion_rate=95.0,
        avg_wait_time=40.0,          # above 30s
        energy_over_baseline=5.0,
        inference_mae=3.0,
        timestamp=ts,
    )


def bad_energy(ts=None):
    return KPIMetrics(
        task_completion_rate=95.0,
        avg_wait_time=10.0,
        energy_over_baseline=15.0,   # above 10%
        inference_mae=3.0,
        timestamp=ts,
    )


def bad_mae(ts=None):
    return KPIMetrics(
        task_completion_rate=95.0,
        avg_wait_time=10.0,
        energy_over_baseline=5.0,
        inference_mae=15.0,          # above 10%
        timestamp=ts,
    )


def all_bad(ts=None):
    return KPIMetrics(
        task_completion_rate=70.0,
        avg_wait_time=60.0,
        energy_over_baseline=25.0,
        inference_mae=20.0,
        timestamp=ts,
    )


# ── Config for fast tests ───────────────────────────────────────────────────

FAST_CONFIG = DeadbandConfig(
    completion_rate_threshold=90.0,
    completion_rate_duration=60.0,   # 1 min instead of 5
    wait_time_threshold=30.0,
    wait_time_duration=10.0,         # 10s
    energy_threshold=10.0,
    energy_duration=10.0,
    mae_threshold=10.0,
    mae_consecutive_windows=3,
    hysteresis_exit_factor=1.1,
    tick_interval=1.0,
)


# ── Tests ───────────────────────────────────────────────────────────────────

class TestNotInDeadband:
    def test_all_metrics_good(self):
        d = DeadbandDetector()
        state = d.update(good_metrics())
        assert not state.in_deadband
        assert state.severity == 0.0
        assert state.breached_metrics == []

    def test_sustained_good_metrics(self):
        d = DeadbandDetector()
        base = 1000.0
        for i in range(10):
            d.update(good_metrics(ts=base + i * 10))
        assert not d.is_in_deadband()


class TestEntersDeadband:
    def test_completion_rate_drop(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 1000.0

        # Good for a while
        for i in range(5):
            d.update(good_metrics(ts=base + i * 10))

        # Drop completion rate for sustained period
        for i in range(10):
            state = d.update(bad_completion(ts=base + 50 + i * 10))

        assert d.is_in_deadband()
        assert DeadbandMetric.COMPLETION_RATE in d.breached_metrics()

    def test_mae_consecutive_windows(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 2000.0

        for i in range(2):
            d.update(bad_mae(ts=base + i))
        assert not d.is_in_deadband()  # only 2 consecutive

        d.update(bad_mae(ts=base + 2))
        assert d.is_in_deadband()
        assert DeadbandMetric.INFERENCE_MAE in d.breached_metrics()

    def test_wait_time_sustained(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 3000.0

        for i in range(5):
            d.update(bad_wait(ts=base + i * 5))

        assert d.is_in_deadband()
        assert DeadbandMetric.WAIT_TIME in d.breached_metrics()


class TestSeverity:
    def test_severity_increases_over_time(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 4000.0
        severities = []

        for i in range(15):
            d.update(bad_completion(ts=base + i * 10))
            if d.is_in_deadband():
                severities.append(d.severity())

        # Severity should be non-decreasing once in deadband
        assert len(severities) >= 2
        for i in range(1, len(severities)):
            assert severities[i] >= severities[i - 1]

    def test_severity_zero_when_not_in_deadband(self):
        d = DeadbandDetector()
        assert d.severity() == 0.0
        d.update(good_metrics())
        assert d.severity() == 0.0

    def test_severity_capped_at_one(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 5000.0

        # All metrics bad for a long time
        for i in range(100):
            d.update(all_bad(ts=base + i * 10))

        assert d.severity() <= 1.0
        assert d.severity() > 0.0


class TestExitsDeadband:
    def test_recovery(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 6000.0

        # Enter deadband
        for i in range(10):
            d.update(bad_completion(ts=base + i * 10))
        assert d.is_in_deadband()

        # Recover with hysteresis — need 90 * 1.1 = 99% completion
        for i in range(10):
            d.update(KPIMetrics(
                task_completion_rate=99.5,  # above hysteresis
                avg_wait_time=10.0,
                energy_over_baseline=5.0,
                inference_mae=3.0,
                timestamp=base + 100 + i * 10,
            ))
        assert not d.is_in_deadband()

    def test_time_in_deadband_resets(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 7000.0

        for i in range(10):
            d.update(bad_completion(ts=base + i * 10))
        assert d.time_in_deadband() > 0

        # Recover
        for i in range(10):
            d.update(KPIMetrics(
                task_completion_rate=99.5,
                avg_wait_time=10.0,
                energy_over_baseline=5.0,
                inference_mae=3.0,
                timestamp=base + 100 + i * 10,
            ))
        assert d.time_in_deadband() == 0.0


class TestMultipleMetrics:
    def test_multiple_breached_simultaneously(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 8000.0

        # Bad completion + bad wait time for sustained period
        for i in range(15):
            d.update(KPIMetrics(
                task_completion_rate=80.0,
                avg_wait_time=40.0,
                energy_over_baseline=5.0,
                inference_mae=3.0,
                timestamp=base + i * 10,
            ))

        assert d.is_in_deadband()
        breached = d.breached_metrics()
        assert DeadbandMetric.COMPLETION_RATE in breached
        assert DeadbandMetric.WAIT_TIME in breached
        assert len(breached) >= 2

    def test_all_four_breached(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 9000.0

        for i in range(15):
            d.update(all_bad(ts=base + i * 10))

        assert len(d.breached_metrics()) == 4


class TestHysteresis:
    def test_no_flicker_on_marginal_recovery(self):
        """Room shouldn't exit deadband if metrics barely cross threshold."""
        d = DeadbandDetector(FAST_CONFIG)
        base = 10000.0

        # Enter deadband
        for i in range(15):
            d.update(bad_completion(ts=base + i * 10))
        assert d.is_in_deadband()

        # Marginal recovery: exactly at threshold (90%), not past hysteresis (99%)
        for i in range(5):
            d.update(KPIMetrics(
                task_completion_rate=90.0,  # exactly at threshold, NOT past hysteresis
                avg_wait_time=10.0,
                energy_over_baseline=5.0,
                inference_mae=3.0,
                timestamp=base + 150 + i * 10,
            ))
        # Should still be in deadband due to hysteresis
        assert d.is_in_deadband()

    def test_full_recovery_exits(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 11000.0

        for i in range(15):
            d.update(bad_completion(ts=base + i * 10))
        assert d.is_in_deadband()

        # Full recovery past hysteresis
        for i in range(5):
            d.update(KPIMetrics(
                task_completion_rate=99.5,  # well past 99% hysteresis
                avg_wait_time=5.0,
                energy_over_baseline=2.0,
                inference_mae=1.0,
                timestamp=base + 150 + i * 10,
            ))
        assert not d.is_in_deadband()


class TestReset:
    def test_reset_clears_state(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 12000.0

        for i in range(15):
            d.update(bad_completion(ts=base + i * 10))
        assert d.is_in_deadband()

        d.reset()
        assert not d.is_in_deadband()
        assert d.severity() == 0.0
        assert d.time_in_deadband() == 0.0
        assert d.breached_metrics() == []

    def test_reset_then_reenter(self):
        d = DeadbandDetector(FAST_CONFIG)
        base = 13000.0

        d.update(bad_completion(ts=base))
        d.reset()

        for i in range(10):
            d.update(bad_completion(ts=base + 100 + i * 10))
        assert d.is_in_deadband()
