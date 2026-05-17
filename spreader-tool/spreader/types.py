"""Spreader-Tool type definitions — FCW, Seed, Deadband types."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import time

# ── Constants ────────────────────────────────────────────────────────────────

WINDOW_DURATION: float = 60.0        # Fixed context window length (seconds)
TICK_INTERVAL: float = 10.0          # Period between core loop ticks
BASELINE_COMPLETION: float = 90.0    # Baseline task completion %
DEADBAND_MIN_DURATION: float = 300.0 # 5 minutes
ESCALATION_MAE_THRESHOLD: float = 10.0
SEED_LOCK_KPI: float = 95.0          # KPI threshold to lock a seed
TASK_COMPLETION_THRESHOLD: float = 90.0
AVG_WAIT_TIME_THRESHOLD: float = 30.0
ENERGY_OVERAGE_THRESHOLD: float = 10.0
INFERENCE_MAE_THRESHOLD: float = 10.0
MAE_CONSECUTIVE_WINDOWS: int = 3

# ── Enums ────────────────────────────────────────────────────────────────────

class RoomType(str, Enum):
    SENSOR = "sensor"
    COLLAB_ANALYSIS = "collab_analysis"
    COMMAND = "command"
    SIMULATION = "simulation"

class DeadbandMetric(str, Enum):
    COMPLETION_RATE = "completion_rate"
    WAIT_TIME = "wait_time"
    ENERGY_OVER_BASELINE = "energy_over_baseline"
    INFERENCE_MAE = "inference_mae"

class DeadbandSeverity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class FCWStatus(str, Enum):
    STAGING = "staging"
    FROZEN = "frozen"
    TESTING = "testing"
    REFINING = "refining"
    LOCKED = "locked"
    DISCARDED = "discarded"

class TriggerType(str, Enum):
    TIME = "time"
    THRESHOLD = "threshold"
    CONTEXT_SHIFT = "context_shift"
    CRITICAL_CALL = "critical_call"
    MANUAL = "manual"

class SeedState(str, Enum):
    UNLOCKED = "unlocked"
    CANDIDATE = "candidate"
    VALIDATING = "validating"
    LOCK_PENDING = "lock_pending"
    LOCKED = "locked"
    ESCALATING = "escalating"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

# ── Valid state transitions ─────────────────────────────────────────────────

_FCW_TRANSITIONS: Dict[FCWStatus, set] = {
    FCWStatus.STAGING: {FCWStatus.FROZEN, FCWStatus.DISCARDED},
    FCWStatus.FROZEN: {FCWStatus.TESTING, FCWStatus.DISCARDED},
    FCWStatus.TESTING: {FCWStatus.REFINING, FCWStatus.FROZEN, FCWStatus.DISCARDED},
    FCWStatus.REFINING: {FCWStatus.TESTING, FCWStatus.LOCKED, FCWStatus.DISCARDED},
    FCWStatus.LOCKED: set(),  # terminal
    FCWStatus.DISCARDED: set(),  # terminal
}

_SEED_TRANSITIONS: Dict[SeedState, set] = {
    SeedState.UNLOCKED: {SeedState.CANDIDATE},
    SeedState.CANDIDATE: {SeedState.VALIDATING, SeedState.UNLOCKED},
    SeedState.VALIDATING: {SeedState.LOCK_PENDING, SeedState.CANDIDATE},
    SeedState.LOCK_PENDING: {SeedState.LOCKED, SeedState.CANDIDATE},
    SeedState.LOCKED: {SeedState.ESCALATING, SeedState.DEPRECATED},
    SeedState.ESCALATING: {SeedState.LOCKED, SeedState.DEPRECATED},
    SeedState.DEPRECATED: {SeedState.ARCHIVED},
    SeedState.ARCHIVED: {SeedState.LOCKED},  # emergency restore
}

# ── Data structures ─────────────────────────────────────────────────────────

@dataclass(frozen=True)
class KPIMetrics:
    task_completion_rate: float   # 0-100 %
    avg_wait_time: float          # seconds
    energy_over_baseline: float   # %
    inference_mae: float          # %
    timestamp: Optional[float] = None
    window_id: Optional[int] = None

@dataclass(frozen=True)
class DeadbandConfig:
    completion_rate_threshold: float = 90.0
    completion_rate_duration: float = 300.0
    wait_time_threshold: float = 30.0
    wait_time_duration: float = 30.0
    energy_threshold: float = 10.0
    energy_duration: float = 30.0
    mae_threshold: float = 10.0
    mae_consecutive_windows: int = 3
    hysteresis_exit_factor: float = 1.1
    tick_interval: float = 10.0

@dataclass
class DeadbandState:
    in_deadband: bool
    severity: float  # 0.0 – 1.0
    breached_metrics: tuple = ()
    time_entered: Optional[float] = None
    durations: tuple = ()  # (metric, seconds) pairs
    mae_consecutive_count: int = 0

@dataclass(frozen=True)
class FrozenContextWindow:
    fcw_id: str
    frozen_at: float
    room_id: str
    room_type: RoomType
    status: FCWStatus
    kpi_snapshot: KPIMetrics
    trigger: TriggerType
    safety_compliant: bool = True
    peer_count: int = 0
    linked_seed_version: Optional[str] = None
    extensions: Dict[str, Any] = field(default_factory=dict)
    _transition_guard: int = 0  # bumped on every transition for copy-on-write

    def can_transition_to(self, new_status: FCWStatus) -> bool:
        return new_status in _FCW_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status: FCWStatus) -> "FrozenContextWindow":
        if not self.can_transition_to(new_status):
            raise ValueError(f"Invalid FCW transition: {self.status} → {new_status}")
        return FrozenContextWindow(
            fcw_id=self.fcw_id,
            frozen_at=self.frozen_at,
            room_id=self.room_id,
            room_type=self.room_type,
            status=new_status,
            kpi_snapshot=self.kpi_snapshot,
            trigger=self.trigger,
            safety_compliant=self.safety_compliant,
            peer_count=self.peer_count,
            linked_seed_version=self.linked_seed_version,
            extensions=dict(self.extensions),
            _transition_guard=self._transition_guard + 1,
        )

@dataclass(frozen=True)
class Seed:
    seed_id: str
    room_id: str
    role_name: str
    lineage_id: str
    state: SeedState
    weights_ref: Optional[str] = None
    context_window_ids: tuple = ()
    locked_kpis: Optional[KPIMetrics] = None
    backtest_score: Optional[float] = None
    version_major: int = 1
    version_minor: int = 0
    created_at: Optional[float] = None
    locked_at: Optional[float] = None
    extensions: Dict[str, Any] = field(default_factory=dict)
    _transition_guard: int = 0

    def can_transition_to(self, new_state: SeedState) -> bool:
        return new_state in _SEED_TRANSITIONS.get(self.state, set())

    def transition_to(self, new_state: SeedState) -> "Seed":
        if not self.can_transition_to(new_state):
            raise ValueError(f"Invalid Seed transition: {self.state} → {new_state}")
        now = time.time()
        locked_at = self.locked_at
        if new_state == SeedState.LOCKED:
            locked_at = now
        return Seed(
            seed_id=self.seed_id,
            room_id=self.room_id,
            role_name=self.role_name,
            lineage_id=self.lineage_id,
            state=new_state,
            weights_ref=self.weights_ref,
            context_window_ids=self.context_window_ids,
            locked_kpis=self.locked_kpis,
            backtest_score=self.backtest_score,
            version_major=self.version_major,
            version_minor=self.version_minor,
            created_at=self.created_at,
            locked_at=locked_at,
            extensions=dict(self.extensions),
            _transition_guard=self._transition_guard + 1,
        )

# ── Factory helpers ─────────────────────────────────────────────────────────

def make_fcw(
    room_id: str,
    room_type: RoomType,
    kpi_snapshot: KPIMetrics,
    trigger: TriggerType,
    **extensions: Any,
) -> FrozenContextWindow:
    return FrozenContextWindow(
        fcw_id=str(uuid4()),
        frozen_at=time.time(),
        room_id=room_id,
        room_type=room_type,
        status=FCWStatus.STAGING,
        kpi_snapshot=kpi_snapshot,
        trigger=trigger,
        extensions=extensions,
    )

def make_seed(
    room_id: str,
    role_name: str,
    lineage_id: Optional[str] = None,
) -> Seed:
    return Seed(
        seed_id=str(uuid4()),
        room_id=room_id,
        role_name=role_name,
        lineage_id=lineage_id or str(uuid4()),
        state=SeedState.UNLOCKED,
        created_at=time.time(),
    )
