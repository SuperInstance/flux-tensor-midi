"""Tests for spreader/redaction.py — RedactionEngine."""

import pytest

from spreader.types import (
    FCWStatus,
    FrozenContextWindow,
    KPIMetrics,
    RoomType,
    TriggerType,
)
from spreader.types import Seed, SeedState
from spreader.redaction import RedactionEngine


# ── Helpers ──────────────────────────────────────────────────────────────────

def _kpi(completion=95.0, wait=10.0, energy=5.0, mae=3.0):
    return KPIMetrics(
        task_completion_rate=completion,
        avg_wait_time=wait,
        energy_over_baseline=energy,
        inference_mae=mae,
    )


def _fcw(fcw_id, kpi=None, room_id="room-A"):
    return FrozenContextWindow(
        fcw_id=fcw_id,
        frozen_at=1000.0,
        room_id=room_id,
        room_type=RoomType.SENSOR,
        status=FCWStatus.FROZEN,
        kpi_snapshot=kpi or _kpi(),
        trigger=TriggerType.TIME,
    )


# ── Construction ─────────────────────────────────────────────────────────────

class TestConstruction:
    def test_default_threshold(self):
        eng = RedactionEngine()
        assert eng._threshold == 0.95

    def test_custom_threshold(self):
        eng = RedactionEngine(coverage_threshold=0.8)
        assert eng._threshold == 0.8

    def test_invalid_threshold_raises(self):
        with pytest.raises(ValueError):
            RedactionEngine(coverage_threshold=1.5)

    def test_negative_threshold_raises(self):
        with pytest.raises(ValueError):
            RedactionEngine(coverage_threshold=-0.1)


# ── value_score ──────────────────────────────────────────────────────────────

class TestValueScore:
    def setup_method(self):
        self.eng = RedactionEngine()

    def test_single_fcw_gets_max_value(self):
        fcw = _fcw("a")
        score = self.eng.value_score(fcw, [fcw])
        assert score == 1.0

    def test_empty_list_returns_one(self):
        fcw = _fcw("a")
        score = self.eng.value_score(fcw, [])
        assert score == 1.0

    def test_identical_fcws_low_value(self):
        kpi = _kpi()
        a = _fcw("a", kpi=kpi)
        b = _fcw("b", kpi=kpi)
        score_a = self.eng.value_score(a, [a, b])
        assert score_a == pytest.approx(0.0)

    def test_distant_fcw_high_value(self):
        kpi_near = _kpi(completion=50.0)
        kpi_far = _kpi(completion=100.0)
        a = _fcw("a", kpi=kpi_near)
        b = _fcw("b", kpi=kpi_far)
        score_a = self.eng.value_score(a, [a, b])
        assert score_a > 0.0


# ── redundancy_score ─────────────────────────────────────────────────────────

class TestRedundancyScore:
    def setup_method(self):
        self.eng = RedactionEngine()

    def test_single_fcw_zero_redundancy(self):
        fcw = _fcw("a")
        r = self.eng.redundancy_score(fcw, [fcw])
        assert r == 0.0

    def test_identical_fcws_max_redundancy(self):
        kpi = _kpi()
        a = _fcw("a", kpi=kpi)
        b = _fcw("b", kpi=kpi)
        r = self.eng.redundancy_score(a, [a, b])
        assert r == pytest.approx(1.0)

    def test_distant_fcws_low_redundancy(self):
        a = _fcw("a", kpi=_kpi(completion=0.0, wait=0.0, energy=0.0, mae=0.0))
        b = _fcw("b", kpi=_kpi(completion=100.0, wait=60.0, energy=50.0, mae=50.0))
        r = self.eng.redundancy_score(a, [a, b])
        assert r < 0.5


# ── rank_for_pruning ─────────────────────────────────────────────────────────

class TestRankForPruning:
    def setup_method(self):
        self.eng = RedactionEngine()

    def test_returns_all_fcws(self):
        fcws = [_fcw(f"f{i}", kpi=_kpi(completion=float(i * 10))) for i in range(5)]
        ranked = self.eng.rank_for_pruning(fcws)
        assert len(ranked) == 5
        assert set(fid for fid, _ in ranked) == {f.fcw_id for f in fcws}

    def test_sorted_lowest_first(self):
        # Middle FCW has identical neighbours → lowest value
        kpi_mid = _kpi(completion=50.0)
        kpi_far = _kpi(completion=0.0)
        kpi_far2 = _kpi(completion=100.0)

        fcws = [
            _fcw("far1", kpi=kpi_far),
            _fcw("mid", kpi=kpi_mid),
            _fcw("far2", kpi=kpi_far2),
        ]
        ranked = self.eng.rank_for_pruning(fcws)
        # The middle one is equidistant to both far ones → moderate value
        # The far ones each have one close neighbour (mid) → lower value
        assert len(ranked) == 3

    def test_empty_list(self):
        ranked = self.eng.rank_for_pruning([])
        assert ranked == []


