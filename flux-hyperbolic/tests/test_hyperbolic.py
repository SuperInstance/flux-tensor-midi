"""Tests for flux_hyperbolic — Poincaré ball hyperbolic geometry."""

import sys, os, math
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flux_hyperbolic.ball import PoincareBall
from flux_hyperbolic.gyro import mobius_add, mobius_multiply, gyro_distance
from flux_hyperbolic.constraint import (
    HyperbolicConstraint, HyperbolicCheckResult, HierarchicalConstraintSystem,
)


# ── PoincareBall construction ───────────────────────────────

class TestPoincareBall:
    def test_basic_construction(self):
        ball = PoincareBall(dimension=3, curvature=1.0)
        assert ball.dimension == 3
        assert ball.c == 1.0

    def test_invalid_dimension(self):
        with pytest.raises(ValueError):
            PoincareBall(dimension=0)

    def test_invalid_curvature(self):
        with pytest.raises(ValueError):
            PoincareBall(curvature=0)

    def test_origin(self):
        ball = PoincareBall(dimension=3)
        o = ball.origin()
        assert o.shape == (3,)
        assert np.allclose(o, 0)

    def test_project_inside(self):
        ball = PoincareBall(dimension=2)
        x = np.array([0.1, 0.2])
        p = ball.project(x)
        assert np.allclose(p, x)  # already inside

    def test_project_outside(self):
        ball = PoincareBall(dimension=2)
        x = np.array([10.0, 10.0])
        p = ball.project(x)
        assert np.linalg.norm(p) < 1.0

    def test_random_point_inside_ball(self):
        ball = PoincareBall(dimension=3)
        rng = np.random.default_rng(42)
        for _ in range(20):
            p = ball.random_point(rng=rng)
            assert np.linalg.norm(p) < 1.0


# ── PoincareBall distance ───────────────────────────────────

class TestPoincareBallDistance:
    def test_distance_to_self_is_zero(self):
        ball = PoincareBall(dimension=3)
        x = np.array([0.1, 0.2, 0.3])
        d = ball.distance(x, x)
        assert d < 1e-10

    def test_distance_symmetry(self):
        ball = PoincareBall(dimension=3)
        x = np.array([0.1, 0.2, 0.3])
        y = np.array([0.2, 0.1, 0.4])
        assert abs(ball.distance(x, y) - ball.distance(y, x)) < 1e-10

    def test_distance_positive(self):
        ball = PoincareBall(dimension=2)
        d = ball.distance(np.array([0.1, 0.1]), np.array([0.2, 0.2]))
        assert d > 0

    def test_origin_distance(self):
        ball = PoincareBall(dimension=2)
        d = ball.distance(ball.origin(), np.array([0.5, 0.0]))
        assert d > 0


# ── PoincareBall conformal factor ───────────────────────────

class TestConformalFactor:
    def test_at_origin(self):
        ball = PoincareBall(dimension=2)
        lam = ball.conformal_factor(ball.origin())
        assert abs(lam - 2.0) < 1e-10

    def test_increases_toward_boundary(self):
        ball = PoincareBall(dimension=2)
        lam_near = ball.conformal_factor(np.array([0.1, 0.0]))
        lam_far = ball.conformal_factor(np.array([0.8, 0.0]))
        assert lam_far > lam_near


# ── PoincareBall exponential/logarithmic maps ───────────────

class TestExpLogMap:
    def test_exp_log_roundtrip(self):
        ball = PoincareBall(dimension=3)
        base = np.array([0.1, 0.2, 0.3])
        v = np.array([0.01, 0.02, 0.01])
        p = ball.exp_map(v, base)
        v2 = ball.log_map(p, base)
        assert np.allclose(v, v2, atol=1e-6)

    def test_exp_map_at_origin(self):
        ball = PoincareBall(dimension=2)
        v = np.array([0.1, 0.0])
        p = ball.exp_map(v)
        assert np.linalg.norm(p) > 0
        assert np.linalg.norm(p) < 1.0


# ── Möbius addition ─────────────────────────────────────────

