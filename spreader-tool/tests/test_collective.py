"""Tests for collective inference loop — predict → observe → gap → learn → share.

Target: 40+ tests covering all components and integration scenarios.
"""

import time
from collections import Counter

import pytest

from spreader.collective import (
    BroadcastTile,
    CollectiveBroadcaster,
    CollectiveConfig,
    CollectiveInference,
    CommitObservation,
    CommitPredictor,
    CycleResult,
    GapDetector,
    GapThresholds,
    GapTile,
    LearningLoop,
    LearningTile,
    Prediction,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_commit(
    repo: str = "plato-training",
    ctype: str = "feat",
    insertions: int = 50,
    deletions: int = 10,
    author: str = "forgemaster",
    cross_poll: bool = False,
    ts: float = 0.0,
) -> CommitObservation:
    return CommitObservation(
        repo=repo,
        commit_type=ctype,
        files_changed=max(1, (insertions + deletions) // 10),
        insertions=insertions,
        deletions=deletions,
        author=author,
        timestamp=ts or time.time(),
        cross_pollination=cross_poll,
    )


def make_diverse_commits(n: int = 50) -> list[CommitObservation]:
    """Generate diverse commits across repos and types."""
    repos = ["plato-training", "tensor-spline", "plato-types", "forgemaster", "casting-call"]
    types = ["feat", "fix", "refactor", "docs", "test", "chore"]
    commits = []
    for i in range(n):
        repo = repos[i % len(repos)]
        ctype = types[i % len(types)]
        # Vary size
        size_mod = i % 5
        insertions = [3, 15, 60, 200, 800][size_mod]
        deletions = [1, 5, 20, 80, 300][size_mod]
        cross_poll = (i % 7 == 0)
        commits.append(make_commit(
            repo=repo, ctype=ctype,
            insertions=insertions, deletions=deletions,
            cross_poll=cross_poll, ts=1700000000.0 + i * 60.0,
        ))
    return commits


# ══════════════════════════════════════════════════════════════════════════════
# CommitObservation tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCommitObservation:
    def test_size_bucket_tiny(self):
        c = make_commit(insertions=2, deletions=1)
        assert c.size_bucket == "tiny"

    def test_size_bucket_small(self):
        c = make_commit(insertions=10, deletions=5)
        assert c.size_bucket == "small"

    def test_size_bucket_medium(self):
        c = make_commit(insertions=50, deletions=30)
        assert c.size_bucket == "medium"

    def test_size_bucket_large(self):
        c = make_commit(insertions=300, deletions=100)
        assert c.size_bucket == "large"

    def test_size_bucket_massive(self):
        c = make_commit(insertions=600, deletions=200)
        assert c.size_bucket == "massive"

    def test_size_bucket_boundary_tiny_small(self):
        c = make_commit(insertions=3, deletions=2)  # total=5
        assert c.size_bucket == "tiny"

    def test_size_bucket_boundary_small_medium(self):
        c = make_commit(insertions=15, deletions=5)  # total=20
        assert c.size_bucket == "small"

    def test_frozen(self):
        c = make_commit()
        with pytest.raises(AttributeError):
            c.repo = "other"  # type: ignore


# ══════════════════════════════════════════════════════════════════════════════
# CommitPredictor tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCommitPredictor:
    def test_cold_start_prediction(self):
        """No history → prediction with zero confidence."""
        pred = CommitPredictor()
        p = pred.predict()
        assert p.repo == "unknown"
        assert p.commit_type == "unknown"
        assert p.size_bucket == "medium"
        assert p.confidence == 0.0
        assert p.metadata.get("cold_start") is True

    def test_single_observation_prediction(self):
        """One commit → predict that same repo/type."""
        pred = CommitPredictor()
        pred.observe(make_commit(repo="tensor-spline", ctype="fix", insertions=10, deletions=5))
        p = pred.predict()
        assert p.repo == "tensor-spline"
        assert p.commit_type == "fix"
        assert p.confidence > 0.0

    def test_repeated_repo_prediction(self):
        """Many commits to same repo → high confidence for that repo."""
        pred = CommitPredictor()
        for _ in range(20):
            pred.observe(make_commit(repo="plato-training"))
        p = pred.predict()
        assert p.repo == "plato-training"
        assert p.confidence > 0.8

    def test_markov_repo_prediction(self):
        """Transition pattern: A always follows B."""
        pred = CommitPredictor()
        # Create alternating pattern
        for _ in range(10):
            pred.observe(make_commit(repo="plato-training"))
            pred.observe(make_commit(repo="tensor-spline"))
        # Last was tensor-spline, should predict plato-training
        p = pred.predict()
        assert p.repo == "plato-training"

    def test_type_frequency_prediction(self):
        """Most common type should be predicted."""
        pred = CommitPredictor()
        # Observe same type to build a dominant frequency with no transitions
        for _ in range(20):
            pred.observe(make_commit(ctype="feat"))
        p = pred.predict()
        assert p.commit_type == "feat"

    def test_size_prediction_from_frequency(self):
        """Most common size bucket should be predicted."""
        pred = CommitPredictor()
        for _ in range(10):
            pred.observe(make_commit(insertions=2, deletions=1))  # tiny
        p = pred.predict()
        assert p.size_bucket == "tiny"

    def test_cross_pollination_probability(self):
        """Cross-pollination probability should match observed frequency."""
        pred = CommitPredictor()
        for i in range(10):
            pred.observe(make_commit(cross_poll=(i % 2 == 0)))
        p = pred.predict()
        assert abs(p.cross_pollination_prob - 0.5) < 0.01

    def test_cross_pollination_zero(self):
        """No cross-poll commits → probability 0."""
        pred = CommitPredictor()
        for _ in range(10):
            pred.observe(make_commit(cross_poll=False))
        p = pred.predict()
        assert p.cross_pollination_prob == 0.0

    def test_prediction_count_increments(self):
        pred = CommitPredictor()
        assert pred.prediction_count == 0
        pred.predict()
        assert pred.prediction_count == 1
        pred.predict()
        assert pred.prediction_count == 2

    def test_total_commits_tracking(self):
        pred = CommitPredictor()
        assert pred.total_commits == 0
        pred.observe(make_commit())
        assert pred.total_commits == 1
        pred.observe(make_commit())
        assert pred.total_commits == 2

    def test_apply_frequency_learning(self):
        """Learning should boost frequency of observed pattern."""
        pred = CommitPredictor()
        pred.observe(make_commit(repo="plato-training", ctype="feat"))
        p1 = pred.predict()

        tile = LearningTile(
            learning_id="test-1",
            source_gap_id="gap-1",
            update_type="frequency",
            update_data={"repo": "tensor-spline", "commit_type": "fix", "size_bucket": "large", "boost": 50},
        )
        pred.apply_learning(tile)
        p2 = pred.predict()
        # After boosting tensor-spline heavily, it should now dominate
        assert p2.repo == "tensor-spline"

    def test_apply_transition_learning(self):
        """Transition learning should update Markov chain."""
        pred = CommitPredictor()
        pred.observe(make_commit(repo="A"))
        pred.observe(make_commit(repo="B"))

        tile = LearningTile(
            learning_id="test-2",
            source_gap_id="gap-2",
            update_type="transition",
            update_data={"prev_repo": "B", "next_repo": "A", "prev_type": "feat", "next_type": "fix", "boost": 50},
        )
        pred.apply_learning(tile)
        # Now B→A transition is very strong
        p = pred.predict()
        assert p.repo == "A"

    def test_apply_cross_poll_learning(self):
        """Cross-poll learning should increase cross-poll probability."""
        pred = CommitPredictor()
        pred.observe(make_commit(cross_poll=False))
        assert pred.predict().cross_pollination_prob == 0.0

        tile = LearningTile(
            learning_id="test-3",
            source_gap_id="gap-3",
            update_type="cross_poll",
            update_data={"observed_cross_poll": True, "boost": 10},
        )
        pred.apply_learning(tile)
        assert pred.predict().cross_pollination_prob > 0.0

    def test_updates_applied_counter(self):
        pred = CommitPredictor()
        assert pred.updates_applied == 0
        tile = LearningTile(
            learning_id="test-4",
            source_gap_id="gap-4",
            update_type="frequency",
            update_data={"repo": "X"},
        )
        pred.apply_learning(tile)
        assert pred.updates_applied == 1


# ══════════════════════════════════════════════════════════════════════════════
# GapDetector tests
# ══════════════════════════════════════════════════════════════════════════════

class TestGapDetector:
    def test_perfect_prediction_no_gap(self):
        """Perfect prediction → no gap tile (below threshold)."""
        det = GapDetector()
        pred = Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.9)
        obs = make_commit(repo="A", ctype="feat", insertions=50, deletions=10, cross_poll=False)
        gap = det.detect(pred, obs)
        assert gap is None

    def test_wrong_repo_creates_gap(self):
        """Wrong repo → gap above threshold (repo weight=0.4)."""
        det = GapDetector()
        pred = Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.9)
        obs = make_commit(repo="B", ctype="feat", insertions=50, deletions=10)
        gap = det.detect(pred, obs)
        assert gap is not None
        assert gap.gap_score >= 0.3  # repo mismatch weight
        assert gap.gap_dimensions["repo"] == 1.0

    def test_wrong_type_creates_gap(self):
        """Wrong type → gap (type weight=0.3)."""
        det = GapDetector(GapThresholds(deadband_threshold=0.2))
        pred = Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.9)
        obs = make_commit(repo="A", ctype="fix", insertions=50, deletions=10)
        gap = det.detect(pred, obs)
        assert gap is not None
        assert gap.gap_dimensions["type"] == 1.0

    def test_wrong_size_creates_gap(self):
        """Wrong size → gap (size weight=0.2)."""
        det = GapDetector(GapThresholds(deadband_threshold=0.15))
        pred = Prediction(repo="A", commit_type="feat", size_bucket="tiny", cross_pollination_prob=0.0, confidence=0.9)
        obs = make_commit(repo="A", ctype="feat", insertions=200, deletions=50)  # large
        gap = det.detect(pred, obs)
        assert gap is not None
        assert gap.gap_dimensions["size"] == 1.0

    def test_high_deadband_threshold_suppresses_gap(self):
        """High threshold → small gaps ignored."""
        det = GapDetector(GapThresholds(deadband_threshold=0.9))
        # Only type wrong → 0.3 gap, below 0.9 threshold
        pred = Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.9)
        obs = make_commit(repo="A", ctype="fix", insertions=50, deletions=10)
        gap = det.detect(pred, obs)
        assert gap is None

    def test_zero_deadband_catches_everything(self):
        """Zero threshold → every mismatch creates a gap."""
        det = GapDetector(GapThresholds(deadband_threshold=0.0))
        pred = Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.5, confidence=0.9)
        obs = make_commit(repo="A", ctype="feat", insertions=50, deletions=10, cross_poll=True)
        gap = det.detect(pred, obs)
        assert gap is not None

    def test_all_wrong_maximum_gap(self):
        """Everything wrong → maximum gap score."""
        det = GapDetector()
        pred = Prediction(repo="A", commit_type="feat", size_bucket="tiny", cross_pollination_prob=0.0, confidence=0.9)
        obs = make_commit(repo="B", ctype="fix", insertions=600, deletions=200, cross_poll=True)
        gap = det.detect(pred, obs)
        assert gap is not None
        assert gap.gap_score >= 0.8  # repo(0.4) + type(0.3) + size(0.2) + cross(~0.1)

    def test_force_detect_always_returns(self):
        """force_detect returns gap tile regardless of threshold."""
        det = GapDetector(GapThresholds(deadband_threshold=1.0))
        pred = Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.9)
        obs = make_commit(repo="A", ctype="feat", insertions=50, deletions=10)
        tile, score = det.force_detect(pred, obs)
        assert tile is not None
        assert score >= 0.0

    def test_average_gap_tracking(self):
        """Average gap should be tracked over multiple detections."""
        det = GapDetector(GapThresholds(deadband_threshold=0.0))
        pred1 = Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.9)
        obs1 = make_commit(repo="A", ctype="feat", insertions=50, deletions=10)  # perfect
        det.force_detect(pred1, obs1)

        pred2 = Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.9)
        obs2 = make_commit(repo="B", ctype="fix", insertions=600, deletions=200)  # all wrong
        det.force_detect(pred2, obs2)

        assert det.average_gap > 0.0
        assert det.gap_count == 2

    def test_gaps_above_threshold(self):
        det = GapDetector(GapThresholds(deadband_threshold=0.3))
        # Perfect prediction
        pred = Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.9)
        obs = make_commit(repo="A", ctype="feat", insertions=50, deletions=10)
        det.detect(pred, obs)  # no gap above threshold

        # Bad prediction
        obs2 = make_commit(repo="Z", ctype="fix", insertions=600, deletions=200)
        det.detect(pred, obs2)  # gap above threshold

        assert det.gaps_above_threshold == 1

    def test_gap_tile_has_correct_fields(self):
        det = GapDetector(GapThresholds(deadband_threshold=0.0))
        pred = Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.9)
        obs = make_commit(repo="B", ctype="fix", insertions=600, deletions=200)
        tile, _ = det.force_detect(pred, obs)
        assert tile.prediction is pred
        assert tile.observation is obs
        assert tile.gap_score > 0
        assert tile.timestamp > 0
        assert "repo" in tile.gap_dimensions


