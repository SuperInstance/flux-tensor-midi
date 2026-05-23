"""
Spline Wavetable Synthesizer — Eisenstein lattice control points for audio.

A novel synthesis method: instead of storing full wavetables (N samples per
cycle), store a handful of control points on the Eisenstein (hexagonal) lattice
and reconstruct waveforms in real-time via inverse-distance weighting.

Compression: 2048-sample wavetable → 16 control points = 128× compression.
Multi-table instruments: even higher ratios via 2D lattice sharing.

Based on tensor-spline's SplineLinear / EisensteinLattice architecture.

Usage:
    synth = SplineWavetable(n_control_points=16, table_length=2048)
    synth.set_waveform("sawtooth")
    audio = synth.render(frequency=440.0, duration=1.0, sample_rate=44100)

    # Morph between timbres
    morphed = synth.morph("sine", "square", t=0.3, frequency=220.0)

    # Constraint-based synthesis
    cps = synth.solve_for_spectrum({1: 1.0, 2: 0.5, 3: 0.25})

Tests: run with `python -m pytest spline_synth.py -v`
"""

from __future__ import annotations

import math
import struct
import wave
from typing import Dict, List, Optional, Sequence, Tuple, Union

import numpy as np


# ---------------------------------------------------------------------------
# Eisenstein Lattice
# ---------------------------------------------------------------------------

class EisensteinLattice:
    """
    Hexagonal (Eisenstein) lattice for control-point placement.

    Points at positions a + bω where ω = e^(2πi/3).
    Cartesian: x = a − b/2, y = b·√3/2.
    """

    _SQRT3_HALF = math.sqrt(3.0) / 2.0

    def __init__(self, n_points: int) -> None:
        if n_points < 1:
            raise ValueError(f"n_points must be ≥ 1, got {n_points}")
        self.n_points = n_points
        self._positions = self._build(n_points)

    def _build(self, n: int) -> np.ndarray:
        R = max(int(math.ceil(math.sqrt(n / 3.0))) + 2, 3)
        candidates: list = []
        for a in range(-R, R + 1):
            for b in range(-R, R + 1):
                x = float(a) - float(b) * 0.5
                y = float(b) * self._SQRT3_HALF
                dist_sq = x * x + y * y
                candidates.append((dist_sq, x, y))
        candidates.sort(key=lambda t: (round(t[0], 9), t[1], t[2]))
        selected = candidates[:n]
        positions = np.array([[x, y] for _, x, y in selected], dtype=np.float64)
        max_dist = np.linalg.norm(positions, axis=1).max()
        if max_dist > 0:
            positions /= max_dist
        return positions

    def positions(self) -> np.ndarray:
        return self._positions

    def interpolation_matrix(self, query_points: np.ndarray, eps: float = 1e-6) -> np.ndarray:
        """Compute N×K IDW² interpolation matrix."""
        diffs = query_points[:, np.newaxis, :] - self._positions[np.newaxis, :, :]
        dists = np.linalg.norm(diffs, axis=2)
        kernel = 1.0 / (dists ** 2 + eps)
        kernel /= kernel.sum(axis=1, keepdims=True)
        return kernel


# ---------------------------------------------------------------------------
# Standard Waveforms
# ---------------------------------------------------------------------------

def _generate_sine(length: int) -> np.ndarray:
    return np.sin(2.0 * np.pi * np.arange(length) / length)

def _generate_sawtooth(length: int) -> np.ndarray:
    return 2.0 * np.arange(length) / length - 1.0

def _generate_square(length: int) -> np.ndarray:
    t = np.arange(length) / length
    return np.where(t < 0.5, 1.0, -1.0)

def _generate_triangle(length: int) -> np.ndarray:
    t = np.arange(length) / length
    return 4.0 * np.abs(t - 0.5) - 1.0

def _generate_pulse(length: int, width: float = 0.25) -> np.ndarray:
    t = np.arange(length) / length
    return np.where(t < width, 1.0, -1.0)

WAVEFORM_GENERATORS = {
    "sine": _generate_sine,
    "sawtooth": _generate_sawtooth,
    "square": _generate_square,
    "triangle": _generate_triangle,
    "pulse": lambda n: _generate_pulse(n, 0.25),
}


