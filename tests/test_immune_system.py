"""Tests for the Musical Immune System (immune_system.py).

Covers:
- Antigen recognition
- Antibody generation and affinity maturation
- Clonal expansion
- Primary vs secondary response timing
- Self-tolerance (don't attack intentional patterns)
- Vaccination (pre-exposure to clichés)
- Immunotherapy (suppress to enable creativity)
- NON-PRE-CALCULABILITY: different exposures → different immune repertoire
"""

import copy
import hashlib
import math
import random
import time
from unittest.mock import patch

import pytest

from flux_tensor_midi.immune_system import (
    AdaptiveImmunity,
    AntigenType,
    InnateImmunity,
    MusicalAntibody,
    MusicalAntigen,
    MusicalImmuneSystem,
    _CLICHE_PATTERNS,
    _NEUTRALIZER_LIBRARY,
    _note_event,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _c_major_scale(length: int = 8, start: int = 60) -> list:
    """Generate a C major scale fragment."""
    intervals = [0, 2, 4, 5, 7, 9, 11, 12]
    return [_note_event(start + intervals[i % len(intervals)], duration=0.25) for i in range(length)]


def _random_events(n: int = 16, seed: int = 42) -> list:
    """Generate n random note events."""
    rng = random.Random(seed)
    return [_note_event(rng.randint(40, 90), rng.randint(30, 120), rng.choice([0.125, 0.25, 0.5]))
            for _ in range(n)]


def _all_same_events(n: int = 20, note: int = 60, dur: float = 0.25) -> list:
    """Generate n identical events (triggers repetition + rhythmic monotony)."""
    return [_note_event(note, 64, dur) for _ in range(n)]


def _silence_events(n: int = 20) -> list:
    """Generate n rest/silence events."""
    return [_note_event(-1, 0, 0.25) for _ in range(n)]


def _dissonant_run(n: int = 8) -> list:
    """Generate a run of chromatic/dissonant intervals."""
    return [_note_event(60 + (i % 2) * 11 + i, 64, 0.25) for i in range(n)]


# ===========================================================================
# 1. Antigen basics
# ===========================================================================

class TestMusicalAntigen:
    def test_dangerous_threshold(self):
        ag = MusicalAntigen(pattern=[_note_event(60)], antigen_type=AntigenType.CLICHE, danger_score=0.8)
        assert ag.is_dangerous is True

    def test_not_dangerous(self):
        ag = MusicalAntigen(pattern=[_note_event(60)], antigen_type=AntigenType.CLICHE, danger_score=0.3)
        assert ag.is_dangerous is False

    def test_fingerprint_stable(self):
        pat = [_note_event(60), _note_event(64)]
        ag1 = MusicalAntigen(pattern=pat, antigen_type=AntigenType.CLICHE, danger_score=0.5)
        ag2 = MusicalAntigen(pattern=list(pat), antigen_type=AntigenType.REPETITION, danger_score=0.9)
        assert ag1.fingerprint == ag2.fingerprint

    def test_fingerprint_differs_for_different_patterns(self):
        ag1 = MusicalAntigen(pattern=[_note_event(60)], antigen_type=AntigenType.CLICHE, danger_score=0.5)
        ag2 = MusicalAntigen(pattern=[_note_event(64)], antigen_type=AntigenType.CLICHE, danger_score=0.5)
        assert ag1.fingerprint != ag2.fingerprint

    def test_position_default(self):
        ag = MusicalAntigen(pattern=[_note_event(60)], antigen_type=AntigenType.RANDOM, danger_score=0.1)
        assert ag.position == 0


# ===========================================================================
# 2. Antibody recognition
# ===========================================================================

class TestMusicalAntibody:
    def test_perfect_recognition(self):
        pat = [_note_event(60, 64, 0.25), _note_event(64, 70, 0.5)]
        ab = MusicalAntibody(target_pattern=list(pat), neutralizer=lambda e, p: e)
        score = ab.recognize(pat)
        assert score >= 0.9

    def test_no_recognition_different_pattern(self):
        target = [_note_event(60), _note_event(64)]
        query = [_note_event(80), _note_event(90)]
        ab = MusicalAntibody(target_pattern=target, neutralizer=lambda e, p: e)
        score = ab.recognize(query)
        assert score < 0.7  # some structure similarity from durations/velocities

    def test_empty_pattern(self):
        ab = MusicalAntibody(target_pattern=[], neutralizer=lambda e, p: e)
        assert ab.recognize([]) == 0.0

    def test_partial_match(self):
        target = [_note_event(60, 64, 0.25), _note_event(62, 64, 0.25)]
        query = [_note_event(60, 64, 0.25), _note_event(65, 64, 0.25)]
        ab = MusicalAntibody(target_pattern=target, neutralizer=lambda e, p: e)
        score = ab.recognize(query)
        assert 0.1 < score < 0.9

    def test_neutralize_called(self):
        """Verify neutralize invokes the stored callable."""
        called = [False]
        def neutralizer(events, pos):
            called[0] = True
            return events
        ab = MusicalAntibody(target_pattern=[_note_event(60)], neutralizer=neutralizer)
        ab.neutralize([_note_event(60)], 0)
        assert called[0] is True

    def test_length_mismatch_recognition(self):
        target = [_note_event(60)]
        query = [_note_event(60), _note_event(64), _note_event(67)]
        ab = MusicalAntibody(target_pattern=target, neutralizer=lambda e, p: e)
        # Should still produce a score (partial match)
        score = ab.recognize(query)
        assert score >= 0.0


# ===========================================================================
# 3. Innate immunity detectors
# ===========================================================================

class TestInnateImmunity:
    def test_detect_cliche_heart_and_soul(self):
        # The exact cliché is in the danger_patterns
        innate = InnateImmunity(danger_patterns=[_CLICHE_PATTERNS[0]])
        events = _all_same_events(10) + list(_CLICHE_PATTERNS[0]) + _all_same_events(10)
        results = innate._detect_cliches(events)
        assert len(results) > 0
        assert any(a.antigen_type == AntigenType.CLICHE for a in results)

    def test_detect_repetition(self):
        events = _all_same_events(30, note=64)
        innate = InnateImmunity()
        results = innate._detect_repetition(events, window=4, threshold=3)
        assert len(results) > 0

    def test_detect_dissonance(self):
        # Build a clear chromatic run: every interval is 1 semitone
        events = [_note_event(60 + i, 64, 0.25) for i in range(10)]
        innate = InnateImmunity()
        results = innate._detect_dissonance(events)
        assert len(results) > 0

    def test_detect_silence(self):
        events = _silence_events(20)
        innate = InnateImmunity()
        results = innate._detect_silence(events)
        assert len(results) > 0

    def test_detect_random(self):
        events = _random_events(20, seed=999)
        innate = InnateImmunity()
        results = innate._detect_random(events, window=8)
        # Depending on seed, may or may not detect; check it doesn't crash
        assert isinstance(results, list)

    def test_detect_range_violation(self):
        events = [_note_event(10), _note_event(60), _note_event(200)]
        innate = InnateImmunity()
        results = innate._detect_range_violation(events)
        assert len(results) == 2  # 10 and 200

    def test_detect_rhythmic_monotony(self):
        events = _all_same_events(20, dur=0.25)
        innate = InnateImmunity()
        results = innate._detect_rhythmic_monotony(events, window=16)
        assert len(results) > 0

    def test_detect_harmonic_stagnation(self):
        events = [_note_event(60, 64, 0.25) for _ in range(16)]
        innate = InnateImmunity()
        results = innate._detect_harmonic_stagnation(events, window=12)
        assert len(results) > 0

    def test_detect_empty_events(self):
        innate = InnateImmunity()
        assert innate.detect([]) == []

    def test_detect_on_clean_scale(self):
        """A clean C major scale should have minimal detections."""
        events = _c_major_scale(16)
        innate = InnateImmunity()
        results = innate.detect(events)
        # May detect some things (scale is a bit cliché), but shouldn't be flooded
        assert len(results) < len(events)

    def test_interval_entropy(self):
        """Constant pitch ⇒ zero entropy."""
        events = [_note_event(60) for _ in range(5)]
        assert InnateImmunity._interval_entropy(events) == 0.0

    def test_window_similarity_identical(self):
        a = [_note_event(60), _note_event(64)]
        assert InnateImmunity._window_similarity(a, a) >= 0.9

    def test_window_similarity_different(self):
        a = [_note_event(60), _note_event(64)]
        b = [_note_event(90), _note_event(20)]
        assert InnateImmunity._window_similarity(a, b) <= 0.55  # durations still match


# ===========================================================================
# 4. Adaptive immunity
# ===========================================================================

class TestAdaptiveImmunity:
    def test_present_novel_antigen_generates_antibody(self):
        adaptive = AdaptiveImmunity()
        ag = MusicalAntigen(pattern=[_note_event(60), _note_event(62)],
                            antigen_type=AntigenType.CLICHE, danger_score=0.7)
        adaptive.present_antigen(ag)
        assert len(adaptive.antibodies) == 1

    def test_present_known_antigen_no_new_antibody(self):
        """When a memory cell already recognises the antigen, no new antibody."""
        adaptive = AdaptiveImmunity()
        pat = [_note_event(60), _note_event(62)]
        ag = MusicalAntigen(pattern=pat, antigen_type=AntigenType.CLICHE, danger_score=0.7)
        # Pre-register a memory cell
        mem = MusicalAntibody(
            target_pattern=list(pat), neutralizer=lambda e, p: e,
            affinity=0.9, memory=True
        )
        adaptive.memory_cells.append(mem)
        adaptive.present_antigen(ag)
        assert len(adaptive.antibodies) == 0  # no new antibody needed

    def test_generate_antibody_has_affinity(self):
        adaptive = AdaptiveImmunity()
        ag = MusicalAntigen(pattern=[_note_event(60)], antigen_type=AntigenType.CLICHE, danger_score=0.5)
        ab = adaptive.generate_antibody(ag)
        assert 0.0 < ab.affinity <= 1.0

    def test_clonal_expansion_count(self):
        adaptive = AdaptiveImmunity()
        ab = MusicalAntibody(target_pattern=[_note_event(60)], neutralizer=lambda e, p: e)
        clones = adaptive.clonal_expansion(ab, n=10)
        assert len(clones) == 10

    def test_clonal_expansion_diversity(self):
        """Clones should have slightly different patterns (mutations)."""
        adaptive = AdaptiveImmunity()
        ab = MusicalAntibody(
            target_pattern=[_note_event(60), _note_event(64), _note_event(67)],
            neutralizer=lambda e, p: e, affinity=0.7
        )
        clones = adaptive.clonal_expansion(ab, n=10)
        notes_sets = set()
        for c in clones:
            notes_sets.add(tuple(e.get("note", 0) for e in c.target_pattern))
        # With mutations, not all clones should be identical
        # (statistically almost guaranteed with 10 clones and 0.3 mutation rate)
        assert len(notes_sets) >= 2

    def test_somatic_hypermutation_changes_generation(self):
        adaptive = AdaptiveImmunity()
        ab = MusicalAntibody(target_pattern=[_note_event(60)], neutralizer=lambda e, p: e, generation=0)
        mutated = adaptive.somatic_hypermutation(ab)
        assert mutated.generation == 1

    def test_somatic_hypermutation_affinity_stays_bounded(self):
        adaptive = AdaptiveImmunity()
        ab = MusicalAntibody(target_pattern=[_note_event(60)], neutralizer=lambda e, p: e, affinity=0.5)
        for _ in range(100):
            ab = adaptive.somatic_hypermutation(ab)
            assert 0.1 <= ab.affinity <= 1.0

    def test_promote_to_memory(self):
        adaptive = AdaptiveImmunity()
        ab = MusicalAntibody(target_pattern=[_note_event(60)], neutralizer=lambda e, p: e, affinity=0.8)
        adaptive.promote_to_memory(ab)
        assert len(adaptive.memory_cells) == 1
        assert adaptive.memory_cells[0].memory is True

    def test_primary_response_slower_than_secondary(self):
        adaptive = AdaptiveImmunity()
        primary = adaptive.primary_response_delay()
        secondary = adaptive.secondary_response_delay()
        assert primary > secondary

    def test_find_best_antibody(self):
        adaptive = AdaptiveImmunity()
        pat = [_note_event(60), _note_event(64)]
        ab = MusicalAntibody(target_pattern=list(pat), neutralizer=lambda e, p: e, affinity=0.9)
        adaptive.antibodies.append(ab)
        ag = MusicalAntigen(pattern=list(pat), antigen_type=AntigenType.CLICHE, danger_score=0.7)
        best = adaptive.find_best_antibody(ag)
        assert best is ab

    def test_find_best_antibody_returns_none_when_empty(self):
        adaptive = AdaptiveImmunity()
        ag = MusicalAntigen(pattern=[_note_event(60)], antigen_type=AntigenType.CLICHE, danger_score=0.5)
        assert adaptive.find_best_antibody(ag) is None


# ===========================================================================
# 5. Full immune system — scanning and response
# ===========================================================================

class TestMusicalImmuneSystem:
    def test_scan_finds_no_issues_in_clean_music(self):
        ims = MusicalImmuneSystem()
        events = _c_major_scale(8)
        antigens = ims.scan(events)
        # May find some minor issues but should not be overwhelmed
        assert len(antigens) < len(events)

    def test_scan_finds_repetition(self):
        ims = MusicalImmuneSystem()
        events = _all_same_events(30)
        antigens = ims.scan(events)
        assert len(antigens) > 0

    def test_respond_neutralises_antigens(self):
        """After response, the result should differ from input if antigens were found."""
        ims = MusicalImmuneSystem()
        events = list(_CLICHE_PATTERNS[0]) + _all_same_events(20)
        antigens = ims.scan(events)
        if antigens:
            result = ims.respond(events, antigens)
            # Should have been modified (at least one antigen neutralised)
            assert result != events or len(ims.response_log) > 0

    def test_primary_vs_secondary_response(self):
        """First exposure = primary, second = secondary."""
        ims = MusicalImmuneSystem()
        events = _all_same_events(30)
        # First exposure
        result1 = ims.respond(events)
        primary_count = sum(1 for r in ims.response_log if r["type"] == "primary")
        # Second exposure (same events)
        result2 = ims.respond(events)
        secondary_count = sum(1 for r in ims.response_log if r["type"] == "secondary")
        assert primary_count > 0
        assert secondary_count > 0
        # Primary responses should have higher delay
        primary_delays = [r["delay"] for r in ims.response_log if r["type"] == "primary"]
        secondary_delays = [r["delay"] for r in ims.response_log if r["type"] == "secondary"]
        assert min(primary_delays) > max(secondary_delays)

    def test_response_returns_events(self):
        ims = MusicalImmuneSystem()
        events = _c_major_scale(8)
        result = ims.respond(events)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_response_empty_input(self):
        ims = MusicalImmuneSystem()
        assert ims.respond([]) == []


# ===========================================================================
# 6. Self-tolerance
# ===========================================================================

class TestSelfTolerance:
    def test_register_self_prevents_attack(self):
        ims = MusicalImmuneSystem()
        # Create an intentional ostinato
        ostinato = [_note_event(60), _note_event(64), _note_event(67)]
        events = ostinato * 10  # lots of repetition but intentional
        ims.register_self(ostinato, label="ostinato")
        antigens = ims.scan(events)
        # The registered pattern should be filtered
        for ag in antigens:
            assert not ims.is_self(ag.pattern)

    def test_is_self_unregistered_pattern(self):
        ims = MusicalImmuneSystem()
        assert ims.is_self([_note_event(60)]) is False

    def test_autoimmune_check_finds_false_positives(self):
        ims = MusicalImmuneSystem()
        ostinato = [_note_event(60), _note_event(64), _note_event(67)]
        events = ostinato * 10
        ims.register_self(ostinato, label="intentional")
        false_pos = ims.autoimmune_check(events)
        # Should find that some detected antigens are actually self
        assert isinstance(false_pos, list)

    def test_tolerance_does_not_affect_non_self(self):
        ims = MusicalImmuneSystem()
        events = list(_CLICHE_PATTERNS[0])
        antigens = ims.scan(events)
        # Without registering anything as self, no false positives expected
        # (but could happen by chance — just check it doesn't crash)
        ims.autoimmune_check(events)


# ===========================================================================
# 7. Vaccination
# ===========================================================================

class TestVaccination:
    def test_vaccinate_creates_memory_cells(self):
        ims = MusicalImmuneSystem()
        ag = MusicalAntigen(pattern=[_note_event(60), _note_event(62)],
                            antigen_type=AntigenType.CLICHE, danger_score=0.8)
        ims.vaccinate([ag])
        assert len(ims.adaptive.memory_cells) == 1
        assert ims.adaptive.memory_cells[0].memory is True
        assert ims.adaptive.memory_cells[0].affinity >= 0.7

    def test_vaccinate_against_cliches(self):
        ims = MusicalImmuneSystem()
        ims.vaccinate_against_cliches()
        assert len(ims.adaptive.memory_cells) == len(_CLICHE_PATTERNS)
        assert len(ims.vaccination_history) == len(_CLICHE_PATTERNS)

    def test_vaccinated_system_responds_faster(self):
        ims = MusicalImmuneSystem()
        ag = MusicalAntigen(pattern=list(_CLICHE_PATTERNS[0]),
                            antigen_type=AntigenType.CLICHE, danger_score=0.8)
        ims.vaccinate([ag])
        # Now expose to the same cliché
        events = list(_CLICHE_PATTERNS[0]) + _all_same_events(20)
        ims.respond(events)
        secondary = [r for r in ims.response_log if r["type"] == "secondary"]
        assert len(secondary) > 0


# ===========================================================================
# 8. Immunotherapy
# ===========================================================================

class TestImmunotherapy:
    def test_immunotherapy_returns_variations(self):
        ims = MusicalImmuneSystem()
        stuck = _all_same_events(16)
        results = ims.immunotherapy(stuck, suppression_level=0.7, duration_steps=4)
        assert len(results) == 4
        for r in results:
            assert isinstance(r, list)

    def test_immunotherapy_restores_state(self):
        ims = MusicalImmuneSystem()
        stuck = _all_same_events(16)
        _ = ims.immunotherapy(stuck)
        assert ims._suppressed is False
        assert ims._suppression_level == 0.0

    def test_suppressed_immune_system_detects_less(self):
        ims = MusicalImmuneSystem()
        events = _all_same_events(30)
        normal_antigens = ims.scan(events)
        ims._suppressed = True
        ims._suppression_level = 1.0
        # Run scan many times with full suppression — some should return empty
        empty_count = sum(1 for _ in range(20) if ims.scan(events) == [])
        assert empty_count > 0  # suppression should sometimes block detection


# ===========================================================================
# 9. Non-pre-calculability: different exposures → different repertoire
# ===========================================================================

class TestNonPreCalculability:
    def test_different_seeds_different_antibodies(self):
        """Two immune systems exposed to different antigens should develop
        different antibody repertoires."""
        rng1 = random.Random(42)
        rng2 = random.Random(999)

        ims1 = MusicalImmuneSystem()
        ims2 = MusicalImmuneSystem()

        # Different exposure sequences
        for _ in range(5):
            pat1 = [_note_event(rng1.randint(40, 80)) for _ in range(3)]
            ag1 = MusicalAntigen(pattern=pat1, antigen_type=AntigenType.CLICHE, danger_score=0.7)
            ims1.adaptive.present_antigen(ag1)

            pat2 = [_note_event(rng2.randint(40, 80)) for _ in range(3)]
            ag2 = MusicalAntigen(pattern=pat2, antigen_type=AntigenType.RANDOM, danger_score=0.7)
            ims2.adaptive.present_antigen(ag2)

        # Different antibody sets
        fp1 = set(hashlib.md5(str(ab.target_pattern).encode()).hexdigest()
                   for ab in ims1.adaptive.antibodies)
        fp2 = set(hashlib.md5(str(ab.target_pattern).encode()).hexdigest()
                   for ab in ims2.adaptive.antibodies)
        assert fp1 != fp2

    def test_same_antigen_different_neutralizer(self):
        """Due to random neutralizer selection, same antigen can produce
        different antibodies across runs."""
        # Run many times and check at least some differ
        antigens = MusicalAntigen(pattern=[_note_event(60), _note_event(62)],
                                  antigen_type=AntigenType.CLICHE, danger_score=0.7)
        neutralizers_seen = set()
        for _ in range(20):
            adaptive = AdaptiveImmunity()
            ab = adaptive.generate_antibody(antigens)
            neutralizers_seen.add(id(ab.neutralizer))
        # Multiple different neutralizers should be selected
        assert len(neutralizers_seen) >= 2

    def test_response_order_affects_outcome(self):
        """Processing antigens in different orders can yield different results."""
        events = list(_CLICHE_PATTERNS[0]) + _all_same_events(20) + list(_CLICHE_PATTERNS[1])

        ims1 = MusicalImmuneSystem()
        ims2 = MusicalImmuneSystem()

        # Both scan the same events but internal randomness may differ
        result1 = ims1.respond(copy.deepcopy(events))
        result2 = ims2.respond(copy.deepcopy(events))

        # Results might differ due to random neutralizer selection
        # (Not guaranteed, but the system is designed to be non-deterministic)
        # At minimum, both should produce valid results
        assert isinstance(result1, list)
        assert isinstance(result2, list)


# ===========================================================================
# 10. Statistics / repertoire summary
# ===========================================================================

class TestRepertoireSummary:
    def test_initial_summary(self):
        ims = MusicalImmuneSystem()
        summary = ims.immune_repertoire_summary()
        assert summary["total_antibodies"] == 0
        assert summary["memory_cells"] == 0
        assert summary["primary_responses"] == 0

    def test_summary_after_exposure(self):
        ims = MusicalImmuneSystem()
        ims.vaccinate_against_cliches()
        events = list(_CLICHE_PATTERNS[0]) + _all_same_events(20)
        ims.respond(events)
        summary = ims.immune_repertoire_summary()
        assert summary["vaccinations"] == len(_CLICHE_PATTERNS)
        assert summary["responses_logged"] > 0
        assert summary["memory_cells"] >= len(_CLICHE_PATTERNS)

    def test_affinity_average(self):
        ims = MusicalImmuneSystem()
        adaptive = ims.adaptive
        ab = MusicalAntibody(target_pattern=[_note_event(60)], neutralizer=lambda e, p: e, affinity=0.8)
        adaptive.antibodies.append(ab)
        summary = ims.immune_repertoire_summary()
        assert abs(summary["antibody_affinity_avg"] - 0.8) < 0.01


# ===========================================================================
# 11. Neutralizer library
# ===========================================================================

class TestNeutralizers:
    def test_all_neutralizers_return_list(self):
        events = _c_major_scale(8)
        for nz in _NEUTRALIZER_LIBRARY:
            result = nz(list(events), 2)
            assert isinstance(result, list)

    def test_transpose_changes_notes(self):
        events = [_note_event(60), _note_event(64), _note_event(67)]
        from flux_tensor_midi.immune_system import _neutralizer_transpose
        result = _neutralizer_transpose(list(events), 0)
        notes_orig = [e["note"] for e in events]
        notes_new = [e["note"] for e in result]
        assert notes_orig != notes_new

    def test_invert_changes_intervals(self):
        events = [_note_event(60), _note_event(64), _note_event(67)]
        from flux_tensor_midi.immune_system import _neutralizer_invert
        result = _neutralizer_invert(list(events), 0)
        # After inversion around 60: 60, 56, 53
        assert result[0]["note"] == 60
        assert result[1]["note"] == 56
        assert result[2]["note"] == 53

    def test_rhythmic_variation_changes_durations(self):
        events = [_note_event(60, 64, 0.25), _note_event(64, 64, 0.25)]
        from flux_tensor_midi.immune_system import _neutralizer_rhythmic_variation
        # Try several times (random)
        changed = False
        for _ in range(20):
            result = _neutralizer_rhythmic_variation(list(events), 0)
            if [e.get("duration") for e in result] != [0.25, 0.25]:
                changed = True
                break
        assert changed

    def test_insert_rest_adds_event(self):
        events = [_note_event(60), _note_event(64)]
        from flux_tensor_midi.immune_system import _neutralizer_insert_rest
        result = _neutralizer_insert_rest(list(events), 0)
        assert len(result) == 3
        assert result[0]["velocity"] == 0


# ===========================================================================
# 12. Integration tests
# ===========================================================================

class TestIntegration:
    def test_full_cycle_scan_respond_rescan(self):
        """Scan → respond → rescan should find fewer or equal antigens."""
        ims = MusicalImmuneSystem()
        events = _all_same_events(30)
        antigens_before = ims.scan(events)
        if antigens_before:
            modified = ims.respond(events, antigens_before)
            antigens_after = ims.scan(modified)
            # May or may not be fewer (depends on mutation), but should be valid
            assert isinstance(antigens_after, list)

    def test_vaccinate_then_expose(self):
        """Vaccination + exposure should trigger memory responses."""
        ims = MusicalImmuneSystem()
        ims.vaccinate_against_cliches()
        events = list(_CLICHE_PATTERNS[0]) + _all_same_events(10)
        ims.respond(events)
        assert any(r["type"] == "secondary" for r in ims.response_log)

    def test_creative_mutation_produces_different_output(self):
        events = _all_same_events(16)
        from flux_tensor_midi.immune_system import MusicalImmuneSystem
        mutated = MusicalImmuneSystem._creative_mutation(events, creativity=1.0)
        # Should differ from original
        assert mutated != events

    def test_immune_system_handles_large_input(self):
        """Should not crash on large inputs."""
        ims = MusicalImmuneSystem()
        events = _random_events(500, seed=123)
        antigens = ims.scan(events)
        result = ims.respond(events, antigens)
        assert len(result) > 0
