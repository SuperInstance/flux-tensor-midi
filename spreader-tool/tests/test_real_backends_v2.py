"""Tests for real_backends v2 — API adapters with mock HTTP responses.

Tests mock the actual HTTP calls but use REAL API response schemas
so the production code works first try against live endpoints.
"""

from __future__ import annotations

import json
import os
import time
import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock, Mock, patch, call

from spreader.real_backends import (
    BackendError,
    BackendFactory,
    BackendHealth,
    CallRecord,
    DeepInfraBackend,
    EnsembleBackend,
    GroqBackend,
    RealModelBackend,
    _load_key,
)


# ── Fixtures: realistic API responses ─────────────────────────────────

def make_groq_response(content: str, prompt_tokens: int = 50, completion_tokens: int = 20) -> dict:
    """Real Groq API response schema."""
    return {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "llama-3.3-70b-versatile",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "prompt_time": 0.01,
            "completion_time": 0.02,
            "total_time": 0.03,
        },
    }


def make_deepinfra_response(content: str, prompt_tokens: int = 50, completion_tokens: int = 20) -> dict:
    """Real DeepInfra API response schema."""
    return {
        "id": "chatcmpl-xyz789",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "ByteDance/Seed-2.0-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def mock_urlopen(response_dict: dict, latency: float = 0.1):
    """Create a mock for urllib.request.urlopen that returns a response."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(response_dict).encode()
    mock_resp.__enter__ = Mock(return_value=mock_resp)
    mock_resp.__exit__ = Mock(return_value=False)
    return mock_resp


# ── Tests: Credential loading ─────────────────────────────────────────

class TestCredentialLoading(unittest.TestCase):
    """Test _load_key reads from file and env."""

    def test_load_from_env(self):
        with patch.dict(os.environ, {"TEST_KEY_X": "env-value-123"}):
            assert _load_key("nonexistent.txt", "TEST_KEY_X") == "env-value-123"

    def test_load_from_file(self):
        import tempfile
        from pathlib import Path
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("file-value-456\n")
            f.flush()
            # Patch the credential directory
            with patch("spreader.real_backends._CRED_DIR", Path(f.name).parent):
                # The filename should match
                result = _load_key(Path(f.name).name, "NONEXISTENT_ENV_VAR")
            os.unlink(f.name)
        assert result == "file-value-456"

    def test_load_empty_when_missing(self):
        result = _load_key("definitely-no-such-file-xyz.txt", "SURELY_NOT_SET_XYZ")
        assert result == ""


# ── Tests: GroqBackend ────────────────────────────────────────────────

class TestGroqBackendInit(unittest.TestCase):
    """Test GroqBackend initialization."""

    def test_init_with_explicit_key(self):
        be = GroqBackend(api_key="test-key-123")
        assert be._api_key == "test-key-123"
        assert be._model == "llama-3.3-70b-versatile"

    def test_init_loads_key_from_file(self):
        with patch("spreader.real_backends._load_key", return_value="file-key"):
            be = GroqBackend()
            assert be._api_key == "file-key"

    def test_initial_metrics_zero(self):
        be = GroqBackend(api_key="k")
        assert be.call_count == 0
        assert be.total_cost == 0.0
        assert be.total_latency_ms == 0.0
        assert be.is_healthy is None


class TestGroqHealthCheck(unittest.TestCase):
    """Test GroqBackend health_check."""

    def test_healthy_response(self):
        be = GroqBackend(api_key="test-key")
        resp = make_groq_response("OK")
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            health = be.health_check()
        assert health.is_healthy is True
        assert health.backend_name == "groq"
        assert health.latency_ms > 0
        assert be.is_healthy is True

    def test_no_api_key(self):
        be = GroqBackend(api_key="")
        health = be.health_check()
        assert health.is_healthy is False
        # Empty key either catches early or gets 403 from API
        assert health.error is not None

    def test_connection_error(self):
        be = GroqBackend(api_key="test-key")
        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            health = be.health_check()
        assert health.is_healthy is False
        assert "Connection refused" in health.error


class TestGroqClassify(unittest.TestCase):
    """Test GroqBackend.classify with mocked HTTP."""

    def test_classify_json_response(self):
        be = GroqBackend(api_key="test-key")
        resp = make_groq_response('{"label": "spam", "confidence": 0.95, "reasoning": "Obvious spam"}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            result = be.classify("Click here for free money!!!")
        assert result["label"] == "spam"
        assert result["confidence"] == 0.95
        assert result["_model"] == "llama-3.3-70b-versatile"

    def test_classify_markdown_wrapped_json(self):
        be = GroqBackend(api_key="test-key")
        content = '```json\n{"label": "ham", "confidence": 0.8}\n```'
        resp = make_groq_response(content)
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            result = be.classify("Meeting at 3pm")
        assert result["label"] == "ham"

    def test_classify_invalid_label_defaults_ambiguous(self):
        be = GroqBackend(api_key="test-key")
        resp = make_groq_response('{"label": "unknown_thing", "confidence": 0.5}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            result = be.classify("Test")
        assert result["label"] == "ambiguous"

    def test_classify_custom_labels(self):
        be = GroqBackend(api_key="test-key")
        resp = make_groq_response('{"label": "positive", "confidence": 0.9}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            result = be.classify("Great product!", labels=["positive", "negative", "neutral"])
        assert result["label"] == "positive"


class TestGroqScore(unittest.TestCase):
    """Test GroqBackend.score."""

    def test_score_response(self):
        be = GroqBackend(api_key="test-key")
        resp = make_groq_response('{"score": 0.82, "metric": "relevance", "reasoning": "On topic"}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            result = be.score("This is relevant text", "relevance")
        assert result["score"] == 0.82
        assert result["metric"] == "relevance"


class TestGroqGenerate(unittest.TestCase):
    """Test GroqBackend.generate."""

    def test_generate_response(self):
        be = GroqBackend(api_key="test-key")
        resp = make_groq_response("This is the generated text.", completion_tokens=30)
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            result = be.generate("Write a short summary")
        assert result["text"] == "This is the generated text."
        assert result["tokens"] == 30
        assert result["cost"] > 0


# ── Tests: DeepInfraBackend ───────────────────────────────────────────

class TestDeepInfraBackendInit(unittest.TestCase):
    """Test DeepInfraBackend initialization."""

    def test_init_default_model(self):
        be = DeepInfraBackend(api_key="test-key")
        assert be._model == "ByteDance/Seed-2.0-mini"

    def test_init_seed_code_model(self):
        be = DeepInfraBackend(api_key="test-key", model="ByteDance/Seed-2.0-code")
        assert be._model == "ByteDance/Seed-2.0-code"


class TestDeepInfraHealthCheck(unittest.TestCase):
    """Test DeepInfraBackend health_check."""

    def test_healthy(self):
        be = DeepInfraBackend(api_key="test-key")
        resp = make_deepinfra_response("OK")
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            health = be.health_check()
        assert health.is_healthy is True
        assert health.backend_name == "deepinfra"


class TestDeepInfraClassify(unittest.TestCase):
    """Test DeepInfraBackend.classify."""

    def test_classify(self):
        be = DeepInfraBackend(api_key="test-key")
        resp = make_deepinfra_response('{"label": "ham", "confidence": 0.88, "reasoning": "Legit"}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            result = be.classify("Can we meet Tuesday?")
        assert result["label"] == "ham"
        assert result["confidence"] == 0.88
        assert result["_model"] == "ByteDance/Seed-2.0-mini"


# ── Tests: Cost tracking ──────────────────────────────────────────────

class TestCostTracking(unittest.TestCase):
    """Test cost tracking across multiple calls."""

    def test_groq_cumulative_cost(self):
        be = GroqBackend(api_key="test-key")
        for _ in range(3):
            resp = make_groq_response('{"label": "ham", "confidence": 0.9}', prompt_tokens=100, completion_tokens=30)
            with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
                be.classify("test")
        assert be.call_count == 3
        assert be.total_cost > 0
        # Groq: (100 * 0.59 + 30 * 0.79) / 1_000_000 per call
        expected_per_call = (100 * 0.59 + 30 * 0.79) / 1_000_000
        assert abs(be.total_cost - 3 * expected_per_call) < 0.0001

    def test_deepinfra_flat_cost(self):
        be = DeepInfraBackend(api_key="test-key")
        resp = make_deepinfra_response('{"label": "spam", "confidence": 0.95}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            be.classify("spam text")
        assert be.total_cost == 0.01  # Flat rate

    def test_call_history_recorded(self):
        be = GroqBackend(api_key="test-key")
        resp = make_groq_response('{"label": "ham", "confidence": 0.9}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            be.classify("test")
        assert len(be.call_history) == 1
        record = be.call_history[0]
        assert isinstance(record, CallRecord)
        assert record.success is True
        assert record.tokens_in == 50
        assert record.tokens_out == 20

    def test_failed_call_recorded(self):
        import urllib.error
        be = GroqBackend(api_key="test-key")
        err = urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            try:
                be.classify("test")
            except BackendError:
                pass
        assert len(be.call_history) == 1
        assert be.call_history[0].success is False
        assert "401" in be.call_history[0].error


# ── Tests: Retry logic ────────────────────────────────────────────────

class TestRetryLogic(unittest.TestCase):
    """Test retry on transient failures."""

    def test_retry_on_rate_limit_then_succeed(self):
        import urllib.error
        be = GroqBackend(api_key="test-key")
        be.RETRY_DELAY = 0.01  # Fast retries in test
        rate_limit = urllib.error.HTTPError("url", 429, "Too Many Requests", {}, None)
        success_resp = make_groq_response('{"label": "ham", "confidence": 0.9}')
        mock_resp = mock_urlopen(success_resp)

        call_count = [0]
        def side_effect(*a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                raise rate_limit
            return mock_resp

        with patch("urllib.request.urlopen", side_effect=side_effect):
            result = be.classify("test")
        assert result["label"] == "ham"
        assert be.call_count == 1  # One successful call

    def test_retry_exhausted_raises(self):
        import urllib.error
        be = GroqBackend(api_key="test-key")
        be.MAX_RETRIES = 2
        be.RETRY_DELAY = 0.01
        err = urllib.error.HTTPError("url", 500, "Internal Server Error", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(BackendError) as ctx:
                be.classify("test")
            assert "2 retries" in str(ctx.exception)


# ── Tests: EnsembleBackend ────────────────────────────────────────────

class TestEnsembleRouting(unittest.TestCase):
    """Test EnsembleBackend routes to cheapest (first) backend."""

    def test_routes_to_first_backend(self):
        """DeepInfra is first (cheapest) — should be selected."""
        deep = DeepInfraBackend(api_key="deep-key")
        groq = GroqBackend(api_key="groq-key")
        ensemble = EnsembleBackend(backends=[deep, groq])

        resp = make_deepinfra_response('{"label": "ham", "confidence": 0.9}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            result = ensemble.classify("test email")
        assert result["label"] == "ham"
        assert ensemble.call_count == 1
        assert ensemble.fallback_count == 0

    def test_fallback_on_failure(self):
        """First backend fails → falls back to second."""
        import urllib.error
        deep = DeepInfraBackend(api_key="deep-key")
        groq = GroqBackend(api_key="groq-key")
        ensemble = EnsembleBackend(backends=[deep, groq])

        deep_err = urllib.error.HTTPError("url", 500, "Error", {}, None)
        groq_resp = make_groq_response('{"label": "spam", "confidence": 0.85}')

        call_count = [0]
        def side_effect(req, *a, **kw):
            call_count[0] += 1
            if call_count[0] <= 3:  # DeepInfra retries exhaust
                raise deep_err
            return mock_urlopen(groq_resp)

        with patch("urllib.request.urlopen", side_effect=side_effect):
            # DeepInfra retries 3 times then raises, ensemble catches and tries Groq
            result = ensemble.classify("test")

        assert result["label"] == "spam"
        assert ensemble.fallback_count >= 1

    def test_all_backends_fail_raises(self):
        import urllib.error
        deep = DeepInfraBackend(api_key="deep-key")
        deep.MAX_RETRIES = 1
        deep.RETRY_DELAY = 0.01
        groq = GroqBackend(api_key="groq-key")
        groq.MAX_RETRIES = 1
        groq.RETRY_DELAY = 0.01
        ensemble = EnsembleBackend(backends=[deep, groq])

        err = urllib.error.HTTPError("url", 500, "Error", {}, None)
        with patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(BackendError):
                ensemble.classify("test")

    def test_session_budget_enforcement(self):
        deep = DeepInfraBackend(api_key="deep-key")
        ensemble = EnsembleBackend(backends=[deep], session_budget=0.025)

        resp = make_deepinfra_response('{"label": "ham", "confidence": 0.9}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            ensemble.classify("first")  # cost = 0.01
            ensemble.classify("second")  # cost = 0.02
        # Third call exceeds 0.025 budget
        with self.assertRaises(BackendError) as ctx:
            ensemble.classify("third")
        assert "budget" in str(ctx.exception).lower()

    def test_remaining_budget_tracking(self):
        deep = DeepInfraBackend(api_key="deep-key")
        ensemble = EnsembleBackend(backends=[deep], session_budget=0.10)
        resp = make_deepinfra_response('{"label": "ham", "confidence": 0.9}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            ensemble.classify("test")
        assert ensemble.remaining_budget < 0.10
        assert ensemble.remaining_budget > 0.08


# ── Tests: BackendHealth ──────────────────────────────────────────────

class TestBackendHealthMonitor(unittest.TestCase):
    """Test health check and monitoring."""

    def test_ensemble_health_check_all(self):
        deep = DeepInfraBackend(api_key="deep-key")
        groq = GroqBackend(api_key="groq-key")
        ensemble = EnsembleBackend(backends=[deep, groq])

        deep_resp = make_deepinfra_response("OK")
        groq_resp = make_groq_response("OK")

        call_count = [0]
        def side_effect(req, *a, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_urlopen(deep_resp)
            return mock_urlopen(groq_resp)

        with patch("urllib.request.urlopen", side_effect=side_effect):
            healths = ensemble.health_check_all()

        assert len(healths) == 2
        assert all(h.is_healthy for h in healths)

    def test_backend_health_status_string(self):
        h = BackendHealth("test", True, latency_ms=100.0)
        assert h.status == "healthy"
        h2 = BackendHealth("test", False, error="fail")
        assert h2.status == "unhealthy"

    def test_health_checked_at_timestamp(self):
        before = time.time()
        h = BackendHealth("test", True)
        after = time.time()
        assert before <= h.checked_at <= after


# ── Tests: BackendFactory ─────────────────────────────────────────────

class TestBackendFactory(unittest.TestCase):
    """Test BackendFactory create and available."""

    def test_create_groq(self):
        be = BackendFactory.create("groq", api_key="test")
        assert isinstance(be, GroqBackend)

    def test_create_deepinfra(self):
        be = BackendFactory.create("deepinfra", api_key="test")
        assert isinstance(be, DeepInfraBackend)

    def test_create_seed_code(self):
        be = BackendFactory.create("seed-code", api_key="test")
        assert isinstance(be, DeepInfraBackend)
        assert be._model == "ByteDance/Seed-2.0-code"

    def test_create_unknown_raises(self):
        with self.assertRaises(ValueError):
            BackendFactory.create("nonexistent")

    def test_available_with_keys(self):
        with patch("spreader.real_backends._load_key", side_effect=lambda f, e: "key" if "groq" in f or "deepinfra" in f else ""):
            avail = BackendFactory.available()
            assert "groq" in avail
            assert "deepinfra" in avail

    def test_available_no_keys(self):
        with patch("spreader.real_backends._load_key", return_value=""):
            avail = BackendFactory.available()
            assert avail == []


# ── Tests: JSON parsing edge cases ────────────────────────────────────

class TestJsonParsing(unittest.TestCase):
    """Test _parse_json_response handles various formats."""

    def setUp(self):
        self.be = GroqBackend(api_key="test")

    def test_clean_json(self):
        result = self.be._parse_json_response('{"label": "ham", "confidence": 0.9}')
        assert result["label"] == "ham"

    def test_markdown_json_block(self):
        text = '```json\n{"label": "spam", "confidence": 0.95}\n```'
        result = self.be._parse_json_response(text)
        assert result["label"] == "spam"

    def test_json_with_surrounding_text(self):
        text = 'Here is my analysis: {"label": "ham", "confidence": 0.8} Thank you.'
        result = self.be._parse_json_response(text)
        assert result["label"] == "ham"

    def test_no_json_returns_raw(self):
        text = "I cannot classify this."
        result = self.be._parse_json_response(text)
        assert result["raw"] == text


# ── Tests: Legacy interface compatibility ─────────────────────────────

class TestLegacyInterface(unittest.TestCase):
    """Test inference() method works for PipelineRoom compatibility."""

    def test_groq_inference(self):
        be = GroqBackend(api_key="test-key")
        resp = make_groq_response('{"label": "spam", "confidence": 0.92}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            result = be.inference("Free money!!!", {"labels": ["ham", "spam"]})
        assert result["label"] == "spam"

    def test_ensemble_inference(self):
        deep = DeepInfraBackend(api_key="test-key")
        ensemble = EnsembleBackend(backends=[deep])
        resp = make_deepinfra_response('{"label": "ham", "confidence": 0.88}')
        with patch("urllib.request.urlopen", return_value=mock_urlopen(resp)):
            result = ensemble.inference("Meeting at 3", {"labels": ["ham", "spam"]})
        assert result["label"] == "ham"


if __name__ == "__main__":
    unittest.main()
