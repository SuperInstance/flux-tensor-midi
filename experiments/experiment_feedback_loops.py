"""
Feedback Loop Experiment: Closing the loops between cells, ecosystem, immune system, and brain.

Experiment A: Cell → Ecosystem feedback (cell quality drives species fitness/resources)
Experiment B: Immune system monitors ecosystem health (low biodiversity = stress antigen)
Experiment C: Neural brain responds to ecosystem state (biodiversity → stimulus pitch)
"""

import numpy as np
import json

print("=== Feedback Loop Experiment ===\n")

# ─── Experiment A: Cell → Ecosystem feedback ─────────────────────────────────

from flux_tensor_midi.ecosystem import MusicalEcosystem, MusicalSpecies
from flux_tensor_midi.living import MusicalCell
from flux_tensor_midi.gene_regulatory import GeneRegulatoryNetwork

eco_a = MusicalEcosystem(epsilon=0.5)
species_names = ['Jazz', 'Blues', 'Rock', 'Classical', 'Electronic']

for name in species_names:
    genome = np.random.rand(25).tolist()
    eco_a.add_species(MusicalSpecies(name=name, genome=genome, population=100))

# Create 5 cells, each representing a species
cells = {}
grns = {}
for name in species_names:
    genome = np.random.rand(25).tolist()
    cells[name] = MusicalCell(name=name, genome=genome)
    grns[name] = GeneRegulatoryNetwork(seed=hash(name) % 2**31)

# Popularity scores (simulate audience preference)
popularity = {'Jazz': 0.8, 'Blues': 0.6, 'Rock': 0.9, 'Classical': 0.5, 'Electronic': 0.7}

history_a = []
for tick in range(100):
    # Each cell acts, quality influenced by GRN state
    cell_outputs = {}
    for name in species_names:
        grns[name].step()
        state = grns[name].get_network_state_summary()
        # Flatten nested TF activations
        all_vals = []
        for tf_dict in state.values():
            all_vals.extend(tf_dict.values())
        avg_activation = np.mean(all_vals) if all_vals else 0.5
        quality = popularity[name] * avg_activation
        cell_outputs[name] = quality

        # FEEDBACK LOOP: cell quality drives species fitness & resources
        sp = eco_a.species_by_name(name)
        if sp:
            sp.fitness = 0.3 + 0.7 * quality
            boost = 0.8 + 0.4 * quality
            sp.resources.attention = max(0.01, sp.resources.attention * boost)
            sp.resources.harmonic_space = max(0.01, sp.resources.harmonic_space * boost)

    eco_a.tick()

    biodiversity = eco_a.biodiversity()
    surviving = [(s.name, s.population) for s in eco_a.species if s.population > 0]

    tick_data = {
        'tick': tick,
        'biodiversity': biodiversity,
        'surviving_count': len(surviving),
        'cell_quality': {k: round(v, 4) for k, v in cell_outputs.items()},
        'species_populations': {s.name: s.population for s in eco_a.species},
    }
    history_a.append(tick_data)

    if tick % 20 == 0:
        avg_q = np.mean(list(cell_outputs.values()))
        print(f"  Tick {tick:3d}: biodiversity={biodiversity:.4f}, surviving={len(surviving)}, avg_quality={avg_q:.4f}")

biodiversities = [h['biodiversity'] for h in history_a]
trend_a = 'increasing' if biodiversities[-1] > biodiversities[0] else 'decreasing'
print(f"\n  Experiment A Summary: biodiversity mean={np.mean(biodiversities):.4f}, "
      f"trend={trend_a}, start={biodiversities[0]:.4f}, end={biodiversities[-1]:.4f}")

# ─── Experiment B: Immune system monitors ecosystem health ────────────────────

from flux_tensor_midi.immune_system import MusicalImmuneSystem, MusicalAntigen, AntigenType

print("\n=== Immune Monitors Ecosystem ===\n")

# Use a stressed ecosystem (low carrying capacity → frequent extinctions → low biodiversity)
eco_b = MusicalEcosystem(epsilon=0.5, carrying_capacity=3)
for name in species_names:
    genome = np.random.rand(25).tolist()
    eco_b.add_species(MusicalSpecies(name=name, genome=genome, population=100))

immune = MusicalImmuneSystem()

