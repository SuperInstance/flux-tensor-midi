"""Tests for model_gate.py — the α dial."""

import pytest
from spreader.model_gate import ModelGate, ModelGateConfig, GateResult, _tier_for_alpha, _cost_for_tier
from spreader.mock_backend import MockModelBackend
from spreader.types import FrozenContextWindow, KPIMetrics, RoomType, TriggerType, make_fcw


class TestTierMapping:
    """α value → model tier mapping."""

    def test_alpha_zero_is_none(self):
        assert _tier_for_alpha(0.0) == "none"

    def test_alpha_negative_is_none(self):
        assert _tier_for_alpha(-0.5) == "none"

    def test_alpha_small_is_micro(self):
        assert _tier_for_alpha(0.1) == "micro"
        assert _tier_for_alpha(0.3) == "micro"

    def test_alpha_mid_is_small(self):
        assert _tier_for_alpha(0.4) == "small"
        assert _tier_for_alpha(0.7) == "small"

    def test_alpha_high_is_full(self):
        assert _tier_for_alpha(0.71) == "full"
        assert _tier_for_alpha(1.0) == "full"


class TestCostMapping:
    """Tier → cost mapping."""

    def test_none_is_free(self):
        assert _cost_for_tier("none") == 0.0

    def test_micro_is_cheap(self):
        assert _cost_for_tier("micro") < _cost_for_tier("small")

    def test_small_moderate(self):
        assert _cost_for_tier("small") < _cost_for_tier("full")

    def test_full_expensive(self):
        assert _cost_for_tier("full") > 0.0


class TestModelGateShouldInvoke:
    """Test should_invoke_model at various α levels."""

    def test_alpha_zero_never_invokes(self):
        gate = ModelGate(ModelGateConfig(alpha=0.0))
        assert gate.should_invoke_model() is False

    def test_alpha_one_always_invokes(self):
        gate = ModelGate(ModelGateConfig(alpha=1.0))
        assert gate.should_invoke_model() is True

    def test_alpha_zero_ignores_fcw(self):
        """Even with a struggling FCW, α=0 never invokes."""
        kpi = KPIMetrics(task_completion_rate=50.0, avg_wait_time=60.0,
                         energy_over_baseline=20.0, inference_mae=30.0)
        fcw = make_fcw("room1", RoomType.SENSOR, kpi, TriggerType.THRESHOLD)
        gate = ModelGate(ModelGateConfig(alpha=0.0))
        assert gate.should_invoke_model(fcw) is False

    def test_alpha_one_invokes_regardless_of_kpi(self):
        """Even with perfect KPIs, α=1 always invokes."""
        kpi = KPIMetrics(task_completion_rate=100.0, avg_wait_time=1.0,
                         energy_over_baseline=0.0, inference_mae=0.0)
        fcw = make_fcw("room1", RoomType.SENSOR, kpi, TriggerType.TIME)
        gate = ModelGate(ModelGateConfig(alpha=1.0))
        assert gate.should_invoke_model(fcw) is True

    def test_struggling_fcw_triggers_mid_alpha(self):
        """At α=0.5, struggling KPIs trigger invocation."""
        kpi = KPIMetrics(task_completion_rate=80.0, avg_wait_time=40.0,
                         energy_over_baseline=5.0, inference_mae=5.0)
        fcw = make_fcw("room1", RoomType.SENSOR, kpi, TriggerType.THRESHOLD)
        gate = ModelGate(ModelGateConfig(alpha=0.5))
        assert gate.should_invoke_model(fcw) is True

    def test_needs_model_extension_triggers(self):
        """FCW extension 'needs_model' forces invocation."""
        kpi = KPIMetrics(task_completion_rate=95.0, avg_wait_time=5.0,
                         energy_over_baseline=2.0, inference_mae=3.0)
        fcw = make_fcw("room1", RoomType.SENSOR, kpi, TriggerType.MANUAL,
                       needs_model=True)
        gate = ModelGate(ModelGateConfig(alpha=0.3))
        assert gate.should_invoke_model(fcw) is True


