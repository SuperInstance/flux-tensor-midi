# Experiment: ε-Sweep Across Living Modules

**Date:** 2026-05-23  
**Modules tested:** MusicalCell, GeneRegulatoryNetwork, MusicalEmbryo, MusicalImmuneSystem  
**Method:** Inject ε-controlled Gaussian noise into module parameters/inputs, sweep ε from 0.0 to 1.0, measure diversity and compression across 5 trials per point.

## Key Findings

### MusicalCell
- **Peak diversity** at ε=0.8 (div=21.33)
- **Most structured** at ε=0.0 (comp=0.052) — deterministic baseline is highly compressible
- **Emergence:** Compression jumps at ε=0.1 — even small noise dramatically changes output structure
- Diversity is broadly non-monotonic; doesn't simply increase with noise

### GeneRegulatoryNetwork
- **Peak diversity** at ε=0.7 (div=14.96)
- **Most structured** at ε=0.4 (comp=0.133)
- **Emergence:** Diversity jumps at ε=0.6–0.7, compression jumps at ε=0.5
- The GRN shows genuine phase-transition behavior around ε≈0.5–0.7
- This is the most interesting module from an emergence standpoint — regulatory networks have critical noise thresholds

### MusicalEmbryo
- **Peak diversity** at ε=0.4 (div=13.12)
- **Most structured** at ε=0.3 (comp=0.0135) — extremely compressible (lots of repetition in development stages)
- **Emergence:** Diversity jump at ε=0.3, compression jumps at ε=0.7–0.8
- Development is robust to noise up to ~ε=0.3, then differentiation patterns shift

### MusicalImmuneSystem
- **Peak diversity** at ε=0.3 (div=7.79)
- **Most structured** at ε=0.0 (comp=0.047)
- **Emergence:** Diversity jumps at ε=0.1 and ε=0.9 — bookend transitions
- Immune system is highly sensitive to even tiny noise (ε=0.1 causes big diversity jump)
- At ε=0.0, all trials produce identical output (zero diversity — deterministic)

## Cross-Module Patterns

1. **Sweet spot is ε≈0.3–0.8** for maximum diversity across all modules
2. **Emergence is real** — several modules show non-monotonic behavior with sudden jumps
3. **GRN is the most emergent** — clear phase transition around ε=0.5–0.7
4. **Immune system is most noise-sensitive** — even ε=0.1 dramatically changes behavior
5. **Structure (compression) and diversity are somewhat anticorrelated** but not perfectly — there are interesting trade-off regions

## Implications for Music Generation

- For **creative/exploratory** generation: ε≈0.4–0.7 gives best diversity without losing all structure
- For **stable/consistent** generation: ε≈0.1–0.2 provides gentle variation
- The GRN's phase transition at ε≈0.5 could be exploited for "genre-switching" behavior
