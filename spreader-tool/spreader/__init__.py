"""Spreader-Tool: Intelligence tiling for PLATO room deadband coverage."""

from spreader.types import (
    # Constants
    WINDOW_DURATION,
    TICK_INTERVAL,
    BASELINE_COMPLETION,
    DEADBAND_MIN_DURATION,
    ESCALATION_MAE_THRESHOLD,
    SEED_LOCK_KPI,
    TASK_COMPLETION_THRESHOLD,
    AVG_WAIT_TIME_THRESHOLD,
    ENERGY_OVERAGE_THRESHOLD,
    INFERENCE_MAE_THRESHOLD,
    MAE_CONSECUTIVE_WINDOWS,
    # Enums
    RoomType,
    DeadbandMetric,
    DeadbandSeverity,
    FCWStatus,
    TriggerType,
    SeedState,
    # Data structures
    KPIMetrics,
    DeadbandConfig,
    DeadbandState,
    FrozenContextWindow,
    Seed,
    # Factories
    make_fcw,
    make_seed,
)
from spreader.deadband import DeadbandDetector, DeadbandConfig as DeadbandDetectorConfig
from spreader.frozen_context import FCWManager
from spreader.store import SpreaderStore
from spreader.seed_lock import SeedLockManager
from spreader.cost import CostTracker
from spreader.redaction import RedactionEngine
from spreader.spreader_room import SpreaderRoom
