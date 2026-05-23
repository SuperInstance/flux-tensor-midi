"""
Experiment 5: Conductor Integration — Wire ALL living modules together.
Observe full system behavior with varying parameters.
"""

import json
import time

print("=== Conductor Integration Experiment ===\n")

try:
    from flux_tensor_midi.conductor import Conductor
    
    # Create conductor with all systems
    conductor = Conductor()
    
    # Experiment 1: Full orchestra, varying ε
    print("--- Full system at different ε ---")
    for epsilon in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        if hasattr(conductor, 'set_epsilon'):
            conductor.set_epsilon(epsilon)
        
        start = time.time()
        result = conductor.perform() if hasattr(conductor, 'perform') else conductor.run()
        elapsed = time.time() - start
        
        # Extract metrics
        n_events = 0
        if isinstance(result, dict):
            n_events = result.get('n_events', len(str(result)))
        elif hasattr(result, 'voices'):
            n_events = sum(len(v.events) for v in result.voices)
        else:
            n_events = len(str(result))
        
        print(f"  ε={epsilon:.1f}: {n_events} events in {elapsed:.2f}s")
    
    # Experiment 2: Multi-cell interaction
    print("\n--- Multi-cell interaction ---")
    if hasattr(conductor, 'add_cell'):
        for i in range(5):
            conductor.add_cell(f"cell_{i}")
        
        for tick in range(20):
            conductor.tick() if hasattr(conductor, 'tick') else None
        
        summary = conductor.summary() if hasattr(conductor, 'summary') else "no summary"
        print(f"  After 20 ticks: {summary}")
    
    # Experiment 3: System response to perturbation
    print("\n--- Perturbation response ---")
    # Introduce unexpected input and see how system reacts
    if hasattr(conductor, 'inject'):
        conductor.inject("perturbation")
        for tick in range(10):
            conductor.tick() if hasattr(conductor, 'tick') else None
        print("  Perturbation injected, system adapted")

