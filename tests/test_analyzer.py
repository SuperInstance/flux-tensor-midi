"""Tests for the analyzer module — FluxAnalyzer, detect_key, AnalysisReport."""

from __future__ import annotations

import math

import pytest

from flux_tensor_midi.analyzer import (
    FluxAnalyzer,
    AnalysisReport,
    detect_key,
    _correlate,
    NOTE_NAMES,
    TERRAIN_SIGNATURES,
)
from flux_tensor_midi.midi.events import MidiEvent


# ── Helper ───────────────────────────────────────────────────────────────────

def make_events(notes, velocity=80, start_base=0, gap=250, duration=200):
    """Build a list of MidiEvent from a list of (note, ...) tuples or ints."""
    events = []
    for i, n in enumerate(notes):
        note = n if isinstance(n, int) else n[0]
        events.append(MidiEvent(
            note=note,
            velocity=velocity,
            start_ms=start_base + i * gap,
            duration_ms=duration,
            channel=0,
        ))
    return events


# ── _correlate ───────────────────────────────────────────────────────────────

class TestCorrelate:
    def test_perfect_positive(self):
        assert _correlate([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0)

    def test_perfect_negative(self):
        assert _correlate([1, 2, 3], [6, 4, 2]) == pytest.approx(-1.0)

    def test_empty(self):
        assert _correlate([], []) == 0.0

    def test_constant_series(self):
        assert _correlate([5, 5, 5], [1, 2, 3]) == 0.0

    def test_self_correlation(self):
        vals = [3.0, 1.5, 4.2, 0.8]
        assert _correlate(vals, vals) == pytest.approx(1.0)


# ── detect_key ───────────────────────────────────────────────────────────────

class TestDetectKey:
    def test_empty_returns_default(self):
        key, mode, conf = detect_key([])
        assert key == 'C'
        assert mode == 'major'
        assert conf == 0.0

    def test_c_major_scale(self):
        # C major scale notes: C D E F G A B
        notes = [60, 62, 64, 65, 67, 69, 71] * 4
        key, mode, conf = detect_key(notes)
        assert key == 'C'
        assert mode == 'major'
        assert conf > 0.5

    def test_a_minor_scale(self):
        # A minor: A B C D E F G — heavily weighted A
        notes = [69] * 8 + [71, 60, 62, 64, 65, 67]
        key, mode, conf = detect_key(notes)
        # The Krumhansl-Schmuckler algorithm should detect minor with A emphasis
        assert mode == 'minor'
        assert conf > 0.0

    def test_single_note(self):
        key, mode, conf = detect_key([60])
        # Should detect something with non-zero confidence
        assert key in NOTE_NAMES
        assert mode in ('major', 'minor')

    def test_confidence_bounds(self):
        _, _, conf = detect_key([60, 62, 64, 65, 67, 69, 71] * 4)
        assert -1.0 <= conf <= 1.0


# ── AnalysisReport ───────────────────────────────────────────────────────────

class TestAnalysisReport:
    def test_defaults(self):
        r = AnalysisReport()
        assert r.note_count == 0
        assert r.duration_ms == 0.0
        assert r.key == 'C'
        assert r.mode == 'major'
        assert r.key_confidence == 0.0

    def test_summary_keys(self):
        r = AnalysisReport()
        s = r.summary()
        assert 'note_count' in s
        assert 'key' in s
        assert 'best_terrain' in s
        assert 'density' in s

    def test_repr(self):
        r = AnalysisReport()
        assert 'AnalysisReport' in repr(r)


# ── FluxAnalyzer ─────────────────────────────────────────────────────────────

class TestFluxAnalyzer:
    def test_empty_events(self):
        analyzer = FluxAnalyzer()
        report = analyzer.from_midi_events([])
        assert report.note_count == 0
        assert report.duration_ms == 0.0

    def test_single_event(self):
        analyzer = FluxAnalyzer()
        events = make_events([60])
        report = analyzer.from_midi_events(events)
        assert report.note_count == 1
        assert report.velocity_mean == 80.0
        assert report.velocity_std == 0.0
        assert report.pitch_range == (60, 60)

    def test_multiple_events(self):
        analyzer = FluxAnalyzer()
        events = make_events([60, 64, 67, 72])
        report = analyzer.from_midi_events(events)
        assert report.note_count == 4
        assert report.duration_ms > 0
        assert report.density > 0
        assert report.pitch_range == (60, 72)
        assert report.mean_interval > 0

    def test_key_detection_in_analysis(self):
        analyzer = FluxAnalyzer()
        # Repeated C major scale
        events = make_events([60, 62, 64, 65, 67, 69, 71] * 4, gap=200)
        report = analyzer.from_midi_events(events)
        assert report.key == 'C'
        assert report.mode == 'major'

    def test_terrain_detection(self):
        analyzer = FluxAnalyzer()
        report = analyzer.from_midi_events(make_events([60, 64, 67] * 10))
        terrain, conf = analyzer.detect_terrain(report)
        assert terrain in TERRAIN_SIGNATURES
        assert 0.0 <= conf <= 1.0

    def test_from_note_data(self):
        analyzer = FluxAnalyzer()
        notes = [
            {'note': 60, 'velocity': 100, 'start_ms': 0, 'duration_ms': 250},
            {'note': 64, 'velocity': 80, 'start_ms': 250, 'duration_ms': 250},
            {'note': 67, 'velocity': 90, 'start_ms': 500, 'duration_ms': 500},
        ]
        report = analyzer.from_note_data(notes)
        assert report.note_count == 3

    def test_compare_same_events(self):
        analyzer = FluxAnalyzer()
        events = make_events([60, 64, 67, 72])
        result = analyzer.compare(events, events)
        assert result['similarity'] == pytest.approx(1.0, abs=0.01)
        assert result['key_match'] is True
        assert result['terrain_match'] is True
        assert result['velocity_diff'] == pytest.approx(0.0)

    def test_compare_different_events(self):
        analyzer = FluxAnalyzer()
        events_a = make_events([60, 64, 67])
        events_b = make_events([70, 74, 77])
        result = analyzer.compare(events_a, events_b)
        assert 'similarity' in result
        assert 'report_a' in result
        assert 'report_b' in result

    def test_compare_empty(self):
        analyzer = FluxAnalyzer()
        result = analyzer.compare([], [])
        assert result['similarity'] == 0.0

    def test_velocity_stats(self):
        analyzer = FluxAnalyzer()
        events = [
            MidiEvent(note=60, velocity=100, start_ms=0, duration_ms=250, channel=0),
            MidiEvent(note=62, velocity=60, start_ms=250, duration_ms=250, channel=0),
        ]
        report = analyzer.from_midi_events(events)
        assert report.velocity_mean == pytest.approx(80.0)
        assert report.velocity_std > 0

    def test_interval_entropy(self):
        analyzer = FluxAnalyzer()
        # Same interval repeated → low entropy
        events = make_events([60, 64, 68, 72, 76])
        report = analyzer.from_midi_events(events)
        assert report.interval_entropy >= 0.0

    def test_flux_vectors_generated(self):
        analyzer = FluxAnalyzer()
        events = make_events([60, 62, 64] * 4, gap=100)
        report = analyzer.from_midi_events(events)
        # flux should be computed
        assert isinstance(report.flux, float)
