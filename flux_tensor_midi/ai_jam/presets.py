"""
Presets: Pre-configured jam sessions with distinct agent personalities.

Five presets, each pairing two AI musicians with contrasting or complementary
constraint profiles.
"""

from __future__ import annotations

from flux_tensor_midi.ai_jam.agent import AIAgent, AgentPersonality
from flux_tensor_midi.ai_jam.session import JamSession, DEFAULT_PROGRESSION


# ---------------------------------------------------------------------------
# Personality definitions
# ---------------------------------------------------------------------------

PARKER = AgentPersonality(
    name="Parker",
    instrument="sax",
    midi_channel=0,
    midi_program=66,  # Alto Sax
    preferred_intervals=(1, 2, 3, 5, 7, 9, 11),  # chromatic + wide
    note_density=4.0,  # fast, dense
    velocity_range=(70, 127),
    rest_probability=0.05,  # rarely rests
    snap_epsilon=0.9,
    direction_change_prob=0.55,  # very angular
    sustain_factor=0.3,  # short articulation
    octave_range=(4, 6),
    consensus_weight=0.6,
)

MILES = AgentPersonality(
    name="Miles",
    instrument="trumpet",
    midi_channel=1,
    midi_program=56,  # Trumpet
    preferred_intervals=(0, 2, 3, 5, 7),  # scalar, lyrical
    note_density=1.2,  # sparse
    velocity_range=(40, 100),
    rest_probability=0.35,  # lots of space
    snap_epsilon=0.5,  # behind/ahead of beat
    direction_change_prob=0.2,  # smooth lines
    sustain_factor=0.85,  # long sustains
    octave_range=(4, 5),
    consensus_weight=0.8,
)

BACH = AgentPersonality(
    name="Bach",
    instrument="organ",
    midi_channel=0,
    midi_program=19,  # Church Organ
    preferred_intervals=(2, 3, 4, 5, 7, 8, 9),  # contrapuntal
    note_density=3.5,
    velocity_range=(60, 100),
    rest_probability=0.05,
    snap_epsilon=0.95,
    direction_change_prob=0.4,
    sustain_factor=0.6,
    octave_range=(3, 6),
    consensus_weight=0.9,
)

VIVALDI = AgentPersonality(
    name="Vivaldi",
    instrument="violin",
    midi_channel=1,
    midi_program=41,  # Violin
    preferred_intervals=(2, 3, 4, 5, 7),  # melodic
    note_density=3.0,
    velocity_range=(50, 120),
    rest_probability=0.1,
    snap_epsilon=0.85,
    direction_change_prob=0.35,
    sustain_factor=0.4,
    octave_range=(4, 6),
    consensus_weight=0.85,
)

COLTRANE = AgentPersonality(
    name="Coltrane",
    instrument="sax",
    midi_channel=0,
    midi_program=67,  # Tenor Sax
    preferred_intervals=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),  # sheets of sound
    note_density=5.0,  # extremely dense
    velocity_range=(65, 125),
    rest_probability=0.03,
    snap_epsilon=0.85,
    direction_change_prob=0.5,
    sustain_factor=0.25,
    octave_range=(3, 6),
    consensus_weight=0.5,
)

MONK = AgentPersonality(
    name="Monk",
    instrument="piano",
    midi_channel=1,
    midi_program=1,  # Piano
    preferred_intervals=(0, 1, 3, 5, 6, 7),  # angular, dissonant
    note_density=2.0,
    velocity_range=(80, 127),  # hits hard
    rest_probability=0.25,  # dramatic pauses
    snap_epsilon=0.7,
    direction_change_prob=0.6,
    sustain_factor=0.5,
    octave_range=(3, 5),
    consensus_weight=0.6,
)

ZAWINUL = AgentPersonality(
    name="Zawinul",
    instrument="keys",
    midi_channel=0,
    midi_program=5,  # Electric Piano
    preferred_intervals=(2, 3, 5, 7, 9, 10),  # dorian/mixolydian
    note_density=3.0,
    velocity_range=(50, 110),
    rest_probability=0.15,
    snap_epsilon=0.8,
    direction_change_prob=0.3,
    sustain_factor=0.6,
    octave_range=(3, 5),
    consensus_weight=0.85,
)