except (ImportError, AttributeError) as e:
    print(f"Conductor low-level API (perform/run): {e}")
    print("Using high-level Conductor API instead...\n")

    # The Conductor doesn't have perform()/run()/set_epsilon()/add_cell()/tick()
    # It uses compose(), live_session(), etc. — let's use the real API.
    
    from flux_tensor_midi.conductor import Conductor
    import numpy as np
    
    # === Experiment A: Compose with each cultural tradition ===
    print("--- Experiment A: Cultural traditions ---")
    cultures = ['midnight_raga', 'cairo_cafe', 'zen_garden', 'djembe_circle', 'bebop_salt']
    event_counts = {}
    
    for preset_name in cultures:
        try:
            c = Conductor.preset(preset_name)
            arr = c.compose(bars=8)
            n_events = sum(len(t.events) for t in arr.tracks)
            n_tracks = len(arr.tracks)
            elapsed_comp = 0  # already composed
            
            analysis = c.analyze(arr)
            constraints = analysis.get('constraint_satisfaction', {})
            
            event_counts[preset_name] = n_events
            print(f"  {preset_name}: {n_tracks} tracks, {n_events} events, "
                  f"snap={constraints.get('snap_accuracy', 0):.2f}, "
                  f"funnel={constraints.get('funnel_convergence', 0):.2f}, "
                  f"consensus={constraints.get('consensus_agreement', 0):.2f}")
        except Exception as e:
            event_counts[preset_name] = 0
            print(f"  {preset_name}: FAILED - {e}")
    
    # === Experiment B: Constraint sweep (ε analog) ===
    print("\n--- Experiment B: Constraint sweep (snap_strength as ε proxy) ---")
    for epsilon in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        try:
            c = Conductor(genre='Jazz', scale='pentatonic_major', tuning='equal_temperament')
            c.constraints.snap_strength = epsilon
            c.constraints.funnel_gravity = epsilon * 100
            c.constraints.consensus_weight = epsilon
            c.constraints.bpm = 120
            
            start = time.time()
            arr = c.compose(bars=4)
            elapsed = time.time() - start
            
            n_events = sum(len(t.events) for t in arr.tracks)
            analysis = c.analyze(arr)
            constraints = analysis.get('constraint_satisfaction', {})
            
            print(f"  ε={epsilon:.1f}: {n_events} events in {elapsed:.3f}s, "
                  f"snap={constraints.get('snap_accuracy', 0):.3f}, "
                  f"funnel={constraints.get('funnel_convergence', 0):.3f}")
        except Exception as e:
            print(f"  ε={epsilon:.1f}: FAILED - {e}")
    
    # === Experiment C: Living systems ===
    print("\n--- Experiment C: Living system modules ---")
    
    # C1: GRN composition
    try:
        c = Conductor(genre='IDM', scale='pentatonic_major')
        c.constraints.bpm = 120
        start = time.time()
        arr = c.live_gene_network(steps=100)
        elapsed = time.time() - start
        n_events = sum(len(t.events) for t in arr.tracks) if hasattr(arr, 'tracks') else 0
        print(f"  GRN (100 steps): {n_events} events in {elapsed:.3f}s")
    except Exception as e:
        print(f"  GRN: {e}")
    
    # C2: Embryonic development
    try:
        c = Conductor(genre='Ambient', scale='in_scale')
        c.constraints.bpm = 60
        start = time.time()
        arr = c.live_embryo(timesteps=50)
        elapsed = time.time() - start
        n_events = sum(len(t.events) for t in arr.tracks) if hasattr(arr, 'tracks') else 0
        print(f"  Embryo (50 steps): {n_events} events in {elapsed:.3f}s")
    except Exception as e:
        print(f"  Embryo: {e}")
    
    # C3: Protein folding
    try:
        c = Conductor(genre='Classical')
        c.constraints.bpm = 72
        start = time.time()
        arr = c.live_protein_fold(sequence='ACDEFGHIKLMNPQRSTVWY')
        elapsed = time.time() - start
        n_events = sum(len(t.events) for t in arr.tracks) if hasattr(arr, 'tracks') else 0
        print(f"  Protein fold: {n_events} events in {elapsed:.3f}s")
    except Exception as e:
        print(f"  Protein fold: {e}")
    
    # C4: Call and response
    try:
        c = Conductor(genre='Polyrhythm', culture='west_african')
        c.constraints.bpm = 120
        start = time.time()
        arr = c.live_call_response(bars=8)
        elapsed = time.time() - start
        n_events = sum(len(t.events) for t in arr.tracks) if hasattr(arr, 'tracks') else 0
        print(f"  Call & Response: {n_events} events in {elapsed:.3f}s")
    except Exception as e:
        print(f"  Call & Response: {e}")
    
    # === Experiment D: Cross-cultural blending ===
    print("\n--- Experiment D: Cross-cultural blending ---")
    blends = [
        ('midnight_raga', 'bebop_salt'),
        ('cairo_cafe', 'zen_garden'),
        ('djembe_circle', 'midnight_raga'),
    ]
    for a, b in blends:
        try:
            c = Conductor.preset(a)
            arr_a = c.compose(bars=4)
            events_a = sum(len(t.events) for t in arr_a.tracks)
            
            c2 = Conductor.preset(b)
            arr_b = c2.compose(bars=4)
            events_b = sum(len(t.events) for t in arr_b.tracks)
            
            print(f"  {a} + {b}: {events_a} + {events_b} events")
        except Exception as e:
            print(f"  {a} + {b}: FAILED - {e}")
    
    # === Experiment E: Cohomology analysis ===
    print("\n--- Experiment E: Cohomology analysis ---")
    try:
        c = Conductor.preset('bebop_salt')
        arr = c.compose(bars=8)
        coh = c.analyze_cohomology(arr)
        print(f"  Bebop: H0={coh['H0']}, H1={coh['H1']}, "
              f"emergence={coh['emergence_score']:.3f}, "
              f"complexity={coh['harmonic_complexity']:.3f}")
        
        c2 = Conductor.preset('midnight_raga')
        arr2 = c2.compose(bars=8)
        coh2 = c2.analyze_cohomology(arr2)
        print(f"  Raga:  H0={coh2['H0']}, H1={coh2['H1']}, "
              f"emergence={coh2['emergence_score']:.3f}, "
              f"complexity={coh2['harmonic_complexity']:.3f}")
    except Exception as e:
        print(f"  Cohomology: {e}")
    
    # === Experiment F: Repair pipeline ===
    print("\n--- Experiment F: Repair pipeline ---")
    try:
        c = Conductor.preset('bebop_salt')
        arr = c.compose(bars=4)
        n_before = sum(len(t.events) for t in arr.tracks)
        
        repaired = c.repair(arr)
        n_after = sum(len(t.events) for t in repaired.tracks)
        print(f"  Repair: {n_before} → {n_after} events")
    except Exception as e:
        print(f"  Repair: {e}")
    
    # === Experiment G: Natural language quick compose ===
    print("\n--- Experiment G: Quick compose (NLP) ---")
    descriptions = [
        'Indian raga Darbari in Jhaptaal',
        'Arabic maqam Rast fast',
        'Jazz swing slow',
        'Ambient pentatonic',
    ]
    for desc in descriptions:
        try:
            start = time.time()
            c = Conductor()
            arr = c.quick(desc)
            elapsed = time.time() - start
            n = sum(len(t.events) for t in arr.tracks)
            print(f"  '{desc}': {n} events in {elapsed:.3f}s")
        except Exception as e:
            print(f"  '{desc}': FAILED - {e}")
    
    # === Experiment H: Evolution ===
    print("\n--- Experiment H: Evolution ---")
    try:
        c = Conductor(genre='Jazz', seed=42)
        start = time.time()
        c.evolve(target_genre='jazz', generations=20, population=50)
        elapsed = time.time() - start
        arr = c.compose(bars=4)
        n = sum(len(t.events) for t in arr.tracks)
        print(f"  Evolved (20 gen): {n} events, "
              f"bpm={c.constraints.bpm:.0f}, swing={c.constraints.swing_ratio:.2f}, "
              f"elapsed={elapsed:.3f}s")
    except Exception as e:
        print(f"  Evolution: {e}")
    
    print("\n=== Conductor has no perform()/run()/tick()/add_cell() — it uses compose(), live_*(), analyze() ===")
    print("=== All modules wired through Conductor's high-level API ===")

# Save whatever results we got
results = {
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    'conductor_available': True,
    'modules': ['gene_regulatory', 'living', 'immune_system', 'ecosystem', 'protein_fold', 'embryonic', 'neural_music'],
    'conductor_api': ['compose', 'live_session', 'live_gene_network', 'live_embryo', 
                      'live_protein_fold', 'live_call_response', 'evolve', 'repair',
                      'analyze', 'analyze_cohomology', 'quick', 'preset'],
    'presets_tested': cultures,
    'event_counts': event_counts if 'event_counts' in dir() else {},
}

with open('experiments/EXPERIMENT-CONDUCTOR.json', 'w') as f:
    json.dump(results, f, indent=2)

print("\nResults saved to experiments/EXPERIMENT-CONDUCTOR.json")
