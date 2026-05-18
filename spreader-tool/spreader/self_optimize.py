"""Self-optimization harness — the spreader-tool optimizes itself.

Monitors the project's test suite, code quality, and development velocity.
When tests fail or metrics degrade (deadband), it freezes snapshots of the
working state. When metrics are excellent, it locks those patterns as seeds
for future development.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .deadband import DeadbandDetector
from .development_patterns import DevelopmentPattern, PatternLibrary
from .frozen_context import FCWManager
from .seed_lock import SeedLockManager
from .spreader_room import SpreaderRoom
from .types import (
    DeadbandConfig,
    KPIMetrics,
    RoomType,
    SEED_LOCK_KPI,
    SeedState,
    TriggerType,
)


@dataclass
class TestResult:
    """Parsed result from a single test."""

    node_id: str
    outcome: str  # passed, failed, error, skipped
    duration: float
    message: Optional[str] = None
    traceback: Optional[str] = None


@dataclass
class OptimizationOpportunity:
    """An identified improvement opportunity."""

    category: str  # duplication, complexity, coverage, slow_test
    description: str
    location: str
    impact: float  # 0–1 estimated impact
    suggestion: str


class SelfOptimizer:
    """The spreader-tool optimizes itself.

    Collects KPIs from the test suite, feeds them into a SpreaderRoom,
    and creates FCWs on deadband entry or locks seeds on excellent KPIs.
    """

    def __init__(self, project_root: str = ".") -> None:
        self.project_root = Path(project_root).resolve()
        self._baseline_loc: Optional[int] = None

        # Subsystems
        self._room = SpreaderRoom(
            room_id="self-optimize",
            room_type=RoomType.SIMULATION,
            window_size=5,
        )
        self._pattern_lib = PatternLibrary()
        self._pattern_lib.load_defaults()

        # History
        self._tick_history: List[Dict[str, Any]] = []
        self._fcw_snapshots: List[str] = []
        self._seeds_locked: List[str] = []

    # ── KPI Collection ───────────────────────────────────────────────────

    def collect_kpis(self, pytest_output: Optional[str] = None) -> KPIMetrics:
        """Run pytest, collect metrics.

        If *pytest_output* is provided (for testing), parse it instead of
        running pytest.

        KPIs:
            task_completion_rate = test_pass_rate * 100
            avg_wait_time = avg test execution time (seconds)
            energy_over_baseline = lines_of_code / baseline (complexity cost)
            inference_mae = coverage gap (100 - coverage%)
        """
        if pytest_output is None:
            pytest_output = self._run_pytest()

        results = self._parse_pytest_output(pytest_output)
        if not results:
            # No tests found — treat as neutral
            return KPIMetrics(
                task_completion_rate=100.0,
                avg_wait_time=0.0,
                energy_over_baseline=0.0,
                inference_mae=0.0,
                timestamp=time.time(),
            )

        # task_completion_rate
        passed = sum(1 for r in results if r.outcome == "passed")
        total = len(results)
        task_completion_rate = (passed / total) * 100.0 if total else 100.0

        # avg_wait_time
        durations = [r.duration for r in results if r.duration > 0]
        avg_wait_time = sum(durations) / len(durations) if durations else 0.0

        # energy_over_baseline
        total_loc = self._count_lines_of_code()
        baseline = self._get_baseline_loc()
        energy_over_baseline = ((total_loc - baseline) / baseline) * 100.0 if baseline > 0 else 0.0
        energy_over_baseline = max(0.0, energy_over_baseline)

        # inference_mae (coverage gap — simplified: estimate from test/file ratio)
        inference_mae = self._estimate_coverage_gap()

        return KPIMetrics(
            task_completion_rate=task_completion_rate,
            avg_wait_time=avg_wait_time,
            energy_over_baseline=energy_over_baseline,
            inference_mae=inference_mae,
            timestamp=time.time(),
        )

    # ── Development Cycle ────────────────────────────────────────────────

    def run_development_cycle(
        self,
        iterations: int = 10,
        pytest_outputs: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Run N iterations of self-optimization.

        For each iteration:
        1. Collect KPIs from test suite
        2. Feed into SpreaderRoom.tick()
        3. If deadband detected:
           - Analyze which tests are failing
           - Create FCW of current state
        4. If excellent KPIs (>= SEED_LOCK_KPI):
           - Lock a seed for the current development pattern

        If *pytest_outputs* is provided, use them instead of running pytest.
        """
        results: List[Dict[str, Any]] = []

        for i in range(iterations):
            # Step 1: Collect KPIs
            output = None
            if pytest_outputs and i < len(pytest_outputs):
                output = pytest_outputs[i]
            kpi = self.collect_kpis(pytest_output=output)

            # Step 2: Feed into SpreaderRoom
            tick_result = self._room.tick(kpi)

            entry: Dict[str, Any] = {
                "iteration": i,
                "kpi": kpi,
                "tick_result": tick_result,
                "fcw_created": None,
                "seed_locked": None,
            }

            # Step 3: Deadband handling
            if tick_result["deadband_state"].in_deadband:
                failures = self.analyze_failures(output)
                entry["failures"] = failures

                if tick_result.get("fcw_created"):
                    snapshot_hash = self.snapshot_working_state()
                    self._fcw_snapshots.append(snapshot_hash)
                    entry["fcw_created"] = snapshot_hash

            # Step 4: Excellent KPIs → lock seed
            if kpi.task_completion_rate >= SEED_LOCK_KPI:
                active = tick_result.get("active_seed")
                if active is not None and hasattr(active, "state"):
                    if active.state == SeedState.LOCKED:
                        if active.seed_id not in self._seeds_locked:
                            self._seeds_locked.append(active.seed_id)
                        entry["seed_locked"] = active.seed_id

            self._tick_history.append(entry)
            results.append(entry)

        return results

    # ── Failure Analysis ─────────────────────────────────────────────────

    def analyze_failures(self, pytest_output: Optional[str] = None) -> List[Dict]:
        """Parse pytest output, identify failing tests, categorize.

        Categories:
            - Import errors
            - Assertion failures
            - Type errors
            - Timeout/complexity issues
            - Other
        """
        if pytest_output is None:
            pytest_output = self._run_pytest()

        results = self._parse_pytest_output(pytest_output)
        failures = [r for r in results if r.outcome in ("failed", "error")]

        categorized: List[Dict] = []
        for f in failures:
            category = self._categorize_failure(f)
            categorized.append({
                "test": f.node_id,
                "category": category,
                "message": f.message,
                "duration": f.duration,
            })

        return categorized

    # ── Snapshot ──────────────────────────────────────────────────────────

    def snapshot_working_state(self) -> str:
        """Create a content-addressed snapshot of all passing tests + current code.

        Returns the content hash for the FCW.
        """
        snapshot_data: Dict[str, Any] = {
            "files": {},
        }

        # Collect Python source files
        for path in sorted(self.project_root.rglob("*.py")):
            # Skip __pycache__, .git, etc.
            parts = path.relative_to(self.project_root).parts
            if any(p.startswith(".") or p == "__pycache__" for p in parts):
                continue
            try:
                content = path.read_text(errors="replace")
                rel = str(path.relative_to(self.project_root))
                snapshot_data["files"][rel] = hashlib.sha256(
                    content.encode()
                ).hexdigest()[:16]
            except OSError:
                continue

        blob = json.dumps(snapshot_data, sort_keys=True)
        content_hash = hashlib.sha256(blob.encode()).hexdigest()[:40]
        return content_hash

    # ── Optimization Opportunities ────────────────────────────────────────

    def find_optimization_opportunities(self) -> List[OptimizationOpportunity]:
        """Analyze the codebase for improvement opportunities.

        Looks for:
        - Duplicated patterns across modules
        - Overly complex functions (high line count)
        - Missing test coverage (modules without test files)
        - Slow tests (execution time outliers)
        """
        opportunities: List[OptimizationOpportunity] = []

        # 1. Missing test coverage
        source_modules = set()
        test_modules = set()
        src_dir = self.project_root / "spreader"
        test_dir = self.project_root / "tests"

        if src_dir.is_dir():
            for f in src_dir.glob("*.py"):
                if f.name.startswith("_") and f.name != "__init__.py":
                    continue
                source_modules.add(f.stem)
        if test_dir.is_dir():
            for f in test_dir.glob("test_*.py"):
                test_modules.add(f.stem.replace("test_", ""))

        for mod in source_modules:
            if mod not in test_modules and mod != "__init__":
                opportunities.append(OptimizationOpportunity(
                    category="coverage",
                    description=f"Module 'spreader/{mod}.py' has no test file",
                    location=f"tests/test_{mod}.py",
                    impact=0.7,
                    suggestion=f"Create tests/test_{mod}.py with unit tests for {mod} module",
                ))

        # 2. Overly complex functions
        if src_dir.is_dir():
            for f in src_dir.glob("*.py"):
                try:
                    content = f.read_text()
                except OSError:
                    continue
                func_blocks = self._extract_functions(content)
                for func_name, line_count in func_blocks:
                    if line_count > 50:
                        opportunities.append(OptimizationOpportunity(
                            category="complexity",
                            description=(
                                f"Function '{func_name}' in {f.name} is "
                                f"{line_count} lines (threshold: 50)"
                            ),
                            location=f"spreader/{f.name}::{func_name}",
                            impact=0.5,
                            suggestion=f"Consider breaking {func_name} into smaller helper functions",
                        ))

        # 3. Duplicated import patterns (simple heuristic)
        import_counts: Dict[str, int] = {}
        if src_dir.is_dir():
            for f in src_dir.glob("*.py"):
                try:
                    content = f.read_text()
                except OSError:
                    continue
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("from ") or stripped.startswith("import "):
                        import_counts[stripped] = import_counts.get(stripped, 0) + 1

        for imp, count in import_counts.items():
            if count >= 3:
                opportunities.append(OptimizationOpportunity(
                    category="duplication",
                    description=f"Import '{imp}' appears in {count} modules",
                    location="spreader/",
                    impact=0.3,
                    suggestion="Consider consolidating into __init__.py or a shared utils module",
                ))

        # Sort by impact descending
        opportunities.sort(key=lambda o: o.impact, reverse=True)
        return opportunities

    # ── Report ────────────────────────────────────────────────────────────

    def generate_improvement_report(self) -> str:
        """Full markdown report of current self-optimization state."""
        lines: List[str] = []
        lines.append("# Self-Optimization Report")
        lines.append("")
        lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Project root:** {self.project_root}")
        lines.append("")

        # Current KPIs
        kpi = self.collect_kpis()
        lines.append("## Current KPIs")
        lines.append("")
        lines.append(f"| Metric | Value | Threshold | Status |")
        lines.append(f"|--------|-------|-----------|--------|")
        lines.append(f"| Task Completion Rate | {kpi.task_completion_rate:.1f}% | ≥90% |"
                      f" {'✅' if kpi.task_completion_rate >= 90 else '❌'} |")
        lines.append(f"| Avg Wait Time | {kpi.avg_wait_time:.3f}s | <30s |"
                      f" {'✅' if kpi.avg_wait_time < 30 else '❌'} |")
        lines.append(f"| Energy Over Baseline | {kpi.energy_over_baseline:.1f}% | <10% |"
                      f" {'✅' if kpi.energy_over_baseline < 10 else '⚠️'} |")
        lines.append(f"| Inference MAE (coverage gap) | {kpi.inference_mae:.1f}% | <10% |"
                      f" {'✅' if kpi.inference_mae < 10 else '❌'} |")
        lines.append("")

        # Deadband status
        status = self._room.status
        lines.append("## Deadband Status")
        lines.append("")
        if status["in_deadband"]:
            lines.append("**Status:** 🔴 IN DEADBAND")
        else:
            lines.append("**Status:** 🟢 NOMINAL")
        lines.append(f"- Tick number: {status['tick_number']}")
        lines.append(f"- Active seed: {status.get('active_seed_id', 'None')}")
        lines.append(f"- FCW count: {status.get('fcw_count', 0)}")
        lines.append("")

        # FCWs
        lines.append("## FCW Snapshots Created")
        lines.append("")
        if self._fcw_snapshots:
            for s in self._fcw_snapshots:
                lines.append(f"- `{s}`")
        else:
            lines.append("No FCWs created yet.")
        lines.append("")

        # Seeds
        lines.append("## Seeds Locked")
        lines.append("")
        if self._seeds_locked:
            for sid in self._seeds_locked:
                lines.append(f"- `{sid}`")
        else:
            lines.append("No seeds locked yet.")
        lines.append("")

        # Optimization opportunities
        opps = self.find_optimization_opportunities()
        lines.append("## Optimization Opportunities")
        lines.append("")
        if opps:
            lines.append(f"| # | Category | Impact | Description |")
            lines.append(f"|---|----------|--------|-------------|")
            for i, o in enumerate(opps[:15], 1):
                lines.append(f"| {i} | {o.category} | {o.impact:.0%} | {o.description} |")
        else:
            lines.append("No optimization opportunities found.")
        lines.append("")

        # Pattern library
        patterns = self._pattern_lib.list_locked()
        lines.append("## Locked Development Patterns")
        lines.append("")
        if patterns:
            for p in patterns:
                lines.append(f"### {p.name}")
                lines.append(f"- **ID:** `{p.pattern_id}`")
                lines.append(f"- **Success rate:** {p.success_rate:.0%}")
                lines.append(f"- **Use count:** {p.use_count}")
                lines.append(f"- **Applies when:** {p.applies_when}")
                lines.append("")
        else:
            lines.append("No patterns locked yet.")
        lines.append("")

        return "\n".join(lines)

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def room(self) -> SpreaderRoom:
        return self._room

    @property
    def pattern_library(self) -> PatternLibrary:
        return self._pattern_lib

    @property
    def tick_history(self) -> List[Dict[str, Any]]:
        return list(self._tick_history)

    @property
    def fcw_snapshots(self) -> List[str]:
        return list(self._fcw_snapshots)

    @property
    def seeds_locked(self) -> List[str]:
        return list(self._seeds_locked)

    # ── Internal: pytest runner ───────────────────────────────────────────

    def _run_pytest(self) -> str:
        """Run pytest and capture output."""
        try:
            result = subprocess.run(
                ["python3", "-m", "pytest", "tests/", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.project_root),
            )
            return result.stdout + "\n" + result.stderr
        except subprocess.TimeoutExpired:
            return "TIMEOUT: pytest exceeded 120s"
        except Exception as e:
            return f"ERROR running pytest: {e}"

    def _parse_pytest_output(self, output: str) -> List[TestResult]:
        """Parse pytest -v output into TestResult objects."""
        results: List[TestResult] = []

        # Match lines like: tests/test_foo.py::TestClass::test_bar PASSED
        pattern = re.compile(
            r"^(tests/\S+::\S+)\s+(PASSED|FAILED|ERROR|SKIP(?:PED)?)\s*(?:\[\s*\d+%\])?\s*$",
            re.MULTILINE,
        )
        for m in pattern.finditer(output):
            node_id = m.group(1)
            outcome_raw = m.group(2).upper()
            if outcome_raw.startswith("SKIP"):
                outcome = "skipped"
            else:
                outcome = outcome_raw.lower()
            results.append(TestResult(
                node_id=node_id,
                outcome=outcome,
                duration=0.0,
            ))

        # Try to parse durations from --durations output
        dur_pattern = re.compile(r"^(\d+\.\d+)s\s+(.+)$", re.MULTILINE)
        duration_map: Dict[str, float] = {}
        for m in dur_pattern.finditer(output):
            dur = float(m.group(1))
            name = m.group(2).strip()
            duration_map[name] = dur

        # Also parse "X passed, Y failed, Z errors" summary
        # If no individual results found, parse the summary line
        if not results:
            summary = re.search(
                r"(\d+) passed(?:,\s*(\d+) failed)?(?:,\s*(\d+) errors?)?",
                output,
            )
            if summary:
                passed = int(summary.group(1))
                failed = int(summary.group(2) or 0)
                errors = int(summary.group(3) or 0)
                for i in range(passed):
                    results.append(TestResult(
                        node_id=f"summary::test_{i}",
                        outcome="passed",
                        duration=0.0,
                    ))
                for i in range(failed):
                    results.append(TestResult(
                        node_id=f"summary::failure_{i}",
                        outcome="failed",
                        duration=0.0,
                    ))
                for i in range(errors):
                    results.append(TestResult(
                        node_id=f"summary::error_{i}",
                        outcome="error",
                        duration=0.0,
                    ))

        return results

    # ── Internal: categorization ──────────────────────────────────────────

    @staticmethod
    def _categorize_failure(result: TestResult) -> str:
        """Categorize a test failure by type."""
        msg = (result.message or "") + (result.traceback or "")
        msg_lower = msg.lower()

        if "import" in msg_lower or "modulenotfound" in msg_lower:
            return "import_error"
        if "assertion" in msg_lower or "assert " in msg_lower:
            return "assertion_failure"
        if "type" in msg_lower and ("error" in msg_lower or "exception" in msg_lower):
            return "type_error"
        if "timeout" in msg_lower or "timed out" in msg_lower:
            return "timeout"
        return "other"

    # ── Internal: code metrics ────────────────────────────────────────────

    def _count_lines_of_code(self) -> int:
        """Count total lines of Python code in the project."""
        total = 0
        for path in self.project_root.rglob("*.py"):
            parts = path.relative_to(self.project_root).parts
            if any(p.startswith(".") or p == "__pycache__" for p in parts):
                continue
            try:
                total += len(path.read_text().splitlines())
            except OSError:
                continue
        return total

    def _get_baseline_loc(self) -> int:
        """Get or establish a baseline LOC count."""
        if self._baseline_loc is None:
            self._baseline_loc = self._count_lines_of_code()
        return self._baseline_loc

    def _estimate_coverage_gap(self) -> float:
        """Estimate coverage gap from source/test function ratio.

        Uses AST to count public functions in source files and test functions
        (starting with test_) in test files, then computes the gap.
        """
        import ast as _ast

        src_dir = self.project_root / "spreader"
        test_dir = self.project_root / "tests"

        if not src_dir.is_dir():
            return 0.0

        # Count public (non-underscore) functions in source files
        source_count = 0
        for f in src_dir.glob("*.py"):
            try:
                content = f.read_text()
            except OSError:
                continue
            source_count += len(self._extract_functions(content))

        # Count test functions (starting with test_) in test files
        tested_count = 0
        if test_dir.is_dir():
            for f in test_dir.glob("test_*.py"):
                try:
                    content = f.read_text()
                except OSError:
                    continue
                try:
                    tree = _ast.parse(content)
                except SyntaxError:
                    continue
                for node in _ast.walk(tree):
                    if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                        if node.name.startswith("test_"):
                            tested_count += 1

        gap = (1.0 - min(1.0, tested_count / max(source_count, 1))) * 100.0
        return gap

    # ── Internal: function extraction ─────────────────────────────────────

    @staticmethod
    def _extract_functions(content: str) -> List[Tuple[str, int]]:
        """Extract function names and their line counts using AST."""
        import ast as _ast
        functions: List[Tuple[str, int]] = []
        try:
            tree = _ast.parse(content)
        except SyntaxError:
            return []
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                if node.name.startswith("_"):
                    continue
                if node.end_lineno is not None:
                    functions.append((node.name, node.end_lineno - node.lineno + 1))
        return functions
