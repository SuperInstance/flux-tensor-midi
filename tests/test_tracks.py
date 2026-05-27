"""Tests for the tracks module — Track, Arrangement, preset functions."""

from __future__ import annotations

import pytest

from flux_tensor_midi.tracks import Track, Arrangement, trap_beat, techno_loop, jazz_combo
from flux_tensor_midi.core.snap import RhythmicRole
from flux_tensor_midi.midi.events import MidiEvent


# ── Track ────────────────────────────────────────────────────────────────────

class TestTrackInit:
    def test_basic_creation(self):
        t = Track('piano', RhythmicRole.ROOT, 'piano', bpm=120.0)
        assert t.name == 'piano'
        assert t.role == RhythmicRole.ROOT
        assert t.voice == 'piano'

    def test_default_voice(self):
        t = Track('test')
        assert t.voice == 'piano'

    def test_musician_attached(self):
        t = Track('bass', RhythmicRole.ROOT, 'bass')
        assert t.musician is not None
        assert t.musician.name == 'bass'

    def test_events_initially_empty(self):
        t = Track('test')
        assert t.events == []

    def test_voice_ranges(self):
        assert 'piano' in Track.VOICE_RANGES
        assert 'bass' in Track.VOICE_RANGES
        assert 'kick' in Track.VOICE_RANGES
        assert 'violin' in Track.VOICE_RANGES

    def test_voice_range_bounds(self):
        lo, hi = Track.VOICE_RANGES['bass']
        assert lo < hi
        assert 0 <= lo <= 127
        assert 0 <= hi <= 127


class TestTrackGenerate:
    def test_generate_produces_events(self):
        t = Track('piano', RhythmicRole.ROOT, 'piano', bpm=120.0, seed=42)
        t.generate(bars=2)
        assert len(t.events) > 0

    def test_generate_clears_previous(self):
        t = Track('test', RhythmicRole.ROOT, 'piano', bpm=120.0, seed=1)
        t.generate(bars=1)
        first = len(t.events)
        t.generate(bars=2)
        assert len(t.events) != first  # should differ (more bars)

    def test_generate_events_are_midi(self):
        t = Track('piano', RhythmicRole.ROOT, 'piano', bpm=120.0, seed=10)
        t.generate(bars=1)
        for ev in t.events:
            assert isinstance(ev, MidiEvent)
            assert 0 <= ev.note <= 127
            assert 1 <= ev.velocity <= 127
            assert ev.start_ms >= 0
            assert ev.duration_ms > 0

    def test_generate_deterministic_with_seed(self):
        t1 = Track('piano', RhythmicRole.ROOT, 'piano', bpm=120.0, seed=99)
        t2 = Track('piano', RhythmicRole.ROOT, 'piano', bpm=120.0, seed=99)
        t1.generate(bars=2)
        t2.generate(bars=2)
        assert len(t1.events) == len(t2.events)
        for e1, e2 in zip(t1.events, t2.events):
            assert e1.note == e2.note
            assert e1.start_ms == e2.start_ms

    def test_generate_doubletime_role(self):
        t = Track('hat', RhythmicRole.DOUBLETIME, 'hat', bpm=140.0, seed=5)
        t.generate(bars=1)
        assert len(t.events) > 0

    def test_generate_halftime_role(self):
        t = Track('bass', RhythmicRole.HALFTIME, 'bass', bpm=120.0, seed=5)
        t.generate(bars=1)
        assert len(t.events) > 0


class TestTrackRepr:
    def test_repr(self):
        t = Track('piano', RhythmicRole.ROOT, 'piano')
        r = repr(t)
        assert 'Track' in r
        assert 'piano' in r
        assert 'ROOT' in r


# ── Arrangement ──────────────────────────────────────────────────────────────

class TestArrangementInit:
    def test_default(self):
        arr = Arrangement()
        assert arr.name == 'arrangement'
        assert arr.bpm == 120.0
        assert arr._bars == 4
        assert arr.tracks == []

    def test_custom_params(self):
        arr = Arrangement(name='test', bpm=140.0, bars=8, seed=42)
        assert arr.name == 'test'
        assert arr.bpm == 140.0


