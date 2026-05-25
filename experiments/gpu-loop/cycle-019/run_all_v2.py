"""Cycle 19 — Fixed experiments matching paper's methodology."""
import numpy as np
import json
import os
import sys

np.random.seed(42)
OUT = os.path.dirname(os.path.abspath(__file__))
_print = print
def print(*a, **k):
    _print(*a, **k, flush=True)

def compute_I(C):
    """I = spectral_gap(λ1-λ2) + participation_entropy from eigenvalues."""
    eigenvalues = np.linalg.eigvalsh(C)
    pos = eigenvalues[eigenvalues > 1e-10]
    if len(pos) < 2:
        return 0.0
    s = np.sort(pos)[::-1]
    gamma = s[0] - s[1]
    total = np.sum(s)
    p = s / total
    H = -np.sum(p[p > 1e-15] * np.log(p[p > 1e-15]))
    return gamma + H

def compute_I_svd(C):
    """I from singular values (for non-symmetric C)."""
    sv = np.linalg.svd(C, compute_uv=False)
    pos = sv[sv > 1e-10]
    if len(pos) < 2:
        return 0.0
    s = np.sort(pos)[::-1]
    gamma = s[0] - s[1]
    total = np.sum(s)
    p = s / total
    H = -np.sum(p[p > 1e-15] * np.log(p[p > 1e-15]))
    return gamma + H

def trajectory_cv(N, T, coupling_fn, noise_std=0.0, use_svd=False):
    """Run trajectory, return CV of I."""
    x = np.random.randn(N)
    x /= np.linalg.norm(x)
    I_vals = []
    for t in range(T):
        C_t = coupling_fn(x, N)
        if use_svd:
            I_vals.append(compute_I_svd(C_t))
        else:
            I_vals.append(compute_I(C_t))
        y = np.tanh(C_t @ x)
        if noise_std > 0:
            y += np.random.randn(N) * noise_std
        x = y / (np.linalg.norm(y) + 1e-12)
    arr = np.array(I_vals)
    # Skip first 5 steps (transient)
    arr = arr[5:]
    m = np.mean(arr)
    if abs(m) < 1e-12:
        return float('nan'), m
    return float(np.std(arr) / abs(m)), m

# ============================================================
# EXP 1: High-dimensional scaling  
# Paper uses tanh + state-dependent coupling
# ============================================================
print("\n=== EXP 1: High-Dim Scaling ===")
dims = [10, 20, 50, 100, 200]
trials = 100
T = 150

# Random static (baseline — should be CV≈0)
exp1_random = {}
for N in dims:
    cvs = []
    A = np.random.randn(N,N)
    C0 = (A+A.T)/2/np.sqrt(N)
    for _ in range(trials):
        fn = lambda x, n, C=C0: C
        cv, _ = trajectory_cv(N, T, fn)
        if not np.isnan(cv):
            cvs.append(cv)
    exp1_random[str(N)] = {'cv': float(np.mean(cvs)), 'std': float(np.std(cvs))}
    print(f"  random N={N}: CV={np.mean(cvs):.6f}")

# Hebbian: C(x) = outer(x,x)/N + diag regularizer
exp1_hebbian = {}
for N in dims:
    cvs = []
    for _ in range(trials):
        def fn_heb(x, n):
            C = np.outer(x, x) / n + np.eye(n) * 0.01
            return (C + C.T) / 2
        cv, m = trajectory_cv(N, T, fn_heb)
        if not np.isnan(cv) and cv < 10:
            cvs.append(cv)
    exp1_hebbian[str(N)] = {'cv': float(np.mean(cvs)) if cvs else -1, 'std': float(np.std(cvs)) if cvs else 0, 'n_valid': len(cvs)}
    print(f"  hebbian N={N}: CV={np.mean(cvs) if cvs else 'DEGEN':.6f} ({len(cvs)}/{trials} valid)")

# Attention: softmax coupling
exp1_attention = {}
for N in dims:
    cvs = []
    for _ in range(trials):
        def fn_att(x, n):
            scores = np.outer(x, x) / np.sqrt(n)
            scores -= np.max(scores)
            W = np.exp(scores)
            W /= W.sum(axis=1, keepdims=True)
            C = (W + W.T) / 2
            return C + np.eye(n) * 0.01  # regularize
        cv, m = trajectory_cv(N, T, fn_att)
        if not np.isnan(cv) and cv < 10:
            cvs.append(cv)
    exp1_attention[str(N)] = {'cv': float(np.mean(cvs)) if cvs else -1, 'std': float(np.std(cvs)) if cvs else 0, 'n_valid': len(cvs)}
    print(f"  attention N={N}: CV={np.mean(cvs) if cvs else 'DEGEN':.6f} ({len(cvs)}/{trials} valid)")

