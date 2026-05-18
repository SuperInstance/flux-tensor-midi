"""Tests for room health monitoring — spectral conservation across PLATO rooms.

Covers:
  - ConservationMonitor with stable, drifting, and violating tiles
  - RoomHealthDashboard aggregation across rooms
  - ConservationViolationHandler with root cause analysis
  - HealthTile creation and serialization
  - Trend detection over tile sequences
"""

import json
import math
import time

import pytest

from spreader.room_health import (
    ConservationMonitor,
    ConservationViolationHandler,
    ConservationAlert,
    ConservationViolation,
    HealthTile,
    RoomHealthDashboard,
    ViolationRootCause,
    RecommendedAction,
    analyze_root_cause,
    recommend_action,
    _linear_regression_slope,
    _compute_entropy_stats,
    CV_THRESHOLD_WARNING,
    CV_THRESHOLD_CRITICAL,
)
from spreader.production import TileSignature
from spreader.pipeline import Tile
from spreader.types import RoomType


def _make_tile(label, confidence, room="test_room", **meta):
    return Tile(room_name=room, label=label, confidence=confidence, metadata=meta)


def _stable_tiles(n=10, room="test_room", base_conf=0.88):
    tiles = []
    for i in range(n):
        conf = base_conf + (i % 3 - 1) * 0.01
        tiles.append(_make_tile("ham", conf, room=room))
    return tiles


def _drifting_tiles(n=12, room="drift_room"):
    tiles = []
    for i in range(n):
        phase = (i % 4) / 4
        conf = 0.5 + 0.45 * math.cos(phase * 2 * math.pi)
        label = "spam" if conf > 0.7 else "ambiguous" if conf < 0.55 else "ham"
        conf = max(0.05, min(0.99, conf))
        tiles.append(_make_tile(label, conf, room=room))
    return tiles


def _violating_tiles(n=8, room="violation_room"):
    tiles = []
    pairs = [
        ("spam", 0.99), ("ambiguous", 0.05), ("spam", 0.98), ("ambiguous", 0.04),
        ("ham", 0.95), ("ambiguous", 0.06), ("spam", 0.97), ("ambiguous", 0.03),
    ]
    for i in range(min(n, len(pairs))):
        tiles.append(_make_tile(pairs[i][0], pairs[i][1], room=room))
    while len(tiles) < n:
        i = len(tiles) % len(pairs)
        tiles.append(_make_tile(pairs[i][0], pairs[i][1], room=room))
    return tiles


def _monotonic_drift_tiles(n=10, room="mono_room"):
    tiles = []
    for i in range(n):
        conf = max(0.99 - 0.09 * i, 0.1)
        label = "spam" if conf > 0.8 else "ham" if conf > 0.5 else "ambiguous"
        tiles.append(_make_tile(label, conf, room=room))
    return tiles

# ════════════════════════════════════════════════════════════════════════════
# ConservationMonitor — stable tiles (CV < 0.03)
# ════════════════════════════════════════════════════════════════════════════