class TestMobiusAdd:
    def test_add_with_zero(self):
        x = np.array([0.3, 0.2])
        z = mobius_add(x, np.zeros(2))
        assert np.allclose(x, z, atol=1e-10)

    def test_non_commutative(self):
        x = np.array([0.3, 0.2])
        y = np.array([0.1, 0.4])
        xy = mobius_add(x, y)
        yx = mobius_add(y, x)
        assert not np.allclose(xy, yx)

    def test_result_inside_ball(self):
        x = np.array([0.5, 0.4])
        y = np.array([0.3, 0.3])
        r = mobius_add(x, y)
        assert np.linalg.norm(r) < 1.0


# ── Möbius multiply ─────────────────────────────────────────

class TestMobiusMultiply:
    def test_zero_scalar(self):
        x = np.array([0.3, 0.2])
        r = mobius_multiply(0, x)
        assert np.allclose(r, 0)

    def test_identity_scalar(self):
        x = np.array([0.3, 0.2])
        r = mobius_multiply(1, x)
        assert np.allclose(r, x, atol=1e-10)

    def test_result_inside_ball(self):
        x = np.array([0.5, 0.4])
        r = mobius_multiply(3, x)
        assert np.linalg.norm(r) < 1.0


# ── Gyro distance ───────────────────────────────────────────

class TestGyroDistance:
    def test_same_point_zero(self):
        x = np.array([0.2, 0.1])
        d = gyro_distance(x, x)
        assert d < 1e-10

    def test_positive_distance(self):
        x = np.array([0.1, 0.2])
        y = np.array([0.3, 0.1])
        d = gyro_distance(x, y)
        assert d > 0


# ── HyperbolicConstraint ────────────────────────────────────

class TestHyperbolicConstraint:
    def test_point_inside(self):
        ball = PoincareBall(dimension=2)
        hc = HyperbolicConstraint(ball, center=np.array([0.1, 0.1]), radius=2.0)
        r = hc.check(np.array([0.1, 0.1]))
        assert r.inside
        assert r.margin > 0

    def test_point_outside(self):
        ball = PoincareBall(dimension=2)
        hc = HyperbolicConstraint(ball, center=np.array([0.0, 0.0]), radius=0.1)
        r = hc.check(np.array([0.8, 0.8]))
        assert not r.inside

    def test_batch_check(self):
        ball = PoincareBall(dimension=2)
        hc = HyperbolicConstraint(ball, center=np.array([0.0, 0.0]), radius=1.0)
        points = np.array([[0.1, 0.1], [0.9, 0.9]])
        results = hc.check_batch(points)
        assert len(results) == 2
        assert results[0].inside
        assert not results[1].inside

    def test_to_dict(self):
        ball = PoincareBall(dimension=2)
        hc = HyperbolicConstraint(ball, center=np.array([0.0, 0.0]), radius=1.0)
        r = hc.check(np.array([0.1, 0.1]))
        d = r.to_dict()
        assert "inside" in d
        assert "margin" in d


# ── HierarchicalConstraintSystem ────────────────────────────

class TestHierarchicalSystem:
    def test_satisfies_all_levels(self):
        ball = PoincareBall(dimension=2)
        sys = HierarchicalConstraintSystem(ball)
        sys.add_constraint(0, HyperbolicConstraint(ball, center=np.array([0.0, 0.0]), radius=5.0))
        sys.add_constraint(1, HyperbolicConstraint(ball, center=np.array([0.0, 0.0]), radius=3.0))
        r = sys.check(np.array([0.1, 0.1]))
        assert r["satisfied"]

    def test_fails_at_deep_level(self):
        ball = PoincareBall(dimension=2)
        sys = HierarchicalConstraintSystem(ball)
        sys.add_constraint(0, HyperbolicConstraint(ball, center=np.array([0.0, 0.0]), radius=5.0))
        sys.add_constraint(1, HyperbolicConstraint(ball, center=np.array([0.0, 0.0]), radius=0.01))
        r = sys.check(np.array([0.5, 0.5]))
        assert not r["satisfied"]
        assert r["per_level"][0]  # passes level 0
        assert not r["per_level"][1]  # fails level 1
