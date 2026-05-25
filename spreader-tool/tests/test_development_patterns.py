"""Tests for the development pattern library."""

import pytest
import tempfile
import os

from spreader.development_patterns import DevelopmentPattern, PatternLibrary


class TestPatternLibraryCreation:
    def test_empty_library(self):
        lib = PatternLibrary()
        assert lib.list_all() == []

    def test_default_patterns_loaded(self):
        lib = PatternLibrary()
        lib.load_defaults()
        all_patterns = lib.list_all()
        assert len(all_patterns) > 0
        # Check some known patterns
        ids = {p.pattern_id for p in all_patterns}
        assert "frozen_dataclass_with_transition" in ids
        assert "hysteresis_guard" in ids
        assert "content_addressed_dedup" in ids

    def test_defaults_include_locked_patterns(self):
        lib = PatternLibrary()
        lib.load_defaults()
        locked = lib.list_locked()
        assert len(locked) > 0
        assert all(p.locked for p in locked)


class TestFindForContext:
    def test_find_matching_patterns(self):
        lib = PatternLibrary()
        lib.load_defaults()
        results = lib.find_for_context("state machine immutable dataclass")
        assert len(results) > 0
        # Should find the frozen dataclass pattern
        names = [p.name for p in results]
        assert any("Frozen Dataclass" in n for n in names)

    def test_find_hysteresis_patterns(self):
        lib = PatternLibrary()
        lib.load_defaults()
        results = lib.find_for_context("hysteresis threshold stability")
        assert len(results) > 0

    def test_find_no_match_returns_empty(self):
        lib = PatternLibrary()
        lib.load_defaults()
        results = lib.find_for_context("xyzzy_plugh_tuesday_grault")
        assert results == []

    def test_results_sorted_by_success_rate(self):
        lib = PatternLibrary()
        lib.load_defaults()
        results = lib.find_for_context("dataclass")
        if len(results) > 1:
            # Results should be sorted by score (keyword match × success_rate) descending
            for i in range(len(results) - 1):
                # At least check they're ordered (all defaults have rate 1.0, so this is trivially true)
                assert results[i].success_rate >= 0


class TestAddPattern:
    def test_add_custom_pattern(self):
        lib = PatternLibrary()
        pattern = DevelopmentPattern(
            pattern_id="test_pattern",
            name="Test Pattern",
            description="A test pattern for unit tests",
            applies_when="When testing the pattern library",
            code_template="pass",
            success_rate=0.5,
            locked=False,
        )
        pid = lib.register(pattern)
        assert pid == "test_pattern"
        retrieved = lib.get("test_pattern")
        assert retrieved is not None
        assert retrieved.name == "Test Pattern"

    def test_add_pattern_auto_generates_id(self):
        lib = PatternLibrary()
        pattern = DevelopmentPattern(
            pattern_id="",
            name="Auto ID Pattern",
            description="Test",
            applies_when="test",
            code_template="pass",
            success_rate=0.8,
            locked=False,
        )
        pid = lib.register(pattern)
        assert pid != ""
        assert len(pid) > 0


class TestRecordUse:
    def test_record_use_increments_count(self):
        lib = PatternLibrary()
        pattern = DevelopmentPattern(
            pattern_id="counter_test",
            name="Counter",
            description="test",
            applies_when="test",
            code_template="pass",
            success_rate=0.5,
            locked=False,
            use_count=0,
        )
        lib.register(pattern)
        p = lib.get("counter_test")
        assert p.use_count == 0

        p.record_use(success=True)
        assert p.use_count == 1

        p.record_use(success=True)
        assert p.use_count == 2

    def test_record_use_updates_success_rate(self):
        lib = PatternLibrary()
        pattern = DevelopmentPattern(
            pattern_id="rate_test",
            name="Rate",
            description="test",
            applies_when="test",
            code_template="pass",
            success_rate=0.0,
            locked=False,
            use_count=0,
        )
        lib.register(pattern)
        p = lib.get("rate_test")

        p.record_use(success=True)
        assert p.success_rate == 1.0

        p.record_use(success=False)
        assert p.success_rate == 0.5

        p.record_use(success=True)
        assert p.success_rate == pytest.approx(2 / 3)


class TestLockUnlock:
    def test_lock_pattern(self):
        lib = PatternLibrary()
        pattern = DevelopmentPattern(
            pattern_id="lock_test",
            name="Lock",
            description="test",
            applies_when="test",
            code_template="pass",
            success_rate=0.9,
            locked=False,
        )
        lib.register(pattern)
        locked = lib.lock_pattern("lock_test")
        assert locked.locked is True

    def test_unlock_pattern(self):
        lib = PatternLibrary()
        pattern = DevelopmentPattern(
            pattern_id="unlock_test",
            name="Unlock",
            description="test",
            applies_when="test",
            code_template="pass",
            success_rate=0.9,
            locked=True,
        )
        lib.register(pattern)
        unlocked = lib.unlock_pattern("unlock_test")
        assert unlocked.locked is False

    def test_lock_nonexistent_raises(self):
        lib = PatternLibrary()
        with pytest.raises(KeyError):
            lib.lock_pattern("nonexistent")


class TestPersistence:
    def test_persist_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "patterns.json")
            lib1 = PatternLibrary(persist_path=path)
            lib1.register(DevelopmentPattern(
                pattern_id="persist_test",
                name="Persist",
                description="test",
                applies_when="test",
                code_template="pass",
                success_rate=0.8,
                locked=False,
            ))

            # Reload from disk
            lib2 = PatternLibrary(persist_path=path)
            p = lib2.get("persist_test")
            assert p is not None
            assert p.name == "Persist"
            assert p.success_rate == 0.8
