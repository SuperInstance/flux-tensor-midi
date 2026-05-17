"""Tests for FCWManager — frozen_context.py."""

import time

import pytest

from spreader.frozen_context import FCWManager
from spreader.types import (
    FCWStatus,
    FrozenContextWindow,
    KPIMetrics,
    RoomType,
    TriggerType,
)


# ── Helpers ────────────────────────────────────────────────────────────────

def _kpi(**overrides) -> KPIMetrics:
    defaults = dict(
        task_completion_rate=85.0,
        avg_wait_time=20.0,
        energy_over_baseline=5.0,
        inference_mae=8.0,
    )
    defaults.update(overrides)
    return KPIMetrics(**defaults)


# ── Create & Freeze ────────────────────────────────────────────────────────

class TestCreateAndFreeze:
    def test_create_returns_staging(self):
        mgr = FCWManager()
        fcw = mgr.create("room-1", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        assert fcw.status == FCWStatus.STAGING
        assert fcw.room_id == "room-1"
        assert fcw.room_type == RoomType.SENSOR
        assert fcw.trigger == TriggerType.TIME
        assert fcw.kpi_snapshot.task_completion_rate == 85.0

    def test_freeze_advances_staging_to_frozen(self):
        mgr = FCWManager()
        fcw = mgr.create("room-1", RoomType.SENSOR, _kpi(), TriggerType.THRESHOLD)
        frozen = mgr.freeze(fcw.fcw_id)
        assert frozen.status == FCWStatus.FROZEN
        assert frozen.fcw_id == fcw.fcw_id
        assert frozen._transition_guard == 1

    def test_create_stores_in_manager(self):
        mgr = FCWManager()
        fcw = mgr.create("room-1", RoomType.COMMAND, _kpi(), TriggerType.MANUAL)
        assert mgr.get(fcw.fcw_id) is fcw

    def test_create_with_extensions(self):
        mgr = FCWManager()
        fcw = mgr.create(
            "room-1", RoomType.SIMULATION, _kpi(), TriggerType.CONTEXT_SHIFT,
            note="test note",
        )
        assert fcw.extensions["note"] == "test note"


# ── Full Lifecycle ─────────────────────────────────────────────────────────

class TestLifecycle:
    def test_full_lifecycle_staging_to_locked(self):
        mgr = FCWManager()
        fcw = mgr.create("room-1", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        assert fcw.status == FCWStatus.STAGING

        fcw = mgr.advance(fcw.fcw_id, FCWStatus.FROZEN)
        assert fcw.status == FCWStatus.FROZEN

        fcw = mgr.advance(fcw.fcw_id, FCWStatus.TESTING)
        assert fcw.status == FCWStatus.TESTING

        fcw = mgr.advance(fcw.fcw_id, FCWStatus.REFINING)
        assert fcw.status == FCWStatus.REFINING

        fcw = mgr.advance(fcw.fcw_id, FCWStatus.LOCKED)
        assert fcw.status == FCWStatus.LOCKED
        assert fcw._transition_guard == 4

    def test_refining_can_go_back_to_testing(self):
        mgr = FCWManager()
        fcw = mgr.create("r", RoomType.COLLAB_ANALYSIS, _kpi(), TriggerType.THRESHOLD)
        fcw = mgr.advance(fcw.fcw_id, FCWStatus.FROZEN)
        fcw = mgr.advance(fcw.fcw_id, FCWStatus.TESTING)
        fcw = mgr.advance(fcw.fcw_id, FCWStatus.REFINING)
        fcw = mgr.advance(fcw.fcw_id, FCWStatus.TESTING)
        assert fcw.status == FCWStatus.TESTING

    def test_testing_can_return_to_frozen(self):
        mgr = FCWManager()
        fcw = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        fcw = mgr.advance(fcw.fcw_id, FCWStatus.FROZEN)
        fcw = mgr.advance(fcw.fcw_id, FCWStatus.TESTING)
        fcw = mgr.advance(fcw.fcw_id, FCWStatus.FROZEN)
        assert fcw.status == FCWStatus.FROZEN


# ── Invalid Transitions ────────────────────────────────────────────────────

class TestInvalidTransitions:
    @pytest.mark.parametrize("from_status,to_status", [
        (FCWStatus.STAGING, FCWStatus.TESTING),
        (FCWStatus.STAGING, FCWStatus.LOCKED),
        (FCWStatus.FROZEN, FCWStatus.STAGING),
        (FCWStatus.FROZEN, FCWStatus.LOCKED),
        (FCWStatus.LOCKED, FCWStatus.STAGING),
        (FCWStatus.LOCKED, FCWStatus.DISCARDED),
        (FCWStatus.DISCARDED, FCWStatus.STAGING),
        (FCWStatus.DISCARDED, FCWStatus.FROZEN),
    ])
    def test_invalid_transition_raises(self, from_status, to_status):
        mgr = FCWManager()
        fcw = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)

        # Walk to the desired from_status
        path = {
            FCWStatus.STAGING: [],
            FCWStatus.FROZEN: [FCWStatus.FROZEN],
            FCWStatus.TESTING: [FCWStatus.FROZEN, FCWStatus.TESTING],
            FCWStatus.REFINING: [FCWStatus.FROZEN, FCWStatus.TESTING, FCWStatus.REFINING],
            FCWStatus.LOCKED: [FCWStatus.FROZEN, FCWStatus.TESTING, FCWStatus.REFINING, FCWStatus.LOCKED],
            FCWStatus.DISCARDED: [FCWStatus.DISCARDED],
        }
        for step in path[from_status]:
            fcw = mgr.advance(fcw.fcw_id, step)

        with pytest.raises(ValueError, match="Invalid FCW transition"):
            mgr.advance(fcw.fcw_id, to_status)

    def test_advance_nonexistent_raises_keyerror(self):
        mgr = FCWManager()
        with pytest.raises(KeyError):
            mgr.advance("no-such-id", FCWStatus.FROZEN)


# ── Content Hashing & Dedup ────────────────────────────────────────────────

class TestContentHashing:
    def test_same_inputs_same_hash(self):
        mgr = FCWManager()
        kpi = _kpi()
        a = mgr.create("room-1", RoomType.SENSOR, kpi, TriggerType.TIME)
        b = mgr.create("room-1", RoomType.SENSOR, kpi, TriggerType.TIME)
        assert mgr.content_hash(a) == mgr.content_hash(b)

    def test_different_kpi_different_hash(self):
        mgr = FCWManager()
        a = mgr.create("room-1", RoomType.SENSOR, _kpi(task_completion_rate=80.0), TriggerType.TIME)
        b = mgr.create("room-1", RoomType.SENSOR, _kpi(task_completion_rate=90.0), TriggerType.TIME)
        assert mgr.content_hash(a) != mgr.content_hash(b)

    def test_different_trigger_different_hash(self):
        mgr = FCWManager()
        kpi = _kpi()
        a = mgr.create("r", RoomType.SENSOR, kpi, TriggerType.TIME)
        b = mgr.create("r", RoomType.SENSOR, kpi, TriggerType.THRESHOLD)
        assert mgr.content_hash(a) != mgr.content_hash(b)

    def test_find_by_content_hash(self):
        mgr = FCWManager()
        kpi = _kpi()
        a = mgr.create("r", RoomType.SENSOR, kpi, TriggerType.TIME)
        mgr.create("r", RoomType.SENSOR, _kpi(task_completion_rate=99.0), TriggerType.TIME)
        c = mgr.create("r", RoomType.SENSOR, kpi, TriggerType.TIME)

        matches = mgr.find_by_content_hash(mgr.content_hash(a))
        ids = {f.fcw_id for f in matches}
        assert ids == {a.fcw_id, c.fcw_id}


# ── Queries ────────────────────────────────────────────────────────────────

class TestQueries:
    def test_query_by_room(self):
        mgr = FCWManager()
        a = mgr.create("room-a", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        mgr.create("room-b", RoomType.COMMAND, _kpi(), TriggerType.TIME)
        c = mgr.create("room-a", RoomType.SENSOR, _kpi(), TriggerType.THRESHOLD)

        results = mgr.query(room_id="room-a")
        ids = {f.fcw_id for f in results}
        assert ids == {a.fcw_id, c.fcw_id}

    def test_query_by_status(self):
        mgr = FCWManager()
        a = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        b = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        mgr.freeze(b.fcw_id)

        frozen = mgr.query(status=FCWStatus.FROZEN)
        assert len(frozen) == 1
        assert frozen[0].fcw_id == b.fcw_id

    def test_query_combined_room_and_status(self):
        mgr = FCWManager()
        mgr.create("room-a", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        b = mgr.create("room-b", RoomType.COMMAND, _kpi(), TriggerType.TIME)
        mgr.freeze(b.fcw_id)

        results = mgr.query(room_id="room-b", status=FCWStatus.FROZEN)
        assert len(results) == 1

    def test_query_time_range(self):
        mgr = FCWManager()
        now = time.time()

        # frozen_at is set by make_fcw to time.time(), so we use real time
        a = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        # Simulate a later FCW by monkey-patching frozen_at via a second create
        b = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)

        # Both have frozen_at ≈ now, so since=now-10 should return both
        results = mgr.query(since=now - 10.0)
        assert len(results) == 2

        # until in the past returns nothing
        results = mgr.query(until=now - 10.0)
        assert len(results) == 0

        # since in the future returns nothing
        results = mgr.query(since=now + 100.0)
        assert len(results) == 0

    def test_query_empty(self):
        mgr = FCWManager()
        assert mgr.query() == []

    def test_active_for_room_excludes_terminal(self):
        mgr = FCWManager()
        a = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        b = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.THRESHOLD)
        mgr.freeze(b.fcw_id)

        # Lock a via full lifecycle
        mgr.advance(a.fcw_id, FCWStatus.FROZEN)
        mgr.advance(a.fcw_id, FCWStatus.TESTING)
        mgr.advance(a.fcw_id, FCWStatus.REFINING)
        mgr.advance(a.fcw_id, FCWStatus.LOCKED)

        active = mgr.active_for_room("r")
        ids = {f.fcw_id for f in active}
        assert b.fcw_id in ids
        assert a.fcw_id not in ids  # LOCKED is terminal


# ── Discard ────────────────────────────────────────────────────────────────

class TestDiscard:
    def test_discard_from_staging(self):
        mgr = FCWManager()
        fcw = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        discarded = mgr.discard(fcw.fcw_id)
        assert discarded.status == FCWStatus.DISCARDED

    def test_discard_from_frozen(self):
        mgr = FCWManager()
        fcw = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        mgr.freeze(fcw.fcw_id)
        discarded = mgr.discard(fcw.fcw_id)
        assert discarded.status == FCWStatus.DISCARDED

    def test_discard_from_testing(self):
        mgr = FCWManager()
        fcw = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        fcw = mgr.freeze(fcw.fcw_id)
        mgr.advance(fcw.fcw_id, FCWStatus.TESTING)
        discarded = mgr.discard(fcw.fcw_id)
        assert discarded.status == FCWStatus.DISCARDED

    def test_discard_from_refining(self):
        mgr = FCWManager()
        fcw = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        fcw = mgr.freeze(fcw.fcw_id)
        fcw = mgr.advance(fcw.fcw_id, FCWStatus.TESTING)
        mgr.advance(fcw.fcw_id, FCWStatus.REFINING)
        discarded = mgr.discard(fcw.fcw_id)
        assert discarded.status == FCWStatus.DISCARDED

    def test_discard_from_locked_raises(self):
        mgr = FCWManager()
        fcw = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        fcw = mgr.freeze(fcw.fcw_id)
        fcw = mgr.advance(fcw.fcw_id, FCWStatus.TESTING)
        fcw = mgr.advance(fcw.fcw_id, FCWStatus.REFINING)
        mgr.advance(fcw.fcw_id, FCWStatus.LOCKED)
        with pytest.raises(ValueError):
            mgr.discard(fcw.fcw_id)


# ── Statistics ─────────────────────────────────────────────────────────────

class TestStatistics:
    def test_count(self):
        mgr = FCWManager()
        assert mgr.count() == 0
        mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        assert mgr.count() == 1
        mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.THRESHOLD)
        assert mgr.count() == 2

    def test_count_by_status(self):
        mgr = FCWManager()
        a = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        b = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.THRESHOLD)
        mgr.freeze(b.fcw_id)

        counts = mgr.count_by_status()
        assert counts[FCWStatus.STAGING] == 1
        assert counts[FCWStatus.FROZEN] == 1


# ── Get ────────────────────────────────────────────────────────────────────

class TestGet:
    def test_get_returns_none_for_unknown(self):
        mgr = FCWManager()
        assert mgr.get("nope") is None

    def test_get_returns_latest_version(self):
        mgr = FCWManager()
        fcw = mgr.create("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        mgr.freeze(fcw.fcw_id)
        latest = mgr.get(fcw.fcw_id)
        assert latest.status == FCWStatus.FROZEN