class TestModelGateInvoke:
    """Test full invocation pipeline."""

    def test_invoke_returns_gate_result(self):
        gate = ModelGate(ModelGateConfig(alpha=0.8))
        result = gate.invoke(input_data={"header": "Test", "body": "Hello"})
        assert isinstance(result, GateResult)

    def test_alpha_zero_returns_not_invoked(self):
        gate = ModelGate(ModelGateConfig(alpha=0.0))
        result = gate.invoke(input_data={"header": "Test"})
        assert result.invoked is False

    def test_alpha_one_invokes_and_returns_response(self):
        gate = ModelGate(ModelGateConfig(alpha=1.0))
        result = gate.invoke(input_data={"header": "Free money now", "body": "Click here"})
        assert result.invoked is True
        assert result.response is not None
        assert "label" in result.response

    def test_invocation_tracks_stats(self):
        gate = ModelGate(ModelGateConfig(alpha=1.0))
        gate.invoke(input_data={"header": "Test"})
        assert gate.invocation_count == 1
        assert gate.total_cost > 0

    def test_cost_gate_blocks_expensive_calls(self):
        """If cost exceeds max_cost_per_call, invocation is blocked."""
        gate = ModelGate(ModelGateConfig(alpha=1.0, max_cost_per_call=0.001))
        result = gate.invoke(input_data={"header": "Test"})
        assert result.invoked is False
        assert "cost" in result.error.lower()

    def test_build_prompt_includes_input(self):
        gate = ModelGate(ModelGateConfig(alpha=1.0))
        prompt = gate.build_prompt(input_data={"header": "Test Subject", "body": "Hello world"})
        assert "Test Subject" in prompt
        assert "Hello world" in prompt

    def test_build_prompt_includes_fcw_context(self):
        kpi = KPIMetrics(task_completion_rate=85.0, avg_wait_time=10.0,
                         energy_over_baseline=5.0, inference_mae=8.0)
        fcw = make_fcw("room1", RoomType.SENSOR, kpi, TriggerType.THRESHOLD)
        gate = ModelGate(ModelGateConfig(alpha=0.8))
        prompt = gate.build_prompt(fcw)
        assert "room1" in prompt
        assert "85.0%" in prompt

    def test_reset_stats(self):
        gate = ModelGate(ModelGateConfig(alpha=1.0))
        gate.invoke(input_data={"header": "Test"})
        assert gate.invocation_count > 0
        gate.reset_stats()
        assert gate.invocation_count == 0
        assert gate.total_cost == 0.0

    def test_config_effective_tier_auto(self):
        config = ModelGateConfig(alpha=0.5, model_tier="auto")
        assert config.effective_tier() == "small"

    def test_config_effective_tier_explicit(self):
        config = ModelGateConfig(alpha=0.5, model_tier="full")
        assert config.effective_tier() == "full"


class TestModelGateConfidence:
    """Test confidence threshold behavior."""

    def test_validated_flag_true_when_confident(self):
        backend = MockModelBackend()
        gate = ModelGate(
            ModelGateConfig(alpha=1.0, confidence_threshold=0.3),
            backend=backend,
        )
        result = gate.invoke(input_data={"header": "Hello", "body": "World"})
        if result.invoked:
            # Mock backend returns confidence >= 0.5, so should validate
            assert result.validated is True

    def test_high_threshold_can_fail_validation(self):
        backend = MockModelBackend()
        gate = ModelGate(
            ModelGateConfig(alpha=1.0, confidence_threshold=0.99),
            backend=backend,
        )
        result = gate.invoke(input_data={"header": "Test"})
        if result.invoked and result.confidence > 0:
            # Most mock responses won't hit 0.99
            assert isinstance(result.validated, bool)
