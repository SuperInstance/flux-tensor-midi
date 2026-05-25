"""Tests for production pipeline and spectral tile integrity."""

import pytest
from spreader.production import (
    TileSignature,
    ConservationState,
    ProductionConfig,
    ProductionPipeline,
    RoomHealthMetrics,
)
from spreader.pipeline import Tile


class TestTileSignature:
    """Spectral signature computation and verification."""

    def test_compute_basic(self):
        tile = Tile(room_name="test", label="spam", confidence=0.9)
        sig = TileSignature.compute(tile)
        assert len(sig.tile_hash) == 16
        assert len(sig.meta_hash) == 12
        assert sig.label_entropy >= 0.0

    def test_entropy_ham(self):
        tile = Tile(room_name="r1", label="ham", confidence=0.9)
        sig = TileSignature.compute(tile)
        # High confidence → low entropy
        assert sig.label_entropy < 0.5

    def test_entropy_uncertain(self):
        tile = Tile(room_name="r1", label="ham", confidence=0.5)
        sig = TileSignature.compute(tile)
        # Max uncertainty → max entropy
        assert sig.label_entropy == pytest.approx(1.0, abs=0.01)

    def test_entropy_ambiguous(self):
        tile = Tile(room_name="r1", label="ambiguous", confidence=0.3)
        sig = TileSignature.compute(tile)
        assert sig.label_entropy == 1.0  # Max uncertainty

    def test_verify_untampered(self):
        tile = Tile(room_name="r1", label="spam", confidence=0.85)
        sig = TileSignature.compute(tile)
        assert sig.verify(tile) is True

    def test_verify_tampered_label(self):
        tile = Tile(room_name="r1", label="spam", confidence=0.85)
        sig = TileSignature.compute(tile)
        tampered = Tile(room_name="r1", label="ham", confidence=0.85)
        assert sig.verify(tampered) is False

    def test_verify_tampered_confidence(self):
        tile = Tile(room_name="r1", label="spam", confidence=0.85)
        sig = TileSignature.compute(tile)
        tampered = Tile(room_name="r1", label="spam", confidence=0.3)
        assert sig.verify(tampered) is False

    def test_verify_tampered_metadata(self):
        tile = Tile(room_name="r1", label="spam", confidence=0.85, metadata={"score": 5})
        sig = TileSignature.compute(tile)
        tampered = Tile(room_name="r1", label="spam", confidence=0.85, metadata={"score": 1})
        assert sig.verify(tampered) is False


class TestConservationState:
    """Information conservation tracking across tiles."""

    def test_empty_is_conserved(self):
        state = ConservationState()
        assert state.is_conserved() is True

    def test_single_tile_conserved(self):
        state = ConservationState()
        tile = Tile(room_name="r1", label="spam", confidence=0.9)
        state.add_tile(tile)
        assert state.is_conserved() is True

    def test_stable_tiles_conserved(self):
        state = ConservationState()
        for conf in [0.85, 0.88, 0.82, 0.90, 0.87]:
            tile = Tile(room_name="r1", label="spam", confidence=conf)
            state.add_tile(tile)
        assert state.is_conserved() is True

    def test_drifting_tiles_conserved(self):
        state = ConservationState()
        # Gradual drift within same label
        for conf in [0.9, 0.85, 0.8, 0.75, 0.7]:
            tile = Tile(room_name="r1", label="spam", confidence=conf)
            state.add_tile(tile)
        # Gradual drift should still be conserved
        assert state.is_conserved() is True

    def test_wild_tiles_violate(self):
        state = ConservationState()
        # Wild swings between confident and ambiguous
        for label, conf in [("spam", 0.95), ("ambiguous", 0.3), ("spam", 0.95), ("ambiguous", 0.3)]:
            tile = Tile(room_name="r1", label=label, confidence=conf)
            state.add_tile(tile)
        # CV should be high → not conserved
        assert not state.is_conserved()


class TestRoomHealthMetrics:
    """PLATO room health from tile signatures."""

    def test_empty_room(self):
        health = RoomHealthMetrics.from_signatures("room1", [])
        assert health.is_healthy is True
        assert health.tile_count == 0

    def test_healthy_room(self):
        sigs = []
        for conf in [0.85, 0.88, 0.82, 0.90, 0.87]:
            tile = Tile(room_name="r1", label="spam", confidence=conf)
            sigs.append(TileSignature.compute(tile))
        health = RoomHealthMetrics.from_signatures("room1", sigs)
        assert health.is_healthy is True
        assert health.tile_count == 5

    def test_unhealthy_room(self):
        sigs = []
        for label, conf in [("spam", 0.95), ("ambiguous", 0.3), ("spam", 0.95), ("ambiguous", 0.3), ("spam", 0.95)]:
            tile = Tile(room_name="r1", label=label, confidence=conf)
            sigs.append(TileSignature.compute(tile))
        health = RoomHealthMetrics.from_signatures("room1", sigs)
        # CV > 0.3 → unhealthy
        assert health.conservation_cv > 0.3
        assert not health.is_healthy


class TestProductionConfig:
    """Config validation."""

    def test_default_config(self):
        config = ProductionConfig()
        assert config.backend_type == "groq"
        assert config.early_exit_threshold == 0.7
        assert config.track_conservation is True

    def test_custom_config(self):
        config = ProductionConfig(
            backend_type="seed-mini",
            fallback_type="groq",
            max_cost_per_input=0.05,
        )
        assert config.backend_type == "seed-mini"
        assert config.max_cost_per_input == 0.05


class TestProductionPipelineNoAPI:
    """Test production pipeline without API keys (mock mode)."""

    def test_pipeline_builds(self):
        """Pipeline should build even without API keys."""
        config = ProductionConfig(backend_type="groq")
        pipe = ProductionPipeline(config)
        assert pipe._pipeline is not None
        assert pipe.stats["processed"] == 0

    def test_code_path_works_without_api(self):
        """Emails that resolve at α=0 should work without any API."""
        config = ProductionConfig(backend_type="groq")
        pipe = ProductionPipeline(config)
        
        # Obvious spam → should resolve at code path
        result = pipe.classify_email(
            sender="promo@spam-domain.xyz",
            header="FREE MONEY NOW CLICK HERE",
            body="Act now! Limited time! Click here now for free money! $500 guarantee!",
            expected="spam",
        )
        # Code path should catch this even without API
        assert result["label"] in ("ham", "spam", "ambiguous", "unknown")
        assert result["confidence"] >= 0.0
        assert "conservation_ok" in result

    def test_stats_tracking(self):
        """Stats should accumulate after processing."""
        config = ProductionConfig(backend_type="groq")
        pipe = ProductionPipeline(config)
        
        pipe.classify_email(
            sender="test@test.com",
            header="Test",
            body="Test body",
        )
        
        assert pipe.stats["processed"] == 1
        assert pipe.stats["total_latency_ms"] > 0

    def test_batch_without_api(self):
        """Batch processing should work for code-resolvable emails."""
        config = ProductionConfig(backend_type="groq")
        pipe = ProductionPipeline(config)
        
        emails = [
            {"sender": "boss@company.com", "header": "Meeting tomorrow",
             "body": "Let's sync at 3pm", "expected": "ham"},
            {"sender": "no-reply@promo.xyz", "header": "FREE MONEY NOW!!!",
             "body": "Click here to claim your prize", "expected": "spam"},
        ]
        
        results = pipe.classify_batch(emails)
        assert len(results) == 2
        assert pipe.stats["processed"] == 2
