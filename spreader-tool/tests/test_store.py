"""Tests for spreader.store — content-addressed storage."""

import os
import pytest

from spreader.store import SpreaderStore
from spreader.types import (
    FCWStatus,
    FrozenContextWindow,
    KPIMetrics,
    RoomType,
    Seed,
    SeedState,
    TriggerType,
    make_fcw,
    make_seed,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture
def store(tmp_path):
    """Fresh store in a temp directory, cleaned up after test."""
    s = SpreaderStore(base_dir=str(tmp_path / ".spreader_store"))
    yield s
    s.destroy()


def _kpi(**overrides):
    defaults = dict(
        task_completion_rate=95.0,
        avg_wait_time=5.0,
        energy_over_baseline=2.0,
        inference_mae=3.0,
    )
    defaults.update(overrides)
    return KPIMetrics(**defaults)


# ── Content hash ─────────────────────────────────────────────────────────────

class TestContentHash:
    def test_deterministic(self):
        data = b"hello spreader"
        h1 = SpreaderStore.content_hash(data)
        h2 = SpreaderStore.content_hash(data)
        assert h1 == h2

    def test_different_data_different_hash(self):
        h1 = SpreaderStore.content_hash(b"aaa")
        h2 = SpreaderStore.content_hash(b"bbb")
        assert h1 != h2

    def test_sha256_length(self):
        h = SpreaderStore.content_hash(b"x")
        assert len(h) == 64  # SHA-256 hex


# ── Put and retrieve FCW ────────────────────────────────────────────────────

class TestFCWStorage:
    def test_put_and_get(self, store):
        fcw = make_fcw("room-1", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        h = store.put(fcw)
        retrieved = store.get(h)
        assert retrieved is not None
        assert isinstance(retrieved, FrozenContextWindow)
        assert retrieved.fcw_id == fcw.fcw_id
        assert retrieved.room_id == "room-1"
        assert retrieved.status == FCWStatus.STAGING
        assert retrieved.kpi_snapshot.task_completion_rate == 95.0

    def test_roundtrip_preserves_enums(self, store):
        fcw = make_fcw("room-2", RoomType.COMMAND, _kpi(), TriggerType.THRESHOLD)
        h = store.put(fcw)
        got = store.get(h)
        assert got.room_type == RoomType.COMMAND
        assert got.trigger == TriggerType.THRESHOLD

    def test_roundtrip_with_extensions(self, store):
        fcw = make_fcw("r", RoomType.SENSOR, _kpi(), TriggerType.MANUAL, custom="value", count=42)
        h = store.put(fcw)
        got = store.get(h)
        assert got.extensions["custom"] == "value"
        assert got.extensions["count"] == 42

    def test_same_content_same_hash(self, store):
        fcw = make_fcw("room-1", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        h1 = store.put(fcw)
        # Same object produces same hash (content-addressed)
        h2 = store.put(fcw)
        assert h1 == h2


# ── Put and retrieve Seed ────────────────────────────────────────────────────

class TestSeedStorage:
    def test_put_and_get(self, store):
        seed = make_seed("room-1", "drift-detect")
        h = store.put(seed)
        retrieved = store.get(h)
        assert retrieved is not None
        assert isinstance(retrieved, Seed)
        assert retrieved.seed_id == seed.seed_id
        assert retrieved.role_name == "drift-detect"
        assert retrieved.state == SeedState.UNLOCKED

    def test_roundtrip_locked_seed(self, store):
        seed = make_seed("r", "role")
        seed = seed.transition_to(SeedState.CANDIDATE)
        seed = seed.transition_to(SeedState.VALIDATING)
        seed = seed.transition_to(SeedState.LOCK_PENDING)
        seed = seed.transition_to(SeedState.LOCKED)
        h = store.put(seed)
        got = store.get(h)
        assert got.state == SeedState.LOCKED
        assert got.locked_at is not None


# ── List with filters ───────────────────────────────────────────────────────

class TestListFilters:
    def test_list_fcws_all(self, store):
        fcw1 = make_fcw("r1", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        fcw2 = make_fcw("r2", RoomType.COMMAND, _kpi(), TriggerType.MANUAL)
        store.put(fcw1)
        store.put(fcw2)
        assert len(store.list_fcws()) == 2

    def test_list_fcws_by_room(self, store):
        fcw1 = make_fcw("r1", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        fcw2 = make_fcw("r2", RoomType.COMMAND, _kpi(), TriggerType.MANUAL)
        store.put(fcw1)
        store.put(fcw2)
        assert len(store.list_fcws(room_id="r1")) == 1
        assert store.list_fcws(room_id="r1")[0].room_id == "r1"

    def test_list_fcws_by_status(self, store):
        fcw = make_fcw("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        frozen = fcw.transition_to(FCWStatus.FROZEN)
        store.put(fcw)  # STAGING
        store.put(frozen)  # FROZEN
        assert len(store.list_fcws(status=FCWStatus.FROZEN)) == 1

    def test_list_seeds_all(self, store):
        s1 = make_seed("r1", "role-a")
        s2 = make_seed("r2", "role-b")
        store.put(s1)
        store.put(s2)
        assert len(store.list_seeds()) == 2

    def test_list_seeds_by_state(self, store):
        s1 = make_seed("r", "role")
        s2 = s1.transition_to(SeedState.CANDIDATE)
        # Give different seed_id so both stored
        s2_unlocked = make_seed("r", "role")
        store.put(s1)           # UNLOCKED
        store.put(s2_unlocked)  # UNLOCKED
        assert len(store.list_seeds(state=SeedState.UNLOCKED)) == 2

    def test_list_seeds_by_room(self, store):
        s1 = make_seed("room-a", "role")
        s2 = make_seed("room-b", "role")
        store.put(s1)
        store.put(s2)
        results = store.list_seeds(room_id="room-a")
        assert len(results) == 1
        assert results[0].room_id == "room-a"


# ── Delete ───────────────────────────────────────────────────────────────────

class TestDelete:
    def test_delete_removes_file(self, store):
        fcw = make_fcw("r", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        h = store.put(fcw)
        assert store.get(h) is not None
        assert store.delete(h) is True
        assert store.get(h) is None

    def test_delete_nonexistent_returns_false(self, store):
        assert store.delete("deadbeef" * 8) is False

    def test_delete_cleans_index(self, store):
        fcw = make_fcw("room-x", RoomType.SENSOR, _kpi(), TriggerType.TIME)
        h = store.put(fcw)
        store.delete(h)
        assert store.list_fcws(room_id="room-x") == []


# ── Missing item ─────────────────────────────────────────────────────────────

class TestMissing:
    def test_get_missing_returns_none(self, store):
        assert store.get("0" * 64) is None
