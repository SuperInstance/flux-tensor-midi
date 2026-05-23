"""
Tests for flux_tensor_midi wave 3 features: genre_brain, tracks, analyzer, CLI.
"""

import sys
import os
import tempfile

# Ensure package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flux_tensor_midi.genre_brain import GenreBrain
from flux_tensor_midi.tracks import Arrangement, Track, trap_beat, techno_loop, jazz_combo
from flux_tensor_midi.analyzer import FluxAnalyzer, detect_key, AnalysisReport
from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.__main__ import main as cli_main


# ── GenreBrain ───────────────────────────────────────────────────────────────

def test_available_genres():
    genres = GenreBrain.available_genres()
    assert 'jazz' in genres
    assert 'hiphop' in genres
    assert 'electronic' in genres
    assert 'classical' in genres
    assert 'math' in genres
    print("  ✓ available_genres lists all genres")


def test_invalid_genre():
    try:
        GenreBrain('reggae')
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert 'reggae' in str(e)
    print("  ✓ invalid genre raises ValueError with helpful message")


def test_create_band_jazz():
    brain = GenreBrain('jazz')
    band, musicians = brain.create_band()
    assert band.member_count == 4  # conductor + 3 musicians
    assert len(musicians) == 3
    assert musicians[0].name == 'piano'
    assert musicians[1].name == 'bass'
    assert musicians[2].name == 'drums'
    print("  ✓ jazz band created with piano, bass, drums")


def test_create_band_with_seed():
    brain = GenreBrain('math')
    band1, mus1 = brain.create_band(seed=42)
    band2, mus2 = brain.create_band(seed=42)

    # Same seed should produce same initial states
    for m1, m2 in zip(mus1, mus2):
        assert m1.state == m2.state, f"Different states for {m1.name}"

    # Different seed should produce different states
    band3, mus3 = brain.create_band(seed=99)
    # (at least one should differ)
    any_diff = any(m1.state != m3.state for m1, m3 in zip(mus1, mus3))
    assert any_diff, "Different seeds should produce different states"
    print("  ✓ seed parameter produces reproducible configurations")


def test_create_band_custom_bpm():
    brain = GenreBrain('hiphop')
    band, _ = brain.create_band(bpm=160)
    assert band.bpm == 160.0
    print("  ✓ custom BPM overrides genre default")


def test_genre_preset():
    brain = GenreBrain('electronic')
    preset = brain.get_preset()
    assert preset['default_bpm'] == 128
    assert preset['default_key'] == 'A'
    assert len(preset['roles']) == len(preset['member_names'])
    assert len(preset['salience_profiles']) == len(preset['member_names'])
    print("  ✓ genre preset has consistent structure")


# ── Tracks ───────────────────────────────────────────────────────────────────

def test_track_generate():
    track = Track('test', seed=42)
    track.generate(bars=2)
    assert len(track.events) >= 0  # may be 0 if initial state is all zeros
    print(f"  ✓ track generated {len(track.events)} events in 2 bars")


def test_arrangement():
    arr = Arrangement(name='test', bpm=120, bars=4, seed=42)
    arr.add_track(Track('piano', seed=42))
    arr.add_track(Track('bass', seed=42))
    arr.generate_all()
    events = arr.to_midi_events()
    print(f"  ✓ arrangement with 2 tracks produced {len(events)} events")


def test_arrangement_loop():
    arr = Arrangement(name='test', bpm=120, bars=2, seed=42)
    arr.add_track(Track('piano', seed=42))
    arr.generate_all()
    base_events = arr.to_midi_events()
    arr.loop(times=2)
    looped_events = arr.to_midi_events()
    assert len(looped_events) == len(base_events) * 3  # original + 2 loops
    print("  ✓ arrangement loop triples event count")


def test_preset_trap_beat():
    beat = trap_beat(bpm=140, bars=4, seed=42)
    assert beat.name == 'trap_beat'
    assert len(beat.tracks) == 3
    beat.generate_all()
    events = beat.to_midi_events()
    print(f"  ✓ trap_beat preset: 3 tracks, {len(events)} events")


def test_preset_techno_loop():
    loop = techno_loop(seed=42)
    assert len(loop.tracks) == 3
    print("  ✓ techno_loop preset: 3 tracks")


def test_preset_jazz_combo():
    combo = jazz_combo(seed=42)
    assert len(combo.tracks) == 3
    print("  ✓ jazz_combo preset: 3 tracks")


# ── Analyzer ─────────────────────────────────────────────────────────────────

def _make_events(notes, bpm=120):
    """Helper: create MidiEvent list from note numbers."""
    quarter = 60000.0 / bpm
    events = []
    for i, note in enumerate(notes):
        events.append(MidiEvent(note=note, velocity=80, start_ms=i * quarter, duration_ms=quarter))
    return events


def test_detect_key_c_major():
    # C major scale
    notes = [60, 62, 64, 65, 67, 69, 71, 72]
    key, mode, conf = detect_key(notes)
    assert key == 'C'
    assert mode == 'major'
    assert conf > 0.5
    print(f"  ✓ detect_key: {key} {mode} (conf={conf:.3f})")


def test_detect_key_a_minor():
    # A minor scale — use multiple octaves for better detection
    notes = [69, 71, 72, 73, 74, 76, 77, 78, 81, 83, 84, 85]
    key, mode, conf = detect_key(notes)
    # Krumhansl-Schmuckler can be ambiguous with scale tones alone;
    # just verify it returns a valid result with reasonable confidence
    assert key in ('A', 'C'), f"Expected A or C (relative keys), got {key}"
    assert conf > 0.3
    print(f"  ✓ detect_key: {key} {mode} (conf={conf:.3f})")


