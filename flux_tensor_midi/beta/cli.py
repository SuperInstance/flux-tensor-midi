"""
Beta test CLI.

Usage:
    python -m flux_tensor_midi beta start
    python -m flux_tensor_midi beta analyze
    python -m flux_tensor_midi beta experiment --name goldilocks --control '{"epsilon": 0.15}' --treatment '{"epsilon": 0.30}'
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _start_cmd(args: argparse.Namespace) -> None:
    """Start a guided beta session."""
    from flux_tensor_midi.beta.session_recorder import SessionRecorder
    from flux_tensor_midi.beta.feedback_collector import FeedbackCollector

    recorder = SessionRecorder()
    collector = FeedbackCollector(headless=getattr(args, "headless", False))

    user_id = input("Enter user ID (or press Enter for anonymous): ").strip() or "anon"
    session_id = recorder.start_session(user_id=user_id)
    print(f"\n🎯 Beta session {session_id} started for user '{user_id}'")
    print("Commands: compose, param <key> <value>, play, rate <1-5>, feedback <text>, nps <0-10>, quit\n")

    comp_count = 0
    while True:
        try:
            line = input("beta> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        parts = line.split(maxsplit=1)
        cmd = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if cmd in ("quit", "exit", "q"):
            break
        elif cmd == "compose":
            comp_count += 1
            midi_hash = f"comp_{comp_count:04d}"
            recorder.log_action("compose", {"midi_hash": midi_hash})
            recorder.log_composition(midi_hash, {"index": comp_count})
            print(f"  ✅ Composition {midi_hash} logged")
        elif cmd == "param":
            kv = rest.split(maxsplit=1)
            if len(kv) == 2:
                key, val = kv
                try:
                    val = json.loads(val)
                except json.JSONDecodeError:
                    pass
                recorder.log_action("param_change", {key: val})
                print(f"  📐 Param: {key}={val}")
            else:
                print("  Usage: param <key> <value>")
        elif cmd == "play":
            recorder.log_action("playback", {"target": rest or "last"})
            print("  🎵 Playback logged")
        elif cmd == "rate":
            try:
                stars = int(rest.strip())
                collector.ask_rating(f"comp_{comp_count:04d}", stars)
                print(f"  ⭐ Rated {stars}/5")
            except ValueError:
                print("  Usage: rate <1-5>")
            except Exception as e:
                print(f"  Error: {e}")
        elif cmd == "feedback":
            if rest:
                collector.ask_text(f"comp_{comp_count:04d}", rest)
                print("  💬 Feedback recorded")
            else:
                print("  Usage: feedback <text>")
        elif cmd == "nps":
            try:
                score = int(rest.strip())
                collector.ask_nps(f"comp_{comp_count:04d}", score)
                category = "detractor" if score <= 6 else ("passive" if score <= 8 else "promoter")
                print(f"  📊 NPS: {score}/10 ({category})")
            except ValueError:
                print("  Usage: nps <0-10>")
            except Exception as e:
                print(f"  Error: {e}")
        elif cmd == "help":
            print("  Commands: compose, param <k> <v>, play, rate <1-5>, feedback <text>, nps <0-10>, quit")
        else:
            print(f"  Unknown: {cmd}. Type 'help' for commands.")

    abandon = None
    if comp_count == 0:
        abandon = "before_compose"

    session = recorder.end_session(abandon_point=abandon)
    if collector.record_count > 0:
        collector.export_feedback()

    print(f"\n📋 Session ended: {session['total_duration_s']:.1f}s, {comp_count} compositions")
    print(f"   Session saved: {session['session_id']}.json")


def _analyze_cmd(args: argparse.Namespace) -> None:
    """Run the discovery engine on collected session data."""
    from flux_tensor_midi.beta.discovery_engine import DiscoveryEngine

    engine = DiscoveryEngine()
    data_dir = getattr(args, "data_dir", "beta_data/sessions")
    n = engine.ingest_from_directory(data_dir)
    print(f"Loaded {n} sessions from {data_dir}")

    patterns = engine.find_patterns()
    print(f"Found {len(patterns)} patterns\n")

    report_path = engine.generate_report(getattr(args, "output", "DISCOVERY-REPORT.md"))
    print(f"Report written to {report_path}")

    for p in patterns:
        print(f"  [{p['category']}] {p['title']}")


def _experiment_cmd(args: argparse.Namespace) -> None:
    """Define and manage experiments."""
    from flux_tensor_midi.beta.experiment_runner import ExperimentRunner

    runner = ExperimentRunner()
    control = json.loads(args.control)
    treatment = json.loads(args.treatment)

    exp = runner.define_experiment(args.name, control, treatment)
    path = runner.save_experiment(args.name)
    print(f"Experiment '{args.name}' defined:")
    print(f"  Control:   {control}")
    print(f"  Treatment: {treatment}")
    print(f"  Saved to:  {path}")

    # Show a few sample assignments
    print("\n  Sample assignments:")
    for uid in ["user_001", "user_002", "user_003", "user_004", "user_005"]:
        group = runner.assign_group(args.name, uid)
        params = runner.get_params(args.name, uid)
        print(f"    {uid} → {group}: {params}")


def build_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the beta subcommand to the main CLI parser."""
    beta = subparsers.add_parser("beta", help="Beta testing and feedback harness")
    beta_sub = beta.add_subparsers(dest="beta_command")

    # start
    start = beta_sub.add_parser("start", help="Start a guided beta session")
    start.add_argument("--headless", action="store_true", help="Headless mode (no prompts)")

    # analyze
    analyze = beta_sub.add_parser("analyze", help="Run discovery engine on collected data")
    analyze.add_argument("--data-dir", default="beta_data/sessions", help="Session data directory")
    analyze.add_argument("--output", "-o", default="DISCOVERY-REPORT.md", help="Report output path")

    # experiment
    experiment = beta_sub.add_parser("experiment", help="Define an A/B experiment")
    experiment.add_argument("--name", required=True, help="Experiment name")
    experiment.add_argument("--control", required=True, help="Control params as JSON")
    experiment.add_argument("--treatment", required=True, help="Treatment params as JSON")


def run_beta_command(args: argparse.Namespace) -> None:
    """Route beta subcommands."""
    if args.beta_command == "start":
        _start_cmd(args)
    elif args.beta_command == "analyze":
        _analyze_cmd(args)
    elif args.beta_command == "experiment":
        _experiment_cmd(args)
    else:
        print("Usage: python -m flux_tensor_midi beta {start|analyze|experiment}")
