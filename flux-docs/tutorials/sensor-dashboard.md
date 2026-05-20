# Building a Real Project: Sensor Dashboard

Walk through a complete sensor monitoring system from scratch. Eight sensors, automotive preset, validation, drift detection, and config persistence.

**Prerequisites:** [Getting Started](../getting-started.md) (5 minutes) and a Python environment with `flux-lib` installed.

```bash
pip install flux-lib
```

---

## Step 1: Define Your Sensors

Automotive engine bay — 8 sensors, each with physically meaningful bounds:

```python
from flux_lib import ConstraintEngine, check_exact, error_mask

engine = ConstraintEngine()

# Automotive engine bay sensor layout
engine.add_constraint("coolant_temp", -40, 150)    # °C
engine.add_constraint("oil_pressure", 0.5, 6.0)    # bar
engine.add_constraint("intake_temp", -40, 80)      # °C
engine.add_constraint("rpm", 800, 3600)            # rev/min
engine.add_constraint("maf_flow", 0, 480)          # g/s
engine.add_constraint("throttle_pos", 0, 100)      # %
engine.add_constraint("battery_voltage", 10.5, 15.0) # V
engine.add_constraint("fuel_level", 0, 100)        # %

print(f"Constraints loaded: {engine.constraint_count}")
# Constraints loaded: 8
```

## Step 2: Check Individual Readings

```python
# Normal operation — everything within bounds
normal = engine.check({
    "coolant_temp": 92,
    "oil_pressure": 3.5,
    "intake_temp": 35,
    "rpm": 2400,
    "maf_flow": 120,
    "throttle_pos": 45,
    "battery_voltage": 13.8,
    "fuel_level": 72
})
print(f"Normal mask: {normal.error_mask:08b}")  # 00000000
print(f"Status: {'OK' if normal.error_mask == 0 else 'ALERT'}")
# Status: OK

# Overheating engine — coolant temp violation
overheating = engine.check({
    "coolant_temp": 158,        # VIOLATES (> 150)
    "oil_pressure": 2.1,
    "intake_temp": 42,
    "rpm": 3200,
    "maf_flow": 200,
    "throttle_pos": 80,
    "battery_voltage": 13.2,
    "fuel_level": 45
})
print(f"Overheat mask: {overheating.error_mask:08b}")  # 00000001
print(f"Violated: {overheating.violated_names}")
# Violated: ['coolant_temp']

# Multiple failures — sensor glitch scenario
glitch = engine.check({
    "coolant_temp": 158,            # VIOLATES
    "oil_pressure": float("nan"),   # VIOLATES (NaN always fails)
    "intake_temp": 42,
    "rpm": 4200,                    # VIOLATES (> 3600)
    "maf_flow": 120,
    "throttle_pos": 45,
    "battery_voltage": 9.0,         # VIOLATES (< 10.5)
    "fuel_level": 72
})
print(f"Glitch mask: {glitch.error_mask:08b}")  # 00011011
print(f"Severity: {glitch.severity}")           # CRITICAL
print(f"Violations: {glitch.violation_count}")  # 4
```

## Step 3: Validate with check_vector

`check_vector` validates a single value against its constraint and returns a structured result — useful when you need the exact violation type, not just the bit:

```python
from flux_lib import check_vector

# Check individual sensor values with detailed results
result = check_vector(158, -40, 150)
print(result)
# CheckResult(violated=True, is_nan=False, below_lo=False, above_hi=True)

result = check_vector(float("nan"), 0, 100)
print(result)
# CheckResult(violated=True, is_nan=True, below_lo=False, above_hi=False)

result = check_vector(92, -40, 150)
print(result)
# CheckResult(violated=False, is_nan=False, below_lo=False, above_hi=False)
```

Use `check_vector` when you need to know *why* a value violated, not just *that* it violated.

## Step 4: Add a Sediment Layer

The oil pressure sensor has a known quirk: it reads 0.5 bar when disconnected, which is technically within bounds but physically impossible if the engine is running (rpm > 0):

```python
from flux_lib import SedimentStack

stack = SedimentStack()

# Layer 1: oil pressure at minimum with engine running = sensor fault
stack.add_layer(
    context="Oil pressure sensor dropout: 0.5 bar with rpm > 0 means disconnected",
    corrections=[{
        "constraint": "oil_pressure",
        "action": "violate",
        "if_value": 0.5,
        "if_other": {"rpm": (0, None)}  # only flag if rpm > 0
    }]
)

# Layer 2: fuel level at 0% triggers low-fuel warning even though in bounds
stack.add_layer(
    context="Low fuel: 0% is within bounds but should flag",
    corrections=[{
        "constraint": "fuel_level",
        "action": "violate",
        "if_value": 0
    }]
)

# Layer 3: coolant temp > 105 should be CRITICAL regardless of other violations
stack.add_layer(
    context="Coolant overheat escalation",
    corrections=[{
        "constraint": "coolant_temp",
        "action": "escalate",
        "if_value_gt": 105
    }]
)

print(f"Sediment layers: {stack.layer_count}")
# Sediment layers: 3
```

