# flux-genome

Genomic constraint analysis — apply constraint theory to DNA/RNA sequences.

```python
from flux_genome import GenomeConstraintEngine, GCContentConstraint

engine = GenomeConstraintEngine()
engine.add_constraint(GCContentConstraint(lo=0.35, hi=0.65))
result = engine.check("ATCGATCGATCG...")
print(result.passed, result.violations)
```

## Constraint Types

- **GCContentConstraint**: GC percentage within bounds
- **HomopolymerConstraint**: Max consecutive identical bases
- **CodonUsageConstraint**: Codon frequency within expected ranges
- **MotifConstraint**: Required/forbidden sequence motifs
- **LengthConstraint**: Sequence length within bounds
- **ComplexityConstraint**: Shannon entropy of k-mer distribution

## Installation

```bash
pip install flux-genome
```
