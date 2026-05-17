"""Module 6: SeedLockManager — simplified seed state machine for MVP.

Manages the lifecycle of intelligence checkpoints:
    UNLOCKED → CANDIDATE → LOCK_PENDING → LOCKED → DEPRECATED

For MVP, validation uses a KPI-threshold backtest against SEED_LOCK_KPI.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from .types import (
    KPIMetrics,
    SEED_LOCK_KPI,
    Seed,
    SeedState,
    _SEED_TRANSITIONS,
)


# ── Minimal in-memory store (used when SpreaderStore isn't available) ──────

class _InMemorySeedStore:
    """Dict-backed seed storage for testing and standalone use."""

    def __init__(self) -> None:
        self._seeds: Dict[str, Seed] = {}

    def put(self, seed: Seed) -> None:
        self._seeds[seed.seed_id] = seed

    def get(self, seed_id: str) -> Optional[Seed]:
        return self._seeds.get(seed_id)

    def query(
        self,
        room_id: Optional[str] = None,
        state: Optional[SeedState] = None,
    ) -> List[Seed]:
        results = list(self._seeds.values())
        if room_id is not None:
            results = [s for s in results if s.room_id == room_id]
        if state is not None:
            results = [s for s in results if s.state == state]
        return results


# ── Store protocol (duck-typed) ─────────────────────────────────────────────
# Any object with put/get/query works.  _InMemorySeedStore qualifies.


class SeedLockManager:
    """Manages seed lifecycle transitions for one or more rooms."""

    def __init__(self, store: Optional[object] = None) -> None:
        # Accept any store-like object; fall back to in-memory.
        if store is not None and hasattr(store, "put") and hasattr(store, "get"):
            self._store = store
        else:
            self._store = _InMemorySeedStore()

    # ── Propose ──────────────────────────────────────────────────────────

    def propose(
        self,
        room_id: str,
        role_name: str,
        weights_ref: str,
        fcw_ids: List[str],
        kpi: KPIMetrics,
    ) -> Seed:
        """Create a new seed in CANDIDATE state."""
        now = time.time()
        seed = Seed(
            seed_id=str(uuid4()),
            room_id=room_id,
            role_name=role_name,
            lineage_id=str(uuid4()),
            state=SeedState.CANDIDATE,
            weights_ref=weights_ref,
            context_window_ids=tuple(fcw_ids),
            locked_kpis=kpi,
            created_at=now,
        )
        self._store.put(seed)
        return seed

    # ── Validate (backtest) ──────────────────────────────────────────────

    def validate(
        self,
        seed_id: str,
        backtest_fn: Optional[Callable[[Seed], bool]] = None,
    ) -> Seed:
        """Run backtest.  Pass → LOCK_PENDING, fail → back to CANDIDATE."""
        seed = self._require_seed(seed_id)
        if seed.state != SeedState.CANDIDATE:
            raise ValueError(
                f"Seed must be CANDIDATE to validate, got {seed.state.value}"
            )

        # Transition to VALIDATING
        seed = seed.transition_to(SeedState.VALIDATING)
        self._store.put(seed)

        # Determine pass/fail
        if backtest_fn is not None:
            passed = backtest_fn(seed)
        else:
            passed = self._default_backtest(seed)

        if passed:
            seed = seed.transition_to(SeedState.LOCK_PENDING)
        else:
            # back to CANDIDATE for refinement
            seed = seed.transition_to(SeedState.CANDIDATE)

        self._store.put(seed)
        return seed

    # ── Lock ─────────────────────────────────────────────────────────────

    def lock(self, seed_id: str) -> Seed:
        """LOCK_PENDING → LOCKED."""
        seed = self._require_seed(seed_id)
        if seed.state != SeedState.LOCK_PENDING:
            raise ValueError(
                f"Seed must be LOCK_PENDING to lock, got {seed.state.value}"
            )
        seed = seed.transition_to(SeedState.LOCKED)
        self._store.put(seed)
        return seed

    # ── Deprecate ────────────────────────────────────────────────────────

    def deprecate(
        self,
        seed_id: str,
        replacement_id: Optional[str] = None,
    ) -> Seed:
        """LOCKED → DEPRECATED (optionally noting replacement)."""
        seed = self._require_seed(seed_id)
        if seed.state != SeedState.LOCKED:
            raise ValueError(
                f"Seed must be LOCKED to deprecate, got {seed.state.value}"
            )
        seed = seed.transition_to(SeedState.DEPRECATED)
        if replacement_id is not None:
            ext = dict(seed.extensions)
            ext["replacement_id"] = replacement_id
            seed = Seed(
                seed_id=seed.seed_id,
                room_id=seed.room_id,
                role_name=seed.role_name,
                lineage_id=seed.lineage_id,
                state=seed.state,
                weights_ref=seed.weights_ref,
                context_window_ids=seed.context_window_ids,
                locked_kpis=seed.locked_kpis,
                backtest_score=seed.backtest_score,
                version_major=seed.version_major,
                version_minor=seed.version_minor,
                created_at=seed.created_at,
                locked_at=seed.locked_at,
                extensions=ext,
                _transition_guard=seed._transition_guard,
            )
        self._store.put(seed)
        return seed

    # ── Queries ──────────────────────────────────────────────────────────

    def get_active_seed(
        self,
        room_id: str,
        role_name: str,
    ) -> Optional[Seed]:
        """Return the currently LOCKED seed for a room+role, if any."""
        all_seeds = self._store.query(room_id=room_id, state=SeedState.LOCKED)
        matches = [s for s in all_seeds if s.role_name == role_name]
        return matches[0] if matches else None

    def list_candidates(
        self,
        room_id: Optional[str] = None,
    ) -> List[Seed]:
        """List seeds in CANDIDATE or LOCK_PENDING state."""
        candidates: List[Seed] = []
        for state in (SeedState.CANDIDATE, SeedState.LOCK_PENDING):
            candidates.extend(
                self._store.query(room_id=room_id, state=state)
            )
        return candidates

    def seed_version(self, seed_id: str) -> Tuple[int, int]:
        """Return (major, minor) version tuple for a seed."""
        seed = self._require_seed(seed_id)
        return (seed.version_major, seed.version_minor)

    # ── Internals ────────────────────────────────────────────────────────

    def _require_seed(self, seed_id: str) -> Seed:
        seed = self._store.get(seed_id)
        if seed is None:
            raise KeyError(f"Seed not found: {seed_id}")
        return seed

    @staticmethod
    def _default_backtest(seed: Seed) -> bool:
        """MVP backtest: check task_completion_rate against SEED_LOCK_KPI."""
        if seed.locked_kpis is None:
            return False
        return seed.locked_kpis.task_completion_rate >= SEED_LOCK_KPI
