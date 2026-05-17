"""FCWManager — Frozen Context Window lifecycle manager.

Handles creation, lifecycle transitions, content-addressed storage, and
querying of FCWs.  Every mutation produces a new FrozenContextWindow
(copy-on-write via the frozen dataclass) and the manager persists the
latest version in a dict keyed by fcw_id.

Content-addressed index lets callers detect duplicate snapshots via a
deterministic hash over (room_id, room_type, kpi_snapshot, trigger).
"""

import hashlib
import json
import os
import time
from typing import Dict, List, Optional, Set

from .types import (
    FCWStatus,
    FrozenContextWindow,
    KPIMetrics,
    RoomType,
    TriggerType,
    make_fcw,
)


class FCWManager:
    """In-memory FCW lifecycle manager with optional disk persistence."""

    def __init__(self, store_path: Optional[str] = ".fcw_store") -> None:
        self._store_path = store_path
        self._fcws: Dict[str, FrozenContextWindow] = {}
        self._content_index: Dict[str, Set[str]] = {}  # hash → {fcw_id, ...}
        self._room_index: Dict[str, Set[str]] = {}  # room_id → {fcw_id, ...}

    # ── CRUD ──────────────────────────────────────────────────────────────

    def create(
        self,
        room_id: str,
        room_type: RoomType,
        kpi: KPIMetrics,
        trigger: TriggerType,
        **extensions: object,
    ) -> FrozenContextWindow:
        """Create a new FCW in STAGING and index it."""
        fcw = make_fcw(room_id, room_type, kpi, trigger, **extensions)
        self._store(fcw)
        return fcw

    def freeze(self, fcw_id: str) -> FrozenContextWindow:
        """Convenience: advance STAGING → FROZEN."""
        return self.advance(fcw_id, FCWStatus.FROZEN)

    def advance(self, fcw_id: str, new_status: FCWStatus) -> FrozenContextWindow:
        """Transition an FCW to *new_status*, validating the transition."""
        fcw = self._get_or_raise(fcw_id)
        updated = fcw.transition_to(new_status)
        self._store(updated)
        return updated

    def discard(self, fcw_id: str) -> FrozenContextWindow:
        """Move an FCW to DISCARDED (valid from any non-terminal state)."""
        return self.advance(fcw_id, FCWStatus.DISCARDED)

    def get(self, fcw_id: str) -> Optional[FrozenContextWindow]:
        """Return an FCW by id, or None."""
        return self._fcws.get(fcw_id)

    # ── Queries ───────────────────────────────────────────────────────────

    def query(
        self,
        room_id: Optional[str] = None,
        status: Optional[FCWStatus] = None,
        since: Optional[float] = None,
        until: Optional[float] = None,
    ) -> List[FrozenContextWindow]:
        """Return FCWs matching all non-None filters.

        Results are sorted by frozen_at ascending (oldest first).
        """
        candidates = list(self._fcws.values())

        if room_id is not None:
            candidates = [f for f in candidates if f.room_id == room_id]
        if status is not None:
            candidates = [f for f in candidates if f.status == status]
        if since is not None:
            candidates = [f for f in candidates if f.frozen_at >= since]
        if until is not None:
            candidates = [f for f in candidates if f.frozen_at <= until]

        candidates.sort(key=lambda f: f.frozen_at)
        return candidates

    def find_by_content_hash(self, content_hash: str) -> List[FrozenContextWindow]:
        """Return all FCWs sharing the given content hash."""
        ids = self._content_index.get(content_hash, set())
        return [self._fcws[i] for i in ids if i in self._fcws]

    def active_for_room(self, room_id: str) -> List[FrozenContextWindow]:
        """Return non-terminal FCWs for a room (not LOCKED or DISCARDED)."""
        terminal = {FCWStatus.LOCKED, FCWStatus.DISCARDED}
        return [
            f for f in self.query(room_id=room_id) if f.status not in terminal
        ]

    # ── Content hashing ───────────────────────────────────────────────────

    def content_hash(self, fcw: FrozenContextWindow) -> str:
        """Deterministic SHA-256 over (room_id, room_type, kpi, trigger).

        Two FCWs with the same room, type, KPI snapshot, and trigger will
        produce the same hash — useful for dedup detection.
        """
        kpi = fcw.kpi_snapshot
        payload = json.dumps(
            {
                "room_id": fcw.room_id,
                "room_type": fcw.room_type.value,
                "kpi": {
                    "task_completion_rate": kpi.task_completion_rate,
                    "avg_wait_time": kpi.avg_wait_time,
                    "energy_over_baseline": kpi.energy_over_baseline,
                    "inference_mae": kpi.inference_mae,
                },
                "trigger": fcw.trigger.value,
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()

    # ── Statistics ─────────────────────────────────────────────────────────

    def count(self) -> int:
        """Return total number of stored FCWs."""
        return len(self._fcws)

    def count_by_status(self) -> Dict[FCWStatus, int]:
        """Return a dict of FCWStatus → count."""
        counts: Dict[FCWStatus, int] = {}
        for fcw in self._fcws.values():
            counts[fcw.status] = counts.get(fcw.status, 0) + 1
        return counts

    # ── Internal helpers ──────────────────────────────────────────────────

    def _store(self, fcw: FrozenContextWindow) -> None:
        """Persist an FCW in all indices."""
        self._fcws[fcw.fcw_id] = fcw

        # Content-addressed index
        ch = self.content_hash(fcw)
        if ch not in self._content_index:
            self._content_index[ch] = set()
        self._content_index[ch].add(fcw.fcw_id)

        # Room index
        if fcw.room_id not in self._room_index:
            self._room_index[fcw.room_id] = set()
        self._room_index[fcw.room_id].add(fcw.fcw_id)

    def _get_or_raise(self, fcw_id: str) -> FrozenContextWindow:
        """Look up an FCW or raise KeyError."""
        fcw = self._fcws.get(fcw_id)
        if fcw is None:
            raise KeyError(f"FCW not found: {fcw_id}")
        return fcw
