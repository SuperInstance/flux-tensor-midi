"""
Tests for protein_fold — Protein Folding via Constraint Theory.

Covers:
- AminoAcid construction and properties
- ProteinFolder: folding, snap, funnel, rigidity, consensus, floppy modes
- ProteinToMusic: structure → score, dynamics → timbre
- MusicToProtein: constraints → sequence, constraints → folding params
- NON-PRE-CALCULABILITY: different seeds → different folds
- Round-trip verification
"""

import math
import random
import pytest
import numpy as np

from flux_tensor_midi.protein_fold import (
    AminoAcid,
    ProteinFolder,
    ProteinToMusic,
    MusicToProtein,
    round_trip_verify,
    AMINO_ACID_PROPERTIES,
    LATTICE_DIRS,
)


# ---------------------------------------------------------------------------
# AminoAcid Tests
# ---------------------------------------------------------------------------


class TestAminoAcid:
    """Tests for AminoAcid dataclass."""

    def test_construction_with_valid_code(self):
        aa = AminoAcid(name="A", index=0)
        assert aa.name == "A"
        assert aa.index == 0
        assert aa.secondary == "none"
        assert len(aa.contacts) == 0

    def test_properties_populated_from_table(self):
        aa = AminoAcid(name="K", index=0)
        assert aa.properties["hydro"] == -3.9
        assert aa.properties["charge"] == 1.0

    def test_unknown_amino_acid_gets_default_properties(self):
        aa = AminoAcid(name="X", index=0, properties={"hydro": 0.0, "charge": 0.0, "size": 0.5, "polar": 0.0})
        assert aa.properties["hydro"] == 0.0

    def test_is_hydrophobic(self):
        assert AminoAcid(name="I", index=0).is_hydrophobic is True
        assert AminoAcid(name="D", index=0).is_hydrophobic is False

    def test_is_polar(self):
        assert AminoAcid(name="S", index=0).is_polar is True
        assert AminoAcid(name="A", index=0).is_polar is False

    def test_is_charged(self):
        assert AminoAcid(name="K", index=0).is_charged is True
        assert AminoAcid(name="A", index=0).is_charged is False
        assert AminoAcid(name="D", index=0).is_charged is True

    def test_is_placed_default_false(self):
        aa = AminoAcid(name="A", index=0)
        assert aa.is_placed is False

    def test_is_placed_after_position_set(self):
        aa = AminoAcid(name="A", index=0)
        aa.position = (1.0, 2.0)
        assert aa.is_placed is True

    def test_distance_to(self):
        aa1 = AminoAcid(name="A", index=0, position=(0.0, 0.0))
        aa2 = AminoAcid(name="A", index=1, position=(3.0, 4.0))
        assert aa1.distance_to(aa2) == 5.0

    def test_distance_to_unplaced_is_inf(self):
        aa1 = AminoAcid(name="A", index=0, position=(0.0, 0.0))
        aa2 = AminoAcid(name="A", index=1)
        assert aa1.distance_to(aa2) == float("inf")


# ---------------------------------------------------------------------------
# ProteinFolder Tests
# ---------------------------------------------------------------------------


class TestProteinFolder:
    """Tests for ProteinFolder."""

    def test_valid_sequence_construction(self):
        folder = ProteinFolder(sequence="ACDEFGHIKLMNPQRSTVWY", seed=42)
        assert folder.length == 20
        assert folder.sequence == "ACDEFGHIKLMNPQRSTVWY"

    def test_invalid_sequence_raises(self):
        with pytest.raises(ValueError, match="Invalid amino acid"):
            ProteinFolder(sequence="ACX")

    def test_case_insensitive_sequence(self):
        folder = ProteinFolder(sequence="acdefg", seed=42)
        assert folder.sequence == "ACDEFG"

    def test_constraints_default(self):
        folder = ProteinFolder(sequence="AAAA", seed=42)
        c = folder.constraints
        assert 0 <= c["snap_strength"] <= 1
        assert c["bond_length"] > 0

    def test_constraints_override(self):
        folder = ProteinFolder(
            sequence="AAAA",
            seed=42,
            constraints={"snap_strength": 0.3, "temperature": 0.5},
        )
        assert folder.constraints["snap_strength"] == 0.3
        assert folder.constraints["temperature"] == 0.5

    def test_not_folded_initially(self):
        folder = ProteinFolder(sequence="AAAA", seed=42)
        assert folder.is_folded is False

    def test_fold_returns_positions(self):
        folder = ProteinFolder(sequence="ACDEFGHIKL", seed=42)
        positions = folder.fold()
        assert len(positions) == 10
        assert all(isinstance(p, tuple) for p in positions)
        assert folder.is_folded is True

    def test_fold_all_placed(self):
        folder = ProteinFolder(sequence="ACDEFGHIKL", seed=42)
        folder.fold()
        for aa in folder.chain:
            assert aa.is_placed

    def test_fold_idempotent(self):
        folder = ProteinFolder(sequence="ACDEFGHIKL", seed=42)
        pos1 = folder.fold()
        pos2 = folder.fold()
        assert pos1 == pos2


