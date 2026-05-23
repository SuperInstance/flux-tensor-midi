"""
Conductor — The unified musical intelligence.

Wires together ALL systems into one coherent API:
  - Cultural traditions (world scales, tunings, ornaments, rhythms)
  - Constraint theory (snap, funnel, consensus, laman, tempo)
  - Synthesis (spline wavetable, MIDI output)
  - Analysis (cohomology-inspired harmonic analysis, hyperbolic genre)
  - Evolution (genome music)
  - Aperiodic geometry (Penrose music)

Usage:
    from flux_tensor_midi.conductor import Conductor

    c = Conductor.preset('midnight_raga')
    arr = c.compose(bars=8)
    c.render_midi(arr, 'output.mid')

    # Or natural language:
    c = Conductor()
    arr = c.quick('Indian raga Darbari in Jhaptaal')
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.core.clock import TZeroClock
from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.snap import EisensteinSnap, EisensteinRatio, RhythmicRole
from flux_tensor_midi.tracks import Arrangement, Track
from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.genre_brain import GenreBrain
from flux_tensor_midi.analyzer import FluxAnalyzer, AnalysisReport
from flux_tensor_midi.world.scales import get_scale, list_scales, scale_to_midi, WORLD_SCALES
from flux_tensor_midi.world.tuning_systems import (
    equal_temperament, just_intonation, shruti_22, quarter_tone_24,
    pentatonic_5, meantone, pythagorean, snap_to_tuning,
)
from flux_tensor_midi.world.ornaments import meend, gamak, quarter_bend, grace_note, murki, shakes
from flux_tensor_midi.world.rhythms import clave, bell_pattern, tala, iqa, swing_ratio
from flux_tensor_midi.midi_writer import MidiFileWriter

# Optional imports — these may not be available in all environments
try:
    from flux_tensor_midi.hyperbolic_genre import HyperbolicGenreMap, GenrePoint
    _HAS_HYPERBOLIC = True
except ImportError:
    _HAS_HYPERBOLIC = False

try:
    from flux_tensor_midi.genome_music import (
        MusicalGenome, GenomePlayer, MusicalEvolution, EvolutionResult,
        evaluate_fitness, GENRE_TARGETS,
    )
    _HAS_GENOME = True
except ImportError:
    _HAS_GENOME = False

try:
    from penrose import (
        CutAndProjectCompiler, PenroseMusicGenerator, ThueMorseMelody,
        fibonacci_groove, golden_phrase, PenroseEvent, events_to_midi_bytes,
    )
    _HAS_PENROSE = True
except ImportError:
    _HAS_PENROSE = False

try:
    from spline_synth import SplineWavetable
    _HAS_SPLINE = True
except ImportError:
    _HAS_SPLINE = False


# ---------------------------------------------------------------------------
# ConstraintProfile
# ---------------------------------------------------------------------------

@dataclass
class ConstraintProfile:
    """Musical constraint parameters governing composition."""
    snap_strength: float = 0.5       # Eisenstein snap tightness [0, 1]
    funnel_gravity: float = 50.0     # Tonal gravity (epsilon_0)
    consensus_weight: float = 0.4    # Ensemble coupling (alpha)
    laman_threshold: float = 0.5     # Structural rigidity (edge density)
    bpm: float = 120.0               # Tempo
    swing_ratio: float = 0.5         # 0.5=straight, 0.67=triplet swing
    rubato: float = 0.0              # Timing flexibility
    grid_resolution: int = 4         # Subdivision grid

    def to_dict(self) -> Dict[str, float]:
        return {
            'snap_strength': self.snap_strength,
            'funnel_gravity': self.funnel_gravity,
            'consensus_weight': self.consensus_weight,
            'laman_threshold': self.laman_threshold,
            'bpm': self.bpm,
            'swing_ratio': self.swing_ratio,
            'rubato': self.rubato,
            'grid_resolution': float(self.grid_resolution),
        }


# ---------------------------------------------------------------------------
# Cultural defaults
# ---------------------------------------------------------------------------

_CULTURE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    'indian': {
        'scale': 'bhairavi',
        'tuning': 'shruti',
        'rhythm': 'teental',
        'genre': 'Raga',
        'bpm': 80.0,
        'ornaments': ['meend', 'gamak'],
        'swing': 0.5,
        'grid': 4,
    },
    'arabic': {
        'scale': 'rast',
        'tuning': 'quarter_tone',
        'rhythm': 'maqsum',
        'genre': 'Maqam',
        'bpm': 100.0,
        'ornaments': ['quarter_bend', 'grace_note'],
        'swing': 0.5,
        'grid': 4,
    },
    'east_asian': {
        'scale': 'in_scale',
        'tuning': 'pentatonic',
        'rhythm': 'teental',
        'genre': 'Gagaku',
        'bpm': 60.0,
        'ornaments': ['grace_note'],
        'swing': 0.5,
        'grid': 3,
    },
    'west_african': {
        'scale': 'ewe_standard',
        'tuning': 'equal_temperament',
        'rhythm': 'agbadza',
        'genre': 'Polyrhythm',
        'bpm': 120.0,
        'ornaments': ['shakes'],
        'swing': 0.55,
        'grid': 4,
    },
    'western': {
        'scale': 'pentatonic_major',
        'tuning': 'equal_temperament',
        'rhythm': 'son_2_3',
        'genre': 'Jazz',
        'bpm': 120.0,
        'ornaments': ['shakes'],
        'swing': 0.5,
        'grid': 4,
    },
}

_TUNING_MAP: Dict[str, Any] = {
    'equal_temperament': equal_temperament,
    'just_intonation': just_intonation,
    'shruti': shruti_22,
    'quarter_tone': quarter_tone_24,
    'pentatonic': pentatonic_5,
    'meantone': meantone,
    'pythagorean': pythagorean,
}

# Indian raga presets (subset of WORLD_SCALES + tala)
_RAGA_PRESETS: Dict[str, Dict[str, Any]] = {
    'bhairavi': {'tala': 'teental', 'tempo': 'vilambit'},
    'yaman': {'tala': 'teental', 'tempo': 'madhya'},
    'darbari': {'tala': 'jhap_tal', 'tempo': 'vilambit'},
    'malkauns': {'tala': 'teental', 'tempo': 'madhya'},
    'bageshri': {'tala': 'rupak', 'tempo': 'madhya'},
    'todi': {'tala': 'teental', 'tempo': 'vilambit'},
    'bhairav': {'tala': 'teental', 'tempo': 'vilambit'},
    'kafi': {'tala': 'dadra', 'tempo': 'madhya'},
    'bilawal': {'tala': 'teental', 'tempo': 'drut'},
    'asavari': {'tala': 'teental', 'tempo': 'madhya'},
}

# Arabic maqam presets
_MAQAM_PRESETS: Dict[str, Dict[str, Any]] = {
    'rast': {'iqa': 'maqsum', 'bpm': 100},
    'bayati': {'iqa': 'baladi', 'bpm': 110},
    'hijaz': {'iqa': 'maqsum', 'bpm': 90},
    'sikah': {'iqa': 'sama_i_thaqil', 'bpm': 80},
    'nahawand': {'iqa': 'maqsum', 'bpm': 100},
    'kurd': {'iqa': 'malfuf', 'bpm': 95},
    'ajam': {'iqa': 'maqsum', 'bpm': 110},
    'saba': {'iqa': 'saidi', 'bpm': 90},
    'huzam': {'iqa': 'aqsaq', 'bpm': 85},
    'nakriz': {'iqa': 'maqsum', 'bpm': 100},
}

# East Asian pentatonic presets
_PENTATONIC_PRESETS: Dict[str, Dict[str, Any]] = {
    'in_scale': {'culture': 'japanese', 'mood': 'melancholy', 'bpm': 60},
    'yo_scale': {'culture': 'japanese', 'mood': 'bright', 'bpm': 72},
    'hirajoshi': {'culture': 'japanese', 'mood': 'tense', 'bpm': 66},
    'kumoi': {'culture': 'japanese', 'mood': 'ethereal', 'bpm': 58},
    'gong_mode': {'culture': 'chinese', 'mood': 'regal', 'bpm': 64},
    'shang_mode': {'culture': 'chinese', 'mood': 'clear', 'bpm': 68},
    'jiao_mode': {'culture': 'chinese', 'mood': 'gentle', 'bpm': 62},
    'zhi_mode': {'culture': 'chinese', 'mood': 'bright', 'bpm': 70},
    'yu_mode': {'culture': 'chinese', 'mood': 'flowing', 'bpm': 56},
}

# West African polyrhythm presets
_POLYRHYTHM_PRESETS: Dict[str, Dict[str, Any]] = {
    'agbadza': {'bell': 'agbadza', 'scale': 'ewe_standard', 'bpm': 120},
    'gahu': {'bell': 'gahu', 'scale': 'ewe_standard', 'bpm': 116},
    'atsiagbekor': {'bell': 'atsiagbekor', 'scale': 'ewe_standard', 'bpm': 130},
    'kinka': {'bell': 'kinka', 'scale': 'pentatonic_african', 'bpm': 140},
    'yanvalou': {'bell': 'yanvalou', 'scale': 'ewe_standard', 'bpm': 100},
}

# Named conductor presets
_CONDUCTOR_PRESETS: Dict[str, Dict[str, Any]] = {
    'midnight_raga': {
        'culture': 'indian', 'scale': 'bhairavi', 'tuning': 'shruti',
        'rhythm': 'teental', 'genre': 'Raga', 'bpm': 40,
        'ornaments': ['meend', 'gamak'],
    },
    'cairo_cafe': {
        'culture': 'arabic', 'scale': 'rast', 'tuning': 'quarter_tone',
        'rhythm': 'maqsum', 'genre': 'Maqam', 'bpm': 100,
        'ornaments': ['quarter_bend', 'grace_note'],
    },
    'zen_garden': {
        'culture': 'east_asian', 'scale': 'in_scale', 'tuning': 'pentatonic',
        'rhythm': 'teental', 'genre': 'Gagaku', 'bpm': 48,
        'ornaments': ['grace_note'],
    },
    'djembe_circle': {
        'culture': 'west_african', 'scale': 'ewe_standard', 'tuning': 'equal_temperament',
        'rhythm': 'agbadza', 'genre': 'Polyrhythm', 'bpm': 120,
        'ornaments': ['shakes'],
    },
    'bebop_salt': {
        'culture': 'western', 'scale': 'pentatonic_major', 'tuning': 'equal_temperament',
        'rhythm': 'son_2_3', 'genre': 'Jazz', 'bpm': 180,
        'ornaments': ['shakes'],
    },
    'bach_fugue': {
        'culture': 'western', 'scale': 'pentatonic_major', 'tuning': 'meantone',
        'rhythm': 'teental', 'genre': 'Baroque', 'bpm': 72,
        'ornaments': [],
    },
    'penrose_dance': {
        'culture': 'western', 'scale': 'pentatonic_major', 'tuning': 'equal_temperament',
        'rhythm': 'son_2_3', 'genre': 'IDM', 'bpm': 120,
        'ornaments': [], 'penrose': True,
    },
    'evolved_hybrid': {
        'culture': 'western', 'scale': 'pentatonic_major', 'tuning': 'equal_temperament',
        'rhythm': 'son_2_3', 'genre': 'Jazz', 'bpm': 120,
        'ornaments': [], 'evolve': True,
    },
    'hyperbolic_exploration': {
        'culture': 'western', 'scale': 'pentatonic_major', 'tuning': 'equal_temperament',
        'rhythm': 'son_2_3', 'genre': 'Jazz', 'bpm': 120,
        'ornaments': [], 'hyperbolic_walk': True,
    },
    'quasicrystal': {
        'culture': 'western', 'scale': 'pentatonic_major', 'tuning': 'equal_temperament',
        'rhythm': 'son_2_3', 'genre': 'Ambient', 'bpm': 80,
        'ornaments': [], 'penrose': True, 'penrose_preset': 'fibonacci_groove',
    },
}

# Tempo markings
_TEMPO_MAP: Dict[str, float] = {
    'vilambit': 40.0,    # slow
    'madhya': 100.0,     # medium
    'drut': 160.0,       # fast
    'ati_drut': 220.0,   # very fast
}


# ---------------------------------------------------------------------------
# Conductor
# ---------------------------------------------------------------------------

class Conductor:
    """The unified musical intelligence.

    Wires together:
    - Cultural traditions (world scales, tunings, ornaments, rhythms)
    - Constraint theory (snap, funnel, consensus, laman, tempo)
    - Synthesis (spline wavetable, MIDI output)
    - Analysis (cohomology-inspired harmonic emergence detection, hyperbolic genre)
    - Evolution (genome music)
    - Aperiodic geometry (Penrose music)

    Parameters
    ----------
    culture : str, optional
        Cultural tradition: 'indian', 'arabic', 'east_asian', 'west_african', 'western'.
    genre : str, optional
        Genre name for hyperbolic genre map or genre brain.
    scale : str, optional
        Scale name from 36 world scales.
    tuning : str, optional
        Tuning system: 'equal_temperament', 'just_intonation', 'shruti',
        'quarter_tone', 'pentatonic', 'meantone', 'pythagorean'.
    rhythm : str, optional
        Rhythm pattern name.
    constraints : ConstraintProfile, optional
        Musical constraint parameters.
    seed : int, optional
        Random seed for reproducibility.
    """

    def __init__(
        self,
        culture: Optional[str] = None,
        genre: Optional[str] = None,
        scale: Optional[str] = None,
        tuning: Optional[str] = None,
        rhythm: Optional[str] = None,
        constraints: Optional[ConstraintProfile] = None,
        seed: Optional[int] = None,
    ):
        # Cultural context
        self.culture = culture
        self.genre = genre
        self.scale_name = scale
        self.tuning_name = tuning
        self.rhythm_name = rhythm
        self.constraints = constraints or ConstraintProfile()
        self.seed = seed

        # Derived state
        self._scale_data: Optional[Dict[str, Any]] = None
        self._tuning_cents: Optional[List[float]] = None
        self._rhythm_data: Optional[Dict[str, Any]] = None
        self._ornament_names: List[str] = []

        # Lazy-initialized subsystems
        self._genre_map: Optional[Any] = None  # HyperbolicGenreMap
        self._spline: Optional[Any] = None     # SplineWavetable
        self._evolution_result: Optional[Any] = None  # EvolutionResult

        # Load scale if provided
        if self.scale_name:
            self._load_scale(self.scale_name)
        if self.tuning_name:
            self._load_tuning(self.tuning_name)
        if self.rhythm_name:
            self._load_rhythm(self.rhythm_name)

    # === Private loaders ===

    def _load_scale(self, name: str) -> None:
        """Load scale data by name."""
        try:
            self._scale_data = get_scale(name)
        except KeyError:
            # Try case-insensitive match
            key = name.lower().replace(" ", "_").replace("-", "_")
            if key in WORLD_SCALES:
                self._scale_data = WORLD_SCALES[key]
            else:
                self._scale_data = None

    def _load_tuning(self, name: str) -> None:
        """Load tuning system by name."""
        factory = _TUNING_MAP.get(name)
        if factory is not None:
            self._tuning_cents = factory()
        elif name == 'equal_temperament':
            self._tuning_cents = equal_temperament()
        else:
            self._tuning_cents = equal_temperament()

    def _load_rhythm(self, name: str) -> None:
        """Load rhythm data by name (tries tala, iqa, clave, bell)."""
        # Try Indian tala
        try:
            self._rhythm_data = tala(name)
            self._rhythm_data['type'] = 'tala'
            return
        except KeyError:
            pass
        # Try Arabic iqa
        try:
            self._rhythm_data = iqa(name)
            self._rhythm_data['type'] = 'iqa'
            return
        except KeyError:
            pass
        # Try bell pattern
        try:
            pattern = bell_pattern(name)
            self._rhythm_data = {'hits': pattern, 'type': 'bell'}
            return
        except KeyError:
            pass
        # Try clave
        try:
            pattern = clave(name)
            self._rhythm_data = {'hits': pattern, 'type': 'clave'}
            return
        except KeyError:
            pass

    def _get_genre_map(self) -> Any:
        """Get or create the HyperbolicGenreMap."""
        if self._genre_map is None and _HAS_HYPERBOLIC:
            self._genre_map = HyperbolicGenreMap()
        return self._genre_map

    def _get_spline(self) -> Any:
        """Get or create the SplineWavetable."""
        if self._spline is None and _HAS_SPLINE:
            self._spline = SplineWavetable(n_control_points=16, table_length=2048)
        return self._spline

    def _make_arrangement(
        self,
        name: str,
        bpm: float,
        bars: int,
        voices: List[Tuple[str, RhythmicRole, str]],
    ) -> Arrangement:
        """Create an Arrangement with the given voices."""
        arr = Arrangement(name=name, bpm=bpm, bars=bars, seed=self.seed)
        for vname, role, voice in voices:
            t = Track(vname, role, voice, bpm=bpm, seed=self.seed)
            arr.add_track(t)
        return arr

    # === Cultural Selection ===

    def set_culture(self, culture: str) -> 'Conductor':
        """Set culture and auto-configure all parameters.

        Configures scale, tuning, rhythm, ornaments, and constraints
        from cultural defaults.

        Parameters
        ----------
        culture : str
            One of: 'indian', 'arabic', 'east_asian', 'west_african', 'western'.

        Returns
        -------
        Conductor
            self, for chaining.
        """
        culture_key = culture.lower().replace('-', '_')
        if culture_key not in _CULTURE_DEFAULTS:
            raise ValueError(
                f"Unknown culture: {culture!r}. "
                f"Available: {list(_CULTURE_DEFAULTS.keys())}"
            )
        defaults = _CULTURE_DEFAULTS[culture_key]
        self.culture = culture_key
        self.scale_name = defaults['scale']
        self.tuning_name = defaults['tuning']
        self.rhythm_name = defaults['rhythm']
        self.genre = defaults.get('genre')
        self._ornament_names = defaults.get('ornaments', [])
        self._load_scale(self.scale_name)
        self._load_tuning(self.tuning_name)
        self._load_rhythm(self.rhythm_name)
        self.constraints.bpm = defaults['bpm']
        self.constraints.swing_ratio = defaults.get('swing', 0.5)
        self.constraints.grid_resolution = defaults.get('grid', 4)
        return self

    def set_scale(self, name: str) -> 'Conductor':
        """Set scale from 36 world scales. Auto-tunes to match.

        Parameters
        ----------
        name : str
            Scale name (e.g., 'bhairavi', 'rast', 'in_scale', 'pelog').

        Returns
        -------
        Conductor
            self, for chaining.
        """
        self.scale_name = name
        self._load_scale(name)
        # Auto-tune: if the scale is Indian, use shruti; if Arabic with quarter tones,
        # use quarter_tone; otherwise equal temperament
        if self._scale_data:
            sc = self._scale_data.get('culture', '')
            if sc == 'indian' and self.tuning_name != 'shruti':
                self.tuning_name = 'shruti'
                self._load_tuning('shruti')
            elif sc == 'arabic' and self._scale_data.get('quarter_tones'):
                if self.tuning_name != 'quarter_tone':
                    self.tuning_name = 'quarter_tone'
                    self._load_tuning('quarter_tone')
        return self

    def set_raga(self, name: str) -> 'Conductor':
        """Set Indian raga: scale, shruti tuning, ornaments (meend/gamak), tala.

        Parameters
        ----------
        name : str
            Raga name (e.g., 'bhairavi', 'darbari', 'yaman').

        Returns
        -------
        Conductor
            self, for chaining.
        """
        self.culture = 'indian'
        self.scale_name = name
        self.tuning_name = 'shruti'
        self._ornament_names = ['meend', 'gamak']
        self._load_scale(name)
        self._load_tuning('shruti')

        # Configure raga-specific parameters
        preset = _RAGA_PRESETS.get(name, {})
        tala_name = preset.get('tala', 'teental')
        tempo_marking = preset.get('tempo', 'madhya')
        self.rhythm_name = tala_name
        self._load_rhythm(tala_name)
        self.constraints.bpm = _TEMPO_MAP.get(tempo_marking, 100.0)
        self.constraints.swing_ratio = 0.5
        self.genre = 'Raga'
        return self

    def set_maqam(self, name: str) -> 'Conductor':
        """Set Arabic maqam: 24-tone scale, quarter-tone tuning, iqa' rhythm.

        Parameters
        ----------
        name : str
            Maqam name (e.g., 'rast', 'bayati', 'hijaz').

        Returns
        -------
        Conductor
            self, for chaining.
        """
        self.culture = 'arabic'
        self.scale_name = name
        self.tuning_name = 'quarter_tone'
        self._ornament_names = ['quarter_bend', 'grace_note']
        self._load_scale(name)
        self._load_tuning('quarter_tone')

        # Configure maqam-specific parameters
        preset = _MAQAM_PRESETS.get(name, {})
        iqa_name = preset.get('iqa', 'maqsum')
        self.rhythm_name = iqa_name
        self._load_rhythm(iqa_name)
        self.constraints.bpm = preset.get('bpm', 100.0)
        self.genre = 'Maqam'
        return self

    def set_pentatonic(self, name: str) -> 'Conductor':
        """Set East Asian pentatonic: 5-note scale, ma silence, jo-ha-kyu.

        Parameters
        ----------
        name : str
            Pentatonic scale name (e.g., 'in_scale', 'yo_scale', 'gong_mode').

        Returns
        -------
        Conductor
            self, for chaining.
        """
        self.culture = 'east_asian'
        self.scale_name = name
        self.tuning_name = 'pentatonic'
        self._ornament_names = ['grace_note']
        self._load_scale(name)
        self._load_tuning('pentatonic')

        preset = _PENTATONIC_PRESETS.get(name, {})
        self.constraints.bpm = preset.get('bpm', 60.0)
        self.genre = 'Gagaku'
        return self

    def set_polyrhythm(self, name: str) -> 'Conductor':
        """Set West African: bell pattern, drum layers, polyrhythmic ratios.

        Parameters
        ----------
        name : str
            Polyrhythm/bell pattern name (e.g., 'agbadza', 'gahu', 'kinka').

        Returns
        -------
        Conductor
            self, for chaining.
        """
        self.culture = 'west_african'
        self._ornament_names = ['shakes']

        preset = _POLYRHYTHM_PRESETS.get(name, {})
        self.scale_name = preset.get('scale', 'ewe_standard')
        self.tuning_name = 'equal_temperament'
        self.rhythm_name = name
        self._load_scale(self.scale_name)
        self._load_tuning('equal_temperament')
        self._load_rhythm(name)
        self.constraints.bpm = preset.get('bpm', 120.0)
        self.constraints.swing_ratio = 0.55
        self.genre = 'Polyrhythm'
        return self

    # === Genre Navigation ===

    def blend_genres(self, *genres: str, weights: Optional[List[float]] = None) -> 'Conductor':
        """Blend genres via Fréchet mean on Poincaré ball.

        Parameters
        ----------
        *genres : str
            Genre names to blend.
        weights : list of float, optional
            Blend weights (must sum to 1.0).

        Returns
        -------
        Conductor
            self, for chaining.
        """
        gm = self._get_genre_map()
        if gm is None:
            raise ImportError("HyperbolicGenreMap requires flux_hyperbolic")
        blended = gm.multi_blend(list(genres), weights)
        constraints = gm.decode_to_constraints(blended)
        self.constraints.snap_strength = constraints.get('timing_tightness', 0.5)
        self.constraints.bpm = 40 + constraints.get('rhythmic_intensity', 0.5) * 200
        self.constraints.swing_ratio = 0.3 + constraints.get('angularity', 0.5) * 0.5
        self.genre = '+'.join(genres)
        return self

    def explore_nearby(self, n: int = 5) -> List[Tuple[str, float]]:
        """Find n nearest genres in hyperbolic space.

        Parameters
        ----------
        n : int
            Number of nearby genres to return.

        Returns
        -------
        list of (genre_name, distance) tuples.
        """
        gm = self._get_genre_map()
        if gm is None:
            raise ImportError("HyperbolicGenreMap requires flux_hyperbolic")
        target = self.genre or 'Jazz'
        return gm.nearest_genres(target, n=n)

    def genre_walk(self, steps: int = 10, step_size: float = 0.1) -> List[Tuple[str, np.ndarray]]:
        """Random walk through genre space.

        Parameters
        ----------
        steps : int
            Number of walk steps.
        step_size : float
            Size of each step in hyperbolic space.

        Returns
        -------
        list of (genre_name, coords) for each step.
        """
        gm = self._get_genre_map()
        if gm is None:
            raise ImportError("HyperbolicGenreMap requires flux_hyperbolic")
        rng = np.random.default_rng(self.seed)
        start = self.genre or 'Jazz'
        results = []
        current = start
        for _ in range(steps):
            new_point, nearest = gm.genre_walk(current, step_size=step_size, rng=rng)
            results.append((nearest, new_point))
            current = nearest
        return results

    # === Composition ===

    def compose(self, bars: int = 8, bpm: Optional[float] = None) -> Arrangement:
        """Generate a full arrangement using all active constraints.

        Uses: scale, rhythm, constraints, ornaments, tuning.
        Applies: snap (to chosen lattice), funnel (tonal gravity),
                 consensus (ensemble agreement), laman (structural rigidity).

        Parameters
        ----------
        bars : int
            Number of bars to compose.
        bpm : float, optional
            Override tempo.

        Returns
        -------
        Arrangement
            Ready for MIDI export or audio rendering.
        """
        actual_bpm = bpm or self.constraints.bpm
        name = f"conductor_{self.culture or 'default'}_{self.genre or 'generic'}"

        # Select voices based on cultural context
        voices = self._default_voices()
        arr = self._make_arrangement(name, actual_bpm, bars, voices)
        arr.generate_all()

        # Apply tuning if available
        if self._tuning_cents and self._scale_data:
            self._apply_tuning_to_arrangement(arr)

        return arr

    def compose_raga(
        self,
        raga: Optional[str] = None,
        tala_name: str = 'teental',
        tempo: str = 'madhya',
    ) -> Arrangement:
        """Full raga composition with aroha/avaroha, pakad, vadi gravity.

        Parameters
        ----------
        raga : str, optional
            Raga name. Uses current if not provided.
        tala_name : str
            Tala name (default 'teental').
        tempo : str
            Tempo marking: 'vilambit', 'madhya', 'drut', 'ati_drut'.

        Returns
        -------
        Arrangement
        """
        if raga:
            self.set_raga(raga)
        if not self.scale_name:
            self.set_raga('bhairavi')

        bpm = _TEMPO_MAP.get(tempo, 100.0)
        self.rhythm_name = tala_name
        self._load_rhythm(tala_name)

        # Create arrangement with raga-appropriate voices
        voices = [
            ('tanpura', RhythmicRole.ROOT, 'bass'),
            ('sitar', RhythmicRole.ROOT, 'lead'),
            ('tabla', RhythmicRole.HALFTIME, 'drums'),
        ]
        arr = self._make_arrangement(
            f"raga_{self.scale_name}", bpm, bars=8, voices=voices
        )
        arr.generate_all()
        return arr

    def compose_maqam(
        self,
        maqam: Optional[str] = None,
        iqa_name: str = 'maqsum',
        bpm: float = 100.0,
    ) -> Arrangement:
        """Full maqam composition with sayr, modulation chain, tarab.

        Parameters
        ----------
        maqam : str, optional
            Maqam name. Uses current if not provided.
        iqa_name : str
            Iqa' pattern name.
        bpm : float
            Tempo in BPM.

        Returns
        -------
        Arrangement
        """
        if maqam:
            self.set_maqam(maqam)
        if not self.scale_name:
            self.set_maqam('rast')

        self.rhythm_name = iqa_name
        self._load_rhythm(iqa_name)

        voices = [
            ('oud', RhythmicRole.ROOT, 'lead'),
            ('qanun', RhythmicRole.OFFSET, 'piano'),
            ('darbuka', RhythmicRole.HALFTIME, 'drums'),
        ]
        arr = self._make_arrangement(
            f"maqam_{self.scale_name}", bpm, bars=8, voices=voices
        )
        arr.generate_all()
        return arr

    def compose_penrose(self, preset: str = 'fibonacci_groove', bars: int = 8) -> Arrangement:
        """Aperiodic composition from Penrose tiling.

        Parameters
        ----------
        preset : str
            Penrose preset: 'fibonacci_groove', 'golden_phrase', 'cut_and_project'.
        bars : int
            Number of bars.

        Returns
        -------
        Arrangement
        """
        if not _HAS_PENROSE:
            raise ImportError("Penrose module not available")

        # Generate penrose events
        if preset == 'fibonacci_groove':
            penrose_events = fibonacci_groove(bars=bars, subdivision=16)
        elif preset == 'golden_phrase':
            penrose_events = golden_phrase(n_notes=bars * 16, base_pitch=60)
        else:
            compiler = CutAndProjectCompiler(source_dim=5, target_dim=2)
            compiler.with_golden_projection()
            tiles = compiler.compile(lattice_range=10)
            gen = PenroseMusicGenerator(tiles)
            penrose_events = gen.generate()

        # Convert PenroseEvent to MidiEvent and create Arrangement
        arr = Arrangement(name=f"penrose_{preset}", bpm=self.constraints.bpm, bars=bars)
        midi_events: List[MidiEvent] = []
        beat_ms = 60000.0 / self.constraints.bpm
        for pe in penrose_events:
            midi_events.append(MidiEvent(
                note=max(0, min(127, pe.pitch)),
                velocity=max(1, min(127, pe.velocity)),
                start_ms=pe.time * beat_ms,
                duration_ms=max(10, pe.duration * beat_ms),
                channel=pe.channel,
            ))

        # Create a single track with all events
        t = Track('penrose', RhythmicRole.ROOT, 'arp', bpm=self.constraints.bpm, seed=self.seed)
        t._events = midi_events
        arr.add_track(t)
        return arr

    def compose_counterpoint(
        self,
        species: int = 1,
        cantus_firmus: Optional[List[int]] = None,
        bars: int = 8,
    ) -> Arrangement:
        """Species counterpoint composition.

        Parameters
        ----------
        species : int
            Counterpoint species (1-5).
        cantus_firmus : list of int, optional
            Cantus firmus as MIDI note list.
        bars : int
            Number of bars.

        Returns
        -------
        Arrangement
        """
        if cantus_firmus is None:
            # Generate a simple cantus firmus using current scale
            scale_notes = [60]
            if self._scale_data:
                scale_notes = scale_to_midi(self.scale_name or 'pentatonic_major', root=60, octave_range=1)
            rng = np.random.default_rng(self.seed)
            cantus_firmus = list(rng.choice(scale_notes, size=min(bars, len(scale_notes))))

        bpm = self.constraints.bpm
        arr = Arrangement(name='counterpoint', bpm=bpm, bars=bars)

        # Cantus firmus track
        cf_track = Track('cantus_firmus', RhythmicRole.ROOT, 'piano', bpm=bpm, seed=self.seed)
        cf_events: List[MidiEvent] = []
        beat_ms = 60000.0 / bpm
        for i, note in enumerate(cantus_firmus):
            cf_events.append(MidiEvent(
                note=note, velocity=80, start_ms=i * beat_ms * 4,
                duration_ms=beat_ms * 3.5, channel=0,
            ))
        cf_track._events = cf_events
        arr.add_track(cf_track)

        # Counterpoint track(s)
        for voice_idx in range(species):
            cp_track = Track(
                f'counterpoint_{voice_idx + 1}',
                RhythmicRole.OFFSET,
                'strings',
                bpm=bpm, seed=self.seed,
            )
            cp_events: List[MidiEvent] = []
            for i, cf_note in enumerate(cantus_firmus):
                # Simple interval: alternate 3rds, 5ths, 6ths
                intervals = [3, 5, 6, 8, 4]
                interval = intervals[(i + voice_idx) % len(intervals)]
                direction = 1 if voice_idx % 2 == 0 else -1
                cp_note = max(0, min(127, cf_note + direction * interval))

                if species == 1:
                    # Note against note
                    cp_events.append(MidiEvent(
                        note=cp_note, velocity=70,
                        start_ms=i * beat_ms * 4,
                        duration_ms=beat_ms * 3.5, channel=voice_idx + 1,
                    ))
                elif species == 2:
                    # Two notes against one
                    for j in range(2):
                        cp_events.append(MidiEvent(
                            note=cp_note + j * 2,
                            velocity=65,
                            start_ms=i * beat_ms * 4 + j * beat_ms * 2,
                            duration_ms=beat_ms * 1.8,
                            channel=voice_idx + 1,
                        ))
                else:
                    # Higher species: more elaborate
                    for j in range(species):
                        cp_events.append(MidiEvent(
                            note=cp_note + j,
                            velocity=60,
                            start_ms=i * beat_ms * 4 + j * beat_ms * 4 / species,
                            duration_ms=beat_ms * 4 / species * 0.9,
                            channel=voice_idx + 1,
                        ))
            cp_track._events = cp_events
            arr.add_track(cp_track)

        return arr

    # === Evolution ===

    def evolve(
        self,
        target_genre: Optional[str] = None,
        generations: int = 50,
        population: int = 100,
    ) -> 'Conductor':
        """Evolve genome toward target genre. Returns self for chaining.

        Parameters
        ----------
        target_genre : str, optional
            Target genre for evolution (e.g., 'jazz', 'classical').
        generations : int
            Number of evolutionary generations.
        population : int
            Population size per generation.

        Returns
        -------
        Conductor
            self, for chaining.
        """
        if not _HAS_GENOME:
            raise ImportError("Genome music module not available")

        genre = target_genre or self.genre or 'jazz'
        # Map hyperbolic genre names to genome targets
        genre_key = genre.lower()
        if genre_key not in GENRE_TARGETS:
            # Try mapping from hyperbolic genre to closest genome target
            mapping = {
                'jazz': 'jazz', 'bebop': 'jazz', 'swing': 'jazz',
                'classical': 'classical', 'baroque': 'classical',
                'romantic': 'classical', 'minimalism': 'classical',
                'electronic': 'electronic', 'techno': 'electronic',
                'ambient': 'ambient', 'house': 'electronic',
                'hiphop': 'hiphop', 'hip-hop': 'hiphop', 'trap': 'hiphop',
            }
            genre_key = mapping.get(genre_key, 'jazz')

        evo = MusicalEvolution(
            target_genre=genre_key,
            population_size=population,
            seed=self.seed,
        )
        self._evolution_result = evo.run(generations=generations)

        # Apply evolved constraints
        best = self._evolution_result.best_config
        self.constraints.snap_strength = best.get('snap_strength', 0.5)
        self.constraints.funnel_gravity = best.get('epsilon_0', 50.0)
        self.constraints.consensus_weight = best.get('coupling_alpha', 0.4)
        self.constraints.laman_threshold = best.get('edge_density', 0.5)
        self.constraints.bpm = best.get('bpm', 120.0)
        self.constraints.swing_ratio = best.get('swing_ratio', 0.5)
        self.constraints.rubato = best.get('rubato_extent', 0.0)

        return self

    def evolve_cross_cultural(
        self,
        culture_a: str,
        culture_b: str,
        generations: int = 50,
    ) -> 'Conductor':
        """Evolve a hybrid of two cultural traditions.

        Parameters
        ----------
        culture_a : str
            First culture ('indian', 'arabic', etc.).
        culture_b : str
            Second culture.
        generations : int
            Number of generations.

        Returns
        -------
        Conductor
            self, for chaining.
        """
        if not _HAS_GENOME:
            raise ImportError("Genome music module not available")

        # Create genomes from both cultures and cross-breed
        defaults_a = _CULTURE_DEFAULTS.get(culture_a, {})
        defaults_b = _CULTURE_DEFAULTS.get(culture_b, {})

        # Evolve with first culture's genre, then blend
        genre_a = defaults_a.get('genre', 'jazz')
        genre_key = 'jazz'
        mapping = {
            'jazz': 'jazz', 'classical': 'classical',
            'electronic': 'electronic', 'ambient': 'ambient',
            'hiphop': 'hiphop',
        }
        for g in [genre_a, defaults_b.get('genre', '')]:
            gk = mapping.get(g.lower(), '')
            if gk:
                genre_key = gk
                break

        evo = MusicalEvolution(
            target_genre=genre_key,
            population_size=100,
            seed=self.seed,
        )
        self._evolution_result = evo.run(generations=generations)

        # Apply with blended BPM
        bpm_a = defaults_a.get('bpm', 120.0)
        bpm_b = defaults_b.get('bpm', 120.0)
        self.constraints.bpm = (bpm_a + bpm_b) / 2.0

        # Apply evolved constraints
        best = self._evolution_result.best_config
        self.constraints.snap_strength = best.get('snap_strength', 0.5)
        self.constraints.funnel_gravity = best.get('epsilon_0', 50.0)
        self.constraints.consensus_weight = best.get('coupling_alpha', 0.4)
        self.constraints.bpm = best.get('bpm', self.constraints.bpm)
        self.constraints.swing_ratio = best.get('swing_ratio', 0.5)

        self.culture = f"{culture_a}_{culture_b}_hybrid"
        self.genre = genre_a
        return self

    # === Analysis ===

    def analyze(self, arrangement: Arrangement) -> Dict[str, Any]:
        """Full analysis: constraint satisfaction, cultural metrics.

        Parameters
        ----------
        arrangement : Arrangement
            Arrangement to analyze.

        Returns
        -------
        dict
            Analysis results including constraint metrics and cultural authenticity.
        """
        events = arrangement.to_midi_events()
        analyzer = FluxAnalyzer()
        report = analyzer.from_midi_events(events) if events else AnalysisReport()

        result = {
            'summary': report.summary(),
            'constraint_satisfaction': self._constraint_satisfaction(arrangement),
            'cultural_metrics': self._cultural_metrics(arrangement),
            'track_count': len(arrangement.tracks),
            'total_events': sum(len(t.events) for t in arrangement.tracks),
        }
        return result

    def analyze_cohomology(self, arrangement: Arrangement) -> Dict[str, Any]:
        """Compute harmonic emergence analysis (cohomology-inspired).

        Computes H0 (connected components of harmonic similarity graph)
        and H1 (cycles in voice-leading space) as musical cohomology.

        Parameters
        ----------
        arrangement : Arrangement
            Arrangement to analyze.

        Returns
        -------
        dict with H0, H1, emergence_score, harmonic_complexity.
        """
        events = arrangement.to_midi_events()
        if not events:
            return {'H0': 0, 'H1': 0, 'emergence_score': 0.0, 'harmonic_complexity': 0.0}

        # Build pitch-class set
        from collections import Counter
        pc_set = Counter(e.note % 12 for e in events)
        unique_pcs = len(pc_set)

        # H0: number of connected components in pitch-class similarity graph
        # Two PCs are connected if they appear within 500ms of each other
        sorted_events = sorted(events, key=lambda e: e.start_ms)
        adjacency: Dict[int, set] = {i: set() for i in range(12)}
        for i, ev_a in enumerate(sorted_events):
            for j in range(i + 1, min(i + 20, len(sorted_events))):
                ev_b = sorted_events[j]
                if ev_b.start_ms - ev_a.start_ms > 500:
                    break
                adjacency[ev_a.note % 12].add(ev_b.note % 12)
                adjacency[ev_b.note % 12].add(ev_a.note % 12)

        # Count connected components
        visited = set()
        components = 0
        for pc in range(12):
            if pc in pc_set and pc not in visited:
                components += 1
                stack = [pc]
                while stack:
                    node = stack.pop()
                    if node in visited:
                        continue
                    visited.add(node)
                    stack.extend(adjacency[node] - visited)

        H0 = max(1, components)

        # H1: count cycles (simple heuristic based on voice-leading intervals)
        intervals: List[int] = []
        for i in range(1, len(sorted_events)):
            diff = abs(sorted_events[i].note - sorted_events[i - 1].note)
            intervals.append(diff % 12)

        # Count repeating interval patterns (proxy for H1 cycles)
        cycle_count = 0
        for length in range(2, min(8, len(intervals) // 2 + 1)):
            pattern = tuple(intervals[:length])
            for start in range(length, len(intervals) - length + 1):
                if tuple(intervals[start:start + length]) == pattern:
                    cycle_count += 1
                    break

        H1 = cycle_count

        # Emergence score: how much harmonic structure exceeds randomness
        expected_random = unique_pcs * 0.3
        emergence = min(1.0, H1 / max(1, expected_random)) if expected_random > 0 else 0.0

        # Harmonic complexity
        entropy = 0.0
        total = sum(pc_set.values())
        if total > 0:
            for count in pc_set.values():
                p = count / total
                if p > 0:
                    entropy -= p * math.log2(p)
        harmonic_complexity = entropy * unique_pcs / 12.0

        return {
            'H0': H0,
            'H1': H1,
            'emergence_score': round(emergence, 4),
            'harmonic_complexity': round(harmonic_complexity, 4),
            'unique_pitch_classes': unique_pcs,
        }

    # === Synthesis ===

    def render_midi(self, arrangement: Arrangement, path: str) -> int:
        """Export arrangement as MIDI file.

        Parameters
        ----------
        arrangement : Arrangement
            Arrangement to render.
        path : str
            Output file path (.mid).

        Returns
        -------
        int
            Number of bytes written.
        """
        return arrangement.to_midi(path)

    def render_spline(
        self,
        arrangement: Arrangement,
        timbre: str = 'warm',
        sample_rate: int = 44100,
    ) -> bytes:
        """Render arrangement to audio bytes using spline wavetable synthesis.

        Parameters
        ----------
        arrangement : Arrangement
            Arrangement to render.
        timbre : str
            Timbre preset: 'warm', 'bright', 'soft', 'harsh'.
        sample_rate : int
            Audio sample rate.

        Returns
        -------
        bytes
            Raw WAV audio bytes.
        """
        synth = self._get_spline()
        if synth is None:
            raise ImportError("Spline wavetable requires spline_synth module")

        events = arrangement.to_midi_events()
        if not events:
            return b''

        # Determine total duration
        total_ms = max((e.end_ms for e in events), default=0.0)
        duration_s = total_ms / 1000.0 + 0.5  # add 0.5s padding

        # Map timbre to waveform blend
        timbre_map = {
            'warm': ('sine', 'triangle', 0.6),
            'bright': ('sawtooth', 'square', 0.5),
            'soft': ('sine', 'sine', 0.8),
            'harsh': ('square', 'sawtooth', 0.4),
        }
        wave_a, wave_b, blend = timbre_map.get(timbre, ('sine', 'triangle', 0.6))

        # Render each event and sum
        total_samples = int(duration_s * sample_rate)
        output = np.zeros(total_samples, dtype=np.float64)

        # Set synth sample rate
        synth.sample_rate = sample_rate

        for ev in events:
            freq = 440.0 * (2.0 ** ((ev.note - 69) / 12.0))
            dur = ev.duration_ms / 1000.0
            vel = ev.velocity / 127.0
            start_sample = int(ev.start_ms / 1000.0 * sample_rate)

            # Render with spline synth
            wave_audio = synth.morph(wave_a, wave_b, t=blend, frequency=freq, duration=dur)
            n = min(len(wave_audio), total_samples - start_sample)
            if n > 0:
                output[start_sample:start_sample + n] += wave_audio[:n] * vel

        # Normalize and convert to 16-bit WAV bytes
        peak = np.max(np.abs(output))
        if peak > 0:
            output = output / peak * 0.9

        import struct
        import io

        samples_16 = (output * 32767).astype(np.int16)
        n_channels = 1
        bytes_per_sample = 2
        data_size = len(samples_16) * bytes_per_sample

        buf = io.BytesIO()
        # WAV header
        buf.write(b'RIFF')
        buf.write(struct.pack('<I', 36 + data_size))
        buf.write(b'WAVE')
        buf.write(b'fmt ')
        buf.write(struct.pack('<I', 16))  # chunk size
        buf.write(struct.pack('<H', 1))   # PCM
        buf.write(struct.pack('<H', n_channels))
        buf.write(struct.pack('<I', sample_rate))
        buf.write(struct.pack('<I', sample_rate * n_channels * bytes_per_sample))
        buf.write(struct.pack('<H', n_channels * bytes_per_sample))
        buf.write(struct.pack('<H', 16))  # bits per sample
        buf.write(b'data')
        buf.write(struct.pack('<I', data_size))
        buf.write(samples_16.tobytes())

        return buf.getvalue()

    def render(self, arrangement: Arrangement, synth: str = 'spline') -> bytes:
        """Render arrangement to audio bytes using chosen synth.

        Parameters
        ----------
        arrangement : Arrangement
            Arrangement to render.
        synth : str
            Synthesis method: 'spline'.

        Returns
        -------
        bytes
            Audio data.
        """
        if synth == 'spline':
            return self.render_spline(arrangement)
        raise ValueError(f"Unknown synth: {synth!r}. Available: 'spline'")

    # === Presets (one-shot) ===

    def quick(self, description: str) -> Arrangement:
        """Natural language composition: auto-configure everything → compose.

        Parses the description to extract cultural context, scale, raga,
        maqam, rhythm, tempo, and genre, then composes an arrangement.

        Parameters
        ----------
        description : str
            Natural language description, e.g.:
            - 'Indian raga Darbari in Jhaptaal'
            - 'Arabic maqam Rast fast'
            - 'Jazz swing in Bb'
            - 'Ambient pentatonic slow'

        Returns
        -------
        Arrangement
        """
        desc_lower = description.lower()

        # Detect culture and configure
        if 'raga' in desc_lower or 'indian' in desc_lower:
            self._parse_raga_description(desc_lower)
        elif 'maqam' in desc_lower or 'arabic' in desc_lower:
            self._parse_maqam_description(desc_lower)
        elif 'pentatonic' in desc_lower or 'zen' in desc_lower or 'japanese' in desc_lower or 'chinese' in desc_lower:
            self._parse_east_asian_description(desc_lower)
        elif 'african' in desc_lower or 'djembe' in desc_lower or 'drum' in desc_lower:
            self._parse_african_description(desc_lower)
        else:
            self._parse_western_description(desc_lower)

        # Detect tempo modifiers
        if 'slow' in desc_lower or 'vilambit' in desc_lower:
            self.constraints.bpm = min(self.constraints.bpm, 80)
        elif 'fast' in desc_lower or 'drut' in desc_lower:
            self.constraints.bpm = max(self.constraints.bpm, 160)
        elif 'medium' in desc_lower or 'madhya' in desc_lower:
            self.constraints.bpm = 100.0

        return self.compose()

    @classmethod
    def preset(cls, name: str) -> 'Conductor':
        """Create a Conductor from a named preset.

        Parameters
        ----------
        name : str
            Preset name. Available:
            - 'midnight_raga': Bhairavi, vilambit, tanpura drone
            - 'cairo_cafe': Maqam Rast, maqsum, oud timbre
            - 'zen_garden': In scale, ma silence, shakuhachi breath
            - 'djembe_circle': Kuku rhythm, pentatonic, call-response
            - 'bebop_salt': Jazz swing, altered scale, syncopated
            - 'bach_fugue': Counterpoint, well-tempered, species 4
            - 'penrose_dance': Aperiodic Fibonacci groove
            - 'evolved_hybrid': 50-gen evolved cross-cultural blend
            - 'hyperbolic_exploration': Walk through genre space
            - 'quasicrystal': Cut-and-project arpeggios

        Returns
        -------
        Conductor
            Configured conductor.
        """
        key = name.lower().replace('-', '_').replace(' ', '_')
        if key not in _CONDUCTOR_PRESETS:
            available = ', '.join(sorted(_CONDUCTOR_PRESETS.keys()))
            raise ValueError(f"Unknown preset: {name!r}. Available: {available}")

        preset = _CONDUCTOR_PRESETS[key]
        c = cls(
            culture=preset.get('culture'),
            genre=preset.get('genre'),
            scale=preset.get('scale'),
            tuning=preset.get('tuning'),
            rhythm=preset.get('rhythm'),
        )
        c.constraints.bpm = preset.get('bpm', 120.0)
        c._ornament_names = preset.get('ornaments', [])
        return c

    # === Private: Description parsers ===

    def _parse_raga_description(self, desc: str) -> None:
        """Parse raga-related description."""
        # Find raga name
        for raga_name in _RAGA_PRESETS:
            if raga_name in desc:
                self.set_raga(raga_name)
                break
        else:
            self.set_raga('bhairavi')

        # Find tala
        for tala_name in ['teental', 'jhap_tal', 'rupak', 'ek_tal', 'dadra', 'deepchandi']:
            if tala_name in desc:
                self.rhythm_name = tala_name
                self._load_rhythm(tala_name)
                break

    def _parse_maqam_description(self, desc: str) -> None:
        """Parse maqam-related description."""
        for maqam_name in _MAQAM_PRESETS:
            if maqam_name in desc:
                self.set_maqam(maqam_name)
                break
        else:
            self.set_maqam('rast')

    def _parse_east_asian_description(self, desc: str) -> None:
        """Parse East Asian description."""
        for scale_name in _PENTATONIC_PRESETS:
            if scale_name in desc:
                self.set_pentatonic(scale_name)
                return
        if 'bright' in desc or 'yo' in desc:
            self.set_pentatonic('yo_scale')
        else:
            self.set_pentatonic('in_scale')

    def _parse_african_description(self, desc: str) -> None:
        """Parse African/polyrhythm description."""
        for name in _POLYRHYTHM_PRESETS:
            if name in desc:
                self.set_polyrhythm(name)
                return
        self.set_polyrhythm('agbadza')

    def _parse_western_description(self, desc: str) -> None:
        """Parse Western genre description."""
        self.culture = 'western'
        self.tuning_name = 'equal_temperament'
        self._load_tuning('equal_temperament')

        # Detect genre
        genre_map = {
            'jazz': 'Jazz', 'bebop': 'Bebop', 'swing': 'Swing',
            'blues': 'Blues', 'rock': 'Rock', 'punk': 'Punk',
            'metal': 'Metal', 'classical': 'Classical',
            'baroque': 'Baroque', 'romantic': 'Romantic',
            'techno': 'Techno', 'house': 'House',
            'ambient': 'Ambient', 'electronic': 'Electronic',
            'hip hop': 'Hip-hop', 'hiphop': 'Hip-hop', 'trap': 'Trap',
            'idm': 'IDM', 'minimalism': 'Minimalism',
        }
        for keyword, genre in genre_map.items():
            if keyword in desc:
                self.genre = genre
                break
        else:
            self.genre = 'Jazz'

        # Detect scale
        if 'minor' in desc:
            self.set_scale('phrygian_dominant' if 'phrygian' in desc else 'hungarian_minor')
        elif 'pentatonic' in desc:
            self.set_scale('pentatonic_major')
        elif 'blues' in desc:
            self.set_scale('phrygian_dominant')
        else:
            self.set_scale('pentatonic_major')

        # Detect BPM
        if 'slow' in desc:
            self.constraints.bpm = 70.0
        elif 'fast' in desc:
            self.constraints.bpm = 160.0
        else:
            self.constraints.bpm = 120.0

        # Detect swing
        if 'swing' in desc:
            self.constraints.swing_ratio = 0.67
        elif 'straight' in desc:
            self.constraints.swing_ratio = 0.5

    # === Private: Helpers ===

    def _default_voices(self) -> List[Tuple[str, RhythmicRole, str]]:
        """Get default voice assignments based on cultural context."""
        culture_voices: Dict[str, List[Tuple[str, RhythmicRole, str]]] = {
            'indian': [
                ('tanpura', RhythmicRole.ROOT, 'bass'),
                ('melody', RhythmicRole.ROOT, 'lead'),
                ('tabla', RhythmicRole.HALFTIME, 'drums'),
            ],
            'arabic': [
                ('oud', RhythmicRole.ROOT, 'lead'),
                ('qanun', RhythmicRole.OFFSET, 'piano'),
                ('darbuka', RhythmicRole.HALFTIME, 'drums'),
            ],
            'east_asian': [
                ('shakuhachi', RhythmicRole.ROOT, 'lead'),
                ('koto', RhythmicRole.OFFSET, 'piano'),
                ('taiko', RhythmicRole.HALFTIME, 'drums'),
            ],
            'west_african': [
                ('djembe', RhythmicRole.ROOT, 'drums'),
                ('dundun', RhythmicRole.HALFTIME, 'bass'),
                ('bell', RhythmicRole.DOUBLETIME, 'hat'),
            ],
            'western': [
                ('piano', RhythmicRole.ROOT, 'piano'),
                ('bass', RhythmicRole.HALFTIME, 'bass'),
                ('drums', RhythmicRole.DOUBLETIME, 'drums'),
            ],
        }
        return culture_voices.get(self.culture or 'western', culture_voices['western'])

    def _apply_tuning_to_arrangement(self, arr: Arrangement) -> None:
        """Apply microtonal tuning to arrangement events (pitch bend)."""
        # For now, snap pitches to scale degrees
        if self._scale_data:
            scale_notes = self._scale_data.get('notes', [])
            for track in arr.tracks:
                for ev in track.events:
                    pc = ev.note % 12
                    # Snap to nearest scale degree
                    if scale_notes:
                        best = min(scale_notes, key=lambda n: abs(n - pc))
                        ev._note = ev.note - pc + best

    def _constraint_satisfaction(self, arrangement: Arrangement) -> Dict[str, float]:
        """Compute constraint satisfaction metrics."""
        events = arrangement.to_midi_events()
        if not events:
            return {'snap_accuracy': 0, 'funnel_convergence': 0,
                    'consensus_agreement': 0, 'laman_rigidity': 0}

        # Snap accuracy: how well events align to grid
        beat_ms = 60000.0 / arrangement.bpm
        grid_ms = beat_ms / self.constraints.grid_resolution
        snap_errors = []
        for ev in events:
            grid_pos = round(ev.start_ms / grid_ms) * grid_ms
            snap_errors.append(abs(ev.start_ms - grid_pos) / max(grid_ms, 1))

        snap_accuracy = max(0, 1.0 - (sum(snap_errors) / len(snap_errors)))

        # Funnel convergence: how well pitches center around mean
        pitches = [e.note for e in events]
        if pitches:
            mean_pitch = sum(pitches) / len(pitches)
            pitch_variance = sum((p - mean_pitch) ** 2 for p in pitches) / len(pitches)
            funnel_convergence = max(0, 1.0 - pitch_variance / 400.0)
        else:
            funnel_convergence = 0.0

        # Consensus agreement: temporal clustering of events
        if len(events) > 1:
            start_times = sorted(e.start_ms for e in events)
            gaps = [start_times[i + 1] - start_times[i] for i in range(len(start_times) - 1)]
            mean_gap = sum(gaps) / len(gaps) if gaps else 1
            gap_variance = sum((g - mean_gap) ** 2 for g in gaps) / max(len(gaps), 1)
            consensus_agreement = max(0, 1.0 - gap_variance / (mean_gap ** 2 + 1))
        else:
            consensus_agreement = 1.0

        # Laman rigidity: structural density
        if events:
            total_duration = max(e.end_ms for e in events) - min(e.start_ms for e in events)
            density = len(events) / max(total_duration / 1000.0, 0.1)
            laman_rigidity = min(1.0, density / 20.0)
        else:
            laman_rigidity = 0.0

        return {
            'snap_accuracy': round(snap_accuracy, 4),
            'funnel_convergence': round(funnel_convergence, 4),
            'consensus_agreement': round(consensus_agreement, 4),
            'laman_rigidity': round(laman_rigidity, 4),
        }

    def _cultural_metrics(self, arrangement: Arrangement) -> Dict[str, Any]:
        """Compute cultural authenticity metrics."""
        events = arrangement.to_midi_events()
        base = {
            'cultural_authenticity': 0.0,
            'scale_conformance': 0.0,
            'scale_name': self.scale_name,
            'culture': self.culture,
        }
        if not events or not self._scale_data:
            return base

        scale_notes = self._scale_data.get('notes', [])
        if not scale_notes:
            base['cultural_authenticity'] = 0.5
            base['scale_conformance'] = 0.5
            return base

        # Check how many notes are in the chosen scale
        in_scale = 0
        for ev in events:
            pc = ev.note % 12
            # Check if pc is close to any scale note
            if any(abs(pc - n) <= 1 for n in scale_notes):
                in_scale += 1

        authenticity = in_scale / max(len(events), 1)
        base['cultural_authenticity'] = round(authenticity, 4)
        base['scale_conformance'] = round(authenticity, 4)
        return base

    # === Representation ===

    def __repr__(self) -> str:
        parts = ['Conductor(']
        if self.culture:
            parts.append(f'culture={self.culture!r}, ')
        if self.genre:
            parts.append(f'genre={self.genre!r}, ')
        if self.scale_name:
            parts.append(f'scale={self.scale_name!r}, ')
        if self.tuning_name:
            parts.append(f'tuning={self.tuning_name!r}, ')
        parts.append(f'bpm={self.constraints.bpm:.0f})')
        return ''.join(parts)
