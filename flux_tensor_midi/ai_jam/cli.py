"""
CLI for AI-AI Jam: `python -m flux_tensor_midi jam --preset parker_miles`
"""

from __future__ import annotations

import argparse
import random
import sys


def jam_command(args: argparse.Namespace) -> None:
    """Execute the jam subcommand."""
    from flux_tensor_midi.ai_jam.presets import get_preset, list_presets
    from flux_tensor_midi.ai_jam.agent import AIAgent
    from flux_tensor_midi.ai_jam.session import JamSession

    if args.list_presets:
        print("Available jam presets:")
        for name in list_presets():
            preset = get_preset(name)
            print(f"  {name:20s} — {preset['description']}")
        return

    if not args.preset:
        print("Error: --preset is required (use --list-presets to see options)", file=sys.stderr)
        sys.exit(1)

    preset = get_preset(args.preset)
    bpm = args.bpm or preset["bpm"]
    bars = args.bars or 32

    agent1 = AIAgent(preset["agent1"], rng=random.Random(args.seed))
    agent2 = AIAgent(preset["agent2"], rng=random.Random(
        (args.seed or 0) + 42
    ))

    session = JamSession(
        agent1=agent1,
        agent2=agent2,
        bpm=bpm,
        total_bars=bars,
        progression=preset["progression"],
        phrase_bars=args.phrase_bars,
    )

    if not args.quiet:
        print(f"🎹 AI Jam: {preset['description']}")
        print(f"   {agent1.personality.name} ({agent1.personality.instrument}) "
              f"× {agent2.personality.name} ({agent2.personality.instrument})")
        print(f"   BPM={bpm} bars={bars} phrase={args.phrase_bars} bars")
        if args.seed is not None:
            print(f"   seed={args.seed}")

    events = session.run()

    if not args.quiet:
        ch1 = agent1.personality.midi_channel
        ch2 = agent2.personality.midi_channel
        n1 = sum(1 for e in events if e.channel == ch1)
        n2 = sum(1 for e in events if e.channel == ch2)
        total_ms = bars * (60_000.0 / bpm) * 4
        print(f"   Generated {len(events)} events "
              f"({agent1.personality.name}: {n1}, {agent2.personality.name}: {n2})")
        print(f"   Duration: {total_ms/1000:.1f}s")

    output = args.output or "jam.mid"
    session.to_midi_file(output)

    if not args.quiet:
        print(f"   → {output}")

    return