class TestConservationMonitorStable:
    def test_empty_monitor(self):
        mon = ConservationMonitor()
        assert mon.room_count == 0
        assert mon.total_tiles == 0
        assert mon.total_violations == 0

    def test_stable_tiles_low_cv(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(20, room="room_a"):
            mon.observe("room_a", tile)
        snap = mon.snapshot("room_a")
        assert snap is not None
        assert snap.cv < 0.05
        assert snap.alert == ConservationAlert.QUASI_STATIC
        assert snap.tile_count == 20
        assert snap.violation_count == 0

    def test_stable_no_violations(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(20, room="room_b"):
            mon.observe("room_b", tile)
        violations = mon.check_violations("room_b")
        assert len(violations) == 0

    def test_stable_metrics_correct(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(10, room="room_c"):
            mon.observe("room_c", tile)
        snap = mon.snapshot("room_c")
        assert snap is not None
        assert snap.tile_count == 10
        assert snap.avg_entropy > 0
        assert snap.metrics.is_healthy is True

    def test_stable_no_trend(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(20, room="room_d"):
            mon.observe("room_d", tile)
        snap = mon.snapshot("room_d")
        assert snap is not None
        assert abs(snap.trend_slope) < 0.01


# ════════════════════════════════════════════════════════════════════════════
# ConservationMonitor — drifting tiles (CV ~ 0.3)
# ════════════════════════════════════════════════════════════════════════════

class TestConservationMonitorDrifting:
    def test_drifting_cv_warning(self):
        mon = ConservationMonitor()
        for tile in _drifting_tiles(12, room="drift_a"):
            mon.observe("drift_a", tile)
        snap = mon.snapshot("drift_a")
        assert snap is not None
        assert snap.cv >= CV_THRESHOLD_WARNING - 0.05
        assert snap.tile_count == 12

    def test_drifting_no_critical(self):
        mon = ConservationMonitor()
        for tile in _drifting_tiles(15, room="drift_b"):
            mon.observe("drift_b", tile)
        violations = mon.check_violations("drift_b")
        assert len(violations) < 2

    def test_drifting_has_some_variance(self):
        mon = ConservationMonitor()
        for tile in _drifting_tiles(12, room="drift_c"):
            mon.observe("drift_c", tile)
        snap = mon.snapshot("drift_c")
        assert snap is not None
        assert snap.entropy_variance > 0.001


# ════════════════════════════════════════════════════════════════════════════
# ConservationMonitor — violating tiles (CV > 0.5)
# ════════════════════════════════════════════════════════════════════════════

class TestConservationMonitorViolating:
    def test_violating_critical_cv(self):
        mon = ConservationMonitor()
        for tile in _violating_tiles(8, room="viol_a"):
            mon.observe("viol_a", tile)
        snap = mon.snapshot("viol_a")
        assert snap is not None
        assert snap.cv > CV_THRESHOLD_CRITICAL
        assert snap.has_critical_alert is True
        assert snap.violation_count > 0

    def test_violating_triggers_violations(self):
        mon = ConservationMonitor()
        for tile in _violating_tiles(8, room="viol_b"):
            mon.observe("viol_b", tile)
        violations = mon.check_violations("viol_b")
        assert len(violations) >= 1
        for v in violations:
            assert v.alert_level in (ConservationAlert.ELEVATED, ConservationAlert.CRITICAL)
            assert v.root_cause != ViolationRootCause.UNKNOWN

    def test_violating_root_cause_rapid_shape(self):
        mon = ConservationMonitor()
        for tile in _violating_tiles(8, room="viol_rshape"):
            mon.observe("viol_rshape", tile)
        violations = mon.check_violations("viol_rshape")
        assert any(v.root_cause == ViolationRootCause.RAPID_SHAPE_CHANGE for v in violations)

    def test_violating_violation_record(self):
        mon = ConservationMonitor()
        for tile in _violating_tiles(8, room="viol_rec"):
            mon.observe("viol_rec", tile)
        violations = mon.check_violations("viol_rec")
        assert len(violations) >= 1
        v = violations[0]
        assert v.room_id == "viol_rec"
        assert v.cv > 0
        assert v.tile_count == 8
        assert len(v.causal_signatures) >= 3

    def test_violating_recent_violations(self):
        mon = ConservationMonitor()
        for tile in _violating_tiles(8, room="viol_recent"):
            mon.observe("viol_recent", tile)
        mon.check_violations("viol_recent")
        recent = mon.recent_violations(5)
        assert len(recent) >= 1


# ════════════════════════════════════════════════════════════════════════════
# Root cause analysis
# ════════════════════════════════════════════════════════════════════════════

class TestRootCauseAnalysis:
    def test_rapid_shape_change(self):
        sigs = []
        for label, conf in [
            ("spam", 0.99), ("ambiguous", 0.05), ("spam", 0.98), ("ambiguous", 0.04),
            ("spam", 0.97), ("ambiguous", 0.06),
        ]:
            tile = _make_tile(label, conf, room="test")
            sigs.append(TileSignature.compute(tile))
        cause, evidence = analyze_root_cause(sigs)
        assert cause == ViolationRootCause.RAPID_SHAPE_CHANGE
        assert "rapid" in evidence.lower()

    def test_coupling_breakdown(self):
        sigs = []
        # Same label, monotonic confidence drop — entropy monotonically increases
        for conf in [0.99, 0.92, 0.85, 0.78, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20]:
            tile = _make_tile("spam", conf, room="test")
            sigs.append(TileSignature.compute(tile))
        cause, evidence = analyze_root_cause(sigs)
        assert cause == ViolationRootCause.COUPLING_BREAKDOWN
        assert "drift" in evidence.lower() or "monotonic" in evidence.lower()

    def test_sensor_drift_or_unknown(self):
        sigs = []
        for i in range(10):
            conf = max(0.9 - i * 0.06, 0.1)
            if i in (3, 7):
                conf = 0.05
            label = "spam" if conf > 0.7 else "ham" if conf > 0.4 else "ambiguous"
            tile = _make_tile(label, conf, room="test")
            sigs.append(TileSignature.compute(tile))
        cause, evidence = analyze_root_cause(sigs)
        assert cause in (
            ViolationRootCause.COUPLING_BREAKDOWN,
            ViolationRootCause.SENSOR_DRIFT,
            ViolationRootCause.UNKNOWN,
        )

    def test_insufficient_data(self):
        sigs = [
            TileSignature.compute(_make_tile("spam", 0.95, room="test")),
            TileSignature.compute(_make_tile("ham", 0.5, room="test")),
        ]
        cause, evidence = analyze_root_cause(sigs)
        assert cause == ViolationRootCause.UNKNOWN
        assert "insufficient" in evidence.lower()

    def test_unknown_pattern(self):
        sigs = []
        for conf in [0.5, 0.55, 0.52, 0.48, 0.53, 0.51]:
            tile = _make_tile("ham", conf, room="test")
            sigs.append(TileSignature.compute(tile))
        cause, evidence = analyze_root_cause(sigs)
        assert isinstance(cause, ViolationRootCause)


# ════════════════════════════════════════════════════════════════════════════
# Action Recommendation
# ════════════════════════════════════════════════════════════════════════════

class TestRecommendAction:
    def test_rapid_shape_increases_alpha(self):
        action = recommend_action(ViolationRootCause.RAPID_SHAPE_CHANGE,
                                  ConservationAlert.ELEVATED, 0.1)
        assert action == RecommendedAction.INCREASE_ALPHA

    def test_coupling_breakdown_reduces_compression(self):
        action = recommend_action(ViolationRootCause.COUPLING_BREAKDOWN,
                                  ConservationAlert.CRITICAL, -0.3)
        assert action == RecommendedAction.REDUCE_COMPRESSION

    def test_sensor_drift_preserves_verbatim(self):
        action = recommend_action(ViolationRootCause.SENSOR_DRIFT,
                                  ConservationAlert.WARNING, 0.2)
        assert action == RecommendedAction.PRESERVE_VERBATIM

    def test_critical_escalates(self):
        action = recommend_action(ViolationRootCause.UNKNOWN,
                                  ConservationAlert.CRITICAL, 0.0)
        assert action == RecommendedAction.ESCALATE

    def test_quasi_static_no_action(self):
        action = recommend_action(ViolationRootCause.UNKNOWN,
                                  ConservationAlert.QUASI_STATIC, 0.0)
        assert action == RecommendedAction.NONE

    def test_unknown_generic_recheck(self):
        action = recommend_action(ViolationRootCause.UNKNOWN,
                                  ConservationAlert.WARNING, 0.01)
        assert action == RecommendedAction.RECHECK

# ════════════════════════════════════════════════════════════════════════════
# Dashboard aggregation
# ════════════════════════════════════════════════════════════════════════════

class TestDashboardAggregation:
    def test_single_room_dashboard(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(10, room="room1"):
            mon.observe("room1", tile)
        dash = mon.dashboard()
        assert dash.total_rooms == 1
        assert dash.total_tiles == 10
        assert dash.overall_fleet_health > 0.9

    def test_multi_room_dashboard(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(20, room="room1"):
            mon.observe("room1", tile)
        for tile in _drifting_tiles(12, room="room2"):
            mon.observe("room2", tile)
        for tile in _violating_tiles(8, room="room3"):
            mon.observe("room3", tile)
        for tile in _stable_tiles(10, room="room5"):
            mon.observe("room5", tile)
        dash = mon.dashboard()
        assert dash.total_rooms == 4
        assert dash.room_snapshots["room1"].alert == ConservationAlert.QUASI_STATIC
        assert dash.room_snapshots["room3"].has_critical_alert is True

    def test_dashboard_critical_rooms(self):
        mon = ConservationMonitor()
        for tile in _violating_tiles(8, room="crit_room"):
            mon.observe("crit_room", tile)
        for tile in _stable_tiles(10, room="good_room"):
            mon.observe("good_room", tile)
        dash = mon.dashboard()
        assert len(dash.critical_rooms) == 1
        assert dash.critical_rooms[0].room_id == "crit_room"

    def test_dashboard_trending_rooms(self):
        mon = ConservationMonitor()
        for tile in _drifting_tiles(20, room="trend_room"):
            mon.observe("trend_room", tile)
        dash = mon.dashboard()
        assert isinstance(dash.trending_rooms, list)

    def test_dashboard_weighted_health(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(10, room="big"):
            mon.observe("big", tile)
        for tile in _violating_tiles(2, room="small"):
            mon.observe("small", tile)
        dash = mon.dashboard()
        assert dash.overall_fleet_health > 0.5

    def test_dashboard_warning_rooms(self):
        mon = ConservationMonitor()
        for tile in _drifting_tiles(10, room="warn_room"):
            mon.observe("warn_room", tile)
        dash = mon.dashboard()
        assert isinstance(dash.warning_rooms, list)

    def test_dashboard_5_rooms(self):
        mon = ConservationMonitor()
        rooms = ["room1", "room2", "room3", "room4", "room5"]
        for i, rid in enumerate(rooms):
            for tile in _stable_tiles(5 + i, room=rid):
                mon.observe(rid, tile)
        dash = mon.dashboard()
        assert dash.total_rooms == 5
        assert len(dash.room_snapshots) == 5


# ════════════════════════════════════════════════════════════════════════════
# Violation handler
# ════════════════════════════════════════════════════════════════════════════

class TestConservationViolationHandler:
    def test_handle_violation(self):
        handler = ConservationViolationHandler()
        violation = ConservationViolation(
            room_id="test_room",
            cv=0.85,
            threshold=0.7,
            alert_level=ConservationAlert.CRITICAL,
            tile_count=15,
            causal_signatures=[],
            root_cause=ViolationRootCause.RAPID_SHAPE_CHANGE,
            root_cause_evidence="Alternating entropy pattern detected",
            recommended_action=RecommendedAction.INCREASE_ALPHA,
            timestamp=time.time(),
        )
        report = handler.handle(violation)
        assert report["room_id"] == "test_room"
        assert report["cv"] == 0.85
        assert report["root_cause"] == "rapid_shape_change"
        assert report["recommended_action"] == "increase_alpha"
        assert "violation_id" in report
        assert handler.handled_count == 1

    def test_multiple_violations(self):
        handler = ConservationViolationHandler()
        for i in range(5):
            vio = ConservationViolation(
                room_id=f"room_{i}",
                cv=0.7 + i * 0.05,
                threshold=0.7,
                alert_level=ConservationAlert.CRITICAL,
                tile_count=10 + i,
                causal_signatures=[],
                root_cause=ViolationRootCause.COUPLING_BREAKDOWN,
                root_cause_evidence="Monotonic entropy drift",
                recommended_action=RecommendedAction.REDUCE_COMPRESSION,
                timestamp=time.time(),
            )
            handler.handle(vio)
        assert handler.handled_count == 5
        assert len(handler.recent_reports) == 5

    def test_clear_handler(self):
        handler = ConservationViolationHandler()
        for i in range(3):
            vio = ConservationViolation(
                room_id=f"room_{i}",
                cv=0.8,
                threshold=0.7,
                alert_level=ConservationAlert.CRITICAL,
                tile_count=10,
                causal_signatures=[],
                root_cause=ViolationRootCause.UNKNOWN,
                root_cause_evidence="test",
                recommended_action=RecommendedAction.ESCALATE,
                timestamp=time.time(),
            )
            handler.handle(vio)
        assert handler.handled_count == 3
        handler.clear()
        assert handler.handled_count == 0
        assert len(handler.recent_reports) == 0

    def test_violation_dict(self):
        vio = ConservationViolation(
            room_id="test_room",
            cv=0.92,
            threshold=0.7,
            alert_level=ConservationAlert.CRITICAL,
            tile_count=20,
            causal_signatures=[],
            root_cause=ViolationRootCause.RAPID_SHAPE_CHANGE,
            root_cause_evidence="test evidence",
            recommended_action=RecommendedAction.INCREASE_ALPHA,
            timestamp=1234567890.0,
        )
        d = vio.to_dict()
        assert d["room_id"] == "test_room"
        assert d["cv"] == 0.92
        assert d["alert_level"] == "critical"
        assert d["root_cause"] == "rapid_shape_change"


# ════════════════════════════════════════════════════════════════════════════
# HealthTile
# ════════════════════════════════════════════════════════════════════════════

class TestHealthTile:
    def test_create_health_tile(self):
        ht = HealthTile(
            room_id="room_a",
            source_monitor="forgemaster",
            cv=0.15,
            alert=ConservationAlert.QUASI_STATIC,
            tile_count=100,
            violation_count=0,
            trend_slope=0.001,
            fleet_health_contribution=0.85,
            timestamp=1000.0,
        )
        assert ht.room_id == "room_a"
        assert ht.source_monitor == "forgemaster"
        assert ht.cv == 0.15
        assert ht.alert == ConservationAlert.QUASI_STATIC
        assert ht.serialized != ""

    def test_health_tile_auto_serialize(self):
        ht = HealthTile(
            room_id="room_b",
            source_monitor="oracle1",
            cv=0.72,
            alert=ConservationAlert.CRITICAL,
            tile_count=50,
            violation_count=3,
            trend_slope=0.05,
            fleet_health_contribution=0.28,
            timestamp=2000.0,
        )
        parsed = json.loads(ht.serialized)
        assert parsed["type"] == "health_tile"
        assert parsed["room_id"] == "room_b"
        assert parsed["source_monitor"] == "oracle1"
        assert parsed["alert"] == "critical"

    def test_health_tile_from_json(self):
        original = HealthTile(
            room_id="room_c",
            source_monitor="ensign",
            cv=0.05,
            alert=ConservationAlert.QUASI_STATIC,
            tile_count=200,
            violation_count=0,
            trend_slope=0.002,
            fleet_health_contribution=0.95,
            timestamp=3000.0,
        )
        restored = HealthTile.from_json(original.serialized)
        assert restored == original
        assert restored.room_id == "room_c"

    def test_health_tile_to_bytes(self):
        ht = HealthTile(
            room_id="room_d",
            source_monitor="forgemaster",
            cv=0.3,
            alert=ConservationAlert.WARNING,
            tile_count=75,
            violation_count=1,
            trend_slope=0.01,
            fleet_health_contribution=0.7,
            timestamp=4000.0,
        )
        data = ht.to_bytes()
        assert isinstance(data, bytes)
        restored = HealthTile.from_json(data.decode("utf-8"))
        assert restored == ht

    def test_monitor_makes_health_tile(self):
        mon = ConservationMonitor(source_monitor="ensign-alpha")
        for tile in _stable_tiles(10, room="ht_room"):
            mon.observe("ht_room", tile)
        ht = mon.make_health_tile("ht_room")
        assert ht is not None
        assert ht.source_monitor == "ensign-alpha"
        assert ht.room_id == "ht_room"
        assert ht.alert == ConservationAlert.QUASI_STATIC
        assert ht.fleet_health_contribution > 0.9

    def test_monitor_makes_all_health_tiles(self):
        mon = ConservationMonitor(source_monitor="fleet-mon")
        for tile in _stable_tiles(5, room="alpha"):
            mon.observe("alpha", tile)
        for tile in _drifting_tiles(8, room="beta"):
            mon.observe("beta", tile)
        for tile in _violating_tiles(6, room="gamma"):
            mon.observe("gamma", tile)
        tiles = mon.make_all_health_tiles()
        assert len(tiles) == 3
        room_ids = {t.room_id for t in tiles}
        assert room_ids == {"alpha", "beta", "gamma"}

    def test_health_tile_none_for_missing_room(self):
        mon = ConservationMonitor()
        ht = mon.make_health_tile("nonexistent")
        assert ht is None

    def test_health_tile_serialization_roundtrip(self):
        mon = ConservationMonitor(source_monitor="fleet-mon")
        for tile in _stable_tiles(15, room="roundtrip"):
            mon.observe("roundtrip", tile)
        ht = mon.make_health_tile("roundtrip")
        assert ht is not None
        restored = HealthTile.from_json(ht.serialized)
        assert restored.room_id == ht.room_id
        assert restored.cv == ht.cv
        assert restored.fleet_health_contribution == ht.fleet_health_contribution

# ════════════════════════════════════════════════════════════════════════════
# Trend detection
# ════════════════════════════════════════════════════════════════════════════

class TestTrendDetection:
    def test_linear_regression_slope_flat(self):
        values = [5.0] * 10
        slope = _linear_regression_slope(values)
        assert abs(slope) < 1e-10

    def test_linear_regression_slope_positive(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        slope = _linear_regression_slope(values)
        assert slope == pytest.approx(1.0, abs=0.01)

    def test_linear_regression_slope_negative(self):
        values = [5.0, 4.0, 3.0, 2.0, 1.0]
        slope = _linear_regression_slope(values)
        assert slope == pytest.approx(-1.0, abs=0.01)

    def test_less_than_two_values(self):
        assert _linear_regression_slope([1.0]) == 0.0
        assert _linear_regression_slope([]) == 0.0

    def test_stable_tiles_zero_trend(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(20, room="trend_stable"):
            mon.observe("trend_stable", tile)
        snap = mon.snapshot("trend_stable")
        assert snap is not None
        assert abs(snap.trend_slope) < 0.01

    def test_monotonic_drift_detected(self):
        mon = ConservationMonitor()
        for tile in _monotonic_drift_tiles(20, room="trend_mono"):
            mon.observe("trend_mono", tile)
        snap = mon.snapshot("trend_mono")
        assert snap is not None
        assert snap.trend_slope != 0.0

    def test_trend_in_drifting_room(self):
        mon = ConservationMonitor()
        for tile in _drifting_tiles(25, room="trend_drift"):
            mon.observe("trend_drift", tile)
        data = mon.get_room("trend_drift")
        assert data is not None
        assert data.trend_slope != 0.0

    def test_detected_over_20_tiles(self):
        mon = ConservationMonitor()
        for tile in _drifting_tiles(20, room="trend_20"):
            mon.observe("trend_20", tile)
        snap = mon.snapshot("trend_20")
        assert snap is not None
        assert snap.tile_count == 20


# ════════════════════════════════════════════════════════════════════════════
# ConservationMonitor — multi-room ops
# ════════════════════════════════════════════════════════════════════════════

class TestConservationMonitorMultiRoom:
    def test_multiple_rooms_independent(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(10, room="indep_a"):
            mon.observe("indep_a", tile)
        for tile in _violating_tiles(8, room="indep_b"):
            mon.observe("indep_b", tile)
        snap_a = mon.snapshot("indep_a")
        snap_b = mon.snapshot("indep_b")
        assert snap_a is not None and snap_b is not None
        assert snap_a.alert == ConservationAlert.QUASI_STATIC
        assert snap_b.has_critical_alert is True

    def test_room_count_correct(self):
        mon = ConservationMonitor()
        for rid in ["alpha", "beta", "gamma", "delta"]:
            for tile in _stable_tiles(5, room=rid):
                mon.observe(rid, tile)
        assert mon.room_count == 4

    def test_observe_with_type(self):
        mon = ConservationMonitor()
        tile = _make_tile("spam", 0.85, room="typed")
        mon.observe_with_type("typed", tile, RoomType.SENSOR)
        data = mon.get_room("typed")
        assert data is not None
        assert data.room_type == RoomType.SENSOR

    def test_total_tiles_aggregated(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(10, room="agg_a"):
            mon.observe("agg_a", tile)
        for tile in _stable_tiles(7, room="agg_b"):
            mon.observe("agg_b", tile)
        for tile in _drifting_tiles(5, room="agg_c"):
            mon.observe("agg_c", tile)
        assert mon.total_tiles == 22

    def test_total_violations(self):
        mon = ConservationMonitor()
        for tile in _violating_tiles(8, room="vio_a"):
            mon.observe("vio_a", tile)
        for tile in _violating_tiles(8, room="vio_b"):
            mon.observe("vio_b", tile)
        mon.check_all_violations()
        assert mon.total_violations >= 2

    def test_to_dict_serialization(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(5, room="ser_a"):
            mon.observe("ser_a", tile)
        for tile in _drifting_tiles(5, room="ser_b"):
            mon.observe("ser_b", tile)
        d = mon.to_dict()
        assert d["room_count"] == 2
        assert d["total_tiles"] == 10
        assert "overall_fleet_health" in d
        assert "ser_a" in d["rooms"]
        assert "ser_b" in d["rooms"]

    def test_non_existent_room(self):
        mon = ConservationMonitor()
        snap = mon.snapshot("nonexistent")
        assert snap is None
        assert mon.check_violations("nonexistent") == []

    def test_get_room(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(3, room="get_test"):
            mon.observe("get_test", tile)
        data = mon.get_room("get_test")
        assert data is not None
        assert data.tile_count == 3
        assert len(data.signatures) == 3

    def test_clear(self):
        mon = ConservationMonitor()
        for tile in _violating_tiles(8, room="clear_test"):
            mon.observe("clear_test", tile)
        mon.check_violations("clear_test")
        assert mon.room_count == 1
        assert mon.total_violations >= 1
        mon.clear()
        assert mon.room_count == 0
        assert mon.total_violations == 0


# ════════════════════════════════════════════════════════════════════════════
# ConservationAlert
# ════════════════════════════════════════════════════════════════════════════

class TestConservationAlert:
    def test_quasi_static_below_03(self):
        assert ConservationAlert.from_cv(0.0) == ConservationAlert.QUASI_STATIC
        assert ConservationAlert.from_cv(0.15) == ConservationAlert.QUASI_STATIC
        assert ConservationAlert.from_cv(0.29) == ConservationAlert.QUASI_STATIC

    def test_warning_03_to_05(self):
        assert ConservationAlert.from_cv(0.3) == ConservationAlert.WARNING
        assert ConservationAlert.from_cv(0.4) == ConservationAlert.WARNING
        assert ConservationAlert.from_cv(0.49) == ConservationAlert.WARNING

    def test_elevated_05_to_07(self):
        assert ConservationAlert.from_cv(0.5) == ConservationAlert.ELEVATED
        assert ConservationAlert.from_cv(0.6) == ConservationAlert.ELEVATED
        assert ConservationAlert.from_cv(0.69) == ConservationAlert.ELEVATED

    def test_critical_above_07(self):
        assert ConservationAlert.from_cv(0.7) == ConservationAlert.CRITICAL
        assert ConservationAlert.from_cv(0.85) == ConservationAlert.CRITICAL
        assert ConservationAlert.from_cv(1.0) == ConservationAlert.CRITICAL
        assert ConservationAlert.from_cv(10.0) == ConservationAlert.CRITICAL


# ════════════════════════════════════════════════════════════════════════════
# Edge cases
# ════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_single_tile_snapshot(self):
        mon = ConservationMonitor()
        mon.observe("room_x", _make_tile("spam", 0.9, room="room_x"))
        snap = mon.snapshot("room_x")
        assert snap is not None
        assert snap.cv == 0.0

    def test_two_tiles_snapshot(self):
        mon = ConservationMonitor()
        mon.observe("room_x", _make_tile("spam", 0.9, room="room_x"))
        mon.observe("room_x", _make_tile("ham", 0.3, room="room_x"))
        snap = mon.snapshot("room_x")
        assert snap is not None
        assert snap.tile_count == 2
        assert snap.cv >= 0

    def test_violations_on_empty_room(self):
        mon = ConservationMonitor()
        result = mon.check_violations("nonexistent")
        assert result == []

    def test_no_violation_below_threshold(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(5, room="no_viol"):
            mon.observe("no_viol", tile)
        result = mon.check_violations("no_viol")
        assert result == []

    def test_room_health_dashboard_standalone(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(10, room="dash_room"):
            mon.observe("dash_room", tile)
        dashboard = RoomHealthDashboard(monitor=mon)
        assert dashboard.fleet_health_score() > 0.9
        dash = dashboard.refresh()
        assert dash.total_rooms == 1

    def test_room_health_dashboard_summary(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(10, room="sum_a"):
            mon.observe("sum_a", tile)
        for tile in _violating_tiles(6, room="sum_b"):
            mon.observe("sum_b", tile)
        dashboard = RoomHealthDashboard(monitor=mon)
        summary = dashboard.summary()
        assert summary["total_rooms"] == 2
        assert summary["critical_count"] == 1
        assert summary["fleet_health"] > 0

    def test_room_health_dashboard_per_room_cv(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(5, room="cv_a"):
            mon.observe("cv_a", tile)
        for tile in _drifting_tiles(8, room="cv_b"):
            mon.observe("cv_b", tile)
        dashboard = RoomHealthDashboard(monitor=mon)
        cvs = dashboard.per_room_cv()
        assert "cv_a" in cvs
        assert "cv_b" in cvs
        assert cvs["cv_a"] < cvs["cv_b"]

    def test_overall_fleet_health_score_calculation(self):
        mon = ConservationMonitor()
        for tile in _stable_tiles(20, room="good_health"):
            mon.observe("good_health", tile)
        dash = mon.dashboard()
        # Stable room → health close to 1.0
        assert dash.overall_fleet_health > 0.95

    def test_recent_violations_ordering(self):
        mon = ConservationMonitor()
        for tile in _violating_tiles(8, room="order_test"):
            mon.observe("order_test", tile)
        mon.check_violations("order_test")
        recent = mon.recent_violations(10)
        assert len(recent) >= 1
        # Multiple checks accumulate violations
        for _ in range(3):
            mon.check_violations("order_test")
        recent2 = mon.recent_violations(10)
        assert len(recent2) >= len(recent)
