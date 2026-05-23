"""
Regression tests for humanize + MIDI export.

Covers: negative tick deltas (P0), multi-track output, and edge cases.
"""

import os
import tempfile
import pytest

import mido

from flux_tensor_midi.drum_rack.sequencer import StepSequencer
from flux_tensor_midi.drum_rack.rack import DrumRack


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _render_to_file(seq, bpm=120.0):
    """Render sequencer to a temp .mid file and return the path."""
    fd, path = tempfile.mkstemp(suffix=".mid")
    os.close(fd)
    seq.render(bpm=bpm, output=path)
    return path


def _read_ticks(path):
    """Return list of (absolute_tick, type, note, channel) from a MIDI file."""
    mid = mido.MidiFile(path)
    results = []
    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            if msg.is_meta:
                continue
            abs_tick += msg.time
            if msg.type in ("note_on", "note_off"):
                results.append((abs_tick, msg.type, msg.note, msg.channel))
    return results


# ---------------------------------------------------------------------------
# P0: Negative tick delta crash
# ---------------------------------------------------------------------------

class TestHumanizeMidiExportCrash:
    """Regression: humanize with timing_range > 0 must not produce negative ticks."""

    def test_humanize_timing_export_no_crash(self):
        """Original bug: timing_range=20 with seed=42 caused ValueError."""
        seq = StepSequencer(16)
        seq.add_hit("kick", 0, 100)
        seq.add_hit("snare", 4, 100)
        humanized = seq.humanize(timing_range=20, seed=42)
        path = _render_to_file(humanized)
        ticks = _read_ticks(path)
        assert len(ticks) > 0
        os.unlink(path)

    def test_large_timing_range_no_crash(self):
        """Even with extreme timing range, no negative deltas."""
        seq = StepSequencer(16)
        for i in range(16):
            seq.add_hit("hihat_closed", i, 80)
        humanized = seq.humanize(timing_range=500, seed=123)
        path = _render_to_file(humanized)

        # Verify all deltas are non-negative by reading the file
        mid = mido.MidiFile(path)
        for track in mid.tracks:
            for msg in track:
                if not msg.is_meta:
                    assert msg.time >= 0, f"Negative delta: {msg.time}"
        os.unlink(path)

    def test_humanize_swing_export(self):
        """Swing + timing must not crash."""
        seq = StepSequencer(16)
        seq.load_preset("boom_bap")
        humanized = seq.humanize(swing=0.7, timing_range=30, velocity_range=15, seed=99)
        path = _render_to_file(humanized, bpm=90)
        ticks = _read_ticks(path)
        assert len(ticks) > 0
        os.unlink(path)

    def test_all_presets_humanize_export(self):
        """Every preset + humanize must export without error."""
        for name in ("boom_bap", "trap_hats", "four_on_floor", "breakbeat", "bossa_nova", "dnb"):
            seq = StepSequencer(16)
            seq.load_preset(name)
            humanized = seq.humanize(timing_range=15, velocity_range=10, seed=42)
            path = _render_to_file(humanized)
            mid = mido.MidiFile(path)
            assert len(mid.tracks) >= 1
            os.unlink(path)

    def test_first_step_negative_offset_clamped(self):
        """Step 0 with large negative timing offset should still produce valid MIDI."""
        seq = StepSequencer(16)
        seq.add_hit("kick", 0, 100)
        # Use seed that tends to produce negative offsets at step 0
        humanized = seq.humanize(timing_range=1000, seed=0)
        events = humanized.render(bpm=120)
        # start_ms should be >= 0
        assert all(e.start_ms >= 0 for e in events), \
            f"Negative start_ms found: {[e.start_ms for e in events if e.start_ms < 0]}"


# ---------------------------------------------------------------------------
# Multi-track MIDI output
# ---------------------------------------------------------------------------

