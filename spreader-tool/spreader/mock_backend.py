"""Deterministic mock model backend for testing and benchmarking.

Returns deterministic responses based on input hash, simulates latency,
tracks all calls for assertions, and supports both "correct" and "error"
modes for testing validation.
"""

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MockCall:
    """Record of a single mock backend call."""
    prompt: str
    context: dict
    response: dict
    latency_ms: float
    tier: str
    timestamp: float


class MockModelBackend:
    """Deterministic model backend for testing.

    Configuration:
        base_latency_ms: simulated latency per call (default 0 for speed)
        error_rate: fraction of calls that return error responses (0.0–1.0)
        error_message: what error responses contain
        tier_latencies: per-tier latency overrides {tier: ms}
    """

    def __init__(
        self,
        base_latency_ms: float = 0.0,
        error_rate: float = 0.0,
        error_message: str = "MODEL_ERROR",
        tier_latencies: Optional[Dict[str, float]] = None,
    ) -> None:
        self.base_latency_ms = base_latency_ms
        self.error_rate = error_rate
        self.error_message = error_message
        self.tier_latencies = tier_latencies or {}
        self._calls: List[MockCall] = []

    def inference(self, prompt: str, context: dict) -> dict:
        """Deterministic inference based on input hash.

        Returns a response dict with:
          - "label": derived deterministically from prompt hash
          - "confidence": 0.0–1.0, derived from hash
          - "error": present if error_rate triggers
        """
        start = time.monotonic()

        # Deterministic hash from prompt + sorted context
        hasher = hashlib.sha256()
        hasher.update(prompt.encode())
        hasher.update(json.dumps(context, sort_keys=True).encode())
        h = int(hasher.hexdigest(), 16)

        # Determine tier from context
        tier = context.get("_tier", "full")
        latency = self.tier_latencies.get(tier, self.base_latency_ms)
        if latency > 0:
            time.sleep(latency / 1000.0)

        # Error injection
        if self.error_rate > 0:
            # Use top byte of hash to decide error
            error_byte = (h >> 248) & 0xFF
            if (error_byte / 255.0) < self.error_rate:
                response = {"error": self.error_message, "confidence": 0.0}
                elapsed = (time.monotonic() - start) * 1000
                self._calls.append(MockCall(
                    prompt=prompt, context=context,
                    response=response, latency_ms=elapsed,
                    tier=tier, timestamp=time.time(),
                ))
                return response

        # Deterministic label from hash
        label_idx = h % 3
        labels = ["ham", "spam", "ambiguous"]
        label = labels[label_idx]

        # Deterministic confidence: 0.5–1.0 range
        confidence_raw = ((h >> 16) & 0xFFFF) / 0xFFFF
        confidence = 0.5 + 0.5 * confidence_raw

        # Deterministic intent for higher tiers
        intents = ["promotional", "phishing", "transactional", "personal", "newsletter"]
        intent = intents[(h >> 8) % len(intents)]

        response = {
            "label": label,
            "confidence": round(confidence, 4),
            "intent": intent,
        }

        elapsed = (time.monotonic() - start) * 1000
        self._calls.append(MockCall(
            prompt=prompt, context=context,
            response=response, latency_ms=elapsed,
            tier=tier, timestamp=time.time(),
        ))
        return response

    def validate(self, response: dict, expected: dict | None) -> float:
        """Validate a response, returning confidence score.

        If expected is provided, checks label match and returns boosted score.
        If response has error, returns 0.0.
        """
        if "error" in response:
            return 0.0
        score = response.get("confidence", 0.0)
        if expected and "label" in expected:
            if response.get("label") == expected["label"]:
                score = min(1.0, score + 0.1)
            else:
                score *= 0.5
        return round(score, 4)

    @property
    def calls(self) -> List[MockCall]:
        """Return list of all recorded calls."""
        return list(self._calls)

    @property
    def call_count(self) -> int:
        """Number of calls made."""
        return len(self._calls)

    def total_latency_ms(self) -> float:
        """Sum of all call latencies."""
        return sum(c.latency_ms for c in self._calls)

    def reset(self) -> None:
        """Clear all recorded calls."""
        self._calls.clear()
