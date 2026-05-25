"""
flux_genome.engine — GenomeConstraintEngine: unified genome sequence checking.

Runs all registered constraints against a DNA/RNA sequence and aggregates results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from flux_genome.constraints import (
    ConstraintViolation,
    GCContentConstraint,
    HomopolymerConstraint,
    ComplexityConstraint,
    LengthConstraint,
)


@dataclass
class GenomeCheckResult:
    """Aggregated result of checking a sequence against all constraints."""
    passed: bool
    n_constraints: int
    n_passed: int
    n_failed: int
    violations: List[ConstraintViolation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "n_constraints": self.n_constraints,
            "n_passed": self.n_passed,
            "n_failed": self.n_failed,
            "violations": [v.to_dict() for v in self.violations],
        }

    def failed_constraints(self) -> List[ConstraintViolation]:
        return [v for v in self.violations if not v.passed]

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"[{status}] {self.n_passed}/{self.n_constraints} constraints passed"]
        for v in self.violations:
            icon = "✓" if v.passed else "✗"
            lines.append(f"  {icon} {v.constraint_name}: {v.message}")
        return "\n".join(lines)


class GenomeConstraintEngine:
    """
    Unified engine for checking genomic sequences against multiple constraints.

    Usage:
        engine = GenomeConstraintEngine()
        engine.add_default_constraints()
        result = engine.check("ATCGATCGATCGATCG...")
        print(result.summary())

    Or with custom constraints:
        engine = GenomeConstraintEngine()
        engine.add_constraint(GCContentConstraint(lo=0.4, hi=0.6))
        engine.add_constraint(HomopolymerConstraint(max_run=4))
        result = engine.check("ATCG...")
    """

    def __init__(self):
        self._constraints: list = []

    def add_constraint(self, constraint) -> None:
        """Add a constraint. Must have a check(sequence) method."""
        self._constraints.append(constraint)

    def add_default_constraints(self,
                                gc_lo: float = 0.35, gc_hi: float = 0.65,
                                max_homopolymer: int = 6,
                                min_length: int = 0, max_length: int = 1000000,
                                min_complexity: float = 1.0) -> None:
        """Add a sensible default set of genomic constraints."""
        self.add_constraint(GCContentConstraint(lo=gc_lo, hi=gc_hi))
        self.add_constraint(HomopolymerConstraint(max_run=max_homopolymer))
        self.add_constraint(LengthConstraint(min_len=min_length, max_len=max_length))
        self.add_constraint(ComplexityConstraint(min_entropy=min_complexity))

    @property
    def n_constraints(self) -> int:
        return len(self._constraints)

    def check(self, sequence: str) -> GenomeCheckResult:
        """Check sequence against all registered constraints."""
        violations = []
        for constraint in self._constraints:
            violation = constraint.check(sequence)
            violations.append(violation)

        n_passed = sum(1 for v in violations if v.passed)
        n_failed = len(violations) - n_passed

        return GenomeCheckResult(
            passed=n_failed == 0,
            n_constraints=len(violations),
            n_passed=n_passed,
            n_failed=n_failed,
            violations=violations,
        )

    def check_batch(self, sequences: List[str]) -> List[GenomeCheckResult]:
        """Check multiple sequences."""
        return [self.check(seq) for seq in sequences]

    def clear(self) -> None:
        """Remove all constraints."""
        self._constraints.clear()

    def __repr__(self) -> str:
        return f"GenomeConstraintEngine(n_constraints={self.n_constraints})"
