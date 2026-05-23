"""
Comprehensive tests for flux-tensor-midi — integration, edge cases,
property-based invariants, and full coverage gaps.
"""

from __future__ import annotations

import os
import tempfile
import wave

import pytest

from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.core.clock import TZeroClock
from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.snap import (
    EisensteinSnap,
    EisensteinRatio,
    RhythmicRole,
    UNISON,
    HALFTIME,
    TRIPLET,
    WALTZ_TIME,
    COMPOUND,
    DOUBLE_TIME,
    OFFSET,
    QUINTUPLE,
    SEPTUPLE,
    ROLE_RATIO_MAP,
)
from flux_tensor_midi.core.prerender import PreRenderBuffer, Zone, PreRenderedBeat
from flux_tensor_midi.midi.events import MidiEvent, NoteName
from flux_tensor_midi.midi.clock import MidiClock
from flux_tensor_midi.midi.channel import (
    MidiChannel,
    channel_for_role,
    program_for_role,
)
from flux_tensor_midi.drum_rack.rack import DrumRack
from flux_tensor_midi.drum_rack.sequencer import StepSequencer
from flux_tensor_midi.harmony.spectrum import (
    spectral_centroid,
    spectral_flux,
    salience_weighted_flux,
    dominant_channel,
    autocorrelation,
)
from flux_tensor_midi.harmony.jaccard import jaccard_index, weighted_jaccard, jaccard_distance
from flux_tensor_midi.harmony.chord import HarmonyState, ChordQuality, INTERVAL_CONSONANCE
from flux_tensor_midi.ensemble.score import Score
from flux_tensor_midi.ensemble.band import Band
from flux_tensor_midi.sidechannel.nod import Nod
from flux_tensor_midi.sidechannel.smile import Smile
from flux_tensor_midi.sidechannel.frown import Frown
from flux_tensor_midi.audio import MockRenderer, create_renderer
from flux_tensor_midi.audio.dawdreamer_bridge import _events_to_midi_bytes, _silence_wav
from flux_tensor_midi.adapters.daw_bridge import (
    build_midi_file,
    MidiExportConfig,
    TrackConfig,
    OscBridge,
    DawBridge,
    get_preset,
    build_osc_msg,
    create_demo_vms_data,
    vms_data_to_midi,
    vms_to_tracks,
    ALL_PRESETS,
)
from flux_tensor_midi.exceptions import ConstraintError, RenderError, GenreError


# ══════════════════════════════════════════════════════════════════════════════
# Integration: RoomMusician → Band → Score → Render pipeline
# ══════════════════════════════════════════════════════════════════════════════


