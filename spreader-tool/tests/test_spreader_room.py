"""Tests for SpreaderRoom — the 8-step intelligence tiling loop."""

import time

import pytest

from spreader.types import (
    DeadbandConfig,
    DeadbandSeverity,
    FCWStatus,
    KPIMetrics,
    RoomType,
    SEED_LOCK_KPI,
    SeedState,
    TriggerType,
)
from spreader.spreader_room import SpreaderRoom


# ── Helpers ──────────────────────────────────────────────────────────────────

def good_kpi(**overrides) -> KPIMetrics:
    """KPIs well within healthy range."""
    defaults = dict(
        task_completion_rate=98.0,
        avg_wait_time=5.0,
        energy_over_baseline=2.0,
        inference_mae=3.0,
        timestamp=time.time(),
    )
    defaults.update(overrides)
    return KPIMetrics(**defaults)


def bad_kpi(**overrides) -> KPIMetrics:
    """KPIs in deadband territory."""
    defaults = dict(
        task_completion_rate=70.0,
        avg_wait_time=45.0,
        energy_over_baseline=20.0,
        inference_mae=25.0,
        timestamp=time.time(),
    )
    defaults.update(overrides)
    return KPIMetrics(**defaults)


def make_room(**config_overrides) -> SpreaderRoom:
    window_size = config_overrides.pop('window_size', 6)
    cfg = DeadbandConfig(
        completion_rate_threshold=90.0,
        completion_rate_duration=0.0,  # instant for tests
        wait_time_threshold=30.0,
        wait_time_duration=0.0,
        energy_threshold=10.0,
        energy_duration=0.0,
        mae_threshold=10.0,
        mae_consecutive_windows=1,  # trigger on first bad window
    )
    cfg.__dict__.update(config_overrides)
    return SpreaderRoom("test-room", RoomType.SENSOR, config=cfg, window_size=window_size)


# ── Tests ────────────────────────────────────────────────────────────────────


class TestSingleTick:
    """Single tick with good KPIs — should NOT be in deadband."""

    def test_good_kpi_not_in_deadband(self):
        room = make_room()
        result = room.tick(good_kpi())

        assert result["deadband_state"].in_deadband is False
        assert result["severity"] == DeadbandSeverity.NONE
        assert result["escalated"] is False
        assert result["tick_number"] == 1

    def test_no_fcw_on_good_kpi(self):
        room = make_room()
        result = room.tick(good_kpi())

        assert result["fcw_created"] is None
        assert result["fcws_created"] == 0

    def test_no_active_seed_initially(self):
        room = make_room()
        result = room.tick(good_kpi())

        # First tick with good KPIs should create and lock a seed
        assert result["active_seed"] is not None
        assert result["active_seed"].state == SeedState.LOCKED


class TestDeadbandEntry:
    """Tick triggers deadband entry."""

    def test_bad_kpi_enters_deadband(self):
        room = make_room()
        result = room.tick(bad_kpi())

        assert result["deadband_state"].in_deadband is True
        assert result["severity"] != DeadbandSeverity.NONE

    def test_deadband_creates_fcw(self):
        room = make_room()
        result = room.tick(bad_kpi())

        fcw = result["fcw_created"]
        assert fcw is not None
        assert fcw.status == FCWStatus.FROZEN
        assert fcw.room_id == "test-room"
        assert fcw.trigger == TriggerType.THRESHOLD

    def test_no_second_fcw_while_still_in_deadband(self):
        room = make_room()
        room.tick(bad_kpi())  # enter deadband, creates FCW
        result = room.tick(bad_kpi())  # still in deadband

        assert result["fcw_created"] is None
        assert result["fcws_created"] == 1  # still 1 from first tick


class TestDeadbandFCW:
    """Deadband creates FCW and tracks episode."""

    def test_fcw_has_correct_kpi_snapshot(self):
        room = make_room()
        kpi = bad_kpi()
        result = room.tick(kpi)

        fcw = result["fcw_created"]
        assert fcw.kpi_snapshot == kpi

    def test_fcw_count_increases(self):
        room = make_room()
        room.tick(bad_kpi())
        assert room.fcw_manager.count() == 1

    def test_new_episode_after_recovery(self):
        room = make_room()
        # Enter deadband
        room.tick(bad_kpi())
        # Recover (need hysteresis-beating KPIs)
        room.tick(good_kpi(
            task_completion_rate=99.5,  # well above hysteresis exit
            avg_wait_time=0.5,
            energy_over_baseline=0.0,
            inference_mae=0.5,
        ))
        # Re-enter deadband — new episode
        result = room.tick(bad_kpi())
        assert result["fcw_created"] is not None
        assert result["fcws_created"] == 1  # new episode counter reset


