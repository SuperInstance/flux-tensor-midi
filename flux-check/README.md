# flux-check

Standalone constraint checker extracted from flux-lib. Zero false negatives, uint8 error masks.

```python
from flux_check import ConstraintEngine, CheckResult, Severity

eng = ConstraintEngine.from_preset("automotive_can")
result = eng.check(7500)  # RPM
print(result.passed, result.error_mask, result.severity)
```

## Features

- **Zero false negatives**: A value outside bounds is ALWAYS detected. NaN always violates.
- **uint8 error masks**: Up to 8 constraints per engine, bit-packed for speed.
- **10 industry presets**: automotive_can, aviation_adsb, medical_fhir, financial_fix, energy_scada, iot_mqtt, maritime_nmea, nuclear_reactor, railway_ertms, robotics.
- **Batch vectorized**: `check_batch()` and `check_vector_batch()` for numpy arrays.
- **Zero-alloc hot path**: `check_mask()` for performance-critical loops.

## Installation

```bash
pip install flux-check
```
