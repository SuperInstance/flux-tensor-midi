# C API — `flux_fracture.h`

Single-header C99 library. No dependencies. No heap allocation.

## Installation

Download [flux_fracture.h](https://github.com/SuperInstance/flux-fracture-c). In exactly one source file:

```c
#define FRACTURE_IMPLEMENTATION
#include "flux_fracture.h"
```

All other files just `#include "flux_fracture.h"` without the define.

## Quick Start

```c
#include <stdio.h>
#include <math.h>

#define FRACTURE_IMPLEMENTATION
#include "flux_fracture.h"

int main() {
    /* 8 independent constraints */
    frac_edge edges[8];
    for (int i = 0; i < 8; i++)
        edges[i] = (frac_edge){i, i};

    /* Fracture */
    frac_result result = frac_fracture_from_edges(edges, 8, 8, 8);
    printf("Blocks: %d, Largest: %d, Speedup: %.1fx\n",
           result.n_blocks, result.largest_block, result.speedup_potential);

    /* Check some values */
    double lo[] = {-40, 0, 0.5, 0, 10, 800, 110, 0.1};
    double hi[] = {150, 100, 10.0, 5, 95, 3600, 240, 15};
    double vals[] = {151, 50, 3.2, 6, 50, 2000, 240, NAN};

    uint8_t mask = 0;
    for (int i = 0; i < 8; i++) {
        uint8_t bit = (isnan(vals[i]) || vals[i] < lo[i] || vals[i] > hi[i]) ? 1 : 0;
        mask |= (bit << i);
    }
    printf("Error mask: %02x\n", mask);

    /* Coalesce block masks */
    uint64_t block_masks[8] = {1, 0, 1, 0, 1, 0, 1, 0};
    frac_coalesce_result cr = frac_coalesce(block_masks, result.blocks, 8, 8);

    /* Verify */
    bool ok = frac_coalesce_verify(cr.error_mask, 0x55, 8);

    frac_result_free(&result);
    return 0;
}
```

## Data Structures

| Type | Description |
|------|-------------|
| `frac_edge` | Bipartite edge: `{constraint_idx, dim_idx}` |
| `frac_block` | Independent block: constraint/dimension index arrays |
| `frac_result` | Fracture result: blocks, stats, speedup |
| `frac_coalesce_result` | Coalesced error mask with verification |
| `frac_adjacency` | Bipartite adjacency matrix |
| `frac_delta` | Change between two fracture results |

## Functions

### Graph Construction

| Function | Description |
|----------|-------------|
| `frac_graph_build(edges, n_edges, n_c, n_d)` | Build adjacency from edge list |
| `frac_graph_from_masks(masks, n_c, max_dims)` | Build from per-constraint dim masks |

### Fracture

| Function | Description |
|----------|-------------|
| `frac_fracture(adj, n_c, n_d)` | BFS connected components → blocks |
| `frac_fracture_from_edges(edges, n_e, n_c, n_d)` | One-step: edges → result |
| `frac_result_free(result)` | Free block memory |

### Coalesce

| Function | Description |
|----------|-------------|
| `frac_coalesce(masks, blocks, n_blocks, n_c)` | Bitwise OR coalescence |
| `frac_coalesce_verify(coalesced, expected, n_c)` | Verify correctness |

### Adaptive

| Function | Description |
|----------|-------------|
| `frac_adaptive_init(adj)` | Initialize adaptive fracture |
| `frac_adaptive_update(adj)` | Re-fracture if changed |
| `frac_adaptive_free()` | Release resources |

## Memory

- **Stack allocation only** in the hot path.
- BFS queue is fixed-size: `uint32_t queue[MAX_CONSTRAINTS]`.
- Blocks allocated with `malloc` — call `frac_result_free()` when done.
- Total working memory for 256 constraints: ~2KB.

## check_vector — Detailed Single Check

```c
typedef struct {
    bool violated;
    bool is_nan;
    bool below_lo;
    bool above_hi;
} frac_vector_result;

frac_vector_result frac_check_vector(double val, double lo, double hi) {
    frac_vector_result r = {0};
    r.is_nan = isnan(val);
    r.below_lo = !r.is_nan && (val < lo);
    r.above_hi = !r.is_nan && (val > hi);
    r.violated = r.is_nan || r.below_lo || r.above_hi;
    return r;
}

/* Usage */
frac_vector_result r = frac_check_vector(158.0, -40.0, 150.0);
// r.violated = true, r.above_hi = true
```

## Serialization

```c
/* Serialize constraint config to JSON string */
char* frac_engine_to_json(const double* lo, const double* hi,
                          const char** names, int n);

/* Deserialize from JSON string */
typedef struct {
    double* lo;
    double* hi;
    char** names;
    int n;
} frac_engine_config;

frac_engine_config frac_engine_from_json(const char* json_str);
void frac_engine_config_free(frac_engine_config* cfg);
```

| Function | Description |
|----------|-------------|
| `frac_engine_to_json(lo, hi, names, n)` | Serialize to JSON string (caller frees) |
| `frac_engine_from_json(str)` | Parse JSON to config struct |
| `frac_engine_config_free(cfg)` | Free config memory |

## Aggregation

```c
/* Batch check: check n_sets of values against one set of bounds */
uint8_t* frac_batch_check(const double* values, int n_values, int n_sets,
                           const double* lo, const double* hi, int n_bounds);

/* Aggregate: bitwise OR of all masks */
uint8_t frac_aggregate_masks(const uint8_t* masks, int n);

/* Per-constraint violation frequency */
int* frac_violation_frequency(const uint8_t* masks, int n_masks, int n_constraints);
```

| Function | Description |
|----------|-------------|
| `frac_batch_check(...)` | Returns array of masks (caller frees) |
| `frac_aggregate_masks(masks, n)` | Bitwise OR of all masks |
| `frac_violation_frequency(masks, n, nc)` | Per-constraint counts (caller frees) |

## Drift Detection

```c
typedef struct {
    double rate;
    bool is_drifting;
    double acceleration;
    double predicted_next;
    int readings_to_violation;  /* -1 if not drifting toward limit */
} frac_drift_result;

frac_drift_result frac_detect_drift(const double* series, int n,
                                     double threshold, int window,
                                     double bound_hi);

/* Usage */
double coolant[] = {92, 95, 102, 115, 148};
frac_drift_result drift = frac_detect_drift(coolant, 5, 5.0, 3, 150.0);
printf("Rate: %.1f\n", drift.rate);                   // 18.7
printf("Drifting: %s\n", drift.is_drifting ? "yes" : "no"); // yes
printf("Predicted: %.1f\n", drift.predicted_next);    // 166.3
```

## Invariants

1. **Zero false negatives** — bitwise OR coalescence is provably correct.
2. **NaN always violates** — `isnan()` check before comparison.
3. **C99 compatible** — works with any C99 compiler, no extensions.
4. **Single header** — `#define FRACTURE_IMPLEMENTATION` + `#include`.
