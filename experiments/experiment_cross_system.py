"""
Cross-System Interaction Experiment
Wire multiple living systems together and observe emergent behavior.
"""
import numpy as np
import json
import traceback

ALL_RESULTS = {}

# ============================================================
# Experiment 1: Ecosystem dynamics (immune + ecosystem model)
# ============================================================
try:
    from flux_tensor_midi.ecosystem import MusicalEcosystem, MusicalSpecies

    print("=== Cross-System Experiment: Ecosystem Dynamics ===\n")

    eco = MusicalEcosystem(epsilon=0.5, seed=42)
    for name in ['Jazz', 'Blues', 'Rock', 'Classical', 'HipHop']:
        genome = np.random.RandomState(hash(name) % 2**31).rand(25).tolist()
        eco.add_species(MusicalSpecies(name=name, genome=genome))

    for i in range(50):
        eco.tick()

    biodiversity_before = eco.biodiversity()
    living_before = [s.name for s in eco.living_species()]
    print(f"Before perturbation: biodiversity={biodiversity_before:.4f}")
    print(f"Living species: {living_before}")

    # Phase 2: Introduce invasive species
    print("\n--- Invasive species arrives ---")
    invasive = MusicalSpecies(name='InvasivePop', genome=np.random.rand(25).tolist())
    eco.add_species(invasive)
    for i in range(50):
        eco.tick()

    biodiversity_after = eco.biodiversity()
    living_after = [s.name for s in eco.living_species()]
    print(f"After invasion: biodiversity={biodiversity_after:.4f}")
    print(f"Surviving: {living_after}")

    # Phase 3: Extinction event
    print("\n--- Extinction event ---")
    eco.extinction_event(intensity=0.5)
    for i in range(30):
        eco.tick()

    biodiversity_post = eco.biodiversity()
    living_post = [s.name for s in eco.living_species()]
    print(f"After extinction: biodiversity={biodiversity_post:.4f}")
    print(f"Surviving: {living_post}")

    # Phase 4: Succession / recovery
    print("\n--- Succession / recovery phase ---")
    for i in range(50):
        eco.tick()

    biodiversity_recovery = eco.biodiversity()
    living_recovery = [s.name for s in eco.living_species()]
    print(f"After recovery: biodiversity={biodiversity_recovery:.4f}")
    print(f"Surviving: {living_recovery}")

    summary = eco.summary()
    print(f"\nEcosystem summary: {json.dumps(summary, indent=2, default=str)}")

    ALL_RESULTS['ecosystem'] = {
        'biodiversity_before': float(biodiversity_before),
        'living_before': living_before,
        'biodiversity_after_invasion': float(biodiversity_after),
        'living_after_invasion': living_after,
        'biodiversity_post_extinction': float(biodiversity_post),
        'living_post_extinction': living_post,
        'biodiversity_recovery': float(biodiversity_recovery),
        'living_recovery': living_recovery,
        'summary': summary,
    }
except Exception as e:
    print(f"Ecosystem experiment FAILED: {e}")
    traceback.print_exc()
    ALL_RESULTS['ecosystem_error'] = str(e)

# ============================================================
# Experiment 2: Gene Regulatory Network → Cell
# ============================================================
try:
    from flux_tensor_midi.gene_regulatory import GeneRegulatoryNetwork
    from flux_tensor_midi.living import MusicalCell, SignalType

    print("\n=== Cross-System: GRN → Cell ===\n")

    grn = GeneRegulatoryNetwork(seed=123)
    history = grn.simulate(steps=50)
    print(f"GRN simulated {len(history)} steps")
    final_state = history[-1] if history else {}
    print(f"Final GRN state keys: {list(final_state.keys())[:10]}")
    print(f"Final GRN state sample: {dict(list(final_state.items())[:5])}")

    cell = MusicalCell(name='GRNCell', genome=np.random.rand(25).tolist())
    sig_types = list(SignalType)

    cell_states = []
    for tick in range(20):
        grn_state = grn.step()
        signals = {}
        for idx, (key, val) in enumerate(grn_state.items()):
            if isinstance(val, (int, float)) and idx < len(sig_types):
                signals[sig_types[idx]] = float(val)

        if signals:
            cell.update_tfs(signals)
            cell.receive(signals)

        events = cell.express()
        output = cell.emit(events if events else None)

        state = {
            'tick': tick,
            'energy': float(cell.energy),
            'grn_genes_active': sum(1 for v in grn_state.values() if isinstance(v, (int, float)) and v > 0.5),
            'n_events': len(events) if events else 0,
        }
        cell_states.append(state)
        if tick % 5 == 0:
            print(f"Tick {tick}: energy={cell.energy:.3f}, active_genes={state['grn_genes_active']}, events={state['n_events']}")

    ALL_RESULTS['grn_cell'] = {
        'cell_states': cell_states,
        'grn_final_state_sample': {str(k): float(v) for k, v in list(final_state.items())[:10] if isinstance(v, (int, float))},
    }
except Exception as e:
    print(f"GRN→Cell experiment FAILED: {e}")
    traceback.print_exc()
    ALL_RESULTS['grn_cell_error'] = str(e)

