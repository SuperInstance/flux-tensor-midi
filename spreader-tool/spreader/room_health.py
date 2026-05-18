"""Room health monitoring — spectral conservation across PLATO rooms.

Wires the spectral first integral I(x) = γ(x) + H(x) into a health monitoring
framework. Each room accumulates tile signatures and computes the coefficient
of variation (CV) of entropy. When CV exceeds thresholds, it raises alerts.

Thresholds:
  - < 0.3  : QUASI-STATIC — information is approximately conserved
  - 0.3–0.5: WARNING     — spectral shape is drifting
  - 0.5–0.7: ELEVATED    — coupling breakdown may be underway
  - > 0.7  : CRITICAL    — conservation violated, action required

Root cause analysis distinguishes two primary failure modes:
  1. Rapid shape change — coupling matrix eigenvalues are shifting quickly
  2. Coupling breakdown  — ||[D,C]|| is growing, rank structure collapsing

Usage:
    monitor = ConservationMonitor()
    for tile in tiles:
        monitor.observe("room1", tile)
    dashboard = monitor.dashboard()
    print(dashboard.overall_fleet_health)
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .types import RoomType
from .production import TileSignature, ConservationState, RoomHealthMetrics, _entropy_cv
from .pipeline import Tile


# ── Constants ────────────────────────────────────────────────────────────────

CV_THRESHOLD_QUASI_STATIC: float = 0.3
CV_THRESHOLD_WARNING: float = 0.3
CV_THRESHOLD_ELEVATED: float = 0.5
CV_THRESHOLD_CRITICAL: float = 0.7
TREND_WINDOW_SIZE: int = 20  # number of tiles for trend detection


# ── Enums ────────────────────────────────────────────────────────────────────

class ConservationAlert(Enum):
    """Alert level based on CV of entropy across tiles in a room."""
    QUASI_STATIC = "quasi-static"
    WARNING = "warning"
    ELEVATED = "elevated"
    CRITICAL = "critical"

    @classmethod
    def from_cv(cls, cv: float) -> ConservationAlert:
        if cv < CV_THRESHOLD_QUASI_STATIC:
            return cls.QUASI_STATIC
        elif cv < CV_THRESHOLD_ELEVATED:
            return cls.WARNING
        elif cv < CV_THRESHOLD_CRITICAL:
            return cls.ELEVATED
        return cls.CRITICAL


class ViolationRootCause(Enum):
    """Root cause of a conservation violation."""
    RAPID_SHAPE_CHANGE = "rapid_shape_change"
    COUPLING_BREAKDOWN = "coupling_breakdown"
    SENSOR_DRIFT = "sensor_drift"
    UNKNOWN = "unknown"


class RecommendedAction(Enum):
    """Action to take based on root cause analysis."""
    INCREASE_ALPHA = "increase_alpha"
    REDUCE_COMPRESSION = "reduce_compression"
    PRESERVE_VERBATIM = "preserve_verbatim"
    ESCALATE = "escalate"
    RECHECK = "recheck"
    NONE = "none"


# ── Data structures ──────────────────────────────────────────────────────────

@dataclass
class RoomConservationData:
    """Per-room conservation tracking data."""
    room_id: str
    room_type: Optional[RoomType] = None
    tile_count: int = 0
    signatures: list[TileSignature] = field(default_factory=list)
    cv_history: list[float] = field(default_factory=list)  # CV after each tile
    violation_count: int = 0
    last_alert: ConservationAlert = ConservationAlert.QUASI_STATIC
    trend_slope: float = 0.0  # linear regression slope of last N CV values


@dataclass
class RoomHealthSnapshot:
    """Immutable snapshot of room health at a point in time."""
    room_id: str
    cv: float
    alert: ConservationAlert
    tile_count: int
    violation_count: int
    avg_entropy: float
    entropy_variance: float
    trend_slope: float
    is_trending_dangerous: bool  # CV increasing AND approaching critical
    has_critical_alert: bool
    metrics: RoomHealthMetrics
    timestamp: float


@dataclass
class ConservationViolation:
    """Record of a conservation violation with root cause analysis."""
    room_id: str
    cv: float
    threshold: float
    alert_level: ConservationAlert
    tile_count: int
    causal_signatures: list[TileSignature]  # Window that triggered violation
    root_cause: ViolationRootCause
    root_cause_evidence: str
    recommended_action: RecommendedAction
    timestamp: float

    def to_dict(self) -> dict:
        return {
            "room_id": self.room_id,
            "cv": round(self.cv, 4),
            "threshold": self.threshold,
            "alert_level": self.alert_level.value,
            "tile_count": self.tile_count,
            "root_cause": self.root_cause.value,
            "root_cause_evidence": self.root_cause_evidence,
            "recommended_action": self.recommended_action.value,
            "timestamp": self.timestamp,
        }


@dataclass
class DashboardSnapshot:
    """Aggregate health snapshot across all monitored rooms."""
    room_snapshots: dict[str, RoomHealthSnapshot]
    overall_fleet_health: float  # 0–1, weighted average
    critical_rooms: list[RoomHealthSnapshot]
    warning_rooms: list[RoomHealthSnapshot]
    trending_rooms: list[RoomHealthSnapshot]
    total_rooms: int
    total_tiles: int
    total_violations: int
    timestamp: float


@dataclass
class HealthTile:
    """Special tile carrying room health metrics for PLATO broadcasting.
    
    Fleet agents consume HealthTiles to monitor each other's health.
    Written periodically to PLATO rooms.
    """
    room_id: str
    source_monitor: str  # monitor/agent identifier
    cv: float
    alert: ConservationAlert
    tile_count: int
    violation_count: int
    trend_slope: float
    fleet_health_contribution: float
    timestamp: float
    serialized: str = ""

    def __post_init__(self) -> None:
        if not self.serialized:
            self.serialized = json.dumps(
                {
                    "type": "health_tile",
                    "room_id": self.room_id,
                    "source_monitor": self.source_monitor,
                    "cv": self.cv,
                    "alert": self.alert.value,
                    "tile_count": self.tile_count,
                    "violation_count": self.violation_count,
                    "trend_slope": self.trend_slope,
                    "fleet_health_contribution": self.fleet_health_contribution,
                    "timestamp": self.timestamp,
                },
                sort_keys=True,
            )

    @staticmethod
    def from_json(data: str) -> HealthTile:
        parsed = json.loads(data)
        return HealthTile(
            room_id=parsed["room_id"],
            source_monitor=parsed["source_monitor"],
            cv=parsed["cv"],
            alert=ConservationAlert(parsed["alert"]),
            tile_count=parsed["tile_count"],
            violation_count=parsed["violation_count"],
            trend_slope=parsed["trend_slope"],
            fleet_health_contribution=parsed["fleet_health_contribution"],
            timestamp=parsed["timestamp"],
            serialized=data,
        )

    def to_bytes(self) -> bytes:
        return self.serialized.encode("utf-8")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HealthTile):
            return NotImplemented
        return self.serialized == other.serialized


# ── Root Cause Analysis ──────────────────────────────────────────────────────

def _entropy_sequence(signatures: list[TileSignature]) -> list[float]:
    """Extract entropy sequence from signatures."""
    return [s.label_entropy for s in signatures]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    var = sum((v - m) ** 2 for v in values) / len(values)
    return math.sqrt(var)


def _linear_regression_slope(values: list[float]) -> float:
    """Compute slope of linear regression for y = values over index steps."""
    n = len(values)
    if n < 2:
        return 0.0
    xs = list(range(n))
    mx = _mean(xs)
    my = _mean(values)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, values))
    den = sum((x - mx) ** 2 for x in xs)
    return num / den if den != 0 else 0.0


def _compute_entropy_stats(signatures: list[TileSignature]) -> dict:
    """Compute descriptive stats from a batch of signatures."""
    entropies = _entropy_sequence(signatures)
    if not entropies:
        return {"mean": 0.0, "std": 0.0, "cv": 0.0, "min": 0.0, "max": 0.0, "count": 0}
    m = _mean(entropies)
    s = _std(entropies)
    cv = s / m if m != 0 else 0.0
    return {
        "mean": m,
        "std": s,
        "cv": cv,
        "min": min(entropies),
        "max": max(entropies),
        "count": len(entropies),
    }


def analyze_root_cause(
    signatures: list[TileSignature],
) -> Tuple[ViolationRootCause, str]:
    """Analyze signatures to determine root cause of conservation violation.
    
    Two primary failure modes:
    1. Rapid shape change — entropy alternates widely (high variance but stable mean)
    2. Coupling breakdown — entropy trends monotonically (slope indicates collapse)
    
    Uses diagnostic heuristics on the entropy sequence.
    """
    if len(signatures) < 3:
        return ViolationRootCause.UNKNOWN, "insufficient data for root cause analysis"

    stats = _compute_entropy_stats(signatures)
    slope = _linear_regression_slope(_entropy_sequence(signatures))
    entropies = _entropy_sequence(signatures)

    # Compute alternating score: how much consecutive entries jump
    jumps = [abs(entropies[i] - entropies[i + 1]) for i in range(len(entropies) - 1)]
    avg_jump = _mean(jumps)
    max_jump = max(jumps) if jumps else 0.0

    # Compute trend score: normalized slope
    mean_e = stats["mean"]
    trend_score = abs(slope) / max(mean_e, 1e-10) if mean_e > 0 else 0.0

    # Rapid shape change: high avg_jump relative to mean entropy
    rapid_shape_score = avg_jump / max(mean_e, 1e-10)

    # Distinguish:
    # - If jumps are large AND slope is small → oscillation → rapid shape change
    # - If slope is large AND jumps are moderate → monotonic drift → coupling breakdown
    # - If both are large → severe mode switching

    # Absolute slope > 0.05 over 10+ points indicates directional drift
    # regardless of mean (which can be large for binary entropy)
    if abs(slope) > 0.05 and rapid_shape_score < 1.0 and len(signatures) >= 5:
        return (
            ViolationRootCause.COUPLING_BREAKDOWN,
            f"Monotonic entropy drift detected: slope={slope:.4f}, "
            f"abs_slope={abs(slope):.4f}, trend_score={trend_score:.4f}. "
            f"Coupling matrix eigenvalues are shifting directionally, "
            f"indicating structural breakdown of the coupling dynamics. "
            f"Spectral gaps are collapsing."
        )
    elif rapid_shape_score > 0.5:
        return (
            ViolationRootCause.RAPID_SHAPE_CHANGE,
            f"Alternating entropy detected: avg_jump={avg_jump:.4f}, "
            f"max_jump={max_jump:.4f}, rapid_shape_score={rapid_shape_score:.4f}. "
            f"Entropy oscillates between high and low values, indicating "
            f"rapid mode-switching in the coupling matrix shape."
        )
    elif abs(slope) > 0.02 and max_jump > 0.3:
        return (
            ViolationRootCause.SENSOR_DRIFT,
            f"Gradual sensor drift detected: slope={slope:.4f}, "
            f"max_jump={max_jump:.4f}. Entropy drifts upward with "
            f"occasional spikes, suggesting sensor calibration drift."
        )
    else:
        return (
            ViolationRootCause.UNKNOWN,
            f"Violation detected but no clear pattern: cv={stats['cv']:.4f}, "
            f"slope={slope:.4f}, avg_jump={avg_jump:.4f}. Manual review recommended."
        )


def recommend_action(
    root_cause: ViolationRootCause,
    alert: ConservationAlert,
    slope: float,
) -> RecommendedAction:
    """Recommend an action based on root cause analysis.
    
    Mapping:
      - Rapid shape change → increase α (smoothing factor on coupling)
      - Coupling breakdown  → reduce compression (preserve spectral structure)
      - Sensor drift        → preserve verbatim (don't filter sensor data)
      - Unknown / Critical  → escalate
    """
    if root_cause == ViolationRootCause.RAPID_SHAPE_CHANGE:
        return RecommendedAction.INCREASE_ALPHA
    elif root_cause == ViolationRootCause.COUPLING_BREAKDOWN:
        return RecommendedAction.REDUCE_COMPRESSION
    elif root_cause == ViolationRootCause.SENSOR_DRIFT:
        return RecommendedAction.PRESERVE_VERBATIM
    elif alert == ConservationAlert.CRITICAL:
        return RecommendedAction.ESCALATE
    elif alert == ConservationAlert.QUASI_STATIC:
        return RecommendedAction.NONE
    return RecommendedAction.RECHECK


# ── Primary Monitor ──────────────────────────────────────────────────────────

class ConservationMonitor:
    """Tracks spectral conservation (CV of entropy) across tiles flowing
    through PLATO rooms.

    Stateless in the sense that all state is in per-room ConservationData.
    The monitor is the orchestrator: it observes tiles, computes alerts,
    and produces violations when thresholds are breached.

    Usage:
        monitor = ConservationMonitor()
        monitor.observe("room1", tile1)
        monitor.observe("room1", tile2)
        snap = monitor.snapshot("room1")
        dash = monitor.dashboard()
        vio = monitor.check_violations("room1")
    """

    def __init__(self, source_monitor: str = "forgemaster") -> None:
        self._rooms: dict[str, RoomConservationData] = {}
        self._violations: list[ConservationViolation] = []
        self._source_monitor = source_monitor

    @property
    def room_count(self) -> int:
        return len(self._rooms)

    @property
    def total_tiles(self) -> int:
        return sum(r.tile_count for r in self._rooms.values())

    @property
    def total_violations(self) -> int:
        return len(self._violations)

    @property
    def rooms(self) -> dict[str, RoomConservationData]:
        return dict(self._rooms)

    def get_room(self, room_id: str) -> Optional[RoomConservationData]:
        return self._rooms.get(room_id)

    def clear(self) -> None:
        """Clear all room data and violations."""
        self._rooms.clear()
        self._violations.clear()

    # ── Observation ──

    def observe(self, room_id: str, tile: Tile) -> None:
        """Observe a tile flowing through a room and update conservation tracking."""
        if room_id not in self._rooms:
            self._rooms[room_id] = RoomConservationData(room_id=room_id)

        room = self._rooms[room_id]
        sig = TileSignature.compute(tile)
        room.signatures.append(sig)
        room.tile_count += 1

        # Update CV history
        cv = _entropy_cv(room.signatures)
        room.cv_history.append(cv)

        # Detect violation in rolling window (last 3 tiles)
        if len(room.signatures) >= 3:
            window_cv = _entropy_cv(room.signatures[-3:])
            if window_cv > CV_THRESHOLD_CRITICAL:
                room.violation_count += 1

        # Update alert level
        room.last_alert = ConservationAlert.from_cv(cv)

        # Update trend slope on last TREND_WINDOW_SIZE entries
        if len(room.cv_history) >= 2:
            trend_window = room.cv_history[-TREND_WINDOW_SIZE:]
            room.trend_slope = _linear_regression_slope(trend_window)

    def observe_with_type(
        self, room_id: str, tile: Tile, room_type: Optional[RoomType] = None
    ) -> None:
        """Observe a tile with explicit room type annotation."""
        self.observe(room_id, tile)
        if room_id in self._rooms and room_type is not None:
            self._rooms[room_id].room_type = room_type

    # ── Snapshot ──

    def snapshot(self, room_id: str) -> Optional[RoomHealthSnapshot]:
        """Get a health snapshot for a single room."""
        if room_id not in self._rooms:
            return None
        room = self._rooms[room_id]
        cv = _entropy_cv(room.signatures) if room.signatures else 0.0
        stats = _compute_entropy_stats(room.signatures)
        alert = ConservationAlert.from_cv(cv)
        metrics = RoomHealthMetrics.from_signatures(room_id, room.signatures)

        # Trending dangerous: CV increasing AND at least WARNING level
        is_trending = (
            room.trend_slope > 0.01
            and len(room.cv_history) >= 3
            and (alert in (ConservationAlert.WARNING, ConservationAlert.ELEVATED, ConservationAlert.CRITICAL))
        )

        return RoomHealthSnapshot(
            room_id=room_id,
            cv=cv,
            alert=alert,
            tile_count=room.tile_count,
            violation_count=room.violation_count,
            avg_entropy=stats["mean"],
            entropy_variance=stats["std"] ** 2,
            trend_slope=room.trend_slope,
            is_trending_dangerous=is_trending,
            has_critical_alert=alert == ConservationAlert.CRITICAL,
            metrics=metrics,
            timestamp=time.time(),
        )

    # ── Dashboard ──

    def dashboard(self) -> DashboardSnapshot:
        """Produce aggregate dashboard of all monitored rooms."""
        snapshots: dict[str, RoomHealthSnapshot] = {}
        for room_id in self._rooms:
            snap = self.snapshot(room_id)
            if snap is not None:
                snapshots[room_id] = snap

        critical = [s for s in snapshots.values() if s.has_critical_alert]
        warning = [s for s in snapshots.values() if s.alert == ConservationAlert.WARNING]
        trending = [s for s in snapshots.values() if s.is_trending_dangerous]

        # Fleet health score: weighted average of (1 - cv) across rooms
        # Each room contributes proportionally to its tile count
        total_weight = sum(s.tile_count for s in snapshots.values()) or 1
        fleet_health = sum(
            max(0.0, 1.0 - s.cv) * s.tile_count / total_weight
            for s in snapshots.values()
        )

        return DashboardSnapshot(
            room_snapshots=snapshots,
            overall_fleet_health=round(fleet_health, 4),
            critical_rooms=critical,
            warning_rooms=warning,
            trending_rooms=trending,
            total_rooms=len(snapshots),
            total_tiles=self.total_tiles,
            total_violations=self.total_violations,
            timestamp=time.time(),
        )

    # ── Violation Detection ──

    def check_violations(self, room_id: str) -> list[ConservationViolation]:
        """Check a room for conservation violations and return violation records."""
        if room_id not in self._rooms:
            return []

        room = self._rooms[room_id]
        if len(room.signatures) < 3:
            return []

        # Use rolling window over last 3 tiles
        cv = _entropy_cv(room.signatures[-3:])
        alert = ConservationAlert.from_cv(cv)

        if alert.value in ("quasi-static", "warning"):
            return []  # No violation

        # Analyze root cause
        root_cause, evidence = analyze_root_cause(room.signatures[-6:])
        action = recommend_action(root_cause, alert, room.trend_slope)

        violation = ConservationViolation(
            room_id=room_id,
            cv=cv,
            threshold=CV_THRESHOLD_CRITICAL if alert == ConservationAlert.CRITICAL else CV_THRESHOLD_ELEVATED,
            alert_level=alert,
            tile_count=room.tile_count,
            causal_signatures=list(room.signatures[-3:]),
            root_cause=root_cause,
            root_cause_evidence=evidence,
            recommended_action=action,
            timestamp=time.time(),
        )

        self._violations.append(violation)
        return [violation]

    def check_all_violations(self) -> list[ConservationViolation]:
        """Check all rooms for violations and return the new violations."""
        all_violations: list[ConservationViolation] = []
        for room_id in self._rooms:
            all_violations.extend(self.check_violations(room_id))
        return all_violations

    def recent_violations(self, n: int = 10) -> list[ConservationViolation]:
        """Return the n most recent violations."""
        return self._violations[-n:]

    # ── Health Tile Generation ──

    def make_health_tile(self, room_id: str) -> Optional[HealthTile]:
        """Create a HealthTile for a room for PLATO broadcasting."""
        snap = self.snapshot(room_id)
        if snap is None:
            return None

        return HealthTile(
            room_id=room_id,
            source_monitor=self._source_monitor,
            cv=snap.cv,
            alert=snap.alert,
            tile_count=snap.tile_count,
            violation_count=snap.violation_count,
            trend_slope=snap.trend_slope,
            fleet_health_contribution=max(0.0, 1.0 - snap.cv),
            timestamp=snap.timestamp,
        )

    def make_all_health_tiles(self) -> list[HealthTile]:
        """Create HealthTiles for all monitored rooms."""
        return [
            ht for room_id in self._rooms
            if (ht := self.make_health_tile(room_id)) is not None
        ]

    # ── Serialization ──

    def to_dict(self) -> dict:
        """Serialize the monitor state to a dict for diagnostics."""
        dash = self.dashboard()
        return {
            "room_count": self.room_count,
            "total_tiles": self.total_tiles,
            "total_violations": self.total_violations,
            "overall_fleet_health": dash.overall_fleet_health,
            "critical_room_count": len(dash.critical_rooms),
            "warning_room_count": len(dash.warning_rooms),
            "trending_room_count": len(dash.trending_rooms),
            "rooms": {
                rid: {
                    "tile_count": r.tile_count,
                    "violation_count": r.violation_count,
                    "cv": _entropy_cv(r.signatures),
                    "alert": r.last_alert.value,
                    "trend_slope": r.trend_slope,
                }
                for rid, r in self._rooms.items()
            },
        }


# ── Convenience / High-Level API ─────────────────────────────────────────────

class ConservationViolationHandler:
    """Handles conservation violations with logging, root cause analysis,
    and action recommendations.

    Usage:
        handler = ConservationViolationHandler()
        handler.handle(violation)
        print(handler.recent_reports)
    """

    def __init__(self) -> None:
        self._reports: list[dict] = []
        self._handled_count: int = 0

    @property
    def handled_count(self) -> int:
        return self._handled_count

    @property
    def recent_reports(self) -> list[dict]:
        return list(self._reports)

    def handle(self, violation: ConservationViolation) -> dict:
        """Handle a conservation violation.
        
        Returns a report dict with log entry, root cause, and recommended action.
        """
        report = {
            "violation_id": hashlib.sha256(
                json.dumps({
                    "room_id": violation.room_id,
                    "cv": violation.cv,
                    "timestamp": violation.timestamp,
                }, sort_keys=True).encode()
            ).hexdigest()[:12],
            "room_id": violation.room_id,
            "cv": round(violation.cv, 4),
            "threshold": violation.threshold,
            "alert_level": violation.alert_level.value,
            "tile_count": violation.tile_count,
            "root_cause": violation.root_cause.value,
            "root_cause_evidence": violation.root_cause_evidence,
            "recommended_action": violation.recommended_action.value,
            "timestamp": violation.timestamp,
            "handled_at": time.time(),
        }

        self._reports.append(report)
        self._handled_count += 1

        # Log to stderr for live monitoring
        import sys
        print(
            f"[ROOM_HEALTH:CRITICAL] Room {violation.room_id} — CV={violation.cv:.3f} "
            f"(threshold={violation.threshold}) — "
            f"Root cause: {violation.root_cause.value} — "
            f"Action: {violation.recommended_action.value}",
            file=sys.stderr,
        )

        return report

    def clear(self) -> None:
        self._reports.clear()
        self._handled_count = 0


class RoomHealthDashboard:
    """Aggregates health metrics across all rooms.
    
    Provides:
      - Per-room conservation CV
      - Trending rooms (CV increasing over last N tiles)
      - Critical alerts (rooms above critical threshold)
      - Overall fleet health score (weighted average)
    """

    def __init__(self, monitor: Optional[ConservationMonitor] = None) -> None:
        self._monitor = monitor or ConservationMonitor()

    @property
    def monitor(self) -> ConservationMonitor:
        return self._monitor

    def refresh(self) -> DashboardSnapshot:
        """Produce a fresh dashboard snapshot from current monitor state."""
        if self._monitor is None:
            raise RuntimeError("No monitor attached to dashboard")
        return self._monitor.dashboard()

    def per_room_cv(self) -> dict[str, float]:
        """Return dict mapping room_id → conservation CV."""
        snap = self.refresh()
        return {rid: s.cv for rid, s in snap.room_snapshots.items()}

    def critical_rooms(self) -> list[RoomHealthSnapshot]:
        """Return rooms currently in critical alert."""
        snap = self.refresh()
        return snap.critical_rooms

    def trending_rooms(self) -> list[RoomHealthSnapshot]:
        """Return rooms trending dangerously (CV increasing)."""
        snap = self.refresh()
        return snap.trending_rooms

    def fleet_health_score(self) -> float:
        """Return overall fleet health score (0–1)."""
        return self.refresh().overall_fleet_health

    def summary(self) -> dict:
        """Return a human-readable summary dict."""
        snap = self.refresh()
        return {
            "fleet_health": snap.overall_fleet_health,
            "total_rooms": snap.total_rooms,
            "total_tiles": snap.total_tiles,
            "total_violations": snap.total_violations,
            "critical_count": len(snap.critical_rooms),
            "warning_count": len(snap.warning_rooms),
            "trending_count": len(snap.trending_rooms),
            "critical_rooms": [s.room_id for s in snap.critical_rooms],
            "warning_rooms": [s.room_id for s in snap.warning_rooms],
            "trending_rooms": [s.room_id for s in snap.trending_rooms],
        }
