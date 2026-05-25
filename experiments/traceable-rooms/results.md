# Traceable Room Intelligence: Training Provenance as First-Class Artifact

**Date:** 2026-05-17 | **Hardware:** RTX 4050 Laptop GPU

## The Architecture

```
TRAINING TIME                          RUNTIME
===========                            =======

Room A ──→ tiles ──→ training data ──┐
Room B ──→ tiles ──→ training data ──┼──→ Model ──→ Decision
Room C ──→ tiles ──→ training data ──┘     │         │
                                           │         │
        Provenance Map ◄───────────────────┘         │
        (which room shaped                            │
         which weight)                                │
                                                     ▼
                                          Traceability Query:
                                          "Why did you say STABLE?"
                                          → "Weights shaped 24% by
                                             room-tile-relevance,
                                             21% by room-anomaly-flag,
                                             ..."
```

## Results

### Multi-Head Room Intelligence Model (1037 params, 4KB)

| Room Task | Accuracy |
|-----------|----------|
| drift-detect (binary) | 89.5% |
| intent-classify (4-class) | 31.0% |
| anomaly-flag (binary) | 97.0% |
| priority-rank (3-class) | 100.0% |
| tile-relevance (binary) | 96.5% |

**Total model: 1037 parameters, 4148 bytes.** Fits in a single WASM page.

### Weight Provenance

All shared weights show contributions from all 5 rooms:

| Room | Contribution to Shared Weights |
|------|------|
| room-tile-relevance | 24.4% |
| room-anomaly-flag | 20.6% |
| room-intent-classify | 19.8% |
| room-priority-rank | 19.1% |
| room-drift-detect | 16.1% |

The relevance room contributes most because its data has the highest dynamic range — it shapes the shared representation more strongly. This is traceable.

### Spectral Conservation

I(x) = 5.29, CV = 0.103 during training. Higher CV than single-task models (0.028) because multi-head training creates competing gradient signals. Still approximately conserved.

### Runtime Traceability Demo

```
Input: drift_rate=0.25, confidence=0.7, density=0.847
Decision: STABLE (confidence: 0.54)
Trace: 0.weight ← shaped by room-tile-relevance (24.4%)
```

The model decided STABLE. If questioned, we can trace: the shared weights were most influenced by room-tile-relevance (which has high tile relevance → stable patterns) and room-anomaly-flag (which classifies 97% correctly → strong signal). The model "learned" from those rooms that moderate drift with high confidence is usually stable.

## The Key Insight (Casey's Vision)

**The model IS the compressed runtime. The provenance map IS the audit trail.**

At runtime:
- Model runs fast (1037 params, microseconds)
- No need to query rooms, tiles, or LLM for routine decisions
- The 4KB model IS the distilled intelligence

When something goes wrong:
- "Why did the model classify this room as stable when it was drifting?"
- Open provenance map: weights shaped 16% by room-drift-detect data
- Check room-drift-detect accuracy: 89.5%
- Check the specific tiles that contributed to the training sample
- Find the gap: maybe drift_rate=0.25 was underrepresented in training data
- Add more data from that regime → retrain → provenance updates

**The training creates traceable connections between rooms. The connections persist in the provenance map even though runtime only needs the model. The logic that built the model is referenceable after training.**

## Escalation Integration

```
                        ┌─────────────────┐
    Room Input ────────►│  Room Model     │──► confidence > 0.8 → Handle locally
                        │  (1037 params)  │
                        └────────┬────────┘
                                 │ confidence < 0.8
                                 ▼
                        ┌─────────────────┐
                        │ Escalation Gate │──► escalate → Call LLM
                        │   (737 params)  │
                        └────────┬────────┘
                                 │ LLM response
                                 ▼
                        ┌─────────────────┐
                        │ New training    │──► retrain model
                        │ data from LLM   │    update provenance
                        └─────────────────┘
```

Total system: 1774 parameters (7KB). Runs anywhere. Gets better over time. Every decision traceable.
