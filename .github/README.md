# SuperInstance

Research into exact numeric computing. Floating-point comparison has known failure modes — NaN passes all bounds checks, ULP drift compounds across operations, and quantized bounds introduce false negatives. This org builds tools that sidestep those problems by checking numeric bounds with exact integer arithmetic.

---

## What We Build

The core engine is called **FLUX**. It checks numeric bounds and produces an 8-bit error mask — one bit per constraint, PASS or FAIL with no intermediate states. NaN is trapped explicitly (`v != v` before comparison). The comparison uses IEEE 754 monotonicity, which means the float comparison itself is exact; the bug in traditional approaches is quantizing the *bounds*, not the comparison.

The engine has been implemented in 96 languages (each one chosen to learn what that paradigm forces you to think about) and reaches 654 million checks/sec in C with AVX2. See the [ecosystem repo](https://github.com/SuperInstance/constraint-theory-ecosystem) for the full implementation matrix and benchmarks.

---

## Quick Start

Pick your language:

| Language | Repo | Install |
|----------|------|---------|
| **Python** | [flux-lib-py](https://github.com/SuperInstance/flux-lib-py) | Clone & import |
| **JavaScript** | [flux-check-js](https://github.com/SuperInstance/flux-check-js) | Clone & import |
| **C** | [flux-engine-c](https://github.com/SuperInstance/flux-engine-c) | Single header, no deps |

Full ecosystem → [constraint-theory-ecosystem](https://github.com/SuperInstance/constraint-theory-ecosystem)

---

## The Stack

```
GUARD DSL          Write constraints: "coolant_temp: -40.0 <= x <= 150.0"
    ↓
FLUX Engine        Integer bounds check → u8 error mask (8 constraints, 1 bit each)
    ↓
Fracture-Coalesce  Split independent constraints into parallel blocks
    ↓
Sediment Layers    Append-only correction history (immutable audit trail)
    ↓
Proof Certificate  SHA-256 hash of inputs + results — tamper-evident, formally verified
```

| Component | Repo |
|-----------|------|
| GUARD compiler | [guardc-v3](https://github.com/SuperInstance/guardc-v3) |
| FLUX VM (Rust) | [flux-vm-v3](https://github.com/SuperInstance/flux-vm-v3) |
| Fracture (Rust) | [flux-fracture](https://github.com/SuperInstance/flux-fracture) |
| Documentation | [flux-docs](https://github.com/SuperInstance/flux-docs) |
| CUDA acceleration | [constraint-cuda](https://github.com/SuperInstance/constraint-cuda) |

---

## Language Implementations

96 ports. Each one taught us something. A few highlights:

| Language | Repo | What it taught us |
|----------|------|-------------------|
| COBOL | [flux-cobol](https://github.com/SuperInstance/flux-cobol) | OCCURS is a schema constraint, not a runtime check |
| RPG | [flux-rpg](https://github.com/SuperInstance/flux-rpg) | Bitmask error flags since 1959 — our error mask is RPG's indicator array |
| MUMPS | [flux-mumps](https://github.com/SuperInstance/flux-mumps) | Global persistence is where sediment layers actually live |
| Fortran | [flux-fortran](https://github.com/SuperInstance/flux-fortran) | Packed decimal = exact arithmetic, zero rounding error |
| CUDA | [constraint-cuda](https://github.com/SuperInstance/constraint-cuda) | GPU parallelism for batch constraint evaluation |
| WASM | [constraint-wasm](https://github.com/SuperInstance/constraint-wasm) | Browser-native bounds checking |

The old language repos each explore what that paradigm teaches about constraint processing.

---

## Research

**[constraint-theory-math](https://github.com/SuperInstance/constraint-theory-math)** — The mathematical foundations. Eisenstein integers (complex numbers on a hexagonal lattice) give us exact arithmetic without floating-point. Spectral conservation laws prove that constraint density is bounded.

**[tensor-spline](https://github.com/SuperInstance/tensor-spline)** — Eisenstein lattice weight parameterization. 20× compression at the same accuracy. Built for deploying micro models to NPU/CPU/GPU targets.

**[flux-research](https://github.com/SuperInstance/flux-research)** — Cross-domain connections: thermodynamics, Galois theory, information geometry. The partition function maps directly to constraint satisfaction.

**[flux-papers](https://github.com/SuperInstance/flux-papers)** — Published work and working papers.

---

## Other Projects

| Project | Repo | What |
|---------|------|------|
| PLATO | [plato-training](https://github.com/SuperInstance/plato-training) | Micro models for AI agents — deploy to any hardware |
| Casting Call | [casting-call](https://github.com/SuperInstance/casting-call) | Which model plays which role — fleet-wide capability database |

---

## Who We Are

Built by the **Cocapn fleet** — AI agents working together under human direction. Led by **[Casey Digennaro](https://github.com/caseydt)**.

We ship first and iterate. Open source. Research-driven. Alaska-based.
