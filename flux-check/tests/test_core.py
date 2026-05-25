"""Tests for flux_check.core — ConstraintEngine."""

import sys, os, json, tempfile
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flux_check.core import (
    ConstraintEngine, CheckResult, Severity, ConstraintDef, ViolationDetail,
    _severity_for_count,
)
from flux_check.presets import get_preset, available_presets


# ── ConstraintDef tests ─────────────────────────────────────

class TestConstraintDef:
    def test_valid_constraint(self):
        cd = ConstraintDef(lo=0.0, hi=100.0, name="temp")
        assert cd.lo == 0.0
        assert cd.hi == 100.0
        assert cd.name == "temp"

    def test_inverted_bounds_raises(self):
        with pytest.raises(ValueError, match="lo.*>.*hi"):
            ConstraintDef(lo=100.0, hi=0.0, name="bad")

    def test_default_severity_is_warning(self):
        cd = ConstraintDef(lo=0, hi=1, name="x")
        assert cd.severity == Severity.WARNING


# ── Severity tests ──────────────────────────────────────────

class TestSeverity:
    def test_severity_values(self):
        assert Severity.PASS == 0
        assert Severity.CAUTION == 1
        assert Severity.WARNING == 2
        assert Severity.CRITICAL == 3

    def test_severity_for_count(self):
        assert _severity_for_count(0) == Severity.PASS
        assert _severity_for_count(1) == Severity.CAUTION
        assert _severity_for_count(3) == Severity.WARNING
        assert _severity_for_count(5) == Severity.CRITICAL
        assert _severity_for_count(100) == Severity.CRITICAL


# ── ConstraintEngine construction ───────────────────────────

class TestConstraintEngineConstruction:
    def test_basic_construction(self):
        engine = ConstraintEngine([
            {"name": "x", "lo": 0, "hi": 10},
        ])
        assert engine.n == 1
        assert engine._names == ("x",)

    def test_max_8_constraints(self):
        with pytest.raises(ValueError, match="Maximum 8"):
            ConstraintEngine([{"name": f"c{i}", "lo": 0, "hi": 1} for i in range(9)])

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            ConstraintEngine([])

    def test_inverted_bounds_raises(self):
        with pytest.raises(ValueError, match="lo.*>.*hi"):
            ConstraintEngine([{"name": "x", "lo": 10, "hi": 0}])


# ── check_mask ──────────────────────────────────────────────

class TestCheckMask:
    @pytest.fixture
    def engine(self):
        return ConstraintEngine([
            {"name": "a", "lo": 0, "hi": 10},
            {"name": "b", "lo": -5, "hi": 5},
        ])

    def test_pass_all(self, engine):
        assert engine.check_mask(3) == 0

    def test_violate_first(self, engine):
        assert engine.check_mask(-1) == 1  # bit 0 set

    def test_violate_second(self, engine):
        assert engine.check_mask(6) == 2  # bit 1 set

    def test_violate_both(self, engine):
        assert engine.check_mask(-10) == 3  # both bits set

    def test_nan_violates_all(self, engine):
        assert engine.check_mask(float("nan")) == 3

    def test_boundary_values(self, engine):
        # engine: a=[0,10], b=[-5,5]
        assert engine.check_mask(0) == 0   # inside both
        assert engine.check_mask(10) == 2  # ok for a (not >10), but >5 violates b
        assert engine.check_mask(-5) == 1  # ok for b (not <-5), but <0 violates a
        assert engine.check_mask(5) == 0   # ok for both


# ── check (full result) ────────────────────────────────────

class TestCheck:
    @pytest.fixture
    def engine(self):
        return ConstraintEngine([
            {"name": "temp", "lo": 0, "hi": 100, "severity": 3},
            {"name": "speed", "lo": 0, "hi": 50, "severity": 2},
        ])

    def test_pass(self, engine):
        r = engine.check(25)
        assert r.passed
        assert r.violated_count == 0
        assert r.severity == Severity.PASS

    def test_fail_with_severity(self, engine):
        r = engine.check(-1)
        assert not r.passed
        assert r.severity == Severity.CRITICAL  # constraint 0 has severity 3

    def test_violation_details(self, engine):
        r = engine.check(60)
        assert r.violated_count == 1
        assert not r.violations[1].passed  # speed violated
        assert r.violations[1].hi_violated is True

    def test_to_dict(self, engine):
        r = engine.check(25)
        d = r.to_dict()
        assert d["passed"]
        assert "violations" in d
        assert len(d["violations"]) == 2


# ── check_vector ────────────────────────────────────────────

class TestCheckVector:
    def test_all_pass(self):
        engine = ConstraintEngine([
            {"name": "a", "lo": 0, "hi": 10},
            {"name": "b", "lo": 0, "hi": 10},
        ])
        r = engine.check_vector([5, 5])
        assert r.passed

    def test_wrong_length_raises(self):
        engine = ConstraintEngine([{"name": "a", "lo": 0, "hi": 10}])
        with pytest.raises(ValueError, match="Expected 1"):
            engine.check_vector([1, 2])


# ── check_batch ─────────────────────────────────────────────

class TestCheckBatch:
    def test_batch(self):
        engine = ConstraintEngine([{"name": "x", "lo": 0, "hi": 10}])
        masks = engine.check_batch([5, -1, 11])
        assert masks[0] == 0
        assert masks[1] == 1
        assert masks[2] == 1


# ── Presets ─────────────────────────────────────────────────

class TestPresets:
    def test_load_preset(self):
        engine = ConstraintEngine.from_preset("automotive_can")
        assert engine.n == 8

    def test_available_presets(self):
        presets = ConstraintEngine.available_presets()
        assert "automotive_can" in presets
        assert len(presets) >= 10

    def test_unknown_preset_raises(self):
        with pytest.raises(KeyError):
            ConstraintEngine.from_preset("nonexistent")


# ── Serialization ───────────────────────────────────────────

class TestSerialization:
    def test_to_dict_from_dict(self):
        engine = ConstraintEngine([
            {"name": "a", "lo": -1, "hi": 1},
        ])
        d = engine.to_dict()
        engine2 = ConstraintEngine.from_dict(d)
        assert engine2.n == 1
        assert engine2.check_mask(0) == 0

    def test_save_load(self):
        engine = ConstraintEngine([{"name": "x", "lo": 0, "hi": 100}])
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            engine.save(path)
            engine2 = ConstraintEngine.load(path)
            assert engine2.n == 1
            assert engine2.check_mask(50) == 0
        finally:
            os.unlink(path)


# ── get_bounds ──────────────────────────────────────────────

class TestGetBounds:
    def test_get_bounds(self):
        engine = ConstraintEngine([
            {"name": "a", "lo": 0, "hi": 10},
            {"name": "b", "lo": -5, "hi": 5},
        ])
        bounds = engine.get_bounds()
        assert bounds[0] == ("a", 0.0, 10.0)
        assert bounds[1] == ("b", -5.0, 5.0)