Now re-check the borderline case:

```python
# Before sediment: 0.5 bar oil pressure PASSES (within [0.5, 6.0])
before = engine.check({
    "coolant_temp": 92, "oil_pressure": 0.5, "intake_temp": 35,
    "rpm": 2400, "maf_flow": 120, "throttle_pos": 45,
    "battery_voltage": 13.8, "fuel_level": 72
})
print(f"Before sediment: {before.error_mask:08b}")  # 00000000 (misses it!)

# After sediment: the layer catches the sensor fault
after = stack.apply(
    base_mask=before.error_mask,
    names=engine.constraint_names,
    values=[92, 0.5, 35, 2400, 120, 45, 13.8, 72],
    definitions=[(-40, 150), (0.5, 6.0), (-40, 80), (800, 3600),
                 (0, 480), (0, 100), (10.5, 15.0), (0, 100)]
)
print(f"After sediment:  {after.error_mask:08b}")    # 00000010 (caught!)
print(f"Layers applied: {after.layers_applied}")     # 1
```

## Step 5: Batch Validation + Aggregation

Real dashboards process hundreds of readings per second. Batch mode checks multiple rows at once and aggregates the results:

```python
from flux_lib import aggregate_masks, batch_check

# Simulate 5 seconds of sensor data (5 readings × 8 sensors)
readings = [
    {"coolant_temp": 92,  "oil_pressure": 3.5, "intake_temp": 35, "rpm": 2400,
     "maf_flow": 120, "throttle_pos": 45, "battery_voltage": 13.8, "fuel_level": 72},
    {"coolant_temp": 95,  "oil_pressure": 3.4, "intake_temp": 36, "rpm": 2500,
     "maf_flow": 130, "throttle_pos": 50, "battery_voltage": 13.7, "fuel_level": 71},
    {"coolant_temp": 102, "oil_pressure": 3.2, "intake_temp": 38, "rpm": 2800,
     "maf_flow": 150, "throttle_pos": 60, "battery_voltage": 13.5, "fuel_level": 70},
    {"coolant_temp": 115, "oil_pressure": 3.0, "intake_temp": 40, "rpm": 3200,
     "maf_flow": 180, "throttle_pos": 75, "battery_voltage": 13.2, "fuel_level": 68},
    {"coolant_temp": 148, "oil_pressure": 2.8, "intake_temp": 44, "rpm": 3500,
     "maf_flow": 220, "throttle_pos": 90, "battery_voltage": 12.8, "fuel_level": 65},
]

# Batch check — returns one mask per reading
results = batch_check(engine, readings)
for i, r in enumerate(results):
    print(f"t={i}s: mask={r.error_mask:08b} violations={r.violation_count}")
# t=0s: mask=00000000 violations=0
# t=1s: mask=00000000 violations=0
# t=2s: mask=00000000 violations=0
# t=3s: mask=00000000 violations=0
# t=4s: mask=00000001 violations=1  ← coolant at 148, nearly at limit

# Aggregate: OR all masks to see "did any reading violate constraint X ever?"
worst_case = aggregate_masks([r.error_mask for r in results])
print(f"Worst-case mask: {worst_case:08b}")  # 00000001

# Aggregate: count violations per constraint across all readings
from collections import Counter
violation_counts = Counter()
for r in results:
    for name in r.violated_names:
        violation_counts[name] += 1
print(f"Violation frequency: {dict(violation_counts)}")
# Violation frequency: {'coolant_temp': 1}
```

## Step 6: Drift Detection

Temperatures are climbing — is the engine trending toward failure? Drift detection compares sequential readings to catch trends before they hit limits:

```python
from flux_lib import detect_drift

# Extract coolant temperature time series
coolant_series = [r["coolant_temp"] for r in readings]
# [92, 95, 102, 115, 148]

# Detect drift: is the rate of change accelerating?
drift = detect_drift(
    series=coolant_series,
    threshold=5.0,     # °C per reading — flag if rising faster
    window=3,          # look at last 3 readings
    bound_hi=150       # upper limit for reference
)

print(f"Drift rate: {drift.rate:.1f} °C/reading")
# Drift rate: 18.7 °C/reading  (92→95→102→115→148)
print(f"Drifting: {drift.is_drifting}")      # True
print(f"Acceleration: {drift.acceleration:.1f} °C/reading²")
# Acceleration: 7.4  (rate is increasing — not just climbing, but climbing FASTER)
print(f"Predicted next: {drift.predicted_next:.1f} °C")
# Predicted next: 166.3 °C (will EXCEED 150!)
print(f"Time to violation: {drift.readings_to_violation}")
# Time to violation: <1 reading

# The dashboard should alert NOW, not when the limit is actually hit
if drift.is_drifting and drift.readings_to_violation is not None:
    if drift.readings_to_violation <= 2:
        print("⚠️ CRITICAL: Coolant temperature will exceed limit within 2 readings!")
```