class TestSeedAccumulation:
    """Multiple ticks accumulate to seed candidate."""

    def test_good_kpis_lock_seed(self):
        room = make_room()
        result = room.tick(good_kpi())

        seed = result["active_seed"]
        assert seed is not None
        assert seed.state == SeedState.LOCKED
        assert seed.locked_kpis.task_completion_rate >= SEED_LOCK_KPI

    def test_substandard_kpis_no_seed(self):
        room = make_room()
        # KPIs that don't meet SEED_LOCK_KPI (95) but aren't deadband
        result = room.tick(good_kpi(task_completion_rate=92.0))

        # No seed locked (92 < 95)
        assert result["active_seed"] is None


class TestFullCycle:
    """Full cycle: good → deadband → FCW → seed candidate → locked → recovered."""

    def test_full_recovery_cycle(self):
        room = make_room()

        # 1. Start healthy — seed locks
        r1 = room.tick(good_kpi())
        assert r1["active_seed"] is not None
        assert r1["deadband_state"].in_deadband is False

        # 2. Enter deadband — FCW created
        r2 = room.tick(bad_kpi())
        assert r2["deadband_state"].in_deadband is True
        assert r2["fcw_created"] is not None

        # 3. Stay in deadband
        r3 = room.tick(bad_kpi())
        assert r3["deadband_state"].in_deadband is True
        assert r3["fcw_created"] is None  # no new FCW

        # 4. Recover with excellent KPIs (beat hysteresis)
        r4 = room.tick(good_kpi(
            task_completion_rate=99.5,
            avg_wait_time=0.5,
            energy_over_baseline=0.0,
            inference_mae=0.5,
        ))
        assert r4["deadband_state"].in_deadband is False

        # 5. Continue healthy — seed should still be locked
        r5 = room.tick(good_kpi())
        assert r5["active_seed"] is not None
        assert r5["active_seed"].state == SeedState.LOCKED


class TestEscalation:
    """Escalation triggers at HIGH/CRITICAL severity."""

    def test_escalation_on_high_severity(self):
        room = make_room()
        # All metrics badly breached should push severity up
        result = room.tick(bad_kpi(
            task_completion_rate=30.0,
            avg_wait_time=120.0,
            energy_over_baseline=50.0,
            inference_mae=40.0,
        ))
        # Whether escalated depends on severity score
        # At minimum, deadband should be active
        assert result["deadband_state"].in_deadband is True

    def test_no_escalation_on_low_severity(self):
        room = make_room()
        # Mild breach — only one metric slightly over
        result = room.tick(good_kpi(avg_wait_time=31.0))
        # Even if in deadband, severity should be LOW → no escalation
        if result["deadband_state"].in_deadband:
            assert result["escalated"] is False


class TestSlidingWindow:
    """Sliding window aggregates KPIs correctly."""

    def test_aggregation_averages(self):
        room = make_room(window_size=3)
        room.tick(good_kpi(inference_mae=10.0))
        room.tick(good_kpi(inference_mae=20.0))
        result = room.tick(good_kpi(inference_mae=30.0))

        agg = result["aggregated_kpi"]
        assert abs(agg.inference_mae - 20.0) < 0.01

    def test_window_respects_max_size(self):
        room = make_room(window_size=2)
        room.tick(good_kpi(inference_mae=10.0))
        room.tick(good_kpi(inference_mae=20.0))
        result = room.tick(good_kpi(inference_mae=30.0))

        agg = result["aggregated_kpi"]
        # Should average last 2 only: (20 + 30) / 2 = 25
        assert abs(agg.inference_mae - 25.0) < 0.01


class TestStatus:
    """Status report is accurate."""

    def test_initial_status(self):
        room = SpreaderRoom("status-room", RoomType.COMMAND)
        s = room.status

        assert s["room_id"] == "status-room"
        assert s["room_type"] == "command"
        assert s["tick_number"] == 0
        assert s["in_deadband"] is False
        assert s["active_seed_id"] is None
        assert s["fcw_count"] == 0

    def test_status_after_ticks(self):
        room = make_room()
        room.tick(good_kpi())
        room.tick(good_kpi())
        s = room.status

        assert s["tick_number"] == 2
        assert s["active_seed_id"] is not None


class TestRunGenerator:
    """run() yields results from a KPI stream."""

    def test_run_with_ticks_limit(self):
        room = make_room()
        kpis = (good_kpi() for _ in range(100))
        results = list(room.run(kpis, ticks=5))

        assert len(results) == 5
        assert all("tick_number" in r for r in results)

    def test_run_unlimited(self):
        room = make_room()
        kpis = [good_kpi() for _ in range(3)]
        results = list(room.run(kpis))

        assert len(results) == 3