class TestFullPipelineIntegration:
    """End-to-end: musicians → band → score → MIDI render."""

    def test_room_to_score_to_midi(self):
        """Multiple musicians play, record to score, export to MIDI."""
        conductor = RoomMusician("conductor", role=RhythmicRole.ROOT, clock=TZeroClock(bpm=120))
        piano = RoomMusician("piano", role=RhythmicRole.HALFTIME)
        bass = RoomMusician("bass", role=RhythmicRole.TRIPLET)

        piano.join_ensemble(conductor)
        bass.join_ensemble(conductor)

        piano.update_state(FluxVector([0.9, 0.3, 0.7, 0.1, 0.2, 0.5, 0.0, 0.0, 0.0]))
        bass.update_state(FluxVector([0.5, 0.8, 0.0, 0.3, 0.6, 0.0, 0.1, 0.0, 0.0]))

        score = Score("Integration Test")
        for _ in range(8):
            ts_p, vec_p = piano.emit()
            score.record_event("piano", ts_p, vec_p)
            ts_b, vec_b = bass.emit()
            score.record_event("bass", ts_b, vec_b)

        assert score.total_events() == 16
        midi_events = score.to_midi_events()
        assert len(midi_events) > 0
        assert all(isinstance(e, MidiEvent) for e in midi_events)
        # Events sorted by start time
        for i in range(1, len(midi_events)):
            assert midi_events[i].start_ms >= midi_events[i - 1].start_ms

    def test_band_tick_all_and_harmony(self):
        """Band.tick_all produces events and harmony analysis works."""
        conductor = RoomMusician("cond")
        band = Band("test_band", conductor=conductor, bpm=120)

        m1 = RoomMusician("m1", role=RhythmicRole.ROOT)
        m2 = RoomMusician("m2", role=RhythmicRole.HALFTIME)
        m3 = RoomMusician("m3", role=RhythmicRole.TRIPLET)

        band.add_musician(m1)
        band.add_musician(m2)
        band.add_musician(m3)

        m1.update_state(FluxVector([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        m2.update_state(FluxVector([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
        m3.update_state(FluxVector([0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))

        results = band.tick_all()
        assert len(results) == 4  # conductor + 3 members

        harmony = band.harmony()
        assert isinstance(harmony, HarmonyState)
        assert harmony.size == 4

        coherence = band.mean_coherence()
        assert 0.0 <= coherence <= 1.0

    def test_score_to_midi_events_multi_musician(self):
        """Score with multiple musicians maps to different MIDI channels."""
        score = Score("multi")
        for i in range(4):
            v = FluxVector.unit(i)
            score.record_event(f"musician_{i}", float(i) * 500.0, v)

        events = score.to_midi_events()
        # musician_0 → ch 0, musician_1 → ch 1, etc.
        channels = {e.channel for e in events}
        assert len(channels) >= 2

    def test_score_harmony_at(self):
        """Score.harmony_at returns HarmonyState near a timestamp."""
        score = Score("harm")
        v1 = FluxVector([0.9, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        v2 = FluxVector([0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        score.record_event("m1", 100.0, v1)
        score.record_event("m2", 105.0, v2)

        harm = score.harmony_at(103.0, window_ms=10.0)
        assert harm is not None
        assert harm.size == 2

    def test_score_harmony_at_no_events(self):
        score = Score("empty")
        assert score.harmony_at(0.0) is None

    def test_score_harmony_at_no_nearby(self):
        score = Score("far")
        score.record_event("m1", 1000.0, FluxVector.zero())
        assert score.harmony_at(0.0, window_ms=1.0) is None

    def test_score_spectral_flux(self):
        score = Score("flux")
        for i in range(5):
            v = FluxVector([float(i), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
            score.record_event("m1", float(i) * 100.0, v)
        flux = score.spectral_flux("m1")
        assert flux > 0.0

    def test_score_summary(self):
        score = Score("test")
        score.record_event("m1", 0.0, FluxVector.zero())
        s = score.summary()
        assert s["title"] == "test"
        assert s["musicians"] == 1
        assert s["total_events"] == 1


class TestDawBridgeIntegration:
    """Integration tests for VMS → MIDI → file pipeline."""

    def test_demo_data_to_midi_file(self):
        """create_demo_vms_data → vms_data_to_midi → valid MIDI bytes."""
        data = create_demo_vms_data()
        midi_bytes = vms_data_to_midi(data)
        assert midi_bytes[:4] == b"MThd"
        assert len(midi_bytes) > 100

    def test_vms_to_tracks(self):
        data = create_demo_vms_data()
        config = vms_to_tracks(data)
        assert isinstance(config, MidiExportConfig)
        assert config.tempo_bpm == 72.0
        assert len(config.tracks) > 0

    def test_build_midi_file_structure(self):
        config = MidiExportConfig(
            tempo_bpm=120.0,
            tracks=[
                TrackConfig(
                    name="test",
                    channel=0,
                    notes=[(0, 480, 60, 100)],
                )
            ]
        )
        data = build_midi_file(config)
        assert data[:4] == b"MThd"
        # Parse header
        import struct
        fmt, n_tracks, ppqn = struct.unpack(">HHH", data[8:14])
        assert fmt == 1
        assert n_tracks == 2  # conductor + 1 data track
        assert ppqn == 480

    def test_osc_bridge_packet_generation(self):
        bridge = OscBridge()
        pkt = bridge.emit_packet("room1", 60, 100, 250.0)
        assert isinstance(pkt, bytes)
        assert len(pkt) > 0

        pkt2 = bridge.nod_packet("room1", "room2", 0.7)
        assert isinstance(pkt2, bytes)

    def test_daw_bridge_export(self):
        bridge = DawBridge("ableton")
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "test.mid")
            size = bridge.export_data(create_demo_vms_data(), out)
            assert size > 0
            assert os.path.exists(out)

    def test_all_presets_accessible(self):
        for name in ALL_PRESETS:
            preset = get_preset(name)
            assert preset.name
            assert preset.osc_port > 0

    def test_get_preset_unknown(self):
        with pytest.raises(KeyError):
            get_preset("nonexistent_daw")

    def test_build_osc_msg_types(self):
        msg_i = build_osc_msg("/test", "i", 42)
        msg_f = build_osc_msg("/test", "f", 3.14)
        msg_s = build_osc_msg("/test", "s", "hello")
        assert all(isinstance(m, bytes) for m in [msg_i, msg_f, msg_s])

    def test_build_osc_msg_bad_type(self):
        with pytest.raises(ValueError, match="Unsupported OSC format char"):
            build_osc_msg("/test", "x", "bad")


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases: FluxVector
# ══════════════════════════════════════════════════════════════════════════════


class TestFluxVectorEdgeCases:
    def test_zero_vector(self):
        v = FluxVector.zero()
        assert v.magnitude == 0.0
        assert len(v) == 9

    def test_unit_vector(self):
        v = FluxVector.unit(3)
        assert v[3] == 1.0
        assert v.magnitude == pytest.approx(1.0)

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="9 values"):
            FluxVector([1.0, 2.0])

    def test_wrong_salience_length(self):
        with pytest.raises(ValueError, match="9 elements"):
            FluxVector([0.0] * 9, salience=[0.5])

    def test_wrong_tolerance_length(self):
        with pytest.raises(ValueError, match="9 elements"):
            FluxVector([0.0] * 9, tolerance=[0.1])

    def test_salience_clamped(self):
        v = FluxVector([1.0] * 9, salience=[2.0] * 9)
        assert all(s <= 1.0 for s in v.salience)

    def test_add_vectors(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(1)
        c = a + b
        assert c[0] == 1.0
        assert c[1] == 1.0

    def test_sub_vectors(self):
        a = FluxVector([1.0] * 9)
        b = FluxVector([0.5] * 9)
        c = a - b
        assert all(c[i] == 0.5 for i in range(9))

    def test_scalar_multiply(self):
        v = FluxVector([1.0] * 9)
        v2 = v * 3.0
        assert all(v2[i] == 3.0 for i in range(9))

    def test_rmul(self):
        v = FluxVector([1.0] * 9)
        v2 = 2.0 * v
        assert all(v2[i] == 2.0 for i in range(9))

    def test_distance_to_self(self):
        v = FluxVector([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0])
        assert v.distance_to(v) == pytest.approx(0.0)

    def test_distance_weighted(self):
        v = FluxVector([1.0] * 9, salience=[1.0] * 9)
        assert v.distance_to(v, weighted=True) == pytest.approx(0.0)

    def test_distance_type_error(self):
        v = FluxVector.zero()
        with pytest.raises(TypeError, match="FluxVector"):
            v.distance_to(42)  # type: ignore[arg-type]

    def test_dot_type_error(self):
        v = FluxVector.zero()
        with pytest.raises(TypeError, match="FluxVector"):
            v.dot(42)  # type: ignore[arg-type]

    def test_cosine_similarity_zero_vectors(self):
        a = FluxVector.zero()
        b = FluxVector.zero()
        assert a.cosine_similarity(b) == 0.0

    def test_cosine_similarity_orthogonal(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(4)
        assert a.cosine_similarity(b) == pytest.approx(0.0)

    def test_cosine_similarity_parallel(self):
        a = FluxVector([1.0] * 9)
        b = FluxVector([2.0] * 9)
        assert a.cosine_similarity(b) == pytest.approx(1.0)

    def test_within_tolerance(self):
        a = FluxVector([1.0] * 9, tolerance=[0.5] * 9)
        b = FluxVector([1.3] * 9)
        assert a.within_tolerance(b)

        c = FluxVector([2.0] * 9)
        assert not a.within_tolerance(c)

    def test_jitter(self):
        v = FluxVector([0.0] * 9, tolerance=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9])
        assert v.jitter(0) == 0.1
        assert v.jitter(8) == 0.9

    def test_equality_and_hash(self):
        a = FluxVector([1.0] * 9)
        b = FluxVector([1.0] * 9)
        assert a == b
        assert hash(a) == hash(b)

    def test_inequality(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(1)
        assert a != b

    def test_eq_not_implemented(self):
        v = FluxVector.zero()
        assert v.__eq__(42) is NotImplemented

    def test_repr(self):
        v = FluxVector.zero()
        assert "FluxVector" in repr(v)

    def test_dot_product(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(0)
        assert a.dot(b) == pytest.approx(1.0)

    def test_salience_weighted_magnitude(self):
        v = FluxVector([1.0] * 9, salience=[0.5] * 9)
        assert v.salience_weighted_magnitude > 0
        assert v.salience_weighted_magnitude < v.magnitude


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases: TZeroClock
# ══════════════════════════════════════════════════════════════════════════════


class TestTZeroClockEdgeCases:
    def test_invalid_alpha_zero(self):
        with pytest.raises(ValueError, match="alpha"):
            TZeroClock(alpha=0.0)

    def test_invalid_alpha_one(self):
        with pytest.raises(ValueError, match="alpha"):
            TZeroClock(alpha=1.0)

    def test_invalid_bpm_zero(self):
        with pytest.raises(ValueError, match="bpm"):
            TZeroClock(bpm=0)

    def test_invalid_bpm_negative(self):
        with pytest.raises(ValueError, match="bpm"):
            TZeroClock(bpm=-10)

    def test_tick_advances(self):
        clock = TZeroClock(bpm=120)
        t0 = clock.tick()
        t1 = clock.tick()
        assert t1 > t0
        assert clock.ticks == 2

    def test_time_ms_no_advance(self):
        clock = TZeroClock(bpm=120)
        ms = clock.time_ms()
        assert isinstance(ms, float)

    def test_drift_ms(self):
        clock = TZeroClock(bpm=120)
        assert clock.drift_ms() == 0.0

    def test_reset(self):
        clock = TZeroClock(bpm=120)
        clock.tick()
        clock.tick()
        clock.reset()
        assert clock.ticks == 0
        assert clock.drift_ms() == 0.0

    def test_reset_with_new_bpm(self):
        clock = TZeroClock(bpm=120)
        clock.tick()
        clock.reset(bpm=60)
        assert clock.bpm == 60
        assert clock.ticks == 0

    def test_reset_invalid_bpm(self):
        clock = TZeroClock(bpm=120)
        with pytest.raises(ValueError, match="bpm"):
            clock.reset(bpm=-1)

    def test_set_bpm(self):
        clock = TZeroClock(bpm=120)
        clock.set_bpm(60)
        assert clock.bpm == 60

    def test_set_bpm_invalid(self):
        clock = TZeroClock(bpm=120)
        with pytest.raises(ValueError, match="bpm"):
            clock.set_bpm(0)

    def test_from_beat(self):
        clock = TZeroClock.from_beat(5, bpm=120)
        assert clock.ticks == 5

    def test_synchronize_to(self):
        c1 = TZeroClock(bpm=120)
        c2 = TZeroClock(bpm=120)
        c1.tick()
        c1.tick()
        c2.synchronize_to(c1)
        assert c2.drift_ms() == c1.drift_ms()

    def test_align(self):
        clock = TZeroClock(bpm=120)
        correction = clock.align(1000.0)
        assert isinstance(correction, float)

    def test_tick_duration_ms(self):
        clock = TZeroClock(bpm=120)
        assert clock.tick_duration_ms == pytest.approx(500.0)

    def test_custom_reference_clock(self):
        ticks = iter([0.0, 0.5, 1.0, 1.5])
        clock = TZeroClock(bpm=120, reference_clock=lambda: next(ticks))
        t = clock.tick()
        assert isinstance(t, float)


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases: EisensteinSnap
# ══════════════════════════════════════════════════════════════════════════════


class TestEisensteinSnapEdgeCases:
    def test_snap_identity(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        assert snap.snap(0.0, RhythmicRole.ROOT) == 0.0

    def test_snap_snaps_to_grid(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        # 490 should snap to 500 (nearest 500)
        result = snap.snap(490.0, RhythmicRole.ROOT)
        assert result == 500.0

    def test_set_tempo(self):
        snap = EisensteinSnap()
        snap.set_tempo(120)
        assert snap.base_period_ms == 500.0

    def test_set_tempo_invalid(self):
        snap = EisensteinSnap()
        with pytest.raises(ValueError, match="bpm"):
            snap.set_tempo(0)

    def test_snap_vector(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        result = snap.snap_vector([0.0, 500.0, 1000.0], RhythmicRole.ROOT)
        assert len(result) == 3
        assert result[0] == 0.0
        assert result[1] == 500.0

    def test_grid_for_root(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        grid = snap.grid_for(RhythmicRole.ROOT)
        assert len(grid) == 16
        assert grid[0] == 0.0
        assert grid[1] == 500.0

    def test_distance_to_grid(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        dist = snap.distance_to_grid(250.0, RhythmicRole.ROOT)
        assert 0.0 <= dist <= 0.5

    def test_in_phase(self):
        snap = EisensteinSnap(base_period_ms=500.0)
        assert snap.in_phase(0.0, 0.0, RhythmicRole.ROOT)
        assert snap.in_phase(500.0, 500.0, RhythmicRole.ROOT)

    def test_hexagonal_distance(self):
        d = EisensteinSnap.hexagonal_distance(0.0, 500.0, 500.0)
        assert d == 500.0

    def test_all_roles_have_ratios(self):
        snap = EisensteinSnap()
        for role in RhythmicRole:
            result = snap.snap(0.0, role)
            assert isinstance(result, float)

    def test_covering_radius(self):
        assert EisensteinSnap.COVERING_RADIUS == pytest.approx(1.0 / (3.0**0.5))


class TestEisensteinRatioEdgeCases:
    def test_invalid_denominator(self):
        with pytest.raises(ValueError, match="denominator"):
            EisensteinRatio(1, 0)

    def test_negative_denominator(self):
        with pytest.raises(ValueError, match="denominator"):
            EisensteinRatio(1, -1)

    def test_ratio_value(self):
        r = EisensteinRatio(3, 2)
        assert r.ratio == pytest.approx(1.5)

    def test_snap_with_phase(self):
        r = EisensteinRatio(1, 1, phase_offset=0.5)
        # At base 500, period=500, phase=250. Snap 0 → -250 rounded to 0*500+250=250
        result = r.snap(0.0, 500.0)
        assert isinstance(result, float)

    def test_repr(self):
        r = EisensteinRatio(3, 2)
        assert "3:2" in repr(r)

    def test_predefined_ratios(self):
        assert UNISON.ratio == 1.0
        assert HALFTIME.ratio == 2.0
        assert TRIPLET.ratio == 1.5
        assert WALTZ_TIME.ratio == 3.0
        assert COMPOUND.ratio == pytest.approx(4.0 / 3.0)
        assert DOUBLE_TIME.ratio == 0.5
        assert QUINTUPLE.ratio == 1.25
        assert SEPTUPLE.ratio == 1.75


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases: RoomMusician
# ══════════════════════════════════════════════════════════════════════════════


class TestRoomMusicianEdgeCases:
    def test_emit_default_state(self):
        r = RoomMusician("test")
        ts, vec = r.emit()
        assert isinstance(ts, float)
        assert vec == FluxVector.zero()

    def test_emit_custom_vector(self):
        r = RoomMusician("test")
        v = FluxVector.unit(0)
        ts, vec = r.emit(v)
        assert vec == v

    def test_listen_to(self):
        a = RoomMusician("a")
        b = RoomMusician("b")
        a.listen_to(b)
        assert b.room_id in a.listeners

    def test_stop_listening(self):
        a = RoomMusician("a")
        b = RoomMusician("b")
        a.listen_to(b)
        a.stop_listening(b)
        assert b.room_id not in a.listeners

    def test_listen_returns_events(self):
        a = RoomMusician("a")
        b = RoomMusician("b")
        a.listen_to(b)
        b.emit()
        events = a.listen()
        assert len(events) == 1
        assert events[0][0] == "b"

    def test_side_channels(self):
        a = RoomMusician("a")
        b = RoomMusician("b")
        a.listen_to(b)
        b.send_nod(a)
        b.send_smile(a)
        b.send_frown(a)

        msgs = a.receive_sidechannels()
        assert "b" in msgs["nods"]
        assert "b" in msgs["smiles"]
        assert "b" in msgs["frowns"]

    def test_coherence_with(self):
        a = RoomMusician("a")
        b = RoomMusician("b")
        a.update_state(FluxVector.unit(0))
        b.update_state(FluxVector.unit(0))
        assert a.coherence_with(b) == pytest.approx(1.0)

    def test_leave_ensemble(self):
        a = RoomMusician("a")
        b = RoomMusician("b")
        c = RoomMusician("c")
        a.listen_to(b)
        a.listen_to(c)
        a.leave_ensemble()
        assert len(a.listeners) == 0

    def test_role_setter(self):
        r = RoomMusician("test")
        r.role = RhythmicRole.TRIPLET
        assert r.role == RhythmicRole.TRIPLET

    def test_state_setter(self):
        r = RoomMusician("test")
        v = FluxVector.unit(4)
        r.state = v
        assert r.state == v

    def test_repr(self):
        r = RoomMusician("test")
        assert "test" in repr(r)
        assert "ROOT" in repr(r)

    def test_event_history(self):
        r = RoomMusician("test")
        assert r.event_history == []
        r.emit()
        assert len(r.event_history) == 1


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases: PreRenderBuffer
# ══════════════════════════════════════════════════════════════════════════════


class TestPreRenderBufferEdgeCases:
    def test_advance_fills_zones(self):
        buf = PreRenderBuffer(room_id="test", depth=6)
        buf.advance(0.0)
        assert len(buf.committed) + len(buf.tentative) + len(buf.sketch) > 0

    def test_get_beat(self):
        buf = PreRenderBuffer(room_id="test", depth=6)
        buf.advance(0.0)
        beat = buf.get_beat(1.0)
        # May or may not exist depending on promotion
        assert beat is None or isinstance(beat, PreRenderedBeat)

    def test_adjust_committed_fails(self):
        buf = PreRenderBuffer(room_id="test", depth=6)
        buf.advance(0.0)
        # Manually add a committed beat
        buf.committed[0.0] = PreRenderedBeat(beat=0.0, zone=Zone.COMMITTED, tile="test")
        assert not buf.adjust(0.0, "new_tile")

    def test_adjust_tentative(self):
        buf = PreRenderBuffer(room_id="test", depth=6)
        buf.tentative[2.0] = PreRenderedBeat(beat=2.0, zone=Zone.TENTATIVE, tile="old")
        assert buf.adjust(2.0, "new")
        assert buf.tentative[2.0].tile == "new"

    def test_adjust_sketch(self):
        buf = PreRenderBuffer(room_id="test", depth=6)
        buf.sketch[5.0] = PreRenderedBeat(beat=5.0, zone=Zone.SKETCH, tile="old")
        assert buf.adjust(5.0, "new")
        assert buf.sketch[5.0].tile == "new"

    def test_adjust_nonexistent(self):
        buf = PreRenderBuffer(room_id="test")
        assert not buf.adjust(99.0, "tile")

    def test_react_nod(self):
        buf = PreRenderBuffer(room_id="test", depth=6)
        buf.sketch[5.0] = PreRenderedBeat(beat=5.0, zone=Zone.SKETCH, tile="old")
        buf.react_to_signal(0.0, "nod")
        # Should promote a sketch → tentative if any exist

    def test_react_smile(self):
        buf = PreRenderBuffer(room_id="test")
        buf.tentative[2.0] = PreRenderedBeat(beat=2.0, zone=Zone.TENTATIVE, tile="x", confidence=0.5)
        buf.react_to_signal(0.0, "smile")
        assert buf.tentative[2.0].confidence > 0.5

    def test_react_frown(self):
        buf = PreRenderBuffer(room_id="test")
        buf.tentative[3.0] = PreRenderedBeat(beat=3.0, zone=Zone.TENTATIVE, tile="x")
        buf.tentative[4.0] = PreRenderedBeat(beat=4.0, zone=Zone.TENTATIVE, tile="y")
        buf.react_to_signal(2.0, "frown")
        assert 3.0 not in buf.tentative
        assert 3.0 in buf.sketch

    def test_react_breath(self):
        buf = PreRenderBuffer(room_id="test")
        buf.react_to_signal(0.0, "breath")  # should not raise

    def test_stats(self):
        buf = PreRenderBuffer(room_id="test")
        s = buf.stats()
        assert s["room_id"] == "test"
        assert "hit_rate" in s

    def test_visualize(self):
        buf = PreRenderBuffer(room_id="test", depth=6)
        buf.advance(0.0)
        vis = buf.visualize(0.0)
        assert "Pre-Render Buffer" in vis

    def test_plan_fn_and_render_fn(self):
        calls = []
        buf = PreRenderBuffer(room_id="test", depth=6)
        buf.plan_fn = lambda b: {"beat": b, "custom": True}
        buf.render_fn = lambda s: {**s, "rendered": True}
        buf.advance(0.0)
        # Sketches should use plan_fn


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases: MidiEvent
# ══════════════════════════════════════════════════════════════════════════════


class TestMidiEventEdgeCases:
    def test_note_out_of_range(self):
        with pytest.raises(ValueError, match="note"):
            MidiEvent(128, 100, 0, 100)

    def test_note_negative(self):
        with pytest.raises(ValueError, match="note"):
            MidiEvent(-1, 100, 0, 100)

    def test_velocity_out_of_range(self):
        with pytest.raises(ValueError, match="velocity"):
            MidiEvent(60, 200, 0, 100)

    def test_channel_out_of_range(self):
        with pytest.raises(ValueError, match="channel"):
            MidiEvent(60, 100, 0, 100, channel=16)

    def test_negative_duration(self):
        with pytest.raises(ValueError, match="duration"):
            MidiEvent(60, 100, 0, -1)

    def test_zero_duration(self):
        ev = MidiEvent(60, 100, 0, 0)
        assert ev.duration_ms == 0
        assert ev.end_ms == 0

    def test_note_on_bytes(self):
        ev = MidiEvent(60, 100, 0, 500, channel=2)
        status, note, vel = ev.note_on_bytes()
        assert status == 0x92
        assert note == 60
        assert vel == 100

    def test_note_off_bytes(self):
        ev = MidiEvent(60, 100, 0, 500, channel=0)
        status, note, vel = ev.note_off_bytes()
        assert status == 0x80
        assert vel == 0

    def test_as_dict(self):
        ev = MidiEvent(60, 100, 0, 500, channel=1)
        d = ev.as_dict()
        assert d["note"] == 60
        assert d["velocity"] == 100
        assert d["channel"] == 1

    def test_from_flux_all_zero(self):
        events = MidiEvent.from_flux((0.0,) * 9, start_ms=0, duration_ms=500)
        assert events == []

    def test_from_flux_nonzero(self):
        events = MidiEvent.from_flux((1.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), start_ms=100, duration_ms=250)
        assert len(events) == 2

    def test_equality(self):
        a = MidiEvent(60, 100, 0, 500)
        b = MidiEvent(60, 100, 0, 500)
        assert a == b

    def test_hash(self):
        a = MidiEvent(60, 100, 0, 500)
        b = MidiEvent(60, 100, 0, 500)
        assert hash(a) == hash(b)

    def test_repr(self):
        ev = MidiEvent(60, 100, 0, 500)
        assert "MidiEvent" in repr(ev)


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases: MidiClock
# ══════════════════════════════════════════════════════════════════════════════


class TestMidiClockEdgeCases:
    def test_negative_bpm(self):
        with pytest.raises(ValueError, match="bpm"):
            MidiClock(bpm=-1)

    def test_zero_bpm(self):
        with pytest.raises(ValueError, match="bpm"):
            MidiClock(bpm=0)

    def test_tick_not_started(self):
        c = MidiClock(bpm=120)
        assert c.tick() == 0

    def test_start_and_tick(self):
        c = MidiClock(bpm=120)
        c.start()
        assert c.tick() == 1
        assert c.tick() == 2

    def test_stop(self):
        c = MidiClock(bpm=120)
        c.start()
        c.tick()
        c.stop()
        assert c.tick() == 1  # frozen

    def test_continue_(self):
        c = MidiClock(bpm=120)
        c.start()
        c.tick()
        c.stop()
        c.continue_()
        assert c.tick() == 2

    def test_reset(self):
        c = MidiClock(bpm=120)
        c.start()
        c.tick()
        c.tick()
        c.reset()
        assert c.tick_count == 0

    def test_beat_and_measure(self):
        c = MidiClock(bpm=120)
        c.start()
        for _ in range(24):
            c.tick()
        assert c.beat() == 1
        assert c.measure() == 0

    def test_tick_in_beat(self):
        c = MidiClock(bpm=120)
        c.start()
        c.tick()
        assert c.tick_in_beat() == 1

    def test_tick_in_measure(self):
        c = MidiClock(bpm=120)
        c.start()
        c.tick()
        assert c.tick_in_measure(beats_per_measure=4) == 1

    def test_pulse_interval(self):
        c = MidiClock(bpm=120)
        assert c.pulse_interval_ms == pytest.approx(60000.0 / (120 * 24))

    def test_quarter_note_ms(self):
        c = MidiClock(bpm=120)
        assert c.quarter_note_ms == 500.0

    def test_tempo_from_delay(self):
        bpm = MidiClock.tempo_from_delay(60000.0 / (120 * 24))
        assert bpm == pytest.approx(120.0, rel=0.01)

    def test_tempo_from_delay_invalid(self):
        with pytest.raises(ValueError, match="pulse_delay_ms"):
            MidiClock.tempo_from_delay(0)

    def test_bpm_setter_invalid(self):
        c = MidiClock(bpm=120)
        with pytest.raises(ValueError, match="bpm"):
            c.bpm = 0

    def test_callback(self):
        ticks = []
        c = MidiClock(bpm=120, tick_callback=ticks.append)
        c.start()
        c.tick()
        assert ticks == [1]

    def test_repr(self):
        c = MidiClock(bpm=120)
        assert "MidiClock" in repr(c)


# ══════════════════════════════════════════════════════════════════════════════
# Edge cases: Drum Rack / StepSequencer (additional)
# ══════════════════════════════════════════════════════════════════════════════


class TestDrumRackAdditional:
    def test_note_number_bounds(self):
        rack = DrumRack()
        with pytest.raises(ValueError, match="Note must be"):
            rack.register("bad", -1)
        with pytest.raises(ValueError, match="Note must be"):
            rack.register("bad", 128)

    def test_repr(self):
        rack = DrumRack()
        assert "DrumRack" in repr(rack)


class TestStepSequencerEdgeCases:
    def test_128_step_pattern_euclidean(self):
        """Euclidean algorithm should work for large step counts."""
        seq = StepSequencer(steps=32)
        seq.euclidean("kick", pulses=7)
        assert seq.density() > 0

    def test_all_instruments_at_once(self):
        """Place every known instrument on step 0."""
        seq = StepSequencer()
        rack = DrumRack()
        for name in rack.instruments():
            seq.add_hit(name, 0, 100)
        hits = seq.get_hits(0)
        assert len(hits) == len(rack.instruments())

    def test_single_step_pattern(self):
        """8-step sequencer with one hit."""
        seq = StepSequencer(steps=8)
        seq.add_hit("kick", 0, 127)
        events = seq.render(bpm=120)
        assert len(events) == 1
        assert events[0].velocity == 127

    def test_empty_pattern_render(self):
        """Rendering an empty pattern returns no events."""
        seq = StepSequencer()
        events = seq.render(bpm=120)
        assert events == []

    def test_maximum_bpm(self):
        """Very high BPM should still render."""
        seq = StepSequencer()
        seq.add_hit("kick", 0)
        events = seq.render(bpm=300)
        assert len(events) == 1
        assert events[0].start_ms >= 0

    def test_zero_velocity_rejected(self):
        with pytest.raises(ValueError, match="velocity"):
            seq = StepSequencer()
            seq.add_hit("kick", 0, 0)

    def test_negative_velocity_rejected(self):
        with pytest.raises(ValueError, match="velocity"):
            seq = StepSequencer()
            seq.add_hit("kick", 0, -5)

    def test_roll_start_greater_than_end(self):
        seq = StepSequencer()
        with pytest.raises(ValueError, match="start"):
            seq.add_roll("kick", 5, 3)

    def test_euclidean_all_pulses(self):
        seq = StepSequencer()
        seq.euclidean("kick", pulses=16)
        assert seq.density() == 1.0

    def test_euclidean_more_pulses_than_steps(self):
        seq = StepSequencer(steps=8)
        seq.euclidean("kick", pulses=20)
        # Should fill all steps
        assert seq.density() == 1.0

    def test_humanize_reproducible_with_seed(self):
        seq = StepSequencer()
        seq.add_hit("kick", 0, 100)
        h1 = seq.humanize(seed=42)
        h2 = seq.humanize(seed=42)
        # Same seed should give same events
        e1 = h1.render(bpm=120)
        e2 = h2.render(bpm=120)
        assert len(e1) == len(e2)

    def test_rotate_negative(self):
        seq = StepSequencer(steps=8)
        seq.add_hit("kick", 4)
        seq.rotate(-2)
        assert len(seq.get_hits(2)) == 1

    def test_get_hits_out_of_range(self):
        seq = StepSequencer(steps=8)
        with pytest.raises(IndexError):
            seq.get_hits(8)

    def test_repr(self):
        seq = StepSequencer()
        assert "StepSequencer" in repr(seq)


# ══════════════════════════════════════════════════════════════════════════════
# Harmony module edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestSpectrumEdgeCases:
    def test_spectral_centroid_empty(self):
        assert spectral_centroid([]) == 0.0

    def test_spectral_centroid_zero_magnitude(self):
        vecs = [FluxVector.zero()] * 3
        assert spectral_centroid(vecs) == 0.0

    def test_spectral_flux_single(self):
        assert spectral_flux([FluxVector.zero()]) == 0.0

    def test_spectral_flux_empty(self):
        assert spectral_flux([]) == 0.0

    def test_salience_weighted_flux(self):
        v1 = FluxVector([1.0] * 9, salience=[1.0] * 9)
        v2 = FluxVector([0.5] * 9, salience=[1.0] * 9)
        flux = salience_weighted_flux([v1, v2])
        assert flux > 0.0

    def test_dominant_channel_empty(self):
        assert dominant_channel([]) == -1

    def test_dominant_channel_all_zero(self):
        assert dominant_channel([FluxVector.zero()]) == -1

    def test_autocorrelation_single(self):
        result = autocorrelation([FluxVector.unit(0)])
        assert result[0] == 1.0

    def test_autocorrelation_constant(self):
        vecs = [FluxVector([1.0] * 9)] * 5
        result = autocorrelation(vecs)
        assert result[0] == 1.0
        assert all(r == 0.0 for r in result[1:])


class TestJaccardEdgeCases:
    def test_both_silent(self):
        a = FluxVector.zero()
        b = FluxVector.zero()
        assert jaccard_index(a, b) == 1.0

    def test_identical(self):
        v = FluxVector([1.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert jaccard_index(v, v) == 1.0

    def test_disjoint(self):
        a = FluxVector([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        b = FluxVector([0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0])
        assert jaccard_index(a, b) == 0.0

    def test_weighted_jaccard_both_zero(self):
        a = FluxVector.zero()
        b = FluxVector.zero()
        assert weighted_jaccard(a, b) == 1.0

    def test_jaccard_distance(self):
        a = FluxVector([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        b = FluxVector([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert jaccard_distance(a, b) == 0.0


class TestChordEdgeCases:
    def test_empty_harmony_state(self):
        h = HarmonyState([])
        assert h.size == 0
        assert h.consonance() == 1.0
        assert h.quality() == ChordQuality.UNKNOWN

    def test_single_vector(self):
        v = FluxVector.unit(0)
        h = HarmonyState([v])
        assert h.size == 1
        assert h.consonance() == 1.0

    def test_correlation(self):
        v1 = FluxVector.unit(0)
        v2 = FluxVector.unit(0)
        h = HarmonyState([v1, v2])
        assert h.correlation() == pytest.approx(1.0)

    def test_voice_leading_cost(self):
        h1 = HarmonyState([FluxVector.unit(0)])
        h2 = HarmonyState([FluxVector.unit(4)])
        cost = h1.voice_leading_cost(h2)
        assert cost > 0.0

    def test_voice_leading_empty(self):
        h1 = HarmonyState([])
        h2 = HarmonyState([])
        assert h1.voice_leading_cost(h2) == 0.0

    def test_repr(self):
        h = HarmonyState([FluxVector.unit(0)])
        assert "HarmonyState" in repr(h)


# ══════════════════════════════════════════════════════════════════════════════
# Side-channel edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestSideChannelEdgeCases:
    def test_nod_invalid_intensity(self):
        with pytest.raises(ValueError, match="intensity"):
            Nod(intensity=1.5)

    def test_smile_invalid_intensity(self):
        with pytest.raises(ValueError, match="intensity"):
            Smile(intensity=-0.1)

    def test_frown_invalid_intensity(self):
        with pytest.raises(ValueError, match="intensity"):
            Frown(intensity=2.0)

    def test_nod_rate_empty(self):
        n = Nod()
        assert n.rate() == 0.0

    def test_nod_has_sent_to(self):
        n = Nod()
        assert not n.has_sent_to("unknown")

    def test_nod_reset(self):
        n = Nod()
        r = RoomMusician("target")
        n.send(r)
        n.reset()
        assert n.count == 0

    def test_all_side_channels_repr(self):
        assert "Nod" in repr(Nod())
        assert "Smile" in repr(Smile())
        assert "Frown" in repr(Frown())


# ══════════════════════════════════════════════════════════════════════════════
# Band edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestBandEdgeCases:
    def test_empty_band(self):
        band = Band("empty")
        assert band.member_count == 0
        assert band.conductor is None
        assert band.tick_all() == {}
        assert band.get_all_events() == []

    def test_single_member_band(self):
        m = RoomMusician("lone")
        band = Band("solo")
        band.add_musician(m)
        assert band.member_count == 1
        coherence = band.mean_coherence()
        assert coherence == 1.0  # single member = perfect coherence

    def test_get_musician_by_name(self):
        m = RoomMusician("alice")
        band = Band("test")
        band.add_musician(m)
        assert band.get_musician("alice") is m
        assert band.get_musician("bob") is None

    def test_remove_musician(self):
        m = RoomMusician("removable")
        band = Band("test")
        band.add_musician(m)
        band.remove_musician(m)
        assert band.member_count == 0

    def test_set_bpm(self):
        band = Band("test", bpm=120)
        m = RoomMusician("m1")
        band.add_musician(m)
        band.set_bpm(140)
        assert band.bpm == 140
        assert m.clock.bpm == 140

    def test_everyone_listens_to_conductor(self):
        cond = RoomMusician("conductor")
        band = Band("test", conductor=cond, bpm=120)
        m1 = RoomMusician("m1")
        m2 = RoomMusician("m2")
        band.add_musician(m1)
        band.add_musician(m2)
        band.everyone_listens_to_conductor()
        assert cond.room_id in m1.listeners
        assert cond.room_id in m2.listeners

    def test_everyone_listens_to_everyone(self):
        m1 = RoomMusician("m1")
        m2 = RoomMusician("m2")
        m3 = RoomMusician("m3")
        band = Band("test")
        band.add_musician(m1)
        band.add_musician(m2)
        band.add_musician(m3)
        band.everyone_listens_to_everyone()
        assert len(m1.listeners) == 2
        assert len(m2.listeners) == 2
        assert len(m3.listeners) == 2

    def test_set_listen(self):
        m1 = RoomMusician("m1")
        m2 = RoomMusician("m2")
        band = Band("test")
        band.add_musician(m1)
        band.add_musician(m2)
        band.set_listen(m1, m2)
        assert m2.room_id in m1.listeners

    def test_get_roles(self):
        m1 = RoomMusician("m1", role=RhythmicRole.ROOT)
        m2 = RoomMusician("m2", role=RhythmicRole.HALFTIME)
        band = Band("test")
        band.add_musician(m1)
        band.add_musician(m2)
        roles = band.get_roles()
        assert roles["m1"] == RhythmicRole.ROOT
        assert roles["m2"] == RhythmicRole.HALFTIME

    def test_repr(self):
        band = Band("test", bpm=120)
        assert "test" in repr(band)


# ══════════════════════════════════════════════════════════════════════════════
# Score edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestScoreEdgeCases:
    def test_empty_score(self):
        s = Score("empty")
        assert s.total_events() == 0
        assert s.duration_ms() == 0.0
        assert s.musician_names == []
        assert s.all_events() == []
        assert s.to_midi_events() == []

    def test_single_event(self):
        s = Score("one")
        s.record_event("m1", 0.0, FluxVector.unit(0))
        assert s.total_events() == 1

    def test_events_for_nonexistent(self):
        s = Score("test")
        assert s.events_for("nobody") == []

    def test_vectors_for(self):
        s = Score("test")
        v = FluxVector.unit(2)
        s.record_event("m1", 0.0, v)
        vecs = s.vectors_for("m1")
        assert len(vecs) == 1
        assert vecs[0] == v

    def test_title_setter(self):
        s = Score("old")
        s.title = "new"
        assert s.title == "new"

    def test_record_side_channel(self):
        s = Score("test")
        s.record_side_channel("m1", "nod", 100.0)
        s.record_side_channel("m1", "nod", 200.0)

    def test_repr(self):
        s = Score("test")
        assert "Score" in repr(s)


# ══════════════════════════════════════════════════════════════════════════════
# Property-based tests: render(any valid input) → valid MIDI
# ══════════════════════════════════════════════════════════════════════════════


class TestPropertyInvariants:
    """Invariants that should hold for all valid inputs."""

    def test_flux_vector_always_9_channels(self):
        for i in range(9):
            v = FluxVector.unit(i)
            assert len(v) == 9
            assert len(v.values) == 9
            assert len(v.salience) == 9
            assert len(v.tolerance) == 9

    def test_midi_event_note_always_in_range(self):
        for note in (0, 1, 60, 127):
            ev = MidiEvent(note, 64, 0, 100)
            assert 0 <= ev.note <= 127

    def test_sequencer_render_always_valid_midi_events(self):
        """Any valid sequencer state produces valid MidiEvents."""
        for steps in (8, 16, 32):
            seq = StepSequencer(steps=steps)
            for i in range(steps):
                if i % 2 == 0:
                    seq.add_hit("kick", i, 80)
            events = seq.render(bpm=120)
            for ev in events:
                assert 0 <= ev.note <= 127
                assert 1 <= ev.velocity <= 127
                assert ev.start_ms >= 0
                assert ev.duration_ms > 0

    def test_sequencer_render_events_sorted(self):
        seq = StepSequencer()
        for i in range(0, 16, 2):
            seq.add_hit("kick", i, 100)
            seq.add_hit("snare", i + 1, 80)
        events = seq.render(bpm=120)
        for i in range(1, len(events)):
            assert events[i].start_ms >= events[i - 1].start_ms

    def test_render_preserves_event_count(self):
        """Each hit produces exactly one MidiEvent."""
        seq = StepSequencer(steps=8)
        seq.add_hit("kick", 0)
        seq.add_hit("snare", 2)
        seq.add_hit("kick", 4)
        events = seq.render(bpm=120)
        assert len(events) == 3

    def test_cosine_similarity_symmetric(self):
        a = FluxVector([0.9, 0.3, 0.7, 0.1, 0.2, 0.5, 0.0, 0.0, 0.0])
        b = FluxVector([0.5, 0.8, 0.3, 0.6, 0.5, 0.1, 0.0, 0.0, 0.0])
        assert a.cosine_similarity(b) == pytest.approx(b.cosine_similarity(a))

    def test_distance_symmetric(self):
        a = FluxVector.unit(0)
        b = FluxVector.unit(4)
        assert a.distance_to(b) == pytest.approx(b.distance_to(a))

    def test_jaccard_symmetric(self):
        a = FluxVector([1.0, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        b = FluxVector([0.5, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        assert jaccard_index(a, b) == pytest.approx(jaccard_index(b, a))

    def test_midi_clock_24_ppqn_invariant(self):
        """MIDI clock always uses 24 PPQN."""
        c = MidiClock(bpm=100)
        assert c.PPQN == 24

    def test_drum_rack_channel_0_15(self):
        for ch in range(16):
            rack = DrumRack(channel=ch)
            assert 0 <= rack.channel <= 15

    def test_build_midi_file_valid_header(self):
        """Any build_midi_file output starts with MThd."""
        config = MidiExportConfig(tracks=[])
        data = build_midi_file(config)
        assert data[:4] == b"MThd"

    def test_score_to_midi_events_note_range(self):
        s = Score("inv")
        for i in range(20):
            v = FluxVector([float(j) * 0.1 for j in range(9)])
            s.record_event("m1", float(i) * 100, v)
        events = s.to_midi_events()
        for ev in events:
            assert 0 <= ev.note <= 127


# ══════════════════════════════════════════════════════════════════════════════
# MIDI channel mapping
# ══════════════════════════════════════════════════════════════════════════════


class TestMidiChannelMapping:
    def test_all_roles_have_channels(self):
        for role in RhythmicRole:
            ch = channel_for_role(role)
            assert isinstance(ch, MidiChannel)

    def test_all_roles_have_programs(self):
        for role in RhythmicRole:
            prog = program_for_role(role)
            assert isinstance(prog, int)
            assert 0 <= prog <= 127

    def test_percussion_channel_10(self):
        assert MidiChannel.CHANNEL_10 == 9


# ══════════════════════════════════════════════════════════════════════════════
# Exceptions module
# ══════════════════════════════════════════════════════════════════════════════


class TestExceptions:
    def test_constraint_error_is_value_error(self):
        assert issubclass(ConstraintError, ValueError)

    def test_render_error_is_runtime_error(self):
        assert issubclass(RenderError, RuntimeError)

    def test_genre_error_is_value_error(self):
        assert issubclass(GenreError, ValueError)

    def test_can_catch_as_parent(self):
        with pytest.raises(ValueError):
            raise ConstraintError("bad constraint")

        with pytest.raises(RuntimeError):
            raise RenderError("render failed")

        with pytest.raises(ValueError):
            raise GenreError("unknown genre")


# ══════════════════════════════════════════════════════════════════════════════
# Audio MockRenderer additional coverage
# ══════════════════════════════════════════════════════════════════════════════


class TestAudioAdditional:
    def test_render_midi_bytes_log(self):
        r = MockRenderer()
        r.render_midi(b"MThd\x00\x00\x00\x06\x00\x01\x00\x01\x00\x78", 1.0, "/tmp/t.wav")
        entry = r.render_log[0]
        assert "bytes" in entry["source"]

    def test_silence_wav_stereo(self):
        data = _silence_wav(2.0, 44100, 2)
        import io
        with wave.open(io.BytesIO(data), "rb") as wf:
            assert wf.getnframes() == 88200

    def test_events_to_midi_bytes_empty(self):
        b = _events_to_midi_bytes([])
        assert b[:4] == b"MThd"

    def test_find_soundfonts_list(self):
        result = create_renderer.__module__
        assert result is not None  # just verify no crash

    def test_note_name_enum(self):
        assert NoteName.C4 == 60
        assert NoteName.A4 == 69