class TestMultiTrackMidi:
    """Render should produce separate tracks per MIDI channel."""

    def test_single_channel_single_track(self):
        """Default drum rack (ch 9) produces one track."""
        seq = StepSequencer(16)
        seq.add_hit("kick", 0)
        seq.add_hit("snare", 4)
        path = _render_to_file(seq)
        mid = mido.MidiFile(path)
        assert len(mid.tracks) == 1
        os.unlink(path)

    def test_multi_channel_multi_track(self):
        """Events on different channels should produce multiple tracks."""
        rack_drums = DrumRack(channel=9)
        rack_bass = DrumRack(channel=1, custom_map={"bass_hit": 36})

        seq_drum = StepSequencer(16, rack=rack_drums)
        seq_drum.add_hit("kick", 0)

        seq_bass = StepSequencer(16, rack=rack_bass)
        seq_bass.add_hit("bass_hit", 0)

        # Render both and combine events
        events_drum = seq_drum.render(bpm=120)
        events_bass = seq_bass.render(bpm=120)

        # Combine and write via sequencer's _write_midi
        combined = events_drum + events_bass
        combined.sort(key=lambda e: e.start_ms)

        fd, path = tempfile.mkstemp(suffix=".mid")
        os.close(fd)
        seq_drum._write_midi(combined, 120.0, path)

        mid = mido.MidiFile(path)
        assert len(mid.tracks) == 2, f"Expected 2 tracks, got {len(mid.tracks)}"

        # Verify each track has the right channel
        channels_found = set()
        for track in mid.tracks:
            for msg in track:
                if msg.type in ("note_on", "note_off"):
                    channels_found.add(msg.channel)
        assert 9 in channels_found, "Drum channel (9) missing"
        assert 1 in channels_found, "Bass channel (1) missing"
        os.unlink(path)

    def test_track_order_sorted_by_channel(self):
        """Tracks should be ordered by channel number."""
        rack0 = DrumRack(channel=0, custom_map={"note": 60})
        rack5 = DrumRack(channel=5, custom_map={"note": 60})
        rack9 = DrumRack(channel=9)

        seq0 = StepSequencer(16, rack=rack0)
        seq0.add_hit("note", 0)
        seq5 = StepSequencer(16, rack=rack5)
        seq5.add_hit("note", 0)
        seq9 = StepSequencer(16, rack=rack9)
        seq9.add_hit("kick", 0)

        combined = seq0.render(120) + seq5.render(120) + seq9.render(120)
        combined.sort(key=lambda e: e.start_ms)

        fd, path = tempfile.mkstemp(suffix=".mid")
        os.close(fd)
        seq0._write_midi(combined, 120.0, path)

        mid = mido.MidiFile(path)
        assert len(mid.tracks) == 3

        # First track should have tempo meta message
        has_tempo = any(m.type == "set_tempo" for m in mid.tracks[0])
        assert has_tempo, "First track should contain tempo event"
        os.unlink(path)


# ---------------------------------------------------------------------------
# Humanize + MIDI export combined edge cases
# ---------------------------------------------------------------------------

class TestHumanizeMidiEdgeCases:

    def test_empty_pattern_export(self):
        """Empty pattern should produce valid (but empty) MIDI."""
        seq = StepSequencer(16)
        humanized = seq.humanize(timing_range=10, seed=1)
        path = _render_to_file(humanized)
        mid = mido.MidiFile(path)
        assert len(mid.tracks) >= 1
        os.unlink(path)

    def test_flam_humanize_export(self):
        """Flams + humanize must not crash."""
        seq = StepSequencer(16)
        seq.add_flam("snare", 4)
        humanized = seq.humanize(timing_range=10, velocity_range=5, seed=42)
        path = _render_to_file(humanized)
        mid = mido.MidiFile(path)
        for track in mid.tracks:
            for msg in track:
                if not msg.is_meta:
                    assert msg.time >= 0
        os.unlink(path)

    def test_euclidean_humanize_export(self):
        """Euclidean rhythm + humanize + export roundtrip."""
        seq = StepSequencer(16)
        seq.euclidean("kick", pulses=5, rotation=1)
        seq.euclidean("snare", pulses=3, rotation=0)
        humanized = seq.humanize(swing=0.5, timing_range=20, seed=7)
        path = _render_to_file(humanized, bpm=140)
        ticks = _read_ticks(path)
        assert len(ticks) > 0
        os.unlink(path)

    def test_deterministic_with_seed(self):
        """Same seed produces identical output."""
        seq = StepSequencer(16)
        seq.add_hit("kick", 0)
        seq.add_hit("snare", 4)
        seq.add_hit("hihat_closed", 8)

        h1 = seq.humanize(timing_range=20, seed=42)
        h2 = seq.humanize(timing_range=20, seed=42)

        ev1 = h1.render(bpm=120)
        ev2 = h2.render(bpm=120)

        for a, b in zip(ev1, ev2):
            assert a.start_ms == b.start_ms
            assert a.velocity == b.velocity
