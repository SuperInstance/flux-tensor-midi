# JavaScript API — `@flux/check`

```bash
npm install @flux/check
```

## Core

```js
import { ConstraintEngine, Severity } from "@flux/check";

const engine = new ConstraintEngine();
engine.addConstraint("coolant_temp", -40, 150);
engine.addConstraint("pressure", 0, 100);

const result = engine.check({ coolant_temp: 151, pressure: 50 });
// result.errorMask === 0b001
// result.severity === Severity.CAUTION
// result.violatedNames === ["coolant_temp"]
```

### `ConstraintEngine`

| Method | Returns | Description |
|--------|---------|-------------|
| `addConstraint(name, lo, hi, dims?)` | — | Add a named constraint |
| `check(values)` | `CheckResult` | Check all constraints |
| `use(strategy)` | — | Enable "fracture" or "sediment" |
| `fracture()` | `FractureResult` | Split into independent blocks |
| `addSedimentLayer(context, corrections)` | — | Add correction layer |
| `checkWithSediment(values)` | `SedimentResult` | Check with sediment |

### `CheckResult`

| Field | Type | Description |
|-------|------|-------------|
| `errorMask` | `number` | Bitmask of violations |
| `violations` | `Uint8Array` | Per-constraint violation array |
| `severity` | `Severity` | PASS / CAUTION / WARNING / CRITICAL |
| `violationCount` | `number` | Number violated |
| `violatedNames` | `string[]` | Names of violated constraints |

## Exact Checking (`src/core.ts`)

```js
import { checkExact, checkOne, errorMask, severityFromMask } from "@flux/check";

// Batch
const violations = checkExact(
    [151, 50, 3.2, 6, 50, 2000, 240, NaN],
    [[-40, 150], [0, 100], [0.5, 10], [0, 5],
     [10, 95], [800, 3600], [110, 240], [0.1, 15]]
);
const mask = errorMask(violations);  // 0b10001001

// Single
checkOne(NaN, 0, 100);  // 1 (NaN always violates)

// Severity from mask
severityFromMask(0b10001001);  // Severity.WARNING
```

| Function | Description |
|----------|-------------|
| `checkExact(values, bounds)` | Batch exact check. NaN always violates. Bounds `<=`. |
| `checkOne(value, lo, hi)` | Single value check → `0 \| 1` |
| `errorMask(violations)` | Bitmask from violation array |
| `severityFromMask(mask)` | PASS / CAUTION / WARNING / CRITICAL |

## Fracture-Coalesce (`src/fracture.ts`)

```js
import { DependencyGraph, fracture, coalesce } from "@flux/check";

const graph = DependencyGraph.fromMasks([[0], [1], [2, 3], [4]]);
const result = fracture(graph);
// result.nBlocks === 4, result.speedupPotential === 4.0

const final = coalesce([0b0001, 0b0000, 0b0100, 0b0000]);  // 0b0101
```

| Function | Description |
|----------|-------------|
| `DependencyGraph.fromMasks(masks)` | Build bipartite graph |
| `fracture(graph)` | BFS connected components |
| `coalesce(blockMasks)` | Bitwise OR coalescence |

## Sediment (`src/sediment.ts`)

```js
import { SedimentStack } from "@flux/check";

const stack = new SedimentStack();
stack.addLayer("Sensor dropout", [
    { constraint: "pressure", action: "violate", ifValue: 0 }
]);
```

| Class/Method | Description |
|-------------|-------------|
| `SedimentStack` | Immutable correction layers |
| `addLayer(context, corrections)` | Add correction |
| `apply(errorMask, names, values, defs)` | Simplified post-processing |

## check_vector — Detailed Single Check

```js
import { checkVector } from "@flux/check";

const result = checkVector(158, -40, 150);
// { violated: true, is_nan: false, below_lo: false, above_hi: true }

const nanResult = checkVector(NaN, 0, 100);
// { violated: true, is_nan: true, below_lo: false, above_hi: false }
```

| Field | Type | Description |
|-------|------|-------------|
| `violated` | `boolean` | True if value is outside bounds or NaN |
| `is_nan` | `boolean` | True if value is NaN |
| `below_lo` | `boolean` | True if value < lower bound |
| `above_hi` | `boolean` | True if value > upper bound |

## Serialization

```js
// Serialize to JSON
const config = engine.toJSON();
localStorage.setItem("flux_config", JSON.stringify(config));

// Load from JSON
const saved = JSON.parse(localStorage.getItem("flux_config"));
const engine2 = ConstraintEngine.fromJSON(saved);

// Sediment serialization
const stackConfig = stack.toJSON();
const stack2 = SedimentStack.fromJSON(stackConfig);
```

| Method | Description |
|--------|-------------|
| `engine.toJSON()` | Serialize constraints to plain object |
| `ConstraintEngine.fromJSON(obj)` | Rebuild from object |
| `stack.toJSON()` | Serialize sediment layers |
| `SedimentStack.fromJSON(obj)` | Rebuild from object |

## Aggregation

```js
import { batchCheck, aggregateMasks, violationFrequency } from "@flux/check";

// Batch check multiple readings
const results = batchCheck(engine, readings);

// Aggregate: bitwise OR of all masks
const worst = aggregateMasks(results.map(r => r.errorMask));

// Per-constraint violation counts
const freqs = violationFrequency(
    results.map(r => r.errorMask),
    engine.constraintNames
);
// { coolant_temp: 3, rpm: 1, ... }
```

| Function | Description |
|----------|-------------|
| `batchCheck(engine, readings)` | Check multiple value objects |
| `aggregateMasks(masks)` | Bitwise OR of all masks |
| `violationFrequency(masks, names)` | Count per-constraint violations |

## Drift Detection

```js
import { detectDrift } from "@flux/check";

const drift = detectDrift(
    [92, 95, 102, 115, 148],  // series
    5.0,    // threshold
    3,      // window
    150     // bound_hi
);
console.log(`Rate: ${drift.rate.toFixed(1)}`);           // 18.7
console.log(`Drifting: ${drift.isDrifting}`);             // true
console.log(`Predicted: ${drift.predictedNext.toFixed(1)}`); // 166.3
console.log(`To violation: ${drift.readingsToViolation}`);   // <1
```

| Field | Type | Description |
|-------|------|-------------|
| `rate` | `number` | Current rate of change |
| `isDrifting` | `boolean` | True if rate exceeds threshold |
| `acceleration` | `number` | Second derivative |
| `predictedNext` | `number` | Projected next value |
| `readingsToViolation` | `number or null` | Readings until limit hit |

## Invariants

1. **Zero false negatives** — always detected.
2. **NaN always violates** — `Number.isNaN()` check, no opt-in.
3. **Bounds checked with `<=`** — boundary values pass.
4. **No external dependencies** — pure TypeScript, runs anywhere (Node, browser, Deno, Bun).

## Build & Test

```bash
npm install
npx tsc
node tests/core.test.mjs
```