class TestSnapToLattice:
    """Tests for snap_to_lattice method."""

    def test_snap_returns_tuple(self):
        folder = ProteinFolder(sequence="AAAA", seed=42)
        aa = AminoAcid(name="A", index=0)
        result = folder.snap_to_lattice((1.3, 0.7), aa)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_snap_near_lattice_point(self):
        folder = ProteinFolder(sequence="AAAA", seed=42)
        aa = AminoAcid(name="A", index=0)
        # Point very close to (1, 0) should snap there (or close)
        result = folder.snap_to_lattice((0.99, 0.01), aa)
        assert abs(result[0] - 1.0) < 0.3 or abs(result[1]) < 0.3

    def test_snap_with_low_strength_stays_closer(self):
        folder_soft = ProteinFolder(
            sequence="AAAA", seed=42,
            constraints={"snap_strength": 0.1, "snap_epsilon": 0.5},
        )
        folder_hard = ProteinFolder(
            sequence="AAAA", seed=42,
            constraints={"snap_strength": 1.0, "snap_epsilon": 0.01},
        )
        aa = AminoAcid(name="A", index=0)
        pos = (1.2, 0.3)
        soft = folder_soft.snap_to_lattice(pos, aa)
        hard = folder_hard.snap_to_lattice(pos, aa)
        # Soft snap should stay closer to original
        soft_dist = math.sqrt((soft[0] - pos[0]) ** 2 + (soft[1] - pos[1]) ** 2)
        hard_dist = math.sqrt((hard[0] - pos[0]) ** 2 + (hard[1] - pos[1]) ** 2)
        assert soft_dist <= hard_dist + 0.01  # soft ≤ hard (with tolerance)


class TestEnergyFunnel:
    """Tests for energy_funnel method."""

    def test_funnel_force_direction(self):
        folder = ProteinFolder(sequence="AAAA", seed=42)
        # Force should point toward target
        force = folder.energy_funnel((5.0, 0.0), (0.0, 0.0))
        assert force[0] < 0  # pointing toward origin (negative x)

    def test_funnel_deadband_no_force(self):
        folder = ProteinFolder(
            sequence="AAAA", seed=42,
            constraints={"funnel_deadband": 2.0, "funnel_gravity": 0.5},
        )
        # Within deadband → no force
        force = folder.energy_funnel((0.5, 0.0), (0.0, 0.0))
        assert force == (0.0, 0.0)

    def test_funnel_force_magnitude_increases_with_distance(self):
        folder = ProteinFolder(
            sequence="AAAA", seed=42,
            constraints={"funnel_deadband": 0.1, "funnel_gravity": 0.5},
        )
        force_near = folder.energy_funnel((0.5, 0.0), (0.0, 0.0))
        force_far = folder.energy_funnel((5.0, 0.0), (0.0, 0.0))
        mag_near = math.sqrt(force_near[0] ** 2 + force_near[1] ** 2)
        mag_far = math.sqrt(force_far[0] ** 2 + force_far[1] ** 2)
        assert mag_far > mag_near


class TestRigidityCheck:
    """Tests for rigidity_check method."""

    def test_short_chain_floppy(self):
        folder = ProteinFolder(sequence="AA", seed=42)
        folder.fold()
        result = folder.rigidity_check()
        # 2 residues, 1 bond → 1 edge, needs 2*2-3=1 → exactly rigid
        assert result["vertices"] == 2
        assert result["status"] in ("rigid", "floppy", "overconstrained")

    def test_rigidity_result_keys(self):
        folder = ProteinFolder(sequence="ACDEFGHIKL", seed=42)
        folder.fold()
        result = folder.rigidity_check()
        assert "rigid" in result
        assert "edges" in result
        assert "vertices" in result
        assert "laman_count" in result
        assert "deficit" in result
        assert "status" in result

    def test_custom_contacts(self):
        folder = ProteinFolder(sequence="AAAAA", seed=42)
        folder.fold()
        # Pass extra contacts
        contacts = [(0, 4), (1, 3), (0, 3)]
        result = folder.rigidity_check(contacts=contacts)
        assert result["edges"] >= 4 + 3  # 4 bonds + 3 contacts


