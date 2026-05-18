"""Signal chain pipeline: N rooms processing real data with α dials.

Each room has an α dial controlling whether it uses code, micro-model,
or full model. Tiles carry context between rooms. The pipeline demonstrates
that most inputs are resolved cheaply (code + micro), with full models only
invoked when tile context shows ambiguity.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .model_gate import ModelGate, ModelGateConfig, GateResult
from .mock_backend import MockModelBackend


@dataclass
class Tile:
    """A tile emitted by a pipeline room — carries context to the next room."""
    room_name: str
    label: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    cost: float = 0.0
    latency_ms: float = 0.0
    invoked_model: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class PipelineRoom:
    """A single room in the signal chain pipeline."""
    name: str
    alpha: float
    model_gate: Optional[ModelGate] = None
    code_handler: Optional[Callable[[dict, List[Tile]], Tile]] = None
    fallback_handler: Optional[Callable[[dict, List[Tile]], Tile]] = None

    def effective_gate(self) -> ModelGate:
        """Get or create the model gate for this room."""
        if self.model_gate is not None:
            return self.model_gate
        return ModelGate(ModelGateConfig(alpha=self.alpha))


@dataclass
class PipelineResult:
    """Full result from running the pipeline."""
    room_results: List[Dict[str, Any]] = field(default_factory=list)
    tiles: List[Tile] = field(default_factory=list)
    total_cost: float = 0.0
    total_latency_ms: float = 0.0
    models_invoked: int = 0
    tiles_created: int = 0
    final_label: Optional[str] = None
    final_confidence: float = 0.0
    early_exit_room: Optional[str] = None


class SignalChainPipeline:
    """N-room signal chain pipeline.

    The pipeline processes data through a chain of rooms. Each room:
    1. Reads accumulated tiles from previous rooms
    2. Checks α dial: code path or model path?
    3. Processes input
    4. Emits tile with result
    5. Passes to next room
    """

    def __init__(self, rooms: Optional[List[PipelineRoom]] = None) -> None:
        self._rooms = rooms or []

    @property
    def rooms(self) -> List[PipelineRoom]:
        return list(self._rooms)

    def add_room(self, room: PipelineRoom) -> None:
        self._rooms.append(room)

    def process(self, input_data: dict) -> PipelineResult:
        """Run input through the full signal chain."""
        result = PipelineResult()
        tiles: List[Tile] = []

        for room in self._rooms:
            room_start = time.monotonic()
            tile = self._process_room(room, input_data, tiles)
            elapsed = (time.monotonic() - room_start) * 1000

            tiles.append(tile)
            result.tiles.append(tile)
            result.tiles_created += 1
            result.total_cost += tile.cost
            result.total_latency_ms += tile.latency_ms
            if tile.invoked_model:
                result.models_invoked += 1

            result.room_results.append({
                "room": room.name,
                "alpha": room.alpha,
                "label": tile.label,
                "confidence": tile.confidence,
                "invoked_model": tile.invoked_model,
                "cost": tile.cost,
                "latency_ms": tile.latency_ms,
                "total_elapsed_ms": elapsed,
            })

            # Early resolution: if a room resolves with high confidence,
            # skip downstream rooms (the signal chain's key efficiency)
            if tile.confidence >= 0.7 and tile.label in ("ham", "spam"):
                result.early_exit_room = room.name
                break

        # Final label: last tile with confidence > 0.5, or last tile
        final = None
        for t in reversed(tiles):
            if t.confidence > 0.5:
                final = t
                break
        if final is None and tiles:
            final = tiles[-1]

        if final:
            result.final_label = final.label
            result.final_confidence = final.confidence

        return result

    def _process_room(self, room: PipelineRoom, input_data: dict, prev_tiles: List[Tile]) -> Tile:
        """Process a single room: decide code vs model, emit tile."""
        gate = room.effective_gate()

        # Try code handler first if α < 1.0
        if room.alpha < 1.0 and room.code_handler is not None:
            code_tile = room.code_handler(input_data, prev_tiles)
            if code_tile is not None:
                # If code resolved with decent confidence, skip the model.
                # Model only invoked when code's confidence is below threshold.
                if code_tile.confidence >= gate._config.confidence_threshold:
                    return code_tile  # Pure code resolution, no model needed

                # Code uncertain — invoke model if α says to
                if gate.should_invoke_model():
                    gate_result = gate.invoke(input_data=input_data)
                    if gate_result.invoked and gate_result.response:
                        # Model overrides or supplements code
                        return Tile(
                            room_name=room.name,
                            label=gate_result.response.get("label", code_tile.label),
                            confidence=gate_result.confidence,
                            metadata=gate_result.response,
                            cost=code_tile.cost + gate_result.cost,
                            latency_ms=code_tile.latency_ms + gate_result.latency_ms,
                            invoked_model=True,
                        )
                return code_tile

        # Model path
        if gate.should_invoke_model():
            gate_result = gate.invoke(input_data=input_data)
            if gate_result.invoked and gate_result.response:
                return Tile(
                    room_name=room.name,
                    label=gate_result.response.get("label"),
                    confidence=gate_result.confidence,
                    metadata=gate_result.response,
                    cost=gate_result.cost,
                    latency_ms=gate_result.latency_ms,
                    invoked_model=True,
                )
            elif gate_result.error:
                # Model failed: try fallback handler
                if room.fallback_handler:
                    return room.fallback_handler(input_data, prev_tiles)

        # Fallback: generic handler
        if room.fallback_handler:
            return room.fallback_handler(input_data, prev_tiles)

        # Last resort: pass-through tile
        return Tile(
            room_name=room.name,
            label="unknown",
            confidence=0.0,
            metadata={"fallback": True},
        )


# ── Spam filter room handlers ───────────────────────────────────────────

# Known spam patterns for deterministic code-path detection
_SPAM_PATTERNS = [
    re.compile(r"free\s+money", re.I),
    re.compile(r"click\s+here\s+now", re.I),
    re.compile(r"act\s+now.{0,10}limited", re.I),
    re.compile(r"\$\d+.*guarantee", re.I),
    re.compile(r"unsubscribe", re.I),
    re.compile(r"viagra|cialis|pharmacy", re.I),
    re.compile(r"winner|congratulations|prize", re.I),
    re.compile(r"nigerian|inheritance|wire\s+transfer", re.I),
]

_HAM_PATTERNS = [
    re.compile(r"meeting\s+(at|on|tomorrow|next)", re.I),
    re.compile(r"attached.*(?:report|document|file)", re.I),
    re.compile(r"please\s+review", re.I),
    re.compile(r"thanks?\s+(for|again)", re.I),
    re.compile(r"re:\s+", re.I),
    re.compile(r"invoice\s*#?\d+", re.I),
]


def header_parse_handler(input_data: dict, prev_tiles: List[Tile]) -> Tile:
    """Room 1: Pure code header parsing. α=0 — no model."""
    header = input_data.get("header", "")
    sender = input_data.get("sender", "")
    body = input_data.get("body", "")

    metadata: Dict[str, Any] = {
        "has_reply_to": header.lower().startswith("re:"),
        "has_fwd": header.lower().startswith("fwd:"),
        "sender_domain": sender.split("@")[-1] if "@" in sender else "unknown",
        "header_length": len(header),
        "body_length": len(body),
        "caps_ratio": sum(1 for c in header if c.isupper()) / max(len(header), 1),
    }

    # Quick classification from headers alone
    if metadata["caps_ratio"] > 0.5 and len(header) > 10:
        return Tile(
            room_name="header_parse",
            label="spam",
            confidence=0.6,
            metadata=metadata,
        )

    return Tile(
        room_name="header_parse",
        label=None,  # Not classified yet
        confidence=0.0,
        metadata=metadata,
    )


def content_classify_handler(input_data: dict, prev_tiles: List[Tile]) -> Tile:
    """Room 2: Code-first content classification with model backup. α=0.4."""
    body = input_data.get("body", "")
    header = input_data.get("header", "")
    text = f"{header} {body}".lower()

    # Check spam patterns
    spam_hits = sum(1 for p in _SPAM_PATTERNS if p.search(text))
    ham_hits = sum(1 for p in _HAM_PATTERNS if p.search(text))

    if spam_hits >= 2:
        return Tile(
            room_name="content_classify",
            label="spam",
            confidence=0.85,
            metadata={"spam_hits": spam_hits, "ham_hits": ham_hits, "path": "code"},
        )
    if spam_hits == 1 and ham_hits == 0:
        return Tile(
            room_name="content_classify",
            label="spam",
            confidence=0.65,
            metadata={"spam_hits": spam_hits, "ham_hits": ham_hits, "path": "code"},
        )
    if ham_hits >= 2:
        return Tile(
            room_name="content_classify",
            label="ham",
            confidence=0.80,
            metadata={"spam_hits": spam_hits, "ham_hits": ham_hits, "path": "code"},
        )
    if ham_hits >= 1 and spam_hits == 0:
        return Tile(
            room_name="content_classify",
            label="ham",
            confidence=0.65,
            metadata={"spam_hits": spam_hits, "ham_hits": ham_hits, "path": "code"},
        )

    # Ambiguous — return None to let model handle
    return None


def intent_extract_handler(input_data: dict, prev_tiles: List[Tile]) -> Tile:
    """Room 3: Intent extraction. α=0.6 — mostly model, some code."""
    body = input_data.get("body", "").lower()
    text = f"{input_data.get('header', '')} {body}".lower()

    # Quick code check for common intents
    if any(w in text for w in ["unsubscribe", "opt out", "remove me"]):
        return Tile(
            room_name="intent_extract",
            label="spam",
            confidence=0.75,
            metadata={"intent": "promotional", "path": "code"},
        )
    if any(w in text for w in ["invoice", "payment", "receipt", "order"]):
        return Tile(
            room_name="intent_extract",
            label="ham",
            confidence=0.70,
            metadata={"intent": "transactional", "path": "code"},
        )

    # Return None to let model handle ambiguous cases
    return None


def escalate_handler(input_data: dict, prev_tiles: List[Tile]) -> Tile:
    """Room 4: Escalation. α=0.8 — full model, only for ambiguous inputs."""
    # Only escalate if previous rooms couldn't classify
    prev_labels = [t.label for t in prev_tiles if t.label is not None]
    prev_confidences = [t.confidence for t in prev_tiles if t.confidence > 0]

    if prev_labels and prev_labels[-1] != "ambiguous":
        # Already classified with decent confidence
        max_conf = max(prev_confidences) if prev_confidences else 0.0
        if max_conf >= 0.7:
            return Tile(
                room_name="escalate",
                label=prev_labels[-1],
                confidence=max_conf,
                metadata={"path": "skipped", "reason": "already_classified"},
            )

    # Need model — return None to trigger model invocation
    return None


def validate_handler(input_data: dict, prev_tiles: List[Tile]) -> Tile:
    """Room 5: Validation/consistency check. α=0.2 — micro-model."""
    labels = [t.label for t in prev_tiles if t.label is not None]
    confidences = [t.confidence for t in prev_tiles if t.confidence > 0]

    if not labels:
        return Tile(
            room_name="validate",
            label="ambiguous",
            confidence=0.3,
            metadata={"path": "code", "reason": "no_labels"},
        )

    # Consistency check: do all rooms agree?
    unique_labels = set(labels)
    if len(unique_labels) == 1:
        # All rooms agree
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.5
        return Tile(
            room_name="validate",
            label=labels[0],
            confidence=min(1.0, avg_conf + 0.1),
            metadata={"path": "code", "consistent": True, "agreeing_rooms": len(labels)},
        )

    # Disagreement: majority vote
    from collections import Counter
    label_counts = Counter(labels)
    winner, count = label_counts.most_common(1)[0]
    agreement_ratio = count / len(labels)

    return Tile(
        room_name="validate",
        label=winner,
        confidence=agreement_ratio * 0.8,
        metadata={
            "path": "code",
            "consistent": False,
            "label_counts": dict(label_counts),
            "majority_ratio": agreement_ratio,
        },
    )


def make_spam_filter_pipeline(backend: Optional[MockModelBackend] = None) -> SignalChainPipeline:
    """Create a 5-room spam filter pipeline."""
    shared_backend = backend or MockModelBackend()

    rooms = [
        PipelineRoom(
            name="header_parse",
            alpha=0.0,
            code_handler=header_parse_handler,
            model_gate=ModelGate(ModelGateConfig(alpha=0.0), backend=shared_backend),
        ),
        PipelineRoom(
            name="content_classify",
            alpha=0.4,
            code_handler=content_classify_handler,
            model_gate=ModelGate(ModelGateConfig(alpha=0.4), backend=shared_backend),
        ),
        PipelineRoom(
            name="intent_extract",
            alpha=0.6,
            code_handler=intent_extract_handler,
            model_gate=ModelGate(ModelGateConfig(alpha=0.6), backend=shared_backend),
        ),
        PipelineRoom(
            name="escalate",
            alpha=0.8,
            code_handler=escalate_handler,
            model_gate=ModelGate(ModelGateConfig(alpha=0.8), backend=shared_backend),
        ),
        PipelineRoom(
            name="validate",
            alpha=0.2,
            code_handler=validate_handler,
            model_gate=ModelGate(ModelGateConfig(alpha=0.2), backend=shared_backend),
        ),
    ]

    return SignalChainPipeline(rooms)