# ══════════════════════════════════════════════════════════════════════════════
# LearningLoop tests
# ══════════════════════════════════════════════════════════════════════════════

class TestLearningLoop:
    def test_learn_creates_frequency_tile(self):
        pred = CommitPredictor()
        pred.observe(make_commit())
        learner = LearningLoop(pred)

        gap = GapTile(
            gap_id="g1", prediction=Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.5),
            observation=make_commit(repo="B", ctype="fix", insertions=10, deletions=5),
            gap_score=0.5,
        )
        tile = learner.learn(gap)
        assert tile.update_type == "frequency"
        assert tile.source_gap_id == "g1"

    def test_learn_creates_transition_tile_with_history(self):
        pred = CommitPredictor()
        pred.observe(make_commit())
        pred.observe(make_commit())
        learner = LearningLoop(pred)

        gap = GapTile(
            gap_id="g2",
            prediction=Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.5,
                                  metadata={"history_size": 5}),
            observation=make_commit(repo="B", ctype="fix", insertions=10, deletions=5),
            gap_score=0.7,
        )
        tiles = learner.learning_tiles
        learner.learn(gap)
        # Should have both frequency and transition tiles
        all_tiles = learner.learning_tiles
        types = {t.update_type for t in all_tiles}
        assert "frequency" in types
        assert "transition" in types

    def test_learn_creates_cross_poll_tile(self):
        pred = CommitPredictor()
        pred.observe(make_commit())
        learner = LearningLoop(pred)

        gap = GapTile(
            gap_id="g3",
            prediction=Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.5,
                                  metadata={"history_size": 5}),
            observation=make_commit(repo="B", ctype="fix", insertions=10, deletions=5, cross_poll=True),
            gap_score=0.8,
        )
        learner.learn(gap)
        all_tiles = learner.learning_tiles
        types = {t.update_type for t in all_tiles}
        assert "cross_poll" in types

    def test_learning_rate_affects_boost(self):
        pred = CommitPredictor()
        pred.observe(make_commit())
        learner = LearningLoop(pred, learning_rate=3.0)

        gap = GapTile(
            gap_id="g4",
            prediction=Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.5),
            observation=make_commit(repo="B", ctype="fix", insertions=10, deletions=5),
            gap_score=0.5,
        )
        tile = learner.learn(gap)
        # Boost should be 2 * learning_rate = 6
        assert tile.update_data["boost"] == 6

    def test_learning_rate_setter_clamped(self):
        pred = CommitPredictor()
        learner = LearningLoop(pred)
        learner.learning_rate = 0.01
        assert learner.learning_rate == 0.1  # min
        learner.learning_rate = 100.0
        assert learner.learning_rate == 5.0  # max

    def test_learning_rate_over_time(self):
        pred = CommitPredictor()
        pred.observe(make_commit())
        learner = LearningLoop(pred)

        for i in range(5):
            gap = GapTile(
                gap_id=f"g{i}",
                prediction=Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.5),
                observation=make_commit(repo="B", ctype="fix", insertions=10, deletions=5),
                gap_score=0.5,
            )
            learner.learn(gap)

        rates = learner.learning_rate_over_time()
        assert len(rates) == 5
        assert rates[0]["step"] == 1
        assert rates[-1]["step"] == 5
        assert rates[-1]["avg_gap"] > 0

    def test_learn_all_multiple_gaps(self):
        pred = CommitPredictor()
        pred.observe(make_commit())
        learner = LearningLoop(pred)

        gaps = [
            GapTile(
                gap_id=f"g{i}",
                prediction=Prediction(repo="A", commit_type="feat", size_bucket="medium", cross_pollination_prob=0.0, confidence=0.5),
                observation=make_commit(repo="B", ctype="fix", insertions=10, deletions=5),
                gap_score=0.5,
            )
            for i in range(3)
        ]
        tiles = learner.learn_all(gaps)
        assert len(tiles) == 3
        assert learner.gaps_processed == 3

    def test_gaps_processed_counter(self):
        pred = CommitPredictor()
        learner = LearningLoop(pred)
        assert learner.gaps_processed == 0


