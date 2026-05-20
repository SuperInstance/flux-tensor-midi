# Getting Started

Check 8 values against 8 bounds in under 5 minutes.

## Python

```bash
pip install flux-lib
```

```python
from flux_lib import ConstraintEngine

engine = ConstraintEngine()
engine.add_constraint("temp", -40, 150)
engine.add_constraint("pressure", 0, 100)
engine.add_constraint("flow_rate", 0.5, 10.0)
engine.add_constraint("vibration", 0, 5)
engine.add_constraint("humidity", 10, 95)
engine.add_constraint("rpm", 800, 3600)
engine.add_constraint("voltage", 110, 240)
engine.add_constraint("current", 0.1, 15)

result = engine.check({
    "temp": 151,        # VIOLATES (above 150)
    "pressure": 50,     # passes
    "flow_rate": 3.2,   # passes
    "vibration": 6,     # VIOLATES (above 5)
    "humidity": 50,     # passes
    "rpm": 2000,        # passes
    "voltage": 240,     # passes (boundary ok)
    "current": float("nan")  # VIOLATES (NaN always fails)
})

print(f"Error mask: {result.error_mask:08b}")  # 01010001
# Bit 0: temp violated
# Bit 3: vibration violated
# Bit 7: current violated (NaN trap)
```

## Rust

```bash
cargo add flux-fracture
```

```rust
use flux_fracture::{ConstraintEngine, Bounds};

fn main() {
    let engine = ConstraintEngine::new();
    engine.add("temp", -40.0, 150.0);
    engine.add("pressure", 0.0, 100.0);
    engine.add("flow_rate", 0.5, 10.0);
    engine.add("vibration", 0.0, 5.0);
    engine.add("humidity", 10.0, 95.0);
    engine.add("rpm", 800.0, 3600.0);
    engine.add("voltage", 110.0, 240.0);
    engine.add("current", 0.1, 15.0);

    let values = [151.0, 50.0, 3.2, 6.0, 50.0, 2000.0, 240.0, f64::NAN];
    let mask = engine.check(&values);

    println!("Error mask: {:08b}", mask);  // 01010001
    assert_ne!(mask, 0);  // violations detected
}
```

## JavaScript

```bash
npm install @flux/check
```

> **If `npm install @flux/check` returns 404**, the package may not yet be published to the registry. Clone it directly:
> ```bash
> git clone https://github.com/SuperInstance/flux-check-js.git
> cd flux-check-js && npm install && npm run build
> ```
> Then import from the local path.

```js
import { ConstraintEngine } from "@flux/check";

const engine = new ConstraintEngine();
engine.addConstraint("temp", -40, 150);
engine.addConstraint("pressure", 0, 100);
engine.addConstraint("flow_rate", 0.5, 10.0);
engine.addConstraint("vibration", 0, 5);
engine.addConstraint("humidity", 10, 95);
engine.addConstraint("rpm", 800, 3600);
engine.addConstraint("voltage", 110, 240);
engine.addConstraint("current", 0.1, 15);

const result = engine.check({
    temp: 151,           // VIOLATES
    pressure: 50,
    flow_rate: 3.2,
    vibration: 6,        // VIOLATES
    humidity: 50,
    rpm: 2000,
    voltage: 240,
    current: NaN         // VIOLATES (NaN always fails)
});

console.log(`Error mask: ${result.errorMask.toString(2).padStart(8, "0")}`);
// 1010001 → bits 0, 3, 7 set
```

## C

Download [flux_fracture.h](https://github.com/SuperInstance/flux-fracture-c) — single header, no dependencies.

```c
#define FRACTURE_IMPLEMENTATION
#include "flux_fracture.h"

int main() {
    /* 8 bounds: {lo, hi} pairs */
    double lo[] = {-40, 0, 0.5, 0, 10, 800, 110, 0.1};
    double hi[] = {150, 100, 10.0, 5, 95, 3600, 240, 15};
    double vals[] = {151, 50, 3.2, 6, 50, 2000, 240, NAN};

    uint8_t mask = 0;
    for (int i = 0; i < 8; i++) {
        uint8_t bit = (isnan(vals[i]) || vals[i] < lo[i] || vals[i] > hi[i]) ? 1 : 0;
        mask |= (bit << i);
    }

    printf("Error mask: %08b\n", mask);  /* 10001001 */
    return mask != 0;
}
```

## What Just Happened?

Every implementation did the same thing:

1. Defined 8 constraints (lower bound, upper bound).
2. Checked 8 values — three of which violate (above max, above max, NaN).
3. Packed the result into a single byte where each bit means "this constraint was violated."

The error mask `10001001` means constraints 0, 3, and 7 failed. One byte. No heap. No iteration needed to ask "did anything fail?" — just `mask != 0`.

**Next:** Understand *why* this data structure matters → [Error Masks](concepts/error-mask.md)

**Go deeper:** [Sensor Dashboard Tutorial](tutorials/sensor-dashboard.md) — build a complete project · [FAQ](faq.md) — common questions
