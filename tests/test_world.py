"""Tests for flux_tensor_midi.world — scales, tuning, ornaments, rhythms."""

import math
import pytest

from flux_tensor_midi.world.scales import WORLD_SCALES, get_scale, list_scales, scale_to_midi
from flux_tensor_midi.world.tuning_systems import (
    equal_temperament,
    just_intonation,
    shruti_22,
    quarter_tone_24,
    pentatonic_5,
    meantone,
    pythagorean,
    snap_to_tuning,
)
from flux_tensor_midi.world.ornaments import (
    meend,
    gamak,
    quarter_bend,
    grace_note,
    murki,
    shakes,
)
from flux_tensor_midi.world.rhythms import clave, bell_pattern, tala, iqa, swing_ratio


# ── Scales ─────────────────────────────────────────────────────────────────

class TestScales:
    def test_world_scales_not_empty(self):
        assert len(WORLD_SCALES) > 0

    def test_get_scale_known(self):
        s = get_scale("bhairavi")
        assert "notes" in s
        assert s["culture"] == "indian"

    def test_get_scale_case_insensitive(self):
        assert get_scale("Bhairavi") == get_scale("bhairavi")

    def test_get_scale_hyphen_and_space(self):
        assert get_scale("gong-mode") == get_scale("gong_mode")
        assert get_scale("gong mode") == get_scale("gong_mode")

    def test_get_scale_unknown_raises(self):
        with pytest.raises(KeyError):
            get_scale("nonexistent_scale")

    def test_list_scales_all(self):
        names = list_scales()
        assert "bhairavi" in names
        assert "rast" in names
        assert "in_scale" in names

    def test_list_scales_culture_filter(self):
        indian = list_scales("indian")
        assert all(WORLD_SCALES[n]["culture"] == "indian" for n in indian)
        assert len(indian) >= 10

    def test_list_scales_arabic(self):
        arabic = list_scales("arabic")
        assert len(arabic) >= 10

    def test_list_scales_japanese(self):
        jp = list_scales("japanese")
        assert len(jp) >= 4

    def test_list_scales_african_returns_results(self):
        # Various african cultures
        results = list_scales("ewe") + list_scales("shona") + list_scales("manden")
        assert len(results) >= 3

    def test_scale_notes_in_octave(self):
        for name, data in WORLD_SCALES.items():
            for n in data["notes"]:
                assert 0 <= n <= 11, f"{name}: note {n} out of range"

    def test_indian_ragas_have_shruti(self):
        for name in list_scales("indian"):
            assert "shruti" in WORLD_SCALES[name]

    def test_scale_to_midi_basic(self):
        midi = scale_to_midi("bilawal", root=60, octave_range=1)
        assert midi[0] == 60
        assert midi[-1] <= 72

    def test_scale_to_midi_multi_octave(self):
        midi = scale_to_midi("yaman", root=60, octave_range=2)
        assert midi[-1] >= 72

    def test_scale_to_midi_valid_range(self):
        for name in list_scales():
            midi = scale_to_midi(name, root=60, octave_range=2)
            for note in midi:
                assert 0 <= note <= 127

    def test_scale_to_midi_unique_notes(self):
        midi = scale_to_midi("bhairavi", root=60, octave_range=2)
        assert len(midi) == len(set(midi))

    def test_all_ten_indian_ragas(self):
        indian = list_scales("indian")
        assert len(indian) >= 10

    def test_all_ten_arabic_maqamat(self):
        arabic = list_scales("arabic")
        assert len(arabic) >= 10

    def test_east_asian_scales_present(self):
        for name in ("in_scale", "yo_scale", "gong_mode"):
            assert name in WORLD_SCALES

    def test_chinese_five_elements(self):
        elements = {WORLD_SCALES[n].get("element") for n in list_scales("chinese")}
        for e in ("earth", "metal", "wood", "fire", "water"):
            assert e in elements


# ── Tuning Systems ─────────────────────────────────────────────────────────

