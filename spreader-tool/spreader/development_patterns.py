"""Development pattern library — seeds locked from successful development cycles.

Stores proven code patterns discovered while building the spreader-tool.
Each pattern captures a reusable approach with context on when to apply it,
a code template, and historical success rate.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from uuid import uuid4


@dataclass
class DevelopmentPattern:
    """A proven development pattern locked from successful cycles."""

    pattern_id: str
    name: str
    description: str
    applies_when: str        # condition description
    code_template: str       # code snippet showing the pattern
    success_rate: float      # 0.0–1.0 historical success rate
    locked: bool
    discovered_at: Optional[float] = None
    use_count: int = 0
    tags: List[str] = field(default_factory=list)

    def record_use(self, success: bool) -> None:
        """Record a usage outcome, updating success rate."""
        total = self.use_count + 1
        successes = int(self.success_rate * self.use_count) + (1 if success else 0)
        self.use_count = total
        self.success_rate = successes / total


class PatternLibrary:
    """Seeds locked from successful development cycles.

    The pattern library stores reusable development patterns discovered
    during self-optimization cycles. Patterns can be queried by context
    and locked once proven.
    """

    def __init__(self, persist_path: Optional[str] = None) -> None:
        self._patterns: Dict[str, DevelopmentPattern] = {}
        self._persist_path = persist_path
        if persist_path and os.path.exists(persist_path):
            self._load(persist_path)

    # ── CRUD ──────────────────────────────────────────────────────────────

    def register(self, pattern: DevelopmentPattern) -> str:
        """Register a new pattern. Returns pattern_id."""
        if not pattern.pattern_id:
            pattern.pattern_id = str(uuid4())
        if pattern.discovered_at is None:
            pattern.discovered_at = time.time()
        self._patterns[pattern.pattern_id] = pattern
        self._maybe_persist()
        return pattern.pattern_id

    def get(self, pattern_id: str) -> Optional[DevelopmentPattern]:
        """Look up a pattern by ID."""
        return self._patterns.get(pattern_id)

    def list_all(self) -> List[DevelopmentPattern]:
        """Return all patterns."""
        return list(self._patterns.values())

    def list_locked(self) -> List[DevelopmentPattern]:
        """Return only locked (proven) patterns."""
        return [p for p in self._patterns.values() if p.locked]

    # ── Query ─────────────────────────────────────────────────────────────

    def find_for_context(self, context: str) -> List[DevelopmentPattern]:
        """Find patterns applicable to the given context string.

        Searches name, description, applies_when, and tags for keyword
        matches. Returns results sorted by success_rate descending.
        """
        context_lower = context.lower()
        keywords = set(context_lower.split())

        scored: List[tuple] = []
        for p in self._patterns.values():
            score = 0
            blob = f"{p.name} {p.description} {p.applies_when} {' '.join(p.tags)}".lower()
            for kw in keywords:
                if kw in blob:
                    score += 1
            if score > 0:
                scored.append((score * p.success_rate, p))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [p for _, p in scored]

    # ── Lock / Unlock ─────────────────────────────────────────────────────

    def lock_pattern(self, pattern_id: str) -> DevelopmentPattern:
        """Lock a pattern — mark it as proven and immutable."""
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            raise KeyError(f"Pattern {pattern_id} not found")
        pattern.locked = True
        self._maybe_persist()
        return pattern

    def unlock_pattern(self, pattern_id: str) -> DevelopmentPattern:
        """Unlock a pattern for revision."""
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            raise KeyError(f"Pattern {pattern_id} not found")
        pattern.locked = False
        self._maybe_persist()
        return pattern

    # ── Persistence ───────────────────────────────────────────────────────

    def _maybe_persist(self) -> None:
        if self._persist_path:
            self._save(self._persist_path)

    def _save(self, path: str) -> None:
        data = {
            pid: {
                "pattern_id": p.pattern_id,
                "name": p.name,
                "description": p.description,
                "applies_when": p.applies_when,
                "code_template": p.code_template,
                "success_rate": p.success_rate,
                "locked": p.locked,
                "discovered_at": p.discovered_at,
                "use_count": p.use_count,
                "tags": p.tags,
            }
            for pid, p in self._patterns.items()
        }
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _load(self, path: str) -> None:
        with open(path) as f:
            data = json.load(f)
        for pid, raw in data.items():
            self._patterns[pid] = DevelopmentPattern(**raw)

    # ── Defaults ──────────────────────────────────────────────────────────

    def load_defaults(self) -> None:
        """Pre-load patterns discovered during spreader-tool MVP development."""

        defaults = [
            DevelopmentPattern(
                pattern_id="frozen_dataclass_with_transition",
                name="Frozen Dataclass with Transition Guard",
                description=(
                    "Use frozen=True dataclass for immutable state objects. "
                    "Add a _transition_guard int field bumped on every copy-on-write "
                    "transition. Validate transitions via a lookup table."
                ),
                applies_when="Building state machines with lifecycle transitions",
                code_template=(
                    "@dataclass(frozen=True)\n"
                    "class State:\n"
                    "    id: str\n"
                    "    status: Status\n"
                    "    _transition_guard: int = 0\n"
                    "\n"
                    "    def can_transition_to(self, new):\n"
                    "        return new in _TRANSITIONS.get(self.status, set())\n"
                    "\n"
                    "    def transition_to(self, new):\n"
                    "        if not self.can_transition_to(new):\n"
                    "            raise ValueError(f'Invalid: {self.status} -> {new}')\n"
                    "        return dataclasses.replace(self, status=new,\n"
                    "                                    _transition_guard=self._transition_guard+1)"
                ),
                success_rate=1.0,
                locked=True,
                tags=["state-machine", "immutable", "dataclass", "lifecycle"],
            ),
            DevelopmentPattern(
                pattern_id="hysteresis_guard",
                name="Hysteresis Guard for State Flickering",
                description=(
                    "Prevent rapid state flickering by requiring exit thresholds "
                    "to be relaxed by a hysteresis factor (e.g., 1.1x). Entry "
                    "triggers on breach, exit only on recovery past the relaxed threshold."
                ),
                applies_when="Detecting threshold breaches with sustained duration checks",
                code_template=(
                    "if currently_in and not new_breach:\n"
                    "    # Hysteresis: must recover PAST threshold\n"
                    "    new_in = not all_recovered(metrics)\n"
                    "\n"
                    "def all_recovered(self, metrics):\n"
                    "    factor = self._config.hysteresis_exit_factor\n"
                    "    return (\n"
                    "        metrics.value >= threshold * factor\n"
                    "    )"
                ),
                success_rate=1.0,
                locked=True,
                tags=["hysteresis", "deadband", "threshold", "stability"],
            ),
            DevelopmentPattern(
                pattern_id="content_addressed_dedup",
                name="Content-Addressed Deduplication",
                description=(
                    "Hash (room_id, room_type, kpi_snapshot, trigger) to produce "
                    "a deterministic content key. Store in an index mapping hash → "
                    "set of IDs. Detect duplicates before storing."
                ),
                applies_when="Storing snapshots that may be duplicates",
                code_template=(
                    "def _content_hash(self, obj) -> str:\n"
                    "    blob = json.dumps(obj, sort_keys=True)\n"
                    "    return hashlib.sha256(blob.encode()).hexdigest()\n"
                    "\n"
                    "# Index: content_hash -> {id1, id2, ...}\n"
                    "self._content_index: Dict[str, Set[str]] = {}"
                ),
                success_rate=1.0,
                locked=True,
                tags=["dedup", "hash", "content-addressed", "storage"],
            ),
            DevelopmentPattern(
                pattern_id="in_memory_store_adapter",
                name="In-Memory Store Adapter (Duck-Typed)",
                description=(
                    "Provide a dict-backed store that duck-types as the real "
                    "store interface (put/get/query). Used for testing without "
                    "filesystem or database dependencies."
                ),
                applies_when="Testing components that depend on a store interface",
                code_template=(
                    "class _InMemoryStore:\n"
                    "    def __init__(self):\n"
                    "        self._data: Dict[str, Any] = {}\n"
                    "\n"
                    "    def put(self, obj) -> None:\n"
                    "        self._data[obj.id] = obj\n"
                    "\n"
                    "    def get(self, id: str) -> Optional[Any]:\n"
                    "        return self._data.get(id)\n"
                    "\n"
                    "    def query(self, **filters) -> List[Any]:\n"
                    "        return [o for o in self._data.values()\n"
                    "                if all(getattr(o, k) == v for k, v in filters.items())]"
                ),
                success_rate=1.0,
                locked=True,
                tags=["testing", "store", "duck-typing", "adapter"],
            ),
            DevelopmentPattern(
                pattern_id="kpi_space_distance",
                name="Euclidean KPI Space Distance",
                description=(
                    "Compare two KPI snapshots using Euclidean distance across "
                    "normalized dimensions. Used for similarity scoring and "
                    "redaction decisions."
                ),
                applies_when="Comparing metric snapshots for similarity or drift",
                code_template=(
                    "def kpi_distance(a: KPIMetrics, b: KPIMetrics) -> float:\n"
                    "    dims = [\n"
                    "        (a.task_completion_rate - b.task_completion_rate),\n"
                    "        (a.avg_wait_time - b.avg_wait_time),\n"
                    "        (a.energy_over_baseline - b.energy_over_baseline),\n"
                    "        (a.inference_mae - b.inference_mae),\n"
                    "    ]\n"
                    "    return math.sqrt(sum(d * d for d in dims))"
                ),
                success_rate=1.0,
                locked=True,
                tags=["distance", "metrics", "comparison", "euclidean"],
            ),
            DevelopmentPattern(
                pattern_id="episode_boundary_tracking",
                name="Episode Boundary Tracking",
                description=(
                    "Create an FCW exactly once when entering deadband (not on every "
                    "tick while in deadband). Track episode state with _was_in_deadband "
                    "flag. Reset episode state when exiting deadband."
                ),
                applies_when="Tracking event boundaries in stateful loops",
                code_template=(
                    "if db_state.in_deadband and not self._was_in_deadband:\n"
                    "    # Just entered deadband — create FCW\n"
                    "    fcw = self._fcw_mgr.create(...)\n"
                    "\n"
                    "if not db_state.in_deadband and self._was_in_deadband:\n"
                    "    # Just exited deadband — reset episode\n"
                    "    self._current_episode_fcw_ids.clear()\n"
                    "\n"
                    "self._was_in_deadband = db_state.in_deadband"
                ),
                success_rate=1.0,
                locked=True,
                tags=["boundary", "episode", "deadband", "state-tracking"],
            ),
            DevelopmentPattern(
                pattern_id="cleanup_bug_pattern",
                name="Cleanup Bug: Don't Delete Tracking State Before Duration Check",
                description=(
                    "When a metric recovers, don't immediately clear breach_start. "
                    "The breach tracking state must survive the recovery check because "
                    "the duration check needs it. Only clear after the hysteresis "
                    "exit is confirmed."
                ),
                applies_when="Fixing threshold tracking bugs where state is cleaned up too early",
                code_template=(
                    "# WRONG: clears state before hysteresis check\n"
                    "# self._breach_start.pop(metric, None)  # too early!\n"
                    "\n"
                    "# RIGHT: only clear in _check_threshold_metric\n"
                    "# when the metric is NOT breached\n"
                    "if not is_breached:\n"
                    "    self._breach_start.pop(metric, None)"
                ),
                success_rate=1.0,
                locked=True,
                tags=["bug", "cleanup", "tracking", "hysteresis", "ordering"],
            ),
        ]

        for p in defaults:
            if p.pattern_id not in self._patterns:
                self._patterns[p.pattern_id] = p
        self._maybe_persist()
