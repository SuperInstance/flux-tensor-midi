"""Cycle 19 — NO per-step normalization, matching paper methodology."""
import numpy as np
import json, os, sys

np.random.seed(42)
OUT = os.path.dirname(os.path.abspath(__file__))
_print = print
def print(*a, **k): _print(*a, **k, flush=True)

def compute_I(C):
    eigenvalues = np.linalg.eigvalsh(C)
    pos = eigenvalues[eigenvalues > 1e-10]
    if len(pos) < 2: return 0.0
    s = np.sort(pos)[::-1]
    gamma = s[0] - s[1]
    total = np.sum(s)
    p = s / total
    H = -np.sum(p[p > 1e-15] * np.log(p[p > 1e-15]))
    return gamma + H

def compute_I_svd(C):
    sv = np.linalg.svd(C, compute_uv=False)
    pos = sv[sv > 1e-10]
    if len(pos) < 2: return 0.0
    s = np.sort(pos)[::-1]
    gamma = s[0] - s[1]
    total = np.sum(s)
    p = s / total
    H = -np.sum(p[p > 1e-15] * np.log(p[p > 1e-15]))
    return gamma + H

def run_traj(N, T, coupling_fn, noise_std=0.0, use_svd=False):
    """Run WITHOUT per-step normalization — tanh naturally bounds state."""
    x = np.random.randn(N) * 0.5  # moderate init
    I_vals = []
    for t in range(T):
        C_t = coupling_fn(x, N)
        I_vals.append(compute_I_svd(C_t) if use_svd else compute_I(C_t))
        y = np.tanh(C_t @ x)
        if noise_std > 0:
            y += np.random.randn(N) * noise_std
        x = y
    arr = np.array(I_vals[5:])
    m = np.mean(arr)
    return float(np.std(arr)/abs(m)) if abs(m) > 1e-12 else float('nan')

# ============================================================
# EXP 1: High-dim scaling
# ============================================================
print("=== EXP 1: High-Dim Scaling (no normalization) ===")
dims = [10, 20, 50, 100]
T = 150
trials = 80

for coupling in ['random', 'hebbian']:
    exp1 = {}
    for N in dims:
        cvs = []
        for trial in range(trials):
            if coupling == 'random':
                A = np.random.randn(N,N)
                C0 = (A+A.T)/2/np.sqrt(N)
                fn = lambda x, n, C=C0: C
            else:
                def fn(x, n):
                    C = np.outer(x,x)/n + np.eye(n)*0.1
                    return (C+C.T)/2
            cv = run_traj(N, T, fn)
            if not np.isnan(cv): cvs.append(cv)
        exp1[str(N)] = {'cv_mean': float(np.mean(cvs)), 'cv_std': float(np.std(cvs)), 'n': len(cvs)}
        print(f"  {coupling} N={N}: CV={np.mean(cvs):.6f} ± {np.std(cvs):.6f}")
    
    with open(os.path.join(OUT, f'exp1_{coupling}_results.json'), 'w') as f:
        json.dump(exp1, f, indent=2)

# ============================================================
# EXP 2: Asymmetry degradation
# ============================================================
print("\n=== EXP 2: Asymmetry ===")
N = 20
epsilons = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
exp2 = {}
trials2 = 100

for eps in epsilons:
    cvs = []
    A_base = np.random.randn(N,N)
    C_sym = (A_base+A_base.T)/2/np.sqrt(N)
    B = np.random.randn(N,N)
    A_anti = (B-B.T)/2/np.sqrt(N)
    C_full = C_sym + eps * A_anti
    
    for _ in range(trials2):
        x = np.random.randn(N) * 0.5
        I_vals = []
        for t in range(T):
            I_vals.append(compute_I_svd(C_full))
            y = np.tanh(C_full @ x)
            x = y
        arr = np.array(I_vals[5:])
        m = np.mean(arr)
        if abs(m) > 1e-12: cvs.append(float(np.std(arr)/abs(m)))
    
    exp2[str(eps)] = {'cv': float(np.mean(cvs)), 'std': float(np.std(cvs)), 'n': len(cvs)}
    print(f"  ε={eps:.1f}: CV={exp2[str(eps)]['cv']:.6f}")

with open(os.path.join(OUT, 'exp2_results.json'), 'w') as f:
    json.dump(exp2, f, indent=2)

# ============================================================
# EXP 3: Noise robustness  
# ============================================================
print("\n=== EXP 3: Noise Robustness ===")
N = 20
noise_levels = [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
exp3 = {}
trials3 = 100
A_base = np.random.randn(N,N)
C0 = (A_base+A_base.T)/2/np.sqrt(N)

for noise_std in noise_levels:
    cvs = []
    for _ in range(trials3):
        fn = lambda x, n, C=C0: C
        cv = run_traj(N, T, fn, noise_std)
        if not np.isnan(cv): cvs.append(cv)
    exp3[str(noise_std)] = {
        'cv': float(np.mean(cvs)),
        'std': float(np.std(cvs)),
        'n': len(cvs)
    }
    print(f"  η={noise_std:.3f}: CV={exp3[str(noise_std)]['cv']:.6f} ± {exp3[str(noise_std)]['std']:.6f}")

with open(os.path.join(OUT, 'exp3_results.json'), 'w') as f:
    json.dump(exp3, f, indent=2)

# ============================================================
# Exp 2b: STATE-DEPENDENT asymmetry
# ============================================================
print("\n=== EXP 2b: State-Dependent Asymmetry ===")
N = 20
exp2b = {}

for eps in epsilons:
    cvs = []
    for _ in range(trials2):
        x = np.random.randn(N) * 0.5
        I_vals = []
        for t in range(T):
            C_base = np.outer(x,x)/N + np.eye(N)*0.1
            C_base = (C_base+C_base.T)/2
            B_t = np.random.randn(N,N)
            A_anti = (B_t-B_t.T)/2/np.sqrt(N)
            C_full = C_base + eps * A_anti
            I_vals.append(compute_I_svd(C_full))
            y = np.tanh(C_full @ x)
            x = y
        arr = np.array(I_vals[5:])
        m = np.mean(arr)
        if abs(m) > 1e-12: cvs.append(float(np.std(arr)/abs(m)))
    
    exp2b[str(eps)] = {'cv': float(np.mean(cvs)), 'std': float(np.std(cvs)), 'n': len(cvs)}
    print(f"  ε={eps:.1f}: CV={exp2b[str(eps)]['cv']:.6f}")

with open(os.path.join(OUT, 'exp2b_state_dep_results.json'), 'w') as f:
    json.dump(exp2b, f, indent=2)

# Summary
print("\n=== SUMMARY ===")
print("Exp1: High-dim (random + hebbian, no normalization)")
print("Exp2: Static asymmetry")
print("Exp2b: State-dependent asymmetry")  
print("Exp3: Noise robustness")

# Check if noise breaks
base = exp3['0.0']['cv']
for ns in noise_levels:
    if exp3[str(ns)]['cv'] > 2*base + 0.005:
        print(f"Noise break: η={ns}")
        break
else:
    print(f"Noise: no break up to η=1.0")
print("Done!")
