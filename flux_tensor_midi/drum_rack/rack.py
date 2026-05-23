"""
Drum Rack: GM percussion map and utility helpers.
"""

from __future__ import annotations

from typing import Dict, Tuple

# Standard GM Level 1 Percussion Key Map (Channel 10)
# Abbreviated to the most commonly used sounds.
GM_DRUM_MAP: Dict[str, int] = {
    # Kicks
    "kick": 36,
    "kick_1": 36,
    "kick_2": 35,
    # Snares
    "snare": 38,
    "snare_1": 38,
    "snare_2": 40,
    "side_stick": 37,
    # Hi-hats
    "hihat_closed": 42,
    "hihat_open": 46,
    "hihat_pedal": 44,
    # Toms
    "tom_low": 45,
    "tom_mid": 47,
    "tom_high": 50,
    "tom_floor": 43,
    # Cymbals
    "crash": 49,
    "crash_2": 57,
    "ride": 51,
    "ride_bell": 53,
    "china": 52,
    "splash": 55,
    # Extras
    "clap": 39,
    "cowbell": 56,
    "tambourine": 54,
    "shaker": 70,
    "conga_high": 63,
    "conga_low": 64,
    "bongo_high": 60,
    "bongo_low": 61,
    "rimshot": 37,
    "whistle_low": 71,
    "whistle_high": 72,
    "guiro_short": 73,
    "guiro_long": 74,
    "claves": 75,
    "woodblock_high": 76,
    "woodblock_low": 77,
    "cuica_high": 78,
    "cuica_low": 79,
    "triangle": 80,
}

# Reverse map: note number -> name
_NOTE_TO_NAME: Dict[int, str] = {v: k for k, v in GM_DRUM_MAP.items()}


class DrumRack:
    """A drum rack mapping instrument names to GM percussion note numbers.

    Parameters
    ----------
    channel : int
        MIDI channel for drums (default 9 = channel 10 in 1-based).
    custom_map : dict, optional
        Override or extend the default GM map.
    """

    def __init__(
        self,
        channel: int = 9,
        custom_map: Dict[str, int] | None = None,
    ):
        if not 0 <= channel <= 15:
            raise ValueError(f"MIDI channel must be 0–15, got {channel}")
        self._channel = channel
        self._map: Dict[str, int] = dict(GM_DRUM_MAP)
        if custom_map:
            self._map.update(custom_map)

    @property
    def channel(self) -> int:
        return self._channel

    def note_for(self, instrument: str) -> int:
        """Return the MIDI note number for *instrument*."""
        try:
            return self._map[instrument]
        except KeyError:
            raise KeyError(
                f"Unknown instrument '{instrument}'. "
                f"Known: {sorted(self._map.keys())}"
            )

    def register(self, name: str, note: int) -> None:
        """Register or override an instrument mapping."""
        if not 0 <= note <= 127:
            raise ValueError(f"Note must be 0–127, got {note}")
        self._map[name] = note

    def instruments(self) -> list[str]:
        """Return sorted list of all mapped instrument names."""
        return sorted(self._map.keys())

    def as_dict(self) -> Dict[str, int]:
        return dict(self._map)

    def __repr__(self) -> str:
        return f"DrumRack(channel={self._channel}, instruments={len(self._map)})"
