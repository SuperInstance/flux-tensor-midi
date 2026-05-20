# Rust API — `flux-fracture`

```toml
[dependencies]
flux-fracture = "0.1.0"
```

## Core

### `DependencyGraph`

Bipartite constraint×dimension adjacency graph.

```rust
use flux_fracture::DependencyGraph;

let graph = DependencyGraph::identity(8);  // 8 independent constraints
```

| Method | Description |
|--------|-------------|
| `from_adjacency(adj, n_c, n_d)` | Build from flat row-major adjacency |
| `from_masks(masks)` | Build from per-constraint dimension index lists |
| `identity(n)` | Identity: constraint `i` touches only dimension `i` |
| `involves(c, d)` | Check if constraint `c` involves dimension `d` |
| `constraint_dims(c)` | Dimensions involved in constraint `c` |
| `dim_constraints(d)` | Constraints involving dimension `d` |
| `set_edge(c, d, val)` | Set an adjacency entry |
| `fill_block(c0, c1, d0, d1)` | Fill a rectangular block with 1s |
| `stats()` | Connected-component statistics |

### `Fracturer`

```rust
use flux_fracture::{Fracturer, DependencyGraph};

let graph = DependencyGraph::identity(8);
let result = Fracturer::new().fracture(&graph);

println!("Blocks: {}", result.n_blocks);           // 8
println!("Speedup: {}x", result.speedup_potential); // 8.0
```

| Method | Description |
|--------|-------------|
| `fracture(&graph)` | BFS connected components → `FractureResult` |

### `FractureResult`

| Field | Type | Description |
|-------|------|-------------|
| `blocks` | `Vec<Block>` | Independent blocks |
| `n_blocks` | `usize` | Number of blocks |
| `largest_block_size` | `usize` | Constraints in the biggest block |
| `speedup_potential` | `f64` | `n_constraints / largest_block_size` |

### `Coalescer`

```rust
use flux_fracture::Coalescer;

let total = Coalescer::new().coalesce_masks(&[0b0001, 0b0010, 0b0100]);
assert_eq!(total, 0b0111);
```

| Method | Description |
|--------|-------------|
| `coalesce_masks(&[u64])` | Bitwise OR of error masks |
| `coalesce_arrays(&[Vec<u8>])` | Elementwise OR of violation arrays |
| `verify_coalescence(masks, indices, mono)` | Verify coalesced == monolithic |

### `AdaptiveFracturer`

Re-fractures when the dependency structure changes.

```rust
use flux_fracture::AdaptiveFracturer;

let mut af = AdaptiveFracturer::new(graph);
let (result, delta) = af.update(&new_graph);
```

| Method | Description |
|--------|-------------|
| `update(&graph)` | Re-fracture, returns `(FractureResult, FractureDelta)` |
| `current()` | Get last fracture result |
| `refracture_count` | How many times structure actually changed |

## Performance

Pure Rust, zero dependencies. BFS on flat adjacency arrays.

| System | Rust | Python | Speedup |
|--------|------|--------|:-------:|
| 8 constraints | ~100 ns | ~10 µs | 100× |
| 64 constraints | ~500 ns | ~50 µs | 100× |
| 256 constraints | ~5 µs | ~500 µs | 100× |

## Testing

```bash
cargo test    # All four dependency structures verified
cargo bench   # Performance benchmarks
```

## Invariants

1. **Zero false negatives** — bitwise OR coalescence preserves all violations.
2. **Zero dependencies** — no external crates.
3. **Zero heap allocation in hot path** — flat arrays, fixed-size BFS queue.

## check_vector — Detailed Single Check

```rust
use flux_fracture::check_vector;

let result = check_vector(158.0, -40.0, 150.0);
// CheckResult { violated: true, is_nan: false, below_lo: false, above_hi: true }

let nan_result = check_vector(f64::NAN, 0.0, 100.0);
// CheckResult { violated: true, is_nan: true, below_lo: false, above_hi: false }
```

| Field | Type | Description |
|-------|------|-------------|
| `violated` | `bool` | True if value is outside bounds or NaN |
| `is_nan` | `bool` | True if value is NaN |
| `below_lo` | `bool` | True if value < lower bound |
| `above_hi` | `bool` | True if value > upper bound |

## Serialization

```rust
use flux_fracture::{ConstraintEngine, SedimentStack};
use serde_json;

// Serialize
let config = engine.to_json()?;
std::fs::write("config.json", &config)?;

// Deserialize
let config_str = std::fs::read_to_string("config.json")?;
let engine2 = ConstraintEngine::from_json(&config_str)?;

// Sediment serialization
let stack_json = stack.to_json()?;
let stack2 = SedimentStack::from_json(&stack_json)?;
```

| Method | Description |
|--------|-------------|
| `engine.to_json()` | Serialize to JSON string |
| `ConstraintEngine::from_json(s)` | Rebuild from JSON |
| `stack.to_json()` | Serialize sediment layers |
| `SedimentStack::from_json(s)` | Rebuild from JSON |

## Aggregation

```rust
use flux_fracture::{batch_check, aggregate_masks, violation_frequency};

// Batch check
let results: Vec<CheckResult> = batch_check(&engine, &readings);

// Aggregate worst case (bitwise OR)
let worst = aggregate_masks(results.iter().map(|r| r.error_mask));

// Per-constraint violation counts
let freqs = violation_frequency(&masks, &names);
```

| Function | Description |
|----------|-------------|
| `batch_check(engine, readings)` | Check multiple value sets |
| `aggregate_masks(masks)` | Bitwise OR of all masks |
| `violation_frequency(masks, names)` | Count per-constraint violations |

## Drift Detection

```rust
use flux_fracture::detect_drift;

let drift = detect_drift(
    &[92.0, 95.0, 102.0, 115.0, 148.0],
    5.0,    // threshold
    3,      // window
    Some(150.0), // bound_hi
);
println!("Rate: {:.1}", drift.rate);              // 18.7
println!("Drifting: {}", drift.is_drifting);      // true
println!("Predicted: {:.1}", drift.predicted_next); // 166.3
println!("To violation: {:?}", drift.readings_to_violation); // Some(0)
```

| Field | Type | Description |
|-------|------|-------------|
| `rate` | `f64` | Current rate of change |
| `is_drifting` | `bool` | True if rate exceeds threshold |
| `acceleration` | `f64` | Second derivative |
| `predicted_next` | `f64` | Projected next value |
| `readings_to_violation` | `Option<usize>` | Readings until limit hit |

## Related Crates

| Crate | Purpose |
|-------|--------|
| `plato-types` | Tile lifecycle, Lamport clocks |
| `tensor-spline` | SplineLinear compression |
| `plato-data` | CSV/JSONL data loading |
| `plato-training` | Micro model training |
