"""
ConstraintAnalyzer — Analyze music through the flux-tensor lens.

The diagnostic is the killer feature. Feed your OWN music in and
see how it maps to FluxVectors, Eisenstein grids, and rhythmic roles.

Usage:
    from flux_tensor_midi.analyzer import FluxAnalyzer

    analyzer = FluxAnalyzer()
    report = analyzer.from_midi_events(events)
    terrain = analyzer.detect_terrain(report)
    diff = analyzer.compare(events_a, events_b)
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.core.snap import RhythmicRole, EisensteinSnap
from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.harmony.spectrum import spectral_centroid, spectral_flux


# ── Key Detection ────────────────────────────────────────────────────────────

MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def _correlate(a: List[float], b: List[float]) -> float:
    """Pearson correlation between two vectors."""
    n = len(a)
    if n == 0:
        return 0.0
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    num = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    den_a = math.sqrt(sum((a[i] - mean_a) ** 2 for i in range(n)))
    den_b = math.sqrt(sum((b[i] - mean_b) ** 2 for i in range(n)))
    if den_a == 0 or den_b == 0:
        return 0.0
    return num / (den_a * den_b)


def detect_key(notes: List[int]) -> Tuple[str, str, float]:
    """Detect the most likely key using Krumhansl-Schmuckler algorithm.

    Returns (key_name, mode, confidence).
    """
    if not notes:
        return ('C', 'major', 0.0)

    pitch_classes = Counter(n % 12 for n in notes)
    distribution = [pitch_classes.get(i, 0) for i in range(12)]
    total = sum(distribution)
    if total > 0:
        distribution = [d / total for d in distribution]

    best_key = 'C'
    best_mode = 'major'
    best_corr = -1.0

    for root in range(12):
        rotated = distribution[root:] + distribution[:root]

        major_corr = _correlate(rotated, MAJOR_PROFILE)
        if major_corr > best_corr:
            best_corr = major_corr
            best_key = NOTE_NAMES[root]
            best_mode = 'major'

        minor_corr = _correlate(rotated, MINOR_PROFILE)
        if minor_corr > best_corr:
            best_corr = minor_corr
            best_key = NOTE_NAMES[root]
            best_mode = 'minor'

    return (best_key, best_mode, best_corr)


# ── Terrain Detection ────────────────────────────────────────────────────────

TERRAIN_SIGNATURES = {
    'bebop': {
        'description': 'Bebop jazz — fast, chromatic, arpeggiated',
        'velocity_range': (60, 120),
        'density_range': (0.4, 0.8),
        'interval_entropy': (2.5, 3.5),
    },
    'trap': {
        'description': 'Trap / hip-hop — sparse kicks, rapid hats',
        'velocity_range': (40, 127),
        'density_range': (0.2, 0.6),
        'interval_entropy': (1.5, 2.5),
    },
    'techno': {
        'description': 'Techno — repetitive, evolving, four-on-floor',
        'velocity_range': (70, 110),
        'density_range': (0.5, 0.9),
        'interval_entropy': (1.0, 2.0),
    },
    'classical': {
        'description': 'Classical — contrapuntal, dynamic, expressive',
        'velocity_range': (30, 110),
        'density_range': (0.3, 0.7),
        'interval_entropy': (2.0, 3.5),
    },
}


class AnalysisReport:
    """Analysis results for a sequence of MIDI events."""

    def __init__(self):
        self.note_count: int = 0
        self.duration_ms: float = 0.0
        self.key: str = 'C'
        self.mode: str = 'major'
        self.key_confidence: float = 0.0
        self.velocity_mean: float = 0.0
        self.velocity_std: float = 0.0
        self.density: float = 0.0  # notes per second
        self.pitch_range: Tuple[int, int] = (0, 0)
        self.mean_interval: float = 0.0
        self.interval_entropy: float = 0.0
        self.flux: float = 0.0
        self.best_terrain: str = 'classical'
        self.terrain_confidence: float = 0.0

    def summary(self) -> Dict[str, Any]:
        return {
            'note_count': self.note_count,
            'duration_ms': self.duration_ms,
            'key': f"{self.key} {self.mode}",
            'key_confidence': round(self.key_confidence, 3),
            'velocity': f"{self.velocity_mean:.0f} ± {self.velocity_std:.0f}",
            'density': f"{self.density:.2f} notes/sec",
            'pitch_range': f"{self.pitch_range[0]}-{self.pitch_range[1]}",
            'mean_interval': round(self.mean_interval, 2),
            'interval_entropy': round(self.interval_entropy, 3),
            'flux': round(self.flux, 4),
            'best_terrain': self.best_terrain,
            'terrain_confidence': round(self.terrain_confidence, 3),
        }

    def __repr__(self) -> str:
        return (
            f"AnalysisReport(key={self.key} {self.mode}, "
            f"notes={self.note_count}, terrain={self.best_terrain})"
        )


class FluxAnalyzer:
    """Analyze MIDI events through the flux-tensor lens."""

    def from_midi_events(self, events: List[MidiEvent]) -> AnalysisReport:
        """Analyze a list of MidiEvent instances."""
        report = AnalysisReport()

        if not events:
            return report

        report.note_count = len(events)

        # Duration
        start = min(e.start_ms for e in events)
        end = max(e.end_ms for e in events)
        report.duration_ms = end - start

        # Key detection
        notes = [e.note for e in events]
        key, mode, conf = detect_key(notes)
        report.key = key
        report.mode = mode
        report.key_confidence = conf

        # Velocity stats
        velocities = [e.velocity for e in events]
        report.velocity_mean = sum(velocities) / len(velocities)
        if len(velocities) > 1:
            mean = report.velocity_mean
            report.velocity_std = math.sqrt(
                sum((v - mean) ** 2 for v in velocities) / (len(velocities) - 1)
            )

        # Density (notes per second)
        if report.duration_ms > 0:
            report.density = report.note_count / (report.duration_ms / 1000.0)

        # Pitch range
        report.pitch_range = (min(notes), max(notes))

        # Interval analysis
        sorted_events = sorted(events, key=lambda e: e.start_ms)
        pitches = [e.note for e in sorted_events]
        if len(pitches) > 1:
            intervals = [abs(pitches[i + 1] - pitches[i]) for i in range(len(pitches) - 1)]
            report.mean_interval = sum(intervals) / len(intervals)

            # Entropy of intervals
            interval_counts = Counter(intervals)
            total = len(intervals)
            entropy = 0.0
            for count in interval_counts.values():
                p = count / total
                if p > 0:
                    entropy -= p * math.log2(p)
            report.interval_entropy = entropy

        # Spectral flux via FluxVectors
        vectors = self._events_to_flux_vectors(sorted_events)
        report.flux = spectral_flux(vectors)

        # Terrain detection
        terrain, t_conf = self._detect_terrain(report)
        report.best_terrain = terrain
        report.terrain_confidence = t_conf

        return report

    def from_note_data(
        self,
        notes: List[Dict[str, Any]],
    ) -> AnalysisReport:
        """Analyze from a list of note dicts: {note, velocity, start_ms, duration_ms}."""
        events = [
            MidiEvent(
                note=n['note'],
                velocity=n.get('velocity', 80),
                start_ms=n.get('start_ms', 0),
                duration_ms=n.get('duration_ms', 250),
                channel=n.get('channel', 0),
            )
            for n in notes
        ]
        return self.from_midi_events(events)

    def detect_terrain(self, report: AnalysisReport) -> Tuple[str, float]:
        """Detect which terrain best matches an analysis report."""
        return self._detect_terrain(report)

    def compare(
        self,
        events_a: List[MidiEvent],
        events_b: List[MidiEvent],
    ) -> Dict[str, Any]:
        """Compare two sets of MIDI events."""
        report_a = self.from_midi_events(events_a)
        report_b = self.from_midi_events(events_b)

        vecs_a = self._events_to_flux_vectors(sorted(events_a, key=lambda e: e.start_ms))
        vecs_b = self._events_to_flux_vectors(sorted(events_b, key=lambda e: e.start_ms))

        # Cosine similarity of mean vectors
        if vecs_a and vecs_b:
            mean_a = FluxVector([sum(v[i] for v in vecs_a) / len(vecs_a) for i in range(9)])
            mean_b = FluxVector([sum(v[i] for v in vecs_b) / len(vecs_b) for i in range(9)])
            similarity = mean_a.cosine_similarity(mean_b)
        else:
            similarity = 0.0

        return {
            'similarity': round(similarity, 4),
            'report_a': report_a.summary(),
            'report_b': report_b.summary(),
            'key_match': report_a.key == report_b.key and report_a.mode == report_b.mode,
            'terrain_match': report_a.best_terrain == report_b.best_terrain,
            'velocity_diff': abs(report_a.velocity_mean - report_b.velocity_mean),
            'density_ratio': (
                report_a.density / max(report_b.density, 0.001)
                if report_b.density > 0 else 0.0
            ),
        }

    # ── Internal ──────────────────────────────────────────────────────────

    def _events_to_flux_vectors(self, events: List[MidiEvent]) -> List[FluxVector]:
        """Convert MIDI events to FluxVectors by grouping into time windows."""
        if not events:
            return []

        window_ms = 250.0  # quarter note at 120 BPM
        vectors: List[FluxVector] = []

        if not events:
            return vectors

        start = events[0].start_ms
        window_end = start + window_ms
        channel_values = [0.0] * 9

        for ev in events:
            while ev.start_ms >= window_end:
                vectors.append(FluxVector(channel_values))
                channel_values = [0.0] * 9
                window_end += window_ms

            # Map note to one of 9 channels (C4..D5 range mapped to 0..8)
            ch = min(8, max(0, (ev.note - 60) % 9))
            channel_values[ch] += ev.velocity / 127.0

        # Flush remaining
        if any(v > 0 for v in channel_values):
            vectors.append(FluxVector(channel_values))

        return vectors

    def _detect_terrain(self, report: AnalysisReport) -> Tuple[str, float]:
        """Score each terrain signature against the report."""
        best = 'classical'
        best_score = 0.0

        for name, sig in TERRAIN_SIGNATURES.items():
            score = 0.0

            # Velocity range match
            v_lo, v_hi = sig['velocity_range']
            if v_lo <= report.velocity_mean <= v_hi:
                score += 0.3

            # Density match
            d_lo, d_hi = sig['density_range']
            if d_lo <= report.density <= d_hi:
                score += 0.3

            # Interval entropy match
            e_lo, e_hi = sig['interval_entropy']
            if e_lo <= report.interval_entropy <= e_hi:
                score += 0.4

            if score > best_score:
                best_score = score
                best = name

        return best, best_score
