"""
Nod side-channel: agreement / acknowledgment between musicians.

A nod is a gentle, affirmative gesture — "I hear you, I agree."
Used for beat alignment, phrase boundaries, and chord changes.
"""

from __future__ import annotations
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flux_tensor_midi.core.room import RoomMusician


class Nod:
    """A nod gesture sent between musicians.

    Parameters
    ----------
    intensity : float, default=0.5
        Strength of the nod (0–1).
    """

    def __init__(self, intensity: float = 0.5):
        if not 0 <= intensity <= 1:
            raise ValueError(f"intensity must be 0–1, got {intensity}")
        self._intensity = intensity
        self._sent_to: set[str] = set()
        self._timestamps: list[float] = []

    @property
    def intensity(self) -> float:
        """Strength of the nod (0–1)."""
        return self._intensity

    @intensity.setter
    def intensity(self, value: float) -> None:
        """Set nod intensity, clamped to [0, 1]."""
        if not 0 <= value <= 1:
            raise ValueError(f"intensity must be 0–1, got {value}")
        self._intensity = value

    @property
    def count(self) -> int:
        """Total number of nods sent."""
        return len(self._timestamps)

    @property
    def timestamps(self) -> list[float]:
        """Copy of all nod timestamps."""
        return list(self._timestamps)

    def send(self, target: RoomMusician) -> None:
        """Send a nod to a target musician.

        Parameters
        ----------
        target : RoomMusician
            The musician to nod to.
        """
        self._sent_to.add(target.room_id)
        self._timestamps.append(time.monotonic())

    def has_sent_to(self, room_id: str) -> bool:
        """Check if a nod was sent to a specific room.

        Parameters
        ----------
        room_id : str
            Room ID to check.

        Returns
        -------
        bool
            True if a nod was sent to this room.
        """
        return room_id in self._sent_to

    def rate(self, window_seconds: float = 10.0) -> float:
        """Nods per second in the given time window.

        Parameters
        ----------
        window_seconds : float, default=10.0
            Time window in seconds.

        Returns
        -------
        float
            Rate of nods per second.
        """
        if window_seconds <= 0:
            return 0.0
        now = time.monotonic()
        recent = [t for t in self._timestamps if now - t <= window_seconds]
        return len(recent) / window_seconds

    def reset(self) -> None:
        """Clear nod history."""
        self._sent_to.clear()
        self._timestamps.clear()

    def __repr__(self) -> str:
        return f"Nod(intensity={self._intensity}, count={self.count})"
