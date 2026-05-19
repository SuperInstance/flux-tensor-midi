# Deadband Framework — Mojo Test & Benchmark
# Tests all primitives and benchmarks them.
# Mojo should be 100x+ faster than pure Python on these operations.

import sys
from deadband import (
    eisenstein_snap, eisenstein_snap_coords, eisenstein_norm,
    eisenstein_snap_simd, hpdf_sample, hpdf_fill,
    Modular360, bma_binary, ShellDecomposer, ShellEntry,
    fibonacci_spline_search, PHI, PHI_INV, SQRT3, EPS
)
from math import sqrt, abs
from runtime.llcl import num_cores
from memory import UnsafePointer
from sys import nanosleep


# ─── Timing Utility ──────────────────────────────────────────────────

fn benchmark_ns(label: StringRef, iterations: Int, fn_to_bench: fn() -> None):
    """Run a function N times and print average ns/op."""
    var start: Int = sys.now()
    for _ in range(iterations):
        fn_to_bench()
    var elapsed_ns: Int = sys.now() - start
    var ns_per: Int = elapsed_ns / iterations
    print("  ", label, "  ", ns_per, " ns/op  (", iterations, " iterations)")


# ─── Tests ────────────────────────────────────────────────────────────

fn test_eisenstein_snap():
    print("\n=== Eisenstein Snap Tests ===")

    # Snap (1, 0) -> (1, 0)
    var (k, l) = eisenstein_snap(1.0, 0.0)
    assert(k == 1, "snap(1,0) k should be 1")
    assert(l == 0, "snap(1,0) l should be 0")

    # Snap (0.5, sqrt3/2) -> (0, 1)
    var (k2, l2) = eisenstein_snap(0.5, SQRT3 / 2.0)
    assert(k2 == 0, "snap(0.5, sqrt3/2) k should be 0")
    assert(l2 == 1, "snap(0.5, sqrt3/2) l should be 1")

    # Near origin
    var (k3, l3) = eisenstein_snap(0.1, 0.1)
    assert(k3 == 0, "snap(0.1,0.1) k should be 0")
    assert(l3 == 0, "snap(0.1,0.1) l should be 0")

    print("  All Eisenstein snap tests passed!")


fn test_eisenstein_norm():
    print("\n=== Eisenstein Norm Tests ===")

    var n0: Float64 = eisenstein_norm(0, 0)
    assert(abs(n0 - 0.0) < EPS, "norm(0,0) should be 0")

    var n1: Float64 = eisenstein_norm(1, 0)
    assert(abs(n1 - 1.0) < EPS, "norm(1,0) should be 1")

    print("  All Eisenstein norm tests passed!")


fn test_modular360():
    print("\n=== Modular360 Tests ===")

    var a: Modular360 = Modular360(30.0)
    var b: Modular360 = Modular360(350.0)
    assert(abs(a.value - 30.0) < EPS, "a should be 30")
    assert(abs(b.value - 350.0) < EPS, "b should be 350")

    var sum: Modular360 = a.add(b)
    assert(abs(sum.value - 20.0) < EPS, "30+350 mod 360 = 20")

    var dist: Float64 = a.distance(b)
    assert(abs(dist - 40.0) < EPS, "dist(30, 350) = 40")

    # Negative normalization
    var neg: Modular360 = Modular360(-45.0)
    assert(abs(neg.value - 315.0) < EPS, "-45 mod 360 = 315")

    print("  All Modular360 tests passed!")


fn test_hpdf():
    print("\n=== HPDF Tests ===")

    var samples: List[Float64] = hpdf_fill(50, 123)
    assert(len(samples) == 50, "Should have 50 samples")
    for s in samples:
        assert(s >= 0.0, "Sample should be >= 0")
        assert(s < 1.0, "Sample should be < 1")

    print("  All HPDF tests passed!")


fn test_bma():
    print("\n=== BMA Binary Tests ===")

    # LFSR: s_i = s_{i-1} XOR s_{i-3}
    var seq: List[Bool] = List[Bool](capacity=10)
    seq.append(True)
    seq.append(False)
    seq.append(False)
    seq.append(True)
    seq.append(False)
    seq.append(False)
    seq.append(True)
    seq.append(False)
    seq.append(False)
    seq.append(True)

    var lc: Int = bma_binary(seq)
    assert(lc == 3, "Linear complexity should be 3")

    # All zeros
    var zeros: List[Bool] = List[Bool](capacity=5)
    for _ in range(5):
        zeros.append(False)
    var lc0: Int = bma_binary(zeros)
    assert(lc0 == 0, "Linear complexity of all zeros should be 0")

    print("  All BMA tests passed!")


