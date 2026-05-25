# FLUX Constraint Engine

**FLUX is a zero-false-negative constraint checking engine that packs results into single-byte error masks, splits independent constraints across CPU cores and GPU warps, and corrects edge cases through immutable sediment layers — all provably correct.**

Three ideas, one system:

1. **Error masks** — One bit per constraint. Eight constraints fit in one byte. No arrays, no booleans, no heap. The bit *is* the answer.
2. **Fracture-coalesce** — Independent constraints split into parallel blocks. Bitwise OR merges results with a proof of zero information loss.
3. **Sediment** — Every edge-case fix is an immutable layer. Correctness only grows. Nothing is deleted, only superseded.

The result: **24.9 billion checks per second on a laptop GPU**, zero false negatives, implementations in 96 languages from Python to COBOL.

---

## Read This Next

**New here? Start here:**

1. [**Getting Started**](getting-started.md) — Check 8 values against 8 bounds in 5 minutes, in any language.
2. [**Error Masks**](concepts/error-mask.md) — The data structure that makes everything else possible.
3. [**NaN Trap**](concepts/nan-trap.md) — The bug that started the whole project.
4. [**Fracture-Coalesce**](concepts/fracture-coalesce.md) — How we get 8× parallelism for free.
5. [**Sediment**](concepts/sediment.md) — Why correctness only goes up.
6. [**Thermodynamics**](concepts/thermodynamics.md) — What physics has to do with it.

**Going deeper:**

7. [**96 Languages**](languages/index.md) — What each language taught us about the architecture.
8. [**Old Language Architecture**](languages/old-architecture.md) — Why COBOL reveals the optimal shape.
9. [**GPU Benchmarks**](gpu/index.md) — 24.9B checks/sec and why error masks are the ideal GPU workload.

**API references:** [Python](api/python.md) · [Rust](api/rust.md) · [JavaScript](api/javascript.md) · [C](api/c.md)

**Tutorials:** [Building a Sensor Dashboard](tutorials/sensor-dashboard.md) — complete real project walkthrough

**FAQ:** [Frequently Asked Questions](faq.md) — common questions answered directly

**Research:** [31 Modules](research/index.md) · [Grand Synthesis](research/grand-synthesis.md)

---

## Background You Don't Need

Some repos in this ecosystem mention **Eisenstein integers**, **hex arithmetic**, and **sheaf cohomology**. You might run into these terms and wonder if you need a math degree to use FLUX.

**You don't.**

FLUX checks whether values are within bounds and packs the results into bits. That's it. The five-minute tutorial above works with zero math beyond basic comparison.

The deeper mathematics — Eisenstein integers (a hexagonal lattice structure), sheaf cohomology (a way to check if distributed systems agree), thermodynamic analogies — exists in the [research modules](research/index.md) for people who want to understand *why* the architecture is what it is. It's depth for the curious, not a prerequisite for the practical.

If you just want to check bounds in your code, start with [Getting Started](getting-started.md). The math will still be here when you want it.
