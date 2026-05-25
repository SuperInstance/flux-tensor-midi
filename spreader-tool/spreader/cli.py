"""Module 10: CLI — plato-spreader command-line interface.

Subcommands:
    deadband-status   Show deadband status for rooms
    freeze            Create and freeze a context window
    list-fcws         List frozen context windows
    seed-candidates   List candidate seeds
    lock-seed         Lock a validated seed
    backtest          Run backtest on a candidate seed
    redact            Run redaction/pruning on stored FCWs
    stats             Show aggregate counts
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from typing import List, Optional, Sequence

from .deadband import DeadbandDetector
from .frozen_context import FCWManager
from .seed_lock import SeedLockManager
from .store import SpreaderStore
from .types import (
    FCWStatus,
    KPIMetrics,
    RoomType,
    SeedState,
    TriggerType,
    make_fcw,
    make_seed,
)


class _SpreaderStoreAdapter:
    """Adapts SpreaderStore (content-hash keyed) to SeedLockManager's
    expected interface: get(seed_id), put(seed), query(room_id, state)."""

    def __init__(self, store: SpreaderStore) -> None:
        self._store = store
        self._by_seed_id: dict = {}  # seed_id → content_hash

    def _reindex(self) -> None:
        """Rebuild seed_id → content_hash index from disk."""
        self._by_seed_id.clear()
        for seed in self._store.list_seeds():
            raw = SpreaderStore._serialize(seed)
            h = SpreaderStore.content_hash(raw.encode())
            self._by_seed_id[seed.seed_id] = h

    def put(self, seed) -> None:
        h = self._store.put(seed)
        self._by_seed_id[seed.seed_id] = h

    def get(self, seed_id: str):
        h = self._by_seed_id.get(seed_id)
        if h is None:
            self._reindex()
            h = self._by_seed_id.get(seed_id)
        if h is None:
            return None
        return self._store.get(h)

    def query(self, room_id=None, state=None):
        return self._store.list_seeds(room_id=room_id, state=state)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _default_store_path() -> str:
    return os.environ.get("SPREADER_STORE", ".spreader_store")


def _fmt_status(s: FCWStatus) -> str:
    return s.value


def _fmt_seed_state(s: SeedState) -> str:
    return s.value


def _room_type_choices() -> List[str]:
    return [rt.value for rt in RoomType]


def _trigger_choices() -> List[str]:
    return [t.value for t in TriggerType]


def _status_choices() -> List[str]:
    return [s.value for s in FCWStatus]


# ── Subcommand: deadband-status ─────────────────────────────────────────────

def cmd_deadband_status(args: argparse.Namespace) -> None:
    """Show current deadband status for all rooms or a specific room."""
    store = SpreaderStore(_default_store_path())
    fcws = store.list_fcws(room_id=args.room if hasattr(args, "room") else None)

    if not fcws:
        print("No FCWs found — no deadband data available.")
        return

    detector = DeadbandDetector()
    for fcw in fcws:
        state = detector.update(fcw.kpi_snapshot)
        status_icon = "🔴" if state.in_deadband else "🟢"
        print(f"  {status_icon} {fcw.room_id}  severity={state.severity:.2f}  "
              f"breached={[m.value for m in state.breached_metrics]}")
    detector.reset()


# ── Subcommand: freeze ──────────────────────────────────────────────────────

def cmd_freeze(args: argparse.Namespace) -> None:
    """Create and freeze a context window."""
    store = SpreaderStore(_default_store_path())
    mgr = FCWManager(store_path=None)  # in-memory for creation

    kpi = KPIMetrics(
        task_completion_rate=getattr(args, "completion", 95.0),
        avg_wait_time=getattr(args, "wait_time", 10.0),
        energy_over_baseline=getattr(args, "energy", 5.0),
        inference_mae=getattr(args, "mae", 3.0),
        timestamp=time.time(),
    )

    fcw = mgr.create(
        room_id=args.room,
        room_type=RoomType(args.room_type),
        kpi=kpi,
        trigger=TriggerType(args.trigger),
    )
    fcw = mgr.freeze(fcw.fcw_id)

    # Persist to store
    store.put(fcw)
    print(f"Frozen FCW: {fcw.fcw_id}")
    print(f"  room={fcw.room_id}  status={fcw.status.value}  trigger={fcw.trigger.value}")


# ── Subcommand: list-fcws ───────────────────────────────────────────────────

def cmd_list_fcws(args: argparse.Namespace) -> None:
    """List frozen context windows."""
    store = SpreaderStore(_default_store_path())
    status = FCWStatus(args.status) if args.status else None
    fcws = store.list_fcws(room_id=args.room, status=status)

    if not fcws:
        print("No FCWs found.")
        return

    print(f"{'FCW ID':<38} {'Room':<20} {'Status':<12} {'Trigger':<16} {'Frozen At'}")
    print("-" * 110)
    for fcw in fcws:
        print(f"{fcw.fcw_id:<38} {fcw.room_id:<20} {fcw.status.value:<12} "
              f"{fcw.trigger.value:<16} {fcw.frozen_at:.1f}")


# ── Subcommand: seed-candidates ─────────────────────────────────────────────

def cmd_seed_candidates(args: argparse.Namespace) -> None:
    """List candidate seeds."""
    store = SpreaderStore(_default_store_path())
    adapter = _SpreaderStoreAdapter(store)
    mgr = SeedLockManager(store=adapter)
    candidates = mgr.list_candidates(room_id=args.room)

    if not candidates:
        print("No candidate seeds found.")
        return

    print(f"{'Seed ID':<38} {'Room':<20} {'State':<15} {'Role':<16} {'Created'}")
    print("-" * 105)
    for s in candidates:
        ts = s.created_at or 0
        print(f"{s.seed_id:<38} {s.room_id:<20} {s.state.value:<15} "
              f"{s.role_name:<16} {ts:.1f}")


# ── Subcommand: lock-seed ───────────────────────────────────────────────────

def cmd_lock_seed(args: argparse.Namespace) -> None:
    """Lock a validated seed (must be in LOCK_PENDING state)."""
    store = SpreaderStore(_default_store_path())
    adapter = _SpreaderStoreAdapter(store)
    mgr = SeedLockManager(store=adapter)

    try:
        seed = mgr.lock(args.seed_id)
        print(f"Locked seed: {seed.seed_id}  state={seed.state.value}")
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


# ── Subcommand: backtest ────────────────────────────────────────────────────

def cmd_backtest(args: argparse.Namespace) -> None:
    """Run backtest on a candidate seed."""
    store = SpreaderStore(_default_store_path())
    adapter = _SpreaderStoreAdapter(store)
    mgr = SeedLockManager(store=adapter)

    try:
        seed = mgr.validate(args.seed_id)
        status = "PASS → LOCK_PENDING" if seed.state.value == "lock_pending" else "FAIL → CANDIDATE"
        print(f"Backtest: {status}  seed={seed.seed_id}")
    except (KeyError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


# ── Subcommand: redact ──────────────────────────────────────────────────────

def cmd_redact(args: argparse.Namespace) -> None:
    """Run redaction/pruning on stored FCWs (discard oldest DISCARDED-status entries)."""
    store = SpreaderStore(_default_store_path())
    target = getattr(args, "target_reduction", 0.1)

    fcws = store.list_fcws()
    if not fcws:
        print("No FCWs to redact.")
        return

    discarded = [f for f in fcws if f.status == FCWStatus.DISCARDED]
    total = len(fcws)
    to_remove = max(1, int(total * target))

    # Remove oldest discarded FCWs first
    discarded.sort(key=lambda f: f.frozen_at)
    removed = 0
    for fcw in discarded[:to_remove]:
        serialized = SpreaderStore._serialize(fcw)
        h = SpreaderStore.content_hash(serialized.encode())
        if store.delete(h):
            removed += 1

    print(f"Redacted {removed} discarded FCWs (target reduction: {target:.0%})")


# ── Subcommand: stats ───────────────────────────────────────────────────────

def cmd_stats(args: argparse.Namespace) -> None:
    """Show counts: FCWs by status, seeds by state, total storage."""
    store = SpreaderStore(_default_store_path())

    fcws = store.list_fcws()
    seeds = store.list_seeds()

    # FCW status counts
    fcw_counts: dict = {}
    for fcw in fcws:
        fcw_counts[fcw.status.value] = fcw_counts.get(fcw.status.value, 0) + 1

    # Seed state counts
    seed_counts: dict = {}
    for seed in seeds:
        seed_counts[seed.state.value] = seed_counts.get(seed.state.value, 0) + 1

    print("FCWs by status:")
    for status in sorted(fcw_counts):
        print(f"  {status}: {fcw_counts[status]}")
    if not fcw_counts:
        print("  (none)")

    print("\nSeeds by state:")
    for state in sorted(seed_counts):
        print(f"  {state}: {seed_counts[state]}")
    if not seed_counts:
        print("  (none)")

    # Storage size
    total_bytes = 0
    store_dir = _default_store_path()
    if os.path.exists(store_dir):
        for root, _dirs, files in os.walk(store_dir):
            for f in files:
                total_bytes += os.path.getsize(os.path.join(root, f))

    print(f"\nTotal: {len(fcws)} FCWs, {len(seeds)} seeds, "
          f"{total_bytes:,} bytes storage")


# ── Argument parser ─────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plato-spreader",
        description="Intelligence tiling for PLATO room deadband coverage",
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # deadband-status
    p = sub.add_parser("deadband-status", help="Show deadband status for rooms")
    p.add_argument("--room", default=None, help="Filter by room ID")

    # freeze
    p = sub.add_parser("freeze", help="Create and freeze a context window")
    p.add_argument("--room", required=True, help="Room ID")
    p.add_argument("--room-type", default="sensor",
                   choices=_room_type_choices(), help="Room type")
    p.add_argument("--trigger", required=True,
                   choices=_trigger_choices(), help="Trigger type")
    p.add_argument("--completion", type=float, default=95.0,
                   help="Task completion rate %%")
    p.add_argument("--wait-time", type=float, default=10.0,
                   help="Average wait time (seconds)")
    p.add_argument("--energy", type=float, default=5.0,
                   help="Energy over baseline %%")
    p.add_argument("--mae", type=float, default=3.0,
                   help="Inference MAE %%")

    # list-fcws
    p = sub.add_parser("list-fcws", help="List frozen context windows")
    p.add_argument("--room", default=None, help="Filter by room ID")
    p.add_argument("--status", default=None,
                   choices=_status_choices(), help="Filter by status")

    # seed-candidates
    p = sub.add_parser("seed-candidates", help="List candidate seeds")
    p.add_argument("--room", default=None, help="Filter by room ID")

    # lock-seed
    p = sub.add_parser("lock-seed", help="Lock a validated seed")
    p.add_argument("seed_id", help="Seed ID to lock")

    # backtest
    p = sub.add_parser("backtest", help="Run backtest on a candidate seed")
    p.add_argument("seed_id", help="Seed ID to backtest")

    # redact
    p = sub.add_parser("redact", help="Run redaction/pruning on stored FCWs")
    p.add_argument("--target-reduction", type=float, default=0.1,
                   help="Target fraction of discarded FCWs to remove (default: 0.1)")

    # stats
    sub.add_parser("stats", help="Show aggregate counts")

    return parser


# ── Main entry point ────────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    dispatch = {
        "deadband-status": cmd_deadband_status,
        "freeze": cmd_freeze,
        "list-fcws": cmd_list_fcws,
        "seed-candidates": cmd_seed_candidates,
        "lock-seed": cmd_lock_seed,
        "backtest": cmd_backtest,
        "redact": cmd_redact,
        "stats": cmd_stats,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