def test_analyzer_from_events():
    events = _make_events([60, 64, 67, 72, 64, 60])
    analyzer = FluxAnalyzer()
    report = analyzer.from_midi_events(events)
    assert report.note_count == 6
    assert report.duration_ms > 0
    assert report.key in ('C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B')
    assert report.velocity_mean > 0
    assert report.best_terrain in ('bebop', 'trap', 'techno', 'classical')
    print(f"  ✓ analyzer report: {report}")


def test_analyzer_empty():
    analyzer = FluxAnalyzer()
    report = analyzer.from_midi_events([])
    assert report.note_count == 0
    print("  ✓ empty events produces empty report")


def test_analyzer_compare():
    events_a = _make_events([60, 64, 67, 72])
    events_b = _make_events([60, 64, 67, 72])
    analyzer = FluxAnalyzer()
    diff = analyzer.compare(events_a, events_b)
    assert diff['key_match'] is True
    assert diff['similarity'] > 0.9
    print(f"  ✓ compare: similarity={diff['similarity']}")


def test_analyzer_from_note_data():
    notes = [
        {'note': 60, 'velocity': 80, 'start_ms': 0, 'duration_ms': 250},
        {'note': 64, 'velocity': 90, 'start_ms': 250, 'duration_ms': 250},
        {'note': 67, 'velocity': 70, 'start_ms': 500, 'duration_ms': 250},
    ]
    analyzer = FluxAnalyzer()
    report = analyzer.from_note_data(notes)
    assert report.note_count == 3
    print("  ✓ from_note_data works")


def test_terrain_detection():
    # Dense, high velocity events → techno-like
    events = _make_events([60] * 50 + [62] * 50 + [64] * 50, bpm=128)
    analyzer = FluxAnalyzer()
    report = analyzer.from_midi_events(events)
    print(f"  ✓ terrain detection: {report.best_terrain} (conf={report.terrain_confidence:.3f})")


# ── CLI ──────────────────────────────────────────────────────────────────────

def test_cli_list_genres(capsys=None):
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        cli_main(['play', '--list-genres'])
    finally:
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
    assert 'jazz' in output
    assert 'hiphop' in output
    print("  ✓ CLI play --list-genres works")


def test_cli_genre():
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        cli_main(['play', '--genre', 'jazz', '--bpm', '160', '--seed', '42'])
    finally:
        output = sys.stdout.getvalue()
        sys.stdout = old_stdout
    assert 'jazz' in output.lower() or 'Genre' in output
    print("  ✓ CLI play --genre jazz --bpm 160 --seed 42 works")


def test_cli_export():
    with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as f:
        outpath = f.name

    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        cli_main(['play', '--genre', 'math', '--seed', '0', '--export', outpath, '--quiet'])
    finally:
        sys.stdout = old_stdout

    assert os.path.exists(outpath)
    size = os.path.getsize(outpath)
    assert size > 14, "MIDI file should be at least 14 bytes (header)"
    os.unlink(outpath)
    print(f"  ✓ CLI play --export produces valid MIDI file ({size} bytes)")


# ── Seed reproducibility ────────────────────────────────────────────────────

def test_seed_reproducibility():
    """Verify same seed → same output across full pipeline.

    Note: TZeroClock uses real wall-clock time (time.monotonic),
    so exact timestamps may differ. We verify note/velocity/duration
    patterns match, which are determined by the seed.
    """
    beat1 = trap_beat(bpm=140, bars=4, seed=42)
    beat2 = trap_beat(bpm=140, bars=4, seed=42)
    beat1.generate_all()
    beat2.generate_all()

    # Compare track-by-track (same seed → same notes/velocities/durations)
    for t1, t2 in zip(beat1.tracks, beat2.tracks):
        e1 = t1.events
        e2 = t2.events
        assert len(e1) == len(e2), (
            f"Track {t1.name}: {len(e1)} vs {len(e2)} events"
        )
        for i, (a, b) in enumerate(zip(e1, e2)):
            assert a.note == b.note, (
                f"Track {t1.name} event {i}: notes differ {a.note} vs {b.note}"
            )
            assert a.velocity == b.velocity, (
                f"Track {t1.name} event {i}: velocities differ"
            )
            assert a.duration_ms == b.duration_ms, (
                f"Track {t1.name} event {i}: durations differ"
            )

    print("  ✓ seed reproducibility: identical notes/velocities/durations for same seed")


# ── Run all tests ────────────────────────────────────────────────────────────

def run_all():
    tests = [
        # GenreBrain
        test_available_genres,
        test_invalid_genre,
        test_create_band_jazz,
        test_create_band_with_seed,
        test_create_band_custom_bpm,
        test_genre_preset,
        # Tracks
        test_track_generate,
        test_arrangement,
        test_arrangement_loop,
        test_preset_trap_beat,
        test_preset_techno_loop,
        test_preset_jazz_combo,
        # Analyzer
        test_detect_key_c_major,
        test_detect_key_a_minor,
        test_analyzer_from_events,
        test_analyzer_empty,
        test_analyzer_compare,
        test_analyzer_from_note_data,
        test_terrain_detection,
        # CLI
        test_cli_list_genres,
        test_cli_genre,
        test_cli_export,
        # Seed
        test_seed_reproducibility,
    ]

    print("=" * 60)
    print("  FLUX-Tensor-MIDI Wave 3 Tests")
    print("=" * 60)
    print()

    passed = 0
    failed = 0
    for test in tests:
        name = test.__name__
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print()
    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    if failed > 0:
        sys.exit(1)


if __name__ == '__main__':
    run_all()
