"""Production pipeline: real backends, spectral tile integrity, PLATO integration.

This is the metal. Not a demo. The real system.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .model_gate import ModelGate, ModelGateConfig
from .pipeline import (
    PipelineRoom,
    SignalChainPipeline,
    Tile,
    header_parse_handler,
    content_classify_handler,
    intent_extract_handler,
    escalate_handler,
    validate_handler,
)
from .real_backends import BackendFactory, RealModelBackend, GroqBackend, DeepInfraBackend


# ── Spectral tile integrity ──────────────────────────────────────────

@dataclass(frozen=True)
class TileSignature:
    """Spectral signature of a tile's information content.
    
    Uses Shannon entropy of the tile's label distribution
    plus a hash of the metadata for integrity checking.
    """
    tile_hash: str        # SHA-256 of canonical tile JSON
    label_entropy: float  # H(label) — information content of classification
    meta_hash: str        # Hash of metadata dict for tamper detection
    timestamp: float
    
    @staticmethod
    def compute(tile: Tile) -> TileSignature:
        """Compute spectral signature from a tile."""
        canonical = json.dumps({
            "room": tile.room_name,
            "label": tile.label,
            "confidence": tile.confidence,
            "metadata": tile.metadata,
            "invoked_model": tile.invoked_model,
        }, sort_keys=True, default=str)
        
        tile_hash = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        meta_hash = hashlib.sha256(
            json.dumps(tile.metadata, sort_keys=True, default=str).encode()
        ).hexdigest()[:12]
        
        # Label entropy: binary classification entropy
        if tile.label in ("ham", "spam"):
            p = tile.confidence
            if 0 < p < 1:
                import math
                entropy = -(p * math.log2(p) + (1 - p) * math.log2(1 - p))
            else:
                entropy = 0.0
        else:
            entropy = 1.0  # Maximum uncertainty
        
        return TileSignature(
            tile_hash=tile_hash,
            label_entropy=round(entropy, 4),
            meta_hash=meta_hash,
            timestamp=time.time(),
        )
    
    def verify(self, tile: Tile) -> bool:
        """Verify tile hasn't been tampered with since signing."""
        fresh = TileSignature.compute(tile)
        return self.tile_hash == fresh.tile_hash and self.meta_hash == fresh.meta_hash


def _entropy_cv(signatures: list[TileSignature]) -> float:
    """Coefficient of variation of entropy across signatures."""
    if len(signatures) < 2:
        return 0.0
    entropies = [s.label_entropy for s in signatures]
    mean = sum(entropies) / len(entropies)
    if mean == 0:
        return 0.0
    var = sum((e - mean) ** 2 for e in entropies) / len(entropies)
    return (var ** 0.5) / mean


@dataclass
class ConservationState:
    """Track information conservation across the pipeline.
    
    I(x) = γ(x) + H(x) approximately conserved for quasi-static coupling.
    Uses CV (coefficient of variation) of entropy across tiles as the
    conservation metric, not raw deltas. Stable tiles have CV < 0.2.
    Wild swings produce CV > 0.5.
    """
    total_information: float = 0.0
    tile_signatures: List[TileSignature] = field(default_factory=list)
    conservation_violations: int = 0
    
    def add_tile(self, tile: Tile) -> None:
        sig = TileSignature.compute(tile)
        self.tile_signatures.append(sig)
        
        # Accumulate information content
        info = sig.label_entropy + tile.confidence  # γ + H approximation
        self.total_information += info
        
        # Check conservation via rolling CV window (last 3 tiles)
        if len(self.tile_signatures) >= 3:
            window = self.tile_signatures[-3:]
            cv = _entropy_cv(window)
            if cv > 0.4:  # Rolling window CV threshold
                self.conservation_violations += 1
    
    def is_conserved(self, threshold: float = 0.3) -> bool:
        """Check if information is approximately conserved across all tiles."""
        cv = _entropy_cv(self.tile_signatures)
        return cv < threshold


# ── Production pipeline builder ───────────────────────────────────────

@dataclass
class ProductionConfig:
    """Configuration for production pipeline."""
    backend_type: str = "groq"     # groq, deepinfra, seed-mini, seed-code
    fallback_type: str = "seed-mini"
    max_cost_per_input: float = 0.10
    early_exit_threshold: float = 0.7
    track_conservation: bool = True
    verify_tiles: bool = True


