"""
ε-Sweep Experiment: Injecting controlled noise into all living modules.

For each module, ε controls the level of perturbation/noise injected:
- ε=0: deterministic/baseline operation
- ε=1: maximum noise/chaos

Measures: diversity (pairwise distance), structure (compression ratio),
          and emergence (sudden metric jumps).
"""

import numpy as np
import gzip
import json
import random
import sys
from itertools import combinations

epsilons = np.arange(0, 1.01, 0.1)
N_TRIALS = 5
results = {}


def diversity(outputs):
    """Mean pairwise cosine-like distance between string outputs."""
    if len(outputs) < 2:
        return 0.0
    # Convert strings to character frequency vectors
    char_sets = set()
    for o in outputs:
        char_sets.update(o[:500])  # sample first 500 chars
    char_list = sorted(char_sets)
    vecs = []
    for o in outputs:
        sample = o[:500]
        vec = [sample.count(c) for c in char_list]
        vecs.append(np.array(vec, dtype=float))
    dists = [np.linalg.norm(a - b) for a, b in combinations(vecs, 2)]
    return float(np.mean(dists)) if dists else 0.0


def compression_ratio(data):
    """Gzip compression ratio: lower = more structure/patterns."""
    raw = '\n'.join(str(d) for d in data).encode()
    if not raw:
        return 1.0
    return len(gzip.compress(raw)) / len(raw)


def detect_emergence(metric_list):
    """Find epsilon values where metrics jump suddenly."""
    jumps = []
    for i in range(1, len(metric_list)):
        delta = abs(metric_list[i] - metric_list[i-1])
        mean_delta = np.mean([abs(metric_list[j] - metric_list[j-1])
                              for j in range(1, len(metric_list))]) if len(metric_list) > 1 else 1
        if mean_delta > 0 and delta > 2 * mean_delta:
            jumps.append({
                'epsilon': float(epsilons[i]),
                'from': float(metric_list[i-1]),
                'to': float(metric_list[i]),
                'delta': float(delta)
            })
    return jumps


# ═══════════════════════════════════════════════════════════════════════
# Module 1: MusicalCell — inject noise into genome weights
# ═══════════════════════════════════════════════════════════════════════
print("=== MusicalCell ε-sweep ===")
try:
    from flux_tensor_midi.living import MusicalCell

    GENOME_SIZE = 25
    cell_results = []
    for eps in epsilons:
        outputs = []
        for trial in range(N_TRIALS):
            # Base genome
            base_genome = [0.5] * GENOME_SIZE
            # Inject ε-controlled noise
            genome = [max(0, min(1, g + np.random.normal(0, eps)))
                      for g in base_genome]
            cell = MusicalCell(name=f"cell_{trial}", genome=genome, channel=0)
            # Run ticks and collect state
            states = []
            for tick in range(20):
                try:
                    events = cell.express(context={
                        'bar_position': tick * 0.25,
                        'beat': tick % 4,
                        'epsilon': eps
                    })
                    state = {
                        'energy': cell.energy,
                        'last_pitch': cell._last_pitch,
                        'n_events': len(events),
                        'epigenetic': {str(k): round(v, 3)
                                       for k, v in list(cell.epigenetic_state.items())[:5]}
                    }
                    states.append(state)
                except Exception:
                    states.append({'tick': tick, 'error': True})
            outputs.append(str(states))

        div = diversity(outputs)
        comp = compression_ratio(outputs)
        cell_results.append({
            'epsilon': float(eps),
            'diversity': div,
            'compression': comp
        })
        print(f"  ε={eps:.1f}: diversity={div:.4f}, compression={comp:.4f}")

    cell_results_with_emergence = cell_results.copy()
    emergence_div = detect_emergence([r['diversity'] for r in cell_results])
    emergence_comp = detect_emergence([r['compression'] for r in cell_results])
    results['cell'] = {
        'data': cell_results,
        'emergence_diversity': emergence_div,
        'emergence_compression': emergence_comp
    }
    if emergence_div:
        print(f"  ⚡ Diversity emergence at: {[j['epsilon'] for j in emergence_div]}")
    if emergence_comp:
        print(f"  ⚡ Compression emergence at: {[j['epsilon'] for j in emergence_comp]}")

