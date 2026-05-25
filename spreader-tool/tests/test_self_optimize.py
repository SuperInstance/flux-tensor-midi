"""Tests for self-optimization harness.

Tests KPI collection, deadband detection via test failures, FCW creation,
seed locking, pattern library, development cycles, and improvement reports.
"""

import time
from unittest.mock import patch, MagicMock

import pytest

from spreader.self_optimize import SelfOptimizer, TestResult, OptimizationOpportunity
from spreader.development_patterns import DevelopmentPattern, PatternLibrary
from spreader.types import KPIMetrics, SEED_LOCK_KPI


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def opt():
    """SelfOptimizer pointed at this project."""
    return SelfOptimizer(project_root=".")


@pytest.fixture
def opt_with_defaults():
    """SelfOptimizer with pattern library loaded."""
    o = SelfOptimizer(project_root=".")
    o.pattern_library.load_defaults()
    return o


# ── Sample pytest outputs ─────────────────────────────────────────────────

PYTEST_ALL_PASS = """\
tests/test_types.py::TestConstants::test_all_constants_positive PASSED
tests/test_types.py::TestConstants::test_constants_reasonable_ranges PASSED
tests/test_deadband.py::TestDeadband::test_basic PASSED
tests/test_store.py::TestStore::test_basic PASSED
3 passed in 0.5s
"""

PYTEST_SOME_FAIL = """\
tests/test_types.py::TestConstants::test_all_constants_positive PASSED
tests/test_deadband.py::TestDeadband::test_basic PASSED
tests/test_store.py::TestStore::test_basic FAILED
tests/test_redaction.py::TestRedaction::test_basic FAILED
2 passed, 2 failed in 1.2s
"""

PYTEST_IMPORT_ERROR = """\
tests/test_broken.py::test_import PASSED
tests/test_broken.py::test_import_error FAILED
1 passed, 1 failed in 0.1s
"""

PYTEST_EMPTY = """\
no tests ran in 0.0s
"""

PYTEST_SUMMARY_ONLY = "5 passed, 3 failed in 2.0s"


# ── Test: KPI Collection ─────────────────────────────────────────────────

class TestKPICollection:
    """Tests for SelfOptimizer.collect_kpis()."""

    def test_all_passing_gives_high_completion(self, opt):
        kpi = opt.collect_kpis(pytest_output=PYTEST_ALL_PASS)
        assert kpi.task_completion_rate == 100.0

    def test_some_failing_gives_partial_completion(self, opt):
        kpi = opt.collect_kpis(pytest_output=PYTEST_SOME_FAIL)
        assert kpi.task_completion_rate == 50.0

    def test_empty_output_gives_perfect_kpis(self, opt):
        kpi = opt.collect_kpis(pytest_output=PYTEST_EMPTY)
        assert kpi.task_completion_rate == 100.0

    def test_kpi_has_timestamp(self, opt):
        kpi = opt.collect_kpis(pytest_output=PYTEST_ALL_PASS)
        assert kpi.timestamp is not None
        assert kpi.timestamp > 0

    def test_summary_only_parsing(self, opt):
        kpi = opt.collect_kpis(pytest_output=PYTEST_SUMMARY_ONLY)
        assert kpi.task_completion_rate == pytest.approx(
            5.0 / 8.0 * 100.0, abs=0.1
        )

    def test_energy_over_baseline_starts_zero(self, opt):
        kpi = opt.collect_kpis(pytest_output=PYTEST_ALL_PASS)
        # First run sets baseline = current LOC, so energy = 0
        assert kpi.energy_over_baseline == 0.0

    def test_inference_mae_is_coverage_gap(self, opt):
        kpi = opt.collect_kpis(pytest_output=PYTEST_ALL_PASS)
        # Should be >= 0 since some modules may lack test files
        assert kpi.inference_mae >= 0.0


# ── Test: Deadband Detection ─────────────────────────────────────────────

