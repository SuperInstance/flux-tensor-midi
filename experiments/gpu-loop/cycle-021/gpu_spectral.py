import torch
import json, os, time
import numpy as np

OUT = "/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-021"
os.makedirs(OUT, exist_ok=True)

device = torch.device('cuda')
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

def compute_I_gpu(C):
    """Spectral conservation invariant on GPU"""
    eigenvalues = torch.linalg.eigvalsh(C)
    pos = eigenvalues[eigenvalues > 1e-10]
    if len(pos) < 2: return torch.tensor(0.0, device=device)
    s = torch.sort(pos, descending=True)[0]
    gamma = s[0] - s[1]
    total = torch.sum(s)
    p = s / total
    mask = p > 1e-15
    H = -torch.sum(p[mask] * torch.log(p[mask]))
    return gamma + H

def cv_of(arr):
    m = torch.mean(arr)
    return torch.std(arr) / abs(m) if abs(m) > 1e-12 else torch.tensor(999.0)

# EXP 1: Scale test — how large can we go on GPU?
print("\n=== EXP 1: GPU Scale Test ===")
scale_results = []
for N in [8, 16, 32, 64, 128, 256, 512]:
    torch.cuda.empty_cache()
    x = torch.randn(N, device=device) * 0.5
    I_vals = []
    T = 100
    
    start = time.time()
    for t in range(T):
        C = torch.outer(x, x) / N + torch.eye(N, device=device) * 0.01
        C = (C + C.T) / 2
        I_vals.append(compute_I_gpu(C).item())
        x = torch.tanh(C @ x)
    
    elapsed = time.time() - start
    cv = np.std(I_vals[5:]) / abs(np.mean(I_vals[5:])) if abs(np.mean(I_vals[5:])) > 1e-12 else 999
    
    mem_used = torch.cuda.max_memory_allocated() / 1e9
    print(f"  N={N:4d}: CV={cv:.6f}, time={elapsed:.3f}s, VRAM={mem_used:.2f}GB")
    scale_results.append({'N': N, 'cv': cv, 'time_s': elapsed, 'vram_gb': mem_used})
    torch.cuda.reset_peak_memory_stats()

# EXP 2: Batched trajectories — run 1000 parallel worlds
print("\n=== EXP 2: Batched Parallel Worlds ===")
N = 16
BATCH = 1000
T = 200
x_batch = torch.randn(BATCH, N, device=device) * 0.5
I_batch = torch.zeros(BATCH, T, device=device)

start = time.time()
for t in range(T):
    C_batch = torch.bmm(x_batch.unsqueeze(2), x_batch.unsqueeze(1)) / N + torch.eye(N, device=device).unsqueeze(0) * 0.01
    C_batch = (C_batch + C_batch.transpose(1, 2)) / 2
    
    for b in range(BATCH):
        I_batch[b, t] = compute_I_gpu(C_batch[b])
    
    x_batch = torch.tanh(torch.bmm(C_batch, x_batch.unsqueeze(2)).squeeze(2))

elapsed = time.time() - start

cvs = []
for b in range(BATCH):
    vals = I_batch[b, 10:].cpu().numpy()
    m = np.mean(vals)
    if abs(m) > 1e-12:
        cvs.append(np.std(vals) / abs(m))

cvs = np.array(cvs)
print(f"  {BATCH} parallel worlds, N={N}, T={T}")
print(f"  Time: {elapsed:.1f}s")
print(f"  CV: mean={np.mean(cvs):.6f}, median={np.median(cvs):.6f}")
print(f"  CV: p10={np.percentile(cvs,10):.6f}, p90={np.percentile(cvs,90):.6f}")
print(f"  % with CV<0.03: {np.mean(cvs < 0.03)*100:.1f}%")
print(f"  % with CV<0.01: {np.mean(cvs < 0.01)*100:.1f}%")

# EXP 3: GPU Spectral Conservation Monitor — real-time tracking
print("\n=== EXP 3: Real-time Conservation Monitor ===")
N = 32
x = torch.randn(N, device=device) * 0.5
violations = 0
max_drift = 0
I_history = []
THRESHOLD = 0.05

I_initial = None
for t in range(500):
    C = torch.outer(x, x) / N + torch.eye(N, device=device) * 0.01
    C = (C + C.T) / 2
    I_val = compute_I_gpu(C).item()
    I_history.append(I_val)
    
    if I_initial is None:
        I_initial = I_val
    
    drift = abs(I_val - I_initial) / abs(I_initial)
    if drift > max_drift:
        max_drift = drift
    if drift > THRESHOLD:
        violations += 1

    x = torch.tanh(C @ x)

cv3 = np.std(I_history[10:]) / abs(np.mean(I_history[10:]))
print(f"  N={N}, T=500")
print(f"  CV: {cv3:.6f}")
print(f"  Max drift: {max_drift*100:.2f}%")
print(f"  Threshold violations (>5%): {violations}/500 ({violations/5:.1f}%)")

# EXP 4: Commutator diagnostic on GPU
print("\n=== EXP 4: Commutator ||[D,C]|| Diagnostic ===")
N = 32
x = torch.randn(N, device=device) * 0.5
comm_norms = []
I_drifts = []

for t in range(200):
    C = torch.outer(x, x) / N + torch.eye(N, device=device) * 0.01
    C = (C + C.T) / 2
    
    D = torch.diag(1 - x**2) @ C
    comm = D @ C - C @ D
    comm_norm = torch.norm(comm, 'fro').item()
    comm_norms.append(comm_norm)
    
    I_val = compute_I_gpu(C).item()
    I_drifts.append(I_val)
    
    x = torch.tanh(C @ x)

I_arr = np.array(I_drifts)
I_diff = np.abs(np.diff(I_arr))
comm_arr = np.array(comm_norms[:-1])

if np.std(comm_arr) > 1e-12 and np.std(I_diff) > 1e-12:
    corr = np.corrcoef(comm_arr, I_diff)[0, 1]
    print(f"  Correlation ||[D,C]|| vs |ΔI|: {corr:.4f}")
else:
    corr = 0
    print(f"  Correlation: insufficient variation")

# Save results
results = {
    'gpu': torch.cuda.get_device_name(0),
    'vram_gb': torch.cuda.get_device_properties(0).total_memory / 1e9,
    'pytorch': torch.__version__,
    'corr_commutator_drift': float(corr),
    'batch_cvs_mean': float(np.mean(cvs)),
    'batch_cvs_pct_under_003': float(np.mean(cvs < 0.03) * 100),
    'scale_results': scale_results,
    'monitor_cv': float(cv3),
    'monitor_max_drift_pct': float(max_drift * 100),
    'monitor_violations': violations,
}
with open(os.path.join(OUT, 'gpu_results.json'), 'w') as f:
    json.dump(results, f, indent=2)

print("\nGPU experiments complete!")
