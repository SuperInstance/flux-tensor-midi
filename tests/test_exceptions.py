"""Tests for the exceptions module."""

from __future__ import annotations

import pytest

from flux_tensor_midi.exceptions import ConstraintError, RenderError, GenreError


class TestConstraintError:
    def test_is_value_error(self):
        assert issubclass(ConstraintError, ValueError)

    def test_raise_and_catch(self):
        with pytest.raises(ConstraintError, match="invalid bpm"):
            raise ConstraintError("invalid bpm")

    def test_catch_as_value_error(self):
        with pytest.raises(ValueError):
            raise ConstraintError("any constraint message")

    def test_str_message(self):
        err = ConstraintError("steps must be positive")
        assert str(err) == "steps must be positive"


class TestRenderError:
    def test_is_runtime_error(self):
        assert issubclass(RenderError, RuntimeError)

    def test_raise_and_catch(self):
        with pytest.raises(RenderError, match="render failed"):
            raise RenderError("render failed")

    def test_not_value_error(self):
        # RenderError should NOT be caught as ValueError
        with pytest.raises(RenderError):
            try:
                raise RenderError("pipe broke")
            except ValueError:
                pytest.fail("RenderError should not be a ValueError")

    def test_str_message(self):
        err = RenderError("missing dependency")
        assert str(err) == "missing dependency"


class TestGenreError:
    def test_is_value_error(self):
        assert issubclass(GenreError, ValueError)

    def test_raise_and_catch(self):
        with pytest.raises(GenreError, match="unknown genre"):
            raise GenreError("unknown genre")

    def test_catch_as_value_error(self):
        with pytest.raises(ValueError):
            raise GenreError("no such preset")

    def test_str_message(self):
        err = GenreError("Unknown preset 'polka'")
        assert "polka" in str(err)


class TestExceptionHierarchy:
    def test_distinct_types(self):
        assert ConstraintError is not RenderError
        assert RenderError is not GenreError
        assert ConstraintError is not GenreError

    def test_can_distinguish_in_catch(self):
        """Verify that catching ValueError gets ConstraintError and GenreError
        but NOT RenderError."""
        caught = []
        for exc_class in [ConstraintError, GenreError, RenderError]:
            try:
                raise exc_class("test")
            except ValueError:
                caught.append(exc_class.__name__)
            except RuntimeError:
                pass
        assert "ConstraintError" in caught
        assert "GenreError" in caught
        assert "RenderError" not in caught
