"""Real model backends for production use.

Groq: Llama 3.3 70B — fast inference, good for classification
DeepInfra: Seed-2.0-mini — cheap, good for bulk processing
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

# Lazy imports — only needed when actually calling APIs


class RealModelBackend:
    """Base class for real API backends."""

    def __init__(self, model: str, api_key: str | None = None, max_tokens: int = 150):
        self._model = model
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._call_count = 0
        self._total_latency = 0.0
        self._total_cost = 0.0

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def total_latency_ms(self) -> float:
        return self._total_latency

    @property
    def total_cost(self) -> float:
        return self._total_cost

    def inference(self, prompt: str, context: dict) -> dict:
        raise NotImplementedError

    def validate(self, response: dict, expected: dict | None) -> float:
        """Validate model response and return confidence 0-1."""
        if not response:
            return 0.0
        label = response.get("label", "")
        conf = response.get("confidence", 0.0)
        if label in ("ham", "spam") and 0.0 <= conf <= 1.0:
            return conf
        return 0.0


class GroqBackend(RealModelBackend):
    """Groq API backend — Llama 3.3 70B, fast inference."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str | None = None, model: str = "llama-3.3-70b-versatile",
                 max_tokens: int = 150):
        key = api_key or os.environ.get("GROQ_API_KEY", "")
        super().__init__(model=model, api_key=key, max_tokens=max_tokens)

    def inference(self, prompt: str, context: dict) -> dict:
        import urllib.request

        system_msg = (
            "You are a classifier. Respond ONLY with valid JSON: "
            '{"label": "ham"|"spam"|"ambiguous", "confidence": 0.0-1.0, "intent": "string"}'
        )

        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self._max_tokens,
            "temperature": 0.1,
        }).encode()

        req = urllib.request.Request(
            self.BASE_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        elapsed = (time.monotonic() - start) * 1000

        content = data["choices"][0]["message"]["content"].strip()
        # Parse JSON from response (model may wrap in markdown)
        json_match = re.search(r'\{[^}]+\}', content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"label": "ambiguous", "confidence": 0.0, "raw": content}

        self._call_count += 1
        self._total_latency += elapsed
        self._total_cost += self._estimate_cost(data.get("usage", {}))

        result["_latency_ms"] = round(elapsed, 1)
        result["_model"] = self._model
        return result

    def _estimate_cost(self, usage: dict) -> float:
        """Groq: $0.59/M input, $0.79/M output tokens."""
        inp = usage.get("prompt_tokens", 0)
        out = usage.get("completion_tokens", 0)
        return (inp * 0.59 + out * 0.79) / 1_000_000


class DeepInfraBackend(RealModelBackend):
    """DeepInfra API backend — Seed-2.0-mini, cheap and fast."""

    BASE_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

    def __init__(self, api_key: str | None = None, model: str = "ByteDance/Seed-2.0-mini",
                 max_tokens: int = 150):
        key = api_key or os.environ.get("DEEPINFRA_KEY", "")
        super().__init__(model=model, api_key=key, max_tokens=max_tokens)

    def inference(self, prompt: str, context: dict) -> dict:
        import urllib.request

        system_msg = (
            "You are a classifier. Respond ONLY with valid JSON: "
            '{"label": "ham"|"spam"|"ambiguous", "confidence": 0.0-1.0, "intent": "string"}'
        )

        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": self._max_tokens,
            "temperature": 0.1,
        }).encode()

        req = urllib.request.Request(
            self.BASE_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

        start = time.monotonic()
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        elapsed = (time.monotonic() - start) * 1000

        content = data["choices"][0]["message"]["content"].strip()
        json_match = re.search(r'\{[^}]+\}', content)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {"label": "ambiguous", "confidence": 0.0, "raw": content}

        self._call_count += 1
        self._total_latency += elapsed
        self._total_cost += self._estimate_cost(data.get("usage", {}))

        result["_latency_ms"] = round(elapsed, 1)
        result["_model"] = self._model
        return result

    def _estimate_cost(self, usage: dict) -> float:
        """DeepInfra Seed-2.0-mini: ~$0.01/query."""
        return 0.01


class BackendFactory:
    """Create backends from config strings."""

    @staticmethod
    def create(backend_type: str, **kwargs) -> RealModelBackend:
        if backend_type == "groq":
            return GroqBackend(**kwargs)
        elif backend_type in ("deepinfra", "seed-mini"):
            return DeepInfraBackend(**kwargs)
        elif backend_type == "seed-code":
            return DeepInfraBackend(model="ByteDance/Seed-2.0-code", **kwargs)
        else:
            raise ValueError(f"Unknown backend: {backend_type}. Use: groq, deepinfra, seed-mini, seed-code")

    @staticmethod
    def available() -> list[str]:
        """Check which backends have API keys configured."""
        available = []
        if os.environ.get("GROQ_API_KEY"):
            available.append("groq")
        if os.environ.get("DEEPINFRA_KEY"):
            available.extend(["deepinfra", "seed-mini", "seed-code"])
        return available
