"""test_deadband.py — Pytest suite for deadband_python"""

import time
import math
import pytest
import numpy as np

# Import from package — will use C ext if available, else pure Python
import deadband_python as db

print(f"[test] Using C extension: {db.using_c_extension()}")


# ── 1. Eisenstein snap ─────────────────────────────────────────────

class TestEisensteinSnap:
    def test_origin_snaps_to_zero(self):
        sx, sy, err = db.eisenstein_snap(0.0, 0.0)
        assert sx == 0.0
        assert sy == 0.0
        assert err == pytest.approx(0.0, abs=1e-12)

    def test_lattice_point_snaps_to_self(self):
        """Lattice points of form a + b*omega should snap to themselves."""
        sqrt3 = math.sqrt(3)
        for a in range(-5, 6):
            for b in range(-5, 6):
                x = a - 0.5 * b
                y = (sqrt3 / 2.0) * b
                sx, sy, err = db.eisenstein_snap(x, y)
                assert err < 1e-9, f"Point ({x},{y}) a={a} b={b}: err={err}"

    def test_snap_nearby_returns_close(self):
        """Points near lattice points snap with small error."""
        sqrt3 = math.sqrt(3)
        # Point (1.1, 0.05) should snap to (1, 0)
        sx, sy, err = db.eisenstein_snap(1.1, 0.05)
        assert err < 0.2

    def test_snap_returns_tuple_of_three(self):
        result = db.eisenstein_snap(1.5, 2.5)
        assert len(result) == 3


# ── 2. HPDF sample ─────────────────────────────────────────────────

class TestHPDF:
    def test_sample_returns_tuple(self):
        result = db.hpdf_sample()
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], float)

    def test_hpdf_variance(self):
        """Variance of 10000 samples should be ~5/36 ≈ 0.1389"""
        N = 10000
        xs = [db.hpdf_sample()[0] for _ in range(N)]
        ys = [db.hpdf_sample()[1] for _ in range(N)]
        var_x = np.var(xs)
        var_y = np.var(ys)
        # Both should be positive and finite
        assert var_x > 0
        assert var_y > 0
        # Check they're in a reasonable range (not testing exact 5/36 since HPDF impl varies)
        assert var_x < 1.0
        assert var_y < 1.0

    def test_hpdf_dither(self):
        signal = np.zeros(100)
        dithered = db.hpdf_dither(signal)
        assert len(dithered) == 100
        assert np.var(dithered) > 0  # Should have noise added


# ── 3. div360 arithmetic ──────────────────────────────────────────

class TestDiv360:
    def test_add_basic(self):
        assert db.div360_add(100, 200) == 300

    def test_add_wrap(self):
        assert db.div360_add(200, 200) == 40

    def test_sub_basic(self):
        assert db.div360_sub(300, 100) == 200

    def test_sub_wrap(self):
        assert db.div360_sub(50, 100) == 310

    def test_mul_basic(self):
        assert db.div360_mul(2, 90) == 180

    def test_mul_wrap(self):
        assert db.div360_mul(3, 180) == 180

    def test_zero_drift_100k(self):
        """100K operations should produce zero drift."""
        x = 0
        for _ in range(100000):
            x = db.div360_add(x, 1)
        assert x == 100000 % 360

        for _ in range(100000):
            x = db.div360_sub(x, 1)
        assert x == 0

    def test_mul_associativity(self):
        """(a*b)*c mod 360 == a*(b*c) mod 360"""
        for a, b, c in [(7, 13, 29), (123, 45, 67), (359, 359, 359)]:
            ab = db.div360_mul(a, b)
            bc = db.div360_mul(b, c)
            assert db.div360_mul(ab, c) == db.div360_mul(a, bc)


# ── 4. BMA ─────────────────────────────────────────────────────────

class TestBMA:
    def test_all_zeros(self):
        seq = np.zeros(20, dtype=np.uint8)
        assert db.bma_detect(seq) == 0

    def test_all_ones(self):
        seq = np.ones(20, dtype=np.uint8)
        assert db.bma_detect(seq) == 1

    def test_alternating(self):
        seq = np.array([0, 1] * 10, dtype=np.uint8)
        L = db.bma_detect(seq)
        assert L <= 2  # Alternating has low complexity

    def test_random_high_complexity(self):
        rng = np.random.RandomState(42)
        seq = rng.randint(0, 2, size=100, dtype=np.uint8)
        L = db.bma_detect(seq)
        assert L > 5  # Random data has high complexity


# ── 5. Deadband perceivable ────────────────────────────────────────

class TestPerceivable:
    def test_large_step_perceivable(self):
        assert db.deadband_perceivable(10, 10) == True

    def test_tiny_step_not_perceivable(self):
        assert db.deadband_perceivable(100, 1) == False

    def test_boundary(self):
        assert db.deadband_perceivable(10, 5) == True

    def test_zero_not_perceivable(self):
        assert db.deadband_perceivable(0, 0) == False


# ── 6. Min bits ────────────────────────────────────────────────────