class TestTuningSystems:
    def test_equal_temperament_12(self):
        tet = equal_temperament(12)
        assert len(tet) == 12
        assert tet[0] == 0.0
        assert abs(tet[-1] - 1100.0) < 0.01  # 11 * 100
        for i in range(11):
            assert abs(tet[i + 1] - tet[i] - 100.0) < 0.01

    def test_equal_temperament_24(self):
        tet24 = equal_temperament(24)
        assert len(tet24) == 24
        assert abs(tet24[1] - 50.0) < 0.01

    def test_just_intonation_12_notes(self):
        ji = just_intonation()
        assert len(ji) == 12
        assert ji[0] == 0.0
        assert abs(ji[-1] - 1088.27) < 1  # 15/8

    def test_shruti_22(self):
        s22 = shruti_22()
        assert len(s22) == 22
        assert s22[0] == 0.0
        assert s22[-1] < 1200.0

    def test_quarter_tone_24(self):
        qt = quarter_tone_24()
        assert len(qt) == 24
        assert qt[1] == 50.0
        assert qt[23] == 1150.0

    def test_pentatonic_5(self):
        p5 = pentatonic_5()
        assert len(p5) == 5
        assert p5[0] == 0.0
        assert abs(p5[1] - 240.0) < 0.01

    def test_meantone_12(self):
        mt = meantone()
        assert len(mt) == 12
        assert mt[0] == 0.0
        # Fifth ≈ 696.6 cents (not 700 like 12-TET)
        fifths = [n for n in mt if abs(n - 696) < 2]
        assert len(fifths) == 1

    def test_pythagorean_12(self):
        py = pythagorean()
        assert len(py) == 12
        assert py[0] == 0.0
        # Fifth ≈ 701.96
        fifths = [n for n in py if abs(n - 701.9) < 2]
        assert len(fifths) == 1

    def test_snap_to_tuning_exact(self):
        tet = equal_temperament(12)
        assert snap_to_tuning(200.0, tet) == 200.0

    def test_snap_to_tuning_nearby(self):
        tet = equal_temperament(12)
        assert snap_to_tuning(203.0, tet) == 200.0

    def test_snap_to_tuning_epsilon(self):
        tet = equal_temperament(12)
        # 250 is 50 cents from 200 and 50 from 300 — snap only if epsilon allows
        assert snap_to_tuning(250.0, tet, epsilon=60) == 200.0 or snap_to_tuning(250.0, tet, epsilon=60) == 300.0
        assert snap_to_tuning(250.0, tet, epsilon=10) == 250.0  # too far, no snap

    def test_pythagorean_wolf_interval(self):
        py = pythagorean()
        # Wolf fifth should be present: ~678.5 cents instead of ~702
        sorted_py = sorted(py)
        intervals = [(sorted_py[(i+1) % 12] - sorted_py[i]) % 1200 for i in range(12)]
        # One interval should be much larger (the wolf)
        assert max(intervals) > 95  # wolf interval > 95 cents


# ── Ornaments ──────────────────────────────────────────────────────────────

class TestOrnaments:
    def test_meend_start_end(self):
        m = meend(60.0, 64.0, steps=20)
        assert len(m) == 21  # steps + 1
        assert abs(m[0] - 60.0) < 0.01
        assert abs(m[-1] - 64.0) < 0.01

    def test_meend_linear(self):
        m = meend(0.0, 10.0, steps=10, curve="linear")
        for i, v in enumerate(m):
            assert abs(v - i) < 0.01

    def test_meend_exponential(self):
        m = meend(0.0, 10.0, steps=10, curve="exponential")
        assert m[-1] == 10.0
        # Should be behind linear at midpoint
        assert m[5] < 5.0

    def test_gamak_oscillates(self):
        g = gamak(60.0, amplitude=1.0, speed=4.0, cycles=2)
        assert len(g) > 0
        assert any(v > 60.0 for v in g)
        assert any(v < 60.0 for v in g)

    def test_gamak_centered(self):
        g = gamak(60.0, amplitude=0.5)
        assert abs(g[0] - 60.5) <= 0.5 or abs(g[0] - 59.5) <= 0.5

    def test_quarter_bend_up(self):
        qb = quarter_bend(60.0, direction="up", cents=50)
        assert qb[0] == 60.0
        assert any(v > 60.0 for v in qb)
        # Should return to start
        assert abs(qb[-1] - 60.0) < 0.01

    def test_quarter_bend_down(self):
        qb = quarter_bend(60.0, direction="down", cents=50)
        assert any(v < 60.0 for v in qb)

    def test_grace_note_adjacent(self):
        gn = grace_note(60.0, approach="adjacent")
        assert len(gn) == 2
        assert gn[0]["pitch"] == 59.0
        assert gn[1]["pitch"] == 60.0

    def test_grace_note_above(self):
        gn = grace_note(60.0, approach="diatonic_above")
        assert gn[0]["pitch"] == 62.0

    def test_murki_alternates(self):
        m = murki([60.0, 62.0, 64.0], speed_ms=80)
        assert len(m) > 4
        assert m[0]["pitch"] == 60.0
        assert m[1]["pitch"] == 62.0
        # All durations should be speed_ms
        for event in m:
            assert event["duration_ms"] == 80

    def test_shakes_oscillate(self):
        s = shakes(60.0, speed=8.0, amplitude=0.3)
        assert len(s) > 0
        assert any(v > 60.0 for v in s)
        assert any(v < 60.0 for v in s)


