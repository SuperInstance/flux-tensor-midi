"""Benchmark: signal chain vs uniform model vs code-only.

Generates the ACTUAL NUMBERS for the paper. Runs N inputs through three
approaches and compares accuracy, cost, and latency.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .model_gate import ModelGate, ModelGateConfig, GateResult
from .pipeline import SignalChainPipeline, PipelineResult, Tile, make_spam_filter_pipeline
from .mock_backend import MockModelBackend


@dataclass
class BenchmarkResult:
    """Comparison result: signal chain vs uniform model vs code-only."""
    # Signal chain (α-tuned pipeline)
    signal_chain_accuracy: float = 0.0
    signal_chain_cost: float = 0.0
    signal_chain_latency_ms: float = 0.0
    signal_chain_models_invoked: int = 0

    # Uniform model (always full model)
    uniform_model_accuracy: float = 0.0
    uniform_model_cost: float = 0.0
    uniform_model_latency_ms: float = 0.0
    uniform_models_invoked: int = 0

    # Code-only (α=0 everywhere)
    code_only_accuracy: float = 0.0
    code_only_cost: float = 0.0
    code_only_latency_ms: float = 0.0
    code_only_models_invoked: int = 0

    # Input stats
    total_inputs: int = 0

    # Per-room breakdown
    room_breakdown: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    @property
    def cost_savings_vs_uniform(self) -> float:
        """Percentage cost savings of signal chain vs uniform model."""
        if self.uniform_model_cost == 0:
            return 0.0
        return (1.0 - self.signal_chain_cost / self.uniform_model_cost) * 100

    @property
    def latency_savings_vs_uniform(self) -> float:
        """Percentage latency savings of signal chain vs uniform."""
        if self.uniform_model_latency_ms == 0:
            return 0.0
        return (1.0 - self.signal_chain_latency_ms / self.uniform_model_latency_ms) * 100

    @property
    def model_reduction_vs_uniform(self) -> float:
        """Percentage reduction in model invocations."""
        if self.uniform_models_invoked == 0:
            return 0.0
        return (1.0 - self.signal_chain_models_invoked / self.uniform_models_invoked) * 100

    def summary_table(self) -> str:
        """Format results as a comparison table."""
        lines = [
            "┌─────────────────────┬───────────────┬───────────────┬───────────────┐",
            "│ Metric              │ Signal Chain  │ Uniform Model │ Code Only     │",
            "├─────────────────────┼───────────────┼───────────────┼───────────────┤",
            f"│ Accuracy            │ {self.signal_chain_accuracy:>11.1f}% │ {self.uniform_model_accuracy:>11.1f}% │ {self.code_only_accuracy:>11.1f}% │",
            f"│ Total Cost          │ ${self.signal_chain_cost:>9.4f}  │ ${self.uniform_model_cost:>9.4f}  │ ${self.code_only_cost:>9.4f}  │",
            f"│ Avg Latency (ms)    │ {self.signal_chain_latency_ms/max(self.total_inputs,1):>11.2f} │ {self.uniform_model_latency_ms/max(self.total_inputs,1):>11.2f} │ {self.code_only_latency_ms/max(self.total_inputs,1):>11.2f} │",
            f"│ Models Invoked      │ {self.signal_chain_models_invoked:>11d} │ {self.uniform_models_invoked:>11d} │ {self.code_only_models_invoked:>11d} │",
            f"│ Cost Savings        │ {self.cost_savings_vs_uniform:>10.1f}% │          base │           N/A │",
            f"│ Model Reduction     │ {self.model_reduction_vs_uniform:>10.1f}% │          base │           N/A │",
            "└─────────────────────┴───────────────┴───────────────┴───────────────┘",
        ]
        return "\n".join(lines)


def _check_accuracy(result_label: Optional[str], ground_truth: str) -> bool:
    """Check if predicted label matches ground truth."""
    if result_label is None:
        return False
    return result_label.lower() == ground_truth.lower()


def run_benchmark(
    inputs: List[Dict[str, Any]],
    pipeline: Optional[SignalChainPipeline] = None,
    backend: Optional[MockModelBackend] = None,
) -> BenchmarkResult:
    """Run benchmark comparing signal chain vs uniform model vs code-only.

    Args:
        inputs: List of dicts with 'header', 'body', 'sender', 'ground_truth' keys
        pipeline: Optional pre-configured pipeline (creates one if None)
        backend: Optional mock backend (creates one if None)

    Returns:
        BenchmarkResult with all three approaches compared.
    """
    result = BenchmarkResult(total_inputs=len(inputs))
    backend = backend or MockModelBackend(base_latency_ms=0.1)

    # ── 1. Signal Chain Pipeline ─────────────────────────────────────────
    pipeline = pipeline or make_spam_filter_pipeline(backend=backend)

    sc_correct = 0
    sc_cost = 0.0
    sc_latency = 0.0
    sc_models = 0
    room_stats: Dict[str, Dict[str, Any]] = {}

    for inp in inputs:
        ground_truth = inp.get("ground_truth", "ambiguous")
        pr = pipeline.process(inp)
        sc_cost += pr.total_cost
        sc_latency += pr.total_latency_ms
        sc_models += pr.models_invoked
        if _check_accuracy(pr.final_label, ground_truth):
            sc_correct += 1

        # Track per-room stats
        for rr in pr.room_results:
            room_name = rr["room"]
            if room_name not in room_stats:
                room_stats[room_name] = {"count": 0, "models_invoked": 0, "cost": 0.0}
            room_stats[room_name]["count"] += 1
            if rr["invoked_model"]:
                room_stats[room_name]["models_invoked"] += 1
            room_stats[room_name]["cost"] += rr["cost"]

    result.signal_chain_accuracy = (sc_correct / max(len(inputs), 1)) * 100
    result.signal_chain_cost = sc_cost
    result.signal_chain_latency_ms = sc_latency
    result.signal_chain_models_invoked = sc_models

    # ── 2. Uniform Model (always full model) ─────────────────────────────
    uniform_gate = ModelGate(
        ModelGateConfig(alpha=1.0, model_tier="full"),
        backend=backend,
    )

    um_correct = 0
    um_cost = 0.0
    um_latency = 0.0
    um_models = 0

    for inp in inputs:
        ground_truth = inp.get("ground_truth", "ambiguous")
        gr = uniform_gate.invoke(input_data=inp)
        um_cost += gr.cost
        um_latency += gr.latency_ms
        if gr.invoked:
            um_models += 1
        label = gr.response.get("label") if gr.response else None
        if _check_accuracy(label, ground_truth):
            um_correct += 1

    result.uniform_model_accuracy = (um_correct / max(len(inputs), 1)) * 100
    result.uniform_model_cost = um_cost
    result.uniform_model_latency_ms = um_latency
    result.uniform_models_invoked = um_models

    # ── 3. Code-Only (α=0 everywhere) ────────────────────────────────────
    code_pipeline = make_spam_filter_pipeline(
        backend=MockModelBackend(),  # Separate backend that won't be called
    )
    # Override all rooms to α=0
    from .pipeline import PipelineRoom
    for room in code_pipeline._rooms:
        room.alpha = 0.0
        room.model_gate = ModelGate(ModelGateConfig(alpha=0.0), backend=MockModelBackend())

    co_correct = 0
    co_cost = 0.0
    co_latency = 0.0
    co_models = 0

    for inp in inputs:
        ground_truth = inp.get("ground_truth", "ambiguous")
        pr = code_pipeline.process(inp)
        co_cost += pr.total_cost
        co_latency += pr.total_latency_ms
        co_models += pr.models_invoked
        if _check_accuracy(pr.final_label, ground_truth):
            co_correct += 1

    result.code_only_accuracy = (co_correct / max(len(inputs), 1)) * 100
    result.code_only_cost = co_cost
    result.code_only_latency_ms = co_latency
    result.code_only_models_invoked = co_models
    result.room_breakdown = room_stats

    return result
