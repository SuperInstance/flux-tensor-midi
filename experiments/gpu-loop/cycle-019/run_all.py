"""Cycle 19 — All 3 experiments in one fast script."""
import numpy as np
import json
import os
import sys

np.random.seed(42)
OUT = os.path.dirname(os.path.abspath(__file__))
print = lambda *a, **k: (sys.stdout.write(' '.join(map(str,a)) + k.get('end','\n')), sys.stdout.flush())

def compute_I(C, x, N):
    """Compute I = spectral_gap + participation_entropy of C."""
    eigenvalues = np.linalg.eigvalsh(C)
    pos = eigenvalues[eigenvalues > 1e-12]
    if len(pos) < 2:
        return 0.0
    sorted_e = np.sort(pos)[::-1]
    gamma = sorted_e[0] - sorted_e[1]
    total = np.sum(pos)
    p = pos / total
    p = p[p > 1e-15]
    H = -np.sum(p * np.log(p))
    return gamma + H

def run_trajectory(N, T, coupling_fn, noise_std=0.0):
    x = np.random.randn(N)
    x /= np.linalg.norm(x)
    I_vals = []
    for t in range(T):
        C_t = coupling_fn(x, N)
        I_vals.append(compute_I(C_t, x, N))
        y = np.tanh(C_t @ x)
        if noise_std > 0:
            y += np.random.randn(N) * noise_std
        x = y / (np.linalg.norm(y) + 1e-12)
    arr = np.array(I_vals)
    m = np.mean(arr)
    return np.std(arr)/m if abs(m)>1e-12 else 999.0

# ============================================================
# EXP 1: High-dimensional scaling
# ============================================================
print("\n=== EXP 1: High-Dim Scaling ===")
dims = [20, 50, 100, 200]
coupling_names = ['random', 'hebbian', 'attention']
exp1 = {}
trials = 50
T = 80

for cname in coupling_names:
    exp1[cname] = {}
    for N in dims:
        cvs = []
        for _ in range(trials):
            if cname == 'random':
                A = np.random.randn(N,N)
                C0 = (A+A.T)/2/np.sqrt(N)
                fn = lambda x, n, C=C0: C
            elif cname == 'hebbian':
                fn = lambda x, n: np.outer(x,x)/np.sqrt(n)
            else:  # attention
                fn = lambda x, n: np.exp(np.outer(x,x)/np.sqrt(n))/n
            cvs.append(run_trajectory(N, T, fn))
        cv_mean = float(np.mean(cvs))
        exp1[cname][str(N)] = {'cv_mean': cv_mean, 'cv_std': float(np.std(cvs)), 'n_trials': trials}
        print(f"  {cname} N={N}: CV={cv_mean:.6f}")

with open(os.path.join(OUT, 'exp1_results.json'), 'w') as f:
    json.dump(exp1, f, indent=2)

# ============================================================
# EXP 2: Non-symmetric coupling
# ============================================================
print("\n=== EXP 2: Non-Symmetric Coupling ===")
N = 30
epsilons = [0.0, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
exp2 = {}
trials = 100

for eps in epsilons:
    cvs = []
    for _ in range(trials):
        A = np.random.randn(N,N)
        C_sym = (A+A.T)/2/np.sqrt(N)
        B = np.random.randn(N,N)
        A_asym = (B-B.T)/2/np.sqrt(N)  # antisymmetric
        C_full = C_sym + eps * A_asym
        # For non-symmetric, use SVD
        x = np.random.randn(N); x /= np.linalg.norm(x)
        I_vals = []
        for t in range(T):
            sv = np.linalg.svd(C_full, compute_uv=False)
            pos = sv[sv > 1e-12]
            if len(pos) >= 2:
                s = np.sort(pos)[::-1]
                gamma = s[0] - s[1]
                total = np.sum(pos)
                p = pos/total
                p = p[p>1e-15]
                H = -np.sum(p*np.log(p))
                I_vals.append(gamma + H)
            y = np.tanh(C_full @ x)
            x = y/(np.linalg.norm(y)+1e-12)
        arr = np.array(I_vals)
        m = np.mean(arr)
        if abs(m) > 1e-12:
            cvs.append(float(np.std(arr)/m))
    exp2[str(eps)] = {'cv_mean': float(np.mean(cvs)), 'cv_std': float(np.std(cvs)),
                       'n_trials': len(cvs), 'epsilon': eps}
    print(f"  eps={eps:.2f}: CV={exp2[str(eps)]['cv_mean']:.6f}")

with open(os.path.join(OUT, 'exp2_results.json'), 'w') as f:
    json.dump(exp2, f, indent=2)

# ============================================================
# EXP 3: Noise robustness
# ============================================================
print("\n=== EXP 3: Noise Robustness ===")
N = 30
noise_levels = [0.0, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0]
exp3 = {}
trials = 100

for noise_std in noise_levels:
    cvs = []
    for _ in range(trials):
        A = np.random.randn(N,N)
        C0 = (A+A.T)/2/np.sqrt(N)
        fn = lambda x, n, C=C0: C
        cvs.append(run_trajectory(N, T, fn, noise_std))
    exp3[str(noise_std)] = {'cv_mean': float(np.mean(cvs)), 'cv_std': float(np.std(cvs)),
                             'n_trials': trials, 'noise_std': noise_std}
    print(f"  noise={noise_std:.3f}: CV={exp3[str(noise_std)]['cv_mean']:.6f}")

with open(os.path.join(OUT, 'exp3_results.json'), 'w') as f:
    json.dump(exp3, f, indent=2)

print("\n=== ALL DONE ===")
