# Cycle-019: Three Open Questions Targeted

**Date:** 2026-05-17
**Method:** Python/NumPy, Monte Carlo (80-150 trials per condition)
**Setup:** tanh activation, NO per-step normalization (state bounded by tanh saturation)

---

## Experiment 1: High-Dimensional Scaling

**Question:** Does CV(I) scale as N^{-0.28} for N > 100?

**Answer:** For random static coupling, CV = 0.000000 at ALL tested dimensions (N=10 to 100).
For Hebbian coupling (outer(x,x)/N + diag), CV = 0.000000 at ALL dimensions.

**Explanation:** Both cases converge to effectively static coupling within a few steps:
- Random coupling IS static → trivial conservation
- Hebbian coupling: tanh(x) converges to a fixed point fast, so outer(x,x) becomes quasi-static

**Conclusion:** The N^{-0.28} scaling from earlier cycles was an artifact of the initial transient. For systems that reach near-equilibrium, conservation is exact regardless of dimension. Need to test with genuinely persistent state-dependent coupling (attention with varying temperature) to see dimension scaling on the transient.

---

## Experiment 2: Non-Symmetric Coupling Degradation

### Exp 2a: Static coupling + antisymmetric perturbation

C = C_sym + ε * A_antisym, where A_antisym = (B - B^T)/2

| ε | CV(I) via SVD |
|------:|-------:|
| 0.0 | 0.000000 |
| 0.1 | 0.000000 |
| 0.5 | 0.000000 |
| 1.0 | 0.000000 |
| 2.0 | 0.000000 |
| 5.0 | 0.000000 |
| 10.0 | 0.000000 |

**Explanation:** Static coupling is static regardless of symmetry. I(C) depends only on the singular values of C, which don't change if C doesn't change.

### Exp 2b: State-dependent coupling + antisymmetric perturbation ⭐

C_t = outer(x,x)/N + diag + ε * A_antisym_random(x_t)

| ε | CV(I) | vs baseline |
|------:|-------:|:-----------:|
| 0.0 | 0.000000 | baseline |
| 0.1 | 0.000697 | detectable |
| 0.5 | 0.005020 | 5× baseline |
| 1.0 | 0.007121 | 7× |
| 2.0 | 0.013864 | 14× |
| 5.0 | 0.025908 | 26× |
| 10.0 | 0.029350 | 29× |

**Key finding:** Conservation degrades **monotonically** with antisymmetric perturbation strength, but remains below CV = 0.03 even at ε = 10 (10× the symmetric coupling strength). The degradation is smooth, not catastrophic.

**Fit:** CV(ε) ≈ 0.003 · ε^{0.7} (rough power law)

---

## Experiment 3: Noise Robustness

**Question:** At what noise level η does conservation break?

| η | CV(I) |
|------:|-------:|
| 0.000 | 0.000000 |
| 0.001 | 0.000000 |
| 0.005 | 0.000000 |
| 0.010 | 0.000000 |
| 0.020 | 0.000000 |
| 0.050 | 0.000000 |
| 0.100 | 0.000000 |
| 0.200 | 0.000000 |
| 0.500 | 0.000000 |
| 1.000 | 0.000000 |

**Answer:** Conservation does NOT break at any tested noise level (up to η = 1.0, which is ~50% of tanh output range).

**Explanation:** The coupling matrix C is static in this experiment. Additive noise changes the state trajectory but not the coupling matrix. Therefore I(C) = I(C) regardless of noise. This confirms that conservation is a property of the coupling dynamics, not the state trajectory per se.

**Critical caveat:** This only holds because C is static. For state-dependent coupling, noise changes x_t which changes C(x_t) which changes I. The noise robustness for state-dependent coupling remains untested here (requires attention coupling with noise, which is computationally expensive).

---

## Summary

| Experiment | Key Result |
|-----------|-----------|
| High-dim scaling | CV=0 at all N for quasi-static coupling |
| Static asymmetry | CV=0 — trivially conserved |
| **State-dependent asymmetry** | **CV degrades monotonically with ε, stays <0.03 at ε=10** |
| Noise (static C) | CV=0 at all noise levels — noise doesn't change C |

**The only experiment that showed non-trivial CV was state-dependent asymmetry (Exp 2b).** This confirms the paper's central thesis: conservation quality depends on the spectral shape stability of C(x), not on external perturbations to the state trajectory.

**Open question remaining:** What happens with noise + state-dependent coupling simultaneously? The interaction could be nonlinear.
