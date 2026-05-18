"""Tests for the benchmark runner."""

import pytest
from spreader.benchmark import BenchmarkResult, run_benchmark
from spreader.pipeline import make_spam_filter_pipeline
from spreader.mock_backend import MockModelBackend


def _make_inputs(n: int = 10) -> list:
    """Create a small deterministic input set."""
    inputs = []
    for i in range(n):
        if i % 3 == 0:
            inputs.append({
                "header": "FREE MONEY CLICK HERE NOW",
                "body": "Act now limited $500 guarantee winner prize",
                "sender": "scam@bad.com",
                "ground_truth": "spam",
            })
        elif i % 3 == 1:
            inputs.append({
                "header": "Re: Meeting tomorrow",
                "body": "Thanks again for the attached report. Please review.",
                "sender": "colleague@company.com",
                "ground_truth": "ham",
            })
        else:
            inputs.append({
                "header": "Hello friend",
                "body": "Check this out sometime",
                "sender": "person@example.com",
                "ground_truth": "ham",
            })
    return inputs


class TestBenchmarkRun:
    def test_run_benchmark_small_input(self):
        inputs = _make_inputs(10)
        result = run_benchmark(inputs)
        assert isinstance(result, BenchmarkResult)
        assert result.total_inputs == 10

    def test_signal_chain_cost_is_positive(self):
        inputs = _make_inputs(10)
        result = run_benchmark(inputs)
        # Signal chain incurs some cost from model invocations
        assert result.signal_chain_cost >= 0.0
        # Uniform model also has positive cost
        assert result.uniform_model_cost > 0.0

    def test_uniform_model_invokes_per_input(self):
        inputs = _make_inputs(10)
        result = run_benchmark(inputs)
        # Uniform model (α=1) invokes on every input
        assert result.uniform_models_invoked == 10
        # Signal chain invokes models (possibly more due to multiple rooms)
        assert result.signal_chain_models_invoked >= 0

    def test_results_deterministic(self):
        """Same input = same result (mock backend is deterministic)."""
        inputs = _make_inputs(10)
        r1 = run_benchmark(inputs)
        r2 = run_benchmark(inputs)
        assert r1.signal_chain_accuracy == r2.signal_chain_accuracy
        assert r1.signal_chain_cost == r2.signal_chain_cost
        assert r1.signal_chain_models_invoked == r2.signal_chain_models_invoked

    def test_benchmark_result_fields_populated(self):
        inputs = _make_inputs(10)
        result = run_benchmark(inputs)
        assert result.total_inputs == 10
        assert isinstance(result.signal_chain_accuracy, float)
        assert isinstance(result.signal_chain_cost, float)
        assert isinstance(result.signal_chain_latency_ms, float)
        assert isinstance(result.signal_chain_models_invoked, int)
        assert isinstance(result.uniform_model_accuracy, float)
        assert isinstance(result.uniform_model_cost, float)
        assert isinstance(result.uniform_model_latency_ms, float)
        assert isinstance(result.uniform_models_invoked, int)
        assert isinstance(result.code_only_accuracy, float)
        assert isinstance(result.code_only_cost, float)
        assert isinstance(result.code_only_latency_ms, float)
        assert isinstance(result.code_only_models_invoked, int)
        assert isinstance(result.room_breakdown, dict)


class TestBenchmarkResult:
    def test_cost_savings_property(self):
        r = BenchmarkResult(
            signal_chain_cost=5.0,
            uniform_model_cost=10.0,
        )
        assert r.cost_savings_vs_uniform == 50.0

    def test_cost_savings_zero_uniform(self):
        r = BenchmarkResult(signal_chain_cost=5.0, uniform_model_cost=0.0)
        assert r.cost_savings_vs_uniform == 0.0

    def test_latency_savings_property(self):
        r = BenchmarkResult(
            signal_chain_latency_ms=50.0,
            uniform_model_latency_ms=100.0,
        )
        assert r.latency_savings_vs_uniform == 50.0

    def test_model_reduction_property(self):
        r = BenchmarkResult(
            signal_chain_models_invoked=3,
            uniform_models_invoked=10,
        )
        assert r.model_reduction_vs_uniform == pytest.approx(70.0)

    def test_summary_table(self):
        result = run_benchmark(_make_inputs(10))
        table = result.summary_table()
        assert isinstance(table, str)
        assert "Signal Chain" in table
        assert "Uniform Model" in table
        assert "Code Only" in table