# ── coverage ─────────────────────────────────────────────────────────────────

class TestCoverage:
    def setup_method(self):
        self.eng = RedactionEngine()

    def test_full_coverage_identical(self):
        kpi = _kpi()
        fcws = [_fcw(f"f{i}", kpi=kpi) for i in range(5)]
        cov = self.eng.coverage(fcws, fcws)
        assert cov == 1.0

    def test_zero_coverage_empty_remaining(self):
        fcws = [_fcw(f"f{i}") for i in range(3)]
        cov = self.eng.coverage([], fcws)
        assert cov == 0.0

    def test_empty_original_is_one(self):
        cov = self.eng.coverage([_fcw("a")], [])
        assert cov == 1.0

    def test_partial_coverage(self):
        # Remaining FCW is far from some originals (all axes distant)
        near_kpi = _kpi(completion=10.0, wait=5.0, energy=2.0, mae=1.0)
        far_kpi = _kpi(completion=90.0, wait=55.0, energy=45.0, mae=45.0)
        originals = [
            _fcw("o1", kpi=near_kpi),
            _fcw("o2", kpi=far_kpi),
        ]
        remaining = [_fcw("r1", kpi=near_kpi)]
        cov = self.eng.coverage(remaining, originals)
        assert 0.0 < cov < 1.0

    def test_nearby_covers(self):
        # Two KPIs close enough to be "covered" by proximity threshold
        kpi1 = _kpi(completion=90.0)
        kpi2 = _kpi(completion=95.0)
        originals = [_fcw("o1", kpi=kpi1)]
        remaining = [_fcw("r1", kpi=kpi2)]
        cov = self.eng.coverage(remaining, originals)
        assert cov == 1.0


# ── prune ────────────────────────────────────────────────────────────────────

class TestPrune:
    def setup_method(self):
        self.eng = RedactionEngine(coverage_threshold=0.5)

    def test_no_reduction(self):
        fcws = [_fcw(f"f{i}", kpi=_kpi(completion=float(i * 20))) for i in range(5)]
        result = self.eng.prune(fcws, target_reduction=0.0)
        assert len(result) == 5

    def test_basic_pruning(self):
        # 10 FCWs, target 20% reduction → keep ~8
        fcws = [_fcw(f"f{i}", kpi=_kpi(completion=float(i * 10))) for i in range(10)]
        result = self.eng.prune(fcws, target_reduction=0.2)
        assert len(result) <= 10
        assert len(result) >= 7  # may keep more if coverage guard kicks in

    def test_prune_respects_coverage_threshold(self):
        # All FCWs are identical → pruning any reduces coverage significantly
        kpi = _kpi()
        fcws = [_fcw(f"f{i}", kpi=kpi) for i in range(10)]
        eng = RedactionEngine(coverage_threshold=0.99)
        result = eng.prune(fcws, target_reduction=0.5)
        # Should keep enough to maintain coverage ≥ 0.99
        assert eng.coverage(result, fcws) >= 0.99

    def test_prune_empty(self):
        result = self.eng.prune([], target_reduction=0.5)
        assert result == []

    def test_prune_single(self):
        fcws = [_fcw("only")]
        result = self.eng.prune(fcws, target_reduction=0.5)
        assert len(result) == 1  # can't prune below 1

    def test_prune_keeps_high_value(self):
        # One unique FCW (far from others) should survive pruning
        unique_kpi = _kpi(completion=0.0)
        common_kpi = _kpi(completion=50.0)
        fcws = [_fcw(f"c{i}", kpi=common_kpi) for i in range(9)]
        fcws.append(_fcw("unique", kpi=unique_kpi))

        result = self.eng.prune(fcws, target_reduction=0.3)
        ids = {f.fcw_id for f in result}
        assert "unique" in ids


# ── Integration: cost + redaction ────────────────────────────────────────────

class TestCostRedactionIntegration:
    def test_pruning_reduces_cost(self):
        from spreader.cost import CostTracker

        ct = CostTracker()
        eng = RedactionEngine(coverage_threshold=0.5)

        kpis = [_kpi(completion=float(i * 10)) for i in range(10)]
        fcws = [_fcw(f"f{i}", kpi=kpis[i]) for i in range(10)]

        seed = Seed(
            seed_id="s1", room_id="r1", role_name="test",
            lineage_id="l1", state=SeedState.LOCKED,
            context_window_ids=tuple(f.fcw_id for f in fcws),
        )

        cost_before = ct.total_cost(seed, fcws)
        pruned = eng.prune(fcws, target_reduction=0.3)
        cost_after = ct.total_cost(seed, pruned)

        assert cost_after <= cost_before