# ============================================================
# Experiment 3: Protein Folding Energy Landscape
# ============================================================
try:
    from flux_tensor_midi.protein_fold import ProteinFolder

    print("\n=== Protein Folding Energy Landscape ===\n")

    aa_names = ['A','G','S','V','L','I','P','F','Y','W','N','Q','D','E','H','K','R','C','M','T']
    rng = np.random.RandomState(99)
    results_by_sequence = []

    for seq_idx in range(5):
        seq_len = rng.randint(10, 25)
        sequence = ''.join(rng.choice(aa_names, seq_len))
        try:
            folder = ProteinFolder(sequence=sequence, seed=seq_idx)
            coords = folder.fold(max_steps=500)
            energy = folder.energy()
            rg = folder.radius_of_gyration()
            folded = folder.is_folded  # property, not method

            results_by_sequence.append({
                'sequence': sequence,
                'length': seq_len,
                'energy': float(energy),
                'radius_of_gyration': float(rg),
                'is_folded': bool(folded),
                'n_coords': len(coords) if coords else 0,
            })
            print(f"Seq {seq_idx} ({len(sequence)}aa): E={energy:.2f}, Rg={rg:.2f}, folded={folded}")
        except Exception as e:
            print(f"Seq {seq_idx} ({sequence}) failed: {e}")
            results_by_sequence.append({'sequence': sequence, 'error': str(e)})

    # Energy funnel analysis
    print("\n--- Energy Funnel Analysis ---")
    seq = ''.join(rng.choice(aa_names, 15))
    folder = ProteinFolder(sequence=seq, seed=42)
    coords = folder.fold(max_steps=1000)
    if coords and len(coords) > 1:
        funnel_pt = folder.energy_funnel((0.0, 0.0), coords[-1])
        print(f"Energy funnel origin→end: {funnel_pt}")
    else:
        funnel_pt = None
        print("No coords for energy funnel")

    ALL_RESULTS['protein_folding'] = {
        'sequences': results_by_sequence,
        'energy_funnel_sample': funnel_pt,
    }
except Exception as e:
    print(f"Protein folding experiment FAILED: {e}")
    traceback.print_exc()
    ALL_RESULTS['protein_folding_error'] = str(e)

# ============================================================
# Experiment 4: Cross-system - Cell output feeds Ecosystem via GRN
# ============================================================
try:
    from flux_tensor_midi.ecosystem import MusicalEcosystem, MusicalSpecies
    from flux_tensor_midi.living import MusicalCell, SignalType
    from flux_tensor_midi.gene_regulatory import GeneRegulatoryNetwork

    print("\n=== Cross-System: Cell signals influence Ecosystem ===\n")

    rng = np.random.RandomState(77)
    eco2 = MusicalEcosystem(epsilon=0.3, seed=77)
    for name in ['Alpha', 'Beta', 'Gamma']:
        eco2.add_species(MusicalSpecies(name=name, genome=rng.rand(25).tolist()))

    cells = [MusicalCell(name=f'Cell_{i}', genome=rng.rand(25).tolist()) for i in range(3)]
    grn2 = GeneRegulatoryNetwork(seed=77)
    sig_types = list(SignalType)

    biodiversities = []
    cell_energies = []

    for tick in range(100):
        grn_state = grn2.step()
        for cell in cells:
            signals = {}
            for idx, (key, val) in enumerate(grn_state.items()):
                if isinstance(val, (int, float)) and idx < len(sig_types):
                    signals[sig_types[idx]] = float(val)
            if signals:
                cell.update_tfs(signals)
            events = cell.express()
            cell.emit(events)

        avg_energy = np.mean([c.energy for c in cells])
        cell_energies.append(float(avg_energy))
        eco2.tick()

        if tick % 20 == 0:
            bd = eco2.biodiversity()
            biodiversities.append(float(bd))
            living = [s.name for s in eco2.living_species()]
            print(f"Tick {tick}: biodiversity={bd:.4f}, cell_avg_energy={avg_energy:.3f}, living={living}")

    final_bd = eco2.biodiversity()
    biodiversities.append(float(final_bd))
    print(f"\nFinal biodiversity: {final_bd:.4f}")
    print(f"Final living species: {[s.name for s in eco2.living_species()]}")
    print(f"Final cell energies: {[c.energy for c in cells]}")

    ALL_RESULTS['cross_system'] = {
        'biodiversities': biodiversities,
        'cell_energies_sample': cell_energies[::10],
        'final_biodiversity': float(final_bd),
        'final_living': [s.name for s in eco2.living_species()],
        'final_cell_energies': [float(c.energy) for c in cells],
    }
except Exception as e:
    print(f"Cross-system experiment FAILED: {e}")
    traceback.print_exc()
    ALL_RESULTS['cross_system_error'] = str(e)

# ============================================================
# Save results
# ============================================================
output_path = 'experiments/EXPERIMENT-CROSS-SYSTEM.json'
with open(output_path, 'w') as f:
    json.dump(ALL_RESULTS, f, indent=2, default=str)
print(f"\nResults saved to {output_path}")
print(f"Result keys: {list(ALL_RESULTS.keys())}")
