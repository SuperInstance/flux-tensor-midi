"""
flux_genome — Genomic constraint analysis.

Apply constraint theory to DNA/RNA sequences for quality control,
synthetic biology design verification, and sequence validation.
"""

from flux_genome.constraints import (
    GCContentConstraint,
    HomopolymerConstraint,
    CodonUsageConstraint,
    MotifConstraint,
    LengthConstraint,
    ComplexityConstraint,
)
from flux_genome.engine import GenomeConstraintEngine, GenomeCheckResult

__all__ = [
    "GCContentConstraint",
    "HomopolymerConstraint",
    "CodonUsageConstraint",
    "MotifConstraint",
    "LengthConstraint",
    "ComplexityConstraint",
    "GenomeConstraintEngine",
    "GenomeCheckResult",
]
__version__ = "0.1.0"
