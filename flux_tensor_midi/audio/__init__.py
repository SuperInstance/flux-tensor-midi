"""
flux_tensor_midi.audio — DawDreamer bridge for audio rendering.

Renders constraint-generated MIDI to actual audio via DawDreamer.
If dawdreamer is not installed, MockRenderer is used for testing.
"""

from flux_tensor_midi.audio.dawdreamer_bridge import (
    DawDreamerRenderer,
    MockRenderer,
    create_renderer,
    find_soundfonts,
)

__all__ = [
    "DawDreamerRenderer",
    "MockRenderer",
    "create_renderer",
    "find_soundfonts",
]
