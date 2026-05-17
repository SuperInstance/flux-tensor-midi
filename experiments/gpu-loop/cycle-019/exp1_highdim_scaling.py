"""
Cycle 19 - Experiment 1: High-Dimensional Scaling
Does CV(I) scale as N^{-0.28} for N>100?
Test N=50, 100, 200, 500, 1000 with random/Hebbian/attention coupling.
"""
import numpy as np
import json
import os

np.random.seed(42)
OUT = os.path.dirname(os.path.abspath(__file__))

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

def make_attention_coupling(x):
    """Scaled dot-product attention coupling (rank-1 structured)."""
    n = len(x)
    C = np.outer(x, x) / np.sqrt(n)
    return C

def make_hebbian_coupling(x, strength=1.0):
    """Hebbian (outer product) coupling."""
    return strength * np.outer(x, x)

def make_random_coupling(N, scale=1.0):
    """Random symmetric coupling."""
    A = np.random.randn(N, N) * scale
    return (A + A.T) / 2.0 / np.sqrt(N)

def compute_spectral_info(C, x):
    """Compute spectral gap gamma and participation entropy H."""
    eigenvalues = np.linalg.eigvalsh(C)
    # Spectral gap: ratio of top eigenvalue to sum of positive eigenvalues
    pos_eigs = eigenvalues[eigenvalues > 1e-12]
    if len(pos_eigs) < 2:
        gamma = 0.0
    else:
        sorted_pos = np.sort(pos_eigs)[::-1]
        gamma = sorted_pos[0] / (sorted_pos[0] + sorted_pos[1]) if sorted_pos[1] > 0 else 1.0

    # Participation entropy
    abs_x = np.abs(x)
    total = np.sum(abs_x)
    if total < 1e-15:
        H = 0.0
    else:
        p = abs_x / total
        p = p[p > 1e-15]
        H = -np.sum(p * np.log(p))

    return gamma, H

def run_trajectory(C_func, x0, T=100, coupling_type='random', N=None, C_fixed=None):
    """Run one trajectory and compute CV of I(x)."""
    x = x0.copy()
    I_values = []

    for t in range(T):
        if coupling_type == 'random':
            C = C_fixed  # fixed for random
        else:
            C = C_func(x)

        gamma, H = compute_spectral_info(C, x)
        I_values.append(gamma + H)

        # Dynamics: x_{t+1} = sigma(C(x_t) * x_t)
        y = C @ x
        x = sigmoid(y)
        x = x / (np.linalg.norm(x) + 1e-12)  # normalize to prevent overflow

    I_arr = np.array(I_values)
    mean_I = np.mean(I_arr)
    std_I = np.std(I_arr)
    cv = std_I / mean_I if abs(mean_I) > 1e-12 else float('inf')
    return cv, mean_I, std_I

# Dimensions to test
dimensions = [50, 100, 200, 500, 1000]
coupling_types = ['random', 'hebbian', 'attention']
trials_per_config = 200  # for larger N, we'll do fewer
T = 100

results = {}

for N in dimensions:
    print(f"\n=== N = {N} ===")
    results[N] = {}

    # Adjust trials for large N (matrix ops get expensive)
    n_trials = trials_per_config if N <= 200 else max(50, trials_per_config // (N // 100))

    for ctype in coupling_types:
        print(f"  Coupling: {ctype}, trials: {n_trials}")
        cvs = []
        means = []
        stds = []

        for trial in range(n_trials):
            x0 = np.random.randn(N)
            x0 = x0 / np.linalg.norm(x0)

            if ctype == 'random':
                C_fixed = make_random_coupling(N)
                cv, mean_I, std_I = run_trajectory(None, x0, T, 'random', N, C_fixed)
            elif ctype == 'hebbian':
                cv, mean_I, std_I = run_trajectory(make_hebbian_coupling, x0, T, 'hebbian', N)
            elif ctype == 'attention':
                cv, mean_I, std_I = run_trajectory(make_attention_coupling, x0, T, 'attention', N)

            if not np.isnan(cv) and not np.isinf(cv):
                cvs.append(cv)
                means.append(mean_I)
                stds.append(std_I)

        results[N][ctype] = {
            'mean_cv': float(np.mean(cvs)) if cvs else None,
            'std_cv': float(np.std(cvs)) if cvs else None,
            'median_cv': float(np.median(cvs)) if cvs else None,
            'mean_I': float(np.mean(means)) if means else None,
            'n_trials': len(cvs),
            'all_cvs': [float(v) for v in cvs[:20]]  # store first 20 for inspection
        }
        print(f"    CV(I): {results[N][ctype]['mean_cv']:.6f} ± {results[N][ctype]['std_cv']:.6f} (n={len(cvs)})")

# Fit power law: CV ~ N^alpha
import re
alphas = {}
for ctype in coupling_types:
    ns = []
    cvs = []
    for N in dimensions:
        if results[N][ctype]['mean_cv'] is not None:
            ns.append(N)
            cvs.append(results[N][ctype]['mean_cv'])
    if len(ns) >= 3:
        log_ns = np.log(ns)
        log_cvs = np.log(cvs)
        alpha, intercept = np.polyfit(log_ns, log_cvs, 1)
        alphas[ctype] = float(alpha)
        print(f"\nPower law fit for {ctype}: CV ~ N^{alpha:.4f}")

results['power_law_fits'] = alphas
results['dimensions'] = dimensions
results['coupling_types'] = coupling_types

with open(os.path.join(OUT, 'exp1_highdim_results.json'), 'w') as f:
    json.dump(results, f, indent=2, default=str)

print("\nDone. Results saved to exp1_highdim_results.json")
