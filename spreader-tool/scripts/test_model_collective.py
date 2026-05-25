#!/usr/bin/env python3
"""Test the model-backed collective inference with REAL API calls.

Compares:
- 5 statistical-only predictions
- 5 model predictions
- The adaptive hybrid approach in action

Uses synthetic commit data mimicking the Cocapn fleet repos.
"""

import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from spreader.collective import CommitObservation, Prediction, GapDetector
from spreader.model_collective import ModelPredictor, HybridPredictor, AdaptiveRouter

# ── Synthetic fleet commit data ─────────────────────────────────────────────

FLEET_COMMITS = [
    # plato-types burst
    CommitObservation(repo="plato-types", commit_type="feat", files_changed=3, insertions=45, deletions=2, author="forgemaster", timestamp=1000.0),
    CommitObservation(repo="plato-types", commit_type="test", files_changed=2, insertions=30, deletions=0, author="forgemaster", timestamp=1010.0),
    CommitObservation(repo="plato-types", commit_type="fix", files_changed=1, insertions=5, deletions=3, author="forgemaster", timestamp=1020.0),
    # tensor-spline burst
    CommitObservation(repo="tensor-spline", commit_type="feat", files_changed=5, insertions=120, deletions=10, author="forgemaster", timestamp=1030.0),
    CommitObservation(repo="tensor-spline", commit_type="refactor", files_changed=4, insertions=80, deletions=60, author="forgemaster", timestamp=1040.0),
    CommitObservation(repo="tensor-spline", commit_type="test", files_changed=3, insertions=55, deletions=0, author="forgemaster", timestamp=1050.0),
    # plato-training burst
    CommitObservation(repo="plato-training", commit_type="feat", files_changed=8, insertions=200, deletions=5, author="forgemaster", timestamp=1060.0),
    CommitObservation(repo="plato-training", commit_type="docs", files_changed=2, insertions=40, deletions=10, author="forgemaster", timestamp=1070.0),
    CommitObservation(repo="plato-training", commit_type="test", files_changed=4, insertions=90, deletions=5, author="forgemaster", timestamp=1080.0),
    CommitObservation(repo="plato-training", commit_type="chore", files_changed=1, insertions=3, deletions=1, author="forgemaster", timestamp=1090.0),
    # spreader-tool
    CommitObservation(repo="spreader-tool", commit_type="feat", files_changed=6, insertions=150, deletions=20, author="forgemaster", timestamp=1100.0),
    CommitObservation(repo="spreader-tool", commit_type="fix", files_changed=2, insertions=10, deletions=8, author="forgemaster", timestamp=1110.0),
    CommitObservation(repo="spreader-tool", commit_type="feat", files_changed=3, insertions=70, deletions=5, author="forgemaster", timestamp=1120.0),
    # casting-call
    CommitObservation(repo="casting-call", commit_type="docs", files_changed=1, insertions=25, deletions=5, author="forgemaster", timestamp=1130.0),
    CommitObservation(repo="casting-call", commit_type="refactor", files_changed=3, insertions=40, deletions=30, author="forgemaster", timestamp=1140.0),
    # back to plato-training
    CommitObservation(repo="plato-training", commit_type="feat", files_changed=10, insertions=300, deletions=15, author="forgemaster", timestamp=1150.0),
    CommitObservation(repo="plato-training", commit_type="fix", files_changed=2, insertions=8, deletions=4, author="forgemaster", timestamp=1160.0),
    CommitObservation(repo="plato-training", commit_type="test", files_changed=5, insertions=110, deletions=0, author="forgemaster", timestamp=1170.0),
    # plato-data
    CommitObservation(repo="plato-data", commit_type="feat", files_changed=4, insertions=85, deletions=3, author="forgemaster", timestamp=1180.0),
    CommitObservation(repo="plato-data", commit_type="test", files_changed=3, insertions=60, deletions=0, author="forgemaster", timestamp=1190.0),
    # final burst
    CommitObservation(repo="forgemaster", commit_type="chore", files_changed=1, insertions=2, deletions=1, author="forgemaster", timestamp=1200.0),
    CommitObservation(repo="plato-training", commit_type="feat", files_changed=7, insertions=180, deletions=10, author="forgemaster", timestamp=1210.0),
    CommitObservation(repo="tensor-spline", commit_type="fix", files_changed=1, insertions=4, deletions=2, author="forgemaster", timestamp=1220.0),
    CommitObservation(repo="plato-types", commit_type="refactor", files_changed=2, insertions=15, deletions=10, author="forgemaster", timestamp=1230.0),
    CommitObservation(repo="spreader-tool", commit_type="feat", files_changed=4, insertions=95, deletions=8, author="forgemaster", timestamp=1240.0),
]


def gap_score(pred: Prediction, obs: CommitObservation) -> float:
    """Compute simple gap score."""
    repo_gap = 0.0 if pred.repo == obs.repo else 1.0
    type_gap = 0.0 if pred.commit_type == obs.commit_type else 1.0
    size_gap = 0.0 if pred.size_bucket == obs.size_bucket else 1.0
    return round(repo_gap * 0.4 + type_gap * 0.3 + size_gap * 0.2, 4)


def print_prediction(pred: Prediction, obs: CommitObservation, label: str):
    """Print a prediction vs actual comparison."""
    gs = gap_score(pred, obs)
    repo_match = "✓" if pred.repo == obs.repo else "✗"
    type_match = "✓" if pred.commit_type == obs.commit_type else "✗"
    size_match = "✓" if pred.size_bucket == obs.size_bucket else "✗"

    print(f"  {label}: repo={pred.repo:20s} {repo_match}  type={pred.commit_type:10s} {type_match}  "
          f"size={pred.size_bucket:8s} {size_match}  conf={pred.confidence:.2f}  gap={gs:.2f}")


