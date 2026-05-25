"""
flux_genome.constraints — Individual genomic constraint types.

Each constraint type checks a specific property of a DNA/RNA sequence.
All constraints follow the same interface: check(sequence) -> dict.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np


@dataclass
class ConstraintViolation:
    """A single constraint violation."""
    constraint_name: str
    passed: bool
    actual: float
    expected_lo: float
    expected_hi: float
    message: str

    def to_dict(self) -> dict:
        return {
            "constraint_name": self.constraint_name,
            "passed": self.passed,
            "actual": self.actual,
            "expected_lo": self.expected_lo,
            "expected_hi": self.expected_hi,
            "message": self.message,
        }


class GCContentConstraint:
    """Check that GC content (fraction) is within bounds.

    Args:
        lo: Minimum GC fraction (0.0 to 1.0)
        hi: Maximum GC fraction (0.0 to 1.0)
        name: Constraint name for reporting
    """

    def __init__(self, lo: float = 0.35, hi: float = 0.65,
                 name: str = "gc_content"):
        self.lo = lo
        self.hi = hi
        self.name = name

    def check(self, sequence: str) -> ConstraintViolation:
        seq = sequence.upper().replace("N", "")
        if not seq:
            return ConstraintViolation(
                self.name, True, 0.0, self.lo, self.hi, "Empty sequence"
            )
        gc = sum(1 for b in seq if b in "GC") / len(seq)
        passed = self.lo <= gc <= self.hi
        msg = f"GC={gc:.3f} within [{self.lo:.3f}, {self.hi:.3f}]" if passed else \
              f"GC={gc:.3f} outside [{self.lo:.3f}, {self.hi:.3f}]"
        return ConstraintViolation(self.name, passed, gc, self.lo, self.hi, msg)


class HomopolymerConstraint:
    """Check that no homopolymer run exceeds max length.

    Args:
        max_run: Maximum consecutive identical bases allowed
        name: Constraint name
    """

    def __init__(self, max_run: int = 6, name: str = "homopolymer"):
        self.max_run = max_run
        self.name = name

    def check(self, sequence: str) -> ConstraintViolation:
        seq = sequence.upper()
        max_found = 1
        current = 1
        for i in range(1, len(seq)):
            if seq[i] == seq[i-1] and seq[i] in "ACGT":
                current += 1
                max_found = max(max_found, current)
            else:
                current = 1
        passed = max_found <= self.max_run
        msg = f"Max homopolymer={max_found} <= {self.max_run}" if passed else \
              f"Max homopolymer={max_found} > {self.max_run}"
        return ConstraintViolation(self.name, passed, float(max_found),
                                   0.0, float(self.max_run), msg)


class CodonUsageConstraint:
    """Check that codon usage frequencies are within expected ranges.

    Args:
        expected: Dict mapping codon to (lo, hi) frequency bounds
        name: Constraint name
    """

    # Standard genetic code
    CODONS = [a + b + c for a in "ACGT" for b in "ACGT" for c in "ACGT"]

    def __init__(self, expected: Optional[Dict[str, tuple]] = None,
                 name: str = "codon_usage"):
        self.name = name
        if expected is None:
            # Default: all codons expected at roughly uniform frequency
            # with generous bounds
            lo = 0.0
            hi = 0.10
            self.expected = {codon: (lo, hi) for codon in self.CODONS}
        else:
            self.expected = expected

    def check(self, sequence: str) -> ConstraintViolation:
        seq = sequence.upper().replace("N", "")
        # Trim to multiple of 3
        seq = seq[:len(seq) - len(seq) % 3] if len(seq) >= 3 else ""
        if not seq:
            return ConstraintViolation(
                self.name, True, 0.0, 0.0, 1.0, "No codons to check"
            )

        codons = [seq[i:i+3] for i in range(0, len(seq), 3)]
        counts = Counter(codons)
        total = len(codons)

        worst_deviation = 0.0
        for codon, (lo, hi) in self.expected.items():
            freq = counts.get(codon, 0) / total
            if freq < lo:
                worst_deviation = max(worst_deviation, lo - freq)
            elif freq > hi:
                worst_deviation = max(worst_deviation, freq - hi)

        passed = worst_deviation < 1e-10
        msg = f"Max codon usage deviation: {worst_deviation:.4f}" if not passed else \
              "All codon frequencies within bounds"
        return ConstraintViolation(self.name, passed, worst_deviation, 0.0, 0.0, msg)


class MotifConstraint:
    """Check for required or forbidden motifs.

    Args:
        required: List of motifs that MUST be present
        forbidden: List of motifs that MUST NOT be present
        name: Constraint name
    """

    def __init__(self, required: Optional[List[str]] = None,
                 forbidden: Optional[List[str]] = None,
                 name: str = "motif"):
        self.required = required or []
        self.forbidden = forbidden or []
        self.name = name

    def check(self, sequence: str) -> ConstraintViolation:
        seq = sequence.upper()
        missing = [m for m in self.required if m.upper() not in seq]
        found_forbidden = [m for m in self.forbidden if m.upper() in seq]

        n_issues = len(missing) + len(found_forbidden)
        passed = n_issues == 0

        parts = []
        if missing:
            parts.append(f"Missing required: {missing}")
        if found_forbidden:
            parts.append(f"Found forbidden: {found_forbidden}")
        msg = "; ".join(parts) if parts else "All motif constraints satisfied"

        return ConstraintViolation(self.name, passed, float(n_issues),
                                   0.0, 0.0, msg)


class LengthConstraint:
    """Check that sequence length is within bounds.

    Args:
        min_len: Minimum sequence length
        max_len: Maximum sequence length
        name: Constraint name
    """

    def __init__(self, min_len: int = 0, max_len: int = 1000000,
                 name: str = "length"):
        self.min_len = min_len
        self.max_len = max_len
        self.name = name

    def check(self, sequence: str) -> ConstraintViolation:
        length = len(sequence)
        passed = self.min_len <= length <= self.max_len
        msg = f"Length={length} within [{self.min_len}, {self.max_len}]" if passed else \
              f"Length={length} outside [{self.min_len}, {self.max_len}]"
        return ConstraintViolation(self.name, passed, float(length),
                                   float(self.min_len), float(self.max_len), msg)


class ComplexityConstraint:
    """Check sequence complexity via Shannon entropy of k-mer distribution.

    Low entropy means the sequence is repetitive (low complexity).
    High entropy means it's well-distributed.

    Args:
        k: K-mer size for entropy calculation
        min_entropy: Minimum Shannon entropy per k-mer position (bits)
        name: Constraint name
    """

    def __init__(self, k: int = 3, min_entropy: float = 1.0,
                 name: str = "complexity"):
        self.k = k
        self.min_entropy = min_entropy
        self.name = name

    def check(self, sequence: str) -> ConstraintViolation:
        seq = sequence.upper().replace("N", "")
        if len(seq) < self.k:
            return ConstraintViolation(
                self.name, True, 0.0, self.min_entropy, float('inf'),
                f"Sequence too short for k={self.k}"
            )

        kmers = [seq[i:i+self.k] for i in range(len(seq) - self.k + 1)]
        counts = Counter(kmers)
        total = len(kmers)

        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        # Normalize to per-position entropy
        # Max entropy for 4^k possible kmers
        max_entropy = math.log2(min(4**self.k, total)) if total > 0 else 1.0
        norm_entropy = entropy / max_entropy if max_entropy > 0 else 0.0

        passed = entropy >= self.min_entropy
        msg = f"Entropy={entropy:.3f} >= {self.min_entropy:.3f}" if passed else \
              f"Entropy={entropy:.3f} < {self.min_entropy:.3f}"
        return ConstraintViolation(self.name, passed, entropy,
                                   self.min_entropy, float('inf'), msg)
