"""
Neural network–inspired music generation.

Operational transfer: neuroscience → music.

Neurons fire musical events when sufficiently stimulated.
Synapses carry signals between neurons. Hebbian plasticity
means the network reshapes itself during performance — same
input can produce different output as learning progresses.

Layers model cortical regions:
  - Auditory (input): receives current musical context
  - Pitch (tonal cortex): processes pitch relationships
  - Rhythm (motor cortex): processes temporal patterns
  - Emotion (limbic): evaluates emotional content
  - Memory (hippocampus): stores and recalls patterns
  - Decision (prefrontal): selects next action
  - Output (motor): generates MidiEvent instances

Zero external dependencies beyond flux-tensor-midi itself.
"""

from __future__ import annotations

import copy
import math
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

from flux_tensor_midi.midi import MidiEvent
from flux_tensor_midi.tracks import Arrangement, Track

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Consonance table: semitone interval → subjective consonance 0–1
_INTERVAL_CONSONANCE: dict[int, float] = {
    0: 0.95,   # unison
    1: 0.25,   # minor second
    2: 0.45,   # major second
    3: 0.70,   # minor third
    4: 0.80,   # major third
    5: 0.90,   # perfect fourth
    6: 0.30,   # tritone
    7: 0.92,   # perfect fifth
    8: 0.70,   # minor sixth
    9: 0.65,   # major sixth
    10: 0.50,  # minor seventh
    11: 0.40,  # major seventh
}


def _interval_consonance(semitones: int) -> float:
    """Return consonance rating for a pitch interval."""
    s = abs(semitones) % 12
    return _INTERVAL_CONSONANCE.get(s, 0.2)


def _sigmoid(x: float, gain: float = 1.0) -> float:
    """Logistic sigmoid."""
    x = max(-50.0, min(50.0, x * gain))
    return 1.0 / (1.0 + math.exp(-x))


def _tanh(x: float) -> float:
    return math.tanh(x)


def _softmax(values: list[float], temperature: float = 1.0) -> list[float]:
    """Numerically stable softmax."""
    if not values:
        return []
    m = max(values)
    exps = [math.exp((v - m) / max(temperature, 0.01)) for v in values]
    s = sum(exps)
    return [e / s for e in exps]


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Neurotransmitter types
# ---------------------------------------------------------------------------

class NeuroTransmitter(Enum):
    """Broad classification of synaptic signalling."""
    EXCITATORY = auto()
    INHIBITORY = auto()
    MODULATORY = auto()


# ---------------------------------------------------------------------------
# Synapse
# ---------------------------------------------------------------------------

@dataclass
class MusicalSynapse:
    """Weighted connection between two MusicalNeuron instances.

    Like a biological synapse: carries a signal from *pre* to *post*,
    modulated by weight and neurotransmitter type. Hebbian plasticity
    adjusts the weight depending on co-activation of pre and post.
    """

    pre_id: str
    post_id: str
    weight: float = 0.5
    neurotransmitter: NeuroTransmitter = NeuroTransmitter.EXCITATORY
    delay_ticks: int = 0          # transmission delay (ticks)
    eligibility: float = 0.0      # eligibility trace for learning
    max_weight: float = 2.0
    min_weight: float = -1.0

    def transmit(self, signal: float) -> float:
        """Return weighted signal, respecting neurotransmitter polarity."""
        base = signal * self.weight
        if self.neurotransmitter == NeuroTransmitter.INHIBITORY:
            return -abs(base)
        if self.neurotransmitter == NeuroTransmitter.MODULATORY:
            return base * 0.3  # weaker direct effect
        return base

    def hebbian_update(self, pre_active: bool, post_active: bool,
                       lr: float = 0.01, decay: float = 0.001) -> None:
        """Classic Hebbian update: Δw ∝ pre · post.

        Also includes weight decay toward zero to prevent runaway growth.
        """
        delta = lr * float(pre_active) * float(post_active)
        delta -= decay * self.weight  # L2 regularisation
        self.weight = _clamp(self.weight + delta,
                             self.min_weight, self.max_weight)
        # Update eligibility trace
        self.eligibility = 0.9 * self.eligibility + float(pre_active and post_active)


# ---------------------------------------------------------------------------
# MusicalNeuron
# ---------------------------------------------------------------------------