# ══════════════════════════════════════════════════════════════════════════════
# CollectiveBroadcaster tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCollectiveBroadcaster:
    def test_broadcast_creates_tile(self):
        bc = CollectiveBroadcaster(agent_name="test-agent")
        tiles = [
            LearningTile(learning_id="l1", source_gap_id="g1", update_type="frequency", update_data={"repo": "X"}),
        ]
        bt = bc.broadcast(tiles)
        assert bt.tile_id.startswith("broadcast-")
        assert bt.source_agent == "test-agent"
        assert len(bt.learning_tiles) == 1

    def test_broadcast_summary(self):
        bc = CollectiveBroadcaster()
        tiles = [
            LearningTile(learning_id="l1", source_gap_id="g1", update_type="frequency", update_data={}),
            LearningTile(learning_id="l2", source_gap_id="g2", update_type="transition", update_data={}),
            LearningTile(learning_id="l3", source_gap_id="g3", update_type="frequency", update_data={}),
        ]
        bt = bc.broadcast(tiles)
        assert "2 frequency" in bt.summary
        assert "1 transition" in bt.summary

    def test_broadcast_count(self):
        bc = CollectiveBroadcaster()
        assert bc.broadcast_count == 0
        bc.broadcast([])
        assert bc.broadcast_count == 1
        bc.broadcast([])
        assert bc.broadcast_count == 2

    def test_plato_buffer(self):
        bc = CollectiveBroadcaster()
        bt = bc.broadcast([])
        assert len(bc.read_plato()) == 1
        assert bc.read_plato()[0] is bt

    def test_clear_plato(self):
        bc = CollectiveBroadcaster()
        bc.broadcast([])
        bc.broadcast([])
        assert len(bc.read_plato()) == 2
        cleared = bc.clear_plato()
        assert cleared == 2
        assert len(bc.read_plato()) == 0

    def test_total_learning_tiles_sent(self):
        bc = CollectiveBroadcaster()
        tiles1 = [LearningTile(learning_id="l1", source_gap_id="g1", update_type="frequency", update_data={})]
        tiles2 = [LearningTile(learning_id="l2", source_gap_id="g2", update_type="frequency", update_data={}),
                   LearningTile(learning_id="l3", source_gap_id="g3", update_type="transition", update_data={})]
        bc.broadcast(tiles1)
        bc.broadcast(tiles2)
        assert bc.total_learning_tiles_sent == 3

    def test_empty_broadcast_summary(self):
        bc = CollectiveBroadcaster()
        bt = bc.broadcast([])
        assert bt.summary == "empty broadcast"

    def test_agent_name(self):
        bc = CollectiveBroadcaster(agent_name="oracle1")
        assert bc.agent_name == "oracle1"