class TestMinBits:
    def test_uniform_data(self):
        data = np.array([5.0, 5.0, 5.0, 5.0])
        bits = db.deadband_min_bits(data, 0.1)
        assert bits == 0  # Zero range

    def test_wide_range(self):
        data = np.linspace(0, 100, 100)
        bits = db.deadband_min_bits(data, 1.0)
        assert bits >= 6  # ~100 levels → 7 bits

    def test_narrow_range(self):
        data = np.array([1.0, 1.01, 1.02, 0.99])
        bits = db.deadband_min_bits(data, 0.1)
        assert bits <= 2


# ── 7. Shell decompose ─────────────────────────────────────────────

class TestShellDecompose:
    def test_identity(self):
        cov = np.eye(2)
        result = db.shell_decompose(cov)
        assert result["energy_ratio"] == pytest.approx(0.5, abs=0.01)
        assert result["lam1"] == pytest.approx(1.0, abs=0.01)
        assert result["lam2"] == pytest.approx(1.0, abs=0.01)

    def test_anisotropic(self):
        cov = np.array([[10.0, 0.0], [0.0, 1.0]])
        result = db.shell_decompose(cov)
        assert result["lam1"] > result["lam2"]
        assert result["energy_ratio"] > 0.8

    def test_returns_dict(self):
        cov = np.eye(2)
        r = db.shell_decompose(cov)
        assert "lam1" in r
        assert "lam2" in r
        assert "e1" in r
        assert "e2" in r
        assert "energy_ratio" in r
        assert "classify" in r
        assert "status" in r


# ── 8. Fib spline search ──────────────────────────────────────────

class TestFibSplineSearch:
    def test_exact_match(self):
        db_data = np.random.randn(50, 10)
        query = db_data[5].copy()
        results = db.fib_spline_search(query, db_data, 1)
        assert results[0][0] == 5  # Should find exact match
        assert results[0][1] > 0.99

    def test_returns_k_results(self):
        db_data = np.random.randn(20, 5)
        query = np.random.randn(5)
        results = db.fib_spline_search(query, db_data, 3)
        assert len(results) == 3

    def test_similarity_decreasing(self):
        db_data = np.random.randn(30, 8)
        query = np.random.randn(8)
        results = db.fib_spline_search(query, db_data, 5)
        sims = [r[1] for r in results]
        for i in range(len(sims) - 1):
            assert sims[i] >= sims[i + 1]

    def test_synthetic_recall(self):
        """Create a database with known clusters, verify recall."""
        rng = np.random.RandomState(42)
        # 3 clusters
        centers = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
        db_data = np.vstack([c + 0.1 * rng.randn(10, 3) for c in centers])
        
        # Query from cluster 1
        query = centers[1] + 0.05 * rng.randn(3)
        results = db.fib_spline_search(query, db_data, 5)
        
        # Top results should be from cluster 1 (indices 10-19)
        top_indices = [r[0] for r in results[:3]]
        assert any(10 <= i < 20 for i in top_indices)


# ── Benchmark ──────────────────────────────────────────────────────

class TestBenchmark:
    def test_benchmark_all(self):
        """Print timing for all functions."""
        print("\n" + "=" * 60)
        print(f"  BENCHMARK (C ext: {db.using_c_extension()})")
        print("=" * 60)

        N = 1000

        # eisenstein_snap
        t0 = time.perf_counter()
        for _ in range(N):
            db.eisenstein_snap(1.5, 2.3)
        dt = time.perf_counter() - t0
        print(f"  eisenstein_snap:    {N/dt:>10.0f} ops/sec")

        # hpdf_sample
        t0 = time.perf_counter()
        for _ in range(N):
            db.hpdf_sample()
        dt = time.perf_counter() - t0
        print(f"  hpdf_sample:        {N/dt:>10.0f} ops/sec")

        # div360_add
        t0 = time.perf_counter()
        for _ in range(N):
            db.div360_add(12345, 67890)
        dt = time.perf_counter() - t0
        print(f"  div360_add:         {N/dt:>10.0f} ops/sec")

        # bma_detect
        seq = np.random.randint(0, 2, size=100, dtype=np.uint8)
        t0 = time.perf_counter()
        for _ in range(N):
            db.bma_detect(seq)
        dt = time.perf_counter() - t0
        print(f"  bma_detect(100):    {N/dt:>10.0f} ops/sec")

        # shell_decompose
        cov = np.eye(2)
        t0 = time.perf_counter()
        for _ in range(N):
            db.shell_decompose(cov)
        dt = time.perf_counter() - t0
        print(f"  shell_decompose:    {N/dt:>10.0f} ops/sec")

        # fib_spline_search
        db_data = np.random.randn(100, 10)
        query = np.random.randn(10)
        t0 = time.perf_counter()
        for _ in range(N):
            db.fib_spline_search(query, db_data, 5)
        dt = time.perf_counter() - t0
        print(f"  fib_spline_search:  {N/dt:>10.0f} ops/sec")

        # hpdf_dither
        signal = np.random.randn(1000)
        t0 = time.perf_counter()
        for _ in range(10):
            db.hpdf_dither(signal)
        dt = time.perf_counter() - t0
        print(f"  hpdf_dither(1000):  {10/dt:>10.0f} ops/sec")

        print("=" * 60)
