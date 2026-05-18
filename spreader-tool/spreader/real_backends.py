"""Real model backends for production use — v2 with full API adapters.

Groq: Llama 3.3 70B — fast inference, good for classification
DeepInfra: Seed-2.0-mini / Seed-2.0-code — cheap, good for bulk processing
EnsembleBackend: cheapest-first routing with health-aware fallback
BackendHealth: connectivity check + latency measurement
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Credential helpers ────────────────────────────────────────────────

_CRED_DIR = Path.home() / ".openclaw" / "workspace" / ".credentials"


def _load_key(filename: str, env_var: str) -> str:
    """Load API key from file, falling back to environment variable."""
    env_val = os.environ.get(env_var, "")
    if env_val:
        return env_val
    key_file = _CRED_DIR / filename
    if key_file.exists():
        return key_file.read_text().strip()
    return ""


# ── Base ──────────────────────────────────────────────────────────────

class BackendError(Exception):
    """Raised when a backend call fails after retries."""


@dataclass
class CallRecord:
    """Tracks a single API call."""
    method: str
    model: str
    latency_ms: float
    cost: float
    tokens_in: int = 0
    tokens_out: int = 0
    success: bool = True
    error: str | None = None


class RealModelBackend:
    """Base class for real API backends."""

    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0  # seconds, doubled each retry
    TIMEOUT: float = 30.0     # seconds

    def __init__(self, model: str, api_key: str | None = None, max_tokens: int = 150):
        self._model = model
        self._api_key = api_key or ""
        self._max_tokens = max_tokens
        self._call_history: list[CallRecord] = []
        self._healthy: bool | None = None  # None = unchecked

    # ── Metrics ───────────────────────────────────────────────────

    @property
    def call_count(self) -> int:
        return len([c for c in self._call_history if c.success])

    @property
    def total_latency_ms(self) -> float:
        return sum(c.latency_ms for c in self._call_history if c.success)

    @property
    def total_cost(self) -> float:
        return sum(c.cost for c in self._call_history if c.success)

    @property
    def is_healthy(self) -> bool | None:
        return self._healthy

    @property
    def call_history(self) -> list[CallRecord]:
        return list(self._call_history)

    # ── Public API ────────────────────────────────────────────────

    def classify(self, text: str, labels: list[str] | None = None) -> dict:
        """Single-label classification. Returns {label, confidence, reasoning}."""
        raise NotImplementedError

    def score(self, text: str, metric: str = "relevance") -> dict:
        """Score text on a 0-1 scale. Returns {score, metric, reasoning}."""
        raise NotImplementedError

    def generate(self, prompt: str, max_tokens: int | None = None) -> dict:
        """Free-form text generation. Returns {text, tokens, cost}."""
        raise NotImplementedError

    def inference(self, prompt: str, context: dict) -> dict:
        """Legacy interface for PipelineRoom compatibility."""
        labels = context.get("labels", ["ham", "spam", "ambiguous"])
        return self.classify(prompt, labels)

    def health_check(self) -> BackendHealth:
        """Test connectivity and measure latency. Returns BackendHealth."""
        raise NotImplementedError

    # ── Internals ─────────────────────────────────────────────────

    def _raw_call(self, messages: list[dict], **kwargs) -> dict:
        """Make an API call with retry logic. Returns raw API response dict."""
        raise NotImplementedError

    def _estimate_cost(self, usage: dict) -> float:
        raise NotImplementedError

    def _record(self, record: CallRecord) -> None:
        self._call_history.append(record)

    def _parse_json_response(self, content: str) -> dict:
        """Extract JSON from model output (may be wrapped in markdown)."""
        # Try direct parse first
        content = content.strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        # Try extracting JSON block
        json_match = re.search(r'\{[^}]+\}', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        # Try ```json ... ``` block
        code_match = re.search(r'```(?:json)?\s*\n?(.*?)```', content, re.DOTALL)
        if code_match:
            try:
                return json.loads(code_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        return {"raw": content}

    def validate(self, response: dict, expected: dict | None) -> float:
        """Validate model response and return confidence 0-1."""
        if not response:
            return 0.0
        label = response.get("label", "")
        conf = response.get("confidence", 0.0)
        if label in ("ham", "spam") and 0.0 <= conf <= 1.0:
            return conf
        return 0.0


# ── Backend Health ────────────────────────────────────────────────────

@dataclass
class BackendHealth:
    """Health check result for a backend."""
    backend_name: str
    is_healthy: bool
    latency_ms: float = 0.0
    error: str | None = None
    model: str = ""
    checked_at: float = field(default_factory=time.time)

    @property
    def status(self) -> str:
        return "healthy" if self.is_healthy else "unhealthy"


# ── Groq Backend ──────────────────────────────────────────────────────

class GroqBackend(RealModelBackend):
    """Groq API backend — Llama 3.3 70B, fast inference."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    # Pricing: $0.59/M input, $0.79/M output
    COST_PER_M_INPUT = 0.59
    COST_PER_M_OUTPUT = 0.79

    def __init__(self, api_key: str | None = None,
                 model: str = "llama-3.3-70b-versatile",
                 max_tokens: int = 150):
        key = api_key or _load_key("groq-api-key.txt", "GROQ_API_KEY")
        super().__init__(model=model, api_key=key, max_tokens=max_tokens)

    def classify(self, text: str, labels: list[str] | None = None) -> dict:
        labels = labels or ["ham", "spam", "ambiguous"]
        system = (
            "You are a precise classifier. Respond ONLY with valid JSON:\n"
            '{"label": "<one of: ' + "|".join(labels) + '>", '
            '"confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}'
        )
        raw = self._raw_call([
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ])
        content = raw["choices"][0]["message"]["content"]
        result = self._parse_json_response(content)
        # Ensure label is valid
        if result.get("label") not in labels:
            result["label"] = "ambiguous"
        if "confidence" not in result or not isinstance(result["confidence"], (int, float)):
            result["confidence"] = 0.5
        result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
        result["_model"] = self._model
        return result

    def score(self, text: str, metric: str = "relevance") -> dict:
        system = (
            f"You are a scoring assistant. Score the text on '{metric}' from 0.0 to 1.0.\n"
            'Respond ONLY with valid JSON: {"score": <0.0-1.0>, "metric": "'
            + metric
            + '", "reasoning": "<brief explanation>"}'
        )
        raw = self._raw_call([
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ])
        content = raw["choices"][0]["message"]["content"]
        result = self._parse_json_response(content)
        result.setdefault("score", 0.5)
        result["score"] = max(0.0, min(1.0, float(result["score"])))
        result["metric"] = metric
        result["_model"] = self._model
        return result

    def generate(self, prompt: str, max_tokens: int | None = None) -> dict:
        mt = max_tokens or self._max_tokens
        raw = self._raw_call(
            [{"role": "user", "content": prompt}],
            max_tokens=mt,
        )
        content = raw["choices"][0]["message"]["content"]
        usage = raw.get("usage", {})
        return {
            "text": content,
            "tokens": usage.get("completion_tokens", 0),
            "cost": self._estimate_cost(usage),
            "_model": self._model,
        }

    def health_check(self) -> BackendHealth:
        if not self._api_key:
            return BackendHealth("groq", False, error="No API key configured", model=self._model)
        try:
            start = time.monotonic()
            raw = self._raw_call(
                [{"role": "user", "content": "Reply with OK"}],
                max_tokens=5,
            )
            elapsed = (time.monotonic() - start) * 1000
            content = raw["choices"][0]["message"]["content"].strip()
            healthy = bool(content)
            self._healthy = healthy
            return BackendHealth("groq", healthy, latency_ms=round(elapsed, 1), model=self._model)
        except Exception as e:
            self._healthy = False
            return BackendHealth("groq", False, error=str(e), model=self._model)

    def _raw_call(self, messages: list[dict], **kwargs) -> dict:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": self._model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "temperature": kwargs.get("temperature", 0.1),
        }).encode()

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                req = urllib.request.Request(
                    self.BASE_URL,
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                start = time.monotonic()
                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                    data = json.loads(resp.read().decode())
                elapsed = (time.monotonic() - start) * 1000
                usage = data.get("usage", {})
                cost = self._estimate_cost(usage)
                self._record(CallRecord(
                    method="raw", model=self._model,
                    latency_ms=round(elapsed, 1), cost=cost,
                    tokens_in=usage.get("prompt_tokens", 0),
                    tokens_out=usage.get("completion_tokens", 0),
                ))
                return data
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code == 429:  # Rate limited
                    delay = self.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Groq rate limited, retrying in {delay}s (attempt {attempt+1}/{self.MAX_RETRIES})")
                    time.sleep(delay)
                elif e.code >= 500:
                    delay = self.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Groq server error {e.code}, retrying in {delay}s")
                    time.sleep(delay)
                else:
                    self._record(CallRecord(
                        method="raw", model=self._model,
                        latency_ms=0, cost=0, success=False,
                        error=f"HTTP {e.code}: {e.reason}",
                    ))
                    raise BackendError(f"Groq API error: HTTP {e.code}: {e.reason}") from e
            except Exception as e:
                last_error = e
                delay = self.RETRY_DELAY * (2 ** attempt)
                logger.warning(f"Groq call failed: {e}, retrying in {delay}s")
                time.sleep(delay)

        self._record(CallRecord(
            method="raw", model=self._model,
            latency_ms=0, cost=0, success=False,
            error=str(last_error),
        ))
        raise BackendError(f"Groq API failed after {self.MAX_RETRIES} retries: {last_error}") from last_error

    def _estimate_cost(self, usage: dict) -> float:
        inp = usage.get("prompt_tokens", 0)
        out = usage.get("completion_tokens", 0)
        return (inp * self.COST_PER_M_INPUT + out * self.COST_PER_M_OUTPUT) / 1_000_000


# ── DeepInfra Backend ─────────────────────────────────────────────────

class DeepInfraBackend(RealModelBackend):
    """DeepInfra API backend — Seed-2.0-mini/code, cheap and capable."""

    BASE_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
    # Seed-2.0-mini pricing: ~$0.01/query (flat approximation)
    COST_PER_QUERY_APPROX = 0.01

    def __init__(self, api_key: str | None = None,
                 model: str = "ByteDance/Seed-2.0-mini",
                 max_tokens: int = 150):
        key = api_key or _load_key("deepinfra-api-key.txt", "DEEPINFRA_KEY")
        super().__init__(model=model, api_key=key, max_tokens=max_tokens)

    def classify(self, text: str, labels: list[str] | None = None) -> dict:
        labels = labels or ["ham", "spam", "ambiguous"]
        system = (
            "You are a precise classifier. Respond ONLY with valid JSON:\n"
            '{"label": "<one of: ' + "|".join(labels) + '>", '
            '"confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}'
        )
        raw = self._raw_call([
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ])
        content = raw["choices"][0]["message"]["content"]
        result = self._parse_json_response(content)
        if result.get("label") not in labels:
            result["label"] = "ambiguous"
        if "confidence" not in result or not isinstance(result["confidence"], (int, float)):
            result["confidence"] = 0.5
        result["confidence"] = max(0.0, min(1.0, float(result["confidence"])))
        result["_model"] = self._model
        return result

    def score(self, text: str, metric: str = "relevance") -> dict:
        system = (
            f"You are a scoring assistant. Score the text on '{metric}' from 0.0 to 1.0.\n"
            'Respond ONLY with valid JSON: {"score": <0.0-1.0>, "metric": "'
            + metric
            + '", "reasoning": "<brief explanation>"}'
        )
        raw = self._raw_call([
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ])
        content = raw["choices"][0]["message"]["content"]
        result = self._parse_json_response(content)
        result.setdefault("score", 0.5)
        result["score"] = max(0.0, min(1.0, float(result["score"])))
        result["metric"] = metric
        result["_model"] = self._model
        return result

    def generate(self, prompt: str, max_tokens: int | None = None) -> dict:
        mt = max_tokens or self._max_tokens
        raw = self._raw_call(
            [{"role": "user", "content": prompt}],
            max_tokens=mt,
        )
        content = raw["choices"][0]["message"]["content"]
        usage = raw.get("usage", {})
        return {
            "text": content,
            "tokens": usage.get("completion_tokens", 0),
            "cost": self._estimate_cost(usage),
            "_model": self._model,
        }

    def health_check(self) -> BackendHealth:
        if not self._api_key:
            return BackendHealth("deepinfra", False, error="No API key configured", model=self._model)
        try:
            start = time.monotonic()
            raw = self._raw_call(
                [{"role": "user", "content": "Reply with OK"}],
                max_tokens=5,
            )
            elapsed = (time.monotonic() - start) * 1000
            content = raw["choices"][0]["message"]["content"].strip()
            healthy = bool(content)
            self._healthy = healthy
            return BackendHealth("deepinfra", healthy, latency_ms=round(elapsed, 1), model=self._model)
        except Exception as e:
            self._healthy = False
            return BackendHealth("deepinfra", False, error=str(e), model=self._model)

    def _raw_call(self, messages: list[dict], **kwargs) -> dict:
        import urllib.request
        import urllib.error

        payload = json.dumps({
            "model": self._model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
            "temperature": kwargs.get("temperature", 0.1),
        }).encode()

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                req = urllib.request.Request(
                    self.BASE_URL,
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                start = time.monotonic()
                with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
                    data = json.loads(resp.read().decode())
                elapsed = (time.monotonic() - start) * 1000
                usage = data.get("usage", {})
                cost = self._estimate_cost(usage)
                self._record(CallRecord(
                    method="raw", model=self._model,
                    latency_ms=round(elapsed, 1), cost=cost,
                    tokens_in=usage.get("prompt_tokens", 0),
                    tokens_out=usage.get("completion_tokens", 0),
                ))
                return data
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code == 429:
                    delay = self.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"DeepInfra rate limited, retrying in {delay}s")
                    time.sleep(delay)
                elif e.code >= 500:
                    delay = self.RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"DeepInfra server error {e.code}, retrying in {delay}s")
                    time.sleep(delay)
                else:
                    self._record(CallRecord(
                        method="raw", model=self._model,
                        latency_ms=0, cost=0, success=False,
                        error=f"HTTP {e.code}: {e.reason}",
                    ))
                    raise BackendError(f"DeepInfra API error: HTTP {e.code}: {e.reason}") from e
            except Exception as e:
                last_error = e
                delay = self.RETRY_DELAY * (2 ** attempt)
                logger.warning(f"DeepInfra call failed: {e}, retrying in {delay}s")
                time.sleep(delay)

        self._record(CallRecord(
            method="raw", model=self._model,
            latency_ms=0, cost=0, success=False,
            error=str(last_error),
        ))
        raise BackendError(f"DeepInfra API failed after {self.MAX_RETRIES} retries: {last_error}") from last_error

    def _estimate_cost(self, usage: dict) -> float:
        return self.COST_PER_QUERY_APPROX