@dataclass
class MusicalNeuron:
    """A neuron that fires musical events when sufficiently stimulated.

    Integrates weighted inputs (membrane potential), fires when the
    potential exceeds *threshold* and the neuron is outside its refractory
    period. On firing it emits a MidiEvent.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    # Synaptic parameters
    threshold: float = 0.6
    refractory_ticks: int = 4
    leak: float = 0.05             # passive decay per tick
    noise_sigma: float = 0.02      # Gaussian noise on potential
    # Musical output
    note: int = 60                 # MIDI note number
    velocity: int = 80
    channel: int = 0
    duration_ticks: int = 8        # default duration in ticks
    # Internal state (not serialised by default)
    potential: float = 0.0
    ticks_since_fire: int = 100    # start outside refractory
    fired: bool = False
    fire_count: int = 0
    # Plasticity
    plasticity: float = 0.01

    # -- integration & firing ------------------------------------------------

    def receive(self, signal: float) -> None:
        """Add *signal* to membrane potential."""
        self.potential += signal

    def integrate(self) -> float:
        """Return current potential after leak + noise."""
        self.potential -= self.leak * self.potential
        self.potential += random.gauss(0, self.noise_sigma)
        self.ticks_since_fire += 1
        return self.potential

    def can_fire(self) -> bool:
        """Is the neuron outside its refractory period?"""
        return self.ticks_since_fire >= self.refractory_ticks

    def fire(self) -> Optional[MidiEvent]:
        """Fire if threshold exceeded and not refractory.

        Returns a MidiEvent on success or None.
        """
        self.fired = False
        if self.potential >= self.threshold and self.can_fire():
            self.fired = True
            self.fire_count += 1
            self.ticks_since_fire = 0
            # After firing, potential resets (spike-and-reset)
            fired_potential = self.potential
            self.potential = 0.0
            vel = _clamp(int(self.velocity * _sigmoid(fired_potential, 2.0)),
                         1, 127)
            return MidiEvent(
                note=self.note,
                velocity=vel,
                start_ms=0.0,       # caller sets absolute time
                duration_ms=float(self.duration_ticks),
                channel=self.channel,
            )
        return None

    def step(self) -> Optional[MidiEvent]:
        """One tick: integrate → fire cycle."""
        self.integrate()
        return self.fire()

    def reset(self) -> None:
        """Clear all dynamic state."""
        self.potential = 0.0
        self.ticks_since_fire = 100
        self.fired = False
        self.fire_count = 0

    # -- Hebbian learning ----------------------------------------------------

    def hebbian_learn(self, pre_active: bool, post_active: bool,
                      lr: Optional[float] = None) -> float:
        """Return a plasticity delta. Callers apply to synapse weights."""
        rate = lr if lr is not None else self.plasticity
        return rate * float(pre_active) * float(post_active)


# ---------------------------------------------------------------------------
# MusicalCortex — a cortical layer
# ---------------------------------------------------------------------------

class CortexType(Enum):
    AUDITORY = "auditory"
    PITCH = "pitch"
    RHYTHM = "rhythm"
    EMOTION = "emotion"
    MEMORY = "memory"
    DECISION = "decision"
    OUTPUT = "output"


@dataclass
class MusicalCortex:
    """A layer of MusicalNeuron instances organised by function.

    Like cortical columns: nearby neurons process similar features.
    """

    layer_type: CortexType = CortexType.PITCH
    neurons: list[MusicalNeuron] = field(default_factory=list)
    lateral_inhibition: float = 0.1   # winner-take-all suppression

    # ---- construction helpers ---------------------------------------------

    @classmethod
    def make_pitch_cortex(cls, root: int = 60, n: int = 12,
                          **kwargs) -> MusicalCortex:
        """Build a cortex spanning *n* semitones from *root*."""
        neurons = [
            MusicalNeuron(
                note=root + i,
                threshold=0.55 - 0.01 * i,      # lower notes slightly easier
                refractory_ticks=max(2, 6 - i // 3),
                duration_ticks=8 + i % 4,
                channel=0,
            )
            for i in range(n)
        ]
        return cls(layer_type=CortexType.PITCH, neurons=neurons, **kwargs)

    @classmethod
    def make_rhythm_cortex(cls, subdivision: int = 16,
                           **kwargs) -> MusicalCortex:
        """One neuron per rhythmic subdivision (e.g. 16th notes in a bar)."""
        neurons = [
            MusicalNeuron(
                note=35 + (i % 4 == 0),          # kick / side-stick
                velocity=100 if i % 4 == 0 else 60,
                threshold=0.5 + 0.02 * (i % 4),   # downbeats easier
                refractory_ticks=1,
                duration_ticks=2,
                channel=9,                         # GM drum channel
            )
            for i in range(subdivision)
        ]
        return cls(layer_type=CortexType.RHYTHM, neurons=neurons, **kwargs)

    @classmethod
    def make_emotion_cortex(cls, n: int = 6,
                            **kwargs) -> MusicalCortex:
        """Small cortex encoding emotional valence dimensions."""
        neurons = [
            MusicalNeuron(
                note=0,   # emotional neurons don't directly play notes
                threshold=0.4 + 0.08 * i,
                velocity=0,
                refractory_ticks=2,
            )
            for i in range(n)
        ]
        return cls(layer_type=CortexType.EMOTION, neurons=neurons, **kwargs)

    @classmethod
    def make_output_cortex(cls, root: int = 48, span: int = 24,
                           **kwargs) -> MusicalCortex:
        """Output neurons that produce the final MIDI events."""
        neurons = [
            MusicalNeuron(
                note=root + i,
                velocity=70 + int(20 * math.sin(math.pi * i / span)),
                threshold=0.5,
                refractory_ticks=4,
                duration_ticks=12,
            )
            for i in range(span)
        ]
        return cls(layer_type=CortexType.OUTPUT, neurons=neurons, **kwargs)

    # ---- activation -------------------------------------------------------

    def activate(self, input_signals: list[float]) -> list[bool]:
        """Present *input_signals* to neurons (one per neuron).

        Returns list of firing decisions.
        """
        fired: list[bool] = []
        for i, neuron in enumerate(self.neurons):
            sig = input_signals[i] if i < len(input_signals) else 0.0
            neuron.receive(sig)
            neuron.integrate()

        # Collect raw potentials before lateral inhibition
        potentials = [n.potential for n in self.neurons]
        max_pot = max(potentials) if potentials else 1.0

        for neuron in self.neurons:
            # Lateral inhibition: suppress neurons below max
            if self.lateral_inhibition > 0 and max_pot > 0:
                suppression = self.lateral_inhibition * (1.0 - neuron.potential / max(max_pot, 1e-6))
                neuron.potential -= suppression
            evt = neuron.fire()
            fired.append(neuron.fired)
        return fired

    def firing_pattern(self) -> list[bool]:
        """Return current firing state without stepping."""
        return [n.fired for n in self.neurons]

    def potentials(self) -> list[float]:
        return [n.potential for n in self.neurons]

    def reset(self) -> None:
        for n in self.neurons:
            n.reset()


# ---------------------------------------------------------------------------
# DopamineSystem
# ---------------------------------------------------------------------------

@dataclass
class DopamineSystem:
    """Reward system — tracks what sounds good.

    Models the mesolimbic pathway. Dopamine signals reward: consonance
    and surprise are rewarding; clichés are not. Over time, dopamine
    decays toward *baseline*, driving novelty-seeking behaviour.
    """

    baseline: float = 0.3
    current: float = 0.3
    decay_rate: float = 0.02        # per tick decay toward baseline
    reward_history: list[float] = field(default_factory=list)
    # Tuning
    consonance_weight: float = 0.5
    surprise_weight: float = 0.3
    novelty_weight: float = 0.2
    # Internal
    _recent_intervals: list[int] = field(default_factory=list)
    _max_history: int = 200

    # ---- reward computation -----------------------------------------------

    def reward(self, event_note: int, context_notes: list[int]) -> float:
        """Compute reward for an event given the current harmonic context.

        Consonance → reward. Surprise → reward. Cliché → no reward.
        """
        if not context_notes:
            r = 0.4  # neutral reward in empty context
        else:
            # Consonance component
            consonances = [_interval_consonance(event_note - cn)
                           for cn in context_notes]
            consonance = sum(consonances) / len(consonances)

            # Surprise component: how different from recent intervals?
            if self._recent_intervals:
                recent = self._recent_intervals[-12:]
                current_intervals = [abs(event_note - cn) % 12 for cn in context_notes]
                # Surprise = how unlike recent intervals
                similarities = [
                    max(0.0, 1.0 - abs(ci - ri) / 12.0)
                    for ci in current_intervals for ri in recent
                ]
                avg_sim = sum(similarities) / max(len(similarities), 1)
                surprise = 1.0 - avg_sim
            else:
                surprise = 0.5

            # Novelty: penalise exact repetition
            novelty = 0.5
            if self._recent_intervals:
                last = self._recent_intervals[-1]
                novelty = 0.3 if abs(event_note - context_notes[-1]) % 12 == last else 0.8

            r = (self.consonance_weight * consonance +
                 self.surprise_weight * surprise +
                 self.novelty_weight * novelty)

        # Record
        if context_notes:
            self._recent_intervals.append(abs(event_note - context_notes[-1]) % 12)
            if len(self._recent_intervals) > self._max_history:
                self._recent_intervals = self._recent_intervals[-self._max_history:]

        self.current = _clamp(self.baseline + r * 0.5)
        self.reward_history.append(r)
        if len(self.reward_history) > self._max_history:
            self.reward_history = self.reward_history[-self._max_history:]
        return r

    def withdrawal(self) -> None:
        """Dopamine decays back to baseline (one tick)."""
        self.current += self.decay_rate * (self.baseline - self.current)

    def tick(self) -> None:
        """Alias for withdrawal."""
        self.withdrawal()

    @property
    def average_reward(self) -> float:
        if not self.reward_history:
            return self.baseline
        return sum(self.reward_history[-50:]) / min(len(self.reward_history), 50)

    def reset(self) -> None:
        self.current = self.baseline
        self.reward_history.clear()
        self._recent_intervals.clear()


# ---------------------------------------------------------------------------
# Hippocampus — pattern memory
# ---------------------------------------------------------------------------

@dataclass
class MemoryPattern:
    """A stored sequence of neural activations."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    pattern: list[bool] = field(default_factory=list)
    reward: float = 0.0
    access_count: int = 0
    tick: int = 0          # when stored

    def similarity(self, other: list[bool]) -> float:
        """Hamming similarity (fraction of matching bits)."""
        if not self.pattern or not other:
            return 0.0
        length = min(len(self.pattern), len(other))
        matches = sum(1 for i in range(length) if self.pattern[i] == other[i])
        return matches / max(length, 1)


