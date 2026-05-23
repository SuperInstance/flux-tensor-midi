"""
FLUX-Tensor-MIDI CLI entry point.

Usage:
    python -m flux_tensor_midi drum --pattern trap_hats --bpm 140 --output beat.mid
    python -m flux_tensor_midi drum --preset-list
    python -m flux_tensor_midi drum --euclidean hihat_closed 16 5 --bpm 120 --output euclid.mid
"""

from __future__ import annotations

import argparse
import sys


def _drum_cmd(args: argparse.Namespace) -> None:
    from flux_tensor_midi.drum_rack import StepSequencer

    # List presets
    if args.preset_list:
        from flux_tensor_midi.drum_rack.sequencer import _PRESETS
        print("Available presets:")
        for name in sorted(_PRESETS.keys()):
            print(f"  {name}")
        return

    seq = StepSequencer(steps=args.steps)

    if args.euclidean:
        # --euclidean instrument pulses [rotation]
        parts = args.euclidean.split()
        instrument = parts[0]
        pulses = int(parts[1]) if len(parts) > 1 else 4
        rotation = int(parts[2]) if len(parts) > 2 else 0
        seq.euclidean(instrument, pulses=pulses, rotation=rotation)
        print(f"Euclidean rhythm: {instrument}, {pulses}/{seq.steps}, rotation={rotation}")
    elif args.pattern:
        seq.load_preset(args.pattern)
        print(f"Loaded preset: {args.pattern}")

    if args.humanize:
        seq = seq.humanize(swing=0.3, velocity_range=10, timing_range=5, seed=42)
        print("Applied humanization")

    bpm = args.bpm or 120
    events = seq.render(bpm=bpm, output=args.output)

    if args.output:
        print(f"Wrote {len(events)} events to {args.output}")
    else:
        print(f"Pattern: {seq}")
        for ev in events[:32]:
            print(f"  {ev}")
        if len(events) > 32:
            print(f"  ... and {len(events) - 32} more")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="flux_tensor_midi",
        description="FLUX-Tensor-MIDI: PLATO rooms as musicians",
    )
    sub = parser.add_subparsers(dest="command")

    # drum subcommand
    drum = sub.add_parser("drum", help="Drum rack / step sequencer")
    drum.add_argument("--pattern", "-p", help="Preset pattern name (boom_bap, trap_hats, etc.)")
    drum.add_argument("--euclidean", "-e", metavar="INST PULSES [ROT]",
                      help="Euclidean rhythm: 'instrument pulses [rotation]'")
    drum.add_argument("--bpm", "-b", type=float, help="Tempo in BPM (default: 120)")
    drum.add_argument("--output", "-o", help="Output .mid file path")
    drum.add_argument("--steps", "-s", type=int, default=16, choices=[8, 16, 32],
                      help="Pattern length in steps (default: 16)")
    drum.add_argument("--humanize", "-H", action="store_true", help="Apply humanization")
    drum.add_argument("--preset-list", action="store_true", help="List available presets")

    args = parser.parse_args(argv)

    if args.command == "drum":
        _drum_cmd(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
