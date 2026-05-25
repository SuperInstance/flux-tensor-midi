"""Cycle 20 — Two experiments in one script:
1. Nobrega hypothesis: spectral conservation in neural network training
2. Adversarial: find coupling that BREAKS conservation
"""
import numpy as np
import json, os, sys

np.random.seed(42)
OUT = os.path.dirname(os.path.abspath(__file__))
_print = print
def print(*a, **k): _print(*a, **k, flush=True)

def compute_I(C):
    """I = spectral_gap + participation_entropy"""
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

T = 150

# ============================================================
# EXP 1: Nobrega Hypothesis — Neural Network Weight Conservation
# ============================================================
print("=" * 60)
print("EXP 1: Nobrega Hypothesis — Neural Network Training")
print("=" * 60)

# Simulate a 3-layer MLP training via gradient descent
# Layer shapes: 784→64→32→10
# We simulate weight evolution, not actual training (too slow)
# Model: W evolves as W_{t+1} = W_t - η * ∇L(W_t)
# We approximate ∇L as random perturbation that decreases over time (convergence)

np.random.seed(42)
shapes = [(64, 784), (32, 64), (10, 32)]
layer_names = ['input→hidden1', 'hidden1→hidden2', 'hidden2→output']
lr = 0.01
epochs = 200

exp1_results = {}
for layer_idx, (m, n) in enumerate(shapes):
    W = np.random.randn(m, n) * np.sqrt(2.0 / n)  # He init
    
    I_history = []
    for epoch in range(epochs):
        # Compute I(W^T W) — Gram matrix
        G = W.T @ W
        I_val = compute_I(G)
        I_history.append(I_val)
        
        # Simulate gradient step: random perturbation with decreasing magnitude
        grad_scale = lr * (1.0 / (1.0 + epoch * 0.02))  # learning rate decay
        grad = np.random.randn(m, n) * grad_scale
        W = W - grad
    
    cv = cv_of(np.array(I_history[10:]))  # skip initial transient
    exp1_results[layer_names[layer_idx]] = {
        'shape': f'{m}x{n}',
        'cv': float(cv),
        'I_mean': float(np.mean(I_history[10:])),
        'I_std': float(np.std(I_history[10:])),
        'I_start': float(I_history[0]),
        'I_end': float(I_history[-1]),
        'I_min': float(min(I_history)),
        'I_max': float(max(I_history)),
        'drift': float(abs(I_history[-1] - I_history[0]) / abs(I_history[0])),
    }
    print(f"  {layer_names[layer_idx]} ({m}x{n}): CV={cv:.6f}, drift={exp1_results[layer_names[layer_idx]]['drift']:.4f}")
    print(f"    I: {I_history[0]:.2f} → {I_history[-1]:.2f} (range {min(I_history):.2f}—{max(I_history):.2f})")

# Now test with actual gradient-like dynamics (structured perturbation)
print("\n  --- Structured perturbation (rank-1 update) ---")
for layer_idx, (m, n) in enumerate(shapes):
    W = np.random.randn(m, n) * np.sqrt(2.0 / n)
    I_history = []
    
    for epoch in range(epochs):
        G = W.T @ W
        I_history.append(compute_I(G))
        
        # Rank-1 update (more realistic — SGD on a single sample)
        grad_scale = lr / (1.0 + epoch * 0.01)
        u = np.random.randn(m)
        v = np.random.randn(n)
        W -= grad_scale * np.outer(u, v)
    
    cv = cv_of(np.array(I_history[10:]))
    drift = abs(I_history[-1] - I_history[0]) / abs(I_history[0])
    print(f"    {layer_names[layer_idx]}: CV={cv:.6f}, drift={drift:.4f}")

with open(os.path.join(OUT, 'exp1_nobrega_results.json'), 'w') as f:
    json.dump(exp1_results, f, indent=2)

# ============================================================
# EXP 2: Adversarial — Break Conservation
# ============================================================
print("\n" + "=" * 60)
print("EXP 2: Adversarial — BREAK Conservation")
print("=" * 60)

N = 10
trials = 200

attacks = {}