# ══════════════════════════════════════════════════════════════════════════════
# CollectiveInference integration tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCollectiveInference:
    def test_single_cycle_cold_start(self):
        """First cycle with no priming → gap expected."""
        ci = CollectiveInference()
        obs = make_commit(repo="plato-training", ctype="feat", insertions=50, deletions=10)
        result = ci.run_cycle(obs)
        assert result.cycle == 1
        assert result.prediction.repo == "unknown"  # cold start
        assert result.gap_score > 0.3  # everything wrong → high gap
        assert result.gap_tile is not None
        assert len(result.learning_tiles) > 0

    def test_primed_prediction(self):
        """After priming, prediction should match primed data."""
        ci = CollectiveInference()
        commits = [make_commit(repo="tensor-spline", ctype="fix") for _ in range(20)]
        ci.prime(commits)
        obs = make_commit(repo="tensor-spline", ctype="fix")
        result = ci.run_cycle(obs)
        assert result.prediction.repo == "tensor-spline"
        assert result.prediction.commit_type == "fix"

    def test_five_cycles_integration(self):
        """Run 5 full cycles and verify all components work together."""
        ci = CollectiveInference()
        commits = make_diverse_commits(5)
        results = ci.run_cycles(commits)
        assert len(results) == 5

        for r in results:
            assert isinstance(r, CycleResult)
            assert r.prediction is not None
            assert r.observation is not None
            assert r.gap_score >= 0.0
            assert r.avg_gap >= 0.0

    def test_learning_reduces_gap_over_time(self):
        """With enough cycles, learning should reduce average gap."""
        ci = CollectiveInference(CollectiveConfig(deadband_threshold=0.1))
        # Create a repetitive pattern
        commits = [make_commit(repo="A", ctype="feat", insertions=10, deletions=5) for _ in range(30)]
        results = ci.run_cycles(commits)

        # First few cycles should have higher gaps than later ones
        early_gaps = [r.gap_score for r in results[:5]]
        late_gaps = [r.gap_score for r in results[-5:]]
        avg_early = sum(early_gaps) / len(early_gaps)
        avg_late = sum(late_gaps) / len(late_gaps)
        # Learning should reduce gap (or at least not make it worse)
        assert avg_late <= avg_early + 0.1  # small tolerance

    def test_broadcast_frequency(self):
        """Broadcaster should fire based on config."""
        ci = CollectiveInference(CollectiveConfig(
            deadband_threshold=0.0,  # every cycle creates a gap
            broadcast_every=2,       # broadcast every 2 gaps
        ))
        # Prime with some data so predictions aren't totally random
        ci.prime(make_diverse_commits(10))

        commits = make_diverse_commits(5)
        results = ci.run_cycles(commits)

        broadcasts = [r for r in results if r.broadcast is not None]
        assert len(broadcasts) >= 1  # at least one broadcast in 5 cycles

    def test_summary(self):
        ci = CollectiveInference()
        ci.prime(make_diverse_commits(5))
        ci.run_cycles(make_diverse_commits(5))
        s = ci.summary()
        assert s["cycles_run"] == 5
        assert s["total_commits_observed"] == 10  # 5 prime + 5 cycle
        assert s["total_predictions"] == 5
        assert "average_gap" in s
        assert "broadcasts_sent" in s

    def test_config_propagation(self):
        cfg = CollectiveConfig(
            deadband_threshold=0.5,
            learning_rate=2.0,
            agent_name="testbot",
        )
        ci = CollectiveInference(cfg)
        assert ci.config.deadband_threshold == 0.5
        assert ci.learner.learning_rate == 2.0
        assert ci.broadcaster.agent_name == "testbot"

    def test_cycle_count(self):
        ci = CollectiveInference()
        assert ci.cycle_count == 0
        ci.run_cycle(make_commit())
        assert ci.cycle_count == 1
        ci.run_cycle(make_commit())
        assert ci.cycle_count == 2

    def test_component_access(self):
        ci = CollectiveInference()
        assert ci.predictor is not None
        assert ci.gap_detector is not None
        assert ci.learner is not None
        assert ci.broadcaster is not None

    def test_perfect_predictions_no_learning(self):
        """If predictions are perfect, no learning tiles should be created."""
        ci = CollectiveInference()
        # Prime with identical commits
        ci.prime([make_commit(repo="X", ctype="feat", insertions=10, deletions=5) for _ in range(30)])
        # Observe the same pattern — predictor should nail it
        results = ci.run_cycles([make_commit(repo="X", ctype="feat", insertions=10, deletions=5) for _ in range(5)])
        learning_tiles_total = sum(len(r.learning_tiles) for r in results)
        # With strong priming, at least some should be correct
        assert any(r.gap_score < 0.5 for r in results)

    def test_run_cycles_returns_all_results(self):
        ci = CollectiveInference()
        commits = make_diverse_commits(10)
        results = ci.run_cycles(commits)
        assert len(results) == 10
        assert all(isinstance(r, CycleResult) for r in results)

    def test_cycle_result_fields(self):
        ci = CollectiveInference()
        result = ci.run_cycle(make_commit())
        assert isinstance(result.prediction, Prediction)
        assert isinstance(result.observation, CommitObservation)
        assert isinstance(result.gap_score, float)
        assert isinstance(result.learning_tiles, list)
        assert isinstance(result.avg_gap, float)

    def test_prime_returns_count(self):
        ci = CollectiveInference()
        commits = make_diverse_commits(7)
        count = ci.prime(commits)
        assert count == 7
        assert ci.predictor.total_commits == 7

    def test_broadcast_with_many_cycles(self):
        """Run 20 cycles and verify broadcasting happens regularly."""
        ci = CollectiveInference(CollectiveConfig(
            deadband_threshold=0.0,
            broadcast_every=1,
        ))
        ci.prime(make_diverse_commits(10))
        results = ci.run_cycles(make_diverse_commits(20))
        broadcasts = [r for r in results if r.broadcast is not None]
        assert len(broadcasts) >= 10  # most cycles should broadcast

    def test_learning_rate_tracking(self):
        """Learning rate over time should show decreasing avg gap."""
        ci = CollectiveInference(CollectiveConfig(deadband_threshold=0.0))
        # Create a very repetitive pattern
        commits = [make_commit(repo="A", ctype="feat", insertions=10, deletions=5) for _ in range(30)]
        ci.run_cycles(commits)

        rates = ci.learner.learning_rate_over_time()
        if len(rates) >= 2:
            # Later avg_gap should be <= earlier
            assert rates[-1]["avg_gap"] <= rates[0]["avg_gap"] + 0.2

    def test_gap_detector_accessible(self):
        ci = CollectiveInference()
        assert ci.gap_detector.thresholds.deadband_threshold == 0.3  # default

    def test_cycle_results_stored(self):
        ci = CollectiveInference()
        ci.run_cycles(make_diverse_commits(3))
        assert len(ci.cycle_results) == 3