# ── Ensemble Backend ──────────────────────────────────────────────────

class EnsembleBackend:
    """Routes to cheapest available backend, falls back on failure.

    Priority order (cheapest first):
      1. DeepInfra (cheapest)
      2. Groq (fastest)
      3. Error (all backends exhausted)

    Tracks cumulative cost per session and enforces budget.
    """

    def __init__(self, backends: list[RealModelBackend] | None = None,
                 session_budget: float = 1.0):
        if backends is None:
            # Auto-create with real keys
            deepinfra_key = _load_key("deepinfra-api-key.txt", "DEEPINFRA_KEY")
            groq_key = _load_key("groq-api-key.txt", "GROQ_API_KEY")
            created = []
            if deepinfra_key:
                created.append(DeepInfraBackend(api_key=deepinfra_key))
            if groq_key:
                created.append(GroqBackend(api_key=groq_key))
            self._backends = created
        else:
            self._backends = list(backends)
        self._session_budget = session_budget
        self._session_cost = 0.0
        self._call_count = 0
        self._fallback_count = 0

    @property
    def session_cost(self) -> float:
        return self._session_cost

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def fallback_count(self) -> int:
        return self._fallback_count

    @property
    def remaining_budget(self) -> float:
        return max(0.0, self._session_budget - self._session_cost)

    @property
    def budget_exhausted(self) -> bool:
        return self._session_cost >= self._session_budget

    def _pick_backend(self) -> RealModelBackend:
        """Select the cheapest healthy backend."""
        for backend in self._backends:
            if backend.is_healthy is False:
                continue
            return backend
        # All marked unhealthy — try first anyway
        if self._backends:
            return self._backends[0]
        raise BackendError("No backends available in ensemble")

    def classify(self, text: str, labels: list[str] | None = None) -> dict:
        if self.budget_exhausted:
            raise BackendError(f"Session budget exhausted: ${self._session_cost:.4f} / ${self._session_budget:.4f}")
        return self._route("classify", text, labels)

    def score(self, text: str, metric: str = "relevance") -> dict:
        if self.budget_exhausted:
            raise BackendError(f"Session budget exhausted: ${self._session_cost:.4f} / ${self._session_budget:.4f}")
        return self._route("score", text, metric)

    def generate(self, prompt: str, max_tokens: int | None = None) -> dict:
        if self.budget_exhausted:
            raise BackendError(f"Session budget exhausted: ${self._session_cost:.4f} / ${self._session_budget:.4f}")
        return self._route("generate", prompt, max_tokens)

    def health_check_all(self) -> list[BackendHealth]:
        """Run health checks on all backends."""
        results = []
        for backend in self._backends:
            health = backend.health_check()
            results.append(health)
        return results

    def _route(self, method: str, *args, **kwargs) -> dict:
        """Route a call through backends with fallback."""
        tried = set()
        for backend in self._backends:
            bid = id(backend)
            if bid in tried:
                continue
            tried.add(bid)
            try:
                fn = getattr(backend, method)
                result = fn(*args, **kwargs)
                cost = result.get("cost", backend.total_cost)
                self._session_cost += cost if isinstance(cost, (int, float)) else 0.01
                self._call_count += 1
                return result
            except (BackendError, Exception) as e:
                logger.warning(f"Backend {backend._model} failed for {method}: {e}")
                backend._healthy = False
                self._fallback_count += 1
                continue

        raise BackendError(f"All backends failed for {method}")

    def inference(self, prompt: str, context: dict) -> dict:
        """Legacy interface compatibility."""
        return self.classify(prompt, context.get("labels"))


# ── Backend Factory ───────────────────────────────────────────────────

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
        if _load_key("groq-api-key.txt", "GROQ_API_KEY"):
            available.append("groq")
        if _load_key("deepinfra-api-key.txt", "DEEPINFRA_KEY"):
            available.extend(["deepinfra", "seed-mini", "seed-code"])
        return available

    @staticmethod
    def create_ensemble(session_budget: float = 1.0) -> EnsembleBackend:
        """Create an EnsembleBackend with all available backends."""
        backends = []
        deepinfra_key = _load_key("deepinfra-api-key.txt", "DEEPINFRA_KEY")
        groq_key = _load_key("groq-api-key.txt", "GROQ_API_KEY")
        if deepinfra_key:
            backends.append(DeepInfraBackend(api_key=deepinfra_key))
        if groq_key:
            backends.append(GroqBackend(api_key=groq_key))
        return EnsembleBackend(backends=backends, session_budget=session_budget)