# ── Rhythms ────────────────────────────────────────────────────────────────

class TestRhythms:
    def test_clave_son_2_3(self):
        c = clave("son_2_3")
        assert len(c) == 5
        assert 0 in c

    def test_clave_bossa_nova(self):
        c = clave("bossa_nova")
        assert len(c) == 6

    def test_clave_rescale(self):
        c = clave("son_2_3", subdivisions=32)
        assert c[0] == 0
        assert c[-1] == 22  # 11 * 2

    def test_clave_unknown_raises(self):
        with pytest.raises(KeyError):
            clave("nonexistent")

    def test_bell_pattern_agbadza(self):
        b = bell_pattern("agbadza")
        assert len(b) == 6
        assert 0 in b

    def test_bell_pattern_all_valid(self):
        for style in ("agbadza", "gahu", "atsiagbekor", "kinka", "yanvalou", "iren"):
            b = bell_pattern(style)
            assert len(b) > 0

    def test_bell_unknown_raises(self):
        with pytest.raises(KeyError):
            bell_pattern("nonexistent")

    def test_tala_teental(self):
        t = tala("teental")
        assert t["beats"] == 16
        assert t["groups"] == [4, 4, 4, 4]
        assert sum(t["groups"]) == t["beats"]

    def test_tala_rupak(self):
        t = tala("rupak")
        assert t["beats"] == 7
        assert t["groups"] == [3, 2, 2]

    def test_tala_groups_sum_to_beats(self):
        for name in ("teental", "jhap_tal", "rupak", "ek_tal", "kaharwa", "dadra", "deepchandi"):
            t_data = tala(name)
            assert sum(t_data["groups"]) == t_data["beats"]

    def test_tala_unknown_raises(self):
        with pytest.raises(KeyError):
            tala("nonexistent")

    def test_iqa_maqsum(self):
        q = iqa("maqsum")
        assert q["beats"] == 4
        assert q["pattern"] == ["D", "T", "D", "T"]

    def test_iqa_baladi(self):
        q = iqa("baladi")
        assert q["beats"] == 4
        assert q["pattern"][0] == "D"

    def test_iqa_all_valid(self):
        for name in ("maqsum", "baladi", "saidi", "malfuf", "fallahi", "sama_i_thaqil", "aqsaq", "dawr_hind"):
            q = iqa(name)
            assert q["beats"] > 0
            assert len(q["pattern"]) > 0

    def test_iqa_unknown_raises(self):
        with pytest.raises(KeyError):
            iqa("nonexistent")

    def test_swing_ratio_straight(self):
        s = swing_ratio(0.5)
        assert abs(s["long"] - s["short"]) < 0.01

    def test_swing_ratio_triplet(self):
        s = swing_ratio(0.67)
        assert s["long"] > s["short"]

    def test_swing_ratio_sum_to_one(self):
        s = swing_ratio(0.67)
        assert abs(s["long"] + s["short"] - 1.0) < 0.01

    def test_swing_ratio_invalid(self):
        with pytest.raises(ValueError):
            swing_ratio(0.1)

    def test_clave_all_types_valid(self):
        for ctype in ("son_2_3", "son_3_2", "rumba_2_3", "rumba_3_2", "bossa_nova"):
            c = clave(ctype)
            assert all(isinstance(x, int) for x in c)
            assert c == sorted(c)