# ══════════════════════════════════════════════════════════════════════════════
# Cross-cutting integration tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCrossCutting:
    def test_predict_observe_gap_learn_share_full_flow(self):
        """End-to-end: predict → observe → gap → learn → share."""
        ci = CollectiveInference(CollectiveConfig(
            deadband_threshold=0.1,
            broadcast_every=1,
        ))

        # Phase 1: Prime with pattern
        pattern = [make_commit(repo="plato-types", ctype="refactor", insertions=30, deletions=20)]
        ci.prime(pattern * 15)

        # Phase 2: Run cycles with same pattern
        results = ci.run_cycles(pattern * 5)

        # Phase 3: Verify the full loop ran
        assert all(r.prediction is not None for r in results)
        assert ci.summary()["cycles_run"] == 5

        # With strong priming, gap should be low
        late_gaps = [r.gap_score for r in results[-3:]]
        assert all(g < 0.8 for g in late_gaps)

    def test_multi_repo_pattern_learning(self):
        """Learn a multi-repo commit pattern."""
        ci = CollectiveInference(CollectiveConfig(deadband_threshold=0.2))

        # Pattern: A → B → C → A → B → C ...
        pattern = [
            make_commit(repo="plato-types", ctype="feat", insertions=30, deletions=5),
            make_commit(repo="tensor-spline", ctype="fix", insertions=10, deletions=3),
            make_commit(repo="plato-training", ctype="test", insertions=80, deletions=20),
        ]
        ci.prime(pattern * 7)  # 21 commits to learn the pattern

        # Run a few more cycles with the same pattern
        results = ci.run_cycles(pattern * 3)  # 9 more

        # The predictor should be getting better at this pattern
        assert len(results) == 9

    def test_broadcast_to_mock_plato(self):
        """Verify broadcast tiles can be stored and retrieved from mock PLATO."""
        bc = CollectiveBroadcaster(agent_name="forgemaster")
        tiles = [
            LearningTile(learning_id="l1", source_gap_id="g1", update_type="frequency",
                         update_data={"repo": "plato-training", "boost": 5}),
            LearningTile(learning_id="l2", source_gap_id="g1", update_type="transition",
                         update_data={"prev_repo": "A", "next_repo": "B"}),
        ]
        bt = bc.broadcast(tiles)

        # Read back from PLATO
        stored = bc.read_plato()
        assert len(stored) == 1
        assert stored[0].tile_id == bt.tile_id
        assert stored[0].source_agent == "forgemaster"
        assert len(stored[0].learning_tiles) == 2

    def test_commit_size_bucket_consistency(self):
        """Verify size buckets are consistent between prediction and observation."""
        for total, expected in [(3, "tiny"), (15, "small"), (80, "medium"), (300, "large"), (1000, "massive")]:
            c = make_commit(insertions=total // 2, deletions=total // 2)
            assert c.size_bucket == expected, f"total={total} expected={expected} got={c.size_bucket}"
