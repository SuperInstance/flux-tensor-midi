"""
Test the Nobrega Hypothesis: Spectral Conservation During Training
===================================================================

Nobrega (arXiv 2604.07405) showed gradient flow preserves L-1 conservation laws.
We test whether I(W^T W) = γ(W^T W) + H(W^T W) is approximately conserved during training.

Setup:
  - 3-layer MLP: 784 → 64 → 32 → 10
  - MNIST subset (1000 samples)
  - Compare SGD with small LR (near-continuous) vs larger LR (discrete)
  - Track I(W_l^T W_l) per layer per epoch
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, Subset
    import torchvision
    import torchvision.transforms as transforms
except ImportError:
    print("ERROR: PyTorch not available. Install with: pip install torch torchvision")
    sys.exit(1)

# ─── Configuration ───────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent
N_SAMPLES = 1000
BATCH_SIZE = 64
EPOCHS = 100
SEED = 42

# Two experimental conditions
CONDITIONS = {
    "sgd_small_lr": {"optimizer": "sgd", "lr": 0.001, "label": "SGD lr=0.001 (near-continuous)"},
    "sgd_large_lr": {"optimizer": "sgd", "lr": 0.1, "label": "SGD lr=0.1 (discrete)"},
}


# ─── Spectral functions ──────────────────────────────────────────────────────

def compute_I(matrix: np.ndarray) -> float:
    """I = spectral_gap + participation_entropy"""
    eigenvalues = np.linalg.eigvalsh(matrix.astype(np.float64))
    pos = eigenvalues[eigenvalues > 1e-10]
    if len(pos) < 2:
        return 0.0
    s = np.sort(pos)[::-1]
    gamma = s[0] - s[1]  # spectral gap
    total = sum(s)
    p = s / total
    # Participation entropy H = -Σ p_i log(p_i)
    H = -sum(p_i * np.log(p_i) for p_i in p if p_i > 1e-15)
    return float(gamma + H)


def compute_spectral_gap(matrix: np.ndarray) -> float:
    eigenvalues = np.linalg.eigvalsh(matrix.astype(np.float64))
    pos = eigenvalues[eigenvalues > 1e-10]
    if len(pos) < 2:
        return 0.0
    s = np.sort(pos)[::-1]
    return float(s[0] - s[1])


def compute_participation_entropy(matrix: np.ndarray) -> float:
    eigenvalues = np.linalg.eigvalsh(matrix.astype(np.float64))
    pos = eigenvalues[eigenvalues > 1e-10]
    if len(pos) < 2:
        return 0.0
    s = np.sort(pos)[::-1]
    total = sum(s)
    p = s / total
    H = -sum(p_i * np.log(p_i) for p_i in p if p_i > 1e-15)
    return float(H)


def compute_frobenius_norm(matrix: np.ndarray) -> float:
    return float(np.linalg.norm(matrix, 'fro'))


# ─── Model ───────────────────────────────────────────────────────────────────

class MLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.fc1 = nn.Linear(784, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 10)

    def forward(self, x):
        x = x.view(-1, 784)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


def get_weight_matrices(model):
    """Extract weight matrices from each layer."""
    return [
        ("fc1", model.fc1.weight.detach().numpy()),
        ("fc2", model.fc2.weight.detach().numpy()),
        ("fc3", model.fc3.weight.detach().numpy()),
    ]


def compute_layer_metrics(model):
    """Compute all spectral metrics for each layer."""
    results = {}
    for name, W in get_weight_matrices(model):
        WtW = W.T @ W
        I_val = compute_I(WtW)
        gamma = compute_spectral_gap(WtW)
        H = compute_participation_entropy(WtW)
        fro = compute_frobenius_norm(W)
        results[name] = {
            "I": I_val,
            "spectral_gap": gamma,
            "entropy": H,
            "frobenius": fro,
        }
    return results


# ─── Data ────────────────────────────────────────────────────────────────────

def get_mnist_subset(n_samples, seed):
    """Load MNIST subset."""
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])
    
    dataset = torchvision.datasets.MNIST(
        root=str(OUT_DIR / "mnist_data"),
        train=True,
        download=True,
        transform=transform,
    )
    
    rng = np.random.RandomState(seed)
    indices = rng.choice(len(dataset), size=min(n_samples, len(dataset)), replace=False)
    subset = Subset(dataset, indices)
    return DataLoader(subset, batch_size=BATCH_SIZE, shuffle=True)


# ─── Training ────────────────────────────────────────────────────────────────

def run_experiment(condition_name, config, dataloader):
    """Run one experimental condition."""
    print(f"\n{'='*60}")
    print(f"Condition: {condition_name} — {config['label']}")
    print(f"{'='*60}")
    
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    
    model = MLP()
    optimizer = torch.optim.SGD(model.parameters(), lr=config["lr"])
    criterion = nn.CrossEntropyLoss()
    
    # Track metrics per epoch
    epoch_data = []
    
    # Initial metrics
    init_metrics = compute_layer_metrics(model)
    init_metrics["epoch"] = 0
    init_metrics["loss"] = None
    epoch_data.append(init_metrics)
    
    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        n_batches = 0
        
        for batch_x, batch_y in dataloader:
            optimizer.zero_grad()
            output = model(batch_x)
            loss = criterion(output, batch_y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            n_batches += 1
        
        avg_loss = total_loss / max(n_batches, 1)
        
        # Compute spectral metrics
        metrics = compute_layer_metrics(model)
        metrics["epoch"] = epoch
        metrics["loss"] = avg_loss
        epoch_data.append(metrics)
        
        if epoch % 20 == 0 or epoch == 1:
            print(f"  Epoch {epoch:3d} | loss={avg_loss:.4f} | "
                  f"I_fc1={metrics['fc1']['I']:.4f} "
                  f"I_fc2={metrics['fc2']['I']:.4f} "
                  f"I_fc3={metrics['fc3']['I']:.4f}")
    
    return epoch_data


def analyze_conservation(epoch_data, condition_name):
    """Analyze how well I is conserved across training."""
    analysis = {"condition": condition_name}
    
    for layer in ["fc1", "fc2", "fc3"]:
        I_values = [e[layer]["I"] for e in epoch_data]
        I_init = I_values[0]
        I_final = I_values[-1]
        I_mean = np.mean(I_values)
        I_std = np.std(I_values)
        
        # Coefficient of variation
        cv = I_std / abs(I_mean) if abs(I_mean) > 1e-10 else float('inf')
        
        # Max drift from initial
        drifts = [abs(v - I_init) for v in I_values]
        max_drift = max(drifts)
        max_drift_pct = max_drift / abs(I_init) * 100 if abs(I_init) > 1e-10 else float('inf')
        
        # Trend: linear regression slope
        epochs = np.arange(len(I_values))
        if len(I_values) > 1:
            slope, intercept = np.polyfit(epochs, I_values, 1)
        else:
            slope, intercept = 0, I_values[0]
        
        analysis[layer] = {
            "I_initial": float(I_init),
            "I_final": float(I_final),
            "I_mean": float(I_mean),
            "I_std": float(I_std),
            "CV": float(cv),
            "max_drift": float(max_drift),
            "max_drift_pct": float(max_drift_pct),
            "trend_slope": float(slope),
            "conserved": cv < 0.1,  # CV < 10% → approximately conserved
        }
        
        status = "✓ CONSERVED" if cv < 0.1 else "✗ NOT conserved"
        print(f"  {layer}: I_init={I_init:.4f} → I_final={I_final:.4f} | "
              f"CV={cv:.4f} ({cv*100:.1f}%) | max_drift={max_drift_pct:.1f}% | {status}")
    
    return analysis


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    start_time = time.time()
    print(f"Nobrega Hypothesis Test — {datetime.now(timezone.utc).isoformat()}")
    print(f"Model: MLP 784→64→32→10 | Samples: {N_SAMPLES} | Epochs: {EPOCHS}")
    
    # Load data
    print("\nLoading MNIST subset...")
    dataloader = get_mnist_subset(N_SAMPLES, SEED)
    print(f"  {len(dataloader.dataset)} samples loaded")
    
    all_results = {}
    all_analyses = {}
    
    for cond_name, config in CONDITIONS.items():
        epoch_data = run_experiment(cond_name, config, dataloader)
        all_results[cond_name] = epoch_data
        
        print(f"\nConservation analysis for {cond_name}:")
        analysis = analyze_conservation(epoch_data, cond_name)
        all_analyses[cond_name] = analysis
    
    elapsed = time.time() - start_time
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Elapsed: {elapsed:.1f}s")
    print()
    
    for cond_name in CONDITIONS:
        print(f"{cond_name}:")
        for layer in ["fc1", "fc2", "fc3"]:
            a = all_analyses[cond_name][layer]
            status = "CONSERVED" if a["conserved"] else "NOT conserved"
            print(f"  {layer}: CV={a['CV']*100:.1f}% — {status}")
        print()
    
    # Overall verdict
    all_conserved = all(
        all_analyses[c][l]["conserved"]
        for c in CONDITIONS
        for l in ["fc1", "fc2", "fc3"]
    )
    small_lr_conserved = all(
        all_analyses["sgd_small_lr"][l]["conserved"]
        for l in ["fc1", "fc2", "fc3"]
    )
    large_lr_conserved = all(
        all_analyses["sgd_large_lr"][l]["conserved"]
        for l in ["fc1", "fc2", "fc3"]
    )
    
    verdict = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hypothesis": "I(W^T W) = γ + H is approximately conserved during training",
        "all_conserved": all_conserved,
        "small_lr_conserved": small_lr_conserved,
        "large_lr_conserved": large_lr_conserved,
        "conclusion": "",
        "elapsed_seconds": elapsed,
    }
    
    if all_conserved:
        verdict["conclusion"] = (
            "STRONG SUPPORT: I is approximately conserved across all conditions and layers. "
            "Nobrega's conservation law extends to spectral complexity."
        )
    elif small_lr_conserved and not large_lr_conserved:
        verdict["conclusion"] = (
            "PARTIAL SUPPORT: I is conserved with small LR (near-continuous gradient flow) "
            "but NOT with large LR (discrete SGD breaks conservation). "
            "This matches Nobrega's theoretical prediction — conservation holds for continuous flow."
        )
    elif small_lr_conserved:
        verdict["conclusion"] = (
            "PARTIAL SUPPORT: I is approximately conserved in small-LR regime "
            "(near-continuous gradient flow), consistent with Nobrega's theory."
        )
    else:
        verdict["conclusion"] = (
            "NOT SUPPORTED: I drifts significantly even with small learning rate. "
            "Spectral complexity I = γ + H is not conserved under standard training."
        )
    
    print(f"VERDICT: {verdict['conclusion']}")
    
    # Save results
    results_json = {
        "metadata": {
            "timestamp": verdict["timestamp"],
            "model": "MLP 784→64→32→10",
            "dataset": f"MNIST {N_SAMPLES} samples",
            "epochs": EPOCHS,
            "seed": SEED,
            "elapsed_seconds": elapsed,
        },
        "verdict": verdict,
        "analyses": all_analyses,
        "conditions": {name: cfg["label"] for name, cfg in CONDITIONS.items()},
    }
    
    # Save per-epoch data (compact)
    for cond_name in CONDITIONS:
        epoch_records = []
        for e in all_results[cond_name]:
            record = {"epoch": e["epoch"], "loss": e["loss"]}
            for layer in ["fc1", "fc2", "fc3"]:
                record[f"I_{layer}"] = e[layer]["I"]
                record[f"gap_{layer}"] = e[layer]["spectral_gap"]
                record[f"H_{layer}"] = e[layer]["entropy"]
                record[f"frob_{layer}"] = e[layer]["frobenius"]
            epoch_records.append(record)
        results_json[f"epochs_{cond_name}"] = epoch_records
    
    out_path = OUT_DIR / "nobrega_results.json"
    with open(out_path, "w") as f:
        json.dump(results_json, f, indent=2, default=str)
    print(f"\nResults saved to {out_path}")
    
    # Write results.md
    md_path = OUT_DIR / "results.md"
    write_results_md(verdict, all_analyses, all_results, CONDITIONS, md_path)
    print(f"Report saved to {md_path}")


def write_results_md(verdict, analyses, results, conditions, path):
    """Write markdown results report."""
    lines = []
    lines.append("# Nobrega Hypothesis Test Results")
    lines.append("")
    lines.append(f"**Date:** {verdict['timestamp']}")
    lines.append(f"**Hypothesis:** {verdict['hypothesis']}")
    lines.append("")
    lines.append(f"## Verdict")
    lines.append("")
    lines.append(f"> {verdict['conclusion']}")
    lines.append("")
    
    for cond_name, cfg in conditions.items():
        lines.append(f"## {cfg['label']}")
        lines.append("")
        lines.append("| Layer | I(initial) | I(final) | CV(%) | Max Drift(%) | Conserved? |")
        lines.append("|-------|-----------|----------|-------|-------------|------------|")
        for layer in ["fc1", "fc2", "fc3"]:
            a = analyses[cond_name][layer]
            status = "✓" if a["conserved"] else "✗"
            lines.append(
                f"| {layer} | {a['I_initial']:.4f} | {a['I_final']:.4f} | "
                f"{a['CV']*100:.2f} | {a['max_drift_pct']:.2f} | {status} |"
            )
        lines.append("")
    
    lines.append("## Interpretation")
    lines.append("")
    lines.append("The spectral complexity I(W^T W) = γ + H combines:")
    lines.append("- **γ (spectral gap):** distance between top two eigenvalues of W^T W")
    lines.append("- **H (participation entropy):** entropy of the normalized eigenvalue distribution")
    lines.append("")
    lines.append("Nobrega showed that gradient flow preserves certain L-1 conservation laws.")
    lines.append("We test whether I, as a natural spectral complexity measure, is also approximately conserved.")
    lines.append("")
    
    if verdict["small_lr_conserved"] and not verdict["large_lr_conserved"]:
        lines.append("### Key Finding")
        lines.append("")
        lines.append("I is conserved under small learning rate (near-continuous gradient flow) but NOT")
        lines.append("under large learning rate (discrete SGD). This is **consistent with Nobrega's theory**,")
        lines.append("which proves conservation for continuous-time gradient flow, not discrete SGD.")
    elif verdict["all_conserved"]:
        lines.append("### Key Finding")
        lines.append("")
        lines.append("I is approximately conserved across ALL training conditions, including large LR.")
        lines.append("This is **stronger than Nobrega's prediction** and suggests spectral conservation")
        lines.append("may be a robust property of gradient-based training.")
    else:
        lines.append("### Key Finding")
        lines.append("")
        lines.append("I drifts significantly during training. Spectral complexity is NOT conserved")
        lines.append("under standard training, even at small learning rates.")
    
    lines.append("")
    lines.append("## Method")
    lines.append("")
    lines.append("- Model: 3-layer MLP (784→64→32→10), ReLU activations")
    lines.append(f"- Data: MNIST, 1000 sample subset")
    lines.append(f"- Training: {EPOCHS} epochs, SGD")
    lines.append("- Metrics: I(W_l^T W_l) computed per layer per epoch")
    lines.append("- Conservation threshold: CV < 10%")
    
    with open(path, "w") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
