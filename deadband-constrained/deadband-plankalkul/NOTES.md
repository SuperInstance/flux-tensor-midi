# Deadband Framework — Plankalkül Notes

**Author:** Forgemaster ⚒️  
**Date:** 2026-05-18  
**Language:** Plankalkül (Konrad Zuse, 1945)

---

## What Plankalkül's Bit-Level Operations Reveal About BMA

Plankalkül exposes computation at the **bit level**. When we write BMA (Bounded Modular Arithmetic) in Plankalkül, the ripple-carry adder becomes explicit:

```
| V0.1 ⊻ V1.1 → Z0.1       [sum = XOR]
| V0.1 ∧ V1.1 → C           [carry = AND]
```

This isn't just notation — it's **ontological**. BMA is fundamentally a bit-level operation, and Plankalkül makes that inescapable. Every `+` in modern code hides this:

1. **The carry chain** — modular addition isn't O(1), it's O(log n) in carry propagation depth
2. **The boundary at 360** — 360 = 101101000₂, an arbitrary boundary that requires explicit comparison
3. **The wrap-around** — modular reduction via complement-and-add is itself another BMA operation

In C or Rust, `((a + b) % 360)` looks atomic. In Plankalkül, you see it's **recursive** — the subtraction inside the mod is itself addition with a complement. The operation is turtles all the way down.

**Insight:** BMA's cost structure is hidden by modern languages. Plankalkül reveals that modular arithmetic is *not* a primitive — it's a derived operation built on bit manipulation. This matters for hardware implementation of deadband systems: the "simple" deadband check actually requires a full adder chain + comparator.

---

## How Plankalkül's Structured Variables Anticipate Modern Struct Types

Plankalkül's component notation (`V0[1]`, `V0[2]`) is **records before records existed**:

```
| V0[1] → shell_number
| V0[2] → eigenvalue_angle
| V0[3] → importance_flag
```

This is:
- **1945:** Zuse designs structured data with named components
- **1970:** Wirth's Pascal formalizes this as `RECORD`
- **1972:** C picks it up as `struct`
- **2010:** Go returns to this simplicity
- **2026:** Rust's `struct` is the same thing with borrow checking

The deadband framework's `ShellResult` — a struct with (shell, eigenvalue, importance) — was *possible to express* in 1945. The abstraction wasn't discovered later; it was there from the beginning. What changed was hardware catching up to make structured access efficient.

**Key observation:** Our `SnapResult` type (angle + hex_vertex + in_hexagon) maps *directly* to Plankalkül's structured result variables. The type system Zuse designed would have caught our bugs at "compile time" (had there been a compiler). Modern languages added nothing fundamental here — they just made it run.

---

## What the 1945 Perspective Adds to Our 2026 Framework

### 1. Modularity Was Always the Answer
Zuse designed plans (R0, R1...) as reusable components. Our deadband framework does the same thing with Rust traits. The pattern — decompose, compose, abstract — is identical. 80 years of "progress" and we're still doing what Zuse described.

### 2. Bit-Level Awareness Is Coming Back
Plankalkül forces bit-level thinking. Modern systems are rediscovering this with:
- Bit manipulation for SIMD deadband checks
- Packed representations for NPUs (our PLATO micro models)
- Boolean arrays for hexagon membership (Pascal's `PACKED ARRAY OF BOOLEAN`)

The 1945 perspective reminds us: **bits are the real machine**. Everything else is abstraction overhead.

### 3. No Recursion → No Stack Overflow
Plankalkül has no recursion. Our Fibonacci-spline search in Plankalkül is purely iterative (Wiederholungsplan). This is actually a *constraint that improves reliability*:
- No stack overflow possible
- Bounded execution time
- Suitable for embedded/NPU deployment

The deadband framework's constraint-theory approach — where constraints make systems *better* — was prefigured by Plankalkül's *lack* of recursion.

### 4. The Deadband Is in the Types
Plankalkül's type system (`S1 = (0..359)`) is a **range constraint**. In 2026 terms, it's a dependent type or a refined type. The deadband check (`R5`) is checking whether a value stays within a type's range. If the type system were expressive enough, the deadband would be *automatic* — verified at "compile time" by the type checker.

This is exactly what Pascal's subrange types achieve (see the Pascal implementation). Plankalkül got there first.

### 5. History Rhymes
- 1945: Zuse designs Plankalkül on paper, no compiler exists
- 1970: Wirth implements the same ideas in Pascal
- 2026: We implement deadband arithmetic using the same patterns

The 80-year gap between Zuse's design and our implementation is mostly hardware evolution. The *ideas* were ready. The silicon wasn't.

---

*"The glitches ARE the research agenda. The gaps ARE the work."* — I2I Protocol
