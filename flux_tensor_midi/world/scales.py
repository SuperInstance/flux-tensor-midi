"""World music scales as data — Indian ragas, Arabic/Turkish maqamat, East Asian pentatonic, African scales."""

from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Scale database
# ---------------------------------------------------------------------------

WORLD_SCALES: dict[str, dict] = {
    # ── Indian Ragas (10) ──────────────────────────────────────────────────
    "bhairavi": {
        "notes": [0, 1, 3, 5, 7, 8, 10],
        "shruti": [0, 90, 204, 294, 384, 498, 590, 702, 792, 890, 996, 1088, 1200],
        "vadi": 1,
        "samvadi": 5,
        "rasa": "devotional",
        "time": "morning",
        "culture": "indian",
        "thaat": "bhairavi",
    },
    "yaman": {
        "notes": [0, 2, 4, 6, 7, 9, 11],
        "shruti": [0, 112, 204, 316, 408, 498, 610, 702, 814, 906, 1018, 1110, 1200],
        "vadi": 0,
        "samvadi": 4,
        "rasa": "romantic",
        "time": "evening",
        "culture": "indian",
        "thaat": "kalyan",
    },
    "darbari": {
        "notes": [0, 2, 3, 5, 7, 8, 10],
        "shruti": [0, 112, 204, 294, 408, 498, 610, 702, 792, 906, 996, 1110, 1200],
        "vadi": 3,
        "samvadi": 7,
        "rasa": "solemn",
        "time": "night",
        "culture": "indian",
        "thaat": "asavari",
    },
    "malkauns": {
        "notes": [0, 2, 4, 6, 8, 10],
        "shruti": [0, 204, 384, 498, 702, 890, 1200],
        "vadi": 2,
        "samvadi": 6,
        "rasa": "meditative",
        "time": "night",
        "culture": "indian",
        "thaat": "bhairavi",
    },
    "bageshri": {
        "notes": [0, 2, 3, 5, 7, 9, 10],
        "shruti": [0, 112, 204, 294, 408, 498, 610, 702, 814, 906, 996, 1110, 1200],
        "vadi": 2,
        "samvadi": 7,
        "rasa": "longing",
        "time": "night",
        "culture": "indian",
        "thaat": "kafi",
    },
    "todi": {
        "notes": [0, 1, 3, 5, 7, 8, 11],
        "shruti": [0, 90, 204, 294, 384, 498, 590, 702, 792, 890, 996, 1088, 1200],
        "vadi": 3,
        "samvadi": 7,
        "rasa": "pathos",
        "time": "morning",
        "culture": "indian",
        "thaat": "todi",
    },
    "bhairav": {
        "notes": [0, 1, 4, 5, 7, 8, 11],
        "shruti": [0, 90, 204, 316, 408, 498, 610, 702, 792, 890, 1018, 1110, 1200],
        "vadi": 4,
        "samvadi": 8,
        "rasa": "solemn",
        "time": "morning",
        "culture": "indian",
        "thaat": "bhairav",
    },
    "kafi": {
        "notes": [0, 2, 3, 5, 7, 9, 10],
        "shruti": [0, 112, 204, 294, 408, 498, 610, 702, 814, 906, 996, 1110, 1200],
        "vadi": 3,
        "samvadi": 7,
        "rasa": "playful",
        "time": "evening",
        "culture": "indian",
        "thaat": "kafi",
    },
    "bilawal": {
        "notes": [0, 2, 4, 5, 7, 9, 11],
        "shruti": [0, 112, 204, 316, 408, 498, 610, 702, 814, 906, 1018, 1110, 1200],
        "vadi": 4,
        "samvadi": 0,
        "rasa": "joyful",
        "time": "morning",
        "culture": "indian",
        "thaat": "bilawal",
    },
    "asavari": {
        "notes": [0, 2, 3, 5, 7, 8, 10],
        "shruti": [0, 112, 204, 294, 408, 498, 610, 702, 792, 906, 996, 1110, 1200],
        "vadi": 3,
        "samvadi": 7,
        "rasa": "melancholy",
        "time": "morning",
        "culture": "indian",
        "thaat": "asavari",
    },

    # ── Arabic / Turkish Maqamat (10) ──────────────────────────────────────
    "rast": {
        "notes": [0, 2, 4, 5, 7, 9, 11],
        "quarter_tones": False,
        "culture": "arabic",
        "family": "rast",
        "ajnas": ["rast", "rast"],
        "tonic": 0,
        "dominant": 4,
    },
    "bayati": {
        "notes": [0, 1.5, 4, 5, 7, 8.5, 10],
        "quarter_tones": True,
        "culture": "arabic",
        "family": "bayati",
        "ajnas": ["bayati", "nahawand"],
        "tonic": 0,
        "dominant": 4,
    },
    "hijaz": {
        "notes": [0, 1, 4, 5, 7, 8, 11],
        "quarter_tones": False,
        "culture": "arabic",
        "family": "hijaz",
        "ajnas": ["hijaz", "nahawand"],
        "tonic": 0,
        "dominant": 4,
    },
    "sikah": {
        "notes": [0, 2, 3.5, 5, 7, 8.5, 10.5],
        "quarter_tones": True,
        "culture": "arabic",
        "family": "sikah",
        "ajnas": ["sikah", "hijaz"],
        "tonic": 0,
        "dominant": 3.5,
    },
    "nahawand": {
        "notes": [0, 2, 3, 5, 7, 8, 11],
        "quarter_tones": False,
        "culture": "arabic",
        "family": "nahawand",
        "ajnas": ["nahawand", "hijaz"],
        "tonic": 0,
        "dominant": 4,
    },
    "kurd": {
        "notes": [0, 1, 3, 5, 7, 8, 10],
        "quarter_tones": False,
        "culture": "arabic",
        "family": "kurd",
        "ajnas": ["kurd", "kurd"],
        "tonic": 0,
        "dominant": 4,
    },
    "ajam": {
        "notes": [0, 2, 4, 5, 7, 9, 11],
        "quarter_tones": False,
        "culture": "arabic",
        "family": "ajam",
        "ajnas": ["ajam", "ajam"],
        "tonic": 0,
        "dominant": 4,
    },
    "saba": {
        "notes": [0, 1, 3, 4, 6, 7, 10],
        "quarter_tones": False,
        "culture": "arabic",
        "family": "saba",
        "ajnas": ["saba", "bayati"],
        "tonic": 0,
        "dominant": 4,
    },
    "huzam": {
        "notes": [0, 2, 3.5, 5, 7, 8.5, 10],
        "quarter_tones": True,
        "culture": "arabic",
        "family": "sikah",
        "ajnas": ["sikah", "nahawand"],
        "tonic": 0,
        "dominant": 3.5,
    },
    "nakriz": {
        "notes": [0, 2, 3, 5, 7, 8, 11],
        "quarter_tones": False,
        "culture": "arabic",
        "family": "nahawand",
        "ajnas": ["nakriz", "hijaz"],
        "tonic": 0,
        "dominant": 4,
    },

    # ── East Asian Pentatonic (10) ─────────────────────────────────────────
    "in_scale": {
        "notes": [0, 2, 3, 7, 8],
        "culture": "japanese",
        "type": "miyako-bushi",
        "mood": "melancholy",
    },
    "yo_scale": {
        "notes": [0, 2, 5, 7, 9],
        "culture": "japanese",
        "type": "yo",
        "mood": "bright",
    },
    "hirajoshi": {
        "notes": [0, 2, 3, 7, 8],
        "culture": "japanese",
        "type": "hirajoshi",
        "mood": "tense",
    },
    "kumoi": {
        "notes": [0, 2, 3, 7, 9],
        "culture": "japanese",
        "type": "kumoi",
        "mood": "ethereal",
    },
    "gong_mode": {
        "notes": [0, 2, 4, 7, 9],
        "culture": "chinese",
        "element": "earth",
        "type": "gong",
    },
    "shang_mode": {
        "notes": [0, 2, 4, 7, 9],
        "culture": "chinese",
        "element": "metal",
        "type": "shang",
    },
    "jiao_mode": {
        "notes": [0, 2, 5, 7, 10],
        "culture": "chinese",
        "element": "wood",
        "type": "jiao",
    },
    "zhi_mode": {
        "notes": [0, 2, 5, 7, 10],
        "culture": "chinese",
        "element": "fire",
        "type": "zhi",
    },
    "yu_mode": {
        "notes": [0, 3, 5, 7, 10],
        "culture": "chinese",
        "element": "water",
        "type": "yu",
    },
    "pentatonic_major": {
        "notes": [0, 2, 4, 7, 9],
        "culture": "east_asian",
        "type": "major_pentatonic",
        "mood": "bright",
    },

    # ── African Scales (6) ─────────────────────────────────────────────────
    "ewe_standard": {
        "notes": [0, 2, 4, 5, 7, 9, 11],
        "culture": "ewe",
        "region": "west_africa",
    },
    "pentatonic_african": {
        "notes": [0, 2, 3, 7, 8],
        "culture": "african",
        "region": "pan_african",
    },
    "zimbabwe_mbira": {
        "notes": [0, 3, 5, 7, 8, 10],
        "culture": "shona",
        "region": "southern_africa",
        "instrument": "mbira",
    },
    "amadinda_scale": {
        "notes": [0, 2, 4, 5, 7, 9],
        "culture": "buganda",
        "region": "east_africa",
        "instrument": "amadinda",
    },
    "manden_scale": {
        "notes": [0, 2, 4, 6, 7, 9, 11],
        "culture": "manden",
        "region": "west_africa",
        "instrument": "kora",
    },
    "tigre_scale": {
        "notes": [0, 1, 3, 5, 7, 8, 10],
        "culture": "tigre",
        "region": "east_africa",
    },

    # ── Additional Scales ──────────────────────────────────────────────────
    "pelog": {
        "notes": [0, 1, 3, 7, 8],
        "culture": "indonesian",
        "type": "pelog",
        "slendro_equivalent": None,
    },
    "slendro": {
        "notes": [0, 2, 4, 7, 9],
        "culture": "indonesian",
        "type": "slendro",
        "pelog_equivalent": None,
    },
    "hungarian_minor": {
        "notes": [0, 2, 3, 6, 7, 8, 11],
        "culture": "eastern_european",
        "type": "hungarian_minor",
    },
    "phrygian_dominant": {
        "notes": [0, 1, 4, 5, 7, 8, 11],
        "culture": "mediterranean",
        "type": "phrygian_dominant",
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_scale(name: str) -> dict:
    """Look up a scale by name (case-insensitive).

    Raises ``KeyError`` if the scale is not found.
    """
    key = name.lower().replace(" ", "_").replace("-", "_")
    if key not in WORLD_SCALES:
        raise KeyError(f"Unknown scale: {name!r}.  Use list_scales() to see available names.")
    return WORLD_SCALES[key]


def list_scales(culture: str | None = None) -> list[str]:
    """Return scale names, optionally filtered by *culture*."""
    if culture is None:
        return sorted(WORLD_SCALES.keys())
    tag = culture.lower()
    return sorted(k for k, v in WORLD_SCALES.items() if v.get("culture", "").lower() == tag)


def scale_to_midi(scale_name: str, root: int = 60, octave_range: int = 2) -> list[int]:
    """Expand a scale across *octave_range* octaves starting at MIDI *root*.

    Only whole semitone notes are returned (quarter-tone scales are rounded).
    """
    data = get_scale(scale_name)
    midi_notes: list[int] = []
    for octave in range(octave_range):
        offset = octave * 12
        for n in data["notes"]:
            rounded = round(n)
            note = root + rounded + offset
            if 0 <= note <= 127 and note not in midi_notes:
                midi_notes.append(note)
    return sorted(midi_notes)