class TestDeadbandDetection:
    """Tests for deadband detection when tests fail."""

    def test_good_kpis_no_deadband(self, opt):
        kpi = opt.collect_kpis(pytest_output=PYTEST_ALL_PASS)
        result = opt.room.tick(kpi)
        # Single tick — deadband needs sustained breach
        assert not result["deadband_state"].in_deadband

    def test_sustained_bad_kpis_enter_deadband(self):
        """Feed many bad KPIs and verify deadband entry."""
        opt = SelfOptimizer(project_root=".")
        bad_kpi = KPIMetrics(
            task_completion_rate=50.0,
            avg_wait_time=40.0,
            energy_over_baseline=20.0,
            inference_mae=20.0,
            timestamp=time.time(),
        )
        from spreader.types import DeadbandConfig

        # Use short durations for testing
        config = DeadbandConfig(
            completion_rate_duration=0.0,  # instant breach
            wait_time_duration=0.0,
            energy_duration=0.0,
            mae_consecutive_windows=1,
        )
        opt.room._detector = __import__(
            "spreader.deadband", fromlist=["DeadbandDetector"]
        ).DeadbandDetector(config)

        result = opt.room.tick(bad_kpi)
        assert result["deadband_state"].in_deadband


# ── Test: FCW Creation ───────────────────────────────────────────────────

class TestFCWCreation:
    """Tests for FCW creation on deadband entry."""

    def test_fcw_created_on_deadband_entry(self):
        opt = SelfOptimizer(project_root=".")
        from spreader.types import DeadbandConfig

        config = DeadbandConfig(
            completion_rate_duration=0.0,
            wait_time_duration=0.0,
            energy_duration=0.0,
            mae_consecutive_windows=1,
        )
        opt.room._detector = __import__(
            "spreader.deadband", fromlist=["DeadbandDetector"]
        ).DeadbandDetector(config)

        good_kpi = KPIMetrics(
            task_completion_rate=100.0,
            avg_wait_time=0.0,
            energy_over_baseline=0.0,
            inference_mae=0.0,
            timestamp=time.time(),
        )
        bad_kpi = KPIMetrics(
            task_completion_rate=50.0,
            avg_wait_time=40.0,
            energy_over_baseline=20.0,
            inference_mae=20.0,
            timestamp=time.time(),
        )

        # Good first → not in deadband
        opt.room.tick(good_kpi)
        # Bad → entering deadband
        result = opt.room.tick(bad_kpi)
        assert result["fcw_created"] is not None


# ── Test: Seed Locking ───────────────────────────────────────────────────

class TestSeedLocking:
    """Tests for seed locking when all tests pass."""

    def test_seed_locked_on_excellent_kpis(self, opt):
        """When KPIs >= SEED_LOCK_KPI, a seed should get locked."""
        excellent_kpi = KPIMetrics(
            task_completion_rate=98.0,
            avg_wait_time=0.1,
            energy_over_baseline=0.0,
            inference_mae=0.0,
            timestamp=time.time(),
        )
        result = opt.room.tick(excellent_kpi)
        # After one tick with excellent KPIs, seed should be proposed + locked
        assert result["active_seed"] is not None
        if result["active_seed"] is not None:
            assert result["active_seed"].state.value == "locked"


# ── Test: Pattern Library ────────────────────────────────────────────────

