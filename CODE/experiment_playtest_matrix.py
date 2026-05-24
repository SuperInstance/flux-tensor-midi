import numpy as np
import json
import time
import sys
sys.path.insert(0, '/tmp/flux-tensor-midi')

from flux_tensor_midi.beta_testing import (
    BetaTestSuite, BetaTester, MusicalIdea, TesterPersona
)
from flux_tensor_midi.creative_engine import CreativeSystem

print("=== Experiment 40: Full Playtest Matrix ===\n")
print("8 personas × 11 ρ values × 5 scales × 3 repetitions\n")

start = time.time()

suite = BetaTestSuite()

rho_values = [1, 3, 5, 10, 15, 20, 25, 28, 35, 45, 55]
scales = {
    'major': [0, 2, 4, 5, 7, 9, 11],
    'minor': [0, 2, 3, 5, 7, 8, 10],
    'pentatonic': [0, 2, 4, 7, 9],
    'blues': [0, 3, 5, 6, 7, 10],
    'chromatic': list(range(12)),
}

results = {}

for rho in rho_values:
    results[rho] = {}
    
    for scale_name, scale in scales.items():
        # Generate 3 ideas for this config
        ideas = []
        for rep in range(3):
            system = CreativeSystem(rho=rho)
            system.run(200, 100)
            idea = MusicalIdea.from_creative_system(system, scale=scale, n_events=64)
            ideas.append(idea)
        
        # Evaluate with all personas
        persona_scores = {}
        for persona in TesterPersona:
            tester = BetaTester(persona)
            scores = []
            for idea in ideas:
                result = tester.evaluate(idea)
                scores.append(result.overall_score)
            persona_scores[persona.value] = {
                'mean': float(np.mean(scores)),
                'std': float(np.std(scores)),
                'would_listen_pct': sum(1 for s in scores if s > 5) / len(scores) * 100,
            }
        
        results[rho][scale_name] = persona_scores
    
    print(f"  ρ={rho:3d} done ({time.time()-start:.1f}s)")

# Analysis
print(f"\n{'='*60}")
print("PLAYTEST MATRIX RESULTS")
print(f"{'='*60}")

# Best configuration per persona
print("\n  Optimal (ρ, scale) per persona:")
for persona in TesterPersona:
    best_score = 0
    best_config = None
    for rho in rho_values:
        for scale_name in scales:
            score = results[rho][scale_name][persona.value]['mean']
            if score > best_score:
                best_score = score
                best_config = (rho, scale_name)
    print(f"    {persona.value:25s}: ρ={best_config[0]:3d}, scale={best_config[1]:12s}, score={best_score:.2f}")

# Best overall configurations
print("\n  Overall top configurations:")
config_scores = {}
for rho in rho_values:
    for scale_name in scales:
        avg = np.mean([results[rho][scale_name][p.value]['mean'] for p in TesterPersona])
        config_scores[(rho, scale_name)] = avg

for config, score in sorted(config_scores.items(), key=lambda x: -x[1])[:5]:
    print(f"    ρ={config[0]:3d}, {config[1]:12s}: avg={score:.2f}")

# Genre-persona affinity
print("\n  Scale preference by persona:")
for persona in TesterPersona:
    scale_avgs = {}
    for scale_name in scales:
        avg = np.mean([results[rho][scale_name][persona.value]['mean'] for rho in rho_values])
        scale_avgs[scale_name] = avg
    best_scale = max(scale_avgs, key=scale_avgs.get)
    worst_scale = min(scale_avgs, key=scale_avgs.get)
    print(f"    {persona.value:25s}: best={best_scale} ({scale_avgs[best_scale]:.2f}), "
          f"worst={worst_scale} ({scale_avgs[worst_scale]:.2f})")

# Rho preference by persona
print("\n  ρ preference by persona:")
for persona in TesterPersona:
    rho_avgs = {}
    for rho in rho_values:
        avg = np.mean([results[rho][s][persona.value]['mean'] for s in scales])
        rho_avgs[rho] = avg
    best_rho = max(rho_avgs, key=rho_avgs.get)
    worst_rho = min(rho_avgs, key=rho_avgs.get)
    print(f"    {persona.value:25s}: best ρ={best_rho:3d} ({rho_avgs[best_rho]:.2f}), "
          f"worst ρ={worst_rho:3d} ({rho_avgs[worst_rho]:.2f})")

# Regime preferences
print("\n  Regime preference by persona:")
for persona in TesterPersona:
    fixed = np.mean([results[r][s][persona.value]['mean'] for r in [1,3,5] for s in scales])
    periodic = np.mean([results[r][s][persona.value]['mean'] for r in [10,15,20] for s in scales])
    chaotic = np.mean([results[r][s][persona.value]['mean'] for r in [25,28,35,45,55] for s in scales])
    best = max([('fixed', fixed), ('periodic', periodic), ('chaotic', chaotic)], key=lambda x: x[1])
    print(f"    {persona.value:25s}: fixed={fixed:.2f}, periodic={periodic:.2f}, chaotic={chaotic:.2f} → {best[0]}")

elapsed = time.time() - start
print(f"\n  Total time: {elapsed:.1f}s")
print(f"  Total evaluations: {8 * 11 * 5 * 3}")

with open('CODE/EXPERIMENT-PLAYTEST-MATRIX.json', 'w') as f:
    json.dump({
        'results': {str(k): v for k, v in results.items()},
        'config': {
            'rho_values': rho_values,
            'scales': list(scales.keys()),
            'personas': [p.value for p in TesterPersona],
            'n_reps': 3,
        }
    }, f, indent=2, default=str)

print("\n=== PLAYTEST MATRIX COMPLETE ===")
