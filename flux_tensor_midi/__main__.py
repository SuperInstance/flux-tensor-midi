"""
FLUX-Tensor-MIDI CLI entry point.

Usage:
    python -m flux_tensor_midi drum --pattern trap_hats --bpm 140 --output beat.mid
    python -m flux_tensor_midi drum --preset-list
    python -m flux_tensor_midi drum --euclidean hihat_closed 16 5 --bpm 120 --output euclid.mid
    python -m flux_tensor_midi play --genre jazz --bpm 180 --seed 42
    python -m flux_tensor_midi play --genre hiphop --bars 8 --seed 0 --export beat.mid
    python -m flux_tensor_midi play --list-genres
    python -m flux_tensor_midi jam --preset parker_miles --bars 32 --output jam.mid
    python -m flux_tensor_midi jam --list-presets
    python -m flux_tensor_midi analyze song.mid
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


def _play_cmd(args: argparse.Namespace) -> None:
    """Genre-based ensemble generation."""
    from flux_tensor_midi.genre_brain import GenreBrain

    # List genres
    if args.list_genres:
        for name in GenreBrain.available_genres():
            brain = GenreBrain(name)
            preset = brain.get_preset()
            print(f"  {name:12s} — {preset['description']}")
            print(f"               BPM={preset['default_bpm']} key={preset['default_key']} "
                  f"bars={preset['loop_bars']} roles={len(preset['roles'])}")
        return

    if not args.genre:
        print("Error: --genre is required (use --list-genres to see options)", file=sys.stderr)
        sys.exit(1)

    brain = GenreBrain(args.genre)

    if not args.quiet:
        print(f"Genre: {args.genre} — {brain.description}")

    band, musicians = brain.create_band(
        bpm=args.bpm,
        key=args.key,
        bars=args.bars,
        seed=args.seed,
    )

    if not args.quiet:
        print(f"  Band: {band.name} ({band.member_count} members)")
        print(f"  BPM: {band.bpm}")
        for m in musicians:
            print(f"    {m.name:12s} role={m.role.name:12s} state={m.state}")
        if args.seed is not None:
            print(f"  Seed: {args.seed}")

    # Tick the band to show activity
    if not args.quiet:
        print("\n  Ticking 8 beats:")
    for i in range(8):
        results = band.tick_all()
        if not args.quiet:
            line = f"    Beat {i+1}: "
            parts = []
            for name, (ts, vec) in results.items():
                parts.append(f"{name}[{vec.magnitude:.2f}]")
            line += " ".join(parts)
            print(line)

    # Export if requested
    if args.export:
        from flux_tensor_midi.tracks import Arrangement, Track
        from flux_tensor_midi.core.snap import RhythmicRole

        preset = brain.get_preset()
        arr = Arrangement(
            name=f"{args.genre}_gen",
            bpm=band.bpm,
            bars=args.bars or preset['loop_bars'],
            seed=args.seed,
        )
        for i, musician in enumerate(musicians):
            role = preset['roles'][i] if i < len(preset['roles']) else RhythmicRole.ROOT
            voice = preset['member_names'][i] if i < len(preset['member_names']) else 'piano'
            arr.add_track(Track(
                musician.name, role, voice,
                bpm=band.bpm, seed=args.seed,
            ))

        arr.generate_all()
        events = arr.to_midi_events()

        from flux_tensor_midi.adapters.daw_bridge import (
            MidiExportConfig, TrackConfig, build_midi_file,
        )
        export = MidiExportConfig(tempo_bpm=band.bpm)
        for i, track in enumerate(arr.tracks):
            tc = TrackConfig(
                name=track.name,
                channel=min(i, 15),
            )
            for ev in track.events:
                ppqn = 480
                start_tick = int(ev.start_ms / (60000.0 / band.bpm) * ppqn)
                dur_ticks = int(ev.duration_ms / (60000.0 / band.bpm) * ppqn)
                tc.notes.append((start_tick, max(1, dur_ticks), ev.note, ev.velocity))
            export.tracks.append(tc)

        midi_bytes = build_midi_file(export)
        with open(args.export, 'wb') as f:
            f.write(midi_bytes)
        if not args.quiet:
            print(f"\n  Exported {len(midi_bytes)} bytes → {args.export}")


def _analyze_cmd(args: argparse.Namespace) -> None:
    """Analyze a MIDI file through the flux-tensor lens."""
    from flux_tensor_midi.analyzer import FluxAnalyzer
    try:
        import mido
    except ImportError:
        print("Error: 'mido' package required for MIDI file analysis. "
              "Install with: pip install mido", file=sys.stderr)
        sys.exit(1)

    analyzer = FluxAnalyzer()
    mid = mido.MidiFile(args.midi_file)
    from flux_tensor_midi.midi.events import MidiEvent
    events = []
    for track in mid.tracks:
        abs_time = 0.0
        for msg in track:
            abs_time += msg.time
            if msg.type == 'note_on' and msg.velocity > 0:
                events.append(MidiEvent(
                    note=msg.note,
                    velocity=msg.velocity,
                    start_ms=abs_time * 1000.0 / mid.ticks_per_beat * (60.0 / 120.0),
                    duration_ms=250.0,
                    channel=getattr(msg, 'channel', 0),
                ))

    report = analyzer.from_midi_events(events)
    print(f"Analysis of {args.midi_file}:")
    for k, v in report.summary().items():
        print(f"  {k:22s} = {v}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="flux_tensor_midi",
        description="FLUX-Tensor-MIDI: PLATO rooms as musicians",
    )
    sub = parser.add_subparsers(dest="command")

    # ── drum subcommand ──────────────────────────────────────────────────
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

    # ── play subcommand ──────────────────────────────────────────────────
    play = sub.add_parser("play", help="Genre-based ensemble generation")
    play.add_argument("--genre", "-g", help="Genre: jazz, hiphop, electronic, classical, math")
    play.add_argument("--bpm", "-b", type=int, default=None, help="Beats per minute")
    play.add_argument("--key", "-k", type=str, default=None, help="Musical key (C, Bb, etc.)")
    play.add_argument("--bars", type=int, default=None, help="Number of bars")
    play.add_argument("--seed", "-s", type=int, default=None,
                      help="Random seed for reproducibility (numpy RandomState)")
    play.add_argument("--list-genres", "-l", action="store_true", help="List available genres")
    play.add_argument("--export", "-e", metavar="OUTPUT.mid",
                      help="Export arrangement to MIDI file")
    play.add_argument("--quiet", "-q", action="store_true", help="Suppress output")

    # ── jam subcommand ──────────────────────────────────────────────────────
    jam = sub.add_parser("jam", help="AI-AI jam session (two agents jamming)")
    jam.add_argument("--preset", "-p", help="Jam preset (parker_miles, bach_vivaldi, etc.)")
    jam.add_argument("--bpm", "-b", type=float, default=None, help="Tempo in BPM")
    jam.add_argument("--bars", type=int, default=None, help="Total session length in bars")
    jam.add_argument("--phrase-bars", type=int, default=4,
                     help="Bars per agent turn (default: 4)")
    jam.add_argument("--output", "-o", default=None, help="Output .mid file path")
    jam.add_argument("--seed", "-s", type=int, default=None, help="Random seed")
    jam.add_argument("--list-presets", "-l", action="store_true", help="List presets")
    jam.add_argument("--quiet", "-q", action="store_true", help="Suppress output")

    # ── analyze subcommand ───────────────────────────────────────────────
    analyze = sub.add_parser("analyze", help="Analyze a MIDI file")
    analyze.add_argument("midi_file", help="Path to .mid file")

    args = parser.parse_args(argv)

    if args.command == "drum":
        _drum_cmd(args)
    elif args.command == "play":
        _play_cmd(args)
    elif args.command == "jam":
        from flux_tensor_midi.ai_jam.cli import jam_command
        jam_command(args)
    elif args.command == "analyze":
        _analyze_cmd(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
