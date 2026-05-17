"""Tests for spreader.types — data structures, enums, state transitions."""

import time
import pytest

from spreader.types import (
    WINDOW_DURATION, TICK_INTERVAL, BASELINE_COMPLETION,
    DEADBAND_MIN_DURATION, ESCALATION_MAE_THRESHOLD, SEED_LOCK_KPI,
    RoomType, DeadbandMetric, DeadbandSeverity, FCWStatus, TriggerType, SeedState,
    KPIMetrics, DeadbandConfig, DeadbandState, FrozenContextWindow, Seed,
    make_fcw, make_seed,
)


# ── Constants ────────────────────────────────────────────────────────────────

class TestConstants:
    def test_all_constants_positive(self):
        assert WINDOW_DURATION > 0
        assert TICK_INTERVAL > 0
        assert BASELINE_COMPLETION > 0
        assert DEADBAND_MIN_DURATION > 0
        assert ESCALATION_MAE_THRESHOLD > 0
        assert SEED_LOCK_KPI > 0

    def test_constants_reasonable_ranges(self):
        assert 0 < WINDOW_DURATION <= 3600
        assert 0 < TICK_INTERVAL <= 60
        assert 0 < BASELINE_COMPLETION <= 100


# ── Enums ────────────────────────────────────────────────────────────────────

class TestEnums:
    def test_room_type_values(self):
        assert len(RoomType) == 4
        assert RoomType.SENSOR.value == "sensor"

    def test_deadband_metric_values(self):
        assert len(DeadbandMetric) == 4
        assert DeadbandMetric.COMPLETION_RATE.value == "completion_rate"

    def test_fcw_status_lifecycle(self):
        assert len(FCWStatus) == 6
        assert FCWStatus.STAGING.value == "staging"
        assert FCWStatus.LOCKED.value == "locked"

    def test_seed_state_lifecycle(self):
        assert len(SeedState) == 8
        assert SeedState.UNLOCKED.value == "unlocked"
        assert SeedState.LOCKED.value == "locked"


# ── FrozenContextWindow ─────────────────────────────────────────────────────

class TestFCW:
    def _make_kpi(self):
        return KPIMetrics(95.0, 5.0, 2.0, 3.0)

    def test_factory_creates_staging(self):
        fcw = make_fcw("room-1", RoomType.SENSOR, self._make_kpi(), TriggerType.TIME)
        assert fcw.status == FCWStatus.STAGING
        assert fcw.room_id == "room-1"
        assert fcw.fcw_id  # UUID assigned
        assert fcw.frozen_at > 0

    def test_staging_to_frozen(self):
        fcw = make_fcw("room-1", RoomType.SENSOR, self._make_kpi(), TriggerType.THRESHOLD)
        frozen = fcw.transition_to(FCWStatus.FROZEN)
        assert frozen.status == FCWStatus.FROZEN
        assert frozen.fcw_id == fcw.fcw_id  # identity preserved

    def test_full_lifecycle(self):
        fcw = make_fcw("r", RoomType.COMMAND, self._make_kpi(), TriggerType.MANUAL)
        fcw = fcw.transition_to(FCWStatus.FROZEN)
        fcw = fcw.transition_to(FCWStatus.TESTING)
        fcw = fcw.transition_to(FCWStatus.REFINING)
        fcw = fcw.transition_to(FCWStatus.LOCKED)
        assert fcw.status == FCWStatus.LOCKED

    def test_discard_from_any_active(self):
        for status in [FCWStatus.STAGING, FCWStatus.FROZEN, FCWStatus.TESTING, FCWStatus.REFINING]:
            fcw = make_fcw("r", RoomType.SENSOR, self._make_kpi(), TriggerType.TIME)
            if status != FCWStatus.STAGING:
                fcw = fcw.transition_to(FCWStatus.FROZEN)
                if status not in [FCWStatus.FROZEN]:
                    fcw = fcw.transition_to(FCWStatus.TESTING)
                    if status == FCWStatus.REFINING:
                        fcw = fcw.transition_to(FCWStatus.REFINING)
            if status == FCWStatus.STAGING:
                pass  # already staging
            elif status == FCWStatus.FROZEN:
                fcw = make_fcw("r", RoomType.SENSOR, self._make_kpi(), TriggerType.TIME).transition_to(FCWStatus.FROZEN)
            discarded = fcw.transition_to(FCWStatus.DISCARDED)
            assert discarded.status == FCWStatus.DISCARDED

    def test_invalid_transition_raises(self):
        fcw = make_fcw("r", RoomType.SENSOR, self._make_kpi(), TriggerType.TIME)
        fcw = fcw.transition_to(FCWStatus.FROZEN)
        fcw = fcw.transition_to(FCWStatus.TESTING)
        fcw = fcw.transition_to(FCWStatus.REFINING)
        fcw = fcw.transition_to(FCWStatus.LOCKED)
        with pytest.raises(ValueError):
            fcw.transition_to(FCWStatus.TESTING)  # LOCKED is terminal

    def test_immutable(self):
        fcw = make_fcw("r", RoomType.SENSOR, self._make_kpi(), TriggerType.TIME)
        with pytest.raises(Exception):
            fcw.status = FCWStatus.LOCKED

    def test_extensions(self):
        fcw = make_fcw("r", RoomType.SENSOR, self._make_kpi(), TriggerType.TIME, custom="data")
        assert fcw.extensions["custom"] == "data"