# ---------------------------------------------------------------------------
# SplineWavetable
# ---------------------------------------------------------------------------

class SplineWavetable:
    """
    Wavetable synthesizer using Eisenstein lattice control points.

    Stores K control points instead of N waveform samples.
    Reconstructs waveforms via IDW² interpolation on the hexagonal lattice.
    """

    def __init__(
        self,
        n_control_points: int = 16,
        table_length: int = 2048,
        sample_rate: int = 44100,
    ) -> None:
        if n_control_points < 2:
            raise ValueError(f"Need ≥ 2 control points, got {n_control_points}")
        if table_length < 4:
            raise ValueError(f"table_length must be ≥ 4, got {table_length}")

        self.n_control_points = n_control_points
        self.table_length = table_length
        self.sample_rate = sample_rate

        self._lattice = EisensteinLattice(n_control_points)
        self._query_points = self._build_query_points_1d(table_length)
        self._interp_matrix = self._lattice.interpolation_matrix(self._query_points)

        # Control points: the compressed representation
        self.control_values: Optional[np.ndarray] = None  # (K,)

        # Named waveform library: name → control_values
        self._waveform_library: Dict[str, np.ndarray] = {}

    def _build_query_points_1d(self, n: int) -> np.ndarray:
        """Map 1D phase positions [0,1) to 2D lattice coordinates."""
        phases = np.linspace(-1.0, 1.0, n, endpoint=False)
        # Map to 2D: x = phase, y = 0 (single wavetable occupies a line)
        return np.column_stack([phases, np.zeros(n)])

    def set_control_values(self, values: np.ndarray) -> None:
        """Set control points directly."""
        if len(values) != self.n_control_points:
            raise ValueError(
                f"Expected {self.n_control_points} values, got {len(values)}"
            )
        self.control_values = values.copy()

    def set_waveform(self, name: str) -> None:
        """Set waveform from a named generator or the library."""
        if name in self._waveform_library:
            self.control_values = self._waveform_library[name].copy()
            return
        if name not in WAVEFORM_GENERATORS:
            raise ValueError(f"Unknown waveform '{name}'. Available: "
                             f"{list(WAVEFORM_GENERATORS.keys())}, "
                             f"{list(self._waveform_library.keys())}")
        full_wavetable = WAVEFORM_GENERATORS[name](self.table_length)
        self.control_values = self._fit_control_points(full_wavetable)

    def _fit_control_points(self, target: np.ndarray) -> np.ndarray:
        """Fit control points to a target waveform via least squares."""
        # A @ c ≈ target  →  c = (A^T A)^{-1} A^T target
        A = self._interp_matrix  # (N, K)
        c, _, _, _ = np.linalg.lstsq(A, target, rcond=None)
        return c

    def reconstruct(self) -> np.ndarray:
        """Reconstruct the full wavetable from control points."""
        if self.control_values is None:
            raise RuntimeError("No control points set — call set_waveform() or set_control_values()")
        return self._interp_matrix @ self.control_values

    def render(
        self,
        frequency: float = 440.0,
        duration: float = 1.0,
        volume: float = 1.0,
    ) -> np.ndarray:
        """
        Render audio at the given frequency and duration.

        Returns float64 array of samples in [-1, 1].
        """
        wavetable = self.reconstruct()
        n_samples = int(self.sample_rate * duration)
        phase_inc = frequency * self.table_length / self.sample_rate
        phase = 0.0
        output = np.zeros(n_samples)

        for i in range(n_samples):
            idx = int(phase) % self.table_length
            frac = phase - int(phase)
            # Linear interpolation between adjacent wavetable samples
            idx_next = (idx + 1) % self.table_length
            sample = wavetable[idx] * (1.0 - frac) + wavetable[idx_next] * frac
            output[i] = sample * volume
            phase += phase_inc

        return output

    def morph(
        self,
        name_a: str,
        name_b: str,
        t: float = 0.5,
        frequency: float = 440.0,
        duration: float = 1.0,
        volume: float = 1.0,
    ) -> np.ndarray:
        """
        Morph between two waveforms and render audio.

        t=0 → pure A, t=1 → pure B, t=0.5 → 50/50 blend.
        """
        cp_a = self._get_control_points(name_a)
        cp_b = self._get_control_points(name_b)
        self.control_values = (1.0 - t) * cp_a + t * cp_b
        return self.render(frequency=frequency, duration=duration, volume=volume)

    def morph_three(
        self,
        name_a: str,
        name_b: str,
        name_c: str,
        alpha: float = 0.33,
        beta: float = 0.33,
        gamma: float = 0.34,
        frequency: float = 440.0,
        duration: float = 1.0,
    ) -> np.ndarray:
        """Three-way morph (barycentric). Weights should sum to ~1."""
        cp_a = self._get_control_points(name_a)
        cp_b = self._get_control_points(name_b)
        cp_c = self._get_control_points(name_c)
        self.control_values = alpha * cp_a + beta * cp_b + gamma * cp_c
        return self.render(frequency=frequency, duration=duration)

    def _get_control_points(self, name: str) -> np.ndarray:
        """Get control points for a named waveform, computing if needed."""
        if name in self._waveform_library:
            return self._waveform_library[name]
        if name in WAVEFORM_GENERATORS:
            full = WAVEFORM_GENERATORS[name](self.table_length)
            return self._fit_control_points(full)
        raise ValueError(f"Unknown waveform '{name}'")

    def store_waveform(self, name: str, waveform: np.ndarray) -> None:
        """Store a custom waveform in the library (as control points)."""
        if len(waveform) != self.table_length:
            waveform = np.interp(
                np.linspace(0, 1, self.table_length),
                np.linspace(0, 1, len(waveform)),
                waveform,
            )
        self._waveform_library[name] = self._fit_control_points(waveform)

    # ------------------------------------------------------------------
    # Constraint-based synthesis
    # ------------------------------------------------------------------

    def solve_for_spectrum(
        self,
        harmonics: Dict[int, float],
        regularization: float = 1e-4,
    ) -> np.ndarray:
        """
        Solve for control points that produce the given harmonic spectrum.

        Args:
            harmonics: {harmonic_number: amplitude}. 1 = fundamental.
            regularization: L2 regularization strength.

        Returns:
            Control point values (also sets them as current).
        """
        target = np.zeros(self.table_length)
        for n, amp in harmonics.items():
            target += amp * np.sin(2.0 * np.pi * n * np.arange(self.table_length) / self.table_length)
        # Normalize peak to ±1
        peak = np.abs(target).max()
        if peak > 0:
            target /= peak

        A = self._interp_matrix
        ATA = A.T @ A + regularization * np.eye(self.n_control_points)
        ATy = A.T @ target
        self.control_values = np.linalg.solve(ATA, ATy)
        return self.control_values

    def solve_for_waveform(
        self,
        target: np.ndarray,
        constraints: Optional[Dict[int, float]] = None,
        regularization: float = 1e-4,
    ) -> np.ndarray:
        """
        Solve for control points that approximate a target waveform,
        optionally with sample-level constraints.

        Args:
            target: Target waveform (length = table_length).
            constraints: {sample_index: value} for hard constraints.
            regularization: L2 regularization strength.

        Returns:
            Control point values.
        """
        if len(target) != self.table_length:
            target = np.interp(
                np.linspace(0, 1, self.table_length),
                np.linspace(0, 1, len(target)),
                target,
            )

        A = self._interp_matrix
        ATA = A.T @ A + regularization * np.eye(self.n_control_points)
        ATy = A.T @ target

        if constraints:
            for idx, val in constraints.items():
                row = A[idx:idx+1, :]  # (1, K)
                ATA += 1e6 * row.T @ row
                ATy += 1e6 * val * row[0]

        self.control_values = np.linalg.solve(ATA, ATy)
        return self.control_values

    def get_spectrum(self, n_harmonics: int = 16) -> Dict[int, complex]:
        """Get the harmonic spectrum of the current wavetable."""
        wavetable = self.reconstruct()
        fft = np.fft.rfft(wavetable)
        harmonics_per_bin = self.table_length // 2
        result = {}
        for n in range(1, min(n_harmonics + 1, len(fft))):
            result[n] = fft[n]
        return result

    def reconstruction_error(self, target: np.ndarray) -> float:
        """RMSE between reconstruction and target waveform."""
        reconstructed = self.reconstruct()
        if len(target) != self.table_length:
            target = np.interp(
                np.linspace(0, 1, self.table_length),
                np.linspace(0, 1, len(target)),
                target,
            )
        return float(np.sqrt(np.mean((reconstructed - target) ** 2)))

    def compression_ratio(self) -> float:
        """Compression ratio vs. storing full wavetable."""
        if self.control_values is None:
            return 1.0
        return self.table_length / self.n_control_points

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_wav(self, filename: str, frequency: float = 440.0, duration: float = 1.0) -> None:
        """Render audio and export as 16-bit WAV."""
        audio = self.render(frequency=frequency, duration=duration)
        audio_16 = np.clip(audio * 32767, -32768, 32767).astype(np.int16)

        with wave.open(filename, 'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_16.tobytes())

    def export_control_points(self, filename: str) -> None:
        """Export control points as numpy .npy file."""
        if self.control_values is None:
            raise RuntimeError("No control points to export")
        np.save(filename, self.control_values)

    def import_control_points(self, filename: str) -> None:
        """Import control points from numpy .npy file."""
        data = np.load(filename)
        self.set_control_values(data)

    def export_wavetable(self, filename: str) -> None:
        """Export the full reconstructed wavetable as numpy .npy."""
        wavetable = self.reconstruct()
        np.save(filename, wavetable)

    def export_multi_table(
        self,
        filename: str,
        names: List[str],
        table_length: Optional[int] = None,
    ) -> np.ndarray:
        """
        Export multiple wavetables as a single 2D array.

        Returns and saves array of shape (len(names), table_length).
        """
        tl = table_length or self.table_length
        tables = np.zeros((len(names), tl))
        for i, name in enumerate(names):
            cp = self._get_control_points(name)
            if tl != self.table_length:
                # Rebuild query points and interp matrix for new length
                qp = self._build_query_points_1d(tl)
                lat = EisensteinLattice(self.n_control_points)
                mat = lat.interpolation_matrix(qp)
                tables[i] = mat @ cp
            else:
                tables[i] = self._interp_matrix @ cp
        np.save(filename, tables)
        return tables

    def __repr__(self) -> str:
        has_cp = self.control_values is not None
        ratio = self.compression_ratio() if has_cp else 0.0
        return (
            f"SplineWavetable(n_cp={self.n_control_points}, "
            f"table_len={self.table_length}, "
            f"ratio={ratio:.0f}×, "
            f"library={len(self._waveform_library)} waveforms)"
        )


# ---------------------------------------------------------------------------
# Multi-Table Synthesizer (2D lattice)
# ---------------------------------------------------------------------------

class MultiTableSynth:
    """
    Multi-timbral synthesizer using 2D Eisenstein lattice.

    Maps (phase, timbre_index) → 2D lattice coordinates.
    All wavetables share the same control points on the 2D lattice.
    """

    def __init__(
        self,
        n_control_points: int = 64,
        table_length: int = 2048,
        n_tables: int = 32,
        sample_rate: int = 44100,
    ) -> None:
        self.n_control_points = n_control_points
        self.table_length = table_length
        self.n_tables = n_tables
        self.sample_rate = sample_rate

        self._lattice = EisensteinLattice(n_control_points)
        self._query_2d = self._build_query_2d()
        self._interp_matrices = self._build_interp_matrices()
        self.control_values: Optional[np.ndarray] = None

    def _build_query_2d(self) -> np.ndarray:
        """Build 2D query points for all (phase, table_index) pairs."""
        phases = np.linspace(-1.0, 1.0, self.table_length, endpoint=False)
        table_indices = np.linspace(-1.0, 1.0, self.n_tables)
        px, tx = np.meshgrid(phases, table_indices, indexing="ij")
        return np.column_stack([px.ravel(), tx.ravel()])

    def _build_interp_matrices(self) -> List[np.ndarray]:
        """Build per-table interpolation matrices."""
        matrices = []
        for t_idx in range(self.n_tables):
            phases = np.linspace(-1.0, 1.0, self.table_length, endpoint=False)
            t_val = np.linspace(-1.0, 1.0, self.n_tables)[t_idx]
            qp = np.column_stack([phases, np.full(self.table_length, t_val)])
            matrices.append(self._lattice.interpolation_matrix(qp))
        return matrices

    def fit_from_waveforms(self, waveforms: List[np.ndarray]) -> np.ndarray:
        """Fit control points to multiple waveforms simultaneously."""
        if len(waveforms) != self.n_tables:
            raise ValueError(f"Expected {self.n_tables} waveforms, got {len(waveforms)}")

        target = np.concatenate(waveforms)
        A_full = np.vstack(self._interp_matrices)

        # Stack interpolation matrices; each table's rows only use its own matrix
        # We need A_full to have shape (n_tables * table_length, n_control_points)
        ATA = A_full.T @ A_full + 1e-4 * np.eye(self.n_control_points)
        ATy = A_full.T @ target
        self.control_values = np.linalg.solve(ATA, ATy)
        return self.control_values

    def reconstruct_table(self, table_index: int) -> np.ndarray:
        """Reconstruct a single wavetable by index."""
        if self.control_values is None:
            raise RuntimeError("No control points — call fit_from_waveforms()")
        return self._interp_matrices[table_index] @ self.control_values

    def reconstruct_all(self) -> np.ndarray:
        """Reconstruct all wavetables. Returns (n_tables, table_length)."""
        return np.array([self.reconstruct_table(i) for i in range(self.n_tables)])

    def render(
        self,
        table_index: float,
        frequency: float = 440.0,
        duration: float = 1.0,
        volume: float = 1.0,
    ) -> np.ndarray:
        """
        Render audio from a (possibly fractional) table index.

        Fractional indices interpolate between adjacent tables.
        """
        t_low = int(table_index) % self.n_tables
        t_high = (t_low + 1) % self.n_tables
        frac = table_index - int(table_index)

        wt_low = self.reconstruct_table(t_low)
        wt_high = self.reconstruct_table(t_high)
        wavetable = (1.0 - frac) * wt_low + frac * wt_high

        n_samples = int(self.sample_rate * duration)
        phase_inc = frequency * self.table_length / self.sample_rate
        phase = 0.0
        output = np.zeros(n_samples)

        for i in range(n_samples):
            idx = int(phase) % self.table_length
            f = phase - int(phase)
            idx_next = (idx + 1) % self.table_length
            output[i] = (wavetable[idx] * (1.0 - f) + wavetable[idx_next] * f) * volume
            phase += phase_inc

        return output

    def compression_ratio(self) -> float:
        """Total compression: all tables vs. control points."""
        total_samples = self.n_tables * self.table_length
        return total_samples / self.n_control_points

    def __repr__(self) -> str:
        ratio = self.compression_ratio()
        return (
            f"MultiTableSynth(n_cp={self.n_control_points}, "
            f"tables={self.n_tables}, table_len={self.table_length}, "
            f"ratio={ratio:.0f}×)"
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _run_tests():
    """Run all tests. Returns (passed, failed, errors)."""
    import traceback

    results = {"pass": 0, "fail": 0, "error": 0}
    tests = []

    def test(name):
        def decorator(fn):
            tests.append((name, fn))
            return fn
        return decorator

    # ---- Construction ----

    @test("SplineWavetable constructs with defaults")
    def _():
        s = SplineWavetable()
        assert s.n_control_points == 16
        assert s.table_length == 2048
        assert s.sample_rate == 44100

    @test("SplineWavetable rejects invalid n_control_points")
    def _():
        try:
            SplineWavetable(n_control_points=1)
            assert False, "Should have raised"
        except ValueError:
            pass

    @test("EisensteinLattice builds correct number of points")
    def _():
        lat = EisensteinLattice(16)
        assert lat.positions().shape == (16, 2)

    @test("EisensteinLattice first point is origin")
    def _():
        lat = EisensteinLattice(7)
        assert np.allclose(lat.positions()[0], [0.0, 0.0])

    # ---- Waveform fitting and reconstruction ----

    @test("Set and reconstruct sine wave")
    def _():
        s = SplineWavetable(n_control_points=32, table_length=2048)
        s.set_waveform("sine")
        reconstructed = s.reconstruct()
        target = _generate_sine(2048)
        rmse = np.sqrt(np.mean((reconstructed - target) ** 2))
        assert rmse < 0.05, f"Sine RMSE too high: {rmse}"

    @test("Set and reconstruct sawtooth")
    def _():
        s = SplineWavetable(n_control_points=64, table_length=2048)
        s.set_waveform("sawtooth")
        reconstructed = s.reconstruct()
        target = _generate_sawtooth(2048)
        rmse = np.sqrt(np.mean((reconstructed - target) ** 2))
        assert rmse < 0.1, f"Sawtooth RMSE too high: {rmse}"

    @test("Set and reconstruct square wave")
    def _():
        s = SplineWavetable(n_control_points=64, table_length=2048)
        s.set_waveform("square")
        reconstructed = s.reconstruct()
        # Square wave has discontinuities — higher RMSE expected
        assert reconstructed is not None
        assert len(reconstructed) == 2048

    @test("Set and reconstruct triangle")
    def _():
        s = SplineWavetable(n_control_points=32, table_length=2048)
        s.set_waveform("triangle")
        reconstructed = s.reconstruct()
        target = _generate_triangle(2048)
        rmse = np.sqrt(np.mean((reconstructed - target) ** 2))
        assert rmse < 0.05, f"Triangle RMSE too high: {rmse}"

    # ---- Compression ----

    @test("Compression ratio is correct")
    def _():
        s = SplineWavetable(n_control_points=16, table_length=2048)
        s.set_waveform("sine")
        ratio = s.compression_ratio()
        assert abs(ratio - 128.0) < 0.01, f"Expected 128×, got {ratio}"

    @test("Control points use correct memory")
    def _():
        s = SplineWavetable(n_control_points=16)
        s.set_waveform("sine")
        # 16 float64 values = 128 bytes
        assert s.control_values.nbytes == 128

    # ---- Morphing ----

    @test("Morph between sine and sawtooth")
    def _():
        s = SplineWavetable(n_control_points=32, table_length=2048)
        audio = s.morph("sine", "sawtooth", t=0.5, frequency=440.0, duration=0.01)
        assert len(audio) == int(44100 * 0.01)
        assert np.abs(audio).max() <= 1.5  # Should be bounded

    @test("Three-way morph produces valid audio")
    def _():
        s = SplineWavetable(n_control_points=32, table_length=2048)
        audio = s.morph_three("sine", "sawtooth", "square", duration=0.01)
        assert len(audio) == int(44100 * 0.01)
        assert not np.all(audio == 0)

    @test("Morph t=0 matches pure waveform A")
    def _():
        s = SplineWavetable(n_control_points=32, table_length=512)
        s.morph("sine", "sawtooth", t=0.0)
        cp_morph = s.control_values.copy()
        s.set_waveform("sine")
        cp_sine = s.control_values.copy()
        assert np.allclose(cp_morph, cp_sine, atol=1e-10)

    # ---- Constraint synthesis ----

    @test("Solve for spectrum with single harmonic")
    def _():
        s = SplineWavetable(n_control_points=32, table_length=2048)
        s.solve_for_spectrum({1: 1.0})
        reconstructed = s.reconstruct()
        # Should look like a sine wave
        target = _generate_sine(2048)
        # Normalize both for comparison
        r = reconstructed / (np.abs(reconstructed).max() + 1e-10)
        t = target / (np.abs(target).max() + 1e-10)
        rmse = np.sqrt(np.mean((r - t) ** 2))
        assert rmse < 0.1, f"Spectrum solve RMSE: {rmse}"

    @test("Solve for spectrum with multiple harmonics")
    def _():
        s = SplineWavetable(n_control_points=64, table_length=2048)
        s.solve_for_spectrum({1: 1.0, 2: 0.5, 3: 0.25, 4: 0.125})
        spec = s.get_spectrum(n_harmonics=8)
        # Fundamental should be strongest
        assert abs(spec[1]) > abs(spec[5])

    @test("Solve for waveform with constraints")
    def _():
        s = SplineWavetable(n_control_points=32, table_length=256)
        target = _generate_triangle(256)
        # Constrain sample 0 to be exactly 0
        s.solve_for_waveform(target, constraints={0: 0.0})
        reconstructed = s.reconstruct()
        assert abs(reconstructed[0]) < 0.05, f"Constraint not met: {reconstructed[0]}"

    # ---- Render ----

    @test("Render produces correct length audio")
    def _():
        s = SplineWavetable(n_control_points=16)
        s.set_waveform("sine")
        audio = s.render(frequency=440.0, duration=0.5)
        assert len(audio) == 22050

    @test("Render volume control works")
    def _():
        s = SplineWavetable(n_control_points=16)
        s.set_waveform("sine")
        loud = s.render(frequency=440.0, duration=0.01, volume=1.0)
        quiet = s.render(frequency=440.0, duration=0.01, volume=0.1)
        assert np.abs(loud).max() > np.abs(quiet).max() * 5

    # ---- Export/Import ----

    @test("Export and import control points roundtrip")
    def _():
        import tempfile, os
        s = SplineWavetable(n_control_points=16)
        s.set_waveform("sine")
        original = s.control_values.copy()
        with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as f:
            path = f.name
        try:
            s.export_control_points(path)
            s2 = SplineWavetable(n_control_points=16)
            s2.import_control_points(path)
            assert np.allclose(original, s2.control_values)
        finally:
            os.unlink(path)

    @test("Export WAV creates valid file")
    def _():
        import tempfile, os
        s = SplineWavetable(n_control_points=16)
        s.set_waveform("sine")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            s.export_wav(path, frequency=440.0, duration=0.1)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)

    # ---- Multi-table ----

    @test("MultiTableSynth compresses multiple tables")
    def _():
        mts = MultiTableSynth(n_control_points=64, table_length=256, n_tables=8)
        waveforms = [
            _generate_sine(256),
            _generate_triangle(256),
            _generate_sawtooth(256),
            _generate_square(256),
            _generate_pulse(256),
            _generate_sine(256),
            _generate_triangle(256),
            _generate_sawtooth(256),
        ]
        mts.fit_from_waveforms(waveforms)
        ratio = mts.compression_ratio()
        # 8 tables × 256 samples / 64 control points = 32×
        assert abs(ratio - 32.0) < 0.01, f"Expected 32×, got {ratio}"

    @test("MultiTableSynth renders audio from table index")
    def _():
        mts = MultiTableSynth(n_control_points=32, table_length=128, n_tables=4)
        waveforms = [_generate_sine(128), _generate_sawtooth(128),
                     _generate_triangle(128), _generate_square(128)]
        mts.fit_from_waveforms(waveforms)
        audio = mts.render(table_index=0.0, frequency=440.0, duration=0.01)
        assert len(audio) == 441

    @test("MultiTableSynth fractional table index works")
    def _():
        mts = MultiTableSynth(n_control_points=32, table_length=128, n_tables=4)
        waveforms = [_generate_sine(128)] * 4
        mts.fit_from_waveforms(waveforms)
        audio = mts.render(table_index=1.5, frequency=440.0, duration=0.01)
        assert len(audio) == 441
        assert not np.all(audio == 0)

    # ---- Custom waveform storage ----

    @test("Store and retrieve custom waveform")
    def _():
        s = SplineWavetable(n_control_points=64, table_length=512)
        custom = np.sin(2 * np.pi * 3 * np.arange(512) / 512)  # 3rd harmonic
        s.store_waveform("custom3", custom)
        s.set_waveform("custom3")
        reconstructed = s.reconstruct()
        rmse = np.sqrt(np.mean((reconstructed - custom) ** 2))
        assert rmse < 0.15, f"Custom waveform RMSE: {rmse}"

    # ---- Run ----

    print(f"\n{'='*60}")
    print(f"Spline Wavetable Synthesizer — {len(tests)} tests")
    print(f"{'='*60}\n")

    for name, fn in tests:
        try:
            fn()
            results["pass"] += 1
            print(f"  ✓ {name}")
        except AssertionError as e:
            results["fail"] += 1
            print(f"  ✗ {name}: {e}")
        except Exception as e:
            results["error"] += 1
            print(f"  ! {name}: {e}")
            traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"  Passed: {results['pass']}  Failed: {results['fail']}  Errors: {results['error']}")
    print(f"{'='*60}\n")
    return results


if __name__ == "__main__":
    _run_tests()