SHORTER = AgentPersonality(
    name="Shorter",
    instrument="sax",
    midi_channel=1,
    midi_program=66,  # Alto Sax
    preferred_intervals=(2, 3, 5, 7, 9, 11),  # wide intervals
    note_density=2.0,
    velocity_range=(40, 100),
    rest_probability=0.2,
    snap_epsilon=0.6,
    direction_change_prob=0.35,
    sustain_factor=0.7,
    octave_range=(4, 6),
    consensus_weight=0.85,
)

NOISE = AgentPersonality(
    name="Noise",
    instrument="synth",
    midi_channel=0,
    midi_program=82,  # Synth Lead
    preferred_intervals=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
    note_density=6.0,  # max chaos
    velocity_range=(30, 127),
    rest_probability=0.02,
    snap_epsilon=0.2,  # very loose timing
    direction_change_prob=0.7,
    sustain_factor=0.15,
    octave_range=(2, 7),  # wide range
    consensus_weight=0.1,  # barely follows consensus
)

DRONE = AgentPersonality(
    name="Drone",
    instrument="bass",
    midi_channel=1,
    midi_program=38,  # Synth Bass
    preferred_intervals=(0, 0, 0, 7),  # mostly root, occasional fifth
    note_density=0.3,  # extremely sparse
    velocity_range=(50, 80),
    rest_probability=0.1,
    snap_epsilon=0.95,
    direction_change_prob=0.02,
    sustain_factor=0.98,  # almost pure sustain
    octave_range=(2, 3),
    consensus_weight=0.95,
)


# ---------------------------------------------------------------------------
# Progressions
# ---------------------------------------------------------------------------

WEATHER_PROGRESSION = [
    ("Dm7", 4),
    ("Em7", 4),
    ("Fmaj7", 4),
    ("Gm7", 4),
    ("Am7", 4),
    ("Bbmaj7", 4),
    ("Cmaj7", 4),
    ("Dm7", 4),
]

NOISE_DRONE_PROGRESSION = [
    ("Dm7", 8),
    ("Dm7", 8),  # static harmony emphasizes the texture contrast
]


# ---------------------------------------------------------------------------
# Preset registry
# ---------------------------------------------------------------------------

_PRESETS: dict[str, dict] = {
    "parker_miles": {
        "description": "Bebop sax × cool jazz trumpet — D Dorian jam",
        "agent1": PARKER,
        "agent2": MILES,
        "bpm": 160,
        "progression": DEFAULT_PROGRESSION,
    },
    "bach_vivaldi": {
        "description": "Baroque counterpoint × baroque melody — contrapuntal dialogue",
        "agent1": BACH,
        "agent2": VIVALDI,
        "bpm": 100,
        "progression": DEFAULT_PROGRESSION,
    },
    "coltrane_monk": {
        "description": "Sheets of sound × angular comping — intense duo",
        "agent1": COLTRANE,
        "agent2": MONK,
        "bpm": 150,
        "progression": DEFAULT_PROGRESSION,
    },
    "weather_report": {
        "description": "Fusion × fusion — high consensus, flowing harmony",
        "agent1": ZAWINUL,
        "agent2": SHORTER,
        "bpm": 120,
        "progression": WEATHER_PROGRESSION,
    },
    "noise_drone": {
        "description": "Pure chaos × pure drone — extreme contrast",
        "agent1": NOISE,
        "agent2": DRONE,
        "bpm": 80,
        "progression": NOISE_DRONE_PROGRESSION,
    },
}


def get_preset(name: str) -> dict:
    """Return a preset dict by name.

    Keys: description, agent1, agent2, bpm, progression.
    """
    if name not in _PRESETS:
        raise ValueError(
            f"Unknown preset {name!r}. Available: {', '.join(_PRESETS)}"
        )
    return _PRESETS[name]


def list_presets() -> list[str]:
    """Return the names of all available presets."""
    return list(_PRESETS.keys())
