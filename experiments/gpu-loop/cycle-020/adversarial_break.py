#!/usr/bin/env python3
"""
Cycle 020 — ADVERSARIAL BREAK: Find a coupling that intentionally BREAKS conservation.

System: x_{t+1} = tanh(C(x_t) · x_t)
Invariant: I(x) = γ(x) + H(x) where γ = σ₁-σ₂, H = spectral entropy
Metric: CV(I) = std(I)/mean(I) across trajectory — lower = more conserved

Previous best adversarial: CV ≈ 0.157 (anti-diagonal)
Target: CV > 0.1 means conservation is genuinely broken

Attack strategies:
  a) Oscillating rank — C alternates between rank-1 and full-rank
  b) Eigenspace rotation — eigenvectors rotate 180° per step
  c) Spectral shape flip — concentrated ↔ flat eigenvalue distribution
  d) Eigenvalue crossing — λ₁ and λ₂ cross at every step
  e) Non-contractive regime — spectral radius near/past stability boundary
"""

import numpy as np
import json, os, sys, time
from scipy.linalg import orthogonal_procrustes

np.random.seed(42)
OUT = os.path.dirname(os.path.abspath(__file__))
_print = print
def print(*a, **k): _print(*a, **k, flush=True)

# ──────────────────────────────────────────────
# Core metrics
# ──────────────────────────────────────────────

def compute_I(C):
    """I = γ + H from eigenvalues of C."""
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

def compute_I_jacobian(C, x):
    """I from Jacobian eigenvalues — the dynamical systems version."""
    J = np.diag(1 - x**2) @ C
    eigs = np.sort(np.abs(np.linalg.eigvals(J)))[::-1]
    if len(eigs) < 2:
        return 0.0
    gamma = eigs[0] - eigs[1]
    total = np.sum(eigs)
    if total < 1e-15:
        return 0.0
    p = eigs / total
    p = p[p > 1e-15]
    H = -np.sum(p * np.log(p))
    return gamma + H

def spectral_radius_J(C, x):
    """Spectral radius of Jacobian."""
    J = np.diag(1 - x**2) @ C
    return float(np.max(np.abs(np.linalg.eigvals(J))))

def run_trajectory(N, T, coupling_fn, x_init=None, use_jacobian=False, noise_std=0.0):
    """Run trajectory and return CV(I), max I, min I, trajectory stats."""
    x = np.random.randn(N) * 0.5 if x_init is None else x_init.copy()
    I_vals = []
    rho_vals = []
    
    for t in range(T):
        C_t = coupling_fn(x, t, N)
        C_t = (C_t + C_t.T) / 2  # enforce symmetry for eigvalsh
        
        if use_jacobian:
            I_vals.append(compute_I_jacobian(C_t, x))
        else:
            I_vals.append(compute_I(C_t))
        rho_vals.append(spectral_radius_J(C_t, x))
        
        y = np.tanh(C_t @ x)
        if noise_std > 0:
            y += np.random.randn(N) * noise_std
        x = y
    
    # Skip transient
    arr = np.array(I_vals[10:])
    m = np.mean(arr)
    if abs(m) < 1e-12:
        return {'cv': float('nan'), 'mean': m, 'std': 0, 'min': float(np.min(arr)),
                'max': float(np.max(arr)), 'rho_mean': float(np.mean(rho_vals)),
                'rho_max': float(np.max(rho_vals))}
    
    cv = float(np.std(arr) / abs(m))
    return {
        'cv': cv,
        'mean': float(m),
        'std': float(np.std(arr)),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
        'rho_mean': float(np.mean(rho_vals)),
        'rho_max': float(np.max(rho_vals))
    }

# ──────────────────────────────────────────────
# ATTACK STRATEGIES
# ──────────────────────────────────────────────

