"""Tests for spreader.types — data structures, enums, state transitions."""

import uuid
from datetime import datetime, timezone

import pytest

from spreader.types import (
    BASELINE_COMPLETION,
    DEADBAND_MIN_DURATION,
    ESCALATION_MAE_THRESHOLD,
    FCWStatus,
    FrozenContextWindow,
    RoomType,
    SEED_LOCK_KPI,
    Seed,
    SeedState,
    TICK_INTERVAL,
    WINDOW_DURATION,
    DeadbandMetric,
    DeadbandState,
    make_fcw,
    make_seed,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

class TestConstants:
    def test_window_duration(self):
        assert WINDOW_DURATION == 60.0

    def test_tick_interval(self):
        assert TICK_INTERVAL == 10.0

    def test_baseline_completion(self):
        assert BASELINE_COMPLETION == 90.0

    def test_deadband_min_duration(self):
        assert DEADBAND_MIN_DURATION == 300.0

    def test_escalation_mae_threshold(self):
        assert ESCALATION_MAE_THRESHOLD == 10.0

    def test_seed_lock_kpi(self):
        assert SEED_LOCK_KPI == 95.0


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestEnums:
    def test_room_type_values(self):
        assert {r.value for r in RoomType} == {
            "sensor", "collab_analysis", "command", "simulation"
        }

    def test_fcw_status_values(self):
        assert {s.value for s in FCWStatus} == {
            "staging", "frozen", "testing", "refining", "locked", "discarded"
        }

    def test_seed_state_values(self):
        assert {s.value for s in SeedState} == {
            "unlocked", "candidate", "validating", "lock_pending",
            "locked", "escalating", "deprecated", "archived"
        }

    def test_deadband_metric_values(self):
        assert {m.value for m in DeadbandMetric} == {
            "task_completion", "avg_wait_time", "energy_overage", "inference_mae"
        }


# ---------------------------------------------------------------------------
# FrozenContextWindow
# ---------------------------------------------------------------------------

class TestFrozenContextWindow:
    def test_create_with_factory(self):
        fcw = make_fcw(
            room_id="room-1",
            room_type=RoomType.SENSOR,
            task_completion_rate=95.0,
        )
        assert fcw.room_id == "room-1"
        assert fcw.room_type == RoomType.SENSOR
        assert fcw.status == FCWStatus.STAGING
        assert fcw.task_completion_rate == 95.0
        assert isinstance(fcw.fcw_id, uuid.UUID)
        assert isinstance(fcw.frozen_at, datetime)

    def test_create_directly(self):
        now = datetime.now(timezone.utc)
        fcw = FrozenContextWindow(
            fcw_id=uuid.uuid4(),
            frozen_at=now,
            room_id="room-2",
            room_type=RoomType.COMMAND,
            status=FCWStatus.FROZEN,
            avg_inference_mae=3.5,
            safety_compliance_score=0.98,
            safety_violations=0,
            peer_sync_count=5,
            peer_agreement_ratio=0.95,
            global_confidence_score=0.88,
        )
        assert fcw.status == FCWStatus.FROZEN
        assert fcw.avg_inference_mae == 3.5
        assert fcw.safety_violations == 0

    def test_immutable(self):
        fcw = make_fcw(room_id="room-3", room_type=RoomType.SIMULATION)
        with pytest.raises(AttributeError):
            fcw.status = FCWStatus.FROZEN  # type: ignore[misc]

    def test_valid_transition_staging_to_frozen(self):
        fcw = make_fcw(room_id="room-4", room_type=RoomType.SENSOR)
        frozen = fcw.transition_to(FCWStatus.FROZEN)
        assert frozen.status == FCWStatus.FROZEN
        assert frozen.fcw_id == fcw.fcw_id  # identity preserved

    def test_full_lifecycle(self):
        fcw = make_fcw(room_id="room-5", room_type=RoomType.SENSOR)
        fcw = fcw.transition_to(FCWStatus.FROZEN)
        fcw = fcw.transition_to(FCWStatus.TESTING)
        fcw = fcw.transition_to(FCWStatus.REFINING)
        fcw = fcw.transition_to(FCWStatus.LOCKED)
        assert fcw.status == FCWStatus.LOCKED

    def test_discard_from_any_active_state(self):
        for status in [FCWStatus.STAGING, FCWStatus.FROZEN, FCWStatus.TESTING, FCWStatus.REFINING]:
            fcw = make_fcw(room_id="room-d", room_type=RoomType.SENSOR, status=status)
            discarded = fcw.transition_to(FCWStatus.DISCARDED)
            assert discarded.status == FCWStatus.DISCARDED

    def test_invalid_transition_locked_to_testing(self):
        fcw = make_fcw(room_id="room-6", room_type=RoomType.SENSOR, status=FCWStatus.LOCKED)
        assert not fcw.can_transition_to(FCWStatus.TESTING)
        with pytest.raises(ValueError, match="Invalid FCW transition"):
            fcw.transition_to(FCWStatus.TESTING)

    def test_invalid_transition_discarded_to_anything(self):
        fcw = make_fcw(room_id="room-7", room_type=RoomType.SENSOR, status=FCWStatus.DISCARDED)
        assert not fcw.can_transition_to(FCWStatus.STAGING)
        with pytest.raises(ValueError):
            fcw.transition_to(FCWStatus.STAGING)

    def test_extensions_default_empty(self):
        fcw = make_fcw(room_id="room-8", room_type=RoomType.SENSOR)
        assert fcw.extensions == {}

    def test_extensions_preserved(self):
        fcw = make_fcw(
            room_id="room-9",
            room_type=RoomType.SENSOR,
            extensions={"custom_key": "custom_value"},
        )
        assert fcw.extensions["custom_key"] == "custom_value"

    def test_all_kpi_fields_default(self):
        fcw = make_fcw(room_id="room-10", room_type=RoomType.SENSOR)
        assert fcw.task_completion_rate == 0.0
        assert fcw.avg_wait_time == 0.0
        assert fcw.energy_overage_pct == 0.0
        assert fcw.avg_inference_mae == 0.0
        assert fcw.linked_seed_id is None


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

class TestSeed:
    def test_create_with_factory(self):
        seed = make_seed(room_id="room-1", role_name="drift-detect")
        assert seed.room_id == "room-1"
        assert seed.role_name == "drift-detect"
        assert seed.state == SeedState.UNLOCKED
        assert isinstance(seed.seed_id, uuid.UUID)
        assert isinstance(seed.lineage_id, uuid.UUID)
        assert isinstance(seed.created_at, datetime)

    def test_create_directly(self):
        sid = uuid.uuid4()
        lid = uuid.uuid4()
        seed = Seed(
            seed_id=sid,
            room_id="room-2",
            role_name="anomaly-flag",
            lineage_id=lid,
            version_major=2,
            version_minor=1,
            micro_model_weights_ref="store://weights/abc123",
            context_window_ids=(uuid.uuid4(), uuid.uuid4()),
            locked_kpi_metrics={"completion": 97.5},
        )
        assert seed.version_major == 2
        assert seed.version_minor == 1
        assert len(seed.context_window_ids) == 2

    def test_immutable(self):
        seed = make_seed(room_id="room-3", role_name="intent-detect")
        with pytest.raises(AttributeError):
            seed.state = SeedState.LOCKED  # type: ignore[misc]

    def test_valid_lifecycle_unlocked_to_locked(self):
        seed = make_seed(room_id="room-4", role_name="drift-detect")
        seed = seed.transition_to(SeedState.CANDIDATE)
        assert seed.state == SeedState.CANDIDATE

        seed = seed.transition_to(SeedState.VALIDATING)
        assert seed.state == SeedState.VALIDATING

        seed = seed.transition_to(SeedState.LOCK_PENDING)
        assert seed.state == SeedState.LOCK_PENDING

        seed = seed.transition_to(SeedState.LOCKED)
        assert seed.state == SeedState.LOCKED
        assert seed.locked_at is not None

    def test_validation_failure_returns_unlocked(self):
        seed = make_seed(room_id="room-5", role_name="drift-detect")
        seed = seed.transition_to(SeedState.CANDIDATE)
        seed = seed.transition_to(SeedState.VALIDATING)
        seed = seed.transition_to(SeedState.UNLOCKED)
        assert seed.state == SeedState.UNLOCKED

    def test_escalation_from_locked(self):
        seed = make_seed(room_id="room-6", role_name="drift-detect")
        seed = seed.transition_to(SeedState.CANDIDATE)
        seed = seed.transition_to(SeedState.VALIDATING)
        seed = seed.transition_to(SeedState.LOCK_PENDING)
        seed = seed.transition_to(SeedState.LOCKED)

        seed = seed.transition_to(SeedState.ESCALATING)
        assert seed.state == SeedState.ESCALATING

        # Resolved back to locked
        seed = seed.transition_to(SeedState.LOCKED)
        assert seed.state == SeedState.LOCKED

    def test_deprecated_sets_timestamp(self):
        seed = make_seed(room_id="room-7", role_name="drift-detect")
        seed = seed.transition_to(SeedState.CANDIDATE)
        seed = seed.transition_to(SeedState.VALIDATING)
        seed = seed.transition_to(SeedState.LOCK_PENDING)
        seed = seed.transition_to(SeedState.LOCKED)

        seed = seed.transition_to(SeedState.DEPRECATED)
        assert seed.state == SeedState.DEPRECATED
        assert seed.deprecated_at is not None

    def test_archived_emergency_restore(self):
        seed = make_seed(room_id="room-8", role_name="drift-detect")
        seed = seed.transition_to(SeedState.CANDIDATE)
        seed = seed.transition_to(SeedState.VALIDATING)
        seed = seed.transition_to(SeedState.LOCK_PENDING)
        seed = seed.transition_to(SeedState.LOCKED)
        seed = seed.transition_to(SeedState.DEPRECATED)
        seed = seed.transition_to(SeedState.ARCHIVED)

        # Emergency restore
        seed = seed.transition_to(SeedState.LOCKED)
        assert seed.state == SeedState.LOCKED

    def test_invalid_transition_unlocked_to_locked(self):
        seed = make_seed(room_id="room-9", role_name="drift-detect")
        with pytest.raises(ValueError, match="Invalid Seed transition"):
            seed.transition_to(SeedState.LOCKED)

    def test_identity_preserved_across_transitions(self):
        seed = make_seed(room_id="room-10", role_name="drift-detect")
        original_id = seed.seed_id
        seed = seed.transition_to(SeedState.CANDIDATE)
        assert seed.seed_id == original_id


# ---------------------------------------------------------------------------
# DeadbandState
# ---------------------------------------------------------------------------

class TestDeadbandState:
    def test_default_not_in_deadband(self):
        state = DeadbandState()
        assert not state.in_deadband
        assert state.severity == 0.0
        assert len(state.breached_metrics) == 0

    def test_with_breached_metrics(self):
        state = DeadbandState(
            in_deadband=True,
            severity=0.7,
            breached_metrics=frozenset({DeadbandMetric.TASK_COMPLETION, DeadbandMetric.AVG_WAIT_TIME}),
            duration=450.0,
            entry_timestamp=datetime.now(timezone.utc),
        )
        assert state.in_deadband
        assert DeadbandMetric.TASK_COMPLETION in state.breached_metrics
        assert state.duration == 450.0

    def test_with_metric_value(self):
        state = DeadbandState(in_deadband=True, severity=0.5)
        state = state.with_metric_value(DeadbandMetric.TASK_COMPLETION, 85.0)
        assert state.metric_values["task_completion"] == 85.0

    def test_immutable(self):
        state = DeadbandState()
        with pytest.raises(AttributeError):
            state.in_deadband = True  # type: ignore[misc]

    def test_frozen_set_default_empty(self):
        state = DeadbandState()
        assert state.breached_metrics == frozenset()
