# Flux Docs — What the Constraint Engine Is and How to Navigate It

This is the documentation site for the Flux Constraint Engine — a system for validating bounded constraints with fracture-coalesce parallelism, accumulated sediment layers, and thermodynamic formalism. Start here, then follow the reading order.

## What's In This Repo

### Start Here

| Page | What You'll Learn |
|------|-------------------|
| [Index](index.md) | What is FLUX? Why constraint engines? The 60-second pitch. |
| [Getting Started](getting-started.md) | 5-minute tutorial in Python, Rust, JavaScript, and C. Run your first constraint check. |

### Core Concepts (Read in Order)

| Page | What You'll Learn |
|------|-------------------|
| [Error Masks](concepts/error-mask.md) | 1 bit per constraint. The fundamental data structure. Why 8 constraints fit in 1 byte. |
| [NaN Trap](concepts/nan-trap.md) | IEEE 754's dirty secret: NaN always violates. Every language hits this. How we handle it. |
| [Fracture-Coalesce](concepts/fracture-coalesce.md) | Independent constraints → parallel blocks → bitwise OR merge. Zero false negatives, provable. |
| [Sediment](concepts/sediment.md) | Immutable correction layers. Correctness only grows. The geological metaphor made precise. |
| [Thermodynamics](concepts/thermodynamics.md) | Constraints as ideal gases. The partition function factorizes. Why the math works. |

### Language Implementations

| Page | What You'll Learn |
|------|-------------------|
| [96 Languages](languages/index.md) | What each language taught us about the constraint engine's architecture. |
| [Old Architecture](languages/old-architecture.md) | Why implementing in COBOL, RPG, PL/I, ALGOL, SNOBOL4, and MUMPS revealed the optimal shape. |

The six old-language repos each teach a specific lesson:

- **flux-cobol** — Fixed-format records force you to design data before logic. OCCURS is a schema constraint.
- **flux-rpg** — The cycle model (read → check → write) IS the hot path. Indicators are error mask bits.
- **flux-pli** — Native `BIT(8)` type. The error mask isn't simulated — it's a language primitive.
- **flux-algol** — `own` variables are sediment. Parallel arrays are columnar storage. The ancestor of everything.
- **flux-snobol** — Pattern match success/failure IS constraint pass/fail. The Maybe monad before monads.
- **flux-mumps** — Globals persist across sessions. MUMPS is where sediment actually lives. COBOL computes, MUMPS remembers.

### GPU

| Page | What You'll Learn |
|------|-------------------|
| [GPU Benchmarks](gpu/index.md) | 24.9B checks/sec. Why error masks are the ideal GPU workload. |

### API Reference

| Page | What You'll Learn |
|------|-------------------|
| [Python](api/python.md) | `flux-lib` — `pip install flux-lib` |
| [Rust](api/rust.md) | `flux-fracture` — `cargo add flux-fracture` |
| [JavaScript](api/javascript.md) | `@flux/check` — `npm install @flux/check` |
| [C](api/c.md) | `flux_fracture.h` — single-header, no dependencies |

### Tutorials

| Page | What You'll Learn |
|------|-------------------|
| [Sensor Dashboard](tutorials/sensor-dashboard.md) | Build a complete 8-sensor monitoring system: batch validation, drift detection, sediment, save/load config. |

### FAQ

| Page | What You'll Find |
|------|------------------|
| [FAQ](faq.md) | Common questions about error masks, NaN, fracture-coalesce, sediment, thermodynamics, and practical usage. |

### Research

| Page | What You'll Learn |
|------|-------------------|
| [31 Modules](research/index.md) | What we asked, what died, what survived, what's new. The experimental record. |
| [Grand Synthesis](research/grand-synthesis.md) | Full analysis: 7 agents, 4 models, 2 rounds. What the data says. |

## Reading Order

1. **Start**: [Index](index.md) → [Getting Started](getting-started.md)
2. **Tutorial**: [Sensor Dashboard](tutorials/sensor-dashboard.md)
3. **Core concepts**: [Error Masks](concepts/error-mask.md) → [NaN Trap](concepts/nan-trap.md) → [Fracture-Coalesce](concepts/fracture-coalesce.md)
4. **Deeper theory**: [Sediment](concepts/sediment.md) → [Thermodynamics](concepts/thermodynamics.md)
5. **Language insights**: [96 Languages](languages/index.md) → [Old Architecture](languages/old-architecture.md)
6. **Performance**: [GPU Benchmarks](gpu/index.md)
7. **Integration**: API for your language
8. **Full picture**: [Research](research/index.md) → [Grand Synthesis](research/grand-synthesis.md)
9. **Questions**: [FAQ](faq.md)

## Build

```bash
# Serve raw markdown locally
cd flux-docs
python3 -m http.server 8080

# Or convert to HTML
make html
```

## License

MIT — Part of the [SuperInstance](https://github.com/SuperInstance) constraint-theory ecosystem.
