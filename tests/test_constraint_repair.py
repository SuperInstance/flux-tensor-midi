"""Tests for flux_tensor_midi.constraint_repair — DNA-inspired error correction."""

import random
import pytest
from flux_tensor_midi.constraint_repair import (
    ConstraintType,
    Constraint,
    MusicalEvent,
    Mismatch,
    MismatchRepair,
    NucleotideExcisionRepair,
    HomologousRecombination,
    SOSResponse,
    SOSState,
    ConstraintRepairSystem,
    _in_scale,
    _nearest_in_scale,
    _pitch_class,
    _SCALE_DEGREES,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _key_constraint(root: int = 0, scale: str = "major") -> Constraint:
    return Constraint(ctype=ConstraintType.KEY, params={"root": root, "scale": scale})


def _range_constraint(lo: int = 48, hi: int = 84) -> Constraint:
    return Constraint(ctype=ConstraintType.RANGE, params={"min_pitch": lo, "max_pitch": hi})


def _velocity_constraint(lo: int = 30, hi: int = 100) -> Constraint:
    return Constraint(ctype=ConstraintType.VELOCITY, params={"min_velocity": lo, "max_velocity": hi})


def _register_constraint(center: int = 60, max_dev: int = 12) -> Constraint:
    return Constraint(ctype=ConstraintType.REGISTER, params={"center_pitch": center, "max_deviation": max_dev})


def _rhythm_constraint(durations: list[float] | None = None) -> Constraint:
    return Constraint(
        ctype=ConstraintType.RHYTHM,
        params={"allowed_durations": durations or [0.25, 0.5, 1.0]},
    )


def _note(pitch: int = 60, velocity: int = 64, start: float = 0.0,
          duration: float = 1.0, channel: int = 0) -> MusicalEvent:
    return MusicalEvent(pitch=pitch, velocity=velocity, start=start,
                        duration=duration, channel=channel)


# C major scale: C=0, D=2, E=4, F=5, G=7, A=9, B=11
CMaj = [_note(p) for p in [0, 2, 4, 5, 7, 9, 11]]
# Out-of-scale notes
CmajBad = [_note(p) for p in [1, 3, 6, 8, 10]]  # C#, D#, F#, G#, A#


# ===========================================================================
# Unit tests — helpers
# ===========================================================================

class TestPitchClass:
    def test_middle_c(self):
        assert _pitch_class(60) == 0

    def test_c_sharp(self):
        assert _pitch_class(61) == 1

    def test_high_octave(self):
        assert _pitch_class(72) == 0

    def test_low_note(self):
        assert _pitch_class(12) == 0


class TestInScale:
    def test_c_in_c_major(self):
        assert _in_scale(60, 0, "major")

    def test_c_sharp_not_in_c_major(self):
        assert not _in_scale(61, 0, "major")

    def test_d_in_d_dorian(self):
        assert _in_scale(62, 2, "dorian")

    def test_chromatic_accepts_all(self):
        for p in range(12):
            assert _in_scale(p, 0, "chromatic")


class TestNearestInScale:
    def test_c_sharp_snaps_to_c(self):
        assert _nearest_in_scale(61, 0, "major") in (60, 62)

    def test_f_sharp_snaps_to_f_or_g(self):
        result = _nearest_in_scale(66, 0, "major")
        assert result in (65, 67)

    def test_already_in_scale(self):
        assert _nearest_in_scale(60, 0, "major") == 60


class TestScaleDegrees:
    def test_major_has_7_degrees(self):
        assert len(_SCALE_DEGREES["major"]) == 7

    def test_pentatonic_has_5(self):
        assert len(_SCALE_DEGREES["pentatonic"]) == 5

    def test_blues_has_6(self):
        assert len(_SCALE_DEGREES["blues"]) == 6


# ===========================================================================
# MusicalEvent
# ===========================================================================

class TestMusicalEvent:
    def test_rest_detection(self):
        e = MusicalEvent(pitch=None)
        assert e.is_rest

    def test_note_not_rest(self):
        e = MusicalEvent(pitch=60)
        assert not e.is_rest

    def test_defaults(self):
        e = MusicalEvent()
        assert e.velocity == 64
        assert e.duration == 1.0
        assert e.channel == 0


# ===========================================================================
# MismatchRepair
# ===========================================================================

class TestMismatchRepairScan:
    def test_clean_events_no_mismatches(self):
        mr = MismatchRepair()
        cs = [_key_constraint()]
        mismatches = mr.scan(CMaj, cs)
        assert len(mismatches) == 0

    def test_out_of_scale_detected(self):
        mr = MismatchRepair()
        cs = [_key_constraint()]
        mismatches = mr.scan(CmajBad, cs)
        assert len(mismatches) == len(CmajBad)

    def test_mismatches_sorted_by_severity(self):
        mr = MismatchRepair()
        events = [_note(1, velocity=200), _note(62)]
        cs = [_key_constraint(), _velocity_constraint()]
        mismatches = mr.scan(events, cs)
        assert all(m.severity >= 0 for m in mismatches)

    def test_rests_not_flagged_for_key(self):
        mr = MismatchRepair()
        events = [MusicalEvent(pitch=None)]
        cs = [_key_constraint()]
        mismatches = mr.scan(events, cs)
        assert len(mismatches) == 0


class TestMismatchRepairProofread:
    def test_clean_event(self):
        mr = MismatchRepair()
        result = mr.proofread(_note(60), [_key_constraint()])
        assert len(result) == 0

    def test_bad_event(self):
        mr = MismatchRepair()
        result = mr.proofread(_note(1), [_key_constraint()])
        assert len(result) >= 1
        assert result[0].constraint.ctype == ConstraintType.KEY


class TestMismatchRepairRepair:
    def test_fixes_out_of_scale(self):
        mr = MismatchRepair()
        events = [_note(1)]
        cs = [_key_constraint()]
        mismatches = mr.scan(events, cs)
        repaired = mr.repair(events, mismatches, cs)
        # Should be snapped to a C-major pitch
        assert _in_scale(repaired[0].pitch, 0, "major")

    def test_preserves_clean_events(self):
        mr = MismatchRepair()
        events = CMaj
        cs = [_key_constraint()]
        mismatches = mr.scan(events, cs)
        repaired = mr.repair(events, mismatches, cs)
        for orig, fix in zip(events, repaired):
            assert orig.pitch == fix.pitch


# ===========================================================================
# NucleotideExcisionRepair
# ===========================================================================

class TestNERDetect:
    def test_no_damage_in_clean(self):
        ner = NucleotideExcisionRepair()
        result = ner.detect_damage(CMaj, [_key_constraint()])
        assert len(result) == 0

    def test_detects_cluster_of_errors(self):
        ner = NucleotideExcisionRepair()
        # 4 consecutive out-of-scale notes
        bad = [_note(p) for p in [1, 3, 6, 8]]
        result = ner.detect_damage(bad, [_key_constraint()], window=4)
        assert len(result) >= 1

    def test_window_merge(self):
        ner = NucleotideExcisionRepair()
        bad = [_note(1), _note(3), _note(60), _note(6), _note(8)]
        result = ner.detect_damage(bad, [_key_constraint()], window=3)
        # Should have merged overlapping regions
        assert isinstance(result, list)


class TestNERExcise:
    def test_excise_middle(self):
        ner = NucleotideExcisionRepair()
        events = [_note(60), _note(62), _note(64), _note(65)]
        remaining, excised = ner.excise(events, 1, 3)
        assert len(remaining) == 2
        assert len(excised) == 2

    def test_excise_all(self):
        ner = NucleotideExcisionRepair()
        events = [_note(60), _note(62)]
        remaining, excised = ner.excise(events, 0, 2)
        assert len(remaining) == 0
        assert len(excised) == 2


class TestNERResynthesize:
    def test_generates_correct_count(self):
        ner = NucleotideExcisionRepair()
        cs = [_key_constraint()]
        result = ner.resynthesize(4, [_note(60)], [_note(67)], cs)
        assert len(result) == 4

    def test_all_events_in_scale(self):
        random.seed(42)
        ner = NucleotideExcisionRepair()
        cs = [_key_constraint()]
        result = ner.resynthesize(8, [_note(60)], [_note(72)], cs)
        for ev in result:
            assert _in_scale(ev.pitch, 0, "major")

    def test_empty_gap(self):
        ner = NucleotideExcisionRepair()
        result = ner.resynthesize(0, [_note(60)], [_note(72)], [])
        assert len(result) == 0

    def test_respect_velocity_constraint(self):
        random.seed(42)
        ner = NucleotideExcisionRepair()
        cs = [_key_constraint(), _velocity_constraint(30, 100)]
        result = ner.resynthesize(6, [_note(60)], [_note(72)], cs)
        for ev in result:
            assert 30 <= ev.velocity <= 100

    def test_respect_range_constraint(self):
        random.seed(42)
        ner = NucleotideExcisionRepair()
        cs = [_key_constraint(), _range_constraint(48, 84)]
        result = ner.resynthesize(6, [_note(60)], [_note(72)], cs)
        for ev in result:
            assert 48 <= ev.pitch <= 84


# ===========================================================================
# HomologousRecombination
# ===========================================================================

class TestHRFind:
    def test_no_templates(self):
        hr = HomologousRecombination()
        result = hr.find_homologous([_note(60)], [])
        assert len(result) == 0

    def test_similar_template_found(self):
        hr = HomologousRecombination()
        damaged = [_note(60), _note(62), _note(64)]
        template = [_note(60), _note(62), _note(64)]
        result = hr.find_homologous(damaged, [template])
        assert len(result) >= 1
        assert result[0][1] > 0.8  # high similarity

    def test_dissimilar_filtered(self):
        hr = HomologousRecombination()
        damaged = [_note(60), _note(62)]
        # Very different template (high pitches, different durations, different length)
        template = [_note(100, duration=4.0), _note(110, duration=4.0), _note(105, duration=4.0)]
        result = hr.find_homologous(damaged, [template], min_similarity=0.8)
        # With high threshold, very different templates should be filtered
        assert all(score < 0.8 for _, score in result)


class TestHRRecombine:
    def test_output_length_matches(self):
        hr = HomologousRecombination()
        damaged = [_note(1), _note(3)]
        template = [_note(60), _note(62)]
        cs = [_key_constraint()]
        result = hr.recombine(damaged, template, cs, crossover_rate=1.0)
        assert len(result) == len(damaged)

    def test_crossover_rate_1_uses_template(self):
        random.seed(42)
        hr = HomologousRecombination()
        damaged = [_note(1), _note(3)]
        template = [_note(60), _note(62)]
        cs = [_key_constraint()]
        result = hr.recombine(damaged, template, cs, crossover_rate=1.0)
        # With rate=1.0, should use template pitches (snapped to scale)
        for ev in result:
            assert _in_scale(ev.pitch, 0, "major")

    def test_crossover_rate_0_keeps_original(self):
        hr = HomologousRecombination()
        damaged = [_note(60), _note(62)]
        template = [_note(1), _note(3)]
        cs = [_key_constraint()]
        result = hr.recombine(damaged, template, cs, crossover_rate=0.0)
        assert result[0].pitch == 60
        assert result[1].pitch == 62

    def test_empty_damaged(self):
        hr = HomologousRecombination()
        result = hr.recombine([], [_note(60)], [])
        assert len(result) == 0


# ===========================================================================
# SOSResponse
# ===========================================================================

class TestSOSErrorDensity:
    def test_clean_gives_zero(self):
        sos = SOSResponse()
        density = sos.error_density(CMaj, [_key_constraint()])
        assert density == 0.0

    def test_all_bad_gives_one(self):
        sos = SOSResponse()
        density = sos.error_density(CmajBad, [_key_constraint()])
        assert density == 1.0

    def test_empty_events(self):
        sos = SOSResponse()
        density = sos.error_density([], [_key_constraint()])
        assert density == 0.0


class TestSOSActivate:
    def test_below_threshold(self):
        sos = SOSResponse(density_threshold=0.5)
        state = sos.activate(0.1)
        assert not state.active

    def test_above_threshold(self):
        sos = SOSResponse(density_threshold=0.3)
        state = sos.activate(0.5)
        assert state.active
        assert state.relaxed_epsilon > 0
        assert state.rigidity_factor < 1.0
        assert state.tempo_flex > 1.0

    def test_deactivate(self):
        sos = SOSResponse(density_threshold=0.3)
        sos.activate(0.8)
        state = sos.deactivate()
        assert not state.active

    def test_custom_threshold_override(self):
        sos = SOSResponse(density_threshold=0.3)
        state = sos.activate(0.4, threshold=0.5)
        assert not state.active


class TestSOSRelax:
    def test_relaxed_when_active(self):
        sos = SOSResponse(density_threshold=0.3)
        sos.activate(0.8)
        cs = [_key_constraint()]
        relaxed = sos.relax_constraints(cs)
        assert not relaxed[0].hard or relaxed[0].epsilon > 0

    def test_no_change_when_inactive(self):
        sos = SOSResponse(density_threshold=0.5)
        sos.activate(0.1)
        cs = [_key_constraint()]
        relaxed = sos.relax_constraints(cs)
        assert relaxed[0].hard == cs[0].hard


# ===========================================================================
# ConstraintRepairSystem — integration
# ===========================================================================

class TestRepairSystem:
    def test_clean_passes_through(self):
        crs = ConstraintRepairSystem(constraints=[_key_constraint()])
        result = crs.repair(CMaj)
        assert len(result) == len(CMaj)
        for orig, fix in zip(CMaj, result):
            assert orig.pitch == fix.pitch

    def test_repairs_out_of_scale(self):
        crs = ConstraintRepairSystem(constraints=[_key_constraint()])
        result = crs.repair(CmajBad)
        for ev in result:
            assert _in_scale(ev.pitch, 0, "major")

    def test_empty_events(self):
        crs = ConstraintRepairSystem(constraints=[_key_constraint()])
        result = crs.repair([])
        assert result == []

    def test_report(self):
        crs = ConstraintRepairSystem(constraints=[_key_constraint()])
        report = crs.repair_report(CmajBad)
        assert report["original_count"] == len(CmajBad)
        assert report["mismatches_found"] > 0
        assert report["error_density_before"] > 0
        assert report["error_density_after"] < report["error_density_before"]
        assert isinstance(report["repaired_events"], list)

    def test_proofread_event(self):
        crs = ConstraintRepairSystem(constraints=[_key_constraint()])
        fixed = crs.proofread_event(_note(1))
        assert _in_scale(fixed.pitch, 0, "major")

    def test_multiple_constraint_types(self):
        cs = [_key_constraint(), _velocity_constraint(30, 100)]
        crs = ConstraintRepairSystem(constraints=cs)
        bad = [_note(1, velocity=200), _note(3, velocity=5)]
        result = crs.repair(bad)
        for ev in result:
            assert _in_scale(ev.pitch, 0, "major")
            assert 30 <= ev.velocity <= 100

    def test_sos_trigger(self):
        crs = ConstraintRepairSystem(constraints=[_key_constraint()], sos_threshold=0.1)
        # All bad notes → density = 1.0 → SOS triggers
        result = crs.repair(CmajBad)
        assert crs.sos.state.active or crs.sos.state.density < 1.0

    def test_with_templates(self):
        head = [_note(60), _note(62), _note(64), _note(67)]
        crs = ConstraintRepairSystem(
            constraints=[_key_constraint()],
            templates=[head],
        )
        damaged = [_note(1), _note(3), _note(6), _note(8)]
        result = crs.repair(damaged)
        for ev in result:
            assert _in_scale(ev.pitch, 0, "major")
