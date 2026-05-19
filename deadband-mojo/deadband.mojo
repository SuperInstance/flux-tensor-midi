# Deadband Framework — Mojo Implementation
# Eisenstein lattice, HPDF sampling, /360 arithmetic, BMA detection,
# Shell decomposition, Fibonacci-spline search.
# Uses Mojo SIMD types, @always_inline, and struct generics.

import random
from math import sqrt, pi, abs, round, mod
from runtime.llcl import num_cores

# ─── Constants ────────────────────────────────────────────────────────

alias PHI: Float64 = 1.6180339887498948482
alias PHI_INV: Float64 = -0.6180339887498948482
alias SQRT3: Float64 = 1.7320508075688772935
alias TAU: Float64 = 2.0 * pi
alias EPS: Float64 = 1.0e-12


# ─── Eisenstein Snap ─────────────────────────────────────────────────

@always_inline
fn eisenstein_snap(x: Float64, y: Float64) -> tuple[Int64, Int64]:
    """Snap a 2D point to the nearest Eisenstein lattice point.
    Basis: (1, 0) and (0.5, sqrt(3)/2).
    """
    var l_exact: Float64 = y / SQRT3
    var k_exact: Float64 = x - 0.5 * l_exact
    var k: Int64 = Int64(round(k_exact))
    var l: Int64 = Int64(round(l_exact))
    return (k, l)


@always_inline
fn eisenstein_snap_coords(x: Float64, y: Float64) -> tuple[Float64, Float64]:
    """Snap and return the actual coordinates of the lattice point."""
    var (k, l) = eisenstein_snap(x, y)
    var kf: Float64 = Float64(k)
    var lf: Float64 = Float64(l)
    var rx: Float64 = kf + 0.5 * lf
    var ry: Float64 = SQRT3 * lf
    return (rx, ry)


@always_inline
fn eisenstein_norm(k: Int64, l: Int64) -> Float64:
    """Compute Eisenstein norm (distance from lattice origin)."""
    var kf: Float64 = Float64(k)
    var lf: Float64 = Float64(l)
    var rx: Float64 = kf + 0.5 * lf
    var ry: Float64 = SQRT3 * lf
    return sqrt(rx * rx + ry * ry)


# ─── SIMD Eisenstein Snap ────────────────────────────────────────────

@always_inline
fn eisenstein_snap_simd(xs: SIMD[DType.float64, 4], ys: SIMD[DType.float64, 4]) ->
    tuple[SIMD[DType.float64, 4], SIMD[DType.float64, 4]]:
    """Snap 4 points simultaneously using Mojo's SIMD type."""
    var half: SIMD[DType.float64, 4] = 0.5
    var sqrt3: SIMD[DType.float64, 4] = SQRT3

    var l_exact: SIMD[DType.float64, 4] = ys / sqrt3
    var k_exact: SIMD[DType.float64, 4] = xs - half * l_exact

    # Round to nearest integer (Mojo doesn't have vectorized round easily,
    # so we do floor(x + 0.5) trick for positive, but for correctness:
    var k: SIMD[DType.float64, 4] = round(k_exact)
    var l: SIMD[DType.float64, 4] = round(l_exact)

    var rx: SIMD[DType.float64, 4] = k + half * l
    var ry: SIMD[DType.float64, 4] = sqrt3 * l
    return (rx, ry)


# ─── HPDF Sampling ───────────────────────────────────────────────────

fn hpdf_sample(index: Int, total: Int, jitter: Float64) -> Float64:
    """Half-Periodic Distribution Function sample using golden-ratio stratification."""
    var golden_strat: Float64 = PHI - 1.0  # ~0.618
    var strat: Float64 = Float64(index) * golden_strat
    var base: Float64 = mod(strat, 1.0)
    var n: Float64 = Float64(max(total, 1))
    return mod(base + jitter / n, 1.0)


fn hpdf_fill(count: Int, seed: Int) -> List[Float64]:
    """Generate HPDF samples."""
    var buf: List[Float64] = List[Float64](capacity=count)
    var rng = random.rand(seed)
    for i in range(count):
        var jitter: Float64 = rng.float64()
        buf.append(hpdf_sample(i, count, jitter))
    return buf


# ─── Modular360 Arithmetic ──────────────────────────────────────────

struct Modular360:
    var value: Float64

    fn __init__(inout self, v: Float64):
        self.value = self._normalize(v)

    @always_inline
    fn _normalize(v: Float64) -> Float64:
        var n: Float64 = mod(v, 360.0)
        if n < 0.0:
            n = n + 360.0
        return n

    fn add(self, other: Modular360) -> Modular360:
        return Modular360(self.value + other.value)

    fn sub(self, other: Modular360) -> Modular360:
        var d: Float64 = self.value - other.value
        return Modular360(d)

    fn distance(self, other: Modular360) -> Float64:
        var diff: Float64 = abs(self.value - other.value)
        return min(diff, 360.0 - diff)


