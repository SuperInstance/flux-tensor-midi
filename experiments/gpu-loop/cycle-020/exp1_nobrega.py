"""Cycle 20 Exp 1: Nobrega hypothesis — small network, fast"""
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

print("EXP 1: Nobrega Hypothesis — Neural Network Weight Conservation\n")

# Small network: 20→16→8→4 (Gram matrices: 20x20, 16x16, 8x8)
shapes = [(16, 20), (8, 16), (4, 8)]
layer_names = ['L1: 16x20', 'L2: 8x16', 'L3: 4x8']
lr = 0.01
epochs = 300

results = {}
for li, (m, n) in enumerate(shapes):
    W = np.random.randn(m, n) * np.sqrt(2.0 / n)
    I_hist = []
    for ep in range(epochs):
        G = W.T @ W  # n×n Gram matrix
        I_hist.append(compute_I(G))
        # Random gradient (simulating SGD)
        g = np.random.randn(m, n) * lr / (1 + ep * 0.01)
        W -= g
    cv = cv_of(np.array(I_hist[10:]))
    drift = abs(I_hist[-1] - I_hist[0]) / abs(I_hist[0])
    results[layer_names[li]] = {'cv': float(cv), 'drift': float(drift),
        'I_start': float(I_hist[0]), 'I_end': float(I_hist[-1]),
        'I_min': float(min(I_hist)), 'I_max': float(max(I_hist))}
    print(f"  {layer_names[li]}: CV={cv:.6f}, drift={drift:.4f}, I: {I_hist[0]:.2f}→{I_hist[-1]:.2f}")

# Test 2: Rank-1 gradient (more realistic SGD)
print("\n  --- Rank-1 gradient (realistic SGD) ---")
for li, (m, n) in enumerate(shapes):
    W = np.random.randn(m, n) * np.sqrt(2.0 / n)
    I_hist = []
    for ep in range(epochs):
        G = W.T @ W
        I_hist.append(compute_I(G))
        u, v = np.random.randn(m), np.random.randn(n)
        W -= lr / (1 + ep * 0.01) * np.outer(u, v)
    cv = cv_of(np.array(I_hist[10:]))
    drift = abs(I_hist[-1] - I_hist[0]) / abs(I_hist[0])
    print(f"    {layer_names[li]}: CV={cv:.6f}, drift={drift:.4f}")

# Test 3: Large learning rate (more drift, should break conservation more)
print("\n  --- Large LR (0.1, should break conservation more) ---")
for li, (m, n) in enumerate(shapes):
    W = np.random.randn(m, n) * np.sqrt(2.0 / n)
    I_hist = []
    for ep in range(epochs):
        G = W.T @ W
        I_hist.append(compute_I(G))
        g = np.random.randn(m, n) * 0.1 / (1 + ep * 0.005)
        W -= g
    cv = cv_of(np.array(I_hist[10:]))
    drift = abs(I_hist[-1] - I_hist[0]) / abs(I_hist[0])
    print(f"    {layer_names[li]}: CV={cv:.6f}, drift={drift:.4f}")

with open(os.path.join(OUT, 'exp1_nobrega_results.json'), 'w') as f:
    json.dump(results, f, indent=2)
print("\nDone!")
