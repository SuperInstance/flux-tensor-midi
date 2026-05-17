"""Tests for spreader/cost.py — CostTracker."""

import pytest

from spreader.types import (
    FCWStatus,
    FrozenContextWindow,
    KPIMetrics,
    RoomType,
    Seed,
    SeedState,
    TriggerType,
)
from spreader.cost import CostTracker


# ── Helpers ──────────────────────────────────────────────────────────────────

def _kpi(completion=95.0, wait=10.0, energy=5.0, mae=3.0):
    return KPIMetrics(
        task_completion_rate=completion,
        avg_wait_time=wait,
        energy_over_baseline=energy,
        inference_mae=mae,
    )


def _fcw(fcw_id="fcw-1", room_id="room-A", ext=None, status=FCWStatus.FROZEN):
    return FrozenContextWindow(
        fcw_id=fcw_id,
        frozen_at=1000.0,
        room_id=room_id,
        room_type=RoomType.SENSOR,
        status=status,
        kpi_snapshot=_kpi(),
        trigger=TriggerType.TIME,
        extensions=ext or {},
    )


def _seed(seed_id="seed-1", room_id="room-A", n_windows=0):
    return Seed(
        seed_id=seed_id,
        room_id=room_id,
        role_name="drift-detect",
        lineage_id="lineage-1",
        state=SeedState.LOCKED,
        context_window_ids=tuple(f"fcw-{i}" for i in range(n_windows)),
    )


# ── CostTracker.model_cost ──────────────────────────────────────────────────

class TestModelCost:
    def setup_method(self):
        self.ct = CostTracker()

    def test_zero_windows(self):
        seed = _seed(n_windows=0)
        assert self.ct.model_cost(seed) == 0.0

    def test_some_windows(self):
        seed = _seed(n_windows=10)
        cost = self.ct.model_cost(seed)
        assert 0.0 < cost < 1.0
        assert cost == pytest.approx(10 / 100)

    def test_max_windows_clamps(self):
        seed = _seed(n_windows=200)
        assert self.ct.model_cost(seed) == 1.0


# ── CostTracker.context_cost ────────────────────────────────────────────────

class TestContextCost:
    def setup_method(self):
        self.ct = CostTracker()

    def test_no_extensions(self):
        fcw = _fcw(ext={})
        cost = self.ct.context_cost(fcw)
        assert cost == pytest.approx(1 / 51)  # (1 + 0) / (1 + 50)

    def test_with_extensions(self):
        fcw = _fcw(ext={"a": 1, "b": 2, "c": 3})
        cost = self.ct.context_cost(fcw)
        assert cost == pytest.approx(4 / 51)

    def test_many_extensions_clamps(self):
        ext = {f"k{i}": i for i in range(100)}
        fcw = _fcw(ext=ext)
        assert self.ct.context_cost(fcw) == 1.0


# ── CostTracker.total_cost ──────────────────────────────────────────────────

class TestTotalCost:
    def setup_method(self):
        self.ct = CostTracker()

    def test_zero_everything(self):
        seed = _seed(n_windows=0)
        assert self.ct.total_cost(seed, []) == 0.0

    def test_combines_seed_and_fcws(self):
        seed = _seed(n_windows=10)
        fcws = [_fcw(fcw_id=f"f{i}") for i in range(3)]
        cost = self.ct.total_cost(seed, fcws)
        expected = 10 / 100 + 3 * (1 / 51)
        assert cost == pytest.approx(expected)

    def test_clamps_to_one(self):
        seed = _seed(n_windows=100)
        fcws = [_fcw(ext={f"k{i}": i for i in range(50)}) for _ in range(5)]
        assert self.ct.total_cost(seed, fcws) == 1.0


# ── CostTracker.refinement_gradient ─────────────────────────────────────────

class TestRefinementGradient:
    def test_positive_gradient(self):
        g = CostTracker.refinement_gradient(
            before_cost=0.2, after_cost=0.3,
            before_coverage=0.5, after_coverage=0.8,
        )
        # Δcoverage=0.3, Δcost=0.1 → G=3.0
        assert g == pytest.approx(3.0)

    def test_negative_gradient(self):
        g = CostTracker.refinement_gradient(
            before_cost=0.2, after_cost=0.5,
            before_coverage=0.8, after_coverage=0.7,
        )
        # Δcoverage=-0.1, Δcost=0.3 → G=-0.333...
        assert g < 0

    def test_zero_cost_change_positive_coverage(self):
        g = CostTracker.refinement_gradient(0.5, 0.5, 0.4, 0.6)
        assert g == float("inf")

    def test_zero_cost_change_no_coverage_change(self):
        g = CostTracker.refinement_gradient(0.5, 0.5, 0.5, 0.5)
        assert g == 0.0

    def test_gradient_boundary(self):
        # Exact zero gradient: coverage and cost both increase by same ratio
        g = CostTracker.refinement_gradient(0.0, 0.1, 0.0, 0.1)
        assert g == pytest.approx(1.0)


# ── CostTracker.is_worth_it ─────────────────────────────────────────────────

class TestIsWorthIt:
    def test_positive_gradient(self):
        assert CostTracker.is_worth_it(0.5) is True

    def test_zero_gradient(self):
        assert CostTracker.is_worth_it(0.0) is False

    def test_negative_gradient(self):
        assert CostTracker.is_worth_it(-1.0) is False

    def test_inf_gradient(self):
        assert CostTracker.is_worth_it(float("inf")) is True
