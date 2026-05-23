import numpy as np
import json
import time

print("=== 1000-Tick Evolution Experiment ===\n")

results = {'ticks': [], 'events': []}

# Initialize all systems
from flux_tensor_midi.ecosystem import MusicalEcosystem, MusicalSpecies
from flux_tensor_midi.living import MusicalCell  
from flux_tensor_midi.gene_regulatory import GeneRegulatoryNetwork
from flux_tensor_midi.protein_fold import ProteinFolder
from flux_tensor_midi.immune_system import MusicalImmuneSystem, MusicalAntigen
from flux_tensor_midi.neural_music import MusicalBrain
from flux_tensor_midi.embryonic import EmbryonicEnsemble

# Ecosystem
eco = MusicalEcosystem(epsilon=0.5)
for name in ['Jazz', 'Blues', 'Rock', 'Classical', 'Electronic', 'Ambient', 'Folk', 'Metal']:
    genome = np.random.rand(25).tolist()
    eco.add_species(MusicalSpecies(name=name, genome=genome))

# Living cells (one per species)
cells = {name: MusicalCell(name=name, genome=np.random.rand(25).tolist()) for name in ['Jazz', 'Blues', 'Rock']}

# GRN
grn = GeneRegulatoryNetwork()

# Immune system
immune = MusicalImmuneSystem()

# Neural brain (use classmethod build)
brain = MusicalBrain.build(epsilon=0.5)

# Protein folder (takes sequence string)

# Embryo ensemble
embryo = EmbryonicEnsemble()

# Run for 1000 ticks
start = time.time()
checkpoints = [0, 50, 100, 200, 500, 750, 1000]

for tick in range(1001):
    # GRN step
    try:
        grn.step()
    except:
        pass
    
    # Cell ticks
    for cell in cells.values():
        try:
            cell.tick()
        except:
            pass
    
    # Ecosystem tick
    eco.tick()
    
    # Embryo development
    if tick < 100:
        try:
            embryo.develop()
        except:
            pass
    
    # Record at checkpoints
    if tick in checkpoints:
        biodiv = eco.biodiversity()
        surviving = len([s for s in eco.species if s.population > 0])
        
        # Fold a protein
        aa_names = ['A','C','D','E','F','G','H','I','K','L','M','N','P','Q','R','S','T','V','W','Y']
        seq_str = ''.join(np.random.choice(aa_names) for _ in range(10))
        folder = ProteinFolder(sequence=seq_str)
        folder.fold()
        energy = folder.energy() if callable(folder.energy) else (folder.energy or 0.0)
        
        # Brain output
        brain.hear([60 + int(biodiv * 12)])
        brain_output = brain.perform()
        n_events = sum(len(t.events) for t in brain_output.tracks) if brain_output and brain_output.tracks else 0
        
        elapsed = time.time() - start
        
        data = {
            'tick': tick,
            'biodiversity': biodiv,
            'surviving_species': surviving,
            'protein_energy': energy,
            'brain_events': n_events,
            'elapsed_seconds': round(elapsed, 2)
        }
        results['ticks'].append(data)
        results['events'].append(data)
        
        print(f"Tick {tick:4d}: bio={biodiv:.4f} | species={surviving}/8 | protein_E={energy:.1f} | brain={n_events} events | {elapsed:.1f}s")

# Final analysis
print(f"\n=== Summary ===")
print(f"Total runtime: {time.time()-start:.1f}s")
print(f"Ticks: {len(results['ticks'])} checkpoints")

biodiversities = [t['biodiversity'] for t in results['ticks']]
surviving_counts = [t['surviving_species'] for t in results['ticks']]
energies = [t['protein_energy'] for t in results['ticks']]

print(f"Biodiversity: {biodiversities[0]:.4f} → {biodiversities[-1]:.4f}")
print(f"Species: {surviving_counts[0]} → {surviving_counts[-1]}")
print(f"Protein energy range: {min(energies):.1f} — {max(energies):.1f}")

# Detect phase transitions (sudden jumps)
for i in range(1, len(biodiversities)):
    delta = abs(biodiversities[i] - biodiversities[i-1])
    if delta > 0.3:
        print(f"⚠️ Phase transition at tick {checkpoints[i]}: bio jumped {delta:.4f}")

with open('experiments/EXPERIMENT-LONG-EVOLUTION.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved.")
