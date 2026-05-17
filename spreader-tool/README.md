# spreader-tool

**Intelligence tiling for PLATO rooms — frozen context windows, seed locking, deadband detection.**

Spreader watches PLATO rooms for **deadband**: the gap between what hardcoded rules handle and what needs real intelligence. When a room enters deadband, Spreader freezes reasoning snapshots, validates them, and locks proven-good checkpoints (Seeds) that deploy fleet-wide.

## Why use it?

Every agent room has a blind spot — tasks too complex for rules, too frequent for full LLM calls. Spreader detects those gaps automatically and builds a library of validated responses. Think of it as a self-improving reflex system for your agent fleet.

- **Deadband detection** — continuous KPI monitoring with hysteresis (no flickering)
- **Frozen Context Windows** — immutable, copy-on-write snapshots of room reasoning state
- **Seed lifecycle** — staged validation pipeline from candidate to fleet-deployable
- **Zero dependencies** — pure Python dataclasses, no framework lock-in

## Install

```bash
# From source (recommended during early development)
pip install git+https://github.com/SuperInstance/spreader-tool.git

# Or clone and install editable
git clone https://github.com/SuperInstance/spreader-tool.git
cd spreader-tool
pip install -e ".[dev]"
```

## Quick Example

```python
from spreader import DeadbandDetector, KPIMetrics, make_seed, SeedState
import time

# Set up a detector with default thresholds
detector = DeadbandDetector()

# Feed KPI snapshots on each tick (completion < 90% triggers deadband)
metrics = KPIMetrics(
    task_completion_rate=82.0,  # below 90% threshold
    avg_wait_time=45.0,         # above 30s threshold
    energy_over_baseline=5.0,
    inference_mae=8.0,
    timestamp=time.time(),
)
state = detector.update(metrics)

print(f"In deadband: {state.in_deadband}")      # True
print(f"Severity: {state.severity:.2f}")         # 0.0–1.0
print(f"Breached: {state.breached_metrics}")     # [COMPLETION_RATE, WAIT_TIME]

# Once validated, lock a seed for fleet deployment
seed = make_seed(room_id="warehouse-1", role_name="drift-detect")
seed = seed.transition_to(SeedState.CANDIDATE)
seed = seed.transition_to(SeedState.VALIDATING)
seed = seed.transition_to(SeedState.LOCK_PENDING)
seed = seed.transition_to(SeedState.LOCKED)  # deployable
```

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────┐
│  KPI Metrics │────▶│ DeadbandDetector │────▶│  FCW Freeze  │
│  (per tick)  │     │  + hysteresis    │     │  (snapshot)  │
└─────────────┘     └──────────────────┘     └──────┬───────┘
                                                     │
                    ┌────────────────────────────────┘
                    ▼
            ┌──────────────┐     ┌──────────────┐
            │   Testing    │────▶│  Seed Lock   │
            │  (validate)  │     │  (fleet-wide)│
            └──────────────┘     └──────────────┘
```

**Flow:** KPI metrics stream in on every tick → DeadbandDetector checks thresholds with duration gates → when deadband is confirmed, a Frozen Context Window is created → tested → validated Seed is locked for fleet deployment.

### Deadband triggers

| Metric | Threshold | Duration |
|--------|-----------|----------|
| Task completion rate | < 90% | 5 minutes sustained |
| Average wait time | > 30s | 30 seconds sustained |
| Energy over baseline | > 10% | 30 seconds sustained |
| Inference MAE | > 10% | 3 consecutive windows |

### FCW lifecycle

`STAGING → FROZEN → TESTING → REFINING → LOCKED` (or `DISCARDED` at any pre-lock stage)

### Seed lifecycle

`UNLOCKED → CANDIDATE → VALIDATING → LOCK_PENDING → LOCKED → DEPRECATED → ARCHIVED`

## Module Structure

```
spreader/
├── __init__.py    # Public API re-exports
├── types.py       # FCW, Seed, KPI types, enums, state machines
└── deadband.py    # DeadbandDetector with hysteresis
```

## Tests

```bash
python -m pytest tests/ -v
```

23 tests covering types, state transitions, immutability, factory functions, and deadband detection logic.

## Related Repos

| Repo | Purpose |
|------|---------|
| [plato-types](https://github.com/SuperInstance/plato-types) | Tile lifecycle, Lamport clocks |
| [plato-training](https://github.com/SuperInstance/plato-training) | Micro models, hardware deploy |
| [tensor-spline](https://github.com/SuperInstance/tensor-spline) | SplineLinear compression |
| [forgemaster](https://github.com/SuperInstance/forgemaster) | Fleet agent (constraint theory) |

## License

MIT