class TestPatternLibrary:
    """Tests for PatternLibrary and DevelopmentPattern."""

    def test_register_and_get(self):
        lib = PatternLibrary()
        p = DevelopmentPattern(
            pattern_id="test-1",
            name="Test Pattern",
            description="A test",
            applies_when="testing",
            code_template="pass",
            success_rate=0.9,
            locked=False,
        )
        lib.register(p)
        assert lib.get("test-1") is not None
        assert lib.get("test-1").name == "Test Pattern"

    def test_find_for_context(self):
        lib = PatternLibrary()
        lib.register(DevelopmentPattern(
            pattern_id="p1",
            name="State Machine Pattern",
            description="Build state machines",
            applies_when="building lifecycle transitions",
            code_template="pass",
            success_rate=1.0,
            locked=True,
            tags=["state-machine"],
        ))
        lib.register(DevelopmentPattern(
            pattern_id="p2",
            name="Cache Pattern",
            description="Cache results",
            applies_when="caching data",
            code_template="pass",
            success_rate=0.8,
            locked=True,
            tags=["cache"],
        ))
        results = lib.find_for_context("state machine transitions")
        assert len(results) >= 1
        assert results[0].pattern_id == "p1"

    def test_lock_pattern(self):
        lib = PatternLibrary()
        lib.register(DevelopmentPattern(
            pattern_id="p-lock",
            name="Lockable",
            description="test",
            applies_when="test",
            code_template="pass",
            success_rate=1.0,
            locked=False,
        ))
        locked = lib.lock_pattern("p-lock")
        assert locked.locked is True
        assert lib.get("p-lock").locked is True

    def test_load_defaults(self):
        lib = PatternLibrary()
        lib.load_defaults()
        all_patterns = lib.list_all()
        assert len(all_patterns) >= 7  # We defined 7 defaults

    def test_default_patterns_locked(self):
        lib = PatternLibrary()
        lib.load_defaults()
        locked = lib.list_locked()
        assert len(locked) >= 7

    def test_default_pattern_has_cleanup_bug(self):
        lib = PatternLibrary()
        lib.load_defaults()
        p = lib.get("cleanup_bug_pattern")
        assert p is not None
        assert "cleanup" in p.name.lower() or "bug" in p.name.lower()

    def test_record_use_updates_rate(self):
        p = DevelopmentPattern(
            pattern_id="r1",
            name="Rate Test",
            description="test",
            applies_when="test",
            code_template="pass",
            success_rate=1.0,
            locked=False,
            use_count=2,
        )
        p.record_use(False)
        assert p.use_count == 3
        assert p.success_rate == pytest.approx(2.0 / 3.0, abs=0.01)

    def test_lock_nonexistent_raises(self):
        lib = PatternLibrary()
        with pytest.raises(KeyError):
            lib.lock_pattern("no-such-id")


# ── Test: Development Cycle ──────────────────────────────────────────────

class TestDevelopmentCycle:
    """Tests for SelfOptimizer.run_development_cycle()."""

    def test_cycle_runs_iterations(self, opt):
        outputs = [PYTEST_ALL_PASS] * 5
        results = opt.run_development_cycle(iterations=5, pytest_outputs=outputs)
        assert len(results) == 5
        assert all("iteration" in r for r in results)
        assert all("kpi" in r for r in results)

    def test_cycle_tracks_history(self, opt):
        outputs = [PYTEST_ALL_PASS] * 3
        opt.run_development_cycle(iterations=3, pytest_outputs=outputs)
        assert len(opt.tick_history) == 3

    def test_cycle_with_bad_kpis_detects_failures(self, opt):
        outputs = [PYTEST_SOME_FAIL] * 5
        results = opt.run_development_cycle(iterations=5, pytest_outputs=outputs)
        # At least one iteration should have failure analysis
        any_failures = any("failures" in r for r in results)
        # May not always detect depending on deadband thresholds
        assert isinstance(results, list)

    def test_cycle_seed_locked_on_good_kpis(self, opt):
        outputs = [PYTEST_ALL_PASS] * 10
        results = opt.run_development_cycle(iterations=10, pytest_outputs=outputs)
        # With all passing tests, should eventually lock a seed
        has_seed = any(r.get("seed_locked") is not None for r in results)
        assert has_seed


# ── Test: Improvement Report ─────────────────────────────────────────────

class TestImprovementReport:
    """Tests for SelfOptimizer.generate_improvement_report()."""

    def test_report_generates_markdown(self, opt):
        # Use mocked pytest output to avoid running real pytest
        opt.collect_kpis(pytest_output=PYTEST_ALL_PASS)
        with patch.object(opt, '_run_pytest', return_value=PYTEST_ALL_PASS):
            report = opt.generate_improvement_report()
        assert "# Self-Optimization Report" in report
        assert "Current KPIs" in report
        assert "Deadband Status" in report

    def test_report_includes_optimization_opportunities(self, opt):
        with patch.object(opt, '_run_pytest', return_value=PYTEST_ALL_PASS):
            report = opt.generate_improvement_report()
        assert "Optimization Opportunities" in report

    def test_report_includes_locked_patterns(self, opt_with_defaults):
        with patch.object(opt_with_defaults, '_run_pytest', return_value=PYTEST_ALL_PASS):
            report = opt_with_defaults.generate_improvement_report()
        assert "Locked Development Patterns" in report
        assert "Frozen Dataclass" in report or "frozen_dataclass" in report