# ─── BMA (Berlekamp-Massey) Detector ─────────────────────────────────

fn bma_binary(seq: List[Bool]) -> Int:
    """Simplified Berlekamp-Massey for binary sequences.
    Returns the linear complexity (LFSR length).
    """
    var n: Int = len(seq)
    if n == 0:
        return 0

    var l: Int = 0
    var m: Int = 1

    # Track connection polynomial as a list of tap positions
    var c: List[Int] = List[Int](capacity=n + 1)
    c.append(0)

    var b: List[Int] = List[Int](capacity=n + 1)
    b.append(0)

    for i in range(n):
        # Compute discrepancy
        var d: Bool = seq[i]
        for j_idx in range(len(c)):
            var j: Int = c[j_idx]
            if j > 0 and j <= i:
                d = d ^ seq[i - j]

        if not d:
            m += 1
        else:
            var temp: List[Int] = List[Int](capacity=len(b))
            for item in b:
                temp.append(item)

            # XOR: toggle membership of j+m in C for each j in B
            for j in b:
                var idx: Int = j + m
                if idx <= i + 1:
                    var found: Bool = False
                    var found_idx: Int = -1
                    for ci in range(len(c)):
                        if c[ci] == idx:
                            found = True
                            found_idx = ci
                            break
                    if found:
                        c.pop(found_idx)
                    else:
                        c.append(idx)

            if 2 * l <= i:
                l = i + 1 - l
                b = temp
                m = 1
            else:
                m += 1

    return l


# ─── Shell Decomposer ────────────────────────────────────────────────

struct ShellEntry:
    var k: Int64
    var l: Int64
    var norm: Float64
    var shell_index: Int

    fn __init__(inout self, k: Int64, l: Int64, norm: Float64):
        self.k = k
        self.l = l
        self.norm = norm
        self.shell_index = 0


struct ShellDecomposer:
    var entries: List[ShellEntry]
    var shell_count: Int

    fn __init__(inout self, points: List[tuple[Float64, Float64]]):
        self.entries = List[ShellEntry](capacity=len(points))
        self.shell_count = 0

        # Snap and compute norms
        for pt in points:
            var (k, l) = eisenstein_snap(pt[0], pt[1])
            var norm: Float64 = eisenstein_norm(k, l)
            self.entries.append(ShellEntry(k, l, norm))

        # Sort by norm (insertion sort)
        var n: Int = len(self.entries)
        for i in range(1, n):
            var key: ShellEntry = self.entries[i]
            var j: Int = i - 1
            while j >= 0 and self.entries[j].norm > key.norm:
                self.entries[j + 1] = self.entries[j]
                j -= 1
            self.entries[j + 1] = key

        # Assign shell indices
        var current_shell: Int = 0
        var prev_norm: Float64 = -1.0
        var tolerance: Float64 = 1.0e-9

        for i in range(len(self.entries)):
            if i == 0 or abs(self.entries[i].norm - prev_norm) > tolerance:
                current_shell += 1
                prev_norm = self.entries[i].norm
            self.entries[i].shell_index = current_shell

        self.shell_count = current_shell

    fn get_shell(self, shell_idx: Int) -> List[ShellEntry]:
        var result: List[ShellEntry] = List[ShellEntry]()
        for entry in self.entries:
            if entry.shell_index == shell_idx:
                result.append(entry)
        return result


# ─── Fibonacci-Spline Search ─────────────────────────────────────────

fn fibonacci_spline_search(
    objective: fn(Float64) -> Float64,
    lo: Float64,
    hi: Float64,
    tolerance: Float64
) -> Float64:
    """Golden-section search for the minimum of a 1D function."""
    var a: Float64 = lo
    var b: Float64 = hi
    var gr: Float64 = PHI

    var c: Float64 = b - (b - a) / gr
    var d: Float64 = a + (b - a) / gr

    var fc: Float64 = objective(c)
    var fd: Float64 = objective(d)

    var iterations: Int = 0
    var max_iter: Int = 100

    while abs(b - a) > tolerance and iterations < max_iter:
        if fc < fd:
            b = d
            d = c
            fd = fc
            c = b - (b - a) / gr
            fc = objective(c)
        else:
            a = c
            c = d
            fc = fd
            d = a + (b - a) / gr
            fd = objective(d)
        iterations += 1

    return (a + b) / 2.0