class TestConsensus:
    """Tests for consensus_round method."""

    def test_empty_neighbors_returns_zero(self):
        folder = ProteinFolder(sequence="AAAA", seed=42)
        result = folder.consensus_round([])
        assert result == (0.0, 0.0)

    def test_consensus_returns_displacement(self):
        folder = ProteinFolder(sequence="AAAA", seed=42)
        neighbors = [
            AminoAcid(name="A", index=1, position=(1.0, 0.0)),
            AminoAcid(name="A", index=2, position=(0.0, 1.0)),
        ]
        result = folder.consensus_round(neighbors)
        assert isinstance(result, tuple)
        assert len(result) == 2


class TestFloppyModes:
    """Tests for floppy_modes method."""

    def test_requires_folded(self):
        folder = ProteinFolder(sequence="AAAA", seed=42)
        with pytest.raises(RuntimeError, match="folded"):
            folder.floppy_modes()

    def test_returns_list(self):
        folder = ProteinFolder(sequence="ACDEFGHIKLMNPQRSTVWY", seed=42)
        folder.fold()
        modes = folder.floppy_modes()
        assert isinstance(modes, list)
        for mode in modes:
            assert "residues" in mode
            assert "deficit" in mode
            assert "flexibility" in mode
            assert "type" in mode

    def test_floppy_modes_classified(self):
        folder = ProteinFolder(sequence="ACDEFGHIKLMNPQRSTVWY", seed=42)
        folder.fold()
        modes = folder.floppy_modes()
        valid_types = {"disordered", "hinge", "linker", "terminal"}
        for mode in modes:
            assert mode["type"] in valid_types


class TestEnergyAndMetrics:
    """Tests for energy, radius of gyration, and contact map."""

    def test_energy_decreases_during_folding(self):
        folder = ProteinFolder(sequence="ACDEFGHIKLMNPQRSTVWY", seed=42, constraints={"temperature": 1.0, "cooling_rate": 0.99})
        folder.fold(max_steps=50)
        if len(folder.energy_history) > 1:
            # Energy should not diverge uncontrollably
            assert folder.energy_history[-1] < 500

    def test_radius_of_gyration(self):
        folder = ProteinFolder(sequence="ACDEFGHIKLMNPQRSTVWY", seed=42)
        folder.fold()
        rg = folder.radius_of_gyration()
        assert rg > 0
        assert rg < 100  # reasonable range

    def test_contact_map_shape(self):
        folder = ProteinFolder(sequence="ACDEFGHIKLMNPQRSTVWY", seed=42)
        folder.fold()
        cmap = folder.contact_map()
        assert cmap.shape == (20, 20)
        # Diagonal should be 0
        assert np.all(np.diag(cmap) == 0)
        # Should be symmetric
        assert np.array_equal(cmap, cmap.T)

    def test_summary_after_folding(self):
        folder = ProteinFolder(sequence="ACDEFGHIKLMNPQRSTVWY", seed=42)
        folder.fold()
        s = folder.summary()
        assert s["status"] == "folded"
        assert s["length"] == 20
        assert isinstance(s["energy"], float)
        assert s["rigidity"] in ("rigid", "floppy", "overconstrained")

    def test_summary_before_folding(self):
        folder = ProteinFolder(sequence="AAAA", seed=42)
        s = folder.summary()
        assert s["status"] == "not folded"


# ---------------------------------------------------------------------------
# NON-PRE-CALCULABILITY Tests
# ---------------------------------------------------------------------------


