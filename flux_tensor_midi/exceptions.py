"""
Custom exceptions for flux-tensor-midi.

All public modules raise these for domain-specific error conditions,
allowing callers to distinguish user mistakes from internal bugs.
"""

from __future__ import annotations


class ConstraintError(ValueError):
    """Invalid constraint parameters.

    Raised when a musical constraint (BPM range, step count, velocity
    bounds, etc.) receives a value outside its valid domain.

    Examples
    --------
    >>> from flux_tensor_midi.drum_rack import StepSequencer
    >>> StepSequencer(steps=7)
    Traceback (most recent call last):
        ...
    ValueError: steps must be 8, 16, or 32, got 7
    """


class RenderError(RuntimeError):
    """MIDI rendering failure.

    Raised when the render pipeline encounters an unrecoverable error,
    such as a missing dependency for file output or corrupt state.

    Examples
    --------
    Attempting to render to a read-only path or with invalid tempo.
    """


class GenreError(ValueError):
    """Unknown genre or preset name.

    Raised when a preset, genre, or pattern name cannot be resolved.

    Examples
    --------
    >>> from flux_tensor_midi.drum_rack import StepSequencer
    >>> seq = StepSequencer()
    >>> seq.load_preset("polka")
    Traceback (most recent call last):
        ...
    ValueError: Unknown preset 'polka'. Available: [...]
    """