@dataclass
class Hippocampus:
    """Stores and recalls activation patterns.

    Like the hippocampus: encodes episodic memories (activation sequences)
    and replays them during sleep for consolidation.
    """

    patterns: list[MemoryPattern] = field(default_factory=list)
    capacity: int = 100
    consolidation_threshold: float = 0.6

    def store(self, pattern: list[bool], reward: float,
              tick: int = 0) -> Optional[MemoryPattern]:
        """Store a pattern if capacity allows."""
        mp = MemoryPattern(pattern=pattern[:], reward=reward, tick=tick)
        if len(self.patterns) >= self.capacity:
            # Evict lowest-reward pattern
            self.patterns.sort(key=lambda p: p.reward)
            self.patterns.pop(0)
        self.patterns.append(mp)
        return mp

    def recall(self, cue: list[bool], top_k: int = 3) -> list[MemoryPattern]:
        """Return *top_k* most similar stored patterns."""
        scored = [(p.similarity(cue), p) for p in self.patterns]
        scored.sort(key=lambda t: t[0], reverse=True)
        results = []
        for sim, pat in scored[:top_k]:
            pat.access_count += 1
            results.append(pat)
        return results

    def consolidate(self) -> int:
        """Strengthen well-rewarded patterns, prune weak ones.

        Returns number of patterns pruned.
        """
        before = len(self.patterns)
        self.patterns = [
            p for p in self.patterns
            if p.reward >= self.consolidation_threshold or p.access_count > 3
        ]
        # Boost surviving patterns' reward
        for p in self.patterns:
            p.reward = min(1.0, p.reward * 1.05)
        return before - len(self.patterns)

    def replay(self) -> list[list[bool]]:
        """Return all stored patterns (for sleep replay)."""
        return [p.pattern for p in self.patterns]