class ProductionPipeline:
    """The real signal chain. Real models, real integrity checks.
    
    Usage:
        pipe = ProductionPipeline(ProductionConfig(backend_type="groq"))
        result = pipe.classify_email(sender=..., header=..., body=...)
    """

    def __init__(self, config: ProductionConfig) -> None:
        self._config = config
        self._primary = BackendFactory.create(config.backend_type)
        self._fallback = BackendFactory.create(config.fallback_type)
        self._pipeline = self._build_pipeline()
        self._conservation = ConservationState()
        self._processed = 0
        self._total_cost = 0.0
        self._total_latency = 0.0

    @property
    def stats(self) -> dict:
        return {
            "processed": self._processed,
            "total_cost": round(self._total_cost, 4),
            "total_latency_ms": round(self._total_latency, 1),
            "avg_cost": round(self._total_cost / max(self._processed, 1), 4),
            "avg_latency_ms": round(self._total_latency / max(self._processed, 1), 1),
            "conservation_violations": self._conservation.conservation_violations,
            "is_conserved": self._conservation.is_conserved(),
            "primary_calls": self._primary.call_count,
            "fallback_calls": self._fallback.call_count,
        }

    def _build_pipeline(self) -> SignalChainPipeline:
        """Build the 5-room pipeline with real backends."""
        rooms = [
            PipelineRoom(
                name="header_parse",
                alpha=0.0,
                code_handler=header_parse_handler,
                model_gate=ModelGate(ModelGateConfig(alpha=0.0)),
            ),
            PipelineRoom(
                name="content_classify",
                alpha=0.4,
                code_handler=content_classify_handler,
                model_gate=ModelGate(
                    ModelGateConfig(alpha=0.4, max_cost_per_call=0.01),
                    backend=self._primary,
                ),
            ),
            PipelineRoom(
                name="intent_extract",
                alpha=0.6,
                code_handler=intent_extract_handler,
                model_gate=ModelGate(
                    ModelGateConfig(alpha=0.6, max_cost_per_call=0.02),
                    backend=self._primary,
                ),
            ),
            PipelineRoom(
                name="escalate",
                alpha=0.8,
                code_handler=escalate_handler,
                model_gate=ModelGate(
                    ModelGateConfig(alpha=0.8, max_cost_per_call=0.05),
                    backend=self._primary,
                ),
            ),
            PipelineRoom(
                name="validate",
                alpha=0.2,
                code_handler=validate_handler,
                model_gate=ModelGate(
                    ModelGateConfig(alpha=0.2, max_cost_per_call=0.01),
                    backend=self._fallback,  # Use cheaper model for validation
                ),
            ),
        ]
        return SignalChainPipeline(rooms)

    def classify_email(
        self,
        sender: str,
        header: str,
        body: str,
        expected: str | None = None,
    ) -> dict:
        """Classify a single email through the full production pipeline."""
        input_data = {"sender": sender, "header": header, "body": body}
        
        start = time.monotonic()
        result = self._pipeline.process(input_data)
        elapsed = (time.monotonic() - start) * 1000

        # Track conservation
        if self._config.track_conservation:
            for tile in result.tiles:
                self._conservation.add_tile(tile)

        # Verify tile integrity
        integrity_ok = True
        if self._config.verify_tiles:
            for i, sig in enumerate(self._conservation.tile_signatures):
                if i < len(result.tiles):
                    if not sig.verify(result.tiles[i]):
                        integrity_ok = False

        self._processed += 1
        self._total_cost += result.total_cost
        self._total_latency += elapsed

        return {
            "label": result.final_label,
            "confidence": result.final_confidence,
            "early_exit": result.early_exit_room,
            "rooms_run": len(result.room_results),
            "models_invoked": result.models_invoked,
            "cost": round(result.total_cost, 4),
            "latency_ms": round(elapsed, 1),
            "tile_chain": [
                {
                    "room": t.room_name,
                    "label": t.label,
                    "confidence": t.confidence,
                    "model": t.invoked_model,
                    "signature": self._conservation.tile_signatures[i].tile_hash
                    if i < len(self._conservation.tile_signatures) else None,
                }
                for i, t in enumerate(result.tiles)
            ],
            "conservation_ok": self._conservation.is_conserved(),
            "integrity_ok": integrity_ok,
            "expected": expected,
            "correct": result.final_label == expected if expected else None,
        }

    def classify_batch(self, emails: list[dict]) -> list[dict]:
        """Classify a batch of emails. Returns results + summary stats."""
        results = []
        for email in emails:
            result = self.classify_email(
                sender=email.get("sender", ""),
                header=email.get("header", ""),
                body=email.get("body", ""),
                expected=email.get("expected"),
            )
            results.append(result)
        
        # Summary
        correct = sum(1 for r in results if r.get("correct") is True)
        total = sum(1 for r in results if r.get("expected") is not None)
        models_used = sum(r["models_invoked"] for r in results)
        
        print(f"\n{'='*60}")
        print(f"Batch: {len(results)} emails | Accuracy: {correct}/{total} ({100*correct/max(total,1):.0f}%)")
        print(f"Models: {models_used}/{len(results)} calls ({100*(len(results)-models_used)/len(results):.0f}% code-resolved)")
        print(f"Cost: ${sum(r['cost'] for r in results):.4f} | Latency: {sum(r['latency_ms'] for r in results):.0f}ms total")
        print(f"Conservation: {'OK' if self._conservation.is_conserved() else 'VIOLATED'} "
              f"({self._conservation.conservation_violations} violations)")
        print(f"{'='*60}\n")
        
        return results


# ── PLATO room health monitor ─────────────────────────────────────────

@dataclass
class RoomHealthMetrics:
    """Health metrics for a PLATO room, computed from tile signatures."""
    room_id: str
    avg_entropy: float
    entropy_variance: float
    conservation_cv: float
    tile_count: int
    violation_count: int
    is_healthy: bool
    
    @staticmethod
    def from_signatures(room_id: str, signatures: list[TileSignature]) -> RoomHealthMetrics:
        if not signatures:
            return RoomHealthMetrics(room_id, 0.0, 0.0, 0.0, 0, 0, True)
        
        entropies = [s.label_entropy for s in signatures]
        mean = sum(entropies) / len(entropies)
        var = sum((e - mean) ** 2 for e in entropies) / len(entropies)
        cv = _entropy_cv(signatures)
        
        # Room is healthy if CV < 0.3 (information is conserved)
        is_healthy = cv < 0.3
        
        return RoomHealthMetrics(
            room_id=room_id,
            avg_entropy=round(mean, 4),
            entropy_variance=round(var, 4),
            conservation_cv=round(cv, 4),
            tile_count=len(signatures),
            violation_count=sum(1 for s in signatures if s.label_entropy > 0.9),
            is_healthy=is_healthy,
        )
