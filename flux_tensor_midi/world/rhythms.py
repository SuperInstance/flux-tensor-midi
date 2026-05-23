"""World rhythm patterns — clave, bell, tala, iqa, swing."""

from __future__ import annotations

from typing import Literal


# ---------------------------------------------------------------------------
# Clave patterns
# ---------------------------------------------------------------------------

_CLAVE_PATTERNS: dict[str, list[int]] = {
    # Subdivisions within a 16-step grid (0-indexed)
    "son_2_3": [0, 3, 6, 8, 11],  # 2-3 son clave
    "son_3_2": [0, 3, 6, 10, 13],  # 3-2 son clave (reversed)
    "rumba_2_3": [0, 3, 6, 8, 12],  # 2-3 rumba clave
    "rumba_3_2": [0, 4, 8, 10, 13],  # 3-2 rumba clave
    "bossa_nova": [0, 3, 6, 8, 11, 14],  # bossa nova pattern
}


def clave(
    type: Literal[
        "son_2_3", "son_3_2", "rumba_2_3", "rumba_3_2", "bossa_nova"
    ] = "son_2_3",
    subdivisions: int = 16,
) -> list[int]:
    """Return clave hit positions within *subdivisions* steps.

    Returns indices of accented beats.
    """
    pattern = _CLAVE_PATTERNS.get(type)
    if pattern is None:
        raise KeyError(f"Unknown clave type: {type!r}.  Available: {list(_CLAVE_PATTERNS)}")
    if subdivisions != 16:
        ratio = subdivisions / 16.0
        return [round(p * ratio) for p in pattern]
    return list(pattern)


# ---------------------------------------------------------------------------
# Bell patterns (iron bell / gankogui)
# ---------------------------------------------------------------------------

_BELL_PATTERNS: dict[str, list[int]] = {
    # 12-pulse bell patterns (common in Ewe music)
    "agbadza": [0, 3, 4, 6, 8, 10],
    "gahu": [0, 2, 5, 6, 8, 10],
    "atsiagbekor": [0, 2, 5, 6, 8, 11],
    "kinka": [0, 3, 6, 8, 11],
    # 16-pulse bell patterns
    "yanvalou": [0, 3, 6, 9, 12, 15],
    "iren": [0, 2, 4, 6, 8, 10, 12, 14],
}


def bell_pattern(
    style: Literal[
        "agbadza", "gahu", "atsiagbekor", "kinka", "yanvalou", "iren"
    ] = "agbadza",
) -> list[int]:
    """Return bell hit positions for the given *style*."""
    pattern = _BELL_PATTERNS.get(style)
    if pattern is None:
        raise KeyError(f"Unknown bell style: {style!r}.  Available: {list(_BELL_PATTERNS)}")
    return list(pattern)


# ---------------------------------------------------------------------------
# Indian tala
# ---------------------------------------------------------------------------

_TALAS: dict[str, dict] = {
    "teental": {"beats": 16, "groups": [4, 4, 4, 4], "claps": [1, 5, 9, 13]},
    "jhap_tal": {"beats": 10, "groups": [2, 3, 2, 3], "claps": [1, 3, 6, 8]},
    "rupak": {"beats": 7, "groups": [3, 2, 2], "claps": [1, 4, 6]},
    "ek_tal": {"beats": 12, "groups": [2, 2, 2, 2, 2, 2], "claps": [1, 3, 5, 7, 9, 11]},
    "kaharwa": {"beats": 8, "groups": [4, 4], "claps": [1, 5]},
    "dadra": {"beats": 6, "groups": [3, 3], "claps": [1, 4]},
    "deepchandi": {"beats": 14, "groups": [3, 4, 3, 4], "claps": [1, 4, 8, 11]},
}


def tala(name: str = "teental") -> dict:
    """Return tala (Indian rhythmic cycle) information.

    Keys: ``beats``, ``groups``, ``claps``.
    """
    key = name.lower().replace(" ", "_").replace("-", "_")
    if key not in _TALAS:
        raise KeyError(f"Unknown tala: {name!r}.  Available: {list(_TALAS)}")
    return dict(_TALAS[key])


# ---------------------------------------------------------------------------
# Arabic iqa'at
# ---------------------------------------------------------------------------

_IQAAT: dict[str, dict] = {
    "maqsum": {"beats": 4, "pattern": ["D", "T", "D", "T"], "subdivisions": 8},
    "baladi": {"beats": 4, "pattern": ["D", "D", "T", "D"], "subdivisions": 8},
    "saidi": {"beats": 4, "pattern": ["D", "T", "D", "D"], "subdivisions": 8},
    "malfuf": {"beats": 2, "pattern": ["D", "T"], "subdivisions": 4},
    "fallahi": {"beats": 2, "pattern": ["D", "D"], "subdivisions": 4},
    "sama_i_thaqil": {"beats": 10, "pattern": ["D", "T", "T", "D", "T"], "subdivisions": 20},
    "aqsaq": {"beats": 9, "pattern": ["D", "T", "T", "D", "T"], "subdivisions": 18},
    "dawr_hind": {"beats": 7, "pattern": ["D", "T", "T", "D"], "subdivisions": 14},
}


def iqa(name: str = "maqsum") -> dict:
    """Return Arabic *iqa'* (rhythmic cycle) information.

    Keys: ``beats``, ``pattern`` (D=Dum, T=Tak), ``subdivisions``.
    """
    key = name.lower().replace(" ", "_").replace("-", "_").replace("'", "")
    if key not in _IQAAT:
        raise KeyError(f"Unknown iqa: {name!r}.  Available: {list(_IQAAT)}")
    return dict(_IQAAT[key])


# ---------------------------------------------------------------------------
# Swing
# ---------------------------------------------------------------------------

def swing_ratio(ratio: float = 0.67) -> dict:
    """Compute swing timing.

    *ratio* ``0.5`` = straight, ``0.67`` = triplet swing, ``0.75`` = dotted.

    Returns ``{"long": float, "short": float}`` normalised to sum 1.0.
    """
    if not 0.25 <= ratio <= 0.85:
        raise ValueError("Swing ratio should be between 0.25 and 0.85")
    long = ratio * 2
    short = (1.0 - ratio) * 2
    total = long + short
    return {"long": round(long / total, 4), "short": round(short / total, 4)}
