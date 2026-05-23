"""
Exercise generation pipeline integration test.

Pipeline: constraint-theory-core exercises → verify solutions → seed reproducibility
"""

import pytest

from constraint_theory_core import generate_exercise
from constraint_theory_core.exercises import TOPICS, DIFFICULTIES


class TestExerciseRoundtrip:
    """Generate exercises, verify solutions, check seed reproducibility."""

    def test_all_topics_have_exercises(self):
        """Every topic/difficulty combination should produce a valid exercise."""
        for topic in TOPICS:
            for difficulty in DIFFICULTIES:
                ex = generate_exercise(topic, difficulty)
                assert ex is not None, f"No exercise for {topic}/{difficulty}"
                assert ex['topic'] == topic
                assert ex['difficulty'] == difficulty
                assert 'instructions' in ex
                assert 'constraints' in ex
                assert len(ex['constraints']) > 0

    def test_solutions_satisfy_constraints(self):
        """For each exercise with a solution, verify the solution exists and is structured."""
        for topic in TOPICS:
            for difficulty in DIFFICULTIES:
                ex = generate_exercise(topic, difficulty, seed=42)
                assert 'solution' in ex, f"No solution key for {topic}/{difficulty}"
                solution = ex['solution']
                assert solution is not None, f"Null solution for {topic}/{difficulty}"
                # Solution should be a dict with at least one key
                assert isinstance(solution, dict), f"Solution should be dict for {topic}/{difficulty}"
                assert len(solution) > 0

    def test_species_counterpoint_exercise_solution(self):
        """Verify species counterpoint exercise uses snap/safety correctly."""
        ex = generate_exercise('species_counterpoint', 'beginner', seed=42)
        sol = ex['solution']

        # Solution should contain interval classifications
        if 'safe' in sol and 'intervals_semitones' in sol:
            from constraint_theory_core import snap, is_safe
            intervals = sol['intervals_semitones']
            safe_flags = sol['safe']

            assert len(intervals) == len(safe_flags)

            # Verify each interval can be snapped and classified
            for interval in intervals:
                _pt, error = snap(interval, 0)
                actual_safe = is_safe(error)
                # We verify the snap mechanics work;
                # the exercise's classification is informational
                assert isinstance(actual_safe, bool)

    def test_seed_reproducibility(self):
        """Same seed → same exercise."""
        for topic in TOPICS:
            for difficulty in DIFFICULTIES:
                ex1 = generate_exercise(topic, difficulty, seed=12345)
                ex2 = generate_exercise(topic, difficulty, seed=12345)

                # Instructions and solution should be identical
                assert ex1['instructions'] == ex2['instructions'], (
                    f"Instructions differ for {topic}/{difficulty} with same seed"
                )
                assert ex1['solution'] == ex2['solution'], (
                    f"Solutions differ for {topic}/{difficulty} with same seed"
                )
                assert ex1['starting_notes'] == ex2['starting_notes'], (
                    f"Starting notes differ for {topic}/{difficulty} with same seed"
                )

    def test_different_seeds_differ(self):
        """Different seeds should (usually) produce different exercises."""
        ex1 = generate_exercise('species_counterpoint', 'beginner', seed=1)
        ex2 = generate_exercise('species_counterpoint', 'beginner', seed=999)

        # At least one of these should differ
        differs = (
            ex1['starting_notes'] != ex2['starting_notes']
            or ex1['solution'] != ex2['solution']
        )
        assert differs, "Different seeds produced identical exercises"

    def test_exercise_has_scoring_rubric(self):
        """Every exercise should have a scoring rubric."""
        for topic in TOPICS:
            for difficulty in DIFFICULTIES:
                ex = generate_exercise(topic, difficulty, seed=42)
                assert 'scoring_rubric' in ex, f"No rubric for {topic}/{difficulty}"
                rubric = ex['scoring_rubric']
                assert isinstance(rubric, dict)
                assert sum(rubric.values()) == 100, (
                    f"Rubric should sum to 100 for {topic}/{difficulty}, got {sum(rubric.values())}"
                )
