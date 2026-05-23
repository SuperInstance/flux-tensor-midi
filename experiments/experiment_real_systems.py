"""
Real experiments using the actual flux-tensor-midi codebase.

Experiment A: Protein Folding — Energy & Time vs snap_epsilon
Experiment B: Ecosystem — Biodiversity over time
Experiment C: Immune System — Primary vs Secondary response
Experiment D: Neural Network — Performance outputs
"""

import json
import sys
import time
import traceback
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, "/home/phoenix/.openclaw/workspace/flux-tensor-midi")

results = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "experiments": {},
}

# ============================================================================
# Experiment A: Protein Folding Speed vs ε (snap_epsilon)
# ============================================================================
print("=" * 70)
print("EXPERIMENT A: Protein Folding Energy & Time vs snap_epsilon")
print("=" * 70)

try:
    from flux_tensor_midi.protein_fold import ProteinFolder

    aa_pool = "ACDEFGHIKLMNPQRSTVWY"
    protein_results = []

    for epsilon in np.arange(0, 1.01, 0.1):
        times = []
        energies = []
        fold_counts = []
        for trial in range(5):
            # Random 20-residue sequence
            rng = np.random.default_rng(seed=trial * 1000 + int(epsilon * 100))
            seq = "".join(rng.choice(list(aa_pool), size=20))

            folder = ProteinFolder(
                sequence=seq,
                seed=trial,
                constraints={"snap_epsilon": round(epsilon, 2)},
            )
            start = time.time()
            positions = folder.fold()
            elapsed = time.time() - start

            energy = folder.energy() if hasattr(folder, "energy") and callable(folder.energy) else 0.0
            times.append(elapsed)
            energies.append(energy)
            fold_counts.append(len(positions))

        entry = {
            "epsilon": round(float(epsilon), 2),
            "avg_time": float(np.mean(times)),
            "avg_energy": float(np.mean(energies)),
            "energy_std": float(np.std(energies)),
            "avg_fold_positions": float(np.mean(fold_counts)),
        }
        protein_results.append(entry)
        print(
            f"  ε={epsilon:.1f}: time={np.mean(times):.4f}s, "
            f"energy={np.mean(energies):.2f}±{np.std(energies):.2f}, "
            f"positions={np.mean(fold_counts):.0f}"
        )

    results["experiments"]["A_protein_folding"] = protein_results
    print("  ✅ Experiment A complete\n")

except Exception as e:
    print(f"  ❌ Experiment A failed: {e}")
    traceback.print_exc()
    results["experiments"]["A_protein_folding"] = {"error": str(e)}
    print()


# ============================================================================
# Experiment B: Ecosystem Biodiversity vs time
# ============================================================================
print("=" * 70)
print("EXPERIMENT B: Ecosystem Biodiversity over 100 ticks")
print("=" * 70)

try:
    from flux_tensor_midi.ecosystem import MusicalEcosystem, MusicalSpecies, Niche
    from flux_tensor_midi.ecosystem import Resources

    ecosystem_results = []

    for run_seed in [42, 123, 999]:
        eco = MusicalEcosystem(seed=run_seed)
        species_names = ["Jazz", "Blues", "Rock", "Classical", "HipHop", "Techno"]
        niches = list(Niche)
        rng = np.random.default_rng(seed=run_seed)

        for i, name in enumerate(species_names):
            genome = rng.random(25).tolist()
            niche = niches[i % len(niches)]
            species = MusicalSpecies(
                name=name,
                genome=genome,
                niche=niche,
                population=100,
            )
            eco.add_species(species)

        biodiversity_history = []
        surviving_history = []

        for tick in range(100):
            eco.tick()
            bio = eco.biodiversity()
            surviving = len(eco.living_species()) if hasattr(eco, "living_species") else len(
                [s for s in eco.species if getattr(s, "population", 0) > 0]
            )
            biodiversity_history.append(bio)
            surviving_history.append(surviving)

        entry = {
            "seed": run_seed,
            "final_biodiversity": float(biodiversity_history[-1]),
            "max_biodiversity": float(max(biodiversity_history)),
            "min_biodiversity": float(min(biodiversity_history)),
            "final_surviving": surviving_history[-1],
            "biodiversity_trajectory": [float(x) for x in biodiversity_history[::10]],
            "surviving_trajectory": surviving_history[::10],
        }
        ecosystem_results.append(entry)
        print(
            f"  seed={run_seed}: final_biodiversity={entry['final_biodiversity']:.4f}, "
            f"surviving={entry['final_surviving']}/{len(species_names)}, "
            f"max_bio={entry['max_biodiversity']:.4f}"
        )

    results["experiments"]["B_ecosystem"] = ecosystem_results
    print("  ✅ Experiment B complete\n")

except Exception as e:
    print(f"  ❌ Experiment B failed: {e}")
    traceback.print_exc()
    results["experiments"]["B_ecosystem"] = {"error": str(e)}
    print()


