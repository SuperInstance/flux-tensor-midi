"""
Conductor Demo — 15 presets including LIVING ones.

Shows how the unified Conductor wires together cultural traditions,
constraint theory, living systems, gene regulatory networks,
protein folding, embryonic development, and DNA-inspired repair.

Run:
    python conductor_demo.py
"""

from flux_tensor_midi.conductor import Conductor

def demo():
    print("=" * 60)
    print("  FLUX TENSOR MIDI — Living Conductor Demo")
    print("=" * 60)

    # === Static Presets ===
    static_presets = [
        'midnight_raga',
        'cairo_cafe',
        'zen_garden',
        'djembe_circle',
        'bebop_salt',
        'bach_fugue',
        'quasicrystal',
    ]

    print("\n### Static Presets (pre-calculable) ###\n")
    for name in static_presets:
        c = Conductor.preset(name)
        arr = c.compose(bars=4)
        arr.generate_all()
        n_events = sum(len(t.events) for t in arr.tracks)
        print(f"  {name:20s}  bpm={c.constraints.bpm:5.0f}  "
              f"culture={c.culture or '?':12s}  events={n_events}")

    # === Living Presets ===
    print("\n### Living Presets (NON-pre-calculable) ###\n")

    # 1. Living Jazz Session
    print("  [living_jazz] JazzSession — 4 autonomous cells")
    c = Conductor(seed=42)
    c.set_culture('western')
    c.constraints.bpm = 140
    arr = c.live_session(bars=16, key='Bb', style='bebop')
    n_events = sum(len(t.events) for t in arr.tracks)
    state = c._session.get_session_state()
    print(f"    → events={n_events}, phase={state['phase']}, "
          f"energy={state['energy']:.3f}")

    # 2. Living Bebop
    print("  [living_bebop] Fast bebop session")
    c = Conductor(seed=99)
    c.constraints.bpm = 180
    arr = c.live_session(bars=16, style='bebop')
    n_events = sum(len(t.events) for t in arr.tracks)
    print(f"    → events={n_events}")

    # 3. Gene Garden
    print("  [gene_garden] Gene Regulatory Network composition")
    c = Conductor(seed=42)
    arr = c.live_gene_network(steps=100)
    n_events = sum(len(t.events) for t in arr.tracks)
    if c._grn:
        summary = c._grn.get_network_state_summary()
        print(f"    → events={n_events}, gene_types={list(summary.keys())}")

    # 4. Protein Sonata
    print("  [protein_sonata] Protein folding → music")
    c = Conductor(seed=42)
    arr = c.live_protein_fold('ACDEFGHIKLMNPQRSTVWY')
    n_events = sum(len(t.events) for t in arr.tracks)
    print(f"    → events={n_events}")

    # 5. Embryo Dream
    print("  [embryo_dream] Embryonic development → composition")
    c = Conductor(seed=42)
    arr = c.live_embryo(timesteps=60)
    n_events = sum(len(t.events) for t in arr.tracks)
    if c._embryo:
        summary = c._embryo.development_summary()
        print(f"    → events={n_events}, cell_types={summary['cell_types']}")

    # 6. Trading Fours
    print("  [trading_fours] Sax and drums trade 4-bar phrases")
    c = Conductor(seed=42)
    c.constraints.bpm = 160
    arr = c.live_trading_fours(bars=16)
    n_events = sum(len(t.events) for t in arr.tracks)
    print(f"    → events={n_events}")

    # 7. Call and Response
    print("  [call_response] Sax calls, piano responds")
    c = Conductor(seed=42)
    arr = c.live_call_response(bars=8)
    n_events = sum(len(t.events) for t in arr.tracks)
    print(f"    → events={n_events}")

    # 8. Repair Shop
    print("  [repair_shop] Compose → repair pipeline")
    c = Conductor.preset('bebop_salt')
    arr = c.compose(bars=4)
    arr.generate_all()
    repaired = c.repair(arr)
    n_events = sum(len(t.events) for t in repaired.tracks)
    print(f"    → repaired events={n_events}")

    # === Analysis with Living State ===
    print("\n### Full Analysis Pipeline ###\n")
    c = Conductor(seed=42)
    arr = c.live_session(bars=16, key='C', style='modal')
    analysis = c.analyze(arr)
    print(f"  Analysis keys: {list(analysis.keys())}")
    if 'session_state' in analysis:
        ss = analysis['session_state']
        print(f"  Session: phase={ss['phase']}, energy={ss['energy']:.3f}")
        for name, cell_data in ss['cells'].items():
            print(f"    {name}: energy={cell_data['energy']:.3f}")

    # === Natural Language Quick with Living ===
    print("\n### Quick API ###\n")
    c = Conductor()
    arr = c.quick('Indian raga Bhairavi vilambit')
    print(f"  quick('Indian raga Bhairavi vilambit') → culture={c.culture}")

    print("\n" + "=" * 60)
    print("  Demo complete. The Conductor is ALIVE.")
    print("=" * 60)


if __name__ == '__main__':
    demo()
