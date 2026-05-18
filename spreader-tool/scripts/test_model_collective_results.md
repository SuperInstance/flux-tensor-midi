# Model Collective Test Results — 2026-05-17

## What was built
- `/spreader-tool/spreader/model_collective.py` — Three components:
  1. **ModelPredictor** — Calls Qwen 0.8B ($0.01/M tokens) via DeepInfra for next-commit prediction
  2. **HybridPredictor** — Merges statistical + model predictions with agreement-based confidence
  3. **AdaptiveRouter** — Routes between stats-only and model calls based on gap rate

## Key finding: Qwen 3.5 0.8B returns content in `reasoning_content`
The model is a "thinking" variant — actual output goes in `reasoning_content`, not `content`. The `content` field is always empty. This is handled in the code.

## Results

| Approach | Avg Gap | Perfect Matches | Cost |
|----------|---------|-----------------|------|
| Stats only (5 preds) | 0.6200 | 0/5 | $0.00 |
| Model only (5 preds) | 0.6200 | 0/5 | $0.000022 |
| Hybrid (25 preds) | 0.6280 | 0/25 | $0.000093 |

## Observations
- **Stats and model perform identically** on this data — both avg gap 0.62
- Model predictions are reasonable (picks plausible repos/types) but not better than frequency tables
- 0.8B model is too small to outperform Markov chains on commit prediction
- Total cost is negligible: $0.000093 for 20 API calls
- Adaptive router correctly escalated to model-every-call when gap rate stayed high (84%)
- The router's adaptation logic works: warmup → sampling → full model when surprised

## Architecture
```
AdaptiveRouter
  └── HybridPredictor
        ├── CommitPredictor (stats: Markov chains, frequency tables)
        └── ModelPredictor (Qwen 0.8B via DeepInfra)
              └── DeepInfraBackend (real API calls, retry logic)
```

## Next steps
- Try a larger model (Gemma 12B at $0.04/M) to see if it outperforms stats
- Feed more realistic commit sequences (real git log data)
- The model needs richer context — timestamps, author patterns, day-of-week