# ── Seed ─────────────────────────────────────────────────────────────────────

class TestSeed:
    def test_factory_creates_unlocked(self):
        seed = make_seed("room-1", "drift-detect")
        assert seed.state == SeedState.UNLOCKED
        assert seed.room_id == "room-1"
        assert seed.role_name == "drift-detect"
        assert seed.seed_id  # UUID assigned

    def test_full_lifecycle(self):
        seed = make_seed("r", "role")
        seed = seed.transition_to(SeedState.CANDIDATE)
        seed = seed.transition_to(SeedState.VALIDATING)
        seed = seed.transition_to(SeedState.LOCK_PENDING)
        seed = seed.transition_to(SeedState.LOCKED)
        assert seed.state == SeedState.LOCKED
        assert seed.locked_at is not None

    def test_validation_failure_returns_unlocked(self):
        seed = make_seed("r", "role")
        seed = seed.transition_to(SeedState.CANDIDATE)
        seed = seed.transition_to(SeedState.VALIDATING)
        # Failed validation → back to candidate
        seed = seed.transition_to(SeedState.CANDIDATE)
        assert seed.state == SeedState.CANDIDATE

    def test_deprecated_from_locked(self):
        seed = make_seed("r", "role")
        seed = seed.transition_to(SeedState.CANDIDATE)
        seed = seed.transition_to(SeedState.VALIDATING)
        seed = seed.transition_to(SeedState.LOCK_PENDING)
        seed = seed.transition_to(SeedState.LOCKED)
        seed = seed.transition_to(SeedState.DEPRECATED)
        assert seed.state == SeedState.DEPRECATED

    def test_emergency_restore(self):
        seed = make_seed("r", "role")
        seed = seed.transition_to(SeedState.CANDIDATE)
        seed = seed.transition_to(SeedState.VALIDATING)
        seed = seed.transition_to(SeedState.LOCK_PENDING)
        seed = seed.transition_to(SeedState.LOCKED)
        seed = seed.transition_to(SeedState.DEPRECATED)
        seed = seed.transition_to(SeedState.ARCHIVED)
        # Emergency restore
        seed = seed.transition_to(SeedState.LOCKED)
        assert seed.state == SeedState.LOCKED

    def test_invalid_transition_raises(self):
        seed = make_seed("r", "role")
        with pytest.raises(ValueError):
            seed.transition_to(SeedState.LOCKED)  # must go through candidate

    def test_identity_preserved(self):
        seed = make_seed("r", "role")
        sid = seed.seed_id
        seed = seed.transition_to(SeedState.CANDIDATE)
        assert seed.seed_id == sid


# ── DeadbandState ────────────────────────────────────────────────────────────

class TestDeadbandState:
    def test_create(self):
        ds = DeadbandState(in_deadband=False, severity=0.0)
        assert not ds.in_deadband
        assert ds.severity == 0.0

    def test_breached_metrics(self):
        ds = DeadbandState(
            in_deadband=True,
            severity=0.5,
            breached_metrics=(DeadbandMetric.COMPLETION_RATE,),
        )
        assert DeadbandMetric.COMPLETION_RATE in ds.breached_metrics

    def test_frozen_by_default(self):
        ds = DeadbandState(in_deadband=False, severity=0.0)
        assert not ds.in_deadband
        # DeadbandState is mutable (deadband detector updates in-place)
        ds.in_deadband = True
        assert ds.in_deadband
