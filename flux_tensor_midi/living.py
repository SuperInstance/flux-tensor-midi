"""
Living Constraint System — MusicalCell and JazzSession.

Autonomous musical agents that use transcription-factor-like constraint
regulation, epigenetic state, and iterative signal exchange to produce
non-pre-calculable jazz performances.

Each MusicalCell is a biological metaphor:
  - Genome: 25 fixed constraint genes (weights)
  - Membrane: input signal filter
  - Ribosome: constraint compiler (genome → constrained output)
  - Mitochondria: dynamics/articulation engine
  - TranscriptionFactors: real-time constraint activation
  - Epigenetic state: methylation marks for readiness
  - Receptors/Emitters: signal I/O

The JazzSession runs 4 cells (piano, bass, drums, sax) in an iterative
loop where each tick depends on the previous tick's signals — output
cannot be predicted without actually running the simulation.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from flux_tensor_midi.midi.events import MidiEvent
from flux_tensor_midi.tracks import Arrangement, Track


# ── Constants ────────────────────────────────────────────────────────────────

GENOME_SIZE = 25

# Gene indices into the genome
GENE_CONSENSUS = 0       # tendency to agree with ensemble
GENE_SNAP = 1            # rhythmic rigidity (Eisenstein snap strength)
GENE_FUNNEL = 2          # melodic gravity toward target
GENE_LAMAN = 3           # constraint rigidity (Laman-graph tightness)
GENE_TEMPO_CONSISTENCY = 4  # resistance to tempo change
GENE_DENSITY = 5         # note density preference
GENE_REGISTER_LO = 6     # lower register boundary weight
GENE_REGISTER_HI = 7     # upper register boundary weight
GENE_VELOCITY_MEAN = 8   # average velocity preference
GENE_VELOCITY_VAR = 9    # velocity variation tolerance
GENE_ARTICULATION = 10   # legato vs staccato tendency
GENE_INTERVAL_MAX = 11   # max interval leap
GENE_REPEAT_AVOID = 12   # avoidance of exact repetition
GENE_TENSION = 13        # harmonic tension preference
GENE_RELEASE = 14        # tension release rate
GENE_RESPONSIVENESS = 15 # how strongly to react to signals
GENE_AUTONOMY = 16       # independence from ensemble
GENE_COMPING = 17        # comping responsiveness (accompaniment)
GENE_WALKING = 18        # walking bass tendency
GENE_GROOVE_DEPTH = 19   # groove pocket depth
GENE_SYNCOPATION = 20    # syncopation preference
GENE_ORNAMENT = 21       # ornamentation tendency
GENE_DYNAMIC_RANGE = 22  # dynamic contrast
GENE_PHRASING = 23       # phrase shaping
GENE_SPACE = 24          # use of silence/rest


# ── Signal Types ─────────────────────────────────────────────────────────────

class SignalType(Enum):
    """Types of inter-cell signals."""
    ENERGY = "energy"
    DENSITY = "density"
    TENSION = "tension"
    REGISTER = "register"
    VELOCITY = "velocity"
    RHYTHM = "rhythm"
    PHRASE_END = "phrase_end"
    PHRASE_START = "phrase_start"
    SOLO_INDICATOR = "solo_indicator"
    ACCENT = "accent"
    REST = "rest"
    GROOVE_LOCK = "groove_lock"
    HARMONIC_CHANGE = "harmonic_change"
    EMOTION = "emotion"
    SPACE = "space"
    SYNCOPATION = "syncopation"


# ── Transcription Factor ────────────────────────────────────────────────────

class TranscriptionFactor:
    """Activates or suppresses constraints based on environmental signals.

    Like biological transcription factors, these bind to specific "genes"
    (constraint indices) and modulate their expression based on the
    presence or absence of activating/suppressing signals.

    Parameters
    ----------
    gene_index : int
        Which gene (constraint) this TF regulates.
    activators : list[SignalType]
        Signal types that increase expression.
    suppressors : list[SignalType]
        Signal types that decrease expression.
    sensitivity : float
        How strongly the TF responds to signals (0.0–2.0).
    """

    def __init__(
        self,
        gene_index: int,
        activators: list[SignalType] | None = None,
        suppressors: list[SignalType] | None = None,
        sensitivity: float = 1.0,
    ):
        if not 0 <= gene_index < GENOME_SIZE:
            raise ValueError(f"gene_index must be 0–{GENOME_SIZE - 1}, got {gene_index}")
        if sensitivity < 0:
            raise ValueError(f"sensitivity must be >= 0, got {sensitivity}")

        self.gene_index = gene_index
        self.activators = list(activators or [])
        self.suppressors = list(suppressors or [])
        self.sensitivity = sensitivity
        self._last_activation = 0.5  # baseline

    def evaluate(self, signals: dict[SignalType, float]) -> float:
        """Returns activation level 0.0–1.0 based on input signals.

        For each activator present, boost activation.
        For each suppressor present, reduce activation.
        Result is clamped to [0, 1] and modulated by sensitivity.

        Parameters
        ----------
        signals : dict
            Mapping of SignalType to signal strength (0.0–1.0).

        Returns
        -------
        float
            Activation level in [0.0, 1.0].
        """
        activation = 0.5  # neutral baseline

        for sig_type in self.activators:
            if sig_type in signals:
                strength = signals[sig_type]
                activation += strength * self.sensitivity * 0.25

        for sig_type in self.suppressors:
            if sig_type in signals:
                strength = signals[sig_type]
                activation -= strength * self.sensitivity * 0.25

        # Add small stochastic noise (biological realism)
        activation += random.gauss(0, 0.02 * self.sensitivity)

        self._last_activation = max(0.0, min(1.0, activation))
        return self._last_activation

    @property
    def last_activation(self) -> float:
        return self._last_activation

    def __repr__(self) -> str:
        act = [a.value for a in self.activators]
        sup = [s.value for s in self.suppressors]
        return (
            f"TranscriptionFactor(gene={self.gene_index}, "
            f"activators={act}, suppressors={sup}, "
            f"sensitivity={self.sensitivity:.2f})"
        )


# ── Constraint Compiler (Ribosome) ──────────────────────────────────────────

class ConstraintCompiler:
    """Translates genomic intent to constrained musical output.

    The ribosome reads the genome, applies epigenetic modifications,
    and compiles a weighted constraint vector that determines
    note selection, timing, velocity, and duration.
    """

    def __init__(self, genome: list[float], epigenetic_state: dict[int, float]):
        self._genome = genome
        self._epigenetic = epigenetic_state

    def compile(
        self,
        tf_activations: dict[int, float],
        context: dict[str, Any],
    ) -> dict[str, float]:
        """Compile genome + epigenetics + TF activations into constraints.

        Returns a constraint dict with keys like:
          'pitch_weight', 'velocity_target', 'duration_target',
          'density', 'syncopation', 'register_center', etc.
        """
        # Start with base genome values
        effective = {}
        for i in range(GENOME_SIZE):
            base = self._genome[i]
            # Apply epigenetic modification
            epi_factor = self._epigenetic.get(i, 1.0)
            # Apply TF activation
            tf_factor = tf_activations.get(i, 1.0)
            effective[i] = base * epi_factor * tf_factor

        # Compile into high-level constraints
        constraints = {
            'pitch_weight': effective[GENE_FUNNEL] * 0.8 + effective[GENE_TENSION] * 0.2,
            'velocity_target': effective[GENE_VELOCITY_MEAN] * 80 + 30,
            'velocity_variance': effective[GENE_VELOCITY_VAR] * 30,
            'duration_target': 100 + effective[GENE_ARTICULATION] * 300,  # ms
            'density': effective[GENE_DENSITY],
            'syncopation': effective[GENE_SYNCOPATION],
            'register_center': (
                (effective[GENE_REGISTER_LO] + effective[GENE_REGISTER_HI]) / 2
            ),
            'register_width': abs(
                effective[GENE_REGISTER_HI] - effective[GENE_REGISTER_LO]
            ),
            'consensus': effective[GENE_CONSENSUS],
            'snap_strength': effective[GENE_SNAP],
            'laman_rigidity': effective[GENE_LAMAN],
            'tempo_consistency': effective[GENE_TEMPO_CONSISTENCY],
            'repeat_avoidance': effective[GENE_REPEAT_AVOID],
            'tension': effective[GENE_TENSION],
            'release_rate': effective[GENE_RELEASE],
            'responsiveness': effective[GENE_RESPONSIVENESS],
            'autonomy': effective[GENE_AUTONOMY],
            'comping': effective[GENE_COMPING],
            'walking': effective[GENE_WALKING],
            'groove_depth': effective[GENE_GROOVE_DEPTH],
            'ornament': effective[GENE_ORNAMENT],
            'dynamic_range': effective[GENE_DYNAMIC_RANGE],
            'phrasing': effective[GENE_PHRASING],
            'space': effective[GENE_SPACE],
            'interval_max': int(effective[GENE_INTERVAL_MAX] * 12) + 1,
        }

        # Apply context modulations
        key_center = context.get('key_center', 60)
        scale = context.get('scale', [0, 2, 4, 5, 7, 9, 11])
        constraints['scale'] = scale
        constraints['key_center'] = key_center

        return constraints

    def __repr__(self) -> str:
        return f"ConstraintCompiler(genes={len(self._genome)})"


# ── Dynamics Engine (Mitochondria) ───────────────────────────────────────────

class DynamicsEngine:
    """Generates energy, articulation, and velocity curves.

    The mitochondria of the cell — produces the energy that drives
    expression. Manages velocity shaping, accent placement, and
    dynamic contour over phrases.
    """

    def __init__(
        self,
        base_energy: float = 0.6,
        contour: str = "natural",
    ):
        self._base_energy = base_energy
        self._contour = contour
        self._energy = base_energy
        self._energy_history: list[float] = []

    @property
    def energy(self) -> float:
        return self._energy

    def update(self, incoming_energy: float, autonomy: float) -> float:
        """Update internal energy based on ensemble energy and autonomy.

        Higher autonomy = less influence from ensemble.
        Returns current energy level.
        """
        # Blend internal and external energy
        blend = 1.0 - autonomy * 0.5
        self._energy = self._energy * (1.0 - blend * 0.3) + incoming_energy * blend * 0.3
        self._energy = max(0.0, min(1.0, self._energy))
        self._energy_history.append(self._energy)
        return self._energy

    def compute_velocity(
        self,
        target: float,
        variance: float,
        beat_position: float,
        syncopation: float,
        accent_signals: float = 0.0,
    ) -> int:
        """Compute velocity for a single note.

        Parameters
        ----------
        target : float
            Target velocity (0–127).
        variance : float
            Allowed variation.
        beat_position : float
            Position within the bar (0.0–1.0).
        syncopation : float
            Syncopation tendency (0–1).
        accent_signals : float
            Incoming accent strength.

        Returns
        -------
        int
            Velocity value 1–127.
        """
        # Natural accent on strong beats
        strong_beat = 1.0 if (beat_position < 0.1 or 0.45 < beat_position < 0.55) else 0.0

        # Syncopation pushes accents to weak beats
        if syncopation > 0.5:
            syncopated_accent = 1.0 if 0.2 < beat_position < 0.4 or 0.7 < beat_position < 0.9 else 0.0
            accent_mix = strong_beat * (1 - syncopation) + syncopated_accent * syncopation
        else:
            accent_mix = strong_beat

        # Add stochastic variation
        noise = random.gauss(0, variance * 0.3)

        # Incoming accent influence
        external = accent_signals * 10

        velocity = target + accent_mix * 15 + noise + external
        return max(1, min(127, int(velocity)))

    def compute_duration(
        self,
        base_ms: float,
        articulation: float,
        energy: float,
        phrasing: float,
        beat_in_phrase: int,
        phrase_length: int,
    ) -> float:
        """Compute note duration in ms.

        articulation: 0 = staccato, 1 = legato
        """
        # Phrase shape: swell in the middle
        phrase_pos = beat_in_phrase / max(1, phrase_length)
        phrase_curve = math.sin(phrase_pos * math.pi) if phrasing > 0.3 else 1.0

        # Articulation modulation
        art_factor = 0.3 + articulation * 0.7

        # Energy makes notes slightly longer (sustained)
        energy_factor = 0.8 + energy * 0.4

        duration = base_ms * art_factor * energy_factor * phrase_curve
        return max(20.0, duration)

    def decay(self) -> None:
        """Natural energy decay between phrases."""
        self._energy *= 0.98
        self._energy = max(0.1, self._energy)

    def boost(self, amount: float) -> None:
        """Energy boost (solo entrance, climax)."""
        self._energy = min(1.0, self._energy + amount)

    def __repr__(self) -> str:
        return (
            f"DynamicsEngine(energy={self._energy:.3f}, "
            f"contour={self._contour!r})"
        )


# ── Musical Cell ─────────────────────────────────────────────────────────────

class MusicalCell:
    """Autonomous musical agent — a cell in the musical organism.

    Each cell has its own genome (25 constraint genes), signal processing
    pipeline, and expression system. Cells interact through a
    signal-response protocol that makes the collective output
    non-pre-calculable.

    Parameters
    ----------
    name : str
        Instrument name (e.g. 'piano', 'bass', 'drums', 'sax').
    genome : list[float]
        25 constraint gene values (0.0–1.0).
    channel : int
        MIDI channel (0–15).
    membrane_fn : Callable, optional
        Signal filter function. Takes signals dict, returns filtered dict.
    note_range : tuple[int, int]
        (low, high) MIDI note range.
    """

    def __init__(
        self,
        name: str,
        genome: list[float],
        channel: int = 0,
        membrane_fn: Callable[[dict], dict] | None = None,
        note_range: tuple[int, int] = (48, 84),
    ):
        if len(genome) != GENOME_SIZE:
            raise ValueError(f"Genome must have {GENOME_SIZE} genes, got {len(genome)}")

        self._id = str(uuid.uuid4())[:8]
        self.name = name
        self.genome = list(genome)
        self.channel = channel
        self.note_range = note_range

        # Organelles
        self.membrane = membrane_fn or self._default_membrane
        self.ribosome: ConstraintCompiler | None = None
        self.mitochondria = DynamicsEngine(
            base_energy=genome[GENE_DYNAMIC_RANGE] * 0.5 + 0.3,
            contour="natural",
        )

        # Transcription factors — wired to relevant genes
        self.tfs: list[TranscriptionFactor] = []

        # Epigenetic state: methylation marks per gene
        # 1.0 = fully expressed, 0.0 = silenced
        self.epigenetic_state: dict[int, float] = {i: 1.0 for i in range(GENOME_SIZE)}

        # Signal I/O
        self.receptors: list[SignalType] = list(SignalType)
        self.emitters: list[SignalType] = list(SignalType)

        # Internal state
        self._filtered_signals: dict[SignalType, float] = {}
        self._tf_activations: dict[int, float] = {}
        self._constraints: dict[str, float] | None = None
        self._history: list[dict] = []
        self._last_output: list[MidiEvent] = []
        self._last_pitch: int = note_range[0]
        self._bar_position: float = 0.0

        # Initialize ribosome with current state
        self.ribosome = ConstraintCompiler(self.genome, self.epigenetic_state)

    @property
    def id(self) -> str:
        return self._id

    @property
    def history(self) -> list[dict]:
        return list(self._history)

    @property
    def last_output(self) -> list[MidiEvent]:
        return list(self._last_output)

    @property
    def energy(self) -> float:
        return self.mitochondria.energy

    # ── Signal processing ────────────────────────────────────────────────

    def _default_membrane(self, signals: dict[SignalType, float]) -> dict[SignalType, float]:
        """Default membrane: pass through signals this cell has receptors for."""
        return {
            sig_type: strength
            for sig_type, strength in signals.items()
            if sig_type in self.receptors
        }

    def receive(self, signals: dict[SignalType, float]) -> None:
        """Filter incoming signals through the membrane.

        Only signals matching this cell's receptors get through.
        """
        self._filtered_signals = self.membrane(signals)

    def update_tfs(self, signals: dict[SignalType, float]) -> None:
        """Update transcription factor activation levels.

        Each TF evaluates the filtered signals and produces an
        activation level for its target gene.
        """
        self._tf_activations = {}
        for tf in self.tfs:
            activation = tf.evaluate(signals)
            self._tf_activations[tf.gene_index] = activation

    # ── Expression ───────────────────────────────────────────────────────

    def express(self, context: dict[str, Any] | None = None) -> list[MidiEvent]:
        """Compile current state into constrained MIDI output.

        This is the core expression pipeline:
        1. Ribosome compiles genome + epigenetics + TFs → constraints
        2. Mitochondria provides energy/articulation
        3. Constraints govern note selection, timing, velocity

        Output is NON-PRE-CALCULABLE because TF activation is stochastic
        and depends on iterative signal exchange.
        """
        ctx = context or {}

        # Update ribosome with current epigenetic state
        self.ribosome = ConstraintCompiler(self.genome, self.epigenetic_state)

        # Compile constraints
        self._constraints = self.ribosome.compile(self._tf_activations, ctx)

        # Update energy
        ensemble_energy = ctx.get('energy', 0.5)
        autonomy = self._constraints.get('autonomy', 0.5)
        current_energy = self.mitochondria.update(ensemble_energy, autonomy)

        # Generate output based on constraints
        events = self._generate_events(ctx, current_energy)
        self._last_output = events

        # Record in history
        self._history.append({
            'beat': ctx.get('beat', 0),
            'bar': ctx.get('bar', 0),
            'events': len(events),
            'energy': current_energy,
            'constraints': dict(self._constraints),
        })

        return events

    def _generate_events(self, context: dict, energy: float) -> list[MidiEvent]:
        """Generate MIDI events from compiled constraints."""
        if self._constraints is None:
            return []

        events: list[MidiEvent] = []

        beat = context.get('beat', 0)
        bar = context.get('bar', 0)
        tempo = context.get('tempo', 120)
        beat_ms = 60000.0 / tempo

        density = self._constraints['density']
        velocity_target = self._constraints['velocity_target']
        velocity_var = self._constraints['velocity_variance']
        syncopation = self._constraints['syncopation']
        interval_max = self._constraints['interval_max']
        repeat_avoid = self._constraints['repeat_avoidance']
        space = self._constraints['space']
        key_center = self._constraints.get('key_center', 60)
        scale = self._constraints.get('scale', [0, 2, 4, 5, 7, 9, 11])
        ornament = self._constraints['ornament']
        phrasing = self._constraints['phrasing']
        articulation_val = self._constraints.get('duration_target', 200)

        # Determine if this beat should have a note (density gate)
        # Space gene adds probability of silence
        silence_prob = space * 0.3
        if random.random() < silence_prob:
            return events

        # Determine number of notes this beat (density-driven)
        num_notes = 1
        if density > 0.7 and random.random() < density - 0.5:
            num_notes = 2
        if density > 0.9 and random.random() < density - 0.7:
            num_notes = 3

        for note_idx in range(num_notes):
            # Pitch selection: constrained random walk
            pitch = self._select_pitch(
                key_center, scale, interval_max, repeat_avoid
            )
            self._last_pitch = pitch

            # Velocity
            beat_pos = (beat % 4) / 4.0
            accent_signal = self._filtered_signals.get(SignalType.ACCENT, 0.0)
            velocity = self.mitochondria.compute_velocity(
                velocity_target, velocity_var, beat_pos, syncopation, accent_signal
            )

            # Duration
            beat_in_phrase = beat % 16
            duration = self.mitochondria.compute_duration(
                beat_ms * 0.5,
                articulation_val / 400.0,
                energy,
                phrasing,
                beat_in_phrase,
                16,
            )

            # Start time
            start_ms = (bar * 4 + beat) * beat_ms
            if note_idx > 0:
                start_ms += beat_ms * 0.5 * note_idx  # sub-beat offset

            events.append(MidiEvent(
                note=pitch,
                velocity=velocity,
                start_ms=start_ms,
                duration_ms=duration,
                channel=self.channel,
            ))

            # Ornaments (grace notes, turns)
            if ornament > 0.5 and random.random() < ornament * 0.3:
                grace_pitch = self._select_pitch(
                    key_center, scale, 3, 0.5
                )
                events.append(MidiEvent(
                    note=grace_pitch,
                    velocity=max(1, velocity - 20),
                    start_ms=start_ms - 30,
                    duration_ms=30,
                    channel=self.channel,
                ))

        return events

    def _select_pitch(
        self,
        key_center: int,
        scale: list[int],
        interval_max: int,
        repeat_avoid: float,
    ) -> int:
        """Select next pitch using constrained random walk on scale."""
        # Build scale across note range
        scale_pitches = []
        for octave in range(-2, 4):
            for degree in scale:
                pitch = key_center + octave * 12 + degree
                if self.note_range[0] <= pitch <= self.note_range[1]:
                    scale_pitches.append(pitch)

        if not scale_pitches:
            return self.note_range[0]

        # Current pitch index in scale
        current = self._last_pitch
        if current in scale_pitches:
            idx = scale_pitches.index(current)
        else:
            # Find nearest scale tone
            idx = min(range(len(scale_pitches)),
                      key=lambda i: abs(scale_pitches[i] - current))

        # Random walk bounded by interval_max
        step = random.randint(-interval_max, interval_max)
        # Bias toward center of range (funnel gene)
        funnel = self._constraints['pitch_weight'] if self._constraints else 0.5
        center_idx = len(scale_pitches) // 2
        if idx > center_idx and random.random() < funnel * 0.3:
            step -= 1
        elif idx < center_idx and random.random() < funnel * 0.3:
            step += 1

        new_idx = max(0, min(len(scale_pitches) - 1, idx + step))

        # Repeat avoidance
        if repeat_avoid > 0.5 and scale_pitches[new_idx] == current:
            # Try adjacent
            if new_idx > 0 and random.random() < repeat_avoid:
                new_idx = max(0, new_idx - 1)
            elif new_idx < len(scale_pitches) - 1 and random.random() < repeat_avoid:
                new_idx = min(len(scale_pitches) - 1, new_idx + 1)

        return scale_pitches[new_idx]

    # ── Signal emission ──────────────────────────────────────────────────

    def emit(self, output: list[MidiEvent] | None = None) -> dict[SignalType, float]:
        """Broadcast signals to other cells based on current output.

        Returns a dict of SignalType → strength for other cells to receive.
        """
        events = output or self._last_output
        signals: dict[SignalType, float] = {}

        if not events:
            signals[SignalType.REST] = 0.8
            signals[SignalType.ENERGY] = self.mitochondria.energy * 0.3
            return signals

        # Compute signal strengths from output
        n_events = len(events)
        avg_velocity = sum(e.velocity for e in events) / n_events
        pitch_range = max(e.note for e in events) - min(e.note for e in events) if n_events > 1 else 0

        signals[SignalType.ENERGY] = self.mitochondria.energy
        signals[SignalType.DENSITY] = min(1.0, n_events / 4.0)
        signals[SignalType.VELOCITY] = avg_velocity / 127.0
        signals[SignalType.REGISTER] = (
            (sum(e.note for e in events) / n_events - self.note_range[0])
            / max(1, self.note_range[1] - self.note_range[0])
        )

        if pitch_range > 12:
            signals[SignalType.TENSION] = min(1.0, pitch_range / 24.0)

        # Rhythmic presence
        if n_events > 2:
            signals[SignalType.RHYTHM] = 0.8
            signals[SignalType.GROOVE_LOCK] = 0.6

        # Accent signal for high-velocity notes
        if any(e.velocity > 100 for e in events):
            signals[SignalType.ACCENT] = max(e.velocity for e in events) / 127.0

        # Emotional coloring
        if avg_velocity > 90:
            signals[SignalType.EMOTION] = 0.8
        elif avg_velocity < 50:
            signals[SignalType.EMOTION] = 0.2
        else:
            signals[SignalType.EMOTION] = 0.5

        return signals

    # ── Learning ─────────────────────────────────────────────────────────

    def learn(self, feedback: dict[str, float]) -> None:
        """Update epigenetic state based on feedback.

        Positive feedback up-regulates (demethylates) genes.
        Negative feedback down-regulates (methylates) genes.

        This is how the cell adapts over time without changing its genome.
        """
        overall = feedback.get('overall', 0.5)
        rhythmic_fit = feedback.get('rhythmic_fit', 0.5)
        harmonic_fit = feedback.get('harmonic_fit', 0.5)
        dynamic_fit = feedback.get('dynamic_fit', 0.5)

        # Adjust epigenetic marks
        # If overall positive, slightly upregulate all genes
        delta = (overall - 0.5) * 0.05
        for i in range(GENOME_SIZE):
            current = self.epigenetic_state.get(i, 1.0)
            self.epigenetic_state[i] = max(0.1, min(1.5, current + delta))

        # Targeted adjustments
        if rhythmic_fit < 0.3:
            self.epigenetic_state[GENE_SNAP] = max(0.2, self.epigenetic_state.get(GENE_SNAP, 1.0) - 0.1)
            self.epigenetic_state[GENE_GROOVE_DEPTH] = min(1.5, self.epigenetic_state.get(GENE_GROOVE_DEPTH, 1.0) + 0.1)

        if harmonic_fit < 0.3:
            self.epigenetic_state[GENE_FUNNEL] = min(1.5, self.epigenetic_state.get(GENE_FUNNEL, 1.0) + 0.1)
            self.epigenetic_state[GENE_TENSION] = max(0.2, self.epigenetic_state.get(GENE_TENSION, 1.0) - 0.1)

        if dynamic_fit < 0.3:
            self.epigenetic_state[GENE_DYNAMIC_RANGE] = min(1.5, self.epigenetic_state.get(GENE_DYNAMIC_RANGE, 1.0) + 0.1)
            self.epigenetic_state[GENE_VELOCITY_VAR] = min(1.5, self.epigenetic_state.get(GENE_VELOCITY_VAR, 1.0) + 0.1)

    def reset_epigenetic(self) -> None:
        """Reset epigenetic state to baseline (all genes fully expressed)."""
        self.epigenetic_state = {i: 1.0 for i in range(GENOME_SIZE)}

    def __repr__(self) -> str:
        return (
            f"MusicalCell(name={self.name!r}, id={self._id}, "
            f"energy={self.mitochondria.energy:.3f}, "
            f"history={len(self._history)})"
        )


# ── Genome Presets ───────────────────────────────────────────────────────────

def piano_genome() -> list[float]:
    """Piano: high consensus, medium snap, high comping responsiveness."""
    return [
        0.75,  # CONSENSUS
        0.50,  # SNAP
        0.60,  # FUNNEL
        0.50,  # LAMAN
        0.70,  # TEMPO_CONSISTENCY
        0.65,  # DENSITY
        0.40,  # REGISTER_LO
        0.70,  # REGISTER_HI
        0.65,  # VELOCITY_MEAN
        0.45,  # VELOCITY_VAR
        0.55,  # Articulation
        0.50,  # INTERVAL_MAX
        0.60,  # REPEAT_AVOID
        0.55,  # TENSION
        0.50,  # RELEASE
        0.70,  # RESPONSIVENESS
        0.40,  # AUTONOMY
        0.80,  # COMPING
        0.30,  # WALKING
        0.50,  # GROOVE_DEPTH
        0.55,  # SYNCOPATION
        0.40,  # ORNAMENT
        0.60,  # DYNAMIC_RANGE
        0.55,  # PHrasing
        0.35,  # SPACE
    ]


def bass_genome() -> list[float]:
    """Bass: high snap (walking bass), high funnel (root motion)."""
    return [
        0.60,  # CONSENSUS
        0.85,  # SNAP — walking bass needs rhythmic precision
        0.80,  # FUNNEL — strong root motion gravity
        0.70,  # LAMAN
        0.80,  # TEMPO_CONSISTENCY
        0.70,  # DENSITY — walking = steady
        0.90,  # REGISTER_LO — bass register
        0.20,  # REGISTER_HI — stay low
        0.55,  # VELOCITY_MEAN
        0.25,  # VELOCITY_VAR — relatively consistent
        0.70,  # Articulation — legato walking
        0.40,  # INTERVAL_MAX — stepwise motion
        0.50,  # REPEAT_AVOID
        0.30,  # TENSION — supportive
        0.60,  # RELEASE
        0.50,  # RESPONSIVENESS
        0.30,  # AUTONOMY — follows
        0.60,  # COMPING
        0.90,  # WALKING — strong walking tendency
        0.70,  # GROOVE_DEPTH
        0.30,  # SYNCOPATION — mostly on beat
        0.15,  # ORNAMENT — minimal
        0.40,  # DYNAMIC_RANGE
        0.45,  # PHrasing
        0.20,  # SPACE — fills time
    ]


def drums_genome() -> list[float]:
    """Drums: high laman (groove rigidity), high tempo consistency."""
    return [
        0.70,  # CONSENSUS
        0.90,  # SNAP — tight rhythm
        0.30,  # FUNNEL — not melodic
        0.85,  # LAMAN — rigid groove
        0.90,  # TEMPO_CONSISTENCY — timekeeper
        0.80,  # DENSITY — busy
        0.50,  # REGISTER_LO
        0.50,  # REGISTER_HI
        0.60,  # VELOCITY_MEAN
        0.55,  # VELOCITY_VAR — dynamic accents
        0.30,  # Articulation — percussive (short)
        0.30,  # INTERVAL_MAX — fixed kit sounds
        0.30,  # REPEAT_AVOID — patterns repeat
        0.20,  # TENSION
        0.40,  # RELEASE
        0.60,  # RESPONSIVENESS
        0.50,  # AUTONOMY — somewhat independent
        0.50,  # COMPING
        0.20,  # WALKING
        0.90,  # GROOVE_DEPTH — deep pocket
        0.60,  # SYNCOPATION
        0.30,  # ORNAMENT
        0.70,  # DYNAMIC_RANGE
        0.50,  # PHrasing
        0.25,  # SPACE
    ]


def sax_genome() -> list[float]:
    """Sax: low snap (expressive), high funnel (melodic gravity)."""
    return [
        0.45,  # CONSENSUS
        0.30,  # SNAP — loose rhythm for expression
        0.75,  # FUNNEL — melodic gravity
        0.35,  # LAMAN
        0.50,  # TEMPO_CONSISTENCY
        0.55,  # DENSITY
        0.45,  # REGISTER_LO
        0.80,  # REGISTER_HI — high range
        0.70,  # VELOCITY_MEAN
        0.65,  # VELOCITY_VAR — lots of variation
        0.60,  # Articulation
        0.70,  # INTERVAL_MAX — wide leaps
        0.70,  # REPEAT_AVOID
        0.75,  # TENSION — builds tension
        0.60,  # RELEASE
        0.60,  # RESPONSIVENESS
        0.65,  # AUTONOMY — independent
        0.30,  # COMPING
        0.20,  # WALKING
        0.40,  # GROOVE_DEPTH
        0.75,  # SYNCOPATION — very syncopated
        0.70,  # ORNAMENT — lots of ornaments
        0.80,  # DYNAMIC_RANGE — wide dynamics
        0.75,  # PHrasing — strong phrasing
        0.40,  # SPACE — uses space expressively
    ]


# ── TF Wiring Presets ────────────────────────────────────────────────────────

def _wire_piano_tfs() -> list[TranscriptionFactor]:
    """Wire TFs for piano cell."""
    return [
        TranscriptionFactor(GENE_COMPING, activators=[SignalType.SOLO_INDICATOR], sensitivity=1.2),
        TranscriptionFactor(GENE_DENSITY, activators=[SignalType.ENERGY], suppressors=[SignalType.REST], sensitivity=0.8),
        TranscriptionFactor(GENE_SYNCOPATION, activators=[SignalType.RHYTHM, SignalType.GROOVE_LOCK], sensitivity=0.9),
        TranscriptionFactor(GENE_VELOCITY_MEAN, activators=[SignalType.ACCENT], sensitivity=0.7),
        TranscriptionFactor(GENE_SPACE, activators=[SignalType.SPACE], suppressors=[SignalType.DENSITY], sensitivity=0.6),
        TranscriptionFactor(GENE_TENSION, activators=[SignalType.TENSION], sensitivity=0.8),
        TranscriptionFactor(GENE_ARTICULATION, activators=[SignalType.EMOTION], sensitivity=0.5),
    ]


def _wire_bass_tfs() -> list[TranscriptionFactor]:
    """Wire TFs for bass cell."""
    return [
        TranscriptionFactor(GENE_WALKING, activators=[SignalType.RHYTHM], suppressors=[SignalType.REST], sensitivity=1.0),
        TranscriptionFactor(GENE_FUNNEL, activators=[SignalType.HARMONIC_CHANGE], sensitivity=1.2),
        TranscriptionFactor(GENE_SNAP, activators=[SignalType.GROOVE_LOCK], sensitivity=0.9),
        TranscriptionFactor(GENE_DENSITY, activators=[SignalType.ENERGY], suppressors=[SignalType.REST], sensitivity=0.7),
        TranscriptionFactor(GENE_VELOCITY_MEAN, activators=[SignalType.ACCENT], sensitivity=0.6),
        TranscriptionFactor(GENE_REGISTER_LO, suppressors=[SignalType.REGISTER], sensitivity=0.5),
    ]


def _wire_drums_tfs() -> list[TranscriptionFactor]:
    """Wire TFs for drums cell."""
    return [
        TranscriptionFactor(GENE_GROOVE_DEPTH, activators=[SignalType.GROOVE_LOCK], sensitivity=1.1),
        TranscriptionFactor(GENE_LAMAN, activators=[SignalType.RHYTHM], suppressors=[SignalType.SYNCOPATION], sensitivity=0.8),
        TranscriptionFactor(GENE_DENSITY, activators=[SignalType.ENERGY], sensitivity=0.9),
        TranscriptionFactor(GENE_DYNAMIC_RANGE, activators=[SignalType.ACCENT, SignalType.EMOTION], sensitivity=0.7),
        TranscriptionFactor(GENE_TEMPO_CONSISTENCY, suppressors=[SignalType.TENSION], sensitivity=0.6),
        TranscriptionFactor(GENE_SYNCOPATION, activators=[SignalType.SYNCOPATION], sensitivity=0.8),
    ]


def _wire_sax_tfs() -> list[TranscriptionFactor]:
    """Wire TFs for sax cell."""
    return [
        TranscriptionFactor(GENE_TENSION, activators=[SignalType.ENERGY], sensitivity=1.0),
        TranscriptionFactor(GENE_ORNAMENT, activators=[SignalType.EMOTION, SignalType.PHRASE_END], sensitivity=0.9),
        TranscriptionFactor(GENE_SYNCOPATION, activators=[SignalType.RHYTHM], sensitivity=0.8),
        TranscriptionFactor(GENE_AUTONOMY, activators=[SignalType.SOLO_INDICATOR], suppressors=[SignalType.GROOVE_LOCK], sensitivity=1.1),
        TranscriptionFactor(GENE_DYNAMIC_RANGE, activators=[SignalType.ACCENT], sensitivity=0.7),
        TranscriptionFactor(GENE_INTERVAL_MAX, activators=[SignalType.TENSION], suppressors=[SignalType.REST], sensitivity=0.8),
        TranscriptionFactor(GENE_PHRASING, activators=[SignalType.PHRASE_START], suppressors=[SignalType.PHRASE_END], sensitivity=0.9),
        TranscriptionFactor(GENE_SPACE, activators=[SignalType.PHRASE_END], sensitivity=0.6),
    ]


# ── Trading Fours ────────────────────────────────────────────────────────────

class TradingFours:
    """Two cells alternate 4-bar phrases, each responding to previous.

    Like jazz musicians trading 4s — one plays, the other listens and
    prepares a response that builds on what came before.

    Parameters
    ----------
    cell_a : MusicalCell
        First cell (e.g. sax).
    cell_b : MusicalCell
        Second cell (e.g. drums).
    phrase_length : int
        Bars per phrase (default 4).
    """

    def __init__(
        self,
        cell_a: MusicalCell,
        cell_b: MusicalCell,
        phrase_length: int = 4,
    ):
        self.cell_a = cell_a
        self.cell_b = cell_b
        self.phrase_length = phrase_length
        self._current_cell: str = 'a'
        self._phrase_beat: int = 0
        self._last_a_signals: dict[SignalType, float] = {}
        self._last_b_signals: dict[SignalType, float] = {}

    @property
    def current_soloist(self) -> MusicalCell:
        return self.cell_a if self._current_cell == 'a' else self.cell_b

    def round(
        self,
        beat: int,
        context: dict[str, Any] | None = None,
    ) -> list[MidiEvent]:
        """One beat: current cell plays, other listens.

        Parameters
        ----------
        beat : int
            Global beat number.
        context : dict
            Shared context (key, tempo, etc.).

        Returns
        -------
        list[MidiEvent]
            Events from the active cell this beat.
        """
        ctx = context or {}
        ctx['beat'] = beat
        ctx['bar'] = beat // 4

        # Determine which cell plays this beat
        phrase_bar = (beat // 4) % (self.phrase_length * 2)
        is_cell_a = phrase_bar < self.phrase_length

        if is_cell_a:
            soloist = self.cell_a
            listener = self.cell_b
            # Feed B's last signals to A
            soloist.receive(self._last_b_signals)
            soloist.update_tfs(self._last_b_signals)
        else:
            soloist = self.cell_b
            listener = self.cell_a
            soloist.receive(self._last_a_signals)
            soloist.update_tfs(self._last_a_signals)

        # Soloist expresses
        output = soloist.express(ctx)
        signals = soloist.emit(output)

        # Store signals for next round
        if is_cell_a:
            self._last_a_signals = signals
        else:
            self._last_b_signals = signals

        # Listener hears (but doesn't play)
        listener.receive(signals)
        listener.update_tfs(signals)

        self._phrase_beat += 1
        self._current_cell = 'a' if is_cell_a else 'b'

        return output

    @property
    def turn(self) -> str:
        return self._current_cell

    def __repr__(self) -> str:
        return (
            f"TradingFours({self.cell_a.name} <-> {self.cell_b.name}, "
            f"phrase={self.phrase_length}, turn={self._current_cell})"
        )


# ── Call and Response ────────────────────────────────────────────────────────

class CallAndResponse:
    """One cell calls, other responds — signal-response protocol.

    The caller produces a phrase and emits signals describing it.
    The responder receives those signals and crafts a complementary
    response.

    Parameters
    ----------
    caller : MusicalCell
        The calling cell.
    responder : MusicalCell
        responding cell.
    call_length : int
        Beats in the call phrase.
    response_length : int
        Beats in the response phrase.
    """

    def __init__(
        self,
        caller: MusicalCell,
        responder: MusicalCell,
        call_length: int = 8,
        response_length: int = 8,
    ):
        self.caller = caller
        self.responder = responder
        self.call_length = call_length
        self.response_length = response_length
        self._phase: str = 'call'  # 'call' or 'response'
        self._beat_in_phase: int = 0
        self._last_call_output: list[MidiEvent] = []
        self._last_call_signals: dict[SignalType, float] = {}

    @property
    def phase(self) -> str:
        return self._phase

    def call(self, context: dict[str, Any] | None = None) -> tuple[list[MidiEvent], dict[SignalType, float]]:
        """Caller produces a phrase.

        Returns
        -------
        tuple[list[MidiEvent], dict]
            (call_events, call_signals)
        """
        ctx = context or {}
        output = self.caller.express(ctx)
        signals = self.caller.emit(output)
        self._last_call_output = output
        self._last_call_signals = signals
        return output, signals

    def respond(
        self,
        call_output: list[MidiEvent] | None = None,
        call_signals: dict[SignalType, float] | None = None,
        context: dict[str, Any] | None = None,
    ) -> list[MidiEvent]:
        """Responder produces a response to the call.

        Parameters
        ----------
        call_output : list[MidiEvent], optional
            The call events (uses stored if None).
        call_signals : dict, optional
            The call signals (uses stored if None).
        context : dict, optional
            Shared context.

        Returns
        -------
        list[MidiEvent]
            Response events.
        """
        signals = call_signals or self._last_call_signals
        ctx = context or {}

        # Responder receives call signals and responds
        self.responder.receive(signals)
        self.responder.update_tfs(signals)

        output = self.responder.express(ctx)
        return output

    def tick(
        self,
        beat: int,
        context: dict[str, Any] | None = None,
    ) -> list[MidiEvent]:
        """Process one beat of the call-response cycle.

        Automatically alternates between call and response phases.
        """
        ctx = context or {}
        ctx['beat'] = beat
        ctx['bar'] = beat // 4

        if self._phase == 'call':
            call_events, call_signals = self.call(ctx)
            self._beat_in_phase += 1

            if self._beat_in_phase >= self.call_length:
                self._phase = 'response'
                self._beat_in_phase = 0
                self._last_call_output = call_events
                self._last_call_signals = call_signals

            return call_events

        else:  # response
            response_events = self.respond(context=ctx)
            self._beat_in_phase += 1

            if self._beat_in_phase >= self.response_length:
                self._phase = 'call'
                self._beat_in_phase = 0

            return response_events

    def __repr__(self) -> str:
        return (
            f"CallAndResponse({self.caller.name} -> {self.responder.name}, "
            f"phase={self._phase}, beat={self._beat_in_phase})"
        )


# ── Vamp ─────────────────────────────────────────────────────────────────────

class Vamp:
    """Repeating pattern that waits for soloist input — like a promoter region.

    A vamp is a repeating accompaniment pattern that loops until the
    soloist signals a transition. Like a biological promoter region,
    it's "on" until a specific signal switches it off.

    Parameters
    ----------
    pattern : list[MidiEvent]
        The repeating vamp pattern.
    bars : int
        Length of the pattern in bars.
    """

    def __init__(
        self,
        pattern: list[MidiEvent],
        bars: int = 2,
    ):
        self.pattern = list(pattern)
        self.bars = bars
        self.waiting: bool = True
        self._loop_count: int = 0
        self._transition_threshold: float = 0.7

    def tick(
        self,
        beat: int,
        tempo: float = 120.0,
        soloist_input: dict[SignalType, float] | None = None,
    ) -> list[MidiEvent]:
        """Repeat pattern, but if soloist signals, mark for transition.

        Parameters
        ----------
        beat : int
            Current beat number.
        tempo : float
            Current tempo.
        soloist_input : dict, optional
            Signals from the soloist.

        Returns
        -------
        list[MidiEvent]
            Vamp events for this beat (time-shifted to current beat).
        """
        beat_ms = 60000.0 / tempo
        beats_per_loop = self.bars * 4
        loop_beat = beat % beats_per_loop

        # Time-shift pattern to current position
        offset_ms = beat * beat_ms
        events = []
        for ev in self.pattern:
            # Check if this event falls on the current beat
            ev_beat_offset = ev.start_ms / beat_ms
            if int(ev_beat_offset) == loop_beat:
                events.append(MidiEvent(
                    note=ev.note,
                    velocity=ev.velocity,
                    start_ms=offset_ms + (ev_beat_offset % 1) * beat_ms,
                    duration_ms=ev.duration_ms,
                    channel=ev.channel,
                ))

        # Check for transition signal
        if soloist_input and self.waiting:
            energy = soloist_input.get(SignalType.ENERGY, 0.0)
            solo = soloist_input.get(SignalType.SOLO_INDICATOR, 0.0)
            phrase_end = soloist_input.get(SignalType.PHRASE_END, 0.0)

            if (energy > self._transition_threshold or
                    solo > 0.8 or
                    phrase_end > 0.8):
                self.waiting = False

        # Count loops
        if loop_beat == 0 and beat > 0:
            self._loop_count += 1

        return events

    def reset(self) -> None:
        """Reset vamp to waiting state."""
        self.waiting = True
        self._loop_count = 0

    @property
    def loop_count(self) -> int:
        return self._loop_count

    @property
    def should_transition(self) -> bool:
        return not self.waiting

    def __repr__(self) -> str:
        return (
            f"Vamp(bars={self.bars}, waiting={self.waiting}, "
            f"loops={self._loop_count})"
        )


# ── Jazz Session ─────────────────────────────────────────────────────────────

class SessionPhase(Enum):
    """Phases of a jazz session."""
    HEAD = "head"                # Playing the melody/head
    SOLO_PIANO = "solo_piano"    # Piano solo
    SOLO_SAX = "solo_sax"        # Sax solo
    TRADING = "trading"          # Trading fours
    COLLECTIVE = "collective"    # Collective improvisation
    CODA = "coda"                # Outro/coda
    ENDED = "ended"              # Session complete


class JazzSession:
    """Full jazz session — 4 musical cells in iterative loop.

    The session creates 4 MusicalCells (piano, bass, drums, sax) with
    instrument-specific genomes and transcription factor wiring.
    Each tick, cells exchange signals and react, making the output
    non-pre-calculable.

    Parameters
    ----------
    key : str
        Key center (e.g. 'C', 'F', 'Bb').
    tempo : float
        Tempo in BPM.
    style : str
        Jazz style hint ('bebop', 'cool', 'hard_bop', 'modal', 'free').
    seed : int, optional
        Random seed for reproducibility (None = non-deterministic).
    """

    # Major scale intervals
    SCALES: dict[str, list[int]] = {
        'major': [0, 2, 4, 5, 7, 9, 11],
        'dorian': [0, 2, 3, 5, 7, 9, 10],
        'mixolydian': [0, 2, 4, 5, 7, 9, 10],
        'bebop': [0, 2, 4, 5, 7, 9, 10, 11],
        'blues': [0, 3, 5, 6, 7, 10],
        'pentatonic': [0, 2, 4, 7, 9],
    }

    KEY_MAP: dict[str, int] = {
        'C': 60, 'C#': 61, 'Db': 61,
        'D': 62, 'D#': 63, 'Eb': 63,
        'E': 64, 'Fb': 64,
        'F': 65, 'F#': 66, 'Gb': 66,
        'G': 67, 'G#': 68, 'Ab': 68,
        'A': 69, 'A#': 70, 'Bb': 70,
        'B': 71, 'Cb': 71,
    }

    def __init__(
        self,
        key: str = 'C',
        tempo: float = 120.0,
        style: str = 'bebop',
        seed: int | None = None,
    ):
        self.key = key
        self.tempo = tempo
        self.style = style
        self._seed = seed

        if seed is not None:
            random.seed(seed)

        # Shared context
        self.shared_context: dict[str, Any] = {
            'key': key,
            'key_center': self.KEY_MAP.get(key, 60),
            'tempo': tempo,
            'style': style,
            'scale': self._scale_for_style(style),
            'energy': 0.5,
            'beat': 0,
            'bar': 0,
            'phase': SessionPhase.HEAD,
        }

        # Beat/bar counters
        self.beat: int = 0
        self.bar: int = 0

        # Phase management
        self.phase: SessionPhase = SessionPhase.HEAD
        self._phase_beats: int = 0
        self._phase_schedule: list[tuple[int, SessionPhase]] = []

        # Create cells
        self.cells: dict[str, MusicalCell] = {
            'piano': self._create_piano(),
            'bass': self._create_bass(),
            'drums': self._create_drums(),
            'sax': self._create_sax(),
        }

        # Session-level structures
        self._trading: TradingFours | None = None
        self._call_response: CallAndResponse | None = None
        self._vamp: Vamp | None = None

        # Output collection
        self._all_events: list[MidiEvent] = []
        self._signals_log: list[dict[str, dict[SignalType, float]]] = []

    def _scale_for_style(self, style: str) -> list[int]:
        """Select scale based on style."""
        if style in ('bebop', 'hard_bop'):
            return self.SCALES['bebop']
        elif style == 'modal':
            return self.SCALES['dorian']
        elif style == 'cool':
            return self.SCALES['mixolydian']
        elif style == 'free':
            return self.SCALES['blues']
        else:
            return self.SCALES['major']

    def _create_piano(self) -> MusicalCell:
        cell = MusicalCell(
            name='piano',
            genome=piano_genome(),
            channel=0,
            note_range=(48, 84),
        )
        cell.tfs = _wire_piano_tfs()
        return cell

    def _create_bass(self) -> MusicalCell:
        cell = MusicalCell(
            name='bass',
            genome=bass_genome(),
            channel=1,
            note_range=(28, 48),
        )
        cell.tfs = _wire_bass_tfs()
        return cell

    def _create_drums(self) -> MusicalCell:
        cell = MusicalCell(
            name='drums',
            genome=drums_genome(),
            channel=9,  # GM drum channel
            note_range=(36, 60),
        )
        cell.tfs = _wire_drums_tfs()
        return cell

    def _create_sax(self) -> MusicalCell:
        cell = MusicalCell(
            name='sax',
            genome=sax_genome(),
            channel=2,
            note_range=(54, 84),
        )
        cell.tfs = _wire_sax_tfs()
        return cell

    # ── Core Tick ────────────────────────────────────────────────────────

    def tick(self) -> list[MidiEvent]:
        """One beat: each cell hears others, updates TFs, expresses, emits.

        NON-PRE-CALCULABLE: output depends on iterative reactions.
        The order of processing matters because each cell's output
        becomes input for the next evaluation.

        Returns
        -------
        list[MidiEvent]
            All MIDI events from this tick.
        """
        ctx = dict(self.shared_context)
        ctx['beat'] = self.beat
        ctx['bar'] = self.bar
        ctx['energy'] = self.shared_context.get('energy', 0.5)

        # Determine active cells based on phase
        tick_events: list[MidiEvent] = []
        round_signals: dict[str, dict[SignalType, float]] = {}

        if self.phase == SessionPhase.TRADING and self._trading:
            # Trading fours: only two cells alternate
            trading_events = self._trading.round(self.beat, ctx)
            tick_events.extend(trading_events)
            # Accompaniment cells still play softly
            for name in ('piano', 'bass'):
                if name not in ('sax', 'drums') or True:  # always
                    cell = self.cells[name]
                    if name not in (self._trading.cell_a.name, self._trading.cell_b.name):
                        # Accompaniment: receive signals, play reduced
                        cell.receive(self._aggregate_signals(round_signals))
                        cell.update_tfs(self._aggregate_signals(round_signals))
                        accom_events = cell.express(ctx)
                        # Reduce accompaniment density
                        accom_events = accom_events[:max(1, len(accom_events) // 2)]
                        tick_events.extend(accom_events)
                        round_signals[name] = cell.emit(accom_events)

        elif self.phase in (SessionPhase.SOLO_PIANO, SessionPhase.SOLO_SAX):
            soloist_name = 'piano' if self.phase == SessionPhase.SOLO_PIANO else 'sax'
            soloist = self.cells[soloist_name]

            # Soloist gets ensemble signals
            soloist.receive(self._aggregate_signals(round_signals))
            soloist.update_tfs(self._aggregate_signals(round_signals))

            # Add solo indicator signal
            solo_signals = {SignalType.SOLO_INDICATOR: 0.9}
            soloist.receive(solo_signals)

            solo_events = soloist.express(ctx)
            tick_events.extend(solo_events)
            round_signals[soloist_name] = soloist.emit(solo_events)

            # Accompaniment plays with comping responsiveness
            for name, cell in self.cells.items():
                if name == soloist_name:
                    continue
                agg = self._aggregate_signals(round_signals)
                agg[SignalType.SOLO_INDICATOR] = 0.7
                cell.receive(agg)
                cell.update_tfs(agg)
                events = cell.express(ctx)
                tick_events.extend(events)
                round_signals[name] = cell.emit(events)

        else:
            # All cells play (head, collective, coda)
            # Phase 1: All cells receive accumulated signals
            accumulated: dict[SignalType, float] = {}
            for name, cell in self.cells.items():
                cell.receive(accumulated)
                cell.update_tfs(accumulated)

            # Phase 2: Express in order (bass→drums→piano→sax)
            order = ['bass', 'drums', 'piano', 'sax']
            for name in order:
                cell = self.cells[name]
                output = cell.express(ctx)
                tick_events.extend(output)
                signals = cell.emit(output)
                round_signals[name] = signals

                # Update accumulated signals for next cell
                for sig_type, strength in signals.items():
                    accumulated[sig_type] = max(
                        accumulated.get(sig_type, 0.0),
                        strength
                    )

        # Update shared context
        self.shared_context['energy'] = self._compute_energy(round_signals)
        self._signals_log.append(round_signals)

        # Advance time
        self.beat += 1
        self.bar = self.beat // 4
        self._phase_beats += 1
        self._all_events.extend(tick_events)

        # Phase transitions
        self._maybe_transition_phase()

        return tick_events

    def _aggregate_signals(
        self,
        round_signals: dict[str, dict[SignalType, float]],
    ) -> dict[SignalType, float]:
        """Aggregate signals from all cells."""
        aggregated: dict[SignalType, float] = {}
        for name, signals in round_signals.items():
            for sig_type, strength in signals.items():
                if sig_type in aggregated:
                    aggregated[sig_type] = max(aggregated[sig_type], strength)
                else:
                    aggregated[sig_type] = strength
        return aggregated

    def _compute_energy(self, signals: dict[str, dict[SignalType, float]]) -> float:
        """Compute ensemble energy from all cell signals."""
        total_energy = 0.0
        count = 0
        for name, sigs in signals.items():
            if SignalType.ENERGY in sigs:
                total_energy += sigs[SignalType.ENERGY]
                count += 1
        if count == 0:
            return self.shared_context.get('energy', 0.5)

        new_energy = total_energy / count
        # Smooth with previous
        old_energy = self.shared_context.get('energy', 0.5)
        return old_energy * 0.7 + new_energy * 0.3

    def _maybe_transition_phase(self) -> None:
        """Phase transitions based on context and time in session.

        head → solo_piano → solo_sax → trading → collective → coda → ended
        """
        energy = self.shared_context.get('energy', 0.5)
        beats_in_phase = self._phase_beats
        bars_in_phase = beats_in_phase // 4

        phase_transitions = {
            SessionPhase.HEAD: (SessionPhase.SOLO_PIANO, 32),      # 32 beats = 8 bars
            SessionPhase.SOLO_PIANO: (SessionPhase.SOLO_SAX, 64),  # 64 beats = 16 bars
            SessionPhase.SOLO_SAX: (SessionPhase.TRADING, 64),     # 64 beats = 16 bars
            SessionPhase.TRADING: (SessionPhase.COLLECTIVE, 64),   # 64 beats = 16 bars
            SessionPhase.COLLECTIVE: (SessionPhase.CODA, 32),      # 32 beats = 8 bars
            SessionPhase.CODA: (SessionPhase.ENDED, 16),           # 16 beats = 4 bars
        }

        if self.phase not in phase_transitions:
            return

        next_phase, min_beats = phase_transitions[self.phase]

        # Transition conditions
        should_transition = False

        if beats_in_phase >= min_beats:
            should_transition = True

            # Energy-based early/late transition
            if self.phase == SessionPhase.HEAD and energy > 0.8:
                if beats_in_phase >= min_beats * 0.75:
                    should_transition = True
            elif self.phase == SessionPhase.COLLECTIVE and energy < 0.3:
                should_transition = True

        if should_transition:
            self._transition_to(next_phase)

    def _transition_to(self, new_phase: SessionPhase) -> None:
        """Execute phase transition."""
        old_phase = self.phase
        self.phase = new_phase
        self.shared_context['phase'] = new_phase
        self._phase_beats = 0

        # Set up phase-specific structures
        if new_phase == SessionPhase.TRADING:
            self._trading = TradingFours(
                cell_a=self.cells['sax'],
                cell_b=self.cells['drums'],
                phrase_length=4,
            )
            # Energy boost for trading
            for cell in self.cells.values():
                cell.mitochondria.boost(0.2)

        elif new_phase == SessionPhase.CODA:
            # Decay energy for coda
            for cell in self.cells.values():
                cell.mitochondria.decay()
                cell.mitochondria.decay()

        elif new_phase == SessionPhase.ENDED:
            pass

        # Reset call-response when entering solo phases
        if new_phase == SessionPhase.SOLO_SAX:
            self._call_response = CallAndResponse(
                caller=self.cells['sax'],
                responder=self.cells['piano'],
            )

    # ── Perform ──────────────────────────────────────────────────────────

    def perform(self, bars: int = 32) -> Arrangement:
        """Run full session. Cannot predict output without running.

        Parameters
        ----------
        bars : int
            Total bars to perform.

        Returns
        -------
        Arrangement
            Complete arrangement with all events.
        """
        total_beats = bars * 4
        self._all_events.clear()

        for _ in range(total_beats):
            if self.phase == SessionPhase.ENDED:
                break
            self.tick()

        # Build arrangement from collected events
        arr = Arrangement(name=f'jazz_{self.key}_{self.style}', bpm=self.tempo, bars=bars)

        # Split events by channel into tracks
        channel_events: dict[int, list[MidiEvent]] = {}
        for ev in self._all_events:
            channel_events.setdefault(ev.channel, []).append(ev)

        channel_names = {0: 'piano', 1: 'bass', 2: 'sax', 9: 'drums'}
        for ch, events in channel_events.items():
            name = channel_names.get(ch, f'ch{ch}')
            track = Track(name=name, voice=name, bpm=self.tempo)
            track._events = sorted(events, key=lambda e: e.start_ms)
            arr.add_track(track)

        return arr

    # ── Utilities ────────────────────────────────────────────────────────

    def get_session_state(self) -> dict:
        """Return current session state for inspection."""
        return {
            'phase': self.phase.value,
            'beat': self.beat,
            'bar': self.bar,
            'energy': self.shared_context.get('energy', 0.5),
            'cells': {
                name: {
                    'energy': cell.energy,
                    'history_size': len(cell.history),
                    'epigenetic': dict(cell.epigenetic_state),
                }
                for name, cell in self.cells.items()
            },
            'total_events': len(self._all_events),
        }

    def reset(self) -> None:
        """Reset session to initial state."""
        self.beat = 0
        self.bar = 0
        self.phase = SessionPhase.HEAD
        self._phase_beats = 0
        self.shared_context['energy'] = 0.5
        self._all_events.clear()
        self._signals_log.clear()
        self._trading = None
        self._call_response = None

        for cell in self.cells.values():
            cell.reset_epigenetic()
            cell._history.clear()
            cell._last_output = []
            cell._last_pitch = cell.note_range[0]

        if self._seed is not None:
            random.seed(self._seed)

    def __repr__(self) -> str:
        return (
            f"JazzSession(key={self.key}, tempo={self.tempo}, "
            f"style={self.style!r}, phase={self.phase.value}, "
            f"beat={self.beat}, bar={self.bar})"
        )


# ── Convenience ──────────────────────────────────────────────────────────────

def create_cell(
    name: str,
    genome: str | list[float] = 'auto',
    **kwargs,
) -> MusicalCell:
    """Create a MusicalCell with an optional named genome.

    Parameters
    ----------
    name : str
        Instrument name.
    genome : str or list[float]
        'auto' picks based on name, or provide explicit genome.
    """
    genome_map = {
        'piano': piano_genome,
        'bass': bass_genome,
        'drums': drums_genome,
        'sax': sax_genome,
    }

    if genome == 'auto':
        genome_fn = genome_map.get(name, piano_genome)
        genome = genome_fn()

    return MusicalCell(name=name, genome=genome, **kwargs)


def quick_session(
    key: str = 'C',
    tempo: float = 120.0,
    style: str = 'bebop',
    bars: int = 32,
) -> tuple[JazzSession, Arrangement]:
    """Create and run a complete jazz session.

    Returns
    -------
    tuple[JazzSession, Arrangement]
        The session and its arrangement output.
    """
    session = JazzSession(key=key, tempo=tempo, style=style)
    arrangement = session.perform(bars=bars)
    return session, arrangement
