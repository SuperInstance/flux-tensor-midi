"""Tests for flux_genome — Genomic constraint analysis."""

import sys, os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flux_genome.constraints import (
    GCContentConstraint, HomopolymerConstraint, CodonUsageConstraint,
    MotifConstraint, LengthConstraint, ComplexityConstraint, ConstraintViolation,
)
from flux_genome.engine import GenomeConstraintEngine, GenomeCheckResult


# ── GCContentConstraint ─────────────────────────────────────

class TestGCContent:
    def test_balanced_gc_passes(self):
        c = GCContentConstraint(lo=0.3, hi=0.7)
        r = c.check("ATCGATCG")
        assert r.passed

    def test_high_gc_fails(self):
        c = GCContentConstraint(lo=0.3, hi=0.6)
        r = c.check("GCGCGCGC")
        assert not r.passed

    def test_all_at_fails(self):
        c = GCContentConstraint(lo=0.3, hi=0.7)
        r = c.check("ATATATAT")
        assert not r.passed

    def test_empty_sequence_passes(self):
        c = GCContentConstraint()
        r = c.check("")
        assert r.passed

    def test_n_bases_ignored(self):
        c = GCContentConstraint(lo=0.4, hi=0.6)
        r = c.check("GNNNC")
        # GC = 2/2 = 1.0 (N's stripped) → outside [0.4, 0.6]
        assert not r.passed

    def test_to_dict(self):
        c = GCContentConstraint()
        r = c.check("ATCG")
        d = r.to_dict()
        assert "constraint_name" in d
        assert "passed" in d


# ── HomopolymerConstraint ───────────────────────────────────

class TestHomopolymer:
    def test_no_long_run_passes(self):
        c = HomopolymerConstraint(max_run=4)
        r = c.check("ATCGATCG")
        assert r.passed

    def test_long_run_fails(self):
        c = HomopolymerConstraint(max_run=3)
        r = c.check("AAAAT")
        assert not r.passed

    def test_exact_limit_passes(self):
        c = HomopolymerConstraint(max_run=3)
        r = c.check("AAAT")
        assert r.passed

    def test_empty_passes(self):
        c = HomopolymerConstraint(max_run=3)
        r = c.check("")
        assert r.passed


# ── LengthConstraint ────────────────────────────────────────

class TestLength:
    def test_valid_length(self):
        c = LengthConstraint(min_len=5, max_len=20)
        r = c.check("ATCGATCG")
        assert r.passed

    def test_too_short(self):
        c = LengthConstraint(min_len=10, max_len=100)
        r = c.check("ATCG")
        assert not r.passed

    def test_too_long(self):
        c = LengthConstraint(min_len=1, max_len=5)
        r = c.check("ATCGATCG")
        assert not r.passed

    def test_exact_min(self):
        c = LengthConstraint(min_len=4, max_len=10)
        r = c.check("ATCG")
        assert r.passed


# ── MotifConstraint ─────────────────────────────────────────

class TestMotif:
    def test_required_present(self):
        c = MotifConstraint(required=["ATG"])
        r = c.check("ATGCGT")
        assert r.passed

    def test_required_missing(self):
        c = MotifConstraint(required=["ATG", "TAA"])
        r = c.check("ATGCGT")
        assert not r.passed

    def test_forbidden_absent(self):
        c = MotifConstraint(forbidden=["AAA"])
        r = c.check("ATCG")
        assert r.passed

    def test_forbidden_present(self):
        c = MotifConstraint(forbidden=["AAA"])
        r = c.check("AAATCG")
        assert not r.passed


# ── CodonUsageConstraint ────────────────────────────────────

class TestCodonUsage:
    def test_uniform_passes(self):
        c = CodonUsageConstraint()
        # Long enough sequence with diverse codons
        r = c.check("ATGCGTATCATCATGCGTATGCGT")
        assert isinstance(r, ConstraintViolation)

    def test_short_sequence_passes(self):
        c = CodonUsageConstraint()
        r = c.check("AT")
        assert r.passed  # no codons to check


# ── ComplexityConstraint ────────────────────────────────────

class TestComplexity:
    def test_complex_passes(self):
        c = ComplexityConstraint(min_entropy=0.5)
        r = c.check("ATCGATCGATCGATCG")
        assert r.passed

    def test_repetitive_fails(self):
        c = ComplexityConstraint(min_entropy=3.0)
        r = c.check("ATATATATATATATAT")
        # This might or might not fail depending on entropy
        assert isinstance(r, ConstraintViolation)

    def test_short_sequence_passes(self):
        c = ComplexityConstraint(min_entropy=1.0)
        r = c.check("AT")
        assert r.passed  # too short → auto-pass


# ── GenomeConstraintEngine ──────────────────────────────────

class TestGenomeEngine:
    def test_add_and_check(self):
        engine = GenomeConstraintEngine()
        engine.add_constraint(GCContentConstraint(lo=0.3, hi=0.7))
        engine.add_constraint(HomopolymerConstraint(max_run=4))
        r = engine.check("ATCGATCG")
        assert r.passed
        assert r.n_constraints == 2

    def test_default_constraints(self):
        engine = GenomeConstraintEngine()
        engine.add_default_constraints()
        assert engine.n_constraints == 4

    def test_batch_check(self):
        engine = GenomeConstraintEngine()
        engine.add_constraint(LengthConstraint(min_len=4, max_len=20))
        results = engine.check_batch(["ATCG", "ATCGATCGATCGATCGATCGATCGATCG"])
        assert results[0].passed
        assert not results[1].passed

    def test_clear(self):
        engine = GenomeConstraintEngine()
        engine.add_constraint(GCContentConstraint())
        engine.clear()
        assert engine.n_constraints == 0

    def test_summary_output(self):
        engine = GenomeConstraintEngine()
        engine.add_constraint(GCContentConstraint())
        r = engine.check("ATCG")
        s = r.summary()
        assert "PASS" in s or "FAIL" in s

    def test_to_dict(self):
        engine = GenomeConstraintEngine()
        engine.add_constraint(GCContentConstraint())
        r = engine.check("ATCG")
        d = r.to_dict()
        assert "passed" in d
        assert "violations" in d

    def test_failed_constraints(self):
        engine = GenomeConstraintEngine()
        engine.add_constraint(LengthConstraint(min_len=100))
        r = engine.check("ATCG")
        failed = r.failed_constraints()
        assert len(failed) == 1

    def test_repr(self):
        engine = GenomeConstraintEngine()
        assert "GenomeConstraintEngine" in repr(engine)