except Exception as e:
    print(f"  SKIP: {e}")
    import traceback; traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════
# Module 2: GeneRegulatoryNetwork — inject noise into concentrations
# ═══════════════════════════════════════════════════════════════════════
print("\n=== GeneRegulatoryNetwork ε-sweep ===")
try:
    from flux_tensor_midi.gene_regulatory import GeneRegulatoryNetwork

    grn_results = []
    for eps in epsilons:
        outputs = []
        for trial in range(N_TRIALS):
            grn = GeneRegulatoryNetwork(seed=42 + trial)
            # Inject noise into initial concentrations
            for gene_name in grn.concentrations:
                base = grn.concentrations[gene_name]
                grn.concentrations[gene_name] = max(0, min(1,
                    base + np.random.normal(0, eps)))

            states = []
            for step_i in range(30):
                # Add noise during stepping
                grn.step()
                # Record concentration snapshot
                snap = {k: round(v, 4) for k, v in grn.concentrations.items()}
                states.append(snap)
                # Inject noise per step
                for gene_name in grn.concentrations:
                    grn.concentrations[gene_name] = max(0, min(1,
                        grn.concentrations[gene_name] + np.random.normal(0, eps * 0.1)))

            outputs.append(str(states))

        div = diversity(outputs)
        comp = compression_ratio(outputs)
        grn_results.append({
            'epsilon': float(eps),
            'diversity': div,
            'compression': comp
        })
        print(f"  ε={eps:.1f}: diversity={div:.4f}, compression={comp:.4f}")

    emergence_div = detect_emergence([r['diversity'] for r in grn_results])
    emergence_comp = detect_emergence([r['compression'] for r in grn_results])
    results['grn'] = {
        'data': grn_results,
        'emergence_diversity': emergence_div,
        'emergence_compression': emergence_comp
    }
    if emergence_div:
        print(f"  ⚡ Diversity emergence at: {[j['epsilon'] for j in emergence_div]}")
    if emergence_comp:
        print(f"  ⚡ Compression emergence at: {[j['epsilon'] for j in emergence_comp]}")

except Exception as e:
    print(f"  SKIP: {e}")
    import traceback; traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════
# Module 3: MusicalEmbryo — inject noise into genome + morphogen sensitivity
# ═══════════════════════════════════════════════════════════════════════
print("\n=== MusicalEmbryo ε-sweep ===")
try:
    from flux_tensor_midi.embryonic import MusicalEmbryo

    emb_results = []
    for eps in epsilons:
        outputs = []
        for trial in range(N_TRIALS):
            # Seed genome with ε-noise
            genome = [max(0, min(1, 0.5 + np.random.normal(0, eps)))
                      for _ in range(25)]
            embryo = MusicalEmbryo(
                seed_genome=genome,
                dimensions=2,
                max_cells=200,
                random_seed=100 + trial
            )
            # Run development with fewer steps for speed
            embryo._setup_morphogens()
            snapshots = []
            for step_i in range(50):
                embryo.tick()
                # Inject noise into morphogen concentrations
                for morphogen in embryo.morphogens:
                    morphogen.initial_concentration += np.random.normal(0, eps * 0.05)

                snap = {
                    'stage': embryo.stage,
                    'n_cells': len(embryo.get_alive_cells()),
                    'n_differentiated': len(embryo.get_differentiated_cells()),
                    'roles': embryo.get_role_distribution()
                }
                snapshots.append(snap)

            outputs.append(str(snapshots))

        div = diversity(outputs)
        comp = compression_ratio(outputs)
        emb_results.append({
            'epsilon': float(eps),
            'diversity': div,
            'compression': comp
        })
        print(f"  ε={eps:.1f}: diversity={div:.4f}, compression={comp:.4f}")

    emergence_div = detect_emergence([r['diversity'] for r in emb_results])
    emergence_comp = detect_emergence([r['compression'] for r in emb_results])
    results['embryonic'] = {
        'data': emb_results,
        'emergence_diversity': emergence_div,
        'emergence_compression': emergence_comp
    }
    if emergence_div:
        print(f"  ⚡ Diversity emergence at: {[j['epsilon'] for j in emergence_div]}")
    if emergence_comp:
        print(f"  ⚡ Compression emergence at: {[j['epsilon'] for j in emergence_comp]}")