exp1 = {'random': exp1_random, 'hebbian': exp1_hebbian, 'attention': exp1_attention}
with open(os.path.join(OUT, 'exp1_results.json'), 'w') as f:
    json.dump(exp1, f, indent=2)

# ============================================================
# EXP 2: Non-symmetric coupling  
# C = C_sym + ε * A_antisym
# ============================================================
print("\n=== EXP 2: Asymmetry Degradation ===")
N = 30
epsilons = [0.0, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
exp2 = {}
trials2 = 150

for eps in epsilons:
    cvs_sym = []  # symmetric I (eigvalsh)
    cvs_svd = []  # SVD-based I
    
    # Generate base coupling ONCE for consistency
    A_base = np.random.randn(N,N)
    C_sym = (A_base + A_base.T) / 2 / np.sqrt(N)
    B = np.random.randn(N,N)
    A_anti = (B - B.T) / 2 / np.sqrt(N)
    C_full = C_sym + eps * A_anti
    
    for _ in range(trials2):
        x = np.random.randn(N); x /= np.linalg.norm(x)
        I_sym = []; I_svd = []
        for t in range(T):
            cv_s, m_s = compute_I(C_full), compute_I_svd(C_full)
            I_sym.append(cv_s)
            I_svd.append(cv_s)
            y = np.tanh(C_full @ x)
            x = y / (np.linalg.norm(y) + 1e-12)
        arr_s = np.array(I_sym[5:])
        arr_v = np.array(I_svd[5:])
        ms = np.mean(arr_s)
        mv = np.mean(arr_v)
        if abs(ms) > 1e-12:
            cvs_sym.append(float(np.std(arr_s)/abs(ms)))
        if abs(mv) > 1e-12:
            cvs_svd.append(float(np.std(arr_v)/abs(mv)))
    
    exp2[str(eps)] = {
        'epsilon': eps,
        'cv_eigenvalue': float(np.mean(cvs_sym)) if cvs_sym else -1,
        'cv_svd': float(np.mean(cvs_svd)) if cvs_svd else -1,
        'n_trials': len(cvs_sym)
    }
    print(f"  ε={eps:.2f}: CV_eig={exp2[str(eps)]['cv_eigenvalue']:.6f} CV_svd={exp2[str(eps)]['cv_svd']:.6f}")

with open(os.path.join(OUT, 'exp2_results.json'), 'w') as f:
    json.dump(exp2, f, indent=2)

# ============================================================
# EXP 3: Noise robustness
# ============================================================
print("\n=== EXP 3: Noise Robustness ===")
N = 30
noise_levels = [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
exp3 = {}
trials3 = 150
A_base = np.random.randn(N,N)
C0 = (A_base + A_base.T) / 2 / np.sqrt(N)

for noise_std in noise_levels:
    cvs = []
    for _ in range(trials3):
        fn = lambda x, n, C=C0: C
        cv, m = trajectory_cv(N, T, fn, noise_std)
        if not np.isnan(cv):
            cvs.append(cv)
    exp3[str(noise_std)] = {
        'noise_std': noise_std,
        'cv_mean': float(np.mean(cvs)),
        'cv_std': float(np.std(cvs)),
        'cv_median': float(np.median(cvs)),
        'n_trials': len(cvs)
    }
    print(f"  η={noise_std:.3f}: CV={exp3[str(noise_std)]['cv_mean']:.6f} ± {exp3[str(noise_std)]['cv_std']:.6f}")

with open(os.path.join(OUT, 'exp3_results.json'), 'w') as f:
    json.dump(exp3, f, indent=2)

# ============================================================
# Summary
# ============================================================
print("\n=== CYCLE 19 SUMMARY ===")
print("Exp 1: High-dim scaling across random/hebbian/attention coupling")
print("Exp 2: Asymmetry degradation via antisymmetric perturbation")
print("Exp 3: Noise robustness — additive Gaussian noise")

# Find noise breaking point
base_cv = exp3['0.0']['cv_mean']
for ns in noise_levels:
    if exp3[str(ns)]['cv_mean'] > 2 * base_cv + 0.01:
        print(f"Noise break point: η={ns} (2× baseline threshold)")
        break
else:
    print(f"Noise: no breaking point found (tested up to η=1.0)")

# Fit dim scaling
print("\nDim scaling (random):")
for N in dims:
    cv = exp1_random[str(N)]['cv']
    print(f"  N={N}: CV={cv:.6f}")

print("\nDone!")
