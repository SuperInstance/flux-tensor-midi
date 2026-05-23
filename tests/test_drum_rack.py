"""Tests for the drum_rack module."""

from __future__ import annotations

import os
import tempfile

import pytest

from flux_tensor_midi.drum_rack.rack import DrumRack, GM_DRUM_MAP
from flux_tensor_midi.drum_rack.sequencer import StepSequencer


# ---- DrumRack tests ----

class TestDrumRack:
    def test_default_channel(self):
        rack = DrumRack()
        assert rack.channel == 9

    def test_note_for_known_instrument(self):
        rack = DrumRack()
        assert rack.note_for("kick") == 36
        assert rack.note_for("snare") == 38
        assert rack.note_for("hihat_closed") == 42

    def test_note_for_unknown_raises(self):
        rack = DrumRack()
        with pytest.raises(KeyError, match="nonexistent"):
            rack.note_for("nonexistent")

    def test_custom_map(self):
        rack = DrumRack(custom_map={"boom": 35})
        assert rack.note_for("boom") == 35

    def test_register_instrument(self):
        rack = DrumRack()
        rack.register("custom_kick", 36)
        assert rack.note_for("custom_kick") == 36

    def test_register_invalid_note_raises(self):
        rack = DrumRack()
        with pytest.raises(ValueError):
            rack.register("bad", 200)

    def test_invalid_channel_raises(self):
        with pytest.raises(ValueError):
            DrumRack(channel=16)

    def test_instruments_returns_sorted(self):
        rack = DrumRack()
        names = rack.instruments()
        assert names == sorted(names)
        assert "kick" in names

    def test_as_dict(self):
        rack = DrumRack()
        d = rack.as_dict()
        assert d["kick"] == 36


# ---- StepSequencer basic tests ----

class TestStepSequencer:
    def test_default_steps(self):
        seq = StepSequencer()
        assert seq.steps == 16

    def test_invalid_steps_raises(self):
        with pytest.raises(ValueError):
            StepSequencer(steps=12)

    def test_valid_steps(self):
        for n in (8, 16, 32):
            seq = StepSequencer(steps=n)
            assert seq.steps == n

    def test_add_hit(self):
        seq = StepSequencer()
        seq.add_hit("kick", 0, 100)
        hits = seq.get_hits(0)
        assert len(hits) == 1
        assert hits[0] == ("kick", 100)

    def test_add_hit_out_of_range(self):
        seq = StepSequencer(steps=8)
        with pytest.raises(IndexError):
            seq.add_hit("kick", 8)

    def test_add_hit_bad_velocity(self):
        seq = StepSequencer()
        with pytest.raises(ValueError):
            seq.add_hit("kick", 0, 200)

    def test_remove_hit(self):
        seq = StepSequencer()
        seq.add_hit("kick", 0)
        assert seq.remove_hit("kick", 0) is True
        assert seq.get_hits(0) == []

    def test_remove_hit_missing(self):
        seq = StepSequencer()
        assert seq.remove_hit("kick", 0) is False

    def test_clear(self):
        seq = StepSequencer()
        seq.add_hit("kick", 0)
        seq.add_hit("snare", 4)
        seq.clear()
        assert seq.density() == 0.0

    def test_density(self):
        seq = StepSequencer(steps=8)
        seq.add_hit("kick", 0)
        seq.add_hit("snare", 2)
        assert seq.density() == pytest.approx(0.25)


# ---- Roll / Flam tests ----

class TestRollAndFlam:
    def test_straight_roll(self):
        seq = StepSequencer()
        seq.add_roll("snare", 0, 3, "straight", velocity=80)
        for i in range(4):
            hits = seq.get_hits(i)
            assert len(hits) == 1
            assert hits[0][1] == 80

    def test_dotted_roll(self):
        seq = StepSequencer(steps=16)
        seq.add_roll("hihat_closed", 0, 7, "dotted")
        hits_steps = [i for i in range(16) if seq.get_hits(i)]
        # Dotted should have fewer hits than straight
        assert len(hits_steps) < 8

    def test_flam(self):
        seq = StepSequencer()
        seq.add_flam("snare", 4, grace_velocity=55, main_velocity=110)
        hits = seq.get_hits(4)
        assert len(hits) == 2
        velocities = sorted([v for _, v in hits])
        assert velocities[0] == 55
        assert velocities[1] == 110

    def test_roll_bad_pattern_raises(self):
        seq = StepSequencer()
        with pytest.raises(ValueError, match="Unknown pattern"):
            seq.add_roll("kick", 0, 4, "wobble")


# ---- Euclidean rhythm tests ----

class TestEuclidean:
    def test_euclidean_basic(self):
        seq = StepSequencer()
        seq.euclidean("kick", pulses=4, velocity=100)
        hit_count = sum(1 for i in range(seq.steps) if seq.get_hits(i))
        assert hit_count == 4

    def test_euclidean_rotation(self):
        seq1 = StepSequencer()
        seq1.euclidean("kick", pulses=4, rotation=0)
        seq2 = StepSequencer()
        seq2.euclidean("kick", pulses=4, rotation=2)
        # Rotated should be different
        hits1 = [bool(seq1.get_hits(i)) for i in range(16)]
        hits2 = [bool(seq2.get_hits(i)) for i in range(16)]
        assert hits1 != hits2

    def test_euclidean_zero_pulses(self):
        seq = StepSequencer()
        seq.euclidean("kick", pulses=0)
        assert seq.density() == 0.0