# ---------------------------------------------------------------------------
# MusicalBrain — full architecture
# ---------------------------------------------------------------------------

@dataclass
class MusicalBrain:
    """Full brain architecture for music generation.

    Layers:
      - Input (auditory cortex): receives current musical context
      - Pitch (tonal cortex): processes pitch relationships
      - Rhythm (motor cortex): processes temporal patterns
      - Emotion (limbic system): evaluates emotional content
      - Memory (hippocampus): stores and recalls patterns
      - Decision (prefrontal): selects next action
      - Output (motor): generates MIDI events

    NON-PRE-CALCULABLE: neural plasticity means the brain changes during
    performance. Same input → different output as learning progresses.
    """

    layers: dict[str, MusicalCortex] = field(default_factory=dict)
    synapses: list[MusicalSynapse] = field(default_factory=list)
    learning_rate: float = 0.02
    dopamine: DopamineSystem = field(default_factory=DopamineSystem)
    hippocampus: Hippocampus = field(default_factory=Hippocampus)
    tick: int = 0
    ticks_per_beat: int = 4          # 16th note resolution at 4/4
    bpm: float = 120.0
    root_note: int = 60
    scale: list[int] = field(default_factory=lambda: [0, 2, 4, 5, 7, 9, 11])
    # Epsilon: controls deviation from input stimulus
    epsilon: float = 0.5               # 0 = mimic, 1 = free improv
    # Stimulus buffer (set by hear())
    _stimulus: list[int] = field(default_factory=list)
    _stimulus_index: int = 0
    # Performance state
    _events: list[MidiEvent] = field(default_factory=list)
    _context_notes: list[int] = field(default_factory=list)
    _rng: random.Random = field(default_factory=lambda: random.Random())

    # ---- construction -----------------------------------------------------

    @classmethod
    def build(cls, root: int = 60, bpm: float = 120.0,
              scale: Optional[list[int]] = None,
              seed: Optional[int] = None,
              epsilon: float = 0.5) -> MusicalBrain:
        """Construct a full brain with default layer architecture."""
        rng = random.Random(seed)
        brain = cls(
            bpm=bpm,
            root_note=root,
            scale=scale or [0, 2, 4, 5, 7, 9, 11],
            epsilon=epsilon,
            _rng=rng,
        )

        # Build cortical layers
        brain.layers = {
            "auditory": MusicalCortex(
                layer_type=CortexType.AUDITORY,
                neurons=[MusicalNeuron(note=root + i, threshold=0.4,
                                       refractory_ticks=2)
                         for i in range(12)],
            ),
            "pitch": MusicalCortex.make_pitch_cortex(root=root, n=12),
            "rhythm": MusicalCortex.make_rhythm_cortex(subdivision=16),
            "emotion": MusicalCortex.make_emotion_cortex(n=6),
            "memory": MusicalCortex(
                layer_type=CortexType.MEMORY,
                neurons=[MusicalNeuron(note=0, threshold=0.5,
                                       refractory_ticks=3)
                         for _ in range(8)],
            ),
            "decision": MusicalCortex(
                layer_type=CortexType.DECISION,
                neurons=[MusicalNeuron(note=0, threshold=0.5,
                                       refractory_ticks=2)
                         for _ in range(8)],
            ),
            "output": MusicalCortex.make_output_cortex(root=root, span=24),
        }

        # Wire inter-layer synapses
        brain._wire_synapses()
        return brain

    def _wire_synapses(self) -> None:
        """Create initial synaptic connections between layers."""
        self.synapses.clear()
        connection_spec = [
            ("auditory", "pitch"),
            ("auditory", "rhythm"),
            ("auditory", "emotion"),
            ("pitch", "decision"),
            ("rhythm", "decision"),
            ("emotion", "decision"),
            ("memory", "decision"),
            ("decision", "output"),
        ]
        for pre_name, post_name in connection_spec:
            pre_layer = self.layers.get(pre_name)
            post_layer = self.layers.get(post_name)
            if pre_layer is None or post_layer is None:
                continue
            for pre_n in pre_layer.neurons:
                # Each pre neuron connects to a random subset of post neurons
                targets = self._rng.sample(
                    post_layer.neurons,
                    min(3, len(post_layer.neurons)),
                )
                for post_n in targets:
                    w = self._rng.gauss(0.5, 0.15)
                    nt = (NeuroTransmitter.EXCITATORY
                          if w > 0 else NeuroTransmitter.INHIBITORY)
                    self.synapses.append(MusicalSynapse(
                        pre_id=pre_n.id,
                        post_id=post_n.id,
                        weight=_clamp(w, -1.0, 2.0),
                        neurotransmitter=nt,
                    ))

    # ---- input methods (stimulus) ------------------------------------------

    def hear(self, midi_events: list[int]) -> None:
        """Feed MIDI note numbers to the auditory cortex.

        Stores the events as internal stimulus for the next perform() call.
        Also immediately activates the auditory cortex so perception is primed.
        """
        self._stimulus = list(midi_events)
        self._stimulus_index = 0

        # Immediately activate auditory cortex with the heard notes
        for neuron in self.layers["auditory"].neurons:
            min_dist = min((abs(neuron.note - n) for n in midi_events),
                           default=12)
            sig = max(0.0, 1.0 - min_dist / 12.0) * 0.8
            neuron.receive(sig)

        # Store in context for downstream processing
        self._context_notes.extend(midi_events)

    def _get_next_stimulus_note(self) -> Optional[int]:
        """Return the next stimulus note, cycling if exhausted."""
        if not self._stimulus:
            return None
        note = self._stimulus[self._stimulus_index % len(self._stimulus)]
        self._stimulus_index += 1
        return note

    def _apply_epsilon(self, note: int) -> int:
        """Apply epsilon deviation to a note.

        epsilon=0: return note unchanged (mimicry)
        epsilon=1: return a random scale note (free improv)
        """
        if self._rng.random() > self.epsilon:
            # Stay close to input — mimic
            deviation = self._rng.choice([-1, 0, 0, 0, 1])
            return max(0, min(127, note + deviation))
        else:
            # Free improv — pick from scale
            octave = note // 12
            degree = self._rng.choice(self.scale) if self.scale else self._rng.randint(0, 11)
            return max(0, min(127, octave * 12 + degree))

    def improvise(self, chord_progression: list[list[int]],
                  key: int = 60, tempo: float = 120.0,
                  bars: int = 8) -> Arrangement:
        """Generate music in response to harmonic context.

        Each chord in the progression provides context for one or more bars.
        The brain uses epsilon to control how closely it follows the harmony.
        """
        saved_bpm = self.bpm
        self.bpm = tempo

        self._events.clear()
        self._context_notes = [key]
        ticks_per_chord = (bars * 4 * self.ticks_per_beat) // max(len(chord_progression), 1)
        total_ticks = bars * 4 * self.ticks_per_beat
        ms_per_tick = 60000.0 / (self.bpm * self.ticks_per_beat)

        for t in range(total_ticks):
            self.tick = t
            # Select current chord
            chord_idx = min(t // max(ticks_per_chord, 1), len(chord_progression) - 1)
            current_chord = chord_progression[chord_idx]

            # Feed chord tones as stimulus
            self.hear(current_chord)

            perception = self.perceive(current_chord)
            events = self._generate_with_stimulus(perception, ms_per_tick)

            for evt in events:
                r = self.dopamine.reward(evt.note, self._context_notes[-8:])
                self.learn(r)
                self._context_notes.append(evt.note)
            self._events.extend(events)
            self.dopamine.withdrawal()

        self.bpm = saved_bpm
        return self._build_arrangement(f"improv_{key}", bars)

    def respond_to(self, other_performance: Arrangement,
                   bars: int = 8) -> Arrangement:
        """Musical conversation: call and response.

        Listens to the other performance, then generates a response.
        Uses epsilon to control how closely it follows vs. creates new material.
        """
        # Extract notes from the other performance
        other_notes: list[int] = []
        if other_performance.tracks:
            for track in other_performance.tracks:
                for evt in track.events:
                    other_notes.append(evt.note)

        if other_notes:
            self.hear(other_notes)

        self._events.clear()
        ms_per_tick = 60000.0 / (self.bpm * self.ticks_per_beat)
        total_ticks = bars * 4 * self.ticks_per_beat

        for t in range(total_ticks):
            self.tick = t
            # Use other performance notes as context
            context = other_notes[-12:] if other_notes else [self.root_note]
            perception = self.perceive(context)
            events = self._generate_with_stimulus(perception, ms_per_tick)

            for evt in events:
                r = self.dopamine.reward(evt.note, self._context_notes[-8:])
                self.learn(r)
                self._context_notes.append(evt.note)
            self._events.extend(events)
            self.dopamine.withdrawal()

        return self._build_arrangement(f"response_{self.root_note}", bars)

    def _generate_with_stimulus(self, perception: dict,
                                ms_per_tick: float) -> list[MidiEvent]:
        """Generate events using stimulus + epsilon deviation."""
        events: list[MidiEvent] = []
        decision_fired = perception.get("decision", [])
        output_layer = self.layers["output"]

        # Get stimulus note if available
        stim_note = self._get_next_stimulus_note()

        for i, neuron in enumerate(output_layer.neurons):
            # Decision-driven signal
            if i < len(decision_fired) and decision_fired[i]:
                neuron.receive(0.6 + self._rng.gauss(0, 0.1))
            else:
                neuron.receive(self._rng.gauss(0, 0.05))

            # Inject stimulus influence (inversely proportional to epsilon)
            if stim_note is not None:
                influence = (1.0 - self.epsilon) * 0.5
                min_dist = abs(neuron.note - stim_note)
                stim_signal = max(0.0, 1.0 - min_dist / 12.0) * influence
                neuron.receive(stim_signal)

            neuron.integrate()
            event = neuron.fire()
            if event is not None:
                # Apply epsilon to the output note
                if stim_note is not None:
                    note = self._apply_epsilon(stim_note)
                else:
                    note = self._snap_to_scale(event.note)
                note = max(0, min(127, note))
                timed = MidiEvent(
                    note=note,
                    velocity=event.velocity,
                    start_ms=self.tick * ms_per_tick,
                    duration_ms=neuron.duration_ticks * ms_per_tick,
                    channel=event.channel,
                )
                events.append(timed)
        return events

    def _build_arrangement(self, name: str, bars: int) -> Arrangement:
        """Build an Arrangement from current _events."""
        arrangement = Arrangement(
            name=name,
            bpm=self.bpm,
            bars=bars,
        )
        if self._events:
            track = Track(name="neural_brain", voice="piano")
            for evt in self._events:
                track._events.append(evt)
            arrangement.add_track(track)
        return arrangement

    # ---- perception -------------------------------------------------------

    def perceive(self, context_notes: Optional[list[int]] = None) -> dict:
        """Process current musical context through all layers.

        Returns a perception dict with layer activations and potentials.
        """
        ctx = context_notes or self._context_notes
        # Auditory cortex: encode context as input signals
        auditory_signals: list[float] = []
        for neuron in self.layers["auditory"].neurons:
            # How close is this neuron's note to any context note?
            min_dist = min((abs(neuron.note - cn) for cn in ctx),
                           default=12)
            sig = max(0.0, 1.0 - min_dist / 12.0)
            auditory_signals.append(sig)

        auditory_fired = self.layers["auditory"].activate(auditory_signals)

        # Propagate through synapses to other layers
        self._propagate_signals()

        # Activate pitch cortex
        pitch_signals = [
            _sigmoid(sum(
                n.potential for n in self.layers["pitch"].neurons
            ) / max(len(self.layers["pitch"].neurons), 1)) * 0.5
            + self._rng.gauss(0, 0.1)
            for _ in self.layers["pitch"].neurons
        ]
        pitch_fired = self.layers["pitch"].activate(pitch_signals)

        # Activate rhythm cortex
        rhythm_phase = (self.tick % 16) / 16.0
        rhythm_signals = [
            _sigmoid(math.sin(2 * math.pi * (i / 16.0 + rhythm_phase)))
            for i in range(len(self.layers["rhythm"].neurons))
        ]
        rhythm_fired = self.layers["rhythm"].activate(rhythm_signals)

        # Activate emotion cortex
        emotion_signals = [
            self.dopamine.current + self._rng.gauss(0, 0.1)
            for _ in self.layers["emotion"].neurons
        ]
        emotion_fired = self.layers["emotion"].activate(emotion_signals)

        # Memory retrieval
        full_pattern = auditory_fired + pitch_fired + emotion_fired
        recalled = self.hippocampus.recall(full_pattern, top_k=2)
        memory_signals = [
            sum(r.reward for r in recalled) / max(len(recalled), 1)
            for _ in self.layers["memory"].neurons
        ]
        self.layers["memory"].activate(memory_signals)

        # Decision cortex: integrate all
        decision_signals: list[float] = []
        for neuron in self.layers["decision"].neurons:
            signal = (
                0.3 * sum(1 for f in pitch_fired if f) / max(len(pitch_fired), 1)
                + 0.2 * sum(1 for f in rhythm_fired if f) / max(len(rhythm_fired), 1)
                + 0.2 * sum(1 for f in emotion_fired if f) / max(len(emotion_fired), 1)
                + 0.2 * self.dopamine.current
                + 0.1 * self._rng.gauss(0, 0.3)
            )
            decision_signals.append(signal)
        decision_fired = self.layers["decision"].activate(decision_signals)

        return {
            "auditory": auditory_fired,
            "pitch": pitch_fired,
            "rhythm": rhythm_fired,
            "emotion": emotion_fired,
            "decision": decision_fired,
            "tick": self.tick,
        }

    def _propagate_signals(self) -> None:
        """Propagate signals through all synapses."""
        # Build neuron id → neuron lookup
        all_neurons: dict[str, MusicalNeuron] = {}
        for layer in self.layers.values():
            for n in layer.neurons:
                all_neurons[n.id] = n

        for syn in self.synapses:
            pre = all_neurons.get(syn.pre_id)
            post = all_neurons.get(syn.post_id)
            if pre is None or post is None:
                continue
            signal = syn.transmit(pre.potential)
            post.receive(signal)

    # ---- decision ---------------------------------------------------------

    def decide(self, perception: dict) -> list[MidiEvent]:
        """Prefrontal cortex decides what to play next.

        Uses decision layer activations to select output neurons.
        Delegates to _generate_with_stimulus when stimulus is available.
        """
        ms_per_tick = 60000.0 / (self.bpm * self.ticks_per_beat)

        # If we have stimulus, use the epsilon-aware generation
        if self._stimulus:
            return self._generate_with_stimulus(perception, ms_per_tick)

        # Original path: no stimulus, purely internal generation
        decision_fired = perception.get("decision", [])
        events: list[MidiEvent] = []

        output_layer = self.layers["output"]
        for i, neuron in enumerate(output_layer.neurons):
            if i < len(decision_fired) and decision_fired[i]:
                neuron.receive(0.6 + self._rng.gauss(0, 0.1))
            else:
                neuron.receive(self._rng.gauss(0, 0.05))

            neuron.integrate()
            event = neuron.fire()
            if event is not None:
                snapped = self._snap_to_scale(event.note)
                timed = MidiEvent(
                    note=max(0, min(127, snapped)),
                    velocity=event.velocity,
                    start_ms=self.tick * ms_per_tick,
                    duration_ms=neuron.duration_ticks * ms_per_tick,
                    channel=event.channel,
                )
                events.append(timed)

        return events

    def _snap_to_scale(self, note: int) -> int:
        """Snap a note to the nearest scale degree."""
        if not self.scale:
            return note
        octave = note // 12
        pitch_class = note % 12
        # Find closest scale degree
        best = min(self.scale, key=lambda s: abs(s - pitch_class))
        return octave * 12 + best

    # ---- learning ---------------------------------------------------------

    def learn(self, reward: float) -> None:
        """Dopamine-modulated Hebbian learning.

        Connections that led to reward are strengthened.
        Connections that led to poor outcomes are weakened.
        """
        modulation = reward - self.dopamine.baseline  # positive = better than expected
        lr = self.learning_rate * max(0.0, modulation)

        # Build neuron id → fired map
        all_fired: dict[str, bool] = {}
        for layer in self.layers.values():
            for n in layer.neurons:
                all_fired[n.id] = n.fired

        for syn in self.synapses:
            pre_active = all_fired.get(syn.pre_id, False)
            post_active = all_fired.get(syn.post_id, False)
            syn.hebbian_update(pre_active, post_active, lr=lr)

        # If reward was very low, also weaken some connections
        if reward < self.dopamine.baseline * 0.5:
            for syn in self.synapses:
                if self._rng.random() < 0.1:
                    syn.weight *= 0.95

    # ---- full performance -------------------------------------------------

    def perform(self, bars: int = 32,
                stimulus: Optional[list[int]] = None) -> Arrangement:
        """Full performance with real-time learning.

        If *stimulus* is provided (list of MIDI note numbers), feeds it via
        hear() first. If no stimulus and none was previously heard, uses an
        internal rhythm generator as fallback so output is never empty.

        The brain gets better (or worse) as it plays.
        Returns an Arrangement ready for MIDI export.
        """
        if stimulus is not None:
            self.hear(stimulus)

        # Fallback: if no stimulus at all, use internal rhythm generator
        if not self._stimulus:
            self._generate_internal_stimulus()

        total_ticks = bars * 4 * self.ticks_per_beat  # 4/4 time
        self._events.clear()
        if not self._context_notes:
            self._context_notes = [self.root_note]
        ms_per_tick = 60000.0 / (self.bpm * self.ticks_per_beat)

        for t in range(total_ticks):
            self.tick = t

            # Perceive current context
            perception = self.perceive(self._context_notes[-12:])

            # Decide what to play (uses stimulus + epsilon)
            events = self._generate_with_stimulus(perception, ms_per_tick)

            # Evaluate and learn
            for evt in events:
                r = self.dopamine.reward(evt.note, self._context_notes[-8:])
                self.learn(r)
                self._context_notes.append(evt.note)

            self._events.extend(events)

            # Dopamine decay each tick
            self.dopamine.withdrawal()

            # Periodically store patterns in hippocampus
            if t % 16 == 0 and t > 0:
                pattern = []
                for layer in self.layers.values():
                    pattern.extend(n.fired for n in layer.neurons)
                self.hippocampus.store(pattern, self.dopamine.current, tick=t)

        return self._build_arrangement(f"neural_perf_{self.root_note}", bars)

    def _generate_internal_stimulus(self) -> None:
        """Create an internal stimulus from scale + rhythm patterns."""
        # Generate a melodic pattern from the current scale
        pattern: list[int] = []
        for i in range(8):
            degree = self.scale[i % len(self.scale)] if self.scale else 0
            octave = (i // len(self.scale)) if self.scale else 0
            note = self.root_note + degree + octave * 12
            pattern.append(max(0, min(127, note)))
        self._stimulus = pattern
        self._stimulus_index = 0

    # ---- sleep (memory consolidation) -------------------------------------

    def sleep(self) -> dict:
        """Memory consolidation during 'sleep'.

        Replay the day's patterns, strengthen important ones,
        prune weak connections.
        Returns consolidation statistics.
        """
        pruned_patterns = self.hippocampus.consolidate()
        pruned_synapses = 0

        # Prune weak synapses
        surviving: list[MusicalSynapse] = []
        for syn in self.synapses:
            if abs(syn.weight) < 0.01 and syn.eligibility < 0.1:
                pruned_synapses += 1
            else:
                surviving.append(syn)
        self.synapses = surviving

        # Replay patterns to strengthen active pathways
        replays = self.hippocampus.replay()
        for pattern in replays:
            # Simulate a quick activation
            idx = 0
            for layer in self.layers.values():
                for neuron in layer.neurons:
                    if idx < len(pattern) and pattern[idx]:
                        neuron.potential = 0.7
                    else:
                        neuron.potential = 0.0
                    idx += 1

        # Reset dynamic state
        for layer in self.layers.values():
            for n in layer.neurons:
                n.potential = 0.0
                n.fired = False
                n.ticks_since_fire = 100

        return {
            "pruned_patterns": pruned_patterns,
            "pruned_synapses": pruned_synapses,
            "remaining_patterns": len(self.hippocampus.patterns),
            "remaining_synapses": len(self.synapses),
            "replays": len(replays),
        }

    # ---- reset / info -----------------------------------------------------

    def reset(self) -> None:
        """Full reset to initial state."""
        self.tick = 0
        self._events.clear()
        self._context_notes.clear()
        self.dopamine.reset()
        for layer in self.layers.values():
            layer.reset()

    def stats(self) -> dict:
        """Return current brain statistics."""
        total_fires = sum(
            n.fire_count
            for layer in self.layers.values()
            for n in layer.neurons
        )
        total_neurons = sum(
            len(layer.neurons) for layer in self.layers.values()
        )
        avg_weight = (
            sum(s.weight for s in self.synapses) / max(len(self.synapses), 1)
        )
        return {
            "tick": self.tick,
            "total_neurons": total_neurons,
            "total_synapses": len(self.synapses),
            "total_fires": total_fires,
            "avg_synapse_weight": round(avg_weight, 4),
            "dopamine": round(self.dopamine.current, 4),
            "avg_reward": round(self.dopamine.average_reward, 4),
            "stored_patterns": len(self.hippocampus.patterns),
        }


# ---------------------------------------------------------------------------
# Helper: build Arrangement from brain performance
# ---------------------------------------------------------------------------

def neural_performance(root: int = 60, bpm: float = 120.0,
                       bars: int = 16,
                       scale: Optional[list[int]] = None,
                       seed: Optional[int] = None) -> Arrangement:
    """Convenience: build a brain, perform, and return the Arrangement."""
    brain = MusicalBrain.build(root=root, bpm=bpm, scale=scale, seed=seed)
    arr = brain.perform(bars=bars)
    return arr
