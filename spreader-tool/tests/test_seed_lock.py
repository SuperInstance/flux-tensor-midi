"""Tests for spreader.seed_lock — SeedLockManager MVP."""

import pytest

from spreader.types import KPIMetrics, SEED_LOCK_KPI, SeedState
from spreader.seed_lock import SeedLockManager


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def mgr() -> SeedLockManager:
    return SeedLockManager()


def _kpi(completion: float = 96.0) -> KPIMetrics:
    return KPIMetrics(
        task_completion_rate=completion,
        avg_wait_time=10.0,
        energy_over_baseline=5.0,
        inference_mae=3.0,
    )


def _propose(mgr: SeedLockManager, kpi: KPIMetrics | None = None) -> object:
    """Propose a seed with default good KPIs."""
    from dataclasses import dataclass
    kpi = kpi or _kpi()
    return mgr.propose(
        room_id="room-1",
        role_name="analyst",
        weights_ref="s3://weights/v1.bin",
        fcw_ids=["fcw-a", "fcw-b"],
        kpi=kpi,
    )


# ── Tests ───────────────────────────────────────────────────────────────────

class TestPropose:
    def test_creates_candidate(self, mgr: SeedLockManager):
        seed = _propose(mgr)
        assert seed.state == SeedState.CANDIDATE
        assert seed.room_id == "room-1"
        assert seed.role_name == "analyst"
        assert seed.weights_ref == "s3://weights/v1.bin"
        assert seed.context_window_ids == ("fcw-a", "fcw-b")
        assert seed.locked_kpis is not None


class TestValidate:
    def test_pass_when_kpi_above_threshold(self, mgr: SeedLockManager):
        seed = _propose(mgr, _kpi(completion=96.0))
        result = mgr.validate(seed.seed_id)
        assert result.state == SeedState.LOCK_PENDING

    def test_fail_when_kpi_below_threshold(self, mgr: SeedLockManager):
        seed = _propose(mgr, _kpi(completion=80.0))
        result = mgr.validate(seed.seed_id)
        assert result.state == SeedState.CANDIDATE

    def test_custom_backtest_fn(self, mgr: SeedLockManager):
        seed = _propose(mgr)
        # custom fn that always passes
        result = mgr.validate(seed.seed_id, backtest_fn=lambda s: True)
        assert result.state == SeedState.LOCK_PENDING

    def test_rejects_non_candidate(self, mgr: SeedLockManager):
        seed = _propose(mgr)
        validated = mgr.validate(seed.seed_id)  # → LOCK_PENDING
        with pytest.raises(ValueError, match="CANDIDATE"):
            mgr.validate(validated.seed_id)


class TestLock:
    def test_lock_promotes_to_locked(self, mgr: SeedLockManager):
        seed = _propose(mgr, _kpi(completion=96.0))
        validated = mgr.validate(seed.seed_id)
        assert validated.state == SeedState.LOCK_PENDING
        locked = mgr.lock(validated.seed_id)
        assert locked.state == SeedState.LOCKED
        assert locked.locked_at is not None

    def test_cant_lock_without_validation(self, mgr: SeedLockManager):
        seed = _propose(mgr)
        with pytest.raises(ValueError, match="LOCK_PENDING"):
            mgr.lock(seed.seed_id)


class TestGetActiveSeed:
    def test_returns_locked_seed(self, mgr: SeedLockManager):
        seed = _propose(mgr, _kpi(completion=96.0))
        mgr.validate(seed.seed_id)
        mgr.lock(seed.seed_id)
        active = mgr.get_active_seed("room-1", "analyst")
        assert active is not None
        assert active.seed_id == seed.seed_id
        assert active.state == SeedState.LOCKED

    def test_returns_none_when_no_locked(self, mgr: SeedLockManager):
        assert mgr.get_active_seed("room-1", "analyst") is None

    def test_returns_none_for_wrong_role(self, mgr: SeedLockManager):
        seed = _propose(mgr, _kpi(completion=96.0))
        mgr.validate(seed.seed_id)
        mgr.lock(seed.seed_id)
        assert mgr.get_active_seed("room-1", "other-role") is None


class TestDeprecate:
    def test_deprecate_moves_to_deprecated(self, mgr: SeedLockManager):
        seed = _propose(mgr, _kpi(completion=96.0))
        mgr.validate(seed.seed_id)
        locked = mgr.lock(seed.seed_id)
        deprecated = mgr.deprecate(locked.seed_id)
        assert deprecated.state == SeedState.DEPRECATED

    def test_deprecate_with_replacement(self, mgr: SeedLockManager):
        seed = _propose(mgr, _kpi(completion=96.0))
        mgr.validate(seed.seed_id)
        locked = mgr.lock(seed.seed_id)
        deprecated = mgr.deprecate(locked.seed_id, replacement_id="new-seed-123")
        assert deprecated.extensions["replacement_id"] == "new-seed-123"

    def test_cant_deprecate_non_locked(self, mgr: SeedLockManager):
        seed = _propose(mgr)
        with pytest.raises(ValueError, match="LOCKED"):
            mgr.deprecate(seed.seed_id)


class TestListCandidates:
    def test_lists_candidates(self, mgr: SeedLockManager):
        _propose(mgr, _kpi(completion=96.0))
        _propose(mgr, _kpi(completion=97.0))
        cands = mgr.list_candidates()
        assert len(cands) == 2
        assert all(s.state == SeedState.CANDIDATE for s in cands)

    def test_filter_by_room(self, mgr: SeedLockManager):
        _propose(mgr, _kpi())
        mgr.propose("room-2", "other", "w", [], _kpi())
        cands = mgr.list_candidates(room_id="room-1")
        assert len(cands) == 1
        assert cands[0].room_id == "room-1"


class TestSeedVersion:
    def test_default_version(self, mgr: SeedLockManager):
        seed = _propose(mgr)
        major, minor = mgr.seed_version(seed.seed_id)
        assert (major, minor) == (1, 0)


class TestEdgeCases:
    def test_missing_seed_raises(self, mgr: SeedLockManager):
        with pytest.raises(KeyError):
            mgr.validate("nonexistent-id")

    def test_full_lifecycle(self, mgr: SeedLockManager):
        """UNLOCKED(implicit) → CANDIDATE → VALIDATING → LOCK_PENDING → LOCKED → DEPRECATED"""
        seed = _propose(mgr, _kpi(completion=98.0))
        assert seed.state == SeedState.CANDIDATE

        validated = mgr.validate(seed.seed_id)
        assert validated.state == SeedState.LOCK_PENDING

        locked = mgr.lock(validated.seed_id)
        assert locked.state == SeedState.LOCKED

        active = mgr.get_active_seed("room-1", "analyst")
        assert active.seed_id == locked.seed_id

        deprecated = mgr.deprecate(locked.seed_id)
        assert deprecated.state == SeedState.DEPRECATED

        # After deprecation, no active seed
        assert mgr.get_active_seed("room-1", "analyst") is None
