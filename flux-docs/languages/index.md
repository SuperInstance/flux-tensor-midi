# The 96-Language Implementation Matrix

The FLUX constraint engine has been implemented across 46+ repositories spanning modern languages, systems languages, embedded targets, and legacy languages dating back to 1957. Every language taught us something.

## What Each Language Taught Us

| Language | Insight |
|----------|---------|
| **Python** | Ergonomics matter. The API should feel obvious. `engine.check(values)` → done. |
| **Rust** | Zero-cost abstractions ARE possible. `flux-fracture` has zero dependencies and runs 100× faster than Python. |
| **JavaScript** | NaN handling is different in every JS engine. Explicit `Number.isNaN()` is non-negotiable. |
| **C** | Single-header libraries still work. `#define FRACTURE_IMPLEMENTATION` + `#include` — that's the whole install. |
| **CUDA** | Error masks are the ideal GPU workload: 1 byte per thread, no divergence, coalesced writes. 24.9B/sec. |
| **Fortran** | Column-major arrays match the constraint×dimension adjacency matrix naturally. Cache-friendly by default. |
| **COBOL** | Fixed-size records (`OCCURS 8 TIMES`) reveal the architecture. No hiding behind `Vec::with_capacity()`. |
| **ALGOL** | Block structure and nested procedures map cleanly to the constraint pipeline. |
| **RPG** | Cycle-driven processing IS batch constraint checking. The language was built for this. |
| **PL/I** | Handles both fixed-point and floating-point in one declaration. The precision class hierarchy was born here. |
| **SNOBOL** | Pattern matching on constraint names. String-driven dispatch. |
| **MUMPS** | Global variable trees as the sediment store. No database needed. MUMPS remembers. |
| **Chapel** | Locales and distributed arrays → multi-node constraint checking. Natural parallelism. |
| **WebAssembly** | Constraint checking in the browser. `@flux/check` compiles to WASM for the edge. |
| **Mojo** | `alias` parameters and compile-time constraint sizing. The type system knows the bounds. |
| **Zig** | `comptime` bounds checking. No runtime cost for fixed constraints. |
| **ESP32** | Constraints on microcontrollers. 8 constraints, ~2KB RAM, sub-millisecond check. |

## The Old-Language Deep Dive

The seven oldest implementations — Fortran (1957), COBOL (1959), RPG (1959), PL/I (1964), ALGOL (1958), SNOBOL (1962), MUMPS (1966) — revealed that the optimal architecture for a constraint engine is:

1. **Fixed-size records** — Constraints are flat arrays of 6 fields. No heap. No indirection.
2. **Linear pipeline** — Validate → Check → Fracture → Coalesce → Sediment → Severity. No branching on type.
3. **In-place mutation** — Set bits, don't allocate. Write to output record, don't return new objects.
4. **Column-major layout** — The dependency matrix matches Fortran's natural iteration order.
5. **Iterative BFS** — No recursion. COBOL can't do recursion. The queue is bounded by the number of constraints.

These aren't limitations of old languages. They're *constraints that reveal the architecture*. Modern languages let you build anything. Old languages only let you build one thing — the right thing.

→ Full deep dive: [Old Language Architecture](old-architecture.md)

## Implementation Repositories

### Core Implementations
| Repo | Language | Status |
|------|----------|--------|
| `flux-lib-py` | Python | Complete |
| `flux-fracture` | Rust | Complete |
| `flux-check-js` | JavaScript/TypeScript | Complete |
| `flux-fracture-c` | C (single header) | Complete |

### GPU
| Repo | What | Peak |
|------|------|------|
| `flux-gpu` | CUDA kernels (RTX 4050) | 24.9B checks/sec |
| `flux-cuda` | CUDA constraint engine | Complete |
| `constraint-cuda` | CUDA experiments | Complete |

### Legacy Languages
| Repo | Language |
|------|----------|
| `flux-fortran` | Fortran 90+ |
| `flux-cobol` | COBOL (GnuCOBOL) |
| `flux-rpg` | RPG/ILE |
| `flux-pli` | PL/I |
| `flux-algol` | ALGOL 60/68 |
| `flux-snobol` | SNOBOL4 |
| `flux-mumps` | MUMPS |

### Specialized
| Repo | Target |
|------|--------|
| `flux-esp32` | ESP32 microcontroller |
| `flux-hdc` | Hyperdimensional computing |
| `flux-chapel` | Multi-node (Chapel) |
| `flux-vm-v3` | 60-opcode stack-based VM |
| `guardc-v3` | GUARD DSL → FLUX-C compiler |
| `flux-isa` | Instruction set architecture |

**Next:** Full old-language architecture analysis → [Old Language Architecture](old-architecture.md)
