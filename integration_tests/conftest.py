"""Shared fixtures for integration tests."""

import os
import tempfile
import pytest


@pytest.fixture
def tmp_midi_dir():
    """Provide a temporary directory for MIDI output files."""
    with tempfile.TemporaryDirectory(prefix="integration_midi_") as d:
        yield d