def make_oscillating_rank(alpha_freq=2.0, base_rank=0.05):
    """
    (a) Oscillating rank: C(x) = α(t)·xx^T/N + (1-α(t))·R
    where α oscillates rapidly between 0 and 1.
    R = random fixed symmetric matrix.
    """
    def coupling(x, t, N):
        alpha = 0.5 + 0.5 * np.sin(alpha_freq * t)  # oscillates 0→1→0
        R = np.random.RandomState(42).randn(N, N)
        R = (R + R.T) / 2 / np.sqrt(N)
        rank1 = np.outer(x, x) / N
        C = alpha * rank1 + (1 - alpha) * R
        return C * 0.8  # moderate coupling strength
    return coupling

def make_eigenspace_rotation(N, rotation_speed=1.0, coupling_strength=0.8):
    """
    (b) Eigenspace rotation: C(x) has fixed eigenvalues but eigenvectors
    that rotate by (rotation_speed * π) per step.
    """
    # Pre-compute a rotation schedule
    rng = np.random.RandomState(123)
    base_eigvecs = np.linalg.qr(rng.randn(N, N))[0]
    eigenvalues = np.exp(-np.arange(N) / 2.0)  # decaying spectrum
    
    def coupling(x, t, N_):
        angle = rotation_speed * np.pi * t
        # Givens rotation in the (0,1) plane — rotate eigenvectors
        R = np.eye(N_)
        c, s = np.cos(angle), np.sin(angle)
        R[0, 0] = c; R[0, 1] = -s
        R[1, 0] = s; R[1, 1] = c
        rotated_vecs = base_eigvecs @ R
        C = rotated_vecs @ np.diag(eigenvalues) @ rotated_vecs.T
        # Add state-dependence: scale by x norm
        xnorm = np.linalg.norm(x)
        C = C * coupling_strength + 0.1 * np.outer(x, x) / (N_ * max(xnorm, 0.1))
        return C
    return coupling

def make_spectral_shape_flip(N, coupling_strength=0.8):
    """
    (c) Spectral shape flip: alternates between concentrated (rank-1 like)
    and flat (identity-like) eigenvalue distributions every step.
    """
    rng = np.random.RandomState(456)
    base_vecs = np.linalg.qr(rng.randn(N, N))[0]
    
    # Concentrated spectrum: one big eigenvalue, rest tiny
    concentrated = np.zeros(N)
    concentrated[0] = 1.0
    concentrated[1:] = 0.01
    
    # Flat spectrum: all eigenvalues equal
    flat = np.ones(N) * (1.0 / N)
    
    def coupling(x, t, N_):
        # Smooth interpolation with state-dependent phase
        phase = np.sin(np.pi * t + 0.5 * np.dot(x, x))
        # phase goes -1 to 1
        w = 0.5 * (1 + phase)  # 0 to 1
        spectrum = w * concentrated + (1 - w) * flat
        C = base_vecs @ np.diag(spectrum) @ base_vecs.T
        C = C * coupling_strength
        # Add state-dependent perturbation
        C += 0.05 * np.outer(x, x) / N_
        return C
    return coupling

def make_eigenvalue_crossing(N, coupling_strength=0.8):
    """
    (d) Deliberate eigenvalue crossing: λ₁ and λ₂ cross at every step.
    At crossing, γ = σ₁ - σ₂ → 0, which should spike H and destabilize I.
    """
    rng = np.random.RandomState(789)
    base_vecs = np.linalg.qr(rng.randn(N, N))[0]
    base_eigs = np.exp(-np.arange(N) / 3.0)  # decaying base spectrum
    
    def coupling(x, t, N_):
        eigs = base_eigs.copy()
        # Make λ₁ and λ₂ cross: oscillate which one is larger
        cross = np.sin(np.pi * t)
        eigs[0] = base_eigs[0] + 0.3 * cross
        eigs[1] = base_eigs[1] - 0.3 * cross
        # Ensure positive
        eigs = np.maximum(eigs, 0.01)
        
        C = base_vecs @ np.diag(eigs) @ base_vecs.T
        C = C * coupling_strength
        # State-dependent: rotate eigenvectors based on x
        xnorm = np.linalg.norm(x)
        if xnorm > 0.01:
            perturb = 0.1 * np.outer(x, x) / (N_ * xnorm)
            C += perturb
        return C
    return coupling

