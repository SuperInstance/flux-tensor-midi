"""
Tests for the beta testing and feedback harness.

Run with: python -m pytest tests/test_beta.py -v
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# ── SessionRecorder tests ───────────────────────────────────────────────


class TestSessionRecorder:
    """Tests for session_recorder.SessionRecorder."""

    def _make_recorder(self, tmp: Path):
        from flux_tensor_midi.beta.session_recorder import SessionRecorder
        return SessionRecorder(output_dir=tmp / "sessions")

    def test_start_session_returns_id(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        sid = rec.start_session()
        assert isinstance(sid, str)
        assert len(sid) == 12

    def test_session_id_property(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        assert rec.session_id is None
        sid = rec.start_session()
        assert rec.session_id == sid

    def test_active_property(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        assert not rec.active
        rec.start_session()
        assert rec.active
        rec.end_session()
        assert not rec.active

    def test_log_action_without_session_raises(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        with pytest.raises(RuntimeError, match="No active session"):
            rec.log_action("play", {})

    def test_log_action_records_event(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec.start_session()
        rec.log_action("param_change", {"epsilon": 0.25})
        rec.log_action("playback", {"midi_hash": "abc"})
        session = rec.end_session()
        assert len(session["actions"]) == 2
        assert session["actions"][0]["event_type"] == "param_change"
        assert session["actions"][0]["params"]["epsilon"] == 0.25
        assert session["actions"][1]["event_type"] == "playback"

    def test_log_action_has_elapsed_time(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec.start_session()
        rec.log_action("test", {})
        session = rec.end_session()
        assert "elapsed_s" in session["actions"][0]
        assert session["actions"][0]["elapsed_s"] >= 0

    def test_log_composition(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec.start_session()
        rec.log_composition("deadbeef", {"epsilon": 0.2, "constraints": ["harmonic"]})
        session = rec.end_session()
        assert len(session["compositions"]) == 1
        assert session["compositions"][0]["midi_hash"] == "deadbeef"
        assert session["compositions"][0]["params"]["epsilon"] == 0.2

    def test_end_session_persists_json(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec.start_session(user_id="test_user")
        rec.log_action("play", {})
        session = rec.end_session()

        # Verify file was written
        files = list((tmp_path / "sessions").glob("*.json"))
        assert len(files) == 1
        loaded = json.loads(files[0].read_text())
        assert loaded["session_id"] == session["session_id"]
        assert loaded["user_id"] == "test_user"

    def test_end_session_with_abandon_point(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec.start_session()
        session = rec.end_session(abandon_point="before_playback")
        assert session["abandon_point"] == "before_playback"

    def test_end_session_records_duration(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec.start_session()
        session = rec.end_session()
        assert session["total_duration_s"] is not None
        assert session["total_duration_s"] >= 0

    def test_end_session_has_timestamps(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec.start_session()
        session = rec.end_session()
        assert "started_at" in session
        assert "ended_at" in session

    def test_load_session(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec.start_session()
        rec.log_action("test", {"x": 1})
        session = rec.end_session()

        from flux_tensor_midi.beta.session_recorder import SessionRecorder
        loaded = SessionRecorder.load_session(tmp_path / "sessions" / f"{session['session_id']}.json")
        assert loaded["session_id"] == session["session_id"]

    def test_load_all_sessions(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec.start_session()
        rec.end_session()
        rec.start_session()
        rec.end_session()

        from flux_tensor_midi.beta.session_recorder import SessionRecorder
        all_sessions = SessionRecorder.load_all_sessions(tmp_path / "sessions")
        assert len(all_sessions) == 2

    def test_multiple_actions_in_order(self, tmp_path):
        rec = self._make_recorder(tmp_path)
        rec.start_session()
        for i in range(5):
            rec.log_action("step", {"i": i})
        session = rec.end_session()
        assert len(session["actions"]) == 5
        for i, action in enumerate(session["actions"]):
            assert action["params"]["i"] == i


# ── FeedbackCollector tests ─────────────────────────────────────────────


class TestFeedbackCollector:
    """Tests for feedback_collector.FeedbackCollector."""

    def _make_collector(self, tmp: Path, headless: bool = False):
        from flux_tensor_midi.beta.feedback_collector import FeedbackCollector
        return FeedbackCollector(output_dir=tmp / "feedback", headless=headless)

    def test_ask_rating_valid(self, tmp_path):
        fc = self._make_collector(tmp_path)
        record = fc.ask_rating("comp_01", 4)
        assert record["kind"] == "rating"
        assert record["payload"]["stars"] == 4
        assert record["composition_id"] == "comp_01"

    def test_ask_rating_invalid_low(self, tmp_path):
        fc = self._make_collector(tmp_path)
        with pytest.raises(ValueError, match="1-5"):
            fc.ask_rating("comp_01", 0)

    def test_ask_rating_invalid_high(self, tmp_path):
        fc = self._make_collector(tmp_path)
        with pytest.raises(ValueError, match="1-5"):
            fc.ask_rating("comp_01", 6)

    def test_ask_rating_boundary_values(self, tmp_path):
        fc = self._make_collector(tmp_path)
        fc.ask_rating("comp_01", 1)
        fc.ask_rating("comp_02", 5)
        assert fc.record_count == 2

    def test_ask_text(self, tmp_path):
        fc = self._make_collector(tmp_path)
        record = fc.ask_text("comp_01", "Loved the harmonic constraint")
        assert record["kind"] == "text"
        assert record["payload"]["text"] == "Loved the harmonic constraint"

    def test_ask_nps_valid(self, tmp_path):
        fc = self._make_collector(tmp_path)
        record = fc.ask_nps("comp_01", 9)
        assert record["kind"] == "nps"
        assert record["payload"]["score"] == 9
        assert record["payload"]["category"] == "promoter"

    def test_ask_nps_categories(self, tmp_path):
        fc = self._make_collector(tmp_path)
        r1 = fc.ask_nps("c1", 3)
        assert r1["payload"]["category"] == "detractor"
        r2 = fc.ask_nps("c2", 7)
        assert r2["payload"]["category"] == "passive"
        r3 = fc.ask_nps("c3", 10)
        assert r3["payload"]["category"] == "promoter"

    def test_ask_nps_invalid(self, tmp_path):
        fc = self._make_collector(tmp_path)
        with pytest.raises(ValueError, match="0-10"):
            fc.ask_nps("c1", 11)

    def test_record_count(self, tmp_path):
        fc = self._make_collector(tmp_path)
        assert fc.record_count == 0
        fc.ask_rating("c1", 3)
        assert fc.record_count == 1
        fc.ask_text("c1", "nice")
        assert fc.record_count == 2

    def test_export_feedback(self, tmp_path):
        fc = self._make_collector(tmp_path)
        fc.ask_rating("c1", 5)
        fc.ask_text("c1", "great")
        records = fc.export_feedback()
        assert len(records) == 2
        # Verify file exists
        files = list((tmp_path / "feedback").glob("*.json"))
        assert len(files) == 1

    def test_headless_flag_in_records(self, tmp_path):
        fc = self._make_collector(tmp_path, headless=True)
        record = fc.ask_rating("c1", 3)
        assert record["headless"] is True

    def test_load_all_feedback(self, tmp_path):
        from flux_tensor_midi.beta.feedback_collector import FeedbackCollector
        fc = FeedbackCollector(output_dir=tmp_path / "feedback")
        fc.ask_rating("c1", 5)
        fc.export_feedback()
        fc2 = FeedbackCollector(output_dir=tmp_path / "feedback")
        fc2.ask_rating("c2", 3)
        fc2.export_feedback()

        all_fb = FeedbackCollector.load_all_feedback(tmp_path / "feedback")
        assert len(all_fb) >= 1  # At least one feedback file loaded


# ── ExperimentRunner tests ──────────────────────────────────────────────


class TestExperimentRunner:
    """Tests for experiment_runner.ExperimentRunner."""

    def _make_runner(self, tmp: Path):
        from flux_tensor_midi.beta.experiment_runner import ExperimentRunner
        return ExperimentRunner(output_dir=tmp / "experiments")

    def test_define_experiment(self, tmp_path):
        runner = self._make_runner(tmp_path)
        exp = runner.define_experiment("test_exp", {"epsilon": 0.15}, {"epsilon": 0.30})
        assert exp.name == "test_exp"
        assert exp.control_params == {"epsilon": 0.15}
        assert exp.treatment_params == {"epsilon": 0.30}

    def test_assign_group_deterministic(self, tmp_path):
        runner = self._make_runner(tmp_path)
        runner.define_experiment("test", {"e": 0.1}, {"e": 0.2})
        g1 = runner.assign_group("test", "user_42")
        g2 = runner.assign_group("test", "user_42")
        assert g1 == g2
        assert g1 in ("control", "treatment")

    def test_assign_group_balanced(self, tmp_path):
        """With enough users, should be roughly 50/50."""
        runner = self._make_runner(tmp_path)
        runner.define_experiment("test", {"e": 0.1}, {"e": 0.2})
        groups = [runner.assign_group("test", f"user_{i}") for i in range(100)]
        ctrl = groups.count("control")
        treat = groups.count("treatment")
        # Should be within 30-70 range for 100 users
        assert 30 <= ctrl <= 70
        assert 30 <= treat <= 70

    def test_get_params(self, tmp_path):
        runner = self._make_runner(tmp_path)
        runner.define_experiment("test", {"e": 0.1}, {"e": 0.2})
        params = runner.get_params("test", "user_1")
        assert "e" in params
        assert params["e"] in (0.1, 0.2)

    def test_record_metric(self, tmp_path):
        runner = self._make_runner(tmp_path)
        runner.define_experiment("test", {"e": 0.1}, {"e": 0.2})
        runner.assign_group("test", "user_1")
        runner.record_metric("test", "user_1", "composition_count", 5.0)
        exp = runner._get_experiment("test")
        # Should have recorded one metric
        total = len(exp.metrics["control"]) + len(exp.metrics["treatment"])
        assert total == 1

    def test_analyze_insufficient_data(self, tmp_path):
        runner = self._make_runner(tmp_path)
        runner.define_experiment("test", {"e": 0.1}, {"e": 0.2})
        results = runner.analyze_results("test")
        assert results["significant_005"] is False
        assert "Insufficient data" in results["note"]

    def test_analyze_with_data(self, tmp_path):
        runner = self._make_runner(tmp_path)
        runner.define_experiment("test", {"e": 0.1}, {"e": 0.2})

        # Generate data: control has lower values
        for i in range(20):
            uid = f"u{i}"
            runner.assign_group("test", uid)
            group = runner._get_experiment("test").assignments[uid]
            val = 3.0 + (0.0 if group == "control" else 2.0) + (i * 0.1)
            runner.record_metric("test", uid, "score", val)

        results = runner.analyze_results("test", metric_name="score")
        assert results["control_n"] > 0
        assert results["treatment_n"] > 0
        assert isinstance(results["t_statistic"], float)

    def test_analyze_undefined_experiment_raises(self, tmp_path):
        runner = self._make_runner(tmp_path)
        with pytest.raises(KeyError, match="not defined"):
            runner.analyze_results("nope")

    def test_save_and_load_experiment(self, tmp_path):
        runner = self._make_runner(tmp_path)
        runner.define_experiment("persist", {"x": 1}, {"x": 2})
        runner.assign_group("persist", "u1")
        runner.record_metric("persist", "u1", "count", 5)

        runner.save_experiment("persist")

        # Load into fresh runner
        runner2 = self._make_runner(tmp_path)
        exp = runner2.load_experiment("persist")
        assert exp.name == "persist"
        assert "u1" in exp.assignments

    def test_welch_t_test_basic(self):
        from flux_tensor_midi.beta.experiment_runner import _welch_t_test
        # Identical samples -> t ~ 0, p ~ 1
        t, p = _welch_t_test([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
        assert abs(t) < 0.01
        assert p > 0.9

    def test_welch_t_test_different(self):
        from flux_tensor_midi.beta.experiment_runner import _welch_t_test
        t, p = _welch_t_test([1, 1, 1, 1, 1], [10, 10, 10, 10, 10])
        # Both groups have std=0, so t will be 0 and p=1
        # This is a degenerate case. Test with slight variance instead:
        t2, p2 = _welch_t_test([1.0, 1.1, 0.9, 1.0, 1.05], [10.0, 10.1, 9.9, 10.0, 10.05])
        assert abs(t2) > 10
        assert p2 < 0.001

    def test_cohens_d(self):
        from flux_tensor_midi.beta.experiment_runner import _cohens_d
        d = _cohens_d([1, 2, 3], [1, 2, 3])
        assert abs(d) < 0.01
        # When both groups have 0 variance, d = 0 (pooled std = 0)
        d_zero = _cohens_d([1, 1, 1], [10, 10, 10])
        assert d_zero == 0.0
        # With slight variance, large effect
        d2 = abs(_cohens_d([1, 2, 1.5], [10, 11, 10.5]))
        assert d2 > 5

    def test_mean_and_std(self):
        from flux_tensor_midi.beta.experiment_runner import _mean, _std
        assert _mean([2, 4, 6]) == 4.0
        assert abs(_std([2, 4, 6]) - 2.0) < 0.01
        assert _mean([]) == 0.0
        assert _std([5]) == 0.0


# ── DiscoveryEngine tests ──────────────────────────────────────────────


class TestDiscoveryEngine:
    """Tests for discovery_engine.DiscoveryEngine."""

    def _make_engine_with_sessions(self, n: int = 5):
        from flux_tensor_midi.beta.discovery_engine import DiscoveryEngine
        engine = DiscoveryEngine()
        sessions = []
        for i in range(n):
            sessions.append({
                "session_id": f"sess_{i:04d}",
                "user_id": f"user_{i % 3}",  # 3 unique users
                "started_at": "2025-01-01T00:00:00Z",
                "ended_at": "2025-01-01T00:01:00Z",
                "total_duration_s": 30 + i * 10,
                "actions": [
                    {"event_type": "param_change", "params": {"epsilon": 0.1 + i * 0.05}, "elapsed_s": 1.0},
                    {"event_type": "playback", "params": {}, "elapsed_s": 5.0},
                ],
                "compositions": [
                    {"midi_hash": f"hash_{i}", "params": {"epsilon": 0.1 + i * 0.05}, "elapsed_s": 3.0},
                ] * (i + 1),
                "abandon_point": "before_playback" if i == 0 else None,
            })
        engine.ingest(sessions)
        return engine

    def test_ingest_counts_sessions(self):
        engine = self._make_engine_with_sessions(10)
        assert len(engine.sessions) == 10

    def test_ingest_filters_invalid(self):
        from flux_tensor_midi.beta.discovery_engine import DiscoveryEngine
        engine = DiscoveryEngine()
        n = engine.ingest([{"bad": True}, {"session_id": "x"}, "not_a_dict"])
        assert n == 1

    def test_find_patterns_returns_list(self):
        engine = self._make_engine_with_sessions(3)
        patterns = engine.find_patterns()
        assert isinstance(patterns, list)
        assert len(patterns) > 0

    def test_find_patterns_popular_params(self):
        engine = self._make_engine_with_sessions(5)
        patterns = engine.find_patterns()
        param_patterns = [p for p in patterns if p["category"] == "popular_parameters"]
        assert len(param_patterns) > 0

    def test_find_patterns_abandon_points(self):
        engine = self._make_engine_with_sessions(5)
        patterns = engine.find_patterns()
        abandon_patterns = [p for p in patterns if p["category"] == "abandon_points"]
        assert len(abandon_patterns) > 0

    def test_find_patterns_retention(self):
        engine = self._make_engine_with_sessions(5)
        patterns = engine.find_patterns()
        retention = [p for p in patterns if p["category"] == "retention"]
        assert len(retention) > 0
        assert retention[0]["data"]["total_users"] == 3

    def test_generate_report(self, tmp_path):
        engine = self._make_engine_with_sessions(5)
        engine.find_patterns()
        report_path = engine.generate_report(tmp_path / "REPORT.md")
        assert report_path.exists()
        content = report_path.read_text()
        assert "Discovery Report" in content

    def test_generate_report_auto_finds_patterns(self, tmp_path):
        engine = self._make_engine_with_sessions(3)
        # Don't call find_patterns first — generate_report should auto-call
        report_path = engine.generate_report(tmp_path / "REPORT.md")
        assert report_path.exists()

    def test_empty_sessions_no_crash(self):
        from flux_tensor_midi.beta.discovery_engine import DiscoveryEngine
        engine = DiscoveryEngine()
        patterns = engine.find_patterns()
        assert patterns == []

    def test_ingest_from_directory(self, tmp_path):
        # Write some session files
        d = tmp_path / "sessions"
        d.mkdir()
        for i in range(3):
            (d / f"s{i}.json").write_text(json.dumps({
                "session_id": f"s{i}",
                "user_id": "u1",
                "actions": [],
                "compositions": [],
            }))

        from flux_tensor_midi.beta.discovery_engine import DiscoveryEngine
        engine = DiscoveryEngine()
        n = engine.ingest_from_directory(d)
        assert n == 3

    def test_ingest_from_missing_directory(self):
        from flux_tensor_midi.beta.discovery_engine import DiscoveryEngine
        engine = DiscoveryEngine()
        n = engine.ingest_from_directory("/nonexistent/path")
        assert n == 0


# ── CLI tests ───────────────────────────────────────────────────────────


class TestBetaCLI:
    """Tests for beta/cli.py argument parsing and routing."""

    def test_experiment_command_creates_experiment(self, tmp_path, capsys):
        from flux_tensor_midi.beta.cli import _experiment_cmd
        import argparse

        args = argparse.Namespace(
            name="goldilocks",
            control='{"epsilon": 0.15}',
            treatment='{"epsilon": 0.30}',
        )

        _experiment_cmd(args)

        output = capsys.readouterr().out
        assert "goldilocks" in output
        assert "0.15" in output
        assert "0.3" in output

    def test_analyze_command(self, tmp_path, capsys):
        from flux_tensor_midi.beta.cli import _analyze_cmd
        import argparse

        args = argparse.Namespace(
            data_dir=str(tmp_path / "sessions"),
            output=str(tmp_path / "REPORT.md"),
        )

        _analyze_cmd(args)

        output = capsys.readouterr().out
        assert "0 sessions" in output

    def test_build_parser(self):
        """Test that build_parser doesn't crash."""
        import argparse
        from flux_tensor_midi.beta.cli import build_parser

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        build_parser(sub)

        # Parse beta experiment command
        args = parser.parse_args(["beta", "experiment", "--name", "test",
                                   "--control", '{"x": 1}',
                                   "--treatment", '{"x": 2}'])
        assert args.beta_command == "experiment"
        assert args.name == "test"