# ============================================================================
# Experiment C: Immune System Learning
# ============================================================================
print("=" * 70)
print("EXPERIMENT C: Immune System Primary vs Secondary Response")
print("=" * 70)

try:
    from flux_tensor_midi.immune_system import MusicalImmuneSystem

    immune_results = []

    # Create a "pathogenic" musical pattern (cliché: repeated same notes)
    pathogen_events = [
        {"note": 60, "velocity": 100, "duration": 0.5, "time": i * 0.5}
        for i in range(8)
    ]

    # And a healthy pattern
    healthy_events = [
        {"note": 60 + i * 2, "velocity": 80, "duration": 0.25, "time": i * 0.25}
        for i in range(8)
    ]

    for trial_seed in [42, 123, 456]:
        immune = MusicalImmuneSystem()

        # Register healthy pattern as self
        immune.register_self(healthy_events, label="healthy_scale")

        # Primary response — first exposure to pathogen
        antigens_primary = immune.scan(pathogen_events)
        response_primary = immune.respond(pathogen_events, antigens_primary)

        # Secondary response — second exposure (should be faster/stronger)
        antigens_secondary = immune.scan(pathogen_events)
        response_secondary = immune.respond(pathogen_events, antigens_secondary)

        # Tertiary for good measure
        antigens_tertiary = immune.scan(pathogen_events)
        response_tertiary = immune.respond(pathogen_events, antigens_tertiary)

        # Now scan the healthy self-pattern (should be tolerated)
        self_antigens = immune.scan(healthy_events)

        entry = {
            "seed": trial_seed,
            "primary_antigens": len(antigens_primary),
            "secondary_antigens": len(antigens_secondary),
            "tertiary_antigens": len(antigens_tertiary),
            "primary_response_len": len(response_primary),
            "secondary_response_len": len(response_secondary),
            "tertiary_response_len": len(response_tertiary),
            "self_tolerance_antigens": len(self_antigens),
            "adaptive_antibodies": len(immune.adaptive.antibodies) if hasattr(immune.adaptive, "antibodies") else 0,
            "response_log_entries": len(immune.response_log),
        }
        immune_results.append(entry)
        print(
            f"  seed={trial_seed}: "
            f"antigens(P/S/T)={len(antigens_primary)}/{len(antigens_secondary)}/{len(antigens_tertiary)}, "
            f"response_len(P/S/T)={len(response_primary)}/{len(response_secondary)}/{len(response_tertiary)}, "
            f"self_antigens={len(self_antigens)}, "
            f"antibodies={entry['adaptive_antibodies']}"
        )

    results["experiments"]["C_immune_system"] = immune_results
    print("  ✅ Experiment C complete\n")

except Exception as e:
    print(f"  ❌ Experiment C failed: {e}")
    traceback.print_exc()
    results["experiments"]["C_immune_system"] = {"error": str(e)}
    print()


# ============================================================================
# Experiment D: Neural Network — Brain Performance
# ============================================================================
print("=" * 70)
print("EXPERIMENT D: Neural Network Brain Performance")
print("=" * 70)

try:
    from flux_tensor_midi.neural_music import MusicalBrain

    neural_results = []

    for seed in [42, 123, 456, 789, 1337]:
        brain = MusicalBrain.build(root=60, bpm=120.0, seed=seed)

        # Perform multiple times and track output
        performances = []
        for perf_num in range(5):
            arrangement = brain.perform(bars=8)
            events_count = len(arrangement.events) if hasattr(arrangement, "events") else 0
            performances.append({
                "performance": perf_num,
                "events": events_count,
                "brain_tick": brain.tick,
            })

        entry = {
            "seed": seed,
            "performances": performances,
            "total_events": sum(p["events"] for p in performances),
            "cortex_count": len(brain.layers),
            "synapse_count": len(brain.synapses),
            "learning_rate": brain.learning_rate,
        }
        neural_results.append(entry)
        event_str = ", ".join(str(p["events"]) for p in performances)
        print(
            f"  seed={seed}: events_per_perf=[{event_str}], "
            f"cortices={len(brain.layers)}, synapses={len(brain.synapses)}"
        )

    results["experiments"]["D_neural_music"] = neural_results
    print("  ✅ Experiment D complete\n")

except Exception as e:
    print(f"  ❌ Experiment D failed: {e}")
    traceback.print_exc()
    results["experiments"]["D_neural_music"] = {"error": str(e)}
    print()


# ============================================================================
# Save results
# ============================================================================
output_path = "/home/phoenix/.openclaw/workspace/flux-tensor-midi/experiments/EXPERIMENT-REAL-RESULTS.json"
with open(output_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"Results saved to {output_path}")
print("=" * 70)
print("ALL EXPERIMENTS COMPLETE")
print("=" * 70)
