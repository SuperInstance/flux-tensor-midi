# ALGOL 60 Deadband Framework — Design Notes

## What the Language FORCED

### 1. Parallel Arrays Instead of Structs
ALGOL 60 has no `struct`/`record` type. Every multi-valued return must use:
- **Global arrays** (`ESOUT[1:2]`, `HPOUT[1:2]`, `SHEIG[1:2]`)
- **Procedure parameters by reference** (Jensen's device, not used here)

This forces a **flat data design** where coordinates are always (array[1], array[2]), never a named pair. The effect: every operation is **indexable**, which means batch processing is trivially parallel. You can't accidentally couple x and y — they're always separate.

**Back-translation value:** Struct-of-arrays (SoA) layout in Rust/C. Better cache performance for batch operations.

### 2. Nested Procedures Instead of Modules
ALGOL 60 has no module system. Everything is a `PROCEDURE` inside a single `BEGIN`/`END` block. This forces **functional decomposition by scope**:
- Utility procedures (`ROUND`, `MOD360`, `RANDOM`) are defined once at the top level
- Domain procedures reference them naturally via lexical scoping
- Test harness is inline at the bottom of the same block

**Back-translation value:** The nested scope model maps to Rust's module system. Inner procedures that capture outer variables → closures. Pure procedures → `fn` items.

### 3. Stack-Only, Bounded Memory
No heap allocation. Arrays must have **compile-time known bounds** (or bounds computable from `OWN` variables). This means:
- BMA uses fixed `INTEGER ARRAY C[1:32]` — LFSR order capped at 32
- Eisenstein uses fixed `ESOUT[1:2]` — always 2D
- No dynamic list growth, no linked structures

**Back-translation value:** Stack-allocated fixed-size arrays in Rust (`[i32; 32]`). Zero allocation. Predictable memory layout. `const` generics for size parameters.

### 4. No String Type — Pure Mathematical Expression
ALGOL 60 has no meaningful string handling. The `OUTSTRING` calls in the test harness are the only concession. Everything else is pure arithmetic.

This means the framework is **mathematically pure by construction**. No logging, no formatting, no serialization concerns inside the primitives. Those are layered on top.

**Back-translation value:** Separate pure computation from I/O. In Rust: `fn eisenstein_snap(x: f64, y: f64) -> [f64; 2]` with no `fmt` or `io` imports.

## Novel Patterns from Constraints

### The "Output Array" Pattern
Since procedures can't return compound values, every multi-output procedure writes to a global array. This is similar to:
- C's "pass a pointer for the output" pattern
- Fortran's OUT parameters
- Go's multiple return values (but more explicit)

The constraint makes **data flow visible** at every call site. You always know where output goes.

### The "Own Variable RNG" Pattern
The `RANDOM` procedure uses `OWN INTEGER SEED` — ALGOL 60's static variable. The seed persists across calls but is encapsulated inside the procedure. This is a **closure over mutable state**, decades before closures were fashionable.

### The "Integer-as-Boolean" Pattern for GF(2)
ALGOL 60 has `BOOLEAN` but BMA works over GF(2) where values are 0/1 integers. Using `INTEGER` with mod-2 arithmetic (`X - 2 * (X DIV 2)`) is cleaner than converting between `BOOLEAN` and `INTEGER`. The constraint forces you to **think in the field**, not in the language.

### The "Classification Integer" Pattern
Shell decomposition returns `SHGOLDEN = 0/1/2` instead of an enum. This is a **sum type encoded as integer** — a tagged union without the tag infrastructure. The constraint forces a flat encoding that's trivially serializable.

## What Would Be Useful Back-Translated

| ALGOL 60 Pattern | Rust Equivalent | Why It Matters |
|-------------------|-----------------|----------------|
| `ESOUT[1:2]` output arrays | `[f64; 2]` return values | Zero-copy, stack-allocated point types |
| `OWN INTEGER SEED` | `Cell<i64>` in module scope | Encapsulated mutable state |
| Fixed bounds `C[1:32]` | `[u8; 32]` with const generic | No heap, no vec, predictable |
| Integer classification | `enum ShellClass { Generic, Golden, AntiGolden }` | Sum types done right |
| Nested procedures | Closures capturing environment | Clean lexical scoping |
| No string I/O in primitives | Separate `fmt::Display` impls | Purity enforced by type system |
| `PROCEDURE` as only abstraction | Trait methods | Uniform interface |
| `ENTIER` for floor | `f64::floor()` | Standard math |
| `ROUND` as user procedure | `f64::round()` | Built-in in modern languages |

## Key Insight

ALGOL 60's constraints produce code that is:
1. **Automatically stack-safe** — no heap means no fragmentation
2. **Automatically bounded** — fixed arrays mean no unbounded growth
3. **Automatically pure** — no strings means no I/O in math code
4. **Automatically parallelizable** — struct-of-arrays layout

These are the same properties we want in the Deadband Framework's hot path. The language that invented structured programming also enforces structured data.

## Build Notes

- ALGOL 60 has no standard file extension (`.alg` used here)
- Compilers: MARST (ALGOL-to-C translator), `a60` interpreter
- Build with MARST: `marst deadband.alg -o deadband.c && gcc deadband.c -lalgol -lm -o deadband`
- Or use the `a60` interpreter directly: `a60 deadband.alg`
