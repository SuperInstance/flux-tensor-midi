"""
Genre Brain — load a genre and the system auto-configures everything.

"The killer feature from the Hermes synthesis that nobody asked for
 but everyone would love."

Each genre preset encodes real musical knowledge distilled from
musician reports. Load one and the whole system adapts:
rhythmic roles, FluxVector salience patterns, Eisenstein grid,
loop behavior, BPM, and key.

Usage:
    from flux_tensor_midi.genre_brain import GenreBrain

    brain = GenreBrain('jazz')
    band = brain.create_band(bpm=180, bars=8)
    config = brain.get_preset()
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from flux_tensor_midi.core.flux import FluxVector
from flux_tensor_midi.core.room import RoomMusician
from flux_tensor_midi.core.snap import RhythmicRole, ROLE_RATIO_MAP
from flux_tensor_midi.core.clock import TZeroClock
from flux_tensor_midi.ensemble.band import Band


class GenreBrain:
    """Auto-configure everything for a specific genre."""

    PRESETS: Dict[str, dict] = {
        'jazz': {
            'description': 'Bebop jazz — rubato solos, chord awareness, arc phrases',
            'roles': [RhythmicRole.ROOT, RhythmicRole.TRIPLET, RhythmicRole.HALFTIME],
            'member_names': ['piano', 'bass', 'drums'],
            'salience_profiles': [
                [0.9, 0.3, 0.7, 0.5, 0.2, 0.4, 0.1, 0.0, 0.0],  # piano: melodic
                [0.2, 0.1, 0.3, 0.9, 0.1, 0.2, 0.0, 0.0, 0.0],  # bass: root-heavy
                [0.5, 0.8, 0.4, 0.2, 0.6, 0.3, 0.1, 0.0, 0.0],  # drums: rhythmic
            ],
            'tolerance_profiles': [
                [0.3, 0.5, 0.2, 0.4, 0.6, 0.3, 0.0, 0.0, 0.0],  # piano: some rubato
                [0.1, 0.2, 0.1, 0.1, 0.3, 0.2, 0.0, 0.0, 0.0],  # bass: tight
                [0.2, 0.1, 0.3, 0.2, 0.1, 0.4, 0.0, 0.0, 0.0],  # drums: crisp
            ],
            'default_bpm': 180,
            'default_key': 'Bb',
            'base_note': 58,  # Bb3
            'grid_resolution': 3,  # triplet grid
            'loop_bars': 12,
            'listen_matrix': 'everyone',
            'ewma_alpha': 0.1,  # slow drift adaptation
        },
        'hiphop': {
            'description': 'Hip-hop / trap — heavy swing, 808 bass, crispy hats',
            'roles': [RhythmicRole.ROOT, RhythmicRole.HALFTIME, RhythmicRole.DOUBLETIME],
            'member_names': ['kick', 'bass', 'hat'],
            'salience_profiles': [
                [0.9, 0.1, 0.2, 0.8, 0.1, 0.1, 0.0, 0.0, 0.0],  # kick: downbeat heavy
                [0.3, 0.1, 0.2, 0.9, 0.1, 0.1, 0.0, 0.0, 0.0],  # bass: sub focus
                [0.4, 0.9, 0.5, 0.1, 0.7, 0.3, 0.1, 0.0, 0.0],  # hat: high activity
            ],
            'tolerance_profiles': [
                [0.05, 0.1, 0.1, 0.05, 0.2, 0.1, 0.0, 0.0, 0.0],  # kick: quantized
                [0.1, 0.2, 0.1, 0.05, 0.2, 0.1, 0.0, 0.0, 0.0],   # bass: tight
                [0.15, 0.1, 0.2, 0.2, 0.1, 0.3, 0.0, 0.0, 0.0],   # hat: slightly loose
            ],
            'default_bpm': 140,
            'default_key': 'C',
            'base_note': 48,  # C3 (808 territory)
            'grid_resolution': 4,  # 16th grid
            'loop_bars': 8,
            'listen_matrix': 'conductor',
            'ewma_alpha': 0.15,
        },
        'electronic': {
            'description': 'Electronic / techno — four-on-floor, evolving textures',
            'roles': [RhythmicRole.ROOT, RhythmicRole.OFFSET, RhythmicRole.DOUBLETIME],
            'member_names': ['kick', 'synth', 'arp'],
            'salience_profiles': [
                [0.9, 0.1, 0.1, 0.9, 0.1, 0.1, 0.0, 0.0, 0.0],  # kick: 4-on-floor
                [0.3, 0.5, 0.7, 0.2, 0.8, 0.4, 0.1, 0.0, 0.0],  # synth: evolving
                [0.6, 0.7, 0.4, 0.3, 0.5, 0.8, 0.2, 0.0, 0.0],  # arp: active
            ],
            'tolerance_profiles': [
                [0.02, 0.1, 0.1, 0.02, 0.1, 0.1, 0.0, 0.0, 0.0],  # kick: machine tight
                [0.3, 0.2, 0.1, 0.4, 0.1, 0.2, 0.0, 0.0, 0.0],   # synth: evolving
                [0.1, 0.05, 0.15, 0.1, 0.1, 0.05, 0.0, 0.0, 0.0], # arp: precise
            ],
            'default_bpm': 128,
            'default_key': 'A',
            'base_note': 57,  # A3
            'grid_resolution': 4,
            'loop_bars': 16,
            'listen_matrix': 'everyone',
            'ewma_alpha': 0.08,  # very smooth drift
        },
        'classical': {
            'description': 'Classical — precise timing, voice leading, contrapuntal',
            'roles': [RhythmicRole.ROOT, RhythmicRole.WALTZ, RhythmicRole.HALFTIME],
            'member_names': ['violin', 'viola', 'cello'],
            'salience_profiles': [
                [0.8, 0.4, 0.6, 0.3, 0.5, 0.7, 0.2, 0.0, 0.0],  # violin: lyrical
                [0.5, 0.6, 0.4, 0.5, 0.3, 0.4, 0.1, 0.0, 0.0],  # viola: inner voice
                [0.3, 0.2, 0.5, 0.8, 0.2, 0.3, 0.1, 0.0, 0.0],  # cello: bass line
            ],
            'tolerance_profiles': [
                [0.1, 0.2, 0.1, 0.15, 0.2, 0.1, 0.0, 0.0, 0.0],
                [0.1, 0.15, 0.1, 0.1, 0.2, 0.15, 0.0, 0.0, 0.0],
                [0.05, 0.1, 0.08, 0.05, 0.15, 0.1, 0.0, 0.0, 0.0],
            ],
            'default_bpm': 72,
            'default_key': 'D',
            'base_note': 62,  # D4
            'grid_resolution': 2,  # 8th note grid
            'loop_bars': 8,
            'listen_matrix': 'everyone',
            'ewma_alpha': 0.05,
        },
        'math': {
            'description': 'Math educator — clean patterns, odd meters, reproducible',
            'roles': [RhythmicRole.QUINTUPLE, RhythmicRole.SEPTUPLE, RhythmicRole.ROOT],
            'member_names': ['voice_a', 'voice_b', 'voice_c'],
            'salience_profiles': [
                [0.7, 0.5, 0.7, 0.5, 0.7, 0.5, 0.3, 0.0, 0.0],  # voice_a: alternating
                [0.5, 0.7, 0.5, 0.7, 0.5, 0.7, 0.3, 0.0, 0.0],  # voice_b: complement
                [0.8, 0.2, 0.8, 0.2, 0.8, 0.2, 0.4, 0.0, 0.0],  # voice_c: pulse
            ],
            'tolerance_profiles': [
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # voice_a: exact
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # voice_b: exact
                [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],  # voice_c: exact
            ],
            'default_bpm': 100,
            'default_key': 'C',
            'base_note': 60,  # C4
            'grid_resolution': 5,
            'loop_bars': 5,
            'listen_matrix': 'conductor',
            'ewma_alpha': 0.02,  # near-zero drift
        },
    }

    def __init__(self, genre: str):
        genre_key = genre.lower()
        if genre_key not in self.PRESETS:
            available = ', '.join(sorted(self.PRESETS.keys()))
            raise ValueError(
                f"Unknown genre '{genre}'. Available: {available}"
            )
        self._genre = genre_key
        self._preset = self.PRESETS[genre_key]

    @property
    def genre(self) -> str:
        return self._genre

    @property
    def description(self) -> str:
        return self._preset['description']

    def get_preset(self) -> dict:
        """Return the raw preset dict."""
        return dict(self._preset)

    def create_band(
        self,
        bpm: Optional[int] = None,
        key: Optional[str] = None,
        bars: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> Tuple[Band, List[RoomMusician]]:
        """Create a fully-configured Band for this genre.

        Returns (band, musicians) where musicians are the ordered list
        of RoomMusicians matching the genre's voice assignments.
        """
        import numpy as np

        rng = np.random.RandomState(seed) if seed is not None else None

        actual_bpm = bpm or self._preset['default_bpm']
        actual_bars = bars or self._preset['loop_bars']

        # Create conductor
        conductor = RoomMusician(
            name='conductor',
            role=RhythmicRole.ROOT,
            clock=TZeroClock(bpm=float(actual_bpm), alpha=self._preset['ewma_alpha']),
        )

        band = Band(
            name=f"{self._genre}_ensemble",
            conductor=conductor,
            bpm=float(actual_bpm),
        )

        # Create musicians from preset
        musicians: List[RoomMusician] = []
        roles = self._preset['roles']
        names = self._preset['member_names']
        salience_profiles = self._preset['salience_profiles']
        tolerance_profiles = self._preset['tolerance_profiles']

        for i, (role, name) in enumerate(zip(roles, names)):
            clock = TZeroClock(
                bpm=float(actual_bpm),
                alpha=self._preset['ewma_alpha'],
            )
            musician = RoomMusician(name=name, role=role, clock=clock)

            # Set initial state from genre's salience/tolerance profiles
            sal = salience_profiles[i]
            tol = tolerance_profiles[i]

            if rng is not None:
                # Add slight variation around the preset
                noise_s = rng.uniform(-0.05, 0.05, size=9).tolist()
                noise_t = rng.uniform(-0.02, 0.02, size=9).tolist()
                sal = [max(0.0, min(1.0, s + n)) for s, n in zip(sal, noise_s)]
                tol = [max(0.0, t + n) for t, n in zip(tol, noise_t)]

            values = sal  # use salience as initial FluxVector values
            musician.update_state(FluxVector(values, salience=sal, tolerance=tol))

            band.add_musician(musician)
            musicians.append(musician)

        # Set up listening matrix
        listen = self._preset['listen_matrix']
        if listen == 'everyone':
            band.everyone_listens_to_everyone()
        else:
            band.everyone_listens_to_conductor()

        return band, musicians

    def configure_band(
        self,
        band: Band,
        musicians: List[RoomMusician],
    ) -> None:
        """Apply genre configuration to an existing band and its musicians."""
        salience_profiles = self._preset['salience_profiles']
        tolerance_profiles = self._preset['tolerance_profiles']

        for i, musician in enumerate(musicians):
            if i >= len(salience_profiles):
                break
            sal = salience_profiles[i]
            tol = tolerance_profiles[i]
            musician.update_state(FluxVector(sal, salience=sal, tolerance=tol))

    @classmethod
    def available_genres(cls) -> List[str]:
        """Return sorted list of available genre names."""
        return sorted(cls.PRESETS.keys())

    def __repr__(self) -> str:
        return f"GenreBrain(genre={self._genre!r}, desc={self.description!r})"
