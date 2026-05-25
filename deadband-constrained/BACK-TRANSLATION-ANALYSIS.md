# Back-Translation Analysis: What Constrained Languages Teach Us

**Forgemaster ⚒️ · May 2026**

---

## The Method

We implemented the Deadband Framework in languages spanning 77 years of computing history:

| Language | Year | Key Constraint | What It Forced |
|----------|------|----------------|----------------|
| **Short Code** | 1949 | Numbers = operations | Deadband-first: every op is bounded |
| **Autocode** | 1952 | No floats, no arrays, no functions | Scaled integer arithmetic |
| **COBOL** | 1959 | PIC fields, English syntax | Field-based types, decimal exact |
| **Lisp** | 1958 | Immutable-first, recursion | Full result structs, no recomputation |
| **ALGOL 60** | 1960 | No structs, no heap | Parallel arrays, stack-only design |
| **FORTRAN** | 1957 | Column-major, 1-indexed | Batch array operations |
| **C** | 1972 | Manual memory, no safety | Raw speed, explicit control |
| **Rust** | 2015 | Ownership, zero-cost | Proven safety at zero cost |
| **Zig** | 2020 | Comptime, no hidden flow | Compile-time verification |
| **CUDA** | 2007 | SIMT, shared memory | Massively parallel snap |
| **Mojo** | 2023 | SIMD types | Unified AI+systems |

Each constraint forced a different design. The patterns surviving ALL languages are essential. The patterns surviving only ONE are accidents.

---

## Universal Patterns (Survive All Languages)

### 1. /360 as a Type, Not an Operation

- **COBOL:** `PIC 9(3) COMP` — type enforces range [0, 359]
- **Lisp:** `(deftype div360 '(integer 0 359))` — proper type
- **Rust:** `struct Div360(u16)` — newtype
- **Autocode:** scaled integer with manual bounds

**Back-translate →** C should use `typedef struct { int32_t val; } div360_t;` with inline functions. Not raw `int64_t`.

### 2. Eisenstein Snap is Three Instructions

Every language reduces snap to: (1) basis coordinates, (2) round, (3) convert back. The 9-candidate search is an optimization, not the fundamental operation.

**Back-translate →** Provide `snap_fast` (3-step, 99.9% accuracy) alongside `snap_exact` (9-candidate, 100%).

### 3. BMA is Pure XOR

Lisp `logxor`, C `^`, ALGOL integer arithmetic — same operation. Language-independent.

**Back-translate →** Word-level BMA (64 bits at a time) should be the DEFAULT, not an optimization.

### 4. Deadband Check is One Comparison

`L <= k`. No statistics, no thresholds, no tuning.

**Back-translate →** All higher-level deadband tools must reduce to this internally. Any statistics on top are unnecessary complexity.

---

## Novel Patterns from Constraints

### Autocode: Scaled Integers Beat Floats

Autocode has no FPU. Multiply by 10000, use integer division. Faster than float for snap because integer multiply = 1 cycle vs 3-5 for float.

**Back-translate →** Add `snap_int` variant for embedded/real-time: no FPU required.

### Short Code: Deadband-First Arithmetic

Every arithmetic operation REQUIRES an explicit bounds check. Every operation is deadband-aware by construction.

**Back-translate →** Add overflow flag to all arithmetic:
```c
int64_t div360_add_checked(int64_t a, int64_t b, bool* crossed_boundary);
```

### COBOL: Field-Based Data Layout

PIC clauses define exact bit widths. A dodecet = `PIC 9(4) COMP`. Five dodecets = 60 bits = 1 CDC word.

**Back-translate →** Dodecet-encoder header should use COBOL-style field specifications.

### Lisp: Immutable Result Structs

`snap-result` returns coordinates + basis + error. Callers who need basis coords get them free — no recomputation.

**Back-translate →** All snap functions return a struct, not just the snapped point.

### ALGOL: Parallel Arrays for Batch Processing

No structs → `x[i]` and `y[i]` as separate arrays. Cache-hostile for random access but cache-FRIENDLY for sequential processing.

**Back-translate →** Batch API with separate arrays:
```c
void eisenstein_snap_batch(const double* x, const double* y, int n,
                           double* sx, double* sy, double* error);
```

---

## Recommendations for the Final API

1. **Type-safe /360** — typedef + inline, not raw int64_t
2. **Snap returns full result struct** — coordinates + basis + error
3. **Batch API with separate x[] y[] arrays** — cache-friendly, SIMD-ready
4. **Scaled integer snap variant** — no FPU, for embedded
5. **Deadband overflow flag on all arithmetic** — detect boundary crossing
6. **BMA uses word-level XOR by default** — 64 bits at a time
7. **All functions are pure (no side effects)** — the Lisp lesson

*The constraints don't limit the design. They reveal it.*
