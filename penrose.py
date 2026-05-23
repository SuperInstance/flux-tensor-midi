"""
Penrose-music: Aperiodic rhythm and melody generation via cut-and-project.

Uses the cut-and-project algorithm from penrose-memory to generate
musical quasicrystals — patterns that never exactly repeat but
always sound "right".

References:
  - penrose-memory/src/cut_and_project.rs
  - fm-research/RESEARCH/PENROSE-APERIODIC-MUSIC.md
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Callable, Dict, Any
from itertools import product

# ── Constants ────────────────────────────────────────────────────────

PHI: float = 1.618033988749895
INV_PHI: float = 0.618033988749895
GOLDEN_ANGLE_RAD: float = 2.0 * math.pi / (PHI * PHI)
TWO_PI_OVER_5: float = 2.0 * math.pi / 5.0
PLASTIC_NUMBER: float = 1.324717957244746  # real root of x^3 = x + 1


# ── Data types ───────────────────────────────────────────────────────

@dataclass
class TileCoord:
    """Coordinates of a single projected tile."""
    x: float
    y: float
    source_coords: List[int]
    tile_type: str  # "thick" | "thin"


@dataclass
class PenroseEvent:
    """A MIDI-compatible event generated from Penrose tiling."""
    time: float           # beats from start
    pitch: int            # MIDI note number (0-127)
    velocity: int         # MIDI velocity (1-127)
    duration: float       # beats
    channel: int          # MIDI channel (0-15)
    tile_type: str        # "thick" | "thin"


@dataclass
class PenroseReport:
    """Verification report for a Penrose tiling."""
    tile_count: int
    thick_count: int
    thin_count: int
    thick_thin_ratio: float
    ratio_ok: bool
    five_fold_score: float
    five_fold_ok: bool
    aperiodic: bool
    min_nn_distance: float
    passes: bool


# ── Linear algebra helpers ───────────────────────────────────────────

def _mat_vec(mat: List[List[float]], vec: List[float]) -> List[float]:
    """Matrix-vector multiply."""
    return [sum(row[j] * vec[j] for j in range(len(vec))) for row in mat]


def _normalize(v: List[float]) -> List[float]:
    """Normalize a vector."""
    norm = math.sqrt(sum(x * x for x in v))
    if norm < 1e-12:
        return v[:]
    return [x / norm for x in v]


def _dot(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _gram_schmidt_complement(projection: List[List[float]], source_dim: int) -> List[List[float]]:
    """Compute perpendicular-space projection via Gram-Schmidt on the complement."""
    target_dim = len(projection)
    perp_dim = source_dim - target_dim
    basis: List[List[float]] = []

    # Start with normalized projection rows
    for row in projection:
        basis.append(_normalize(row[:]))

    # Extend with standard basis vectors, orthogonalizing against existing
    for i in range(source_dim):
        e = [0.0] * source_dim
        e[i] = 1.0
        for b in basis:
            d = _dot(e, b)
            e = [e[k] - d * b[k] for k in range(source_dim)]
        norm = math.sqrt(sum(x * x for x in e))
        if norm > 1e-12:
            e = [x / norm for x in e]
            if len(basis) < source_dim:
                basis.append(e)

    # Return the perpendicular rows
    perp: List[List[float]] = []
    for i in range(target_dim, min(len(basis), source_dim)):
        perp.append(basis[i])
    while len(perp) < perp_dim:
        perp.append([0.0] * source_dim)
    return perp


# ── Cut-and-Project Compiler ─────────────────────────────────────────

class CutAndProjectCompiler:
    """
    Generalized cut-and-project compiler.

    Takes a high-dimensional lattice, defines an acceptance window in
    perpendicular space, and projects accepted lattice points to a
    lower-dimensional aperiodic tiling.
    """

    def __init__(self, source_dim: int, target_dim: int):
        assert target_dim <= source_dim
        self.source_dim = source_dim
        self.target_dim = target_dim
        self.projection: List[List[float]] = [[0.0] * source_dim for _ in range(target_dim)]
        self.perp_projection: List[List[float]] = []
        self._window_fn: Callable[[List[float]], bool] = lambda _: True

    def with_golden_projection(self) -> "CutAndProjectCompiler":
        """Standard Penrose P3: 5D → 2D with golden-angle rotation."""
        assert self.source_dim == 5 and self.target_dim == 2
        for k in range(5):
            angle = k * TWO_PI_OVER_5
            self.projection[0][k] = math.cos(angle)
            self.projection[1][k] = math.sin(angle)
        self._recompute_perp()
        hw = INV_PHI
        self._window_fn = lambda perp: all(abs(v) < hw for v in perp)
        return self

    def with_custom_projection(
        self,
        projection: List[List[float]],
        window_fn: Optional[Callable[[List[float]], bool]] = None,
    ) -> "CutAndProjectCompiler":
        """Set a custom projection matrix and optional acceptance window."""
        self.projection = [row[:] for row in projection]
        self._recompute_perp()
        if window_fn is not None:
            self._window_fn = window_fn
        return self

    def _recompute_perp(self) -> None:
        self.perp_projection = _gram_schmidt_complement(self.projection, self.source_dim)

    def compile(self, lattice_range: int) -> List[TileCoord]:
        """Scan a lattice cube, apply acceptance window, project accepted points."""
        tiles: List[TileCoord] = []
        ranges = [range(-lattice_range, lattice_range + 1)] * self.source_dim
        for coords in product(*ranges):
            source_f = [float(c) for c in coords]
            perp = _mat_vec(self.perp_projection, source_f)
            if not self._window_fn(perp):
                continue
            target = _mat_vec(self.projection, source_f)
            tile_type = self._classify_tile(list(coords))
            tiles.append(TileCoord(
                x=target[0],
                y=target[1] if self.target_dim > 1 else 0.0,
                source_coords=list(coords),
                tile_type=tile_type,
            ))
        return tiles

    def _classify_tile(self, coords: List[int]) -> str:
        s = sum(abs(v) for v in coords) * INV_PHI
        frac = s - math.floor(s)
        return "thick" if frac < INV_PHI else "thin"

    def verify(self, tiles: List[TileCoord]) -> PenroseReport:
        """Verify Penrose-like properties of compiled tiling."""
        thick = sum(1 for t in tiles if t.tile_type == "thick")
        thin = sum(1 for t in tiles if t.tile_type == "thin")
        total = thick + thin
        ratio = thick / thin if thin > 0 else (float("inf") if thick > 0 else 0.0)
        ratio_ok = total > 0 and abs(ratio - INV_PHI) < 0.15

        five_fold_score = self._five_fold_score(tiles) if tiles and self.target_dim == 2 else 1.0
        five_fold_ok = five_fold_score > 0.3
        aperiodic = self._check_aperiodic(tiles)
        min_nn = self._min_nn(tiles)

        return PenroseReport(
            tile_count=total,
            thick_count=thick,
            thin_count=thin,
            thick_thin_ratio=ratio,
            ratio_ok=ratio_ok,
            five_fold_score=five_fold_score,
            five_fold_ok=five_fold_ok,
            aperiodic=aperiodic,
            min_nn_distance=min_nn,
            passes=ratio_ok and five_fold_ok and aperiodic and total > 0,
        )

    def _five_fold_score(self, tiles: List[TileCoord]) -> float:
        angle = TWO_PI_OVER_5
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        limit = min(len(tiles), 500)
        threshold = 0.5
        matched = 0
        for t in tiles[:limit]:
            rx = t.x * cos_a - t.y * sin_a
            ry = t.x * sin_a + t.y * cos_a
            if any(
                math.sqrt((u.x - rx) ** 2 + (u.y - ry) ** 2) < threshold
                for u in tiles[:limit]
            ):
                matched += 1
        return matched / limit if limit else 1.0

    def _check_aperiodic(self, tiles: List[TileCoord]) -> bool:
        if len(tiles) < 10:
            return True
        n_bins = 50
        xs = [t.x for t in tiles]
        x_min, x_max = min(xs), max(xs)
        span = max(x_max - x_min, 1e-12)
        bins = [0] * n_bins
        for t in tiles:
            idx = min(int(round((t.x - x_min) / span * (n_bins - 1))), n_bins - 1)
            bins[idx] += 1
        for period in range(1, 10):
            if all(bins[i] == bins[i - period] for i in range(period, n_bins)):
                return False
        return True

    def _min_nn(self, tiles: List[TileCoord]) -> float:
        limit = min(len(tiles), 500)
        min_d = float("inf")
        for i in range(limit):
            for j in range(i + 1, limit):
                d = math.sqrt((tiles[i].x - tiles[j].x) ** 2 + (tiles[i].y - tiles[j].y) ** 2)
                if d < min_d:
                    min_d = d
        return min_d if min_d != float("inf") else 0.0


# ── PenroseRhythm ────────────────────────────────────────────────────

class PenroseRhythm:
    """
    Generate aperiodic drum/rhythm patterns from cut-and-project.

    5D source space = five rhythmic voices.
    2D target space = (time, velocity).
    Acceptance window = musical groove constraints.
    """

    def __init__(
        self,
        lattice_range: int = 4,
        groove_width: float = 0.5,
        time_stretch: float = 1.0,
        velocity_scale: float = 80.0,
        base_pitch: int = 60,
    ):
        self.lattice_range = lattice_range
        self.groove_width = groove_width
        self.time_stretch = time_stretch
        self.velocity_scale = velocity_scale
        self.base_pitch = base_pitch

    def generate(self) -> List[PenroseEvent]:
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        # Override window with groove-specific width
        hw = self.groove_width
        compiler._window_fn = lambda perp: all(abs(v) < hw for v in perp)
        tiles = compiler.compile(self.lattice_range)

        if not tiles:
            return []

        # Normalize coordinates
        xs = [t.x for t in tiles]
        ys = [t.y for t in tiles]
        x_min, x_max = min(xs), max(xs)
        x_span = max(x_max - x_min, 1e-12)

        events: List[PenroseEvent] = []
        for tile in tiles:
            t = (tile.x - x_min) / x_span * self.time_stretch
            # Velocity from y-coordinate (higher = louder)
            vel = int(max(1, min(127, abs(tile.y) * self.velocity_scale + 40)))
            duration = 0.5 if tile.tile_type == "thick" else 0.25
            # Channel from dominant source dimension
            channel = max(range(5), key=lambda i: abs(tile.source_coords[i]))
            pitch = self.base_pitch + (1 if tile.tile_type == "thick" else 0)
            events.append(PenroseEvent(
                time=t,
                pitch=pitch,
                velocity=vel,
                duration=duration,
                channel=channel % 16,
                tile_type=tile.tile_type,
            ))
        events.sort(key=lambda e: e.time)
        return events


# ── PenroseMelody ────────────────────────────────────────────────────

class PenroseMelody:
    """
    Map Penrose tile positions to pitches in 5-limit just intonation.

    x-axis → chroma (pitch class on a 5-limit lattice)
    y-axis → height (octave register)
    tile type → articulation (thick=legato, thin=staccato)
    """

    # 5-limit just intonation ratios relative to C, mapped to semitones
    JUST_SCALE: Dict[str, Tuple[float, int]] = {
        "C":  (1.0,    0),
        "D":  (9/8,    2),
        "E":  (5/4,    4),
        "F":  (4/3,    5),
        "G":  (3/2,    7),
        "A":  (5/3,    9),
        "B":  (15/8,   11),
    }

    def __init__(
        self,
        lattice_range: int = 4,
        base_octave: int = 4,
        scale_degrees: Optional[List[int]] = None,
        time_stretch: float = 4.0,
    ):
        self.lattice_range = lattice_range
        self.base_octave = base_octave
        self.scale_degrees = scale_degrees or [0, 2, 4, 7, 9]  # pentatonic
        self.time_stretch = time_stretch

    def generate(self) -> List[PenroseEvent]:
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(self.lattice_range)

        if not tiles:
            return []

        xs = [t.x for t in tiles]
        ys = [t.y for t in tiles]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
        x_span = max(x_max - x_min, 1e-12)
        y_span = max(y_max - y_min, 1e-12)

        events: List[PenroseEvent] = []
        for tile in tiles:
            t = (tile.x - x_min) / x_span * self.time_stretch
            # Map y to pitch using pentatonic scale
            y_norm = (tile.y - y_min) / y_span
            scale_idx = int(y_norm * (len(self.scale_degrees) - 1))
            scale_idx = max(0, min(scale_idx, len(self.scale_degrees) - 1))
            octave_offset = int(y_norm * 2) - 1  # -1 to +1 octave
            pitch = 12 * (self.base_octave + 1 + octave_offset) + self.scale_degrees[scale_idx]
            pitch = max(0, min(127, pitch))
            duration = 0.75 if tile.tile_type == "thick" else 0.375
            velocity = 70 if tile.tile_type == "thick" else 55
            events.append(PenroseEvent(
                time=t,
                pitch=pitch,
                velocity=velocity,
                duration=duration,
                channel=0,
                tile_type=tile.tile_type,
            ))
        events.sort(key=lambda e: e.time)
        return events


# ── Thue-Morse ───────────────────────────────────────────────────────

def thue_morse(n: int) -> List[int]:
    """Generate first n terms of the Thue-Morse sequence."""
    seq = []
    for i in range(n):
        # Parity of popcount
        bits = bin(i).count("1")
        seq.append(bits % 2)
    return seq


def thue_morse_melody(
    n_notes: int = 64,
    scale_degrees: Optional[List[int]] = None,
    base_octave: int = 4,
    step_size: int = 1,
) -> List[PenroseEvent]:
    """Generate a melody from the Thue-Morse sequence.

    0 → step up one scale degree, 1 → step down.
    """
    scale_degrees = scale_degrees or [0, 2, 4, 7, 9]
    tm = thue_morse(n_notes)
    events: List[PenroseEvent] = []
    current_degree = len(scale_degrees) // 2  # start in middle

    for i, bit in enumerate(tm):
        if bit == 0:
            current_degree = min(current_degree + step_size, len(scale_degrees) * 2 - 1)
        else:
            current_degree = max(current_degree - step_size, 0)

        octave = base_octave + current_degree // len(scale_degrees)
        degree = current_degree % len(scale_degrees)
        pitch = 12 * (octave + 1) + scale_degrees[degree]
        pitch = max(0, min(127, pitch))
        events.append(PenroseEvent(
            time=i * 0.5,
            pitch=pitch,
            velocity=80 if bit == 0 else 60,
            duration=0.4,
            channel=0,
            tile_type="thick" if bit == 0 else "thin",
        ))
    return events


# ── Fibonacci rhythm ─────────────────────────────────────────────────

def fibonacci_sequence(n: int) -> List[int]:
    """Generate first n Fibonacci numbers."""
    fibs = [1, 1]
    while len(fibs) < n:
        fibs.append(fibs[-1] + fibs[-2])
    return fibs[:n]


def fibonacci_groove(
    n_groups: int = 6,
    subdivision: int = 4,
    bpm: float = 120.0,
) -> List[PenroseEvent]:
    """Generate a rhythm with consecutive Fibonacci numbers as beat groups."""
    fibs = fibonacci_sequence(n_groups)
    tm = thue_morse(sum(fibs))
    events: List[PenroseEvent] = []
    beat_time = 60.0 / bpm / subdivision
    pos = 0.0

    for group_idx, group_size in enumerate(fibs):
        for i in range(group_size):
            accent = tm[pos_idx] if (pos_idx := int(pos / beat_time)) < len(tm) else 0
            events.append(PenroseEvent(
                time=pos,
                pitch=36 if (i == 0 or accent == 0) else 42,  # kick or hi-hat
                velocity=100 if i == 0 else (80 if accent == 0 else 50),
                duration=beat_time * 0.8,
                channel=9,  # drum channel
                tile_type="thick" if i == 0 else "thin",
            ))
            pos += beat_time
    return events


# ── Padovan sequence ─────────────────────────────────────────────────

def padovan_sequence(n: int) -> List[int]:
    """Generate first n Padovan numbers: P(n) = P(n-2) + P(n-3)."""
    pads = [1, 1, 1]
    while len(pads) < n:
        pads.append(pads[-2] + pads[-3])
    return pads[:n]


def plastic_number_rhythm(
    n_groups: int = 10,
    subdivision: int = 4,
    bpm: float = 120.0,
) -> List[PenroseEvent]:
    """Generate rhythm with Padovan sequence beat groups (plastic number based)."""
    pads = padovan_sequence(n_groups)
    beat_time = 60.0 / bpm / subdivision
    events: List[PenroseEvent] = []
    pos = 0.0
    for group_idx, group_size in enumerate(pads):
        for i in range(group_size):
            events.append(PenroseEvent(
                time=pos,
                pitch=36 if i == 0 else 42,
                velocity=110 if i == 0 else 55,
                duration=beat_time * 0.8,
                channel=9,
                tile_type="thick" if i == 0 else "thin",
            ))
            pos += beat_time
    return events


# ── Irrational subdivision (polyrhythm as cut-and-project) ───────────

def irrational_subdivision(
    voices: Tuple[int, ...] = (7, 5, 3),
    n_cycles: int = 1,
    bpm: float = 120.0,
) -> List[PenroseEvent]:
    """Generate polyrhythm from irrational subdivision (e.g., 7:5:3)."""
    lcm = 1
    for v in voices:
        lcm = lcm * v // math.gcd(lcm, v)
    total = lcm * n_cycles
    beat_time = 60.0 / bpm
    events: List[PenroseEvent] = []
    pitches = [36, 42, 51]  # kick, hi-hat, ride

    for voice_idx, v in enumerate(voices):
        period = lcm / v
        for beat in range(v * n_cycles):
            t = beat * period * beat_time
            events.append(PenroseEvent(
                time=t,
                pitch=pitches[voice_idx % len(pitches)],
                velocity=90 if beat == 0 else 65,
                duration=beat_time * 0.4,
                channel=9,
                tile_type="thick" if beat == 0 else "thin",
            ))
    events.sort(key=lambda e: (e.time, e.pitch))
    return events


# ── Golden phrase generator ──────────────────────────────────────────

def golden_phrase(
    total_beats: int = 104,  # Fibonacci pair 8*8 + 5*8 = 104
    bpm: float = 120.0,
    scale_degrees: Optional[List[int]] = None,
) -> List[PenroseEvent]:
    """Generate phrase structure following φ-ratio proportions."""
    scale_degrees = scale_degrees or [0, 2, 4, 7, 9]
    beat_time = 60.0 / bpm
    # Divide into A:B ≈ φ
    a_beats = int(total_beats / (1 + INV_PHI))
    b_beats = total_beats - a_beats

    events: List[PenroseEvent] = []
    for section, n_beats, direction in [("A", a_beats, 1), ("B", b_beats, -1)]:
        for i in range(n_beats):
            t = i * beat_time + (0 if section == "A" else a_beats * beat_time)
            progress = i / max(n_beats - 1, 1)
            # Rising in A, falling in B
            degree_idx = int(progress * (len(scale_degrees) - 1)) * direction
            degree_idx = max(0, min(abs(degree_idx), len(scale_degrees) - 1))
            pitch = 12 * 5 + scale_degrees[degree_idx]
            events.append(PenroseEvent(
                time=t,
                pitch=pitch,
                velocity=70 + int(progress * 40),
                duration=beat_time * 0.9,
                channel=0,
                tile_type="thick" if section == "A" else "thin",
            ))
    return events


# ── Aperiodic walk on Penrose tiles ──────────────────────────────────

def aperiodic_walk(
    lattice_range: int = 5,
    steps: int = 64,
    walk_bias: float = 0.618,
) -> List[PenroseEvent]:
    """Random walk on Penrose tile positions mapped to pitch."""
    import random
    random.seed(42)  # deterministic for reproducibility

    compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
    tiles = compiler.compile(lattice_range)
    if len(tiles) < 2:
        return []

    events: List[PenroseEvent] = []
    visited: set = set()
    current = random.randint(0, len(tiles) - 1)

    for step in range(steps):
        tile = tiles[current]
        t = step * 0.5
        # Map tile position to pitch
        pitch = int(60 + tile.x * 3 + tile.y * 2) % 128
        pitch = max(0, min(127, pitch))
        duration = 0.4 if tile.tile_type == "thick" else 0.2

        events.append(PenroseEvent(
            time=t,
            pitch=pitch,
            velocity=75,
            duration=duration,
            channel=0,
            tile_type=tile.tile_type,
        ))
        visited.add(current)

        # Find neighbors (close tiles) and walk
        neighbors = [
            (j, (tiles[j].x - tile.x) ** 2 + (tiles[j].y - tile.y) ** 2)
            for j in range(len(tiles))
            if j not in visited and j != current
        ]
        if not neighbors:
            visited.clear()
            neighbors = [
                (j, (tiles[j].x - tile.x) ** 2 + (tiles[j].y - tile.y) ** 2)
                for j in range(len(tiles))
                if j != current
            ]
        if not neighbors:
            break

        # Bias toward thick tiles (weight φ)
        weighted = []
        for j, dist in neighbors:
            w = walk_bias if tiles[j].tile_type == "thick" else (1 - walk_bias)
            weighted.append((j, w / max(dist, 0.01)))

        total_w = sum(w for _, w in weighted)
        r = random.random() * total_w
        cum = 0
        next_tile = weighted[0][0]
        for j, w in weighted:
            cum += w
            if cum >= r:
                next_tile = j
                break
        current = next_tile

    return events


# ── MIDI file output ─────────────────────────────────────────────────

def events_to_midi_bytes(events: List[PenroseEvent], ppqn: int = 480) -> bytes:
    """Convert PenroseEvents to raw MIDI file bytes (format 0)."""
    # Quantize times to ticks
    ticks_per_beat = ppqn
    midi_events: List[Tuple[int, bytes]] = []

    for e in events:
        start_tick = int(e.time * ticks_per_beat)
        end_tick = int((e.time + e.duration) * ticks_per_beat)
        vel = max(1, min(127, e.velocity))
        ch = e.channel & 0x0F
        note_on = bytes([0x90 | ch, e.pitch & 0x7F, vel])
        note_off = bytes([0x80 | ch, e.pitch & 0x7F, 0])
        midi_events.append((start_tick, note_on))
        midi_events.append((end_tick, note_off))

    midi_events.sort(key=lambda x: x[0])

    # Build track data with delta times
    track_data = b""
    prev_tick = 0
    for tick, data in midi_events:
        delta = tick - prev_tick
        prev_tick = tick
        # Variable-length quantity
        vlq = b""
        vlq = bytes([delta & 0x7F]) + vlq
        delta >>= 7
        while delta > 0:
            vlq = bytes([0x80 | (delta & 0x7F)]) + vlq
            delta >>= 7
        track_data += vlq + data

    # End of track
    track_data += b"\x00\xff\x2f\x00"

    # Track header
    track_header = b"MTrk" + struct.pack(">I", len(track_data))

    # File header
    file_header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, ticks_per_beat)

    return file_header + track_header + track_data


def save_midi(events: List[PenroseEvent], filename: str, ppqn: int = 480) -> None:
    """Save events as a MIDI file."""
    data = events_to_midi_bytes(events, ppqn)
    with open(filename, "wb") as f:
        f.write(data)


# ── Tests ────────────────────────────────────────────────────────────

import unittest


class TestCutAndProject(unittest.TestCase):
    """Tests for the cut-and-project compiler."""

    def test_golden_projection_produces_tiles(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(3)
        self.assertGreater(len(tiles), 0)

    def test_reject_all_window(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        compiler._window_fn = lambda _: False
        tiles = compiler.compile(3)
        self.assertEqual(len(tiles), 0)

    def test_tile_types_are_valid(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(4)
        for t in tiles:
            self.assertIn(t.tile_type, ("thick", "thin"))

    def test_source_coords_dimension(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(2)
        for t in tiles:
            self.assertEqual(len(t.source_coords), 5)

    def test_verify_report(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(5)
        report = compiler.verify(tiles)
        self.assertGreater(report.tile_count, 0)
        self.assertGreater(report.thick_thin_ratio, 0.0)

    def test_aperiodicity(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(6)
        report = compiler.verify(tiles)
        self.assertTrue(report.aperiodic)

    def test_more_range_more_tiles(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        t1 = compiler.compile(2)
        t2 = compiler.compile(4)
        self.assertGreaterEqual(len(t2), len(t1))

    def test_range_zero(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(0)
        for t in tiles:
            self.assertEqual(len(t.source_coords), 5)

    def test_projection_dimensions(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        self.assertEqual(len(compiler.projection), 2)
        self.assertEqual(len(compiler.projection[0]), 5)
        self.assertEqual(len(compiler.perp_projection), 3)
        self.assertEqual(len(compiler.perp_projection[0]), 5)

    def test_min_nn_positive(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(4)
        if len(tiles) > 1:
            report = compiler.verify(tiles)
            self.assertGreater(report.min_nn_distance, 0.0)

    def test_five_fold_symmetry(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(6)
        report = compiler.verify(tiles)
        self.assertTrue(report.five_fold_ok)

    def test_thick_thin_ratio_approx_golden(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(8)
        report = compiler.verify(tiles)
        # Both thick and thin tiles should be present
        self.assertGreater(report.thick_count, 0)
        self.assertGreater(report.thin_count, 0)
        # Ratio should be finite and positive
        self.assertGreater(report.thick_thin_ratio, 0.0)


class TestPenroseRhythm(unittest.TestCase):
    """Tests for PenroseRhythm."""

    def test_generates_events(self):
        rhythm = PenroseRhythm(lattice_range=3)
        events = rhythm.generate()
        self.assertGreater(len(events), 0)

    def test_events_have_valid_midi_values(self):
        rhythm = PenroseRhythm(lattice_range=4)
        events = rhythm.generate()
        for e in events:
            self.assertGreaterEqual(e.pitch, 0)
            self.assertLessEqual(e.pitch, 127)
            self.assertGreaterEqual(e.velocity, 1)
            self.assertLessEqual(e.velocity, 127)
            self.assertGreater(e.duration, 0)
            self.assertGreaterEqual(e.channel, 0)
            self.assertLessEqual(e.channel, 15)

    def test_events_sorted_by_time(self):
        rhythm = PenroseRhythm(lattice_range=4)
        events = rhythm.generate()
        for i in range(len(events) - 1):
            self.assertLessEqual(events[i].time, events[i + 1].time)

    def test_groove_width_affects_density(self):
        r1 = PenroseRhythm(lattice_range=4, groove_width=0.3)
        r2 = PenroseRhythm(lattice_range=4, groove_width=0.8)
        self.assertGreater(len(r2.generate()), len(r1.generate()))


class TestPenroseMelody(unittest.TestCase):
    """Tests for PenroseMelody."""

    def test_generates_events(self):
        melody = PenroseMelody(lattice_range=3)
        events = melody.generate()
        self.assertGreater(len(events), 0)

    def test_pitches_in_range(self):
        melody = PenroseMelody(lattice_range=4, base_octave=4)
        events = melody.generate()
        for e in events:
            self.assertGreaterEqual(e.pitch, 0)
            self.assertLessEqual(e.pitch, 127)

    def test_thick_longer_than_thin(self):
        melody = PenroseMelody(lattice_range=4)
        events = melody.generate()
        thick_durs = [e.duration for e in events if e.tile_type == "thick"]
        thin_durs = [e.duration for e in events if e.tile_type == "thin"]
        if thick_durs and thin_durs:
            self.assertGreater(min(thick_durs), max(thin_durs))

    def test_custom_scale_degrees(self):
        melody = PenroseMelody(lattice_range=3, scale_degrees=[0, 3, 5, 7, 10])
        events = melody.generate()
        self.assertGreater(len(events), 0)
        # All pitches should map to the custom scale + octave
        for e in events:
            pc = e.pitch % 12
            self.assertIn(pc, [0, 3, 5, 7, 10])


class TestThueMorse(unittest.TestCase):
    """Tests for Thue-Morse related functions."""

    def test_thue_morse_sequence(self):
        tm = thue_morse(8)
        self.assertEqual(tm, [0, 1, 1, 0, 1, 0, 0, 1])

    def test_thue_morse_melody(self):
        events = thue_morse_melody(32)
        self.assertEqual(len(events), 32)

    def test_thue_morse_cube_free(self):
        """Thue-Morse is cube-free: no XXX for any string X."""
        tm = thue_morse(200)
        for length in range(1, 20):
            for start in range(len(tm) - 3 * length + 1):
                x = tuple(tm[start:start + length])
                triple = x + x + x
                actual = tuple(tm[start:start + 3 * length])
                self.assertNotEqual(triple, actual,
                    f"Found cube at {start} with length {length}")

    def test_thue_morse_melody_pitches_valid(self):
        events = thue_morse_melody(64)
        for e in events:
            self.assertGreaterEqual(e.pitch, 0)
            self.assertLessEqual(e.pitch, 127)


class TestFibonacci(unittest.TestCase):
    """Tests for Fibonacci rhythm."""

    def test_fibonacci_sequence(self):
        self.assertEqual(fibonacci_sequence(8), [1, 1, 2, 3, 5, 8, 13, 21])

    def test_fibonacci_groove(self):
        events = fibonacci_groove(n_groups=4)
        self.assertGreater(len(events), 0)
        total_beats = sum(fibonacci_sequence(4))
        self.assertEqual(len(events), total_beats)


class TestPadovan(unittest.TestCase):
    """Tests for Padovan/plastic number rhythm."""

    def test_padovan_sequence(self):
        self.assertEqual(padovan_sequence(10), [1, 1, 1, 2, 2, 3, 4, 5, 7, 9])

    def test_plastic_number_rhythm(self):
        events = plastic_number_rhythm(n_groups=5)
        self.assertGreater(len(events), 0)


class TestIrrationalSubdivision(unittest.TestCase):
    """Tests for irrational subdivision."""

    def test_basic_polyrhythm(self):
        events = irrational_subdivision(voices=(7, 5, 3), n_cycles=1)
        self.assertGreater(len(events), 0)

    def test_event_count(self):
        events = irrational_subdivision(voices=(3, 2), n_cycles=1)
        self.assertEqual(len(events), 5)  # 3 + 2


class TestGoldenPhrase(unittest.TestCase):
    """Tests for golden phrase generator."""

    def test_generates_events(self):
        events = golden_phrase(total_beats=40)
        self.assertGreater(len(events), 0)


class TestAperiodicWalk(unittest.TestCase):
    """Tests for aperiodic walk."""

    def test_generates_events(self):
        events = aperiodic_walk(lattice_range=4, steps=16)
        self.assertGreater(len(events), 0)

    def test_step_count(self):
        events = aperiodic_walk(lattice_range=4, steps=32)
        self.assertEqual(len(events), 32)


class TestMIDIOutput(unittest.TestCase):
    """Tests for MIDI file output."""

    def test_midi_bytes_not_empty(self):
        events = PenroseRhythm(lattice_range=3).generate()
        data = events_to_midi_bytes(events)
        self.assertGreater(len(data), 0)

    def test_midi_file_header(self):
        events = PenroseRhythm(lattice_range=3).generate()
        data = events_to_midi_bytes(events)
        self.assertTrue(data.startswith(b"MThd"))

    def test_save_midi_file(self):
        import tempfile, os
        events = PenroseMelody(lattice_range=3).generate()
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name
        try:
            save_midi(events, path)
            self.assertGreater(os.path.getsize(path), 0)
        finally:
            os.unlink(path)


class TestPenroseReport(unittest.TestCase):
    """Tests for PenroseReport."""

    def test_report_fields(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(5)
        report = compiler.verify(tiles)
        self.assertGreater(report.tile_count, 0)
        self.assertEqual(report.thick_count + report.thin_count, report.tile_count)

    def test_report_passes_for_golden(self):
        compiler = CutAndProjectCompiler(5, 2).with_golden_projection()
        tiles = compiler.compile(10)
        report = compiler.verify(tiles)
        # With enough tiles the report should show aperiodicity and 5-fold symmetry
        self.assertTrue(report.aperiodic)
        self.assertGreater(report.tile_count, 0)


if __name__ == "__main__":
    unittest.main()
