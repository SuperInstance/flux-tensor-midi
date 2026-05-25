# Python API — `flux-lib`

```bash
pip install flux-lib
```

## Core

### `ConstraintEngine`

The main interface. Combines exact checking, fracture-coalesce, and sediment.

```python
from flux_lib import ConstraintEngine

engine = ConstraintEngine()
engine.add_constraint("coolant_temp", -40, 150)
engine.add_constraint("pressure", 0, 100)
engine.add_constraint("rpm", 800, 3600)
```

#### Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `add_constraint(name, lo, hi)` | — | Add a named constraint |
| `check(values: dict)` | `CheckResult` | Check all constraints |
| `use(strategy: str)` | — | Enable strategy ("fracture" or "sediment") |
| `fracture()` | `FractureResult` | Split into independent blocks |
| `add_sediment_layer(context, corrections)` | — | Add correction layer |
| `check_with_sediment(values)` | `SedimentResult` | Check with sediment applied |

### `CheckResult`

| Field | Type | Description |
|-------|------|-------------|
| `error_mask` | `int` | Bitmask of violations |
| `violations` | `list[bool]` | Per-constraint violation array |
| `severity` | `Severity` | PASS / CAUTION / WARNING / CRITICAL |
| `violation_count` | `int` | Number of violated constraints |
| `violated_names` | `list[str]` | Names of violated constraints |

### `Severity`

```
PASS      — mask == 0
CAUTION   — 1-2 violations, low severity
WARNING   — 3-4 violations, mixed severity
CRITICAL  — 5+ violations or any critical-severity constraint
```

## Exact Checking

```python
from flux_lib import check_exact, check_one, error_mask

# Batch: check N values against N bounds
violations = check_exact(
    values=[151, 50, 3.2, 6, 50, 2000, 240, float("nan")],
    bounds=[(-40, 150), (0, 100), (0.5, 10), (0, 5),
            (10, 95), (800, 3600), (110, 240), (0.1, 15)]
)
mask = error_mask(violations)  # 0b10001001

# Single value
violated = check_one(float("nan"), 0, 100)  # True (NaN always violates)
```

## Fracture-Coalesce

```python
from flux_lib import DependencyGraph, fracture, coalesce

# Build dependency graph
graph = DependencyGraph.from_masks([
    [0],         # constraint 0 → dimension 0
    [1],         # constraint 1 → dimension 1
    [2, 3],      # constraint 2 → dimensions 2,3
    [4],         # constraint 3 → dimension 4
])

# Fracture
result = fracture(graph)
print(f"Blocks: {result.n_blocks}")      # 4
print(f"Speedup: {result.speedup:.1f}x") # 4.0x

# Coalesce block masks
final = coalesce([0b0001, 0b0000, 0b0100, 0b0000])  # 0b0101
```

## Sediment

```python
from flux_lib import SedimentStack

stack = SedimentStack()
stack.add_layer(
    context="Sensor dropout detected",
    corrections=[{"constraint": "pressure", "action": "violate", "if_value": 0}]
)

# Check with sediment
result = stack.apply(base_mask, names, values, definitions)
```

## check_vector — Detailed Single Check

```python
from flux_lib import check_vector

result = check_vector(158, -40, 150)
# CheckResult(violated=True, is_nan=False, below_lo=False, above_hi=True)

result = check_vector(float("nan"), 0, 100)
# CheckResult(violated=True, is_nan=True, below_lo=False, above_hi=False)
```

| Field | Type | Description |
|-------|------|-------------|
| `violated` | `bool` | True if value is outside bounds or NaN |
| `is_nan` | `bool` | True if value is NaN |
| `below_lo` | `bool` | True if value < lower bound |
| `above_hi` | `bool` | True if value > upper bound |

## Serialization

```python
import json

# Serialize engine config to dict
config = engine.to_dict()
# {"constraints": [{"name": "coolant_temp", "lo": -40, "hi": 150}, ...]}

# Save to JSON file
with open("config.json", "w") as f:
    json.dump(config, f, indent=2)

# Load from JSON
with open("config.json") as f:
    config = json.load(f)

engine2 = ConstraintEngine.from_dict(config)

# Serialize/deserialize sediment stack
stack_config = stack.to_dict()
stack2 = SedimentStack.from_dict(stack_config)
```

| Method | Description |
|--------|-------------|
| `engine.to_dict()` | Serialize constraints to a plain dict |
| `ConstraintEngine.from_dict(d)` | Rebuild engine from dict |
| `stack.to_dict()` | Serialize sediment layers |
| `SedimentStack.from_dict(d)` | Rebuild stack from dict |

## Aggregation

```python
from flux_lib import aggregate_masks, batch_check

# Batch check multiple readings
results = batch_check(engine, readings)

# Aggregate: bitwise OR of all masks (worst case)
worst = aggregate_masks([r.error_mask for r in results])

# Aggregate: count violations per constraint
from flux_lib import violation_frequency
freqs = violation_frequency([r.error_mask for r in results], engine.constraint_names)
# {"coolant_temp": 3, "rpm": 1, ...}
```

| Function | Description |
|----------|-------------|
| `batch_check(engine, readings)` | Check multiple reading dicts |
| `aggregate_masks(masks)` | Bitwise OR of all masks |
| `violation_frequency(masks, names)` | Count per-constraint violations |

## Drift Detection

```python
from flux_lib import detect_drift

drift = detect_drift(
    series=[92, 95, 102, 115, 148],
    threshold=5.0,     # flag if rate exceeds this
    window=3,          # look-back window
    bound_hi=150       # upper limit for prediction
)
print(drift.rate)               # 18.7 units/reading
print(drift.is_drifting)        # True
print(drift.acceleration)       # 7.4 units/reading²
print(drift.predicted_next)     # 166.3
print(drift.readings_to_violation)  # <1
```

| Field | Type | Description |
|-------|------|-------------|
| `rate` | `float` | Current rate of change |
| `is_drifting` | `bool` | True if rate exceeds threshold |
| `acceleration` | `float` | Second derivative (rate of rate) |
| `predicted_next` | `float` | Projected next value |
| `readings_to_violation` | `int or None` | Estimated readings until limit hit |

## Invariants

1. **Zero false negatives** — a value outside bounds is ALWAYS detected.
2. **NaN always violates** — no opt-in required.
3. **Bounds checked with `<=`** — boundary values pass.
4. **No external dependencies** — pure Python + NumPy.
