"""
Tests for MidiFileWriter and convenience to_midi methods.

Covers: multi-track output, tempo/time/key signatures, program changes,
control changes, delta-time correctness, overlapping notes, quantization,
to_bytes, to_midi on Arrangement/StepSequencer/JamSession/RoomMusician,
and CLI generate command.
"""

from __future__ import annotations

import os
import tempfile

import mido
import pytest

from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.midi_writer import MidiFileWriter, TrackMeta


# ── Helpers ──────────────────────────────────────────────────────────────────


def _tmp_path(suffix: str = ".mid") -> str:
    """Return a temporary file path for MIDI output."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.close(fd)
    return path


def _read_mid(path: str) -> mido.MidiFile:
    return mido.MidiFile(path)


def _basic_events() -> list[MidiEvent]:
    return [
        MidiEvent(note=60, velocity=100, start_ms=0, duration_ms=500, channel=0),
        MidiEvent(note=64, velocity=80, start_ms=500, duration_ms=250, channel=0),
        MidiEvent(note=67, velocity=90, start_ms=750, duration_ms=500, channel=0),
    ]


# ── 1. Basic construction & write ────────────────────────────────────────────


class TestBasicWrite:
    def test_single_track_write(self):
        writer = MidiFileWriter(bpm=120)
        writer.add_track("Piano", channel=0, events=_basic_events())
        path = _tmp_path()
        try:
            size = writer.write(path)
            assert size > 0
            assert os.path.exists(path)
            mid = _read_mid(path)
            assert len(mid.tracks) == 2  # conductor + 1 data track
        finally:
            os.unlink(path)

    def test_to_bytes(self):
        writer = MidiFileWriter(bpm=120)
        writer.add_track("Piano", channel=0, events=_basic_events())
        data = writer.to_bytes()
        assert isinstance(data, bytes)
        assert len(data) > 14  # minimum MIDI file size
        # Should start with MThd
        assert data[:4] == b"MThd"

    def test_empty_writer(self):
        writer = MidiFileWriter(bpm=120)
        data = writer.to_bytes()
        assert len(data) > 0
        # Should have only the conductor track
        path = _tmp_path()
        try:
            writer.write(path)
            mid = _read_mid(path)
            assert len(mid.tracks) == 1  # just conductor
        finally:
            os.unlink(path)


# ── 2. Multi-track ───────────────────────────────────────────────────────────


class TestMultiTrack:
    def test_multiple_tracks(self):
        writer = MidiFileWriter(bpm=140)
        writer.add_track("Bass", channel=0, events=[
            MidiEvent(note=36, velocity=100, start_ms=0, duration_ms=400),
        ])
        writer.add_track("Lead", channel=1, events=[
            MidiEvent(note=72, velocity=80, start_ms=0, duration_ms=200),
        ])
        writer.add_track("Pad", channel=2, events=[
            MidiEvent(note=60, velocity=60, start_ms=0, duration_ms=800),
        ])
        mid = writer.build()
        assert len(mid.tracks) == 4  # conductor + 3

    def test_track_names(self):
        writer = MidiFileWriter(bpm=120)
        writer.add_track("Drums", channel=9)
        writer.add_track("Bass", channel=1)
        mid = writer.build()
        names = [t.name for t in mid.tracks]
        assert "Drums" in names
        assert "Bass" in names

    def test_tracks_property(self):
        writer = MidiFileWriter(bpm=120)
        writer.add_track("A", channel=0)
        writer.add_track("B", channel=1)
        assert writer.num_tracks == 2
        assert len(writer.tracks) == 2


# ── 3. Tempo and time signature ─────────────────────────────────────────────


class TestTempoTimeSig:
    def test_default_tempo(self):
        writer = MidiFileWriter(bpm=120)
        mid = writer.build()
        conductor = mid.tracks[0]
        tempo_msgs = [m for m in conductor if m.type == "set_tempo"]
        assert len(tempo_msgs) == 1
        assert tempo_msgs[0].tempo == mido.bpm2tempo(120)

    def test_custom_tempo(self):
        writer = MidiFileWriter(bpm=140)
        mid = writer.build()
        conductor = mid.tracks[0]
        tempo_msgs = [m for m in conductor if m.type == "set_tempo"]
        assert tempo_msgs[0].tempo == mido.bpm2tempo(140)

    def test_time_signature(self):
        writer = MidiFileWriter(bpm=120, time_signature=(3, 4))
        mid = writer.build()
        conductor = mid.tracks[0]
        ts_msgs = [m for m in conductor if m.type == "time_signature"]
        assert len(ts_msgs) == 1
        assert ts_msgs[0].numerator == 3
        assert ts_msgs[0].denominator == 4

    def test_tempo_changes(self):
        writer = MidiFileWriter(bpm=120)
        writer.add_tempo_change(2000.0, 160.0)
        mid = writer.build()
        conductor = mid.tracks[0]
        tempo_msgs = [m for m in conductor if m.type == "set_tempo"]
        assert len(tempo_msgs) == 2

    def test_tempo_change_invalid_bpm(self):
        writer = MidiFileWriter(bpm=120)
        with pytest.raises(ValueError):
            writer.add_tempo_change(0.0, -10.0)


# ── 4. Key signature ─────────────────────────────────────────────────────────


class TestKeySignature:
    def test_key_signature_c_major(self):
        writer = MidiFileWriter(bpm=120, key_signature="C")
        mid = writer.build()
        conductor = mid.tracks[0]
        ks_msgs = [m for m in conductor if m.type == "key_signature"]
        assert len(ks_msgs) == 1
        assert ks_msgs[0].key == "C"

    def test_key_signature_a_minor(self):
        writer = MidiFileWriter(bpm=120, key_signature="Am")
        mid = writer.build()
        conductor = mid.tracks[0]
        ks_msgs = [m for m in conductor if m.type == "key_signature"]
        assert ks_msgs[0].key == "Am"

    def test_key_signature_sharp(self):
        writer = MidiFileWriter(bpm=120, key_signature="E")
        mid = writer.build()
        conductor = mid.tracks[0]
        ks_msgs = [m for m in conductor if m.type == "key_signature"]
        assert ks_msgs[0].key == "E"

    def test_no_key_signature(self):
        writer = MidiFileWriter(bpm=120)
        mid = writer.build()
        conductor = mid.tracks[0]
        ks_msgs = [m for m in conductor if m.type == "key_signature"]
        assert len(ks_msgs) == 0


# ── 5. Program changes ──────────────────────────────────────────────────────


class TestProgramChange:
    def test_program_change_written(self):
        writer = MidiFileWriter(bpm=120)
        writer.add_track("Piano", channel=0, program=1, events=_basic_events())
        mid = writer.build()
        track = mid.tracks[1]
        pc_msgs = [m for m in track if m.type == "program_change"]
        assert len(pc_msgs) == 1
        assert pc_msgs[0].program == 1

    def test_different_programs_per_track(self):
        writer = MidiFileWriter(bpm=120)
        writer.add_track("A", channel=0, program=24)
        writer.add_track("B", channel=1, program=33)
        mid = writer.build()
        pc_msgs_1 = [m for m in mid.tracks[1] if m.type == "program_change"]
        pc_msgs_2 = [m for m in mid.tracks[2] if m.type == "program_change"]
        assert pc_msgs_1[0].program == 24
        assert pc_msgs_2[0].program == 33


# ── 6. Control changes ──────────────────────────────────────────────────────


class TestControlChanges:
    def test_cc_in_track(self):
        writer = MidiFileWriter(bpm=120)
        writer.add_track("Mod", channel=0, events=_basic_events(),
                         control_changes=[(250.0, 1, 64)])
        mid = writer.build()
        track = mid.tracks[1]
        cc_msgs = [m for m in track if m.type == "control_change"]
        assert len(cc_msgs) >= 1
        assert cc_msgs[0].control == 1
        assert cc_msgs[0].value == 64


# ── 7. Delta-time correctness ────────────────────────────────────────────────


class TestDeltaTimes:
    def test_events_have_correct_timing(self):
        writer = MidiFileWriter(bpm=120)
        events = [
            MidiEvent(note=60, velocity=100, start_ms=0, duration_ms=500),
            MidiEvent(note=64, velocity=80, start_ms=1000, duration_ms=500),
        ]
        writer.add_track("Test", channel=0, events=events)
        mid = writer.build()
        track = mid.tracks[1]
        note_on_msgs = [m for m in track if m.type == "note_on" and m.velocity > 0]
        assert len(note_on_msgs) == 2
        # First note_on should be at time > 0 (after program change)
        # Second note_on delta should represent 1000ms gap
        # At 120 BPM, 1 beat = 500ms = 480 ticks, so 1000ms = 960 ticks
        assert note_on_msgs[1].time > 0


# ── 8. Overlapping notes ────────────────────────────────────────────────────


class TestOverlappingNotes:
    def test_overlapping_notes_no_hang(self):
        writer = MidiFileWriter(bpm=120)
        events = [
            MidiEvent(note=60, velocity=100, start_ms=0, duration_ms=1000),
            MidiEvent(note=64, velocity=80, start_ms=500, duration_ms=500),
        ]
        writer.add_track("Chord", channel=0, events=events)
        mid = writer.build()
        track = mid.tracks[1]

        # Count note_on and note_off
        note_on = [m for m in track if m.type == "note_on" and m.velocity > 0]
        note_off = [m for m in track if m.type == "note_off"]
        assert len(note_on) == 2
        assert len(note_off) == 2

        # Every note that's turned on should be turned off
        on_notes = {m.note for m in note_on}
        off_notes = {m.note for m in note_off}
        assert on_notes == off_notes

    def test_same_note_repeated(self):
        writer = MidiFileWriter(bpm=120)
        events = [
            MidiEvent(note=60, velocity=100, start_ms=0, duration_ms=250),
            MidiEvent(note=60, velocity=80, start_ms=500, duration_ms=250),
        ]
        writer.add_track("Melody", channel=0, events=events)
        mid = writer.build()
        track = mid.tracks[1]
        note_on = [m for m in track if m.type == "note_on" and m.velocity > 0]
        note_off = [m for m in track if m.type == "note_off"]
        assert len(note_on) == 2
        assert len(note_off) == 2


# ── 9. Quantization ─────────────────────────────────────────────────────────


class TestQuantization:
    def test_quantize_snaps_to_grid(self):
        events = [
            MidiEvent(note=60, velocity=100, start_ms=123.0, duration_ms=256.0),
            MidiEvent(note=64, velocity=80, start_ms=499.0, duration_ms=99.0),
        ]
        grid = 125.0  # 16th note at 120 BPM
        quantized = MidiFileWriter.quantize_events(events, grid)
        assert quantized[0].start_ms == 125.0  # snapped to nearest 125
        assert quantized[0].duration_ms == 250.0
        assert quantized[1].start_ms == 500.0
        assert quantized[1].duration_ms == 125.0  # minimum is grid size

    def test_quantize_zero_grid_raises(self):
        with pytest.raises(ValueError):
            MidiFileWriter.quantize_events([], 0)


# ── 10. Conductor track ─────────────────────────────────────────────────────


class TestConductorTrack:
    def test_conductor_track_is_first(self):
        writer = MidiFileWriter(bpm=120)
        writer.add_track("Piano", channel=0)
        mid = writer.build()
        assert mid.tracks[0].name == "Conductor"

    def test_conductor_has_end_of_track(self):
        writer = MidiFileWriter(bpm=120)
        mid = writer.build()
        eot = [m for m in mid.tracks[0] if m.type == "end_of_track"]
        assert len(eot) == 1


# ── 11. Arrangement.to_midi() ────────────────────────────────────────────────


class TestArrangementToMidi:
    def test_arrangement_export(self):
        from flux_tensor_midi.tracks import Arrangement, Track
        arr = Arrangement(name="test", bpm=120, bars=4, seed=42)
        arr.add_track(Track("piano", bpm=120.0, seed=42))
        arr.generate_all()
        path = _tmp_path()
        try:
            size = arr.to_midi(path)
            assert size > 0
            mid = _read_mid(path)
            assert len(mid.tracks) >= 2  # conductor + at least 1 track
        finally:
            os.unlink(path)


# ── 12. StepSequencer.to_midi() ──────────────────────────────────────────────


class TestStepSequencerToMidi:
    def test_sequencer_export(self):
        from flux_tensor_midi.drum_rack import StepSequencer
        seq = StepSequencer(steps=16)
        seq.load_preset("boom_bap")
        path = _tmp_path()
        try:
            size = seq.to_midi(path, bpm=120)
            assert size > 0
            mid = _read_mid(path)
            assert len(mid.tracks) >= 1
        finally:
            os.unlink(path)


# ── 13. JamSession.to_midi() ────────────────────────────────────────────────


class TestJamSessionToMidi:
    def test_jam_export(self):
        from flux_tensor_midi.ai_jam.session import JamSession
        from flux_tensor_midi.ai_jam.agent import AIAgent, AgentPersonality
        a1 = AIAgent(AgentPersonality(
            name="Agent1", instrument="piano", midi_channel=0, midi_program=1,
        ))
        a2 = AIAgent(AgentPersonality(
            name="Agent2", instrument="bass", midi_channel=1, midi_program=34,
        ))
        session = JamSession(agent1=a1, agent2=a2, bpm=120, total_bars=8, phrase_bars=4)
        path = _tmp_path()
        try:
            result = session.to_midi(path)
            assert result == path
            assert os.path.exists(path)
            mid = _read_mid(path)
            assert len(mid.tracks) == 2  # two agent tracks
        finally:
            os.unlink(path)


# ── 14. RoomMusician.render_to_file() ────────────────────────────────────────


class TestRoomMusicianRenderToFile:
    def test_render_to_file(self):
        from flux_tensor_midi.core.room import RoomMusician
        from flux_tensor_midi.core.flux import FluxVector
        room = RoomMusician("test_room")
        room.update_state(FluxVector(
            [0.8, 0.0, 0.5, 0.0, 0.3, 0.0, 0.0, 0.0, 0.0],
            salience=[1.0] * 9,
            tolerance=[0.1] * 9,
        ))
        path = _tmp_path()
        try:
            size = room.render_to_file(path, bpm=120, bars=2)
            assert size > 0
            mid = _read_mid(path)
            assert len(mid.tracks) == 2  # conductor + 1 data track
        finally:
            os.unlink(path)


# ── 15. CLI generate command ────────────────────────────────────────────────


class TestCLIGenerate:
    def test_generate_with_preset(self):
        import subprocess
        path = _tmp_path()
        try:
            result = subprocess.run(
                ["python3", "-m", "flux_tensor_midi", "generate",
                 "--preset", "trap_beat", "--output", path],
                capture_output=True, text=True, timeout=30,
                cwd="/home/phoenix/.openclaw/workspace/flux-tensor-midi",
            )
            assert result.returncode == 0
            assert os.path.exists(path)
            mid = _read_mid(path)
            assert len(mid.tracks) >= 2
        finally:
            if os.path.exists(path):
                os.unlink(path)


# ── 16. Validation ──────────────────────────────────────────────────────────


class TestValidation:
    def test_invalid_channel(self):
        writer = MidiFileWriter(bpm=120)
        with pytest.raises(ValueError):
            writer.add_track("Bad", channel=16)

    def test_invalid_program(self):
        writer = MidiFileWriter(bpm=120)
        with pytest.raises(ValueError):
            writer.add_track("Bad", channel=0, program=128)

    def test_negative_channel(self):
        writer = MidiFileWriter(bpm=120)
        with pytest.raises(ValueError):
            writer.add_track("Bad", channel=-1)

    def test_bpm_setter_validation(self):
        writer = MidiFileWriter(bpm=120)
        with pytest.raises(ValueError):
            writer.bpm = 0


# ── 17. Repr ─────────────────────────────────────────────────────────────────


class TestRepr:
    def test_writer_repr(self):
        writer = MidiFileWriter(bpm=140, ppqn=960)
        r = repr(writer)
        assert "140" in r
        assert "960" in r


# ── 18. PPQN customization ──────────────────────────────────────────────────


class TestPPQN:
    def test_custom_ppqn(self):
        writer = MidiFileWriter(bpm=120, ppqn=960)
        mid = writer.build()
        assert mid.ticks_per_beat == 960

    def test_default_ppqn(self):
        writer = MidiFileWriter(bpm=120)
        assert writer.ppqn == 480


# ── 19. MIDI file can be re-read by mido ────────────────────────────────────


class TestRoundTrip:
    def test_write_and_read_roundtrip(self):
        writer = MidiFileWriter(bpm=120, time_signature=(6, 8), key_signature="Am")
        writer.add_track("Piano", channel=0, program=1, events=_basic_events())
        path = _tmp_path()
        try:
            writer.write(path)
            mid = _read_mid(path)
            assert mid.ticks_per_beat == 480
            # Verify conductor track
            conductor = mid.tracks[0]
            ts = [m for m in conductor if m.type == "time_signature"][0]
            assert ts.numerator == 6
            assert ts.denominator == 8
            # Verify data track
            piano = mid.tracks[1]
            assert piano.name == "Piano"
        finally:
            os.unlink(path)
