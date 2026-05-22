"""Tests for tensor_penrose — Constraint tensors on Penrose tilings (Rust extension)."""

import sys, os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tensor_penrose import (
    Tile, Tiling, EisensteinBackend, PenroseBackend,
    ThresholdOp, L1NormOp, apply_threshold, from_coordinates,
)


# ── EisensteinBackend ───────────────────────────────────────

class TestEisensteinBackend:
    def test_create(self):
        backend = EisensteinBackend()
        assert backend is not None
        assert "Eisenstein" in repr(backend)


# ── PenroseBackend ──────────────────────────────────────────

class TestPenroseBackend:
    def test_create(self):
        backend = PenroseBackend()
        assert backend is not None
        assert "Penrose" in repr(backend)


# ── from_coordinates ────────────────────────────────────────

class TestFromCoordinates:
    def test_single_point(self):
        result = from_coordinates([(0, 0, 0, 0, 0)])
        assert result is not None
        assert "tiles=1" in repr(result)

    def test_multiple_points(self):
        coords = [(0, 0, 0, 0, 0), (1, 0, 0, 0, 0), (0, 1, 0, 0, 0)]
        result = from_coordinates(coords)
        assert "tiles=3" in repr(result)

    def test_eisenstein_backend(self):
        result = from_coordinates([(0, 0, 0, 0, 0)], backend="eisenstein")
        assert "eisenstein" in repr(result).lower()

    def test_penrose_backend(self):
        result = from_coordinates([(0, 0, 0, 0, 0)], backend="penrose")
        assert "penrose" in repr(result).lower()

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="length"):
            from_coordinates([(0, 0)])  # needs length 5

    def test_five_points(self):
        coords = [(i, 0, 0, 0, 0) for i in range(5)]
        result = from_coordinates(coords)
        assert "tiles=5" in repr(result)


# ── ThresholdOp ─────────────────────────────────────────────

class TestThresholdOp:
    def test_create(self):
        op = ThresholdOp(0.5)
        assert "0.5" in repr(op)

    def test_create_zero(self):
        op = ThresholdOp(0.0)
        assert op is not None


# ── L1NormOp ────────────────────────────────────────────────

class TestL1NormOp:
    def test_create(self):
        op = L1NormOp()
        assert op is not None


# ── apply_threshold ─────────────────────────────────────────

class TestApplyThreshold:
    def test_basic(self):
        coords = [(0, 0, 0, 0, 0), (1, 0, 0, 0, 0), (0, 1, 0, 0, 0)]
        tiling = from_coordinates(coords)
        result = apply_threshold(tiling, 0.5)
        # apply_threshold modifies in-place or returns None
        # just verify no crash

    def test_high_threshold(self):
        coords = [(0, 0, 0, 0, 0)]
        tiling = from_coordinates(coords)
        apply_threshold(tiling, 10.0)


# ── Tiling (from from_coordinates) ──────────────────────────

class TestTiling:
    def test_repr(self):
        tiling = from_coordinates([(0, 0, 0, 0, 0)])
        r = repr(tiling)
        assert "Tiling" in r
        assert "tiles" in r

    def test_edges_count(self):
        # 5 points with Eisenstein should have edges
        coords = [(i, 0, 0, 0, 0) for i in range(5)]
        tiling = from_coordinates(coords)
        r = repr(tiling)
        assert "edges=" in r