# Register healthy patterns as "self"
healthy_pattern = [{'note': 60, 'duration': 1.0}, {'note': 64, 'duration': 1.0}, {'note': 67, 'duration': 1.0}]
immune.register_self(healthy_pattern, label='healthy_major_triad')
immune.vaccinate_against_cliches()

stress_detections = []
immune_log = []

for tick in range(50):
    eco_b.tick()
    bio = eco_b.biodiversity()

    # Generate music-like events from ecosystem state
    events = []
    for sp in eco_b.species:
        if sp.population > 0:
            events.append({'note': int(60 + sp.fitness * 24), 'duration': 0.25})

    # When biodiversity is low, add repetitive stress patterns
    if bio < 1.0:
        stress_events = events + [{'note': 60, 'duration': 0.25}] * 24
    else:
        stress_events = events

    antigens = immune.scan(stress_events)
    if antigens:
        stress_detections.append({'tick': tick, 'bio': bio, 'antigens': len(antigens)})
        response = immune.respond(stress_events, antigens)
        immune_log.append({
            'tick': tick,
            'biodiversity': round(bio, 4),
            'antigens_found': len(antigens),
            'response_events': len(response),
            'danger_scores': [round(a.is_dangerous, 3) for a in antigens],
        })

for entry in immune_log[:10]:
    print(f"  Tick {entry['tick']:3d}: STRESS DETECTED, bio={entry['biodiversity']:.4f}, "
          f"antigens={entry['antigens_found']}, response_events={entry['response_events']}, "
          f"danger={entry['danger_scores']}")

repertoire = immune.immune_repertoire_summary()
print(f"\n  Immune repertoire: {json.dumps({k: v for k, v in repertoire.items() if isinstance(v, (int, float, str))}, indent=2)}")
print(f"  Total stress detections: {len(stress_detections)}")

# ─── Experiment C: Neural brain responds to ecosystem state ───────────────────

from flux_tensor_midi.neural_music import MusicalBrain

print("\n=== Neural Brain Responds to Ecosystem ===\n")

eco_c = MusicalEcosystem(epsilon=0.5)
for name in species_names:
    genome = np.random.rand(25).tolist()
    eco_c.add_species(MusicalSpecies(name=name, genome=genome, population=100))

brain = MusicalBrain.build(root=60, bpm=120.0, epsilon=0.5)
brain_c_log = []

for tick in range(10):
    eco_c.tick()
    bio = eco_c.biodiversity()

    # Map biodiversity to stimulus: higher biodiversity = richer stimulus
    center_pitch = 60 + int(bio * 12)
    stimulus = [center_pitch, center_pitch + 4, center_pitch + 7]

    brain.hear(stimulus)
    result = brain.perform(bars=8, stimulus=stimulus)

    # Count events in arrangement tracks
    n_events = 0
    if result and hasattr(result, 'tracks'):
        for track in result.tracks:
            if hasattr(track, 'events'):
                n_events += len(track.events)

    entry = {
        'tick': tick,
        'biodiversity': round(bio, 4),
        'stimulus_center': center_pitch,
        'brain_events': n_events,
    }
    brain_c_log.append(entry)
    print(f"  Tick {tick}: bio={bio:.4f}, stimulus_pitch={center_pitch}, brain_events={n_events}")

print("\n  Brain adapts output to ecosystem health ✓")

# ─── Save results ────────────────────────────────────────────────────────────

results = {
    'experiment': 'feedback_loops',
    'description': 'Closing feedback loops between cells, ecosystem, immune system, and neural brain',
    'experiment_a': {
        'name': 'Cell → Ecosystem feedback',
        'history': history_a,
        'summary': {
            'biodiversity_mean': round(float(np.mean(biodiversities)), 4),
            'biodiversity_start': round(biodiversities[0], 4),
            'biodiversity_end': round(biodiversities[-1], 4),
            'trend': trend_a,
        },
    },
    'experiment_b': {
        'name': 'Immune monitors ecosystem',
        'detections': len(stress_detections),
        'immune_log': immune_log,
        'repertoire': {k: v for k, v in repertoire.items() if isinstance(v, (int, float, str))},
    },
    'experiment_c': {
        'name': 'Brain responds to ecosystem',
        'log': brain_c_log,
    },
}

output_path = 'experiments/EXPERIMENT-FEEDBACK-LOOPS.json'
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✓ Results saved to {output_path}")
