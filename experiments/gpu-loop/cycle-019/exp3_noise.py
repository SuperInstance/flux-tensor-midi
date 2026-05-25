"""
Cycle 19 - Experiment 3: Noise Robustness
x_{t+1} = σ(C(x_t)·x_t) + η_t
At what noise level does conservation break?
"""
import numpy as np
import json
import os

np.random.seed(456)
OUT = os.path.dirname(os.path.abspath(__file__))

def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))

def compute_spectral_info(C, x):
    eigenvalues = np.linalg.eigvalsh(C)
    pos_eigs = eigenvalues[eigenvalues > 1e-12]
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

def run_trajectory_noisy(C, x0, T=100, noise_std=0.0, coupling_type='fixed', N=50):
    x = x0.copy()
    I_values = []

    for t in range(T):
        # State-dependent coupling
        if coupling_type == 'attention':
            v = x
            C_t = np.outer(v, v) / N
        elif coupling_type == 'hebbian':
            C_t = np.outer(x, x) / np.sqrt(N)
        else:
            C_t = C  # fixed

        gamma, H = compute_spectral_info(C_t, x)
        I_values.append(gamma + H)

        y = C_t @ x
        x = sigmoid(y)

        # Add noise
        if noise_std > 0:
            eta = np.random.randn(N) * noise_std
            x = x + eta

        # Renormalize
        x = x / (np.linalg.norm(x) + 1e-12)

    I_arr = np.array(I_values)
    mean_I = np.mean(I_arr)
    std_I = np.std(I_arr)
    cv = std_I / mean_I if abs(mean_I) > 1e-12 else float('inf')
    return cv, mean_I, std_I, I_values

# Parameters
N = 50
T = 150
n_trials = 500
noise_levels = [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
coupling_types = ['fixed_random', 'attention', 'hebbian']

results = {}

for ctype in coupling_types:
    print(f"\n=== Coupling: {ctype} ===")
    results[ctype] = {}

    for noise_std in noise_levels:
        cvs = []
        means = []
        sample_trajectories = []

        for trial in range(n_trials):
            x0 = np.random.randn(N)
            x0 = x0 / np.linalg.norm(x0)

            if ctype == 'fixed_random':
                A = np.random.randn(N, N)
                C = (A + A.T) / 2.0 / np.sqrt(N)
                cv, mean_I, _, I_vals = run_trajectory_noisy(C, x0, T, noise_std, 'fixed', N)
            else:
                cv, mean_I, _, I_vals = run_trajectory_noisy(None, x0, T, noise_std, ctype, N)

            if not np.isnan(cv) and not np.isinf(cv):
                cvs.append(cv)
                means.append(mean_I)
                if len(sample_trajectories) < 5:
                    sample_trajectories.append([float(v) for v in I_vals[:20]])

        results[ctype][noise_std] = {
            'mean_cv': float(np.mean(cvs)),
            'std_cv': float(np.std(cvs)),
            'median_cv': float(np.median(cvs)),
            'mean_I': float(np.mean(means)),
            'n_trials': len(cvs)
        }
        print(f"  noise_std={noise_std:.3f}: CV={results[ctype][noise_std]['mean_cv']:.6f} ± {results[ctype][noise_std]['std_cv']:.6f}")

with open(os.path.join(OUT, 'exp3_noise_results.json'), 'w') as f:
    json.dump(results, f, indent=2)

# Find breaking point: first noise level where CV exceeds 2x baseline
print("\n=== Breaking Point Analysis ===")
for ctype in coupling_types:
    base_cv = results[ctype][0.0]['mean_cv']
    threshold = base_cv * 2.0
    breaking_point = None
    for noise_std in noise_levels:
        if results[ctype][noise_std]['mean_cv'] > threshold:
            breaking_point = noise_std
            break
    print(f"{ctype}: base CV={base_cv:.6f}, breaks at noise_std={breaking_point} (2x threshold)")

print("\nDone.")