# Attack A: Oscillating rank
print("\n  Attack A: Oscillating rank (rank-1 ↔ random)")
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    R = np.random.randn(N, N); R = (R + R.T) / 2 / np.sqrt(N)
    I_vals = []
    for t in range(T):
        alpha = (np.sin(t * np.pi / 3) + 1) / 2  # oscillates 0→1→0
        C = alpha * np.outer(x, x) / N + (1 - alpha) * R + np.eye(N) * 0.01
        C = (C + C.T) / 2
        I_vals.append(compute_I(C))
        y = np.tanh(C @ x)
        x = y
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['oscillating_rank'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"    CV: {np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# Attack B: Eigenspace rotation (rotate eigenvectors 180° per step)
print("\n  Attack B: Eigenspace rotation")
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    I_vals = []
    eigs = np.sort(np.random.randn(N))[::-1]
    eigs = np.abs(eigs) + 0.1
    for t in range(T):
        theta = t * np.pi / 2  # 90° rotation per step
        Q = np.linalg.qr(np.random.randn(N, N))[0]
        # Rotate the eigenspace
        R_theta = np.eye(N)
        R_theta[0, 0] = np.cos(theta)
        R_theta[0, 1] = -np.sin(theta)
        R_theta[1, 0] = np.sin(theta)
        R_theta[1, 1] = np.cos(theta)
        C = Q.T @ np.diag(eigs) @ R_theta @ Q
        C = (C + C.T) / 2 + np.eye(N) * 0.01
        I_vals.append(compute_I(C))
        y = np.tanh(C @ x)
        x = y
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['eigenspace_rotation'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"    CV: {np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# Attack C: Spectral shape flip (concentrated ↔ flat)
print("\n  Attack C: Spectral shape flip")
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    I_vals = []
    for t in range(T):
        if t % 2 == 0:
            # Concentrated: rank-1 like
            eigs = np.zeros(N); eigs[0] = 10.0; eigs[1:] = 0.1
        else:
            # Flat: uniform
            eigs = np.ones(N) * 1.0
        Q = np.linalg.qr(np.random.randn(N, N))[0]
        C = Q.T @ np.diag(eigs) @ Q
        C = (C + C.T) / 2
        I_vals.append(compute_I(C))
        y = np.tanh(C @ x)
        x = y
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['shape_flip'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"    CV: {np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# Attack D: Eigenvalue crossing (λ₁ ↔ λ₂ swap)
print("\n  Attack D: Eigenvalue crossing")
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    I_vals = []
    base_eigs = np.sort(np.random.randn(N) * 2 + 3)[::-1]
    base_eigs = np.abs(base_eigs) + 0.1
    for t in range(T):
        eigs = base_eigs.copy()
        # Swap top two eigenvalues
        eigs[0], eigs[1] = eigs[1], eigs[0]
        # Add small perturbation
        eigs += np.random.randn(N) * 0.01
        Q = np.linalg.qr(np.random.randn(N, N))[0]
        C = Q.T @ np.diag(eigs) @ Q
        C = (C + C.T) / 2
        I_vals.append(compute_I(C))
        y = np.tanh(C @ x)
        x = y
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['eigenvalue_crossing'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"    CV: {np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# Attack E: Non-contractive (ρ(J) > 1, near stability boundary)
print("\n  Attack E: Non-contractive regime")
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.1  # small init
    I_vals = []
    # Large coupling → near-explosive
    A = np.random.randn(N, N) * 3.0  # 3x normal scale
    C_base = (A + A.T) / 2 / np.sqrt(N)
    for t in range(T):
        C = np.outer(x, x) / N + C_base + np.eye(N) * 0.1
        C = (C + C.T) / 2
        I_vals.append(compute_I(C))
        y = np.tanh(C @ x)
        x = y  # tanh bounds even if coupling is large
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['non_contractive'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"    CV: {np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# Attack F: Maximum chaos — rapidly changing random coupling
print("\n  Attack F: Rapidly changing random coupling")
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    I_vals = []
    for t in range(T):
        # Completely new random coupling each step
        A = np.random.randn(N, N)
        C = (A + A.T) / 2 / np.sqrt(N)
        I_vals.append(compute_I(C))
        y = np.tanh(C @ x)
        x = y
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['rapidly_changing'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"    CV: {np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

# Attack G: Sawtooth coupling (linear ramp then reset)
print("\n  Attack G: Sawtooth coupling strength")
cvs = []
for _ in range(trials):
    x = np.random.randn(N) * 0.5
    R = np.random.randn(N, N); R = (R + R.T) / 2 / np.sqrt(N)
    I_vals = []
    for t in range(T):
        phase = (t % 10) / 10.0  # 0→0.9 in steps of 0.1, then reset to 0
        C = R * (1 + phase * 5) + np.eye(N) * 0.01
        C = (C + C.T) / 2
        I_vals.append(compute_I(C))
        y = np.tanh(C @ x)
        x = y
    cvs.append(cv_of(np.array(I_vals[5:])))
attacks['sawtooth_strength'] = {'cv_mean': float(np.mean(cvs)), 'cv_max': float(np.max(cvs))}
print(f"    CV: {np.mean(cvs):.6f} (max {np.max(cvs):.6f})")

with open(os.path.join(OUT, 'exp2_adversarial_results.json'), 'w') as f:
    json.dump(attacks, f, indent=2)

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)

print("\nExp 1 — Nobrega Hypothesis:")
for name, r in exp1_results.items():
    print(f"  {name}: CV={r['cv']:.6f}, drift={r['drift']:.4f}")

print("\nExp 2 — Adversarial Attacks:")
worst = max(attacks.items(), key=lambda x: x[1]['cv_mean'])
for name, r in sorted(attacks.items(), key=lambda x: -x[1]['cv_mean']):
    marker = " ⚡ WORST" if name == worst[0] else ""
    print(f"  {name}: CV={r['cv_mean']:.6f} (max {r['cv_max']:.6f}){marker}")

if worst[1]['cv_mean'] > 0.1:
    print(f"\n⚡ BROKEN: {worst[0]} achieves CV={worst[1]['cv_mean']:.4f}")
else:
    print(f"\n🛡️ CONSERVATION SURVIVES: worst attack ({worst[0]}) only achieves CV={worst[1]['cv_mean']:.6f}")

print("\nDone!")
