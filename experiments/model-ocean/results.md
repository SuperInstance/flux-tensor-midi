# The Model Ocean — Results

**Date:** 2026-05-17 | **Hardware:** RTX 4050 Laptop GPU

## The Ecosystem After 100 Ticks

```
  370 cells | 38,052 params (148.6KB)
  
  🔬 sandbox   : 328 cells | fit=0.419 best=0.770 | gen=9 | 29,520 params
  🌊 tide_pool :  38 cells | fit=0.462 best=0.650 | gen=2 |  6,764 params  
  🐟 school    :   3 cells | fit=0.583 best=0.670 | gen=0 |  1,062 params
  🐋 whale     :   1 cell  | fit=0.430 best=0.430 | gen=0 |    706 params
```

## What Happened

### Sandboxes (🔬) — The Explorers
- Started at 80, exploded to 328 through reproduction
- Fitness climbed from 0 → 0.79 in early ticks, settled around 0.42 average
- 9 generations of mutation — the most evolved lineage in the ocean
- Each sandbox is only 90 params (360B) — microscopic
- They test hypotheses fast, most die, best ones reproduce
- **The sandbars of the ocean — churn through possibilities**

### Tide Pools (🌊) — The Specialists
- Started at 25, grew to 38 through reproduction + sandbox promotion
- Each tide pool specializes in one room task (drift, anomaly, intent, etc.)
- 178 params each — small enough for any device
- 2 generations of evolution
- **The coral reefs — stable, specialized, enduring**

### Schools (🐟) — The Coordinators
- 3 cells, 354 params each, best average fitness (0.583)
- Too big to reproduce much, too valuable to lose
- They coordinate across rooms — see patterns that specialists miss
- **The fish schools — collective intelligence from individual simplicity**

### The Whale (🐋) — The Deep Thinker
- 1 cell, 706 params, fitness 0.430
- Slowest to evolve, most expensive to run
- But it sees the WHOLE ocean — trained on all 5 task streams
- **The whale — slow, deep, irreplaceable**

## The Architecture Casey Described

```
                    ┌─────────────────────────┐
                    │   THE MODEL OCEAN       │
                    │   370 cells, 148KB      │
                    │                         │
    🔬 Sandboxes    │  328 cells × 90 params  │  ← Fast experiments
    (sandbars)      │  Die fast, mutate fast   │  ← Most don't survive
                    │  Best ones promote up    │
                    │                         │
    🌊 Tide Pools   │   38 cells × 178 params │  ← Task specialists
    (reefs)         │   One per room task      │  ← Stable, proven
                    │   Self-organizing         │
                    │                         │
    🐟 Schools      │    3 cells × 354 params │  ← Cross-room patterns
    (open water)    │    Coordinate rooms       │  ← Best avg fitness
                    │    Medium speed           │
                    │                         │
    🐋 Whale        │    1 cell × 706 params  │  ← Sees everything
    (deep ocean)    │    Slow but deep          │  ← Last resort
                    │    Trained on ALL rooms   │
                    └─────────────────────────┘
                    
    Runtime: Query the ocean → weighted vote → decision
    The 148KB IS the intelligence. No LLM needed for routine decisions.
    When confidence drops → escalate to LLM → new training data → ocean evolves.
```

## Why This Is Different From One Model

| Property | One Model | Model Ocean |
|----------|-----------|-------------|
| Failure mode | Single point of failure | Graceful degradation |
| Adaptation | Retrain everything | Local mutation |
| Traceability | One provenance chain | Every cell has lineage |
| Deployment | All or nothing | Deploy sandboxes to WASM, whales to GPU |
| Specialization | General (mediocre everywhere) | Specialists per room |
| Evolution speed | Slow (full retrain) | Fast (sandbox mutation) |
| Memory | One model fits or doesn't | Right-size for each device |

## The Traceability Chain

Every cell carries its history:
```
sandbox genome bb6cb724:
  ← room-experimental (spawned)
  ← room-drift-detect:tick12 (fed data)
  ← room-drift-detect:tick37 (fed data)
  ← promoted:sandbox→tide_pool@tick50 (promotion event)
  gen 9, fitness 0.77, 178 params
```

At runtime you just run the model. But when something goes wrong, you can trace:
1. **Which cell made the decision?** → genome bb6cb724
2. **What data shaped it?** → room-drift-detect, ticks 12 and 37
3. **When was it promoted?** → tick 50 (sandbox → tide pool)
4. **What was its parent?** → genome a3f1e902 (gen 8 sandbox)
5. **Why did it evolve this way?** → high fitness on drift-detect stream

## The Distillation Loop

```
                    ┌──────────┐
   PLATO Rooms ────►│ Training │──── Ocean evolves
   (tile streams)   │  Data    │     new cells
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │  Ocean   │───► 370 cells make decisions
                    │ 148KB    │     (no LLM needed for routine)
                    └────┬─────┘
                         │ low confidence
                    ┌────▼─────┐
                    │   LLM    │───► New insight → new tile → new training data
                    └────┬─────┘     Ocean learns from LLM wisdom
                         │
                    ┌────▼─────┐
                    │ Verify   │───► Did the LLM help? Score it.
                    │ Score    │     Feed scores back to ocean.
                    └──────────┘     Good cells reproduce. Bad cells die.
```

**The ocean gets better over time. The LLM gets called less and less. The cells get more specialized. The traceability chain grows longer.**

## What This Enables

1. **Any app embeds the ocean** — 148KB is nothing. Phones, WASM, NPU, embedded.
2. **The ocean specializes to the app** — sandboxes mutate toward useful tasks
3. **Traceable AI decisions** — every cell has provenance back to training data
4. **Graceful degradation** — lose some cells, ocean keeps working
5. **Self-evolving** — LLM escalations feed back as training data
6. **Right-sized inference** — sandboxes on WASM, whales on GPU
7. **Fleet topology** — each PLATO room hosts its own tide pool, schools coordinate
