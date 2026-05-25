"""Collective Inference Loop — predict → observe → gap → learn → share.

Runs on real fleet git data (commits across repos). Each cycle:
1. CommitPredictor predicts next commit characteristics from tile history
2. GapDetector compares predictions against actual commits
3. LearningLoop updates the predictor when gaps exceed deadband thresholds
4. CollectiveBroadcaster shares learned tiles via PLATO rooms
5. CollectiveInference orchestrates the full loop
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .pipeline import Tile


# ── Data types ───────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class CommitObservation:
    """An actual commit observed in fleet data."""
    repo: str
    commit_type: str       # feat, fix, refactor, docs, test, chore, etc.
    files_changed: int
    insertions: int
    deletions: int
    author: str = ""
    timestamp: float = 0.0
    message: str = ""
    cross_pollination: bool = False  # did this commit touch multiple repos?

    @property
    def size_bucket(self) -> str:
        """Categorize commit size."""
        total = self.insertions + self.deletions
        if total <= 5:
            return "tiny"
        elif total <= 20:
            return "small"
        elif total <= 100:
            return "medium"
        elif total <= 500:
            return "large"
        return "massive"


@dataclass(frozen=True)
class Prediction:
    """A prediction about the next commit."""
    repo: str
    commit_type: str
    size_bucket: str
    cross_pollination_prob: float  # 0–1
    confidence: float              # 0–1
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GapTile:
    """A tile representing a prediction gap — the prediction was wrong."""
    gap_id: str
    prediction: Prediction
    observation: CommitObservation
    gap_score: float           # 0–1, how wrong the prediction was
    gap_dimensions: Dict[str, float] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass(frozen=True)
class LearningTile:
    """A tile representing a learned update from a gap."""
    learning_id: str
    source_gap_id: str
    update_type: str           # "frequency", "transition", "cross_poll"
    update_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass(frozen=True)
class BroadcastTile:
    """A tile ready for fleet broadcast via PLATO rooms."""
    tile_id: str
    source_agent: str
    learning_tiles: Tuple[LearningTile, ...] = ()
    summary: str = ""
    timestamp: float = 0.0


# ── 1. CommitPredictor ──────────────────────────────────────────────────────

class CommitPredictor:
    """Predicts next commit characteristics from history.

    Starts with simple statistical models (frequency tables, Markov chains),
    escalates to ML when deadband opens.
    """

    def __init__(self) -> None:
        # Frequency tables
        self._repo_freq: Counter[str] = Counter()
        self._type_freq: Counter[str] = Counter()
        self._size_freq: Counter[str] = Counter()
        self._cross_poll_count: int = 0
        self._total_commits: int = 0

        # Transition tables: (repo, type) → next (repo, type) counts
        self._repo_transitions: Counter[Tuple[str, str], int] = Counter()
        self._type_transitions: Counter[Tuple[str, str], int] = Counter()

        # Size transition: prev_size → next_size
        self._size_transitions: Counter[Tuple[str, str], int] = Counter()

        # Last observed state for Markov prediction
        self._last_repo: Optional[str] = None
        self._last_type: Optional[str] = None
        self._last_size: Optional[str] = None

        # Temporal patterns: hour_of_day → type frequency
        self._hour_type_freq: Dict[int, Counter[str]] = defaultdict(Counter)

        # Learning rate tracking
        self._updates_applied: int = 0
        self._prediction_count: int = 0

    def observe(self, commit: CommitObservation) -> None:
        """Ingest a commit observation into the frequency tables."""
        self._total_commits += 1
        size = commit.size_bucket

        # Update frequency tables
        self._repo_freq[commit.repo] += 1
        self._type_freq[commit.commit_type] += 1
        self._size_freq[size] += 1
        if commit.cross_pollination:
            self._cross_poll_count += 1

        # Update transition tables
        if self._last_repo is not None:
            self._repo_transitions[(self._last_repo, commit.repo)] += 1
        if self._last_type is not None:
            self._type_transitions[(self._last_type, commit.commit_type)] += 1
        if self._last_size is not None:
            self._size_transitions[(self._last_size, size)] += 1

        # Temporal patterns
        if commit.timestamp > 0:
            hour = int(time.localtime(commit.timestamp).tm_hour)
            self._hour_type_freq[hour][commit.commit_type] += 1

        # Update last state
        self._last_repo = commit.repo
        self._last_type = commit.commit_type
        self._last_size = size

    def predict(self) -> Prediction:
        """Generate a prediction for the next commit."""
        self._prediction_count += 1
        ts = time.time()

        # Cold start: no data
        if self._total_commits == 0:
            return Prediction(
                repo="unknown",
                commit_type="unknown",
                size_bucket="medium",
                cross_pollination_prob=0.0,
                confidence=0.0,
                timestamp=ts,
                metadata={"cold_start": True},
            )

        # Predict repo: use Markov if available, else frequency
        repo, repo_conf = self._predict_repo()
        ctype, type_conf = self._predict_type()
        size, size_conf = self._predict_size()
        cross_prob = self._predict_cross_pollination()

        # Overall confidence: geometric mean of component confidences
        confidences = [c for c in [repo_conf, type_conf, size_conf] if c > 0]
        overall_conf = (
            (confidences[0] * confidences[1] * confidences[2]) ** (1.0 / 3.0)
            if len(confidences) == 3
            else sum(confidences) / max(len(confidences), 1)
        )

        return Prediction(
            repo=repo,
            commit_type=ctype,
            size_bucket=size,
            cross_pollination_prob=cross_prob,
            confidence=overall_conf,
            timestamp=ts,
            metadata={
                "repo_confidence": repo_conf,
                "type_confidence": type_conf,
                "size_confidence": size_conf,
                "history_size": self._total_commits,
            },
        )

    def apply_learning(self, tile: LearningTile) -> None:
        """Apply a learning update from a gap tile."""
        self._updates_applied += 1
        data = tile.update_data

        if tile.update_type == "frequency":
            # Boost frequency counts for the observed pattern
            repo = data.get("repo", "")
            ctype = data.get("commit_type", "")
            size = data.get("size_bucket", "")
            boost = data.get("boost", 2)

            if repo:
                self._repo_freq[repo] += boost
            if ctype:
                self._type_freq[ctype] += boost
            if size:
                self._size_freq[size] += boost

        elif tile.update_type == "transition":
            prev_repo = data.get("prev_repo", "")
            next_repo = data.get("next_repo", "")
            prev_type = data.get("prev_type", "")
            next_type = data.get("next_type", "")
            boost = data.get("boost", 2)

            if prev_repo and next_repo:
                self._repo_transitions[(prev_repo, next_repo)] += boost
            if prev_type and next_type:
                self._type_transitions[(prev_type, next_type)] += boost

        elif tile.update_type == "cross_poll":
            observed = data.get("observed_cross_poll", False)
            boost = data.get("boost", 2)
            if observed:
                self._cross_poll_count += boost
                self._total_commits += boost  # keep ratio correct

    @property
    def total_commits(self) -> int:
        return self._total_commits

    @property
    def updates_applied(self) -> int:
        return self._updates_applied

    @property
    def prediction_count(self) -> int:
        return self._prediction_count

    # ── Internal prediction methods ──────────────────────────────────────

    def _predict_repo(self) -> Tuple[str, float]:
        """Predict next repo using Markov chain or frequency fallback."""
        if self._last_repo is not None and self._repo_transitions:
            # Markov: what usually follows the last repo?
            candidates: Dict[str, int] = {}
            for (prev, nxt), count in self._repo_transitions.items():
                if prev == self._last_repo:
                    candidates[nxt] = count
            if candidates:
                total = sum(candidates.values())
                best = max(candidates, key=lambda k: candidates[k])
                return best, candidates[best] / total

        # Fallback: most frequent repo
        if self._repo_freq:
            total = sum(self._repo_freq.values())
            best = self._repo_freq.most_common(1)[0][0]
            return best, self._repo_freq[best] / total
        return "unknown", 0.0

    def _predict_type(self) -> Tuple[str, float]:
        """Predict next commit type using Markov chain or frequency fallback."""
        if self._last_type is not None and self._type_transitions:
            candidates: Dict[str, int] = {}
            for (prev, nxt), count in self._type_transitions.items():
                if prev == self._last_type:
                    candidates[nxt] = count
            if candidates:
                total = sum(candidates.values())
                best = max(candidates, key=lambda k: candidates[k])
                return best, candidates[best] / total

        if self._type_freq:
            total = sum(self._type_freq.values())
            best = self._type_freq.most_common(1)[0][0]
            return best, self._type_freq[best] / total
        return "unknown", 0.0

    def _predict_size(self) -> Tuple[str, float]:
        """Predict next commit size using transition or frequency."""
        if self._last_size is not None and self._size_transitions:
            candidates: Dict[str, int] = {}
            for (prev, nxt), count in self._size_transitions.items():
                if prev == self._last_size:
                    candidates[nxt] = count
            if candidates:
                total = sum(candidates.values())
                best = max(candidates, key=lambda k: candidates[k])
                return best, candidates[best] / total

        if self._size_freq:
            total = sum(self._size_freq.values())
            best = self._size_freq.most_common(1)[0][0]
            return best, self._size_freq[best] / total
        return "medium", 0.0

    def _predict_cross_pollination(self) -> float:
        """Predict probability of cross-pollination commit."""
        if self._total_commits == 0:
            return 0.0
        return self._cross_poll_count / self._total_commits


# ── 2. GapDetector ──────────────────────────────────────────────────────────

@dataclass
class GapThresholds:
    """Thresholds for gap detection."""
    repo_mismatch_weight: float = 0.4     # wrong repo → big gap
    type_mismatch_weight: float = 0.3     # wrong type → medium gap
    size_mismatch_weight: float = 0.2     # wrong size → small gap
    cross_poll_weight: float = 0.1        # cross-poll mismatch → tiny gap
    deadband_threshold: float = 0.3       # gap > this → learning tile


class GapDetector:
    """Compares predictions against actual commits. Computes prediction gap.

    When gap exceeds deadband threshold, creates a learning tile.
    """

    def __init__(self, thresholds: Optional[GapThresholds] = None) -> None:
        self._thresholds = thresholds or GapThresholds()
        self._gap_history: List[float] = []
        self._gaps_created: int = 0

    def detect(
        self,
        prediction: Prediction,
        observation: CommitObservation,
    ) -> Optional[GapTile]:
        """Compare prediction vs observation. Return GapTile if gap exceeds threshold."""
        gap_score, dimensions = self._compute_gap(prediction, observation)
        self._gap_history.append(gap_score)

        if gap_score > self._thresholds.deadband_threshold:
            self._gaps_created += 1
            return GapTile(
                gap_id=f"gap-{self._gaps_created}-{int(time.time())}",
                prediction=prediction,
                observation=observation,
                gap_score=gap_score,
                gap_dimensions=dimensions,
                timestamp=time.time(),
            )
        return None

    def force_detect(
        self,
        prediction: Prediction,
        observation: CommitObservation,
    ) -> Tuple[GapTile, float]:
        """Always compute and return a gap tile, regardless of threshold."""
        gap_score, dimensions = self._compute_gap(prediction, observation)
        self._gap_history.append(gap_score)
        self._gaps_created += 1

        tile = GapTile(
            gap_id=f"gap-{self._gaps_created}-{int(time.time())}",
            prediction=prediction,
            observation=observation,
            gap_score=gap_score,
            gap_dimensions=dimensions,
            timestamp=time.time(),
        )
        return tile, gap_score

    @property
    def average_gap(self) -> float:
        """Running average gap score."""
        if not self._gap_history:
            return 0.0
        return sum(self._gap_history) / len(self._gap_history)

    @property
    def gap_count(self) -> int:
        return len(self._gap_history)

    @property
    def gaps_above_threshold(self) -> int:
        return sum(1 for g in self._gap_history if g > self._thresholds.deadband_threshold)

    @property
    def thresholds(self) -> GapThresholds:
        return self._thresholds

    # ── Internal ─────────────────────────────────────────────────────────

    def _compute_gap(
        self,
        pred: Prediction,
        obs: CommitObservation,
    ) -> Tuple[float, Dict[str, float]]:
        """Compute multi-dimensional gap score."""
        dims: Dict[str, float] = {}
        t = self._thresholds

        # Repo mismatch
        repo_gap = 0.0 if pred.repo == obs.repo else 1.0
        dims["repo"] = repo_gap

        # Type mismatch
        type_gap = 0.0 if pred.commit_type == obs.commit_type else 1.0
        dims["type"] = type_gap

        # Size mismatch
        size_gap = 0.0 if pred.size_bucket == obs.size_bucket else 1.0
        dims["size"] = size_gap

        # Cross-pollination mismatch (continuous)
        obs_cross = 1.0 if obs.cross_pollination else 0.0
        cross_gap = abs(pred.cross_pollination_prob - obs_cross)
        dims["cross_poll"] = cross_gap

        # Weighted sum
        total_gap = (
            repo_gap * t.repo_mismatch_weight
            + type_gap * t.type_mismatch_weight
            + size_gap * t.size_mismatch_weight
            + cross_gap * t.cross_poll_weight
        )

        return round(total_gap, 4), dims


# ── 3. LearningLoop ─────────────────────────────────────────────────────────

class LearningLoop:
    """Takes gap tiles and updates the predictor.

    Implements the predict→observe→gap→learn cycle.
    Tracks learning rate over time.
    """

    def __init__(self, predictor: CommitPredictor, learning_rate: float = 1.0) -> None:
        self._predictor = predictor
        self._learning_rate = learning_rate  # multiplier for boost amounts
        self._learning_tiles: List[LearningTile] = []
        self._gap_tiles_processed: int = 0
        self._learning_history: List[Dict[str, Any]] = []

    def learn(self, gap: GapTile) -> LearningTile:
        """Process a gap tile and produce learning updates."""
        self._gap_tiles_processed += 1
        obs = gap.observation
        pred = gap.prediction

        # Determine what type of learning to apply
        tiles: List[LearningTile] = []

        # 1. Frequency update: boost the observed pattern
        freq_tile = LearningTile(
            learning_id=f"learn-freq-{self._gap_tiles_processed}",
            source_gap_id=gap.gap_id,
            update_type="frequency",
            update_data={
                "repo": obs.repo,
                "commit_type": obs.commit_type,
                "size_bucket": obs.size_bucket,
                "boost": max(1, int(2 * self._learning_rate)),
            },
            timestamp=time.time(),
        )
        tiles.append(freq_tile)
        self._predictor.apply_learning(freq_tile)

        # 2. Transition update: if previous state was known
        if gap.prediction.metadata.get("history_size", 0) > 1:
            trans_tile = LearningTile(
                learning_id=f"learn-trans-{self._gap_tiles_processed}",
                source_gap_id=gap.gap_id,
                update_type="transition",
                update_data={
                    "prev_repo": pred.repo,       # what we predicted
                    "next_repo": obs.repo,         # what actually happened
                    "prev_type": pred.commit_type,
                    "next_type": obs.commit_type,
                    "boost": max(1, int(2 * self._learning_rate)),
                },
                timestamp=time.time(),
            )
            tiles.append(trans_tile)
            self._predictor.apply_learning(trans_tile)

        # 3. Cross-pollination update
        if obs.cross_pollination:
            cross_tile = LearningTile(
                learning_id=f"learn-cross-{self._gap_tiles_processed}",
                source_gap_id=gap.gap_id,
                update_type="cross_poll",
                update_data={
                    "observed_cross_poll": True,
                    "boost": max(1, int(3 * self._learning_rate)),
                },
                timestamp=time.time(),
            )
            tiles.append(cross_tile)
            self._predictor.apply_learning(cross_tile)

        # Record learning event
        entry = {
            "gap_score": gap.gap_score,
            "gap_dimensions": dict(gap.gap_dimensions),
            "tiles_created": len(tiles),
            "timestamp": time.time(),
        }
        self._learning_history.append(entry)
        self._learning_tiles.extend(tiles)

        # Return the primary learning tile
        return tiles[0]

    def learn_all(self, gaps: Sequence[GapTile]) -> List[LearningTile]:
        """Process multiple gap tiles."""
        return [self.learn(gap) for gap in gaps]

    @property
    def predictor(self) -> CommitPredictor:
        return self._predictor

    @property
    def learning_tiles(self) -> List[LearningTile]:
        return list(self._learning_tiles)

    @property
    def gaps_processed(self) -> int:
        return self._gap_tiles_processed

    @property
    def learning_rate(self) -> float:
        return self._learning_rate

    @learning_rate.setter
    def learning_rate(self, rate: float) -> None:
        self._learning_rate = max(0.1, min(rate, 5.0))

    def learning_rate_over_time(self) -> List[Dict[str, Any]]:
        """Return learning history with computed rates."""
        if not self._learning_history:
            return []

        rates: List[Dict[str, Any]] = []
        cumulative_gap = 0.0
        for i, entry in enumerate(self._learning_history):
            cumulative_gap += entry["gap_score"]
            avg_gap = cumulative_gap / (i + 1)
            rates.append({
                "step": i + 1,
                "gap_score": entry["gap_score"],
                "avg_gap": round(avg_gap, 4),
                "tiles_created": entry["tiles_created"],
            })
        return rates


# ── 4. CollectiveBroadcaster ────────────────────────────────────────────────

class CollectiveBroadcaster:
    """Shares learned tiles with fleet via PLATO rooms."""

    def __init__(self, agent_name: str = "forgemaster") -> None:
        self._agent_name = agent_name
        self._broadcast_history: List[BroadcastTile] = []
        self._plato_buffer: List[BroadcastTile] = []  # simulates PLATO room storage

    def broadcast(self, learning_tiles: Sequence[LearningTile]) -> BroadcastTile:
        """Package learning tiles into a broadcast tile for PLATO."""
        broadcast = BroadcastTile(
            tile_id=f"broadcast-{len(self._broadcast_history) + 1}",
            source_agent=self._agent_name,
            learning_tiles=tuple(learning_tiles),
            summary=self._summarize(learning_tiles),
            timestamp=time.time(),
        )
        self._broadcast_history.append(broadcast)
        self._plato_buffer.append(broadcast)
        return broadcast

    def read_plato(self) -> List[BroadcastTile]:
        """Read all tiles from the PLATO room buffer."""
        return list(self._plato_buffer)

    def clear_plato(self) -> int:
        """Clear the PLATO buffer (simulates consumption). Returns count cleared."""
        count = len(self._plato_buffer)
        self._plato_buffer.clear()
        return count

    @property
    def broadcast_count(self) -> int:
        return len(self._broadcast_history)

    @property
    def agent_name(self) -> str:
        return self._agent_name

    @staticmethod
    def _summarize(tiles: Sequence[LearningTile]) -> str:
        """Create a human-readable summary of learning tiles."""
        if not tiles:
            return "empty broadcast"

        types = Counter(t.update_type for t in tiles)
        parts = [f"{count} {utype}" for utype, count in types.most_common()]
        return f"learned: {', '.join(parts)}"

    @property
    def total_learning_tiles_sent(self) -> int:
        return sum(len(b.learning_tiles) for b in self._broadcast_history)


# ── 5. CollectiveInference ───────────────────────────────────────────────────

@dataclass
class CollectiveConfig:
    """Configuration for the collective inference loop."""
    cycle_interval: float = 1.0            # seconds between cycles
    deadband_threshold: float = 0.3        # gap threshold for learning
    learning_rate: float = 1.0             # learning rate multiplier
    broadcast_every: int = 1               # broadcast after every N gaps
    max_cycles: int = 1000                  # safety limit
    agent_name: str = "forgemaster"


@dataclass
class CycleResult:
    """Result from one cycle of the collective inference loop."""
    cycle: int
    prediction: Prediction
    observation: CommitObservation
    gap_score: float
    gap_tile: Optional[GapTile]          # None if below threshold
    learning_tiles: List[LearningTile]    # empty if no gap
    broadcast: Optional[BroadcastTile]    # None if not broadcasting this cycle
    avg_gap: float                        # running average gap


class CollectiveInference:
    """Main orchestrator for the collective inference loop.

    Runs the full predict→observe→gap→learn→share cycle on fleet commit data.
    """

    def __init__(self, config: Optional[CollectiveConfig] = None) -> None:
        self._config = config or CollectiveConfig()

        # Components
        self._predictor = CommitPredictor()
        self._gap_detector = GapDetector(GapThresholds(
            deadband_threshold=self._config.deadband_threshold,
        ))
        self._learner = LearningLoop(
            self._predictor,
            learning_rate=self._config.learning_rate,
        )
        self._broadcaster = CollectiveBroadcaster(
            agent_name=self._config.agent_name,
        )

        # State
        self._cycle_count: int = 0
        self._pending_gaps: List[GapTile] = []
        self._cycle_results: List[CycleResult] = []

    def prime(self, commits: Sequence[CommitObservation]) -> int:
        """Prime the predictor with historical commits (no learning)."""
        for commit in commits:
            self._predictor.observe(commit)
        return len(commits)

    def run_cycle(self, observation: CommitObservation) -> CycleResult:
        """Run one predict→observe→gap→learn→share cycle."""
        self._cycle_count += 1

        # Step 1: PREDICT
        prediction = self._predictor.predict()

        # Step 2: OBSERVE — the observation is given to us

        # Step 3: GAP — compare prediction vs observation
        gap_tile = self._gap_detector.detect(prediction, observation)
        gap_score = 0.0
        learning_tiles: List[LearningTile] = []
        broadcast: Optional[BroadcastTile] = None

        if gap_tile is not None:
            gap_score = gap_tile.gap_score

            # Step 4: LEARN — update predictor from gap
            learning_tiles = [self._learner.learn(gap_tile)]
            self._pending_gaps.append(gap_tile)

            # Step 5: SHARE — broadcast if enough pending gaps
            if len(self._pending_gaps) >= self._config.broadcast_every:
                broadcast = self._broadcaster.broadcast(learning_tiles)
                self._pending_gaps.clear()
        else:
            # No significant gap — still compute score for tracking
            _, forced_score = self._gap_detector.force_detect(prediction, observation)
            gap_score = forced_score

        # Ingest the observation for future predictions
        self._predictor.observe(observation)

        result = CycleResult(
            cycle=self._cycle_count,
            prediction=prediction,
            observation=observation,
            gap_score=gap_score,
            gap_tile=gap_tile,
            learning_tiles=learning_tiles,
            broadcast=broadcast,
            avg_gap=self._gap_detector.average_gap,
        )
        self._cycle_results.append(result)
        return result

    def run_cycles(
        self,
        observations: Sequence[CommitObservation],
    ) -> List[CycleResult]:
        """Run multiple cycles over a sequence of observations."""
        return [self.run_cycle(obs) for obs in observations]

    @property
    def predictor(self) -> CommitPredictor:
        return self._predictor

    @property
    def gap_detector(self) -> GapDetector:
        return self._gap_detector

    @property
    def learner(self) -> LearningLoop:
        return self._learner

    @property
    def broadcaster(self) -> CollectiveBroadcaster:
        return self._broadcaster

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def cycle_results(self) -> List[CycleResult]:
        return list(self._cycle_results)

    @property
    def config(self) -> CollectiveConfig:
        return self._config

    def summary(self) -> Dict[str, Any]:
        """Return a summary of the collective inference state."""
        return {
            "cycles_run": self._cycle_count,
            "total_commits_observed": self._predictor.total_commits,
            "total_predictions": self._predictor.prediction_count,
            "total_gaps_detected": self._gap_detector.gap_count,
            "gaps_above_threshold": self._gap_detector.gaps_above_threshold,
            "average_gap": round(self._gap_detector.average_gap, 4),
            "learning_tiles_created": len(self._learner.learning_tiles),
            "learning_updates_applied": self._predictor.updates_applied,
            "broadcasts_sent": self._broadcaster.broadcast_count,
            "total_learning_tiles_broadcast": self._broadcaster.total_learning_tiles_sent,
        }
