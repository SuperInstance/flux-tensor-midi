#!/usr/bin/env python3
"""
conductor_demo.py — 10 preset usages of the unified Conductor.

Run: python conductor_demo.py
"""

import os
import sys

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flux_tensor_midi.conductor import Conductor


def demo_midnight_raga():
    """Preset: midnight_raga — Bhairavi raga at vilambit tempo."""
    print("\n" + "=" * 60)
    print("🎵 Preset 1: midnight_raga")
    print("=" * 60)

    c = Conductor.preset('midnight_raga')
    print(f"  Conductor: {c}")
    arr = c.compose(bars=8)
    print(f"  Arrangement: {arr.summary()}")

    path = '/tmp/midnight_raga.mid'
    c.render_midi(arr, path)
    print(f"  MIDI written to {path} ({os.path.getsize(path)} bytes)")

    analysis = c.analyze(arr)
    print(f"  Analysis: {analysis['summary']}")


def demo_cairo_cafe():
    """Preset: cairo_cafe — Maqam Rast with maqsum rhythm."""
    print("\n" + "=" * 60)
    print("🎵 Preset 2: cairo_cafe")
    print("=" * 60)

    c = Conductor.preset('cairo_cafe')
    arr = c.compose(bars=8)
    print(f"  Conductor: {c}")
    print(f"  Arrangement: {arr.summary()}")

    path = '/tmp/cairo_cafe.mid'
    c.render_midi(arr, path)
    print(f"  MIDI written to {path}")


def demo_zen_garden():
    """Preset: zen_garden — Japanese In scale, slow and spacious."""
    print("\n" + "=" * 60)
    print("🎵 Preset 3: zen_garden")
    print("=" * 60)

    c = Conductor.preset('zen_garden')
    arr = c.compose(bars=8)
    print(f"  Conductor: {c}")
    print(f"  Arrangement: {arr.summary()}")

    path = '/tmp/zen_garden.mid'
    c.render_midi(arr, path)
    print(f"  MIDI written to {path}")


def demo_djembe_circle():
    """Preset: djembe_circle — West African polyrhythm."""
    print("\n" + "=" * 60)
    print("🎵 Preset 4: djembe_circle")
    print("=" * 60)

    c = Conductor.preset('djembe_circle')
    arr = c.compose(bars=8)
    print(f"  Conductor: {c}")
    print(f"  Arrangement: {arr.summary()}")

    path = '/tmp/djembe_circle.mid'
    c.render_midi(arr, path)
    print(f"  MIDI written to {path}")


def demo_bebop_salt():
    """Preset: bebop_salt — Jazz bebop with swing."""
    print("\n" + "=" * 60)
    print("🎵 Preset 5: bebop_salt")
    print("=" * 60)

    c = Conductor.preset('bebop_salt')
    arr = c.compose(bars=8)
    print(f"  Conductor: {c}")
    print(f"  Arrangement: {arr.summary()}")

    path = '/tmp/bebop_salt.mid'
    c.render_midi(arr, path)
    print(f"  MIDI written to {path}")


def demo_bach_fugue():
    """Preset: bach_fugue — Baroque counterpoint."""
    print("\n" + "=" * 60)
    print("🎵 Preset 6: bach_fugue")
    print("=" * 60)

    c = Conductor.preset('bach_fugue')
    arr = c.compose_counterpoint(species=2, bars=8)
    print(f"  Conductor: {c}")
    print(f"  Counterpoint: {arr.summary()}")

    path = '/tmp/bach_fugue.mid'
    c.render_midi(arr, path)
    print(f"  MIDI written to {path}")


def demo_penrose_dance():
    """Preset: penrose_dance — Aperiodic Fibonacci groove."""
    print("\n" + "=" * 60)
    print("🎵 Preset 7: penrose_dance")
    print("=" * 60)

    c = Conductor.preset('penrose_dance')
    try:
        arr = c.compose_penrose(preset='fibonacci_groove', bars=8)
        print(f"  Conductor: {c}")
        print(f"  Penrose: {arr.summary()}")

        path = '/tmp/penrose_dance.mid'
        c.render_midi(arr, path)
        print(f"  MIDI written to {path}")
    except ImportError as e:
        print(f"  Skipped: {e}")


def demo_evolved_hybrid():
    """Preset: evolved_hybrid — Evolved cross-cultural blend."""
    print("\n" + "=" * 60)
    print("🎵 Preset 8: evolved_hybrid")
    print("=" * 60)

    c = Conductor.preset('evolved_hybrid')
    try:
        c.evolve_cross_cultural('indian', 'western', generations=10)
        print(f"  Conductor: {c}")
        arr = c.compose(bars=8)
        print(f"  Evolved hybrid: {arr.summary()}")

        path = '/tmp/evolved_hybrid.mid'
        c.render_midi(arr, path)
        print(f"  MIDI written to {path}")
    except ImportError as e:
        print(f"  Skipped: {e}")


def demo_hyperbolic_exploration():
    """Preset: hyperbolic_exploration — Walk through genre space."""
    print("\n" + "=" * 60)
    print("🎵 Preset 9: hyperbolic_exploration")
    print("=" * 60)

    c = Conductor.preset('hyperbolic_exploration')
    try:
        walk = c.genre_walk(steps=5, step_size=0.1)
        print(f"  Conductor: {c}")
        print(f"  Genre walk visited:")
        for name, coords in walk:
            print(f"    → {name} (norm={coords.dot(coords)**0.5:.3f})")

        nearby = c.explore_nearby(n=5)
        print(f"  Nearby genres to Jazz:")
        for name, dist in nearby:
            print(f"    {name}: {dist:.4f}")
    except ImportError as e:
        print(f"  Skipped: {e}")


def demo_quick():
    """Quick: natural language composition."""
    print("\n" + "=" * 60)
    print("🎵 Preset 10: quick() — Natural language")
    print("=" * 60)

    descriptions = [
        'Indian raga Darbari in Jhaptaal slow',
        'Arabic maqam Rast fast',
        'Jazz swing in Bb',
    ]

    for desc in descriptions:
        c = Conductor()
        arr = c.quick(desc)
        print(f"  '{desc}' → {c}")
        print(f"    Arrangement: {arr.summary()}")

    # Full pipeline: compose → analyze → render
    print("\n  Full pipeline: compose → analyze → render")
    c = Conductor()
    arr = c.quick('Indian raga Bhairavi')
    analysis = c.analyze(arr)
    cohomology = c.analyze_cohomology(arr)
    print(f"    Summary: {analysis['summary']}")
    print(f"    Cohomology: {cohomology}")

    path = '/tmp/quick_raga.mid'
    c.render_midi(arr, path)
    print(f"    MIDI written to {path}")


if __name__ == '__main__':
    print("=" * 60)
    print("🎶 FLUX-TENSOR-MIDI CONDUCTOR DEMO")
    print("=" * 60)

    demo_midnight_raga()
    demo_cairo_cafe()
    demo_zen_garden()
    demo_djembe_circle()
    demo_bebop_salt()
    demo_bach_fugue()
    demo_penrose_dance()
    demo_evolved_hybrid()
    demo_hyperbolic_exploration()
    demo_quick()

    print("\n" + "=" * 60)
    print("🎶 All demos complete!")
    print("=" * 60)