# ---- Humanize tests ----

class TestHumanize:
    def test_humanize_returns_new_sequencer(self):
        seq = StepSequencer()
        seq.add_hit("kick", 0)
        human = seq.humanize(swing=0.5, velocity_range=15, timing_range=10, seed=42)
        assert human is not seq
        assert isinstance(human, StepSequencer)

    def test_humanize_preserves_hits(self):
        seq = StepSequencer()
        seq.add_hit("kick", 0, 100)
        human = seq.humanize(seed=42)
        assert len(human.get_hits(0)) == 1


# ---- Rotate tests ----

class TestRotate:
    def test_rotate_forward(self):
        seq = StepSequencer(steps=8)
        seq.add_hit("kick", 0, 100)
        seq.rotate(2)
        assert len(seq.get_hits(2)) == 1
        assert len(seq.get_hits(0)) == 0

    def test_rotate_zero(self):
        seq = StepSequencer()
        seq.add_hit("kick", 0)
        seq.rotate(0)
        assert len(seq.get_hits(0)) == 1

    def test_rotate_full(self):
        seq = StepSequencer(steps=8)
        seq.add_hit("kick", 3)
        seq.rotate(8)
        assert len(seq.get_hits(3)) == 1


# ---- Render tests ----

class TestRender:
    def test_render_returns_events(self):
        seq = StepSequencer()
        seq.add_hit("kick", 0)
        seq.add_hit("snare", 4)
        events = seq.render(bpm=120)
        assert len(events) == 2
        assert events[0].note == 36  # kick
        assert events[1].note == 38  # snare

    def test_render_events_sorted_by_time(self):
        seq = StepSequencer()
        seq.add_hit("snare", 4)
        seq.add_hit("kick", 0)
        events = seq.render(bpm=120)
        assert events[0].start_ms < events[1].start_ms

    def test_render_to_midi_file(self):
        seq = StepSequencer()
        seq.load_preset("boom_bap")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test.mid")
            events = seq.render(bpm=90, output=path)
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

    def test_render_bpm_affects_timing(self):
        seq = StepSequencer()
        seq.add_hit("kick", 0)
        seq.add_hit("kick", 4)
        ev_slow = seq.render(bpm=60)
        ev_fast = seq.render(bpm=240)
        # Fast BPM = shorter step duration
        assert ev_fast[1].start_ms < ev_slow[1].start_ms


# ---- Preset tests ----

class TestPresets:
    @pytest.mark.parametrize("name", [
        "boom_bap", "trap_hats", "four_on_floor", "breakbeat", "bossa_nova", "dnb"
    ])
    def test_preset_loads_and_renders(self, name):
        seq = StepSequencer()
        seq.load_preset(name)
        assert seq.density() > 0
        events = seq.render(bpm=120)
        assert len(events) > 0

    def test_unknown_preset_raises(self):
        seq = StepSequencer()
        with pytest.raises(ValueError, match="Unknown preset"):
            seq.load_preset("nonexistent")

    def test_boom_bap_has_kick_and_snare(self):
        seq = StepSequencer()
        seq.load_preset("boom_bap")
        events = seq.render(bpm=90)
        notes = {e.note for e in events}
        assert 36 in notes  # kick
        assert 38 in notes  # snare

    def test_trap_hats_dense(self):
        seq = StepSequencer()
        seq.load_preset("trap_hats")
        # Should have hats on most steps
        hat_hits = sum(
            1 for i in range(seq.steps)
            for inst, _ in seq.get_hits(i) if inst == "hihat_closed"
        )
        assert hat_hits >= 14

    def test_four_on_floor_kicks(self):
        seq = StepSequencer()
        seq.load_preset("four_on_floor")
        kick_steps = [i for i in range(seq.steps) if any(inst == "kick" for inst, _ in seq.get_hits(i))]
        assert 0 in kick_steps
        assert 4 in kick_steps
        assert 8 in kick_steps
        assert 12 in kick_steps


# ---- CLI integration test ----

class TestCLI:
    def test_drum_pattern_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cli_test.mid")
            from flux_tensor_midi.__main__ import main
            main(["drum", "--pattern", "trap_hats", "--bpm", "140", "--output", path])
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0

    def test_drum_preset_list(self, capsys):
        from flux_tensor_midi.__main__ import main
        main(["drum", "--preset-list"])
        out = capsys.readouterr().out
        assert "boom_bap" in out
        assert "trap_hats" in out

    def test_drum_euclidean(self, capsys):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "euclid.mid")
            from flux_tensor_midi.__main__ import main
            main(["drum", "--euclidean", "hihat_closed 5 1", "--bpm", "120", "--output", path])
            assert os.path.exists(path)