fn test_shell_decomposer():
    print("\n=== Shell Decomposer Tests ===")

    var points: List[tuple[Float64, Float64]] = List[tuple[Float64, Float64]](capacity=6)
    points.append((0.0, 0.0))
    points.append((1.0, 0.0))
    points.append((0.5, SQRT3 / 2.0))
    points.append((2.0, 0.0))
    points.append((1.0, SQRT3))
    points.append((0.1, 0.1))

    var sd: ShellDecomposer = ShellDecomposer(points)
    assert(sd.shell_count >= 2, "Should have at least 2 shells")

    var shell1: List[ShellEntry] = sd.get_shell(1)
    assert(len(shell1) >= 1, "Shell 1 should have at least 1 entry")

    print("  Shell count:", sd.shell_count)
    print("  All Shell decomposer tests passed!")


fn test_fibonacci_spline():
    print("\n=== Fibonacci-Spline Search Tests ===")

    fn parabola(x: Float64) -> Float64:
        var d: Float64 = x - 2.5
        return d * d

    var result: Float64 = fibonacci_spline_search(parabola, 0.0, 10.0, 1.0e-10)
    assert(abs(result - 2.5) < 1.0e-8, "Minimum should be at 2.5")

    print("  Found minimum at:", result)
    print("  All Fibonacci-spline tests passed!")


# ─── Benchmarks ──────────────────────────────────────────────────────

fn bench_eisenstein_snap():
    print("\n=== Eisenstein Snap Benchmarks ===")
    let N: Int = 1_000_000

    benchmark_ns("snap(1.0, 0.0)", N, fn(): Void =
        var _ = eisenstein_snap(1.0, 0.0)
    )

    benchmark_ns("snap(2.7, 1.5)", N, fn(): Void =
        var _ = eisenstein_snap(2.7, 1.5)
    )

    benchmark_ns("snap_coords(3.14, 2.71)", N, fn(): Void =
        var _ = eisenstein_snap_coords(3.14, 2.71)
    )


fn bench_modular360():
    print("\n=== Modular360 Benchmarks ===")
    let N: Int = 1_000_000

    benchmark_ns("init(45.0)", N, fn(): Void =
        var _ = Modular360(45.0)
    )

    benchmark_ns("add(30, 350)", N, fn(): Void =
        var a: Modular360 = Modular360(30.0)
        var b: Modular360 = Modular360(350.0)
        var _ = a.add(b)
    )

    benchmark_ns("distance(30, 350)", N, fn(): Void =
        var a: Modular360 = Modular360(30.0)
        var b: Modular360 = Modular360(350.0)
        var _ = a.distance(b)
    )


fn bench_simd():
    print("\n=== SIMD Eisenstein Snap ===")
    let N: Int = 1_000_000

    benchmark_ns("snap_simd(4 points)", N, fn(): Void =
        var xs: SIMD[DType.float64, 4] = SIMD[DType.float64, 4](1.0, 0.5, 2.3, 0.1)
        var ys: SIMD[DType.float64, 4] = SIMD[DType.float64, 4](0.0, SQRT3/2.0, 1.1, 0.1)
        var _ = eisenstein_snap_simd(xs, ys)
    )


# ─── Main ─────────────────────────────────────────────────────────────

fn main():
    print("\n⚒️  Deadband Framework — Mojo Tests & Benchmarks")
    print("=" * 50)

    # Run tests
    test_eisenstein_snap()
    test_eisenstein_norm()
    test_modular360()
    test_hpdf()
    test_bma()
    test_shell_decomposer()
    test_fibonacci_spline()

    print("\n" + "=" * 50)
    print("ALL TESTS PASSED ✓")

    # Run benchmarks
    print("\n" + "=" * 50)
    print("BENCHMARKS (ReleaseFast)")
    print("=" * 50)

    bench_eisenstein_snap()
    bench_modular360()
    bench_simd()

    print("\n" + "=" * 50)
    print("Done. All primitives tested and benchmarked.")
