"""Tests for spreader.cli — argument parsing and subcommand invocations."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from unittest import mock

import pytest

from spreader.cli import build_parser, main
from spreader.seed_lock import SeedLockManager, _InMemorySeedStore
from spreader.store import SpreaderStore
from spreader.types import (
    FCWStatus,
    KPIMetrics,
    RoomType,
    Seed,
    SeedState,
    TriggerType,
    make_fcw,
)


@pytest.fixture
def tmp_store(tmp_path):
    """Create a temporary store directory and set SPREADER_STORE env var."""
    store_dir = str(tmp_path / "store")
    with mock.patch.dict(os.environ, {"SPREADER_STORE": store_dir}):
        yield store_dir
    # cleanup handled by tmp_path


@pytest.fixture
def store_with_fcw(tmp_store):
    """Store with one frozen FCW in it."""
    store = SpreaderStore(tmp_store)
    kpi = KPIMetrics(
        task_completion_rate=85.0,
        avg_wait_time=40.0,
        energy_over_baseline=15.0,
        inference_mae=12.0,
        timestamp=time.time(),
    )
    fcw = make_fcw("room-1", RoomType.SENSOR, kpi, TriggerType.THRESHOLD)
    fcw = fcw.transition_to(FCWStatus.FROZEN)
    store.put(fcw)
    return tmp_store


@pytest.fixture
def store_with_seed(tmp_store):
    """Store with a LOCK_PENDING seed ready to be locked."""
    store = SpreaderStore(tmp_store)
    kpi = KPIMetrics(
        task_completion_rate=96.0,
        avg_wait_time=5.0,
        energy_over_baseline=2.0,
        inference_mae=1.0,
        timestamp=time.time(),
    )
    seed = Seed(
        seed_id="seed-test-001",
        room_id="room-1",
        role_name="drift-detect",
        lineage_id="lin-001",
        state=SeedState.LOCK_PENDING,
        locked_kpis=kpi,
        created_at=time.time(),
    )
    store.put(seed)
    return tmp_store


# ── Parser tests ────────────────────────────────────────────────────────────

class TestParser:
    def test_no_args_prints_help(self, capsys):
        """No command should print help and exit 0."""
        with pytest.raises(SystemExit) as exc_info:
            main([])
        assert exc_info.value.code == 0

    def test_deadband_status_parses(self):
        parser = build_parser()
        args = parser.parse_args(["deadband-status"])
        assert args.command == "deadband-status"

    def test_deadband_status_with_room(self):
        parser = build_parser()
        args = parser.parse_args(["deadband-status", "--room", "room-42"])
        assert args.room == "room-42"

    def test_freeze_parses(self):
        parser = build_parser()
        args = parser.parse_args([
            "freeze", "--room", "room-1", "--trigger", "threshold"
        ])
        assert args.command == "freeze"
        assert args.room == "room-1"
        assert args.trigger == "threshold"

    def test_freeze_with_all_options(self):
        parser = build_parser()
        args = parser.parse_args([
            "freeze", "--room", "room-1", "--trigger", "manual",
            "--room-type", "command", "--completion", "80",
            "--wait-time", "20", "--energy", "8", "--mae", "5"
        ])
        assert args.completion == 80.0
        assert args.wait_time == 20.0
        assert args.energy == 8.0
        assert args.mae == 5.0

    def test_list_fcws_parses(self):
        parser = build_parser()
        args = parser.parse_args(["list-fcws"])
        assert args.command == "list-fcws"

    def test_list_fcws_with_filters(self):
        parser = build_parser()
        args = parser.parse_args([
            "list-fcws", "--room", "room-1", "--status", "frozen"
        ])
        assert args.room == "room-1"
        assert args.status == "frozen"

    def test_seed_candidates_parses(self):
        parser = build_parser()
        args = parser.parse_args(["seed-candidates"])
        assert args.command == "seed-candidates"

    def test_lock_seed_parses(self):
        parser = build_parser()
        args = parser.parse_args(["lock-seed", "abc-123"])
        assert args.seed_id == "abc-123"

    def test_backtest_parses(self):
        parser = build_parser()
        args = parser.parse_args(["backtest", "abc-123"])
        assert args.seed_id == "abc-123"

    def test_redact_parses(self):
        parser = build_parser()
        args = parser.parse_args(["redact", "--target-reduction", "0.2"])
        assert args.target_reduction == 0.2

    def test_redact_default(self):
        parser = build_parser()
        args = parser.parse_args(["redact"])
        assert args.target_reduction == 0.1

    def test_stats_parses(self):
        parser = build_parser()
        args = parser.parse_args(["stats"])
        assert args.command == "stats"


# ── Subcommand invocation tests ─────────────────────────────────────────────

class TestDeadbandStatus:
    def test_no_fcws(self, tmp_store, capsys):
        main(["deadband-status"])
        out = capsys.readouterr().out
        assert "No FCWs found" in out

    def test_with_fcw(self, store_with_fcw, capsys):
        main(["deadband-status"])
        out = capsys.readouterr().out
        assert "room-1" in out


class TestFreeze:
    def test_freeze_creates_fcw(self, tmp_store, capsys):
        main(["freeze", "--room", "room-test", "--trigger", "manual"])
        out = capsys.readouterr().out
        assert "Frozen FCW:" in out
        assert "room-test" in out

        # Verify it landed in the store
        store = SpreaderStore(tmp_store)
        fcws = store.list_fcws()
        assert len(fcws) == 1
        assert fcws[0].room_id == "room-test"


class TestListFcws:
    def test_empty(self, tmp_store, capsys):
        main(["list-fcws"])
        out = capsys.readouterr().out
        assert "No FCWs found" in out

    def test_lists_existing(self, store_with_fcw, capsys):
        main(["list-fcws"])
        out = capsys.readouterr().out
        assert "room-1" in out
        assert "frozen" in out

    def test_filter_by_status(self, store_with_fcw, capsys):
        main(["list-fcws", "--status", "staging"])
        out = capsys.readouterr().out
        assert "No FCWs found" in out


class TestSeedCandidates:
    def test_no_candidates(self, tmp_store, capsys):
        main(["seed-candidates"])
        out = capsys.readouterr().out
        assert "No candidate seeds" in out


class TestLockSeed:
    def test_lock_pending_seed(self, store_with_seed, capsys):
        # The fixture stores via content-hash, so we need to re-store through adapter
        from spreader.cli import _SpreaderStoreAdapter
        store = SpreaderStore(store_with_seed)
        adapter = _SpreaderStoreAdapter(store)
        mgr = SeedLockManager(store=adapter)

        # Re-propose the seed through the adapter so seed_id lookup works
        kpi = KPIMetrics(
            task_completion_rate=96.0,
            avg_wait_time=5.0,
            energy_over_baseline=2.0,
            inference_mae=1.0,
            timestamp=time.time(),
        )
        seed = mgr.propose("room-1", "drift-detect", "weights:v1", [], kpi)
        # Advance to LOCK_PENDING via validate (KPI > 95 → pass)
        seed = mgr.validate(seed.seed_id)
        assert seed.state == SeedState.LOCK_PENDING

        main(["lock-seed", seed.seed_id])
        out = capsys.readouterr().out
        assert "Locked seed" in out

    def test_lock_nonexistent(self, tmp_store, capsys):
        with pytest.raises(SystemExit):
            main(["lock-seed", "nonexistent"])
        err = capsys.readouterr().err
        assert "Error" in err


class TestBacktest:
    def test_backtest_candidate(self, tmp_store, capsys):
        # Create a CANDIDATE seed via the CLI's adapter path
        from spreader.cli import _SpreaderStoreAdapter
        store = SpreaderStore(tmp_store)
        adapter = _SpreaderStoreAdapter(store)
        mgr = SeedLockManager(store=adapter)
        kpi = KPIMetrics(
            task_completion_rate=96.0,
            avg_wait_time=5.0,
            energy_over_baseline=2.0,
            inference_mae=1.0,
            timestamp=time.time(),
        )
        seed = mgr.propose("room-1", "drift-detect", "weights:v1", [], kpi)
        seed_id = seed.seed_id

        main(["backtest", seed_id])
        out = capsys.readouterr().out
        assert "Backtest:" in out


class TestRedact:
    def test_empty_store(self, tmp_store, capsys):
        main(["redact"])
        out = capsys.readouterr().out
        assert "No FCWs to redact" in out


class TestStats:
    def test_empty_store(self, tmp_store, capsys):
        main(["stats"])
        out = capsys.readouterr().out
        assert "FCWs by status:" in out
        assert "(none)" in out

    def test_with_data(self, store_with_fcw, capsys):
        main(["stats"])
        out = capsys.readouterr().out
        assert "frozen:" in out
        assert "1 FCWs" in out