def make_non_contractive(N, rho_target=1.2, coupling_strength=1.5):
    """
    (e) Non-contractive regime: deliberately push ρ(J) > 1.
    Near the stability boundary, tanh saturation barely contains the dynamics.
    """
    rng = np.random.RandomState(314)
    A = rng.randn(N, N)
    A = (A + A.T) / 2
    # Scale to have large spectral radius
    eigs = np.linalg.eigvalsh(A)
    max_eig = np.max(np.abs(eigs))
    A = A / max_eig * rho_target  # spectral radius = rho_target
    
    def coupling(x, t, N_):
        # State-dependent: amplify when x is small (before tanh clips)
        xnorm = np.linalg.norm(x)
        scale = coupling_strength
        if xnorm < 0.5:
            scale *= 1.5  # extra push in linear regime
        C = A * scale
        # Add state-dependent perturbation to break symmetry of dynamics
        C += 0.2 * np.outer(x, x) / N_
        return C
    return coupling

# ──────────────────────────────────────────────
# COMBINED / EXTREME STRATEGIES
# ──────────────────────────────────────────────

def make_combined_oscillate_cross(N):
    """Combine oscillating rank + eigenvalue crossing + state dependence."""
    rng = np.random.RandomState(666)
    R = (rng.randn(N, N) + rng.randn(N, N).T) / 2 / np.sqrt(N)
    base_vecs = np.linalg.qr(rng.randn(N, N))[0]
    
    def coupling(x, t, N_):
        # Eigenvalue crossing component
        cross = np.sin(2 * np.pi * t)
        eigs = np.ones(N) * 0.1
        eigs[0] = 0.5 + 0.4 * cross
        eigs[1] = 0.5 - 0.4 * cross
        
        C_cross = base_vecs @ np.diag(eigs) @ base_vecs.T
        
        # Oscillating rank component
        alpha = 0.5 + 0.5 * np.cos(3 * t)
        rank1 = np.outer(x, x) / N_
        
        C = alpha * rank1 + (1 - alpha) * C_cross + 0.3 * R
        
        # Scale to push near instability
        C *= 1.2
        return C
    return coupling

def make_chaos_coupling(N):
    """Maximally chaotic: rapidly switching eigenvectors + crossing eigenvalues + large coupling."""
    rng = np.random.RandomState(999)
    vecs1 = np.linalg.qr(rng.randn(N, N))[0]
    vecs2 = np.linalg.qr(rng.randn(N, N))[0]
    vecs3 = np.linalg.qr(rng.randn(N, N))[0]
    
    def coupling(x, t, N_):
        # Cycle through 3 different eigenspaces
        idx = t % 3
        vecs = [vecs1, vecs2, vecs3][idx]
        
        # Oscillating spectrum
        eigs = np.ones(N) * 0.3
        cross = np.sin(np.pi * t)
        eigs[0] = 0.8 + 0.5 * cross
        eigs[1] = 0.8 - 0.5 * cross
        
        C = vecs @ np.diag(np.maximum(eigs, 0.01)) @ vecs.T
        
        # Large state-dependent kick
        xnorm = np.linalg.norm(x)
        if xnorm > 0.01:
            C += 0.3 * np.outer(x, x) / (N_ * xnorm) * np.linalg.norm(x)**2
        
        C *= 1.0  # full strength
        return C
    return coupling

# ──────────────────────────────────────────────
# EXPERIMENT RUNNER
# ──────────────────────────────────────────────

