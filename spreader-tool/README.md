# Spreader-Tool

Intelligence tiling for PLATO room deadband coverage.

## What It Is

The Spreader-Tool watches PLATO rooms for **deadband** — the gap between what hardcoded rules can handle and what requires full LLM inference. When a room enters deadband, the Spreader freezes snapshots of reasoning state (Frozen Context Windows), validates them, and locks proven-good checkpoints (Seeds) that can be deployed fleet-wide.

**Analogy:** A self-driving car encounters a new intersection type. Instead of sending every frame to the cloud, it freezes a snapshot, flags the gap, and gradually builds a "known good" response pattern. Once validated, that pattern becomes a seed any car can use.

## Status

**Phase 1 MVP** — single-room implementation proving the concept.

## Install

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Quick Example

```python
from spreader import (
    make_fcw, make_seed,
    RoomType, FCWStatus, SeedState,
    DeadbandState, DeadbandMetric,
)

# Create a frozen context window for a sensor room
fcw = make_fcw(
    room_id="warehouse-drone-1",
    room_type=RoomType.SENSOR,
    task_completion_rate=85.0,  # below 90% baseline → deadband territory
    avg_inference_mae=12.0,
)

# Advance through the lifecycle (immutable copy-on-write)
fcw = fcw.transition_to(FCWStatus.FROZEN)
fcw = fcw.transition_to(FCWStatus.TESTING)
fcw = fcw.transition_to(FCWStatus.REFINING)
fcw = fcw.transition_to(FCWStatus.LOCKED)

# Create and advance a seed
seed = make_seed(room_id="warehouse-drone-1", role_name="drift-detect")
seed = seed.transition_to(SeedState.CANDIDATE)
seed = seed.transition_to(SeedState.VALIDATING)
seed = seed.transition_to(SeedState.LOCK_PENDING)
seed = seed.transition_to(SeedState.LOCKED)  # now deployable fleet-wide

# Check deadband state
deadband = DeadbandState(
    in_deadband=True,
    severity=0.7,
    breached_metrics=frozenset({DeadbandMetric.TASK_COMPLETION}),
    duration=450.0,
)
print(f"Room in deadband: {deadband.in_deadband}, severity: {deadband.severity}")
```

## Module Structure

```
spreader/
├── __init__.py      # Re-exports all public types
├── types.py         # All data structures, enums, constants
├── deadband.py      # Deadband detection (Phase 1, next)
├── frozen_context.py  # FCW lifecycle manager (Phase 1)
├── seed_lock.py     # Seed state machine (Phase 1)
└── ...              # More modules as roadmap progresses
```

## Architecture

See [SPREADER-TOOL-ARCHITECTURE.md](../review/SPREADER-TOOL-ARCHITECTURE.md) for the full design document.

## Tests

```bash
python -m pytest tests/ -v
```

36 tests covering all data structures, state transitions, immutability, and factory functions.
