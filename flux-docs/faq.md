# FAQ

Common questions about FLUX, answered directly.

---

## General

### What is FLUX?

FLUX is a constraint checking engine. You give it values and bounds, it tells you which values are out of bounds. The results are packed into error masks — one bit per constraint, one byte for 8 constraints. This makes them extremely fast to check, merge, and aggregate.

### What makes FLUX different from `if value < lo or value > hi`?

Three things:
1. **NaN handling.** Standard comparison silently passes NaN. FLUX always catches it. See [NaN Trap](concepts/nan-trap.md).
2. **Parallel checking.** [Fracture-coalesce](concepts/fracture-coalesce.md) splits independent constraints across cores and GPU warps, then merges with a single bitwise OR.
3. **Immutable corrections.** [Sediment layers](concepts/sediment.md) let you add edge-case fixes without changing the hot path.

### How fast is it?

24.9 billion checks per second on a laptop GPU. ~100ns for 8 constraints on CPU in Rust. See [GPU Benchmarks](gpu/index.md).

### What languages are supported?

Python, Rust, JavaScript, C, and 92 others including COBOL, Fortran, MUMPS, and APL. See [96 Languages](languages/index.md).

---

## Error Masks

### Why one bit per constraint?

Because it's the smallest representation that preserves all information. A boolean list of 8 values takes 8×16+ bytes in Python. An error mask takes 1 byte. And bitwise operations (OR, AND, popcount) are single CPU instructions. See [Error Masks](concepts/error-mask.md).

### What if I have more than 8 constraints?

Use `uint64` — 64 constraints in 8 bytes. For more than 64, use arrays of `uint64` and SIMD instructions. The principle doesn't change.

### Can I get more detail than pass/fail?

Yes. Use `check_vector` to get a structured result with `is_nan`, `below_lo`, and `above_hi` fields. See [Python API](api/python.md), [Rust API](api/rust.md), [JavaScript API](api/javascript.md), or [C API](api/c.md).

### What about error messages?

Error masks don't store strings — they're bits for performance. Use `violated_names` on the `CheckResult` to get human-readable names of violated constraints. This keeps the hot path fast and moves human-readable output to where it's needed.

---

## NaN

### Why does NaN always violate?

Because IEEE 754 comparison with NaN always returns false. `NaN < 5` is false, `NaN > 5` is false, so `if value < lo or value > hi` passes NaN silently. FLUX checks `isnan(value)` before the bounds comparison. See [NaN Trap](concepts/nan-trap.md).

### Can I disable the NaN check?

No. It's fundamental to the zero-false-negative guarantee. Every FLUX implementation checks NaN first, always.

### What about Infinity?

`Inf > hi` is `True`, so Infinity is caught by the upper bound check. `-Inf < lo` is `True`, so negative infinity is caught by the lower bound. NaN is the only IEEE 754 special value that sneaks through standard comparisons.

---

## Fracture-Coalesce

### When does fracture help?

When your constraints have independent dimensions. If constraint A checks temperature and constraint B checks pressure, they can run in parallel. Fracture finds these independent groups automatically. If all constraints share dimensions, you get no parallelism — but the overhead is negligible (microseconds).

### Is coalescence really free?

Essentially yes. It's one bitwise OR per block. For 6 blocks, that's 6 OR instructions. On GPU, it's a warp-level reduction using `__ballot_sync()`.

### What's the proof?

Each constraint belongs to exactly one block (connected components partition the set). Bitwise OR sets a bit iff at least one input has that bit set. Therefore every violation appears in the coalesced mask. Zero false negatives. See [Fracture-Coalesce](concepts/fracture-coalesce.md) for the full proof.

---

## Sediment

### Can sediment layers slow down my system?

Minimally. Sediment only re-checks constraints that already violated in the base check (or passed constraints that should have failed). In practice, ~5% overhead on GPU.

### Can I remove a sediment layer?

No — layers are immutable. If a layer was wrong, add a new layer that corrects it. The stack grows, never shrinks. This is the audit trail.

### How many layers can I have?

The stack has a fixed maximum (configurable). When full, the oldest layer is superseded (marked inactive, not deleted). The newest correction always wins.

---

## Thermodynamics

### Is the thermodynamics stuff real or a metaphor?

Both. The partition function factorization is mathematically exact for independent constraints — not an approximation. But the temperature parameter is a metaphor for strictness. You don't need to understand physics to use it. See [Thermodynamics](concepts/thermodynamics.md).

### When would I use soft constraints?

During testing (high temperature = see all violations, nothing is fatal) vs. production (low temperature = strict enforcement). The temperature knob interpolates between these modes without changing any code.

---

## Practical

### How do I save my constraint configuration?

All four main APIs support JSON serialization. See [Serialization](api/python.md) in your language's API docs.

### How do I detect trends before they hit limits?

Use `detect_drift`. It computes rate of change, acceleration, and predicts when a value will hit the bound. See the [Sensor Dashboard Tutorial](tutorials/sensor-dashboard.md) for a complete example.

### Can I use FLUX in a web browser?

Yes. The JavaScript package (`@flux/check`) is pure TypeScript with no dependencies. It runs in Node, browsers, Deno, and Bun.

### Can I use FLUX on a microcontroller?

Yes. The C implementation is a single-header library with no heap allocation in the hot path. The BFS queue is fixed-size. Total working memory for 256 constraints: ~2KB. See [C API](api/c.md).

### Is FLUX production-ready?

FLUX's core operations (bounds check + NaN trap + error mask) are simple enough to verify by inspection. The fracture-coalesce proof guarantees correctness. The hot path has no branches beyond the comparison. It's designed for the kind of reliability that matters — not feature completeness, but mathematical certainty.

### Where do I start?

[Getting Started](getting-started.md). Five minutes, four languages, one byte.

---

**Still have questions?** Check the [concepts](concepts/error-mask.md) or the [API docs](api/python.md) for your language. The [Sensor Dashboard Tutorial](tutorials/sensor-dashboard.md) walks through a complete real project.