except Exception as e:
    print(f"  SKIP: {e}")
    import traceback; traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════
# Module 4: MusicalImmuneSystem — inject noise into antigen patterns
# ═══════════════════════════════════════════════════════════════════════
print("\n=== MusicalImmuneSystem ε-sweep ===")
try:
    from flux_tensor_midi.immune_system import MusicalImmuneSystem

    imm_results = []
    for eps in epsilons:
        outputs = []
        for trial in range(N_TRIALS):
            immune = MusicalImmuneSystem()
            # Generate input events with ε-controlled noise
            events = []
            for i in range(40):
                base_note = 60 + (i % 12)
                note = int(base_note + np.random.normal(0, eps * 12))
                events.append({
                    'note': note,
                    'velocity': int(max(1, min(127, 80 + np.random.normal(0, eps * 40)))),
                    'duration': max(0.1, 0.5 + np.random.normal(0, eps * 0.3)),
                    'time': i * 0.25
                })

            # Register some self-patterns
            immune.register_self(events[:4], label="theme")
            immune.register_self(events[8:12], label="bridge")

            antigens = immune.scan(events)
            response = immune.respond(events, antigens)

            output_state = {
                'n_antigens': len(antigens),
                'antigen_types': [a.antigen_type.value if hasattr(a.antigen_type, 'value')
                                  else str(a.antigen_type) for a in antigens],
                'n_response_events': len(response),
                'n_antibodies': len(immune.adaptive.antibodies),
                'response_log_len': len(immune.response_log),
            }
            outputs.append(str(output_state))

        div = diversity(outputs)
        comp = compression_ratio(outputs)
        imm_results.append({
            'epsilon': float(eps),
            'diversity': div,
            'compression': comp
        })
        print(f"  ε={eps:.1f}: diversity={div:.4f}, compression={comp:.4f}")

    emergence_div = detect_emergence([r['diversity'] for r in imm_results])
    emergence_comp = detect_emergence([r['compression'] for r in imm_results])
    results['immune'] = {
        'data': imm_results,
        'emergence_diversity': emergence_div,
        'emergence_compression': emergence_comp
    }
    if emergence_div:
        print(f"  ⚡ Diversity emergence at: {[j['epsilon'] for j in emergence_div]}")
    if emergence_comp:
        print(f"  ⚡ Compression emergence at: {[j['epsilon'] for j in emergence_comp]}")

except Exception as e:
    print(f"  SKIP: {e}")
    import traceback; traceback.print_exc()


# ═══════════════════════════════════════════════════════════════════════
# Save results
# ═══════════════════════════════════════════════════════════════════════
with open('experiments/EXPERIMENT-EPSILON-SWEEP.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 60)
print("=== SUMMARY ===")
print("=" * 60)
for module, data in results.items():
    module_data = data.get('data', data) if isinstance(data, dict) else data
    if isinstance(module_data, list) and module_data:
        best_div = max(module_data, key=lambda x: x.get('diversity', 0))
        best_comp = min(module_data, key=lambda x: x.get('compression', 1))
        print(f"\n{module}:")
        print(f"  Peak diversity: ε={best_div['epsilon']:.1f} (div={best_div['diversity']:.4f})")
        print(f"  Most structured: ε={best_comp['epsilon']:.1f} (comp={best_comp['compression']:.4f})")
        # Emergence
        em = data.get('emergence_diversity', []) if isinstance(data, dict) else []
        if em:
            print(f"  ⚡ Emergence jumps at ε={[j['epsilon'] for j in em]}")

print("\nResults saved to experiments/EXPERIMENT-EPSILON-SWEEP.json")
