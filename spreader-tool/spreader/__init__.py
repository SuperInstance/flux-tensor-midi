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