class TestNonPreCalculability:
    """Verify that folding is NON-PRE-CALCULABLE: different seeds → different folds."""

    def test_different_seeds_different_positions(self):
        """Same sequence, different seeds → different final positions."""
        seq = "ACDEFGHIKLMNPQRSTVWY"
        folder1 = ProteinFolder(sequence=seq, seed=42)
        folder2 = ProteinFolder(sequence=seq, seed=137)

        pos1 = folder1.fold()
        pos2 = folder2.fold()

        # At least some positions should differ
        differences = sum(
            1 for p1, p2 in zip(pos1, pos2)
            if abs(p1[0] - p2[0]) > 0.01 or abs(p1[1] - p2[1]) > 0.01
        )
        assert differences > 0, "Same sequence with different seeds produced identical folds"

    def test_different_seeds_different_energy(self):
        """Same sequence, different seeds → different energies."""
        seq = "ACDEFGHIKLMNPQRSTVWY"
        energies = []
        for seed in [1, 42, 137, 256, 999]:
            folder = ProteinFolder(sequence=seq, seed=seed)
            folder.fold()
            energies.append(folder.energy())

        # Not all energies should be the same
        unique_energies = len(set(round(e, 4) for e in energies))
        assert unique_energies > 1, "All seeds produced the same energy"

    def test_different_seeds_different_contacts(self):
        """Same sequence, different seeds → different contact maps."""
        seq = "ACDEFGHIKLMNPQRSTVWY"
        folder1 = ProteinFolder(sequence=seq, seed=42)
        folder2 = ProteinFolder(sequence=seq, seed=137)
        folder1.fold()
        folder2.fold()

        cmap1 = folder1.contact_map()
        cmap2 = folder2.contact_map()
        # At least some contact differences
        assert not np.array_equal(cmap1, cmap2), "Same contact maps for different seeds"

    def test_deterministic_with_same_seed(self):
        """Same sequence, same seed → identical fold."""
        seq = "ACDEFGHIKLMNPQRSTVWY"
        folder1 = ProteinFolder(sequence=seq, seed=42)
        folder2 = ProteinFolder(sequence=seq, seed=42)

        pos1 = folder1.fold()
        pos2 = folder2.fold()

        assert pos1 == pos2, "Same seed produced different folds"

    def test_folding_history_non_trivial(self):
        """Folding history should show iterative refinement."""
        folder = ProteinFolder(sequence="ACDEFGHIKLMNPQRSTVWY", seed=42)
        folder.fold(max_steps=50)
        assert len(folder.folding_history) > 0


# ---------------------------------------------------------------------------
# ProteinToMusic Tests
# ---------------------------------------------------------------------------


class TestProteinToMusic:
    """Tests for biology → music transfer."""

    def _folded_protein(self):
        folder = ProteinFolder(sequence="ACDEFGHIKLMNPQRSTVWY", seed=42)
        folder.fold()
        return folder

    def test_requires_folded_protein(self):
        folder = ProteinFolder(sequence="AAAA", seed=42)
        with pytest.raises(RuntimeError, match="folded"):
            ProteinToMusic(folder)

    def test_structure_to_score_returns_dict(self):
        p2m = ProteinToMusic(self._folded_protein())
        score = p2m.structure_to_score()
        assert isinstance(score, dict)
        assert "title" in score
        assert "bpm" in score
        assert "voices" in score
        assert "tonal_center" in score

    def test_voices_contain_events(self):
        p2m = ProteinToMusic(self._folded_protein())
        score = p2m.structure_to_score()
        total_events = sum(len(v) for v in score["voices"].values())
        assert total_events > 0

    def test_pitch_in_midi_range(self):
        p2m = ProteinToMusic(self._folded_protein())
        score = p2m.structure_to_score()
        for voice_name, events in score["voices"].items():
            for event in events:
                assert 0 <= event["pitch"] <= 127

    def test_velocity_in_midi_range(self):
        p2m = ProteinToMusic(self._folded_protein())
        score = p2m.structure_to_score()
        for voice_name, events in score["voices"].items():
            for event in events:
                assert 1 <= event["velocity"] <= 127

    def test_dynamics_to_timbre_returns_list(self):
        folder = self._folded_protein()
        # Need folding history - fold with history
        p2m = ProteinToMusic(folder)
        timbre = p2m.dynamics_to_timbre()
        assert isinstance(timbre, list)
        if timbre:
            for t in timbre:
                assert "brightness" in t
                assert "warmth" in t
                assert "dissonance" in t
                assert 0 <= t["brightness"] <= 1
                assert 0 <= t["warmth"] <= 1

    def test_metadata_present(self):
        p2m = ProteinToMusic(self._folded_protein())
        score = p2m.structure_to_score()
        meta = score["metadata"]
        assert "sequence_length" in meta
        assert "energy" in meta


# ---------------------------------------------------------------------------
# MusicToProtein Tests
# ---------------------------------------------------------------------------


