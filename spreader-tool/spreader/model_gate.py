"""Model gate: when deadband opens, wake up a model.

The α dial per room:
  α = 0: pure code, no model
  α ∈ (0, 0.3]: micro-model only (local, <1ms)
  α ∈ (0.3, 0.7]: small model (local/remote, <100ms)
  α ∈ (0.7, 1.0): full model (remote, cost incurred)
  α = 1.0: always model, never code
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol

from .types import FrozenContextWindow, Seed, KPIMetrics
from .mock_backend import MockModelBackend


class ModelBackend(Protocol):
    """Interface for any model provider."""

    def inference(self, prompt: str, context: dict) -> dict: ...
    def validate(self, response: dict, expected: dict | None) -> float: ...


def _tier_for_alpha(alpha: float) -> str:
    """Map α value to model tier name."""
    if alpha <= 0.0:
        return "none"
    elif alpha <= 0.3:
        return "micro"
    elif alpha <= 0.7:
        return "small"
    else:
        return "full"


def _cost_for_tier(tier: str) -> float:
    """Estimated cost per call for each tier."""
    return {"none": 0.0, "micro": 0.0001, "small": 0.005, "full": 0.03}.get(tier, 0.0)


@dataclass(frozen=True)
class ModelGateConfig:
    """Configuration for a model gate (α dial)."""
    alpha: float = 0.0            # 0–1
    model_tier: str = "auto"      # "none", "micro", "small", "full", or "auto"
    max_latency_ms: float = 100.0
    max_cost_per_call: float = 0.05
    require_validation: bool = True
    confidence_threshold: float = 0.7

    def effective_tier(self) -> str:
        """Resolve 'auto' tier from alpha."""
        if self.model_tier != "auto":
            return self.model_tier
        return _tier_for_alpha(self.alpha)


@dataclass
class GateResult:
    """Result from a model gate invocation."""
    invoked: bool
    tier: str
    response: Optional[dict] = None
    confidence: float = 0.0
    latency_ms: float = 0.0
    cost: float = 0.0
    validated: bool = False
    error: Optional[str] = None


class ModelGate:
    """The actual α dial.

    When deadband opens, this gate decides:
    1. Which model tier to invoke
    2. What context from the FCW to send
    3. Whether to accept or reject the response
    4. Whether to lock the response as a seed
    """

    def __init__(
        self,
        config: ModelGateConfig,
        backend: Optional[ModelBackend] = None,
    ) -> None:
        self._config = config
        self._backend = backend or MockModelBackend()
        self._invocation_count = 0
        self._total_cost = 0.0
        self._total_latency = 0.0

    @property
    def config(self) -> ModelGateConfig:
        return self._config

    @property
    def alpha(self) -> float:
        return self._config.alpha

    @property
    def invocation_count(self) -> int:
        return self._invocation_count

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def total_latency_ms(self) -> float:
        return self._total_latency

    def should_invoke_model(self, fcw: Optional[FrozenContextWindow] = None) -> bool:
        """Returns True if the α dial says to invoke a model.

        At α=0: never invoke.
        At α=1: always invoke.
        In between: invoke when the FCW shows deadband or low confidence.
        """
        alpha = self._config.alpha
        if alpha <= 0.0:
            return False
        if alpha >= 1.0:
            return True
        # For mid-range α, use FCW context to decide
        if fcw is not None:
            kpi = fcw.kpi_snapshot
            # If any KPI is degraded, invoke model
            if kpi.task_completion_rate < 90.0:
                return True
            if kpi.inference_mae > 10.0:
                return True
            # Check extensions for explicit signal
            if fcw.extensions.get("needs_model", False):
                return True
            # Probabilistic: use α as probability when KPIs are marginal
            # Use room_id hash for deterministic behavior
            import hashlib
            h = int(hashlib.sha256(fcw.fcw_id.encode()).hexdigest(), 16)
            # α scaled by severity of context
            effective_alpha = alpha
            if kpi.task_completion_rate < 95.0:
                effective_alpha = min(1.0, alpha * 1.5)
            threshold = (h % 10000) / 10000.0
            return effective_alpha > threshold
        # No FCW: invoke based on α alone (probability)
        return alpha > 0.3

    def invoke(self, fcw: Optional[FrozenContextWindow] = None, input_data: Optional[dict] = None) -> GateResult:
        """Full invocation pipeline:
        1. Check if model should be invoked
        2. Build prompt from FCW context
        3. Call model backend
        4. Validate response
        5. Return result with confidence score
        """
        tier = self._config.effective_tier()

        if not self.should_invoke_model(fcw):
            return GateResult(
                invoked=False,
                tier=tier,
                confidence=0.0,
            )

        # Build context for backend
        context = {
            "_tier": tier,
            "room_id": fcw.room_id if fcw else "unknown",
        }
        if fcw:
            context["room_type"] = fcw.room_type.value
            context["completion_rate"] = fcw.kpi_snapshot.task_completion_rate
            context["mae"] = fcw.kpi_snapshot.inference_mae
            context.update(fcw.extensions)
        if input_data:
            context["input"] = input_data

        prompt = self.build_prompt(fcw, input_data)
        cost = _cost_for_tier(tier)

        # Cost gate
        if cost > self._config.max_cost_per_call:
            return GateResult(
                invoked=False,
                tier=tier,
                error=f"cost ${cost:.4f} exceeds max ${self._config.max_cost_per_call:.4f}",
            )

        start = time.monotonic()
        try:
            response = self._backend.inference(prompt, context)
        except Exception as e:
            return GateResult(
                invoked=True,
                tier=tier,
                error=str(e),
                cost=cost,
                latency_ms=(time.monotonic() - start) * 1000,
            )
        elapsed_ms = (time.monotonic() - start) * 1000

        # Validate
        confidence = 0.0
        validated = False
        if self._config.require_validation and response:
            confidence = self._backend.validate(response, None)
            validated = confidence >= self._config.confidence_threshold
        elif response:
            confidence = response.get("confidence", 0.0)
            validated = True

        # Update stats
        self._invocation_count += 1
        self._total_cost += cost
        self._total_latency += elapsed_ms

        return GateResult(
            invoked=True,
            tier=tier,
            response=response,
            confidence=round(confidence, 4),
            latency_ms=round(elapsed_ms, 4),
            cost=cost,
            validated=validated,
        )

    def build_prompt(self, fcw: Optional[FrozenContextWindow] = None, input_data: Optional[dict] = None) -> str:
        """Convert FCW state + input into a model prompt."""
        parts = []

        if input_data:
            header = input_data.get("header", "")
            body = input_data.get("body", "")
            sender = input_data.get("sender", "")
            parts.append(f"Classify this message:")
            if sender:
                parts.append(f"From: {sender}")
            if header:
                parts.append(f"Subject: {header}")
            if body:
                parts.append(f"Body: {body[:500]}")
            parts.append("Respond with label (ham/spam/ambiguous), confidence (0-1), and intent.")

        if fcw:
            parts.append(f"[Room: {fcw.room_id}, Type: {fcw.room_type.value}]")
            kpi = fcw.kpi_snapshot
            parts.append(f"[Completion: {kpi.task_completion_rate:.1f}%, MAE: {kpi.inference_mae:.1f}%]")

        return "\n".join(parts) if parts else "Classify: unknown input"

    def reset_stats(self) -> None:
        """Reset invocation statistics."""
        self._invocation_count = 0
        self._total_cost = 0.0
        self._total_latency = 0.0
