# Fracture-Coalesce

Split independent constraints into parallel blocks. Merge results with a proof.

## The Problem

You have 8 constraints. Some share dimensions (both check temperature), some don't (one checks temperature, another checks voltage). If you check them all sequentially, you're leaving performance on the table.

If two constraints are *independent* — they touch completely different dimensions — they can be checked simultaneously on different cores, different GPU warps, even different machines.

## The Dependency Graph

Build a bipartite graph: constraints on one side, dimensions on the other. An edge connects constraint `c` to dimension `d` if constraint `c` depends on dimension `d`.

```
Constraints    Dimensions
   C0 ───────── d0 (temperature)
   C1 ───────── d1 (pressure)
   C2 ─┬────── d2 (flow_rate)
       └────── d3 (total_flow)  ← C2 depends on both
   C3 ───────── d4 (vibration)
   C4 ───────── d5 (humidity)
   C5 ─┬────── d6 (rpm)
       └────── d7 (power)
   C6 ───────── d4 (vibration)  ← shares dimension with C3
   C7 ───────── d0 (temperature) ← shares dimension with C0
```

Connected components in this graph are independent blocks:

- **Block A:** {C0, C7} + {d0} — both check temperature
- **Block B:** {C1} + {d1} — pressure only
- **Block C:** {C2} + {d2, d3} — flow pair
- **Block D:** {C3, C6} + {d4} — vibration pair
- **Block E:** {C4} + {d5} — humidity only
- **Block F:** {C5} + {d6, d7} — rpm/power pair

6 blocks. Check them all simultaneously → **up to 6× parallelism.**

## BFS Connected Components

The fracture algorithm is BFS on the bipartite graph:

1. Pick an unvisited constraint.
2. BFS outward through constraint–dimension edges.
3. All reached nodes = one connected component (one block).
4. Repeat until all constraints are visited.

This is O(V + E) — linear in the graph size. For typical constraint systems (8–256 constraints), this takes microseconds on CPU.

## Coalescence: Bitwise OR

Each block produces its own error mask. To get the final result, OR them together:

```
Block A mask: 0b00000001  (C0 violated)
Block B mask: 0b00000000  (C1 passed)
Block C mask: 0b00000100  (C2 violated)
Block D mask: 0b00001000  (C3 violated)
Block E mask: 0b00000000  (C4 passed)
Block F mask: 0b00000000  (C5 passed)

Final mask:   0b00001101
```

One `OR` instruction per block. On GPU, this is a warp-level reduction using `__ballot_sync()`. Zero extra memory.

## The Proof

> **Theorem:** If fracture correctly identifies connected components of the constraint–dimension dependency graph, coalescence via bitwise OR preserves zero false negatives.

**Proof:**

Each constraint violation is a Boolean event. Each constraint belongs to exactly one block (connected components partition the constraint set). Therefore each violation bit appears in exactly one block's error mask.

The bitwise OR of all block masks sets a bit if and only if at least one block has that bit set. Since each bit appears in exactly one block, `bit i` is set in the coalesced mask if and only if constraint `i` was violated in its block.

No false negatives: every violation appears. No false positives: no bit is set without a violation. QED.

## Why This Matters

For fully independent constraints (identity dependency graph), you get N× parallelism for N constraints. In practice:

| Structure | Constraints | Blocks | Speedup |
|-----------|:-----------:|:------:|:-------:|
| Fully independent | 8 | 8 | 8× |
| Block diagonal (2×4) | 8 | 2 | 2× |
| Chain (cyclic pairs) | 8 | 1 | 1× |
| Fully connected | 8 | 1 | 1× |

Even partially independent systems benefit. And the coalescence is *free* — one bitwise OR per block, which is a single CPU instruction.

## Adaptive Re-Fracture

The dependency structure can change at runtime (a constraint is added, a dimension changes). The adaptive fracture algorithm detects changes and re-fractures only when necessary:

```
if dependency_changed:
    new_result = fracture(graph)
    delta = diff(old_result, new_result)
    old_result = new_result
```

Re-fracture is cheap (microseconds). Skipping it when nothing changed saves even more.

## On GPU

Fracture-coalesce maps perfectly to GPU architecture:

- Each CUDA block = one independent constraint group
- Each thread = one value to check
- `__ballot_sync()` + `__popc()` for warp-level violation counting
- Final OR across blocks = single kernel launch barrier

The [GPU benchmarks](../gpu/index.md) show this hitting **20.8 billion checks/sec** in batch mode — exactly the fracture-coalesce pattern.

## Code Example

```python
from flux_lib import DependencyGraph, fracture, coalesce

# Define which dimensions each constraint touches
# Constraint 0 → temp, Constraint 1 → pressure, etc.
graph = DependencyGraph.from_masks([
    [0],         # C0: temp only
    [1],         # C1: pressure only
    [2, 3],      # C2: flow_rate + total_flow (linked)
    [4],         # C3: vibration
    [5],         # C4: humidity
    [6, 7],      # C5: rpm + power (linked)
    [4],         # C6: vibration (shares with C3)
    [0],         # C7: temp (shares with C0)
])

# Fracture into independent blocks
result = fracture(graph)
print(f"Blocks: {result.n_blocks}")       # 6
print(f"Speedup: {result.speedup:.1f}x")  # up to 6.0x

# Each block produces its own error mask
block_masks = [0b00000001, 0b00000000, 0b00000100,
               0b00001000, 0b00000000, 0b00000000]

# Coalesce with a single OR per block
final = coalesce(block_masks)
print(f"Final mask: {final:08b}")  # 00001101
```

→ **Package:** [`flux-lib` (Python)](../api/python.md) · [`flux-fracture` (Rust)](../api/rust.md) · [`@flux/check` (JS)](../api/javascript.md) · [`flux_fracture.h` (C)](../api/c.md)

## When Would I Use This?

- **Multi-core constraint checking.** If you have more constraints than cores, fracture-coalesce lets you split the work across available parallelism. The proof guarantees you don't lose any violations.
- **GPU workloads.** Each independent block maps to a CUDA thread block or OpenCL workgroup. The coalescence step is a warp-level reduction — essentially free.
- **Distributed checking.** Split blocks across machines, coalesce the masks. Zero coordination needed beyond the final OR.
- **Mixed constraint systems.** Some constraints share dimensions (linked), some don't. Fracture finds the natural parallelism without manual partitioning.
- **Adaptive systems.** When constraints change at runtime, adaptive re-fracture updates the parallelism plan in microseconds.

**See also:** [Error Masks](error-mask.md) — the data structure being coalesced · [Sediment](sediment.md) — corrections applied after coalescence · [GPU Benchmarks](../gpu/index.md) — 20.8B checks/sec with fracture-coalesce · [Getting Started](../getting-started.md)