def main():
    print("=" * 80)
    print("MODEL-BACKED COLLECTIVE INFERENCE TEST")
    print("=" * 80)
    print(f"\nFleet commits: {len(FLEET_COMMITS)}")
    print(f"Repos: {sorted(set(c.repo for c in FLEET_COMMITS))}")
    print(f"Types: {sorted(set(c.commit_type for c in FLEET_COMMITS))}")
    print()

    # ── Phase 1: Statistical-only predictions ───────────────────────────
    print("─" * 80)
    print("PHASE 1: STATISTICAL PREDICTIONS (5 commits, stats only)")
    print("─" * 80)

    from spreader.collective import CommitPredictor
    stats_predictor = CommitPredictor()

    # Prime with first 10 commits
    for obs in FLEET_COMMITS[:10]:
        stats_predictor.observe(obs)

    stats_gaps = []
    for i, obs in enumerate(FLEET_COMMITS[10:15], 1):
        pred = stats_predictor.predict()
        gs = gap_score(pred, obs)
        stats_gaps.append(gs)
        print_prediction(pred, obs, f"Stats #{i}")
        stats_predictor.observe(obs)

    stats_avg = sum(stats_gaps) / len(stats_gaps)
    print(f"\n  Stats average gap: {stats_avg:.4f}")
    print(f"  Stats correct (gap=0): {sum(1 for g in stats_gaps if g == 0)}/{len(stats_gaps)}")

    # ── Phase 2: Model predictions ──────────────────────────────────────
    print(f"\n{'─' * 80}")
    print("PHASE 2: MODEL PREDICTIONS (5 commits, Qwen 0.8B via DeepInfra)")
    print("─" * 80)

    model_predictor = ModelPredictor()
    print(f"  Model: {model_predictor.DEFAULT_MODEL}")
    print(f"  Backend available: {model_predictor.is_available}")

    if not model_predictor.is_available:
        print("  ⚠ No DeepInfra key — skipping model phase")
    else:
        model_gaps = []
        # Build history from first 15 commits
        history = list(FLEET_COMMITS[:15])

        for i, obs in enumerate(FLEET_COMMITS[15:20], 1):
            pred = model_predictor.predict(history[-5:])
            gs = gap_score(pred, obs)
            model_gaps.append(gs)
            source = pred.metadata.get("source", "unknown")
            print_prediction(pred, obs, f"Model #{i} [{source}]")
            history.append(obs)

        model_avg = sum(model_gaps) / len(model_gaps)
        print(f"\n  Model average gap: {model_avg:.4f}")
        print(f"  Model correct (gap=0): {sum(1 for g in model_gaps if g == 0)}/{len(model_gaps)}")
        print(f"  API calls made: {model_predictor.call_count}")
        print(f"  API failures: {model_predictor.fail_count}")
        print(f"  Total cost: ${model_predictor.total_cost:.6f}")
        print(f"  Total latency: {model_predictor.total_latency_ms:.0f}ms")

    # ── Phase 3: Hybrid with Adaptive Router ────────────────────────────
    print(f"\n{'─' * 80}")
    print("PHASE 3: ADAPTIVE HYBRID ROUTER (all 25 commits)")
    print("─" * 80)

    hybrid = HybridPredictor()
    router = AdaptiveRouter(hybrid, warmup=5, sample_every=5)

    results = []
    for i, obs in enumerate(FLEET_COMMITS, 1):
        result, gs = router.predict_and_observe(obs)
        results.append((i, result, gs, obs))
        source = result.source
        model_used = result.model_prediction is not None
        agree = "✓" if result.agreement else "✗"
        print(f"  #{i:2d}: gap={gs:.2f}  model={'ON ' if model_used else 'OFF'}  "
              f"agree={agree}  src={source:20s}  "
              f"pred=({result.prediction.repo[:12]:12s}/{result.prediction.commit_type:8s})  "
              f"actual=({obs.repo[:12]:12s}/{obs.commit_type:8s})")

    print(f"\n{'─' * 80}")
    print("ROUTER SUMMARY")
    print("─" * 80)
    summary = router.summary()
    for k, v in summary.items():
        print(f"  {k}: {v}")

    # ── Comparison ───────────────────────────────────────────────────────
    print(f"\n{'─' * 80}")
    print("COMPARISON")
    print("─" * 80)
    print(f"  Stats-only avg gap:     {stats_avg:.4f}")
    if model_predictor.is_available and model_predictor.call_count > 0:
        print(f"  Model-only avg gap:     {model_avg:.4f}")
    print(f"  Hybrid avg gap:         {sum(r[2] for r in results) / len(results):.4f}")
    print(f"  Hybrid total cost:      ${router.total_cost:.6f}")
    print(f"  Model call fraction:    {router.model_call_fraction:.1%}")

    # Show how routing adapted
    print(f"\n  Routing adaptation (sample_rate over time):")
    log = router.routing_log
    for entry in log[::3]:  # every 3rd entry
        print(f"    Step {entry['step']:2d}: model={str(entry['use_model']):5s}  "
              f"gap={entry['gap_score']:.2f}  rate={entry['sample_rate']}")

    print(f"\n{'=' * 80}")
    print("DONE — model_collective.py is live")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()
