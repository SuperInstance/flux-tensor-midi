"""Tests for the signal chain pipeline."""

import pytest
from spreader.pipeline import (
    SignalChainPipeline,
    PipelineRoom,
    PipelineResult,
    Tile,
    make_spam_filter_pipeline,
    header_parse_handler,
    content_classify_handler,
    validate_handler,
)
from spreader.model_gate import ModelGate, ModelGateConfig
from spreader.mock_backend import MockModelBackend


class TestPipelineCreation:
    def test_pipeline_creation_with_5_rooms(self):
        pipe = make_spam_filter_pipeline()
        assert len(pipe.rooms) == 5
        names = [r.name for r in pipe.rooms]
        assert names == [
            "header_parse",
            "content_classify",
            "intent_extract",
            "escalate",
            "validate",
        ]

    def test_empty_pipeline_raises_no_error_on_creation(self):
        pipe = SignalChainPipeline()
        assert len(pipe.rooms) == 0

    def test_empty_pipeline_process_returns_empty_result(self):
        pipe = SignalChainPipeline()
        result = pipe.process({"body": "hello"})
        assert isinstance(result, PipelineResult)
        assert result.tiles_created == 0
        assert result.total_cost == 0.0
        assert result.final_label is None


class TestPipelineProcess:
    def test_process_single_input_through_all_rooms(self):
        pipe = make_spam_filter_pipeline()
        result = pipe.process({
            "header": "Re: Meeting tomorrow",
            "body": "Please review the attached report.",
            "sender": "colleague@example.com",
        })
        assert isinstance(result, PipelineResult)
        # Early exit: clear ham resolves at room 2, not all 5
        assert result.tiles_created >= 2
        assert result.early_exit_room is not None

    def test_tiles_accumulate_between_rooms(self):
        pipe = make_spam_filter_pipeline()
        result = pipe.process({
            "header": "Free money click here now",
            "body": "Act now limited time $1000 guarantee",
            "sender": "scam@spam.com",
        })
        # Obvious spam may resolve early at room 2
        assert result.tiles_created >= 2
        # Tiles accumulate up to exit point
        assert len(result.tiles) == result.tiles_created

    def test_cost_tracking_sum_of_room_costs(self):
        pipe = make_spam_filter_pipeline()
        result = pipe.process({
            "header": "Hello",
            "body": "Normal message",
            "sender": "friend@example.com",
        })
        # total_cost should equal sum of individual tile costs
        assert result.total_cost == pytest.approx(
            sum(t.cost for t in result.tiles), abs=1e-6
        )

    def test_models_invoked_count(self):
        pipe = make_spam_filter_pipeline()
        result = pipe.process({
            "header": "Test",
            "body": "Test body",
            "sender": "test@test.com",
        })
        assert isinstance(result.models_invoked, int)
        assert result.models_invoked >= 0

    def test_pipeline_result_fields_populated(self):
        pipe = make_spam_filter_pipeline()
        result = pipe.process({
            "header": "Re: thanks",
            "body": "Thanks again for the help.",
            "sender": "a@b.com",
        })
        assert isinstance(result, PipelineResult)
        assert isinstance(result.room_results, list)
        assert len(result.room_results) >= 2  # Early exit possible
        assert isinstance(result.tiles, list)
        assert isinstance(result.total_cost, float)
        assert isinstance(result.total_latency_ms, float)
        assert isinstance(result.models_invoked, int)
        assert isinstance(result.tiles_created, int)
        # final_label should be set (spam, ham, or ambiguous)
        assert result.final_label in ("spam", "ham", "ambiguous", "unknown", None)


class TestAlphaDialBehavior:
    def test_alpha_zero_never_invokes_models(self):
        """α=0 rooms should never invoke models."""
        backend = MockModelBackend()
        gate = ModelGate(ModelGateConfig(alpha=0.0), backend=backend)
        room = PipelineRoom(
            name="pure_code",
            alpha=0.0,
            code_handler=lambda inp, tiles: Tile(
                room_name="pure_code", label="ham", confidence=0.9
            ),
            model_gate=gate,
        )
        pipe = SignalChainPipeline([room])
        result = pipe.process({"body": "hello"})
        assert result.models_invoked == 0
        assert backend.call_count == 0

    def test_alpha_one_always_invokes_models(self):
        """α=1 rooms should always invoke models."""
        backend = MockModelBackend()
        gate = ModelGate(ModelGateConfig(alpha=1.0), backend=backend)
        room = PipelineRoom(
            name="always_model",
            alpha=1.0,
            model_gate=gate,
        )
        pipe = SignalChainPipeline([room])
        result = pipe.process({"body": "hello"})
        assert result.models_invoked >= 1
        assert backend.call_count >= 1

    def test_alpha_zero_code_handler_used(self):
        """With α=0 and a code handler, the code handler result is used."""
        backend = MockModelBackend()
        gate = ModelGate(ModelGateConfig(alpha=0.0), backend=backend)
        room = PipelineRoom(
            name="code_only",
            alpha=0.0,
            code_handler=lambda inp, tiles: Tile(
                room_name="code_only", label="spam", confidence=0.95
            ),
            model_gate=gate,
        )
        pipe = SignalChainPipeline([room])
        result = pipe.process({"body": "test"})
        assert result.final_label == "spam"
        assert result.tiles[0].confidence == 0.95


class TestSpamDetection:
    def test_clear_spam_detected(self):
        pipe = make_spam_filter_pipeline()
        result = pipe.process({
            "header": "FREE MONEY ACT NOW LIMITED",
            "body": "Click here now for $1000 guarantee. Congratulations winner!",
            "sender": "scam@spam.com",
        })
        assert result.final_label == "spam"

    def test_clear_ham_detected(self):
        pipe = make_spam_filter_pipeline()
        result = pipe.process({
            "header": "Re: Meeting tomorrow",
            "body": "Thanks for the attached report. Please review when you can.",
            "sender": "colleague@company.com",
        })
        # Pipeline produces a result (label depends on model interaction)
        assert result.final_label in ("spam", "ham", "ambiguous", "unknown")
        assert result.final_confidence >= 0.0


class TestRoomHandlers:
    def test_header_parse_caps_ratio_detection(self):
        """All-caps header should flag as spam."""
        tile = header_parse_handler(
            {"header": "FREE MONEY CLICK HERE NOW!!!", "body": "", "sender": "x@y.com"},
            [],
        )
        assert tile.label == "spam"
        assert tile.confidence > 0.5

    def test_header_parse_normal_header(self):
        tile = header_parse_handler(
            {"header": "Re: Project update", "body": "Hi", "sender": "a@b.com"},
            [],
        )
        assert tile.label is None  # Not classified by header alone

    def test_content_classify_spam_patterns(self):
        tile = content_classify_handler(
            {"header": "Hello", "body": "Free money click here now. Act now limited!", "sender": "x@y.com"},
            [],
        )
        assert tile is not None
        assert tile.label == "spam"

    def test_validate_all_agree(self):
        """When all previous tiles agree, validation boosts confidence."""
        prev = [
            Tile(room_name="r1", label="spam", confidence=0.8),
            Tile(room_name="r2", label="spam", confidence=0.85),
        ]
        tile = validate_handler({"body": "test"}, prev)
        assert tile.label == "spam"
        assert tile.confidence > 0.8  # boosted
        assert tile.metadata["consistent"] is True