def run_experiment(name, coupling_fn, N, T=200, trials=200, use_jacobian=False, noise_std=0.0):
    """Run multiple trials of a coupling strategy."""
    print(f"\n{'='*60}")
    print(f"STRATEGY: {name} | N={N} | T={T} | trials={trials}")
    print(f"{'='*60}")
    
    cvs = []
    details = []
    
    for trial in range(trials):
        np.random.seed(trial * 7 + 13)
        result = run_trajectory(N, T, coupling_fn, use_jacobian=use_jacobian, noise_std=noise_std)
        if not np.isnan(result['cv']):
            cvs.append(result['cv'])
            details.append(result)
    
    if not cvs:
        print(f"  No valid trials!")
        return {'name': name, 'N': N, 'trials': trials, 'valid': 0}
    
    arr = np.array(cvs)
    summary = {
        'name': name,
        'N': N,
        'trials': trials,
        'valid': len(cvs),
        'cv_mean': float(np.mean(arr)),
        'cv_std': float(np.std(arr)),
        'cv_max': float(np.max(arr)),
        'cv_min': float(np.min(arr)),
        'cv_median': float(np.median(arr)),
        'cv_p95': float(np.percentile(arr, 95)),
        'cv_p99': float(np.percentile(arr, 99)),
    }
    
    # Find worst case
    worst_idx = np.argmax(arr)
    worst = details[worst_idx]
    summary['worst_cv'] = worst['cv']
    summary['worst_rho_max'] = worst['rho_max']
    summary['worst_rho_mean'] = worst['rho_mean']
    
    print(f"  CV: mean={summary['cv_mean']:.6f} ± {summary['cv_std']:.6f}")
    print(f"  CV: max={summary['cv_max']:.6f} | median={summary['cv_median']:.6f}")
    print(f"  CV: p95={summary['cv_p95']:.6f} | p99={summary['cv_p99']:.6f}")
    print(f"  Worst trial: CV={worst['cv']:.6f}, ρ_max={worst['rho_max']:.4f}")
    
    return summary

# ──────────────────────────────────────────────
# MAIN: Run all strategies
# ──────────────────────────────────────────────