## Step 7: Save and Load Configuration

Don't hardcode constraints. Save the configuration and load it at startup:

```python
import json

# Save the full config: constraints + sediment layers
config = {
    "name": "automotive_engine_bay",
    "version": "1.0.0",
    "constraints": [
        {"name": "coolant_temp",   "lo": -40, "hi": 150},
        {"name": "oil_pressure",   "lo": 0.5, "hi": 6.0},
        {"name": "intake_temp",    "lo": -40, "hi": 80},
        {"name": "rpm",            "lo": 800, "hi": 3600},
        {"name": "maf_flow",       "lo": 0,   "hi": 480},
        {"name": "throttle_pos",   "lo": 0,   "hi": 100},
        {"name": "battery_voltage","lo": 10.5,"hi": 15.0},
        {"name": "fuel_level",     "lo": 0,   "hi": 100},
    ],
    "sediment": [
        {
            "context": "Oil pressure sensor dropout",
            "corrections": [{"constraint": "oil_pressure", "action": "violate",
                           "if_value": 0.5, "if_other": {"rpm": [0, None]}}]
        },
        {
            "context": "Low fuel warning",
            "corrections": [{"constraint": "fuel_level", "action": "violate",
                           "if_value": 0}]
        },
    ],
    "drift": {
        "threshold": 5.0,
        "window": 3
    }
}

# Serialize to JSON
with open("sensor_config.json", "w") as f:
    json.dump(config, f, indent=2)
print("Config saved to sensor_config.json")

# --- Later: load from file ---

with open("sensor_config.json") as f:
    loaded = json.load(f)

# Rebuild the engine from config
engine2 = ConstraintEngine()
for c in loaded["constraints"]:
    engine2.add_constraint(c["name"], c["lo"], c["hi"])

# Rebuild sediment from config
stack2 = SedimentStack()
for layer in loaded["sediment"]:
    stack2.add_layer(layer["context"], layer["corrections"])

# Ready to use — identical to the original
result = engine2.check({
    "coolant_temp": 92, "oil_pressure": 3.5, "intake_temp": 35, "rpm": 2400,
    "maf_flow": 120, "throttle_pos": 45, "battery_voltage": 13.8, "fuel_level": 72
})
print(f"Loaded engine mask: {result.error_mask:08b}")  # 00000000
print(f"Constraints: {engine2.constraint_count}")       # 8
```

## The Complete System

Here's the full loop that a real dashboard would run:

```python
from flux_lib import (ConstraintEngine, SedimentStack, batch_check,
                       aggregate_masks, detect_drift)
import json

# --- Load config ---
with open("sensor_config.json") as f:
    config = json.load(f)

engine = ConstraintEngine()
for c in config["constraints"]:
    engine.add_constraint(c["name"], c["lo"], c["hi"])

stack = SedimentStack()
for layer in config["sediment"]:
    stack.add_layer(layer["context"], layer["corrections"])

drift_cfg = config["drift"]

# --- Process a batch of readings ---
def process_batch(readings):
    # 1. Check all readings
    results = batch_check(engine, readings)

    # 2. Apply sediment to each
    for i, r in enumerate(results):
        values = [readings[i][n] for n in engine.constraint_names]
        corrected = stack.apply(
            base_mask=r.error_mask,
            names=engine.constraint_names,
            values=values,
            definitions=engine.constraint_definitions
        )
        results[i] = corrected

    # 3. Aggregate worst case
    worst = aggregate_masks([r.error_mask for r in results])

    # 4. Drift detection on coolant temp
    coolant = [r["coolant_temp"] for r in readings]
    drift = detect_drift(coolant, **drift_cfg, bound_hi=150)

    # 5. Dashboard output
    return {
        "total_readings": len(readings),
        "violations": sum(r.violation_count for r in results),
        "worst_case_mask": f"{worst:08b}",
        "any_critical": worst != 0,
        "drift_alert": drift.is_drifting,
        "drift_sensor": "coolant_temp",
        "drift_predicted": drift.predicted_next,
        "drift_time_to_limit": drift.readings_to_violation,
    }

# Run it
report = process_batch(readings)
print(json.dumps(report, indent=2))
```

**What you built:** A complete sensor monitoring pipeline with bounds checking, edge-case correction, batch processing, trend detection, and persistent configuration — in ~100 lines of Python.

---

## Next Steps

- **[Error Masks](../concepts/error-mask.md)** — understand the bit-level data structure
- **[NaN Trap](../concepts/nan-trap.md)** — why NaN always violates
- **[Sediment Layers](../concepts/sediment.md)** — the immutable correction system
- **[Thermodynamics](../concepts/thermodynamics.md)** — soft constraints and anomaly detection
- **[Python API](../api/python.md)** — full API reference
- **[FAQ](../faq.md)** — common questions