class TestArrangementTracks:
    def test_add_track(self):
        arr = Arrangement()
        arr.add_track(Track('kick', RhythmicRole.ROOT, 'kick'))
        assert len(arr.tracks) == 1
        assert arr.tracks[0].name == 'kick'

    def test_tracks_returns_copy(self):
        arr = Arrangement()
        arr.add_track(Track('test', RhythmicRole.ROOT))
        tracks = arr.tracks
        tracks.clear()
        assert len(arr.tracks) == 1  # original unchanged


class TestArrangementGenerate:
    def test_generate_all(self):
        arr = Arrangement(bpm=120.0, bars=2, seed=42)
        arr.add_track(Track('piano', RhythmicRole.ROOT, 'piano', bpm=120.0, seed=42))
        arr.add_track(Track('bass', RhythmicRole.HALFTIME, 'bass', bpm=120.0, seed=42))
        arr.generate_all()
        for track in arr.tracks:
            assert len(track.events) > 0

    def test_to_midi_events(self):
        arr = Arrangement(bpm=120.0, bars=2, seed=42)
        arr.add_track(Track('piano', RhythmicRole.ROOT, 'piano', bpm=120.0, seed=42))
        arr.generate_all()
        events = arr.to_midi_events()
        assert len(events) > 0
        # Events should be sorted by start time
        for i in range(len(events) - 1):
            assert events[i].start_ms <= events[i + 1].start_ms

    def test_to_midi_events_with_loop(self):
        arr = Arrangement(bpm=120.0, bars=2, seed=42)
        arr.add_track(Track('piano', RhythmicRole.ROOT, 'piano', bpm=120.0, seed=42))
        arr.generate_all()
        arr.loop(2)
        events = arr.to_midi_events()
        assert len(events) > 0

    def test_summary(self):
        arr = Arrangement(name='test', bpm=140.0, bars=8)
        arr.add_track(Track('kick', RhythmicRole.ROOT, 'kick'))
        arr.generate_all()
        s = arr.summary()
        assert s['name'] == 'test'
        assert s['bpm'] == 140.0
        assert s['tracks'] == 1
        assert s['total_events'] > 0

    def test_repr(self):
        arr = Arrangement(name='combo', bpm=120.0)
        r = repr(arr)
        assert 'Arrangement' in r
        assert 'combo' in r


# ── Preset Functions ─────────────────────────────────────────────────────────

class TestTrapBeat:
    def test_creates_arrangement(self):
        arr = trap_beat(bpm=140, bars=8, seed=42)
        assert isinstance(arr, Arrangement)
        assert arr.name == 'trap_beat'
        assert arr.bpm == 140.0
        assert len(arr.tracks) == 3

    def test_track_roles(self):
        arr = trap_beat(seed=42)
        roles = [t.role for t in arr.tracks]
        assert RhythmicRole.ROOT in roles
        assert RhythmicRole.DOUBLETIME in roles
        assert RhythmicRole.HALFTIME in roles

    def test_generates(self):
        arr = trap_beat(bpm=140, bars=4, seed=42)
        arr.generate_all()
        for t in arr.tracks:
            assert len(t.events) > 0


class TestTechnoLoop:
    def test_creates_arrangement(self):
        arr = techno_loop(bpm=128, bars=16, seed=42)
        assert isinstance(arr, Arrangement)
        assert arr.name == 'techno_loop'
        assert arr.bpm == 128.0
        assert len(arr.tracks) == 3

    def test_generates(self):
        arr = techno_loop(seed=42)
        arr.generate_all()
        events = arr.to_midi_events()
        assert len(events) > 0


class TestJazzCombo:
    def test_creates_arrangement(self):
        arr = jazz_combo(bpm=180, bars=12, seed=42)
        assert isinstance(arr, Arrangement)
        assert arr.name == 'jazz_combo'
        assert arr.bpm == 180.0
        assert len(arr.tracks) == 3

    def test_has_triplet_drums(self):
        arr = jazz_combo(seed=42)
        drum_track = [t for t in arr.tracks if t.name == 'drums']
        assert len(drum_track) == 1
        assert drum_track[0].role == RhythmicRole.TRIPLET

    def test_generates(self):
        arr = jazz_combo(seed=42)
        arr.generate_all()
        for t in arr.tracks:
            assert len(t.events) > 0
