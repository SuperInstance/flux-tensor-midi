"""Module 9: SpreaderRoom — the 8-step intelligence tiling loop.

Wires together deadband detection, frozen context windows, and seed locking
into a single tick-based room that runs the spreader intelligence loop.

The loop:
    1. CAPTURE STATE        — record incoming KPIs
    2. UPDATE SLIDING WINDOW — aggregate metrics over the context window
    3. CREATE FROZEN SNAPSHOT — snapshot KPIs when deadband first detected
    4. CHECK DEADBAND        — are we struggling?
    5. CHECK ESCALATION      — need LLM help?
    6. RUN LOCAL INFERENCE   — use locked seed if available
    7. UPDATE SEED LOCK      — validate / promote candidates
    8. SYNC                  — return state for peer coordination
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, Generator, Iterable, List, Optional

from .deadband import DeadbandDetector
from .frozen_context import FCWManager
from .seed_lock import SeedLockManager
from .types import (
    DeadbandConfig,
    DeadbandSeverity,
    FrozenContextWindow,
    KPIMetrics,
    RoomType,
    SEED_LOCK_KPI,
    Seed,
    SeedState,
    TriggerType,
)


# ── Severity classifier ─────────────────────────────────────────────────────

def _classify_severity(score: float) -> DeadbandSeverity:
    """Map a 0–1 severity score to a DeadbandSeverity enum."""
    if score < 0.2:
        return DeadbandSeverity.NONE
    if score < 0.4:
        return DeadbandSeverity.LOW
    if score < 0.6:
        return DeadbandSeverity.MEDIUM
    if score < 0.8:
        return DeadbandSeverity.HIGH
    return DeadbandSeverity.CRITICAL


# ── SpreaderRoom ─────────────────────────────────────────────────────────────

class SpreaderRoom:
    """A PLATO room running the spreader intelligence tiling loop.

    Usage::

        room = SpreaderRoom("room-1", RoomType.SENSOR)
        for kpi in kpi_stream:
            result = room.tick(kpi)
            # result["deadband_state"] tells you if we're struggling
    """

    def __init__(
        self,
        room_id: str,
        room_type: RoomType,
        config: Optional[DeadbandConfig] = None,
        *,
        fcw_manager: Optional[FCWManager] = None,
        seed_manager: Optional[SeedLockManager] = None,
        window_size: int = 6,
    ) -> None:
        self.room_id = room_id
        self.room_type = room_type
        self._config = config or DeadbandConfig()

        # Subsystems
        self._detector = DeadbandDetector(self._config)
        self._fcw_mgr = fcw_manager or FCWManager()
        self._seed_mgr = seed_manager or SeedLockManager()

        # Sliding window for KPI aggregation (step 2)
        self._window_size = window_size
        self._kpi_window: deque[KPIMetrics] = deque(maxlen=window_size)

        # Tick bookkeeping
        self._tick_number: int = 0
        self._last_kpi: Optional[KPIMetrics] = None

        # Deadband entry tracking — create FCW once per deadband episode
        self._was_in_deadband: bool = False
        self._current_episode_fcw_ids: List[str] = []

        # Current active seed reference
        self._active_seed: Optional[Seed] = None

    # ── The 8-step tick ──────────────────────────────────────────────────

    def tick(self, kpi: KPIMetrics) -> Dict[str, Any]:
        """Run one iteration of the 8-step loop.

        Returns dict with:
            deadband_state  — current DeadbandState
            severity        — DeadbandSeverity enum
            escalated       — bool, True when we need LLM help
            active_seed     — locked Seed or None
            fcw_created     — FrozenContextWindow if created this tick, else None
            fcws_created    — count of FCWs created this episode
            tick_number     — monotonically increasing tick counter
            aggregated_kpi  — averaged KPIMetrics over the sliding window
        """
        self._tick_number += 1

        # ── Step 1: CAPTURE STATE ────────────────────────────────────────
        self._last_kpi = kpi

        # ── Step 2: UPDATE SLIDING WINDOW ────────────────────────────────
        self._kpi_window.append(kpi)
        aggregated = self._aggregate_window()

        # ── Step 3 & 4: CHECK DEADBAND ───────────────────────────────────
        db_state = self._detector.update(kpi)
        severity = _classify_severity(db_state.severity)

        fcw_created: Optional[FrozenContextWindow] = None

        # ── Step 3 (conditional): CREATE FROZEN SNAPSHOT ─────────────────
        if db_state.in_deadband and not self._was_in_deadband:
            # Entering deadband — create FCW to capture the context
            fcw_created = self._fcw_mgr.create(
                room_id=self.room_id,
                room_type=self.room_type,
                kpi=kpi,
                trigger=TriggerType.THRESHOLD,
            )
            # Advance to FROZEN immediately
            fcw_created = self._fcw_mgr.freeze(fcw_created.fcw_id)
            self._current_episode_fcw_ids.append(fcw_created.fcw_id)

        # ── Step 5: CHECK ESCALATION ─────────────────────────────────────
        escalated = (
            db_state.in_deadband
            and severity in (DeadbandSeverity.HIGH, DeadbandSeverity.CRITICAL)
        )

        # ── Step 6: RUN LOCAL INFERENCE ──────────────────────────────────
        # For MVP: if we have a locked seed, we "use" it (flag only).
        # Actual inference dispatch is a later module.

        # ── Step 7: UPDATE SEED LOCK ─────────────────────────────────────
        self._update_seed(kpi)

        # ── Episode boundary tracking ────────────────────────────────────
        if not db_state.in_deadband and self._was_in_deadband:
            # Exiting deadband — reset episode state
            self._current_episode_fcw_ids.clear()

        self._was_in_deadband = db_state.in_deadband

        # ── Step 8: SYNC ─────────────────────────────────────────────────
        return {
            "deadband_state": db_state,
            "severity": severity,
            "escalated": escalated,
            "active_seed": self._active_seed,
            "fcw_created": fcw_created,
            "fcws_created": len(self._current_episode_fcw_ids),
            "tick_number": self._tick_number,
            "aggregated_kpi": aggregated,
        }

    # ── Continuous runner ────────────────────────────────────────────────

    def run(
        self,
        kpi_stream: Iterable[KPIMetrics],
        ticks: Optional[int] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """Run continuous loop over *kpi_stream*.

        Yields the result dict from each ``tick()``.  If *ticks* is given,
        stop after that many iterations (useful for tests).
        """
        count = 0
        for kpi in kpi_stream:
            yield self.tick(kpi)
            count += 1
            if ticks is not None and count >= ticks:
                break

    # ── Status ───────────────────────────────────────────────────────────

    @property
    def status(self) -> Dict[str, Any]:
        """Current room status snapshot."""
        return {
            "room_id": self.room_id,
            "room_type": self.room_type.value,
            "tick_number": self._tick_number,
            "in_deadband": self._was_in_deadband,
            "active_seed_id": self._active_seed.seed_id if self._active_seed else None,
            "active_seed_state": (
                self._active_seed.state.value if self._active_seed else None
            ),
            "fcw_count": self._fcw_mgr.count(),
            "window_size": len(self._kpi_window),
        }

    # ── Subsystem accessors ──────────────────────────────────────────────

    @property
    def detector(self) -> DeadbandDetector:
        return self._detector

    @property
    def fcw_manager(self) -> FCWManager:
        return self._fcw_mgr

    @property
    def seed_manager(self) -> SeedLockManager:
        return self._seed_mgr

    # ── Internal ─────────────────────────────────────────────────────────

    def _aggregate_window(self) -> KPIMetrics:
        """Average KPIs across the sliding window."""
        if not self._kpi_window:
            return self._last_kpi or KPIMetrics(
                task_completion_rate=100.0,
                avg_wait_time=0.0,
                energy_over_baseline=0.0,
                inference_mae=0.0,
            )

        n = len(self._kpi_window)
        return KPIMetrics(
            task_completion_rate=sum(k.task_completion_rate for k in self._kpi_window) / n,
            avg_wait_time=sum(k.avg_wait_time for k in self._kpi_window) / n,
            energy_over_baseline=sum(k.energy_over_baseline for k in self._kpi_window) / n,
            inference_mae=sum(k.inference_mae for k in self._kpi_window) / n,
            timestamp=self._kpi_window[-1].timestamp,
            window_id=self._tick_number,
        )

    def _update_seed(self, kpi: KPIMetrics) -> None:
        """Step 7: Manage seed lifecycle based on current KPI state.

        Logic:
        - If no active seed and KPIs are excellent → propose + validate + lock
        - If KPIs are recovering from deadband and no active seed → try to
          promote a candidate
        """
        existing = self._seed_mgr.get_active_seed(self.room_id, "default")

        if existing is not None:
            self._active_seed = existing
            return

        # Check if we have candidates waiting to be validated
        candidates = self._seed_mgr.list_candidates(room_id=self.room_id)

        if candidates:
            # Validate the first candidate
            try:
                seed = self._seed_mgr.validate(candidates[0].seed_id)
                if seed.state == SeedState.LOCK_PENDING:
                    seed = self._seed_mgr.lock(seed.seed_id)
                    self._active_seed = seed
            except (ValueError, KeyError):
                pass
            return

        # If KPIs are good enough to warrant a seed, propose one
        if kpi.task_completion_rate >= SEED_LOCK_KPI:
            try:
                seed = self._seed_mgr.propose(
                    room_id=self.room_id,
                    role_name="default",
                    weights_ref="local://baseline",
                    fcw_ids=list(self._current_episode_fcw_ids),
                    kpi=kpi,
                )
                # Immediately validate — MVP fast-path
                seed = self._seed_mgr.validate(seed.seed_id)
                if seed.state == SeedState.LOCK_PENDING:
                    seed = self._seed_mgr.lock(seed.seed_id)
                    self._active_seed = seed
            except (ValueError, KeyError):
                pass
