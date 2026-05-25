"""Cycle 20 Exp 2: Adversarial — BREAK conservation"""
import numpy as np, json, os, sys

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

def cv_of(arr):
    m = np.mean(arr)
    return np.std(arr) / abs(m) if abs(m) > 1e-12 else 999.0

N = 8; T = 100; trials = 100
print("EXP 2: Adversarial — BREAK Conservation\n")

attacks = {}

# A: Oscillating rank
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    R = np.random.randn(N,N); R = (R+R.T)/2/np.sqrt(N)
    I_vals = []
    for t in range(T):
        alpha = (np.sin(t * np.pi / 3) + 1) / 2
        C = alpha * np.outer(x,x)/N + (1-alpha) * R + np.eye(N)*0.01
        C = (C+C.T)/2
        I_vals.append(compute_I(C))
        x = np.tanh(C @ x)
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['oscillating_rank'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"A: oscillating_rank: CV={np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# B: Shape flip (concentrated ↔ flat every step)
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    I_vals = []
    for t in range(T):
        if t % 2 == 0:
            eigs = np.zeros(N); eigs[0] = 10.0; eigs[1:] = 0.1
        else:
            eigs = np.ones(N)
        Q = np.linalg.qr(np.random.randn(N,N))[0]
        C = Q.T @ np.diag(eigs) @ Q
        C = (C+C.T)/2
        I_vals.append(compute_I(C))
        x = np.tanh(C @ x)
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['shape_flip'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"B: shape_flip: CV={np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# C: Rapidly changing random coupling (no state dependence)
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    I_vals = []
    for t in range(T):
        A = np.random.randn(N,N)
        C = (A+A.T)/2/np.sqrt(N)
        I_vals.append(compute_I(C))
        x = np.tanh(C @ x)
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['rapidly_changing'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"C: rapidly_changing: CV={np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# D: Eigenvalue crossing (swap top 2 every step)
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    base = np.sort(np.abs(np.random.randn(N)) + 0.5)[::-1]
    I_vals = []
    for t in range(T):
        eigs = base.copy()
        eigs[0], eigs[1] = eigs[1], eigs[0]
        eigs += np.random.randn(N) * 0.01
        Q = np.linalg.qr(np.random.randn(N,N))[0]
        C = Q.T @ np.diag(eigs) @ Q; C = (C+C.T)/2
        I_vals.append(compute_I(C))
        x = np.tanh(C @ x)
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['eigenvalue_crossing'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"D: eigenvalue_crossing: CV={np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# E: Sawtooth coupling strength (abrupt reset)
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    R = np.random.randn(N,N); R = (R+R.T)/2/np.sqrt(N)
    I_vals = []
    for t in range(T):
        phase = (t % 10) / 10.0
        C = R * (1 + phase * 5) + np.eye(N)*0.01; C = (C+C.T)/2
        I_vals.append(compute_I(C))
        x = np.tanh(C @ x)
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['sawtooth_strength'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"E: sawtooth_strength: CV={np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# F: State-dependent with ANTI-correlation (C opposes x)
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    I_vals = []
    for t in range(T):
        C = -np.outer(x,x)/N + np.eye(N)*0.5  # anti-Hebbian
        C = (C+C.T)/2
        I_vals.append(compute_I(C))
        x = np.tanh(C @ x)
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['anti_hebbian'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"F: anti_hebbian: CV={np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# G: Maximum chaos — completely different spectral shape every step
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    I_vals = []
    for t in range(T):
        # Random eigenvalues drawn from different distributions each step
        if t % 3 == 0:
            eigs = np.array([10, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
        elif t % 3 == 1:
            eigs = np.array([2, 2, 2, 2, 2, 2, 2, 2])
        else:
            eigs = np.array([5, 3, 1, 0.5, 0.3, 0.1, 0.05, 0.01])
        Q = np.linalg.qr(np.random.randn(N,N))[0]
        C = Q.T @ np.diag(eigs) @ Q; C = (C+C.T)/2
        I_vals.append(compute_I(C))
        x = np.tanh(C @ x)
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['triple_shape_cycle'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"G: triple_shape_cycle: CV={np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

with open(os.path.join(OUT, 'exp2_adversarial_results.json'), 'w') as f:
    json.dump(attacks, f, indent=2)

# Summary
print("\n=== ADVERSARIAL SUMMARY ===")
worst = max(attacks.items(), key=lambda x: x[1]['cv_mean'])
for name, r in sorted(attacks.items(), key=lambda x: -x[1]['cv_mean']):
    marker = " ⚡" if name == worst[0] else ""
    print(f"  {name}: CV={r['cv_mean']:.4f} (max {r['cv_max']:.4f}){marker}")

if worst[1]['cv_mean'] > 0.1:
    print(f"\n⚡ CONSERVATION BROKEN: {worst[0]} achieves CV={worst[1]['cv_mean']:.4f}")
elif worst[1]['cv_mean'] > 0.05:
    print(f"\n⚠️ CONSERVATION DEGRADED: {worst[0]} achieves CV={worst[1]['cv_mean']:.4f}")
else:
    print(f"\n🛡️ CONSERVATION SURVIVES ALL ATTACKS")

print("\nDone!")
