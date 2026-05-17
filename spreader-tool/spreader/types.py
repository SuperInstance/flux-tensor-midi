"""Spreader-Tool type definitions — FCW, Seed, Deadband types."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
from uuid import UUID


# ── Deadband types ──────────────────────────────────────────────────────────

class DeadbandMetric(str, Enum):
    """Which KPI triggered deadband entry."""
    COMPLETION_RATE = "completion_rate"
    WAIT_TIME = "wait_time"
    ENERGY_OVER_BASELINE = "energy_over_baseline"
    INFERENCE_MAE = "inference_mae"


class DeadbandSeverity(str, Enum):
    """Coarse severity bucket."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DeadbandConfig:
    """Configurable thresholds for deadband detection."""
    completion_rate_threshold: float = 90.0      # %
    completion_rate_duration: float = 300.0       # seconds (5 min)
    wait_time_threshold: float = 30.0             # seconds
    wait_time_duration: float = 30.0              # sustained duration
    energy_threshold: float = 10.0                # % above baseline
    energy_duration: float = 30.0                 # sustained duration
    mae_threshold: float = 10.0                   # %
    mae_consecutive_windows: int = 3
    hysteresis_exit_factor: float = 1.1           # must recover 10% past threshold to exit
    tick_interval: float = 10.0                   # seconds between updates


@dataclass
class KPIMetrics:
    """Snapshot of room KPIs fed into the deadband detector."""
    task_completion_rate: float   # 0-100 %
    avg_wait_time: float          # seconds
    energy_over_baseline: float   # %
    inference_mae: float          # %

    # Optional metadata
    timestamp: Optional[float] = None  # unix epoch, auto-filled if None
    window_id: Optional[int] = None


@dataclass
class DeadbandState:
    """Full deadband assessment at a point in time."""
    in_deadband: bool
    severity: float                               # 0.0 – 1.0
    breached_metrics: List[DeadbandMetric] = field(default_factory=list)
    time_entered: Optional[float] = None          # unix epoch when entered
    durations: dict = field(default_factory=dict)  # metric → seconds breached
    mae_consecutive_count: int = 0


# ── FCW types (minimal stub for Module 2) ───────────────────────────────────

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


# ── Seed types (minimal stub for Module 2) ──────────────────────────────────

class SeedState(str, Enum):
    UNLOCKED = "unlocked"
    CANDIDATE = "candidate"
    VALIDATING = "validating"
    LOCK_PENDING = "lock_pending"
    LOCKED = "locked"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"