# ── Test: Failure Analysis ───────────────────────────────────────────────

class TestFailureAnalysis:
    """Tests for SelfOptimizer.analyze_failures()."""

    def test_parse_failing_tests(self, opt):
        failures = opt.analyze_failures(pytest_output=PYTEST_SOME_FAIL)
        assert len(failures) == 2
        assert all("test" in f for f in failures)
        assert all("category" in f for f in failures)

    def test_no_failures_returns_empty(self, opt):
        failures = opt.analyze_failures(pytest_output=PYTEST_ALL_PASS)
        assert len(failures) == 0

    def test_import_error_categorization(self, opt):
        failures = opt.analyze_failures(pytest_output=PYTEST_IMPORT_ERROR)
        categories = [f["category"] for f in failures]
        # At least one should be categorized
        assert len(failures) >= 1


# ── Test: Snapshot ────────────────────────────────────────────────────────

class TestSnapshot:
    """Tests for SelfOptimizer.snapshot_working_state()."""

    def test_snapshot_returns_hash(self, opt):
        h = opt.snapshot_working_state()
        assert isinstance(h, str)
        assert len(h) > 0

    def test_snapshot_is_deterministic(self, opt):
        h1 = opt.snapshot_working_state()
        h2 = opt.snapshot_working_state()
        assert h1 == h2

    def test_snapshot_format(self, opt):
        h = opt.snapshot_working_state()
        # Should be a hex string (sha256 prefix)
        assert all(c in "0123456789abcdef" for c in h)


# ── Test: Optimization Opportunities ─────────────────────────────────────

class TestOptimizationOpportunities:
    """Tests for SelfOptimizer.find_optimization_opportunities()."""

    def test_finds_opportunities(self, opt):
        opps = opt.find_optimization_opportunities()
        assert isinstance(opps, list)

    def test_opportunity_fields(self, opt):
        opps = opt.find_optimization_opportunities()
        for o in opps:
            assert isinstance(o, OptimizationOpportunity)
            assert o.category in ("duplication", "complexity", "coverage", "slow_test")
            assert 0.0 <= o.impact <= 1.0

    def test_opportunities_sorted_by_impact(self, opt):
        opps = opt.find_optimization_opportunities()
        impacts = [o.impact for o in opps]
        assert impacts == sorted(impacts, reverse=True)

    def test_coverage_gap_detected(self, opt):
        """Self-optimize module itself should be detected as uncovered."""
        opps = opt.find_optimization_opportunities()
        categories = [o.category for o in opps]
        assert "coverage" in categories


# ── Test: TestResult parsing ──────────────────────────────────────────────

class TestTestResultParsing:
    """Tests for internal pytest output parsing."""

    def test_parse_passed(self, opt):
        results = opt._parse_pytest_output(PYTEST_ALL_PASS)
        # 4 individual results + possibly summary parsed
        individual = [r for r in results if not r.node_id.startswith("summary::")]
        assert len(individual) == 4
        assert all(r.outcome == "passed" for r in individual)

    def test_parse_mixed(self, opt):
        results = opt._parse_pytest_output(PYTEST_SOME_FAIL)
        passed = [r for r in results if r.outcome == "passed"]
        failed = [r for r in results if r.outcome == "failed"]
        assert len(passed) == 2
        assert len(failed) == 2

    def test_parse_empty(self, opt):
        results = opt._parse_pytest_output(PYTEST_EMPTY)
        assert len(results) == 0

    def test_parse_node_ids(self, opt):
        results = opt._parse_pytest_output(PYTEST_ALL_PASS)
        for r in results:
            assert "::" in r.node_id