if __name__ == '__main__':
    t0 = time.time()
    all_results = {}
    
    # Test at multiple dimensions
    dims = [10, 20, 50]
    T = 200
    trials = 200
    
    # ── Strategy (a): Oscillating rank ──
    for freq in [1.0, 2.0, 5.0, 10.0]:
        for N in dims:
            name = f"a_oscillating_rank_f{freq:.0f}_N{N}"
            coupling = make_oscillating_rank(alpha_freq=freq)
            r = run_experiment(name, coupling, N, T, trials)
            all_results[name] = r
    
    # ── Strategy (b): Eigenspace rotation ──
    for speed in [0.5, 1.0, 2.0, 4.0]:
        for N in dims:
            name = f"b_eigenspace_rot_s{speed:.1f}_N{N}"
            coupling = make_eigenspace_rotation(N, rotation_speed=speed)
            r = run_experiment(name, coupling, N, T, trials)
            all_results[name] = r
    
    # ── Strategy (c): Spectral shape flip ──
    for N in dims:
        name = f"c_spectral_flip_N{N}"
        coupling = make_spectral_shape_flip(N)
        r = run_experiment(name, coupling, N, T, trials)
        all_results[name] = r
    
    # ── Strategy (d): Eigenvalue crossing ──
    for N in dims:
        name = f"d_eigenvalue_cross_N{N}"
        coupling = make_eigenvalue_crossing(N)
        r = run_experiment(name, coupling, N, T, trials)
        all_results[name] = r
    
    # ── Strategy (e): Non-contractive regime ──
    for rho in [0.9, 1.0, 1.2, 1.5]:
        for N in dims:
            name = f"e_noncontractive_rho{rho:.1f}_N{N}"
            coupling = make_non_contractive(N, rho_target=rho)
            r = run_experiment(name, coupling, N, T, trials)
            all_results[name] = r
    
    # ── Combined strategies ──
    for N in dims:
        name = f"combined_osc_cross_N{N}"
        coupling = make_combined_oscillate_cross(N)
        r = run_experiment(name, coupling, N, T, trials)
        all_results[name] = r
    
    for N in dims:
        name = f"chaos_N{N}"
        coupling = make_chaos_coupling(N)
        r = run_experiment(name, coupling, N, T, trials)
        all_results[name] = r
    
    # ── Jacobian-based I (alternative metric) on best couplings ──
    print("\n" + "="*60)
    print("RE-RUNNING TOP CANDIDATES WITH JACOBIAN METRIC")
    print("="*60)
    
    # Sort by CV and pick top 5
    sorted_results = sorted(all_results.items(), key=lambda x: x[1].get('cv_max', 0), reverse=True)
    top5 = sorted_results[:5]
    
    jacobian_results = {}
    for name, r in top5:
        N = r['N']
        # Reconstruct coupling
        if name.startswith('a_'):
            freq = float(name.split('_f')[1].split('_')[0])
            coupling = make_oscillating_rank(alpha_freq=freq)
        elif name.startswith('b_'):
            speed = float(name.split('_s')[1].split('_')[0])
            coupling = make_eigenspace_rotation(N, rotation_speed=speed)
        elif name.startswith('c_'):
            coupling = make_spectral_shape_flip(N)
        elif name.startswith('d_'):
            coupling = make_eigenvalue_crossing(N)
        elif name.startswith('e_'):
            rho = float(name.split('_rho')[1].split('_')[0])
            coupling = make_non_contractive(N, rho_target=rho)
        elif 'combined' in name:
            coupling = make_combined_oscillate_cross(N)
        elif 'chaos' in name:
            coupling = make_chaos_coupling(N)
        else:
            continue
        
        jname = f"JACOBIAN_{name}"
        jr = run_experiment(jname, coupling, N, T, trials, use_jacobian=True)
        jacobian_results[jname] = jr
    
    # ── Summary ──
    elapsed = time.time() - t0
    print(f"\n{'='*60}")
    print(f"TOTAL TIME: {elapsed:.1f}s")
    print(f"TOTAL CONFIGURATIONS: {len(all_results) + len(jacobian_results)}")
    print(f"{'='*60}")
    
    # Save all results
    full_results = {**all_results, **jacobian_results}
    with open(os.path.join(OUT, 'adversarial_results.json'), 'w') as f:
        json.dump(full_results, f, indent=2)
    
    # ── Print ranked table ──
    print("\n" + "="*80)
    print("RANKED BY MAX CV (TOP 20)")
    print("="*80)
    ranked = sorted(all_results.items(), key=lambda x: x[1].get('cv_max', 0), reverse=True)
    print(f"{'Rank':<5} {'Strategy':<40} {'N':<5} {'CV_mean':<12} {'CV_max':<12} {'CV_p99':<12}")
    print("-" * 86)
    for i, (name, r) in enumerate(ranked[:20]):
        print(f"{i+1:<5} {name:<40} {r.get('N','?'):<5} {r.get('cv_mean',0):<12.6f} "
              f"{r.get('cv_max',0):<12.6f} {r.get('cv_p99',0):<12.6f}")
    
    # ── Conservation verdict ──
    max_cv = max(r.get('cv_max', 0) for r in all_results.values())
    print(f"\n{'='*60}")
    print(f"MAX CV ACHIEVED: {max_cv:.6f}")
    if max_cv > 0.1:
        print("⚠️  CONSERVATION BROKEN — CV > 0.1 achieved!")
    elif max_cv > 0.05:
        print("⚡ CONSERVATION STRAINED — CV > 0.05 but < 0.1")
    else:
        print("✅ CONSERVATION HOLDS — could not break past CV = 0.1")
    print(f"{'='*60}")