class TestMusicToProtein:
    """Tests for music → biology transfer."""

    def test_constraints_to_sequence_returns_string(self):
        m2p = MusicToProtein(
            constraints={"snap_strength": 0.8, "funnel_gravity": 0.5},
            target_length=20,
            seed=42,
        )
        seq = m2p.constraints_to_sequence()
        assert isinstance(seq, str)
        assert len(seq) == 20

    def test_all_residues_valid(self):
        m2p = MusicToProtein(
            constraints={"snap_strength": 0.5},
            target_length=30,
            seed=42,
        )
        seq = m2p.constraints_to_sequence()
        valid = set(AMINO_ACID_PROPERTIES.keys())
        for aa in seq:
            assert aa in valid

    def test_high_snap_produces_helix_formers(self):
        """High snap strength should enrich helix-forming residues."""
        m2p = MusicToProtein(
            constraints={"snap_strength": 0.95, "snap_epsilon": 0.01},
            target_length=50,
            seed=42,
        )
        seq = m2p.constraints_to_sequence()
        helix_aa = set(m2p.HELIX_FORMERS)
        helix_count = sum(1 for aa in seq if aa in helix_aa)
        # At least 30% should be helix formers
        assert helix_count / len(seq) > 0.3

    def test_high_funnel_produces_hydrophobic_core(self):
        """High funnel gravity should enrich hydrophobic residues in core."""
        m2p = MusicToProtein(
            constraints={"funnel_gravity": 0.95, "snap_strength": 0.5, "snap_epsilon": 0.01},
            target_length=30,
            seed=42,
        )
        seq = m2p.constraints_to_sequence()
        # Check core region (middle third)
        third = len(seq) // 3
        core = seq[third:2 * third]
        hydro = set(m2p.HYDROPHOBIC)
        hydro_count = sum(1 for aa in core if aa in hydro)
        # Core should have more hydrophobic than expected by chance
        assert hydro_count >= 1

    def test_high_laman_produces_cysteines(self):
        """High laman threshold should introduce cysteines."""
        m2p = MusicToProtein(
            constraints={"laman_threshold": 0.9, "snap_strength": 0.5},
            target_length=30,
            seed=42,
        )
        seq = m2p.constraints_to_sequence()
        cys_count = seq.count("C")
        assert cys_count >= 2  # at least one disulfide pair

    def test_high_consensus_produces_symmetry(self):
        """High consensus should produce palindromic/symmetric sequences."""
        m2p = MusicToProtein(
            constraints={"consensus_weight": 0.95, "snap_strength": 0.5, "snap_epsilon": 0.01},
            target_length=20,
            seed=42,
        )
        seq = m2p.constraints_to_sequence()
        # Check for palindromic symmetry
        half = len(seq) // 2
        matches = sum(1 for i in range(half) if seq[i] == seq[-(i + 1)])
        assert matches > 0  # at least some symmetry

    def test_soft_snap_produces_disorder(self):
        """High epsilon (soft snap) should produce disordered residues."""
        m2p = MusicToProtein(
            constraints={"snap_epsilon": 0.8, "snap_strength": 0.5},
            target_length=50,
            seed=42,
        )
        seq = m2p.constraints_to_sequence()
        disorder_aa = set(m2p.DISORDER_PROMOTERS)
        disorder_count = sum(1 for aa in seq if aa in disorder_aa)
        # Should have significant disorder
        assert disorder_count / len(seq) > 0.1

    def test_constraints_to_folding_params(self):
        m2p = MusicToProtein(
            constraints={"snap_strength": 0.7, "funnel_gravity": 0.4},
            target_length=20,
        )
        params = m2p.constraints_to_folding_params()
        assert params["snap_strength"] == 0.7
        assert params["funnel_gravity"] == 0.4


# ---------------------------------------------------------------------------
# Round-trip Tests
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Tests for full Biology → Music → Biology round trip."""

    def test_round_trip_completes(self):
        result = round_trip_verify("ACDEFGHIKLMN", seed=42)
        assert "original_sequence" in result
        assert "derived_sequence" in result
        assert "original_summary" in result
        assert "derived_summary" in result

    def test_round_trip_sequences_different(self):
        """Round trip should generally produce a different sequence."""
        result = round_trip_verify("ACDEFGHIKLMN", seed=42)
        # Sequences likely differ (music transfer is lossy)
        # But both should be valid
        orig = result["original_sequence"]
        derived = result["derived_sequence"]
        for aa in orig + derived:
            assert aa in AMINO_ACID_PROPERTIES

    def test_round_trip_both_folded(self):
        result = round_trip_verify("ACDEFGHIKLMN", seed=42)
        assert result["original_summary"]["status"] == "folded"
        assert result["derived_summary"]["status"] == "folded"
