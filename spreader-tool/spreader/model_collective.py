"""Model-backed collective inference — real API calls for prediction.

Layers on top of the statistical CommitPredictor with:
1. ModelPredictor — calls cheap DeepInfra models for next-commit prediction
2. HybridPredictor — statistical baseline + model tie-breaking
3. AdaptiveRouter — decides when to burn API calls vs use stats alone
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .collective import (
    CommitObservation,
    Prediction,
    GapTile,
    LearningTile,
    CommitPredictor,
    GapDetector,
    LearningLoop,
    CollectiveBroadcaster,
    CollectiveInference,
    CollectiveConfig,
    CycleResult,
    GapThresholds,
)
from .real_backends import (
    DeepInfraBackend,
    BackendError,
    _load_key,
)

logger = logging.getLogger(__name__)

# ── 1. ModelPredictor ───────────────────────────────────────────────────────

class ModelPredictor:
    """Uses a cheap LLM to predict next commit characteristics.

    Given the last N commits as context, asks the model:
    "Given this commit history, predict the next commit's repo, type, and size."

    Falls back to statistical predictor when API is unavailable.
    """

    DEFAULT_MODEL = "Qwen/Qwen3.5-0.8B"
    MAX_CONTEXT_COMMITS = 5

    # Known repos and types for constrained output
    KNOWN_REPOS = [
        "plato-types", "tensor-spline", "plato-data", "plato-training",
        "forgemaster", "cocapn-fleet", "spreader-tool", "casting-call",
        "purple-pincher",
    ]
    KNOWN_TYPES = ["feat", "fix", "refactor", "docs", "test", "chore", "ci"]
    KNOWN_SIZES = ["tiny", "small", "medium", "large", "massive"]

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        max_context: int = 5,
    ) -> None:
        self._model = model or self.DEFAULT_MODEL
        self._max_context = max_context
        self._api_key = api_key or _load_key("deepinfra-api-key.txt", "DEEPINFRA_KEY")
        self._backend: DeepInfraBackend | None = None
        self._fallback = CommitPredictor()
        self._call_count = 0
        self._fail_count = 0
        self._total_cost = 0.0
        self._total_latency_ms = 0.0

        # Initialize backend if key available
        if self._api_key:
            self._backend = DeepInfraBackend(
                api_key=self._api_key,
                model=self._model,
                max_tokens=100,
            )

    def predict(self, history: Sequence[CommitObservation]) -> Prediction:
        """Predict the next commit given recent history.

        Tries the model first, falls back to statistical if API fails.
        """
        # Always update the statistical fallback
        if history:
            # Re-prime fallback with the history we have
            self._fallback = CommitPredictor()
            for obs in history:
                self._fallback.observe(obs)

        ts = time.time()

        if not self._backend:
            logger.debug("No backend available, using statistical fallback")
            return self._fallback.predict()

        if len(history) < 2:
            logger.debug("Insufficient history for model prediction")
            return self._fallback.predict()

        # Try the model
        try:
            result = self._call_model(history)
            self._call_count += 1
            return result
        except Exception as e:
            self._fail_count += 1
            logger.warning(f"Model prediction failed ({self._fail_count}th fail): {e}")
            return self._fallback.predict()

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def fail_count(self) -> int:
        return self._fail_count

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def total_latency_ms(self) -> float:
        return self._total_latency_ms

    @property
    def is_available(self) -> bool:
        return self._backend is not None

    def _call_model(self, history: Sequence[CommitObservation]) -> Prediction:
        """Make the actual API call to predict next commit."""
        # Build context from recent history
        recent = list(history[-self._max_context:])
        context_lines = []
        for obs in recent:
            context_lines.append(
                f"- repo={obs.repo}, type={obs.commit_type}, "
                f"size={obs.size_bucket}, files={obs.files_changed}, "
                f"+{obs.insertions}/-{obs.deletions}"
            )
        context_str = "\n".join(context_lines)

        prompt = (
            f"Given these recent commits:\n{context_str}\n\n"
            f"Predict the NEXT commit. Respond ONLY with valid JSON:\n"
            f'{{"repo": "<one of: {", ".join(self.KNOWN_REPOS)}>", '
            f'"type": "<one of: {", ".join(self.KNOWN_TYPES)}>", '
            f'"size": "<one of: {", ".join(self.KNOWN_SIZES)}>", '
            f'"confidence": <0.0-1.0>}}'
        )

        start = time.monotonic()
        raw = self._backend._raw_call(
            [{"role": "user", "content": prompt}],
            max_tokens=80,
            temperature=0.3,
        )
        elapsed = (time.monotonic() - start) * 1000
        self._total_latency_ms += elapsed

        msg = raw["choices"][0]["message"]
        content = msg.get("content", "") or ""
        # Qwen 3.x puts output in reasoning_content when thinking
        if not content.strip():
            content = msg.get("reasoning_content", "") or ""
        usage = raw.get("usage", {})
        # Estimate cost: Qwen 0.8B is ~$0.01/M input, $0.05/M output
        inp = usage.get("prompt_tokens", 0)
        out = usage.get("completion_tokens", 0)
        cost = (inp * 0.01 + out * 0.05) / 1_000_000
        self._total_cost += cost

        # Parse the response
        parsed = self._parse_prediction(content)

        return Prediction(
            repo=parsed.get("repo", "unknown"),
            commit_type=parsed.get("type", "unknown"),
            size_bucket=parsed.get("size", "medium"),
            cross_pollination_prob=0.0,
            confidence=parsed.get("confidence", 0.3),
            timestamp=time.time(),
            metadata={
                "source": "model",
                "model": self._model,
                "latency_ms": round(elapsed, 1),
                "cost": cost,
                "raw_response": content[:200],
            },
        )

    def _parse_prediction(self, content: str) -> Dict[str, Any]:
        """Extract prediction from model output."""
        content = content.strip()
        # Try direct JSON parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        # Try extracting JSON block
        match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        # Try ```json ... ```
        match = re.search(r'```(?:json)?\s*\n?(.*?)```', content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        logger.warning(f"Failed to parse model output: {content[:200]}")
        return {}


# ── 2. HybridPredictor ─────────────────────────────────────────────────────

@dataclass
class HybridResult:
    """Result from a hybrid prediction showing both sources."""
    prediction: Prediction
    stats_prediction: Prediction
    model_prediction: Prediction | None
    agreement: bool           # did stats and model agree on all dimensions?
    source: str               # "stats", "model", or "hybrid"
    metadata: Dict[str, Any] = field(default_factory=dict)


class HybridPredictor:
    """Combines statistical frequency tables with model predictions.

    Strategy:
    - Statistical as baseline (cheap, fast)
    - Model for tie-breaking and novel patterns
    - When both agree → high confidence
    - When they disagree → gap detector gets activated at lower threshold
    """

    def __init__(
        self,
        model_predictor: ModelPredictor | None = None,
        history_window: int = 20,
    ) -> None:
        self._model_predictor = model_predictor or ModelPredictor()
        self._stats_predictor = CommitPredictor()
        self._history: List[CommitObservation] = []
        self._history_window = history_window
        self._predictions_made = 0
        self._agreements = 0
        self._disagreements = 0

    def observe(self, commit: CommitObservation) -> None:
        """Feed an observation to the statistical predictor and history."""
        self._stats_predictor.observe(commit)
        self._history.append(commit)
        # Trim history
        if len(self._history) > self._history_window:
            self._history = self._history[-self._history_window:]

    def predict(self, use_model: bool = True) -> HybridResult:
        """Generate a hybrid prediction."""
        self._predictions_made += 1

        # Always get statistical prediction
        stats_pred = self._stats_predictor.predict()

        if not use_model or not self._model_predictor.is_available:
            return HybridResult(
                prediction=stats_pred,
                stats_prediction=stats_pred,
                model_prediction=None,
                agreement=True,
                source="stats",
            )

        # Get model prediction
        model_pred = self._model_predictor.predict(self._history)

        # Compare
        agreement = (
            stats_pred.repo == model_pred.repo
            and stats_pred.commit_type == model_pred.commit_type
            and stats_pred.size_bucket == model_pred.size_bucket
        )

        if agreement:
            self._agreements += 1
            # Boost confidence when both agree
            boosted_conf = min(1.0, (stats_pred.confidence + model_pred.confidence) / 2 * 1.2)
            final_pred = Prediction(
                repo=stats_pred.repo,
                commit_type=stats_pred.commit_type,
                size_bucket=stats_pred.size_bucket,
                cross_pollination_prob=stats_pred.cross_pollination_prob,
                confidence=boosted_conf,
                timestamp=time.time(),
                metadata={
                    "source": "hybrid_agree",
                    "stats_conf": stats_pred.confidence,
                    "model_conf": model_pred.confidence,
                },
            )
            return HybridResult(
                prediction=final_pred,
                stats_prediction=stats_pred,
                model_prediction=model_pred,
                agreement=True,
                source="hybrid",
            )

        self._disagreements += 1

        # Disagreement: use model for repo/type (pattern recognition),
        # stats for size (more reliable statistically)
        # But if model confidence is low, defer to stats
        if model_pred.confidence > stats_pred.confidence * 0.8:
            # Model seems reasonable — use it for repo and type
            final_pred = Prediction(
                repo=model_pred.repo,
                commit_type=model_pred.commit_type,
                size_bucket=stats_pred.size_bucket,  # stats better for size
                cross_pollination_prob=stats_pred.cross_pollination_prob,
                confidence=(model_pred.confidence + stats_pred.confidence) / 2,
                timestamp=time.time(),
                metadata={
                    "source": "hybrid_disagree_model",
                    "stats_conf": stats_pred.confidence,
                    "model_conf": model_pred.confidence,
                    "disagree_dims": self._disagree_dims(stats_pred, model_pred),
                },
            )
        else:
            # Model not confident — trust stats
            final_pred = Prediction(
                repo=stats_pred.repo,
                commit_type=stats_pred.commit_type,
                size_bucket=stats_pred.size_bucket,
                cross_pollination_prob=stats_pred.cross_pollination_prob,
                confidence=stats_pred.confidence * 0.9,  # slight discount
                timestamp=time.time(),
                metadata={
                    "source": "hybrid_disagree_stats",
                    "stats_conf": stats_pred.confidence,
                    "model_conf": model_pred.confidence,
                },
            )

        return HybridResult(
            prediction=final_pred,
            stats_prediction=stats_pred,
            model_prediction=model_pred,
            agreement=False,
            source="hybrid",
        )

    def _disagree_dims(self, a: Prediction, b: Prediction) -> List[str]:
        """Which dimensions disagree?"""
        dims = []
        if a.repo != b.repo:
            dims.append("repo")
        if a.commit_type != b.commit_type:
            dims.append("type")
        if a.size_bucket != b.size_bucket:
            dims.append("size")
        return dims

    @property
    def agreement_rate(self) -> float:
        if self._predictions_made == 0:
            return 0.0
        return self._agreements / self._predictions_made

    @property
    def stats_predictor(self) -> CommitPredictor:
        return self._stats_predictor

    @property
    def model_predictor(self) -> ModelPredictor:
        return self._model_predictor

    @property
    def predictions_made(self) -> int:
        return self._predictions_made

    @property
    def total_cost(self) -> float:
        return self._model_predictor.total_cost


# ── 3. AdaptiveRouter ───────────────────────────────────────────────────────

class AdaptiveRouter:
    """Decides when to call the model vs use stats alone.

    Routing logic:
    - First N predictions: stats only (building baseline)
    - After warmup: model for every Kth prediction (sampling)
    - If gap rate > 50%: call model every time (we're getting surprised)
    - If gap rate < 10%: call model every 10th (we're predicting well)
    """

    def __init__(
        self,
        hybrid: HybridPredictor,
        warmup: int = 10,
        sample_every: int = 5,
        high_gap_threshold: float = 0.5,
        low_gap_threshold: float = 0.1,
    ) -> None:
        self._hybrid = hybrid
        self._warmup = warmup
        self._sample_every = sample_every
        self._high_gap_threshold = high_gap_threshold
        self._low_gap_threshold = low_gap_threshold

        # State
        self._predictions_made = 0
        self._model_calls = 0
        self._stats_only_calls = 0
        self._gap_scores: List[float] = []
        self._current_sample_rate = sample_every
        self._routing_log: List[Dict[str, Any]] = []

    def predict_and_observe(
        self,
        observation: CommitObservation,
    ) -> Tuple[HybridResult, float]:
        """Predict, then observe. Returns (hybrid_result, gap_score).

        The gap_score is computed against the observation (how wrong were we).
        """
        # Decide: model or stats only?
        use_model = self._should_use_model()

        # Predict
        result = self._hybrid.predict(use_model=use_model)
        pred = result.prediction
        self._predictions_made += 1

        if use_model:
            self._model_calls += 1
        else:
            self._stats_only_calls += 1

        # Compute gap score
        gap_score = self._compute_gap(pred, observation)
        self._gap_scores.append(gap_score)

        # Feed observation
        self._hybrid.observe(observation)

        # Update sampling rate based on recent gap rate
        self._update_sample_rate()

        # Log
        self._routing_log.append({
            "step": self._predictions_made,
            "use_model": use_model,
            "gap_score": gap_score,
            "agreement": result.agreement,
            "source": result.source,
            "sample_rate": self._current_sample_rate,
        })

        return result, gap_score

    @property
    def gap_rate(self) -> float:
        """Fraction of predictions with gap > 0.3 (above deadband)."""
        if not self._gap_scores:
            return 0.0
        above = sum(1 for g in self._gap_scores if g > 0.3)
        return above / len(self._gap_scores)

    @property
    def recent_gap_rate(self) -> float:
        """Gap rate over the last 10 predictions."""
        recent = self._gap_scores[-10:]
        if not recent:
            return 0.0
        above = sum(1 for g in recent if g > 0.3)
        return above / len(recent)

    @property
    def model_call_fraction(self) -> float:
        if self._predictions_made == 0:
            return 0.0
        return self._model_calls / self._predictions_made

    @property
    def total_cost(self) -> float:
        return self._hybrid.total_cost

    @property
    def routing_log(self) -> List[Dict[str, Any]]:
        return list(self._routing_log)

    def summary(self) -> Dict[str, Any]:
        return {
            "predictions_made": self._predictions_made,
            "model_calls": self._model_calls,
            "stats_only_calls": self._stats_only_calls,
            "model_fraction": round(self.model_call_fraction, 3),
            "gap_rate": round(self.gap_rate, 3),
            "recent_gap_rate": round(self.recent_gap_rate, 3),
            "current_sample_rate": self._current_sample_rate,
            "avg_gap": round(sum(self._gap_scores) / max(len(self._gap_scores), 1), 4),
            "total_cost": f"${self.total_cost:.6f}",
        }

    def _should_use_model(self) -> bool:
        """Routing decision."""
        # Warmup phase: stats only
        if self._predictions_made < self._warmup:
            return False

        # High gap rate: call model every time
        if self.recent_gap_rate > self._high_gap_threshold:
            return True

        # Low gap rate: call model infrequently
        if self.recent_gap_rate < self._low_gap_threshold:
            return (self._predictions_made % 10) == 0

        # Normal: sample at current rate
        return (self._predictions_made % self._current_sample_rate) == 0

    def _update_sample_rate(self) -> None:
        """Adjust how often we call the model based on recent performance."""
        if len(self._gap_scores) < 5:
            return
        recent_rate = self.recent_gap_rate
        if recent_rate > 0.5:
            self._current_sample_rate = 1  # every time
        elif recent_rate > 0.3:
            self._current_sample_rate = 3
        elif recent_rate > 0.15:
            self._current_sample_rate = 5
        else:
            self._current_sample_rate = 10

    @staticmethod
    def _compute_gap(pred: Prediction, obs: CommitObservation) -> float:
        """Simple gap computation (matches collective.py GapDetector weights)."""
        repo_gap = 0.0 if pred.repo == obs.repo else 1.0
        type_gap = 0.0 if pred.commit_type == obs.commit_type else 1.0
        size_gap = 0.0 if pred.size_bucket == obs.size_bucket else 1.0
        return round(
            repo_gap * 0.4 + type_gap * 0.3 + size_gap * 0.2,
            4,
        )
