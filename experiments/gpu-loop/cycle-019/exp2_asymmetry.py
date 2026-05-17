"""
Cycle 19 - Experiment 2: Non-Symmetric Coupling
How does conservation degrade with asymmetry?
C → C + ε·A where A is random antisymmetric, varying ε from 0 to 10.
"""
import numpy as np
import json
import os

np.random.seed(123)
OUT = os.path.dirname(os.path.abspath(__file__))

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

def compute_spectral_info(C, x):
    """Compute spectral gap and entropy for possibly non-symmetric C."""
    # For non-symmetric, use |eigenvalues|
    eigenvalues = np.linalg.eigvals(C)
    real_eigs = np.real(eigenvalues)
    pos_eigs = real_eigs[real_eigs > 1e-12]

    if len(pos_eigs) < 2:
        gamma = 0.0
    else:
        sorted_pos = np.sort(pos_eigs)[::-1]
        gamma = sorted_pos[0] / (sorted_pos[0] + sorted_pos[1])

    abs_x = np.abs(x)
    total = np.sum(abs_x)
    if total < 1e-15:
        H = 0.0
    else:
        p = abs_x / total
        p = p[p > 1e-15]
        H = -np.sum(p * np.log(p))

    return gamma, H

def run_trajectory(C, x0, T=100):
    x = x0.copy()
    I_values = []
    for t in range(T):
        gamma, H = compute_spectral_info(C, x)
        I_values.append(gamma + H)
        y = C @ x
        x = sigmoid(y)
        x = x / (np.linalg.norm(x) + 1e-12)

    I_arr = np.array(I_values)
    mean_I = np.mean(I_arr)
    std_I = np.std(I_arr)
    cv = std_I / mean_I if abs(mean_I) > 1e-12 else float('inf')
    return cv, mean_I, std_I

# Parameters
N = 50
T = 100
n_trials = 500
epsilons = [0.0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]

# Also test multiple coupling base types
base_types = ['random', 'attention', 'hebbian']

results = {}

for base_type in base_types:
    print(f"\n=== Base coupling: {base_type} ===")
    results[base_type] = {}

    for eps in epsilons:
        cvs = []
        means = []

        for trial in range(n_trials):
            x0 = np.random.randn(N)
            x0 = x0 / np.linalg.norm(x0)

            # Create base symmetric coupling
            if base_type == 'random':
                A_sym = np.random.randn(N, N)
                C_base = (A_sym + A_sym.T) / 2.0 / np.sqrt(N)
            elif base_type == 'attention':
                # Fixed attention-like rank-1
                v = np.random.randn(N)
                C_base = np.outer(v, v) / N
            elif base_type == 'hebbian':
                v = np.random.randn(N)
                C_base = np.outer(v, v) / np.sqrt(N)

            # Add antisymmetric perturbation
            if eps > 0:
                B = np.random.randn(N, N)
                A_anti = (B - B.T) / 2.0 / np.sqrt(N)
                C = C_base + eps * A_anti
            else:
                C = C_base

            cv, mean_I, _ = run_trajectory(C, x0, T)
            if not np.isnan(cv) and not np.isinf(cv):
                cvs.append(cv)
                means.append(mean_I)

        results[base_type][eps] = {
            'mean_cv': float(np.mean(cvs)),
            'std_cv': float(np.std(cvs)),
            'median_cv': float(np.median(cvs)),
            'mean_I': float(np.mean(means)),
            'n_trials': len(cvs)
        }
        print(f"  ε={eps:6.2f}: CV={results[base_type][eps]['mean_cv']:.6f} ± {results[base_type][eps]['std_cv']:.6f}")

with open(os.path.join(OUT, 'exp2_asymmetry_results.json'), 'w') as f:
    json.dump(results, f, indent=2)

# Compute degradation rates
print("\n=== Degradation Analysis ===")
for base_type in base_types:
    base_cv = results[base_type][0.0]['mean_cv']
    print(f"\n{base_type} (base CV = {base_cv:.6f}):")
    for eps in epsilons[1:]:
        cv = results[base_type][eps]['mean_cv']
        ratio = cv / base_cv if base_cv > 1e-10 else float('inf')
        print(f"  ε={eps:6.2f}: CV={cv:.6f} ({ratio:.2f}x baseline)")

print("\nDone.")
