"""
Tests for the Living Constraint System — MusicalCell and JazzSession.

50+ tests covering:
- TranscriptionFactor activation/suppression
- MusicalCell receive/express/emit cycle
- Epigenetic state updates
- TradingFours alternation
- CallAndResponse signal protocol
- Vamp waiting and transition
- JazzSession full lifecycle
- NON-PRE-CALCULABILITY: stochastic TFs produce different outputs
"""

import random
import pytest
from flux_tensor_midi.living import (
    GENOME_SIZE,
    SignalType,
    TranscriptionFactor,
    ConstraintCompiler,
    DynamicsEngine,
    MusicalCell,
    TradingFours,
    CallAndResponse,
    Vamp,
    JazzSession,
    SessionPhase,
    piano_genome,
    bass_genome,
    drums_genome,
    sax_genome,
    create_cell,
    quick_session,
    _wire_piano_tfs,
    _wire_bass_tfs,
    _wire_drums_tfs,
    _wire_sax_tfs,
)
from flux_tensor_midi.midi.events import MidiEvent


# ── TranscriptionFactor Tests ────────────────────────────────────────────────

class TestTranscriptionFactor:
    """Test TF activation and suppression mechanics."""

    def test_basic_activation(self):
        """TF with activator signal should exceed baseline 0.5."""
        tf = TranscriptionFactor(
            gene_index=0,
            activators=[SignalType.ENERGY],
            sensitivity=1.0,
        )
        # Seed for reproducibility within this test
        random.seed(42)
        result = tf.evaluate({SignalType.ENERGY: 0.8})
        assert result > 0.5, f"Expected activation > 0.5, got {result}"

    def test_basic_suppression(self):
        """TF with suppressor signal should fall below baseline 0.5."""
        tf = TranscriptionFactor(
            gene_index=0,
            suppressors=[SignalType.REST],
            sensitivity=1.5,
        )
        random.seed(42)
        result = tf.evaluate({SignalType.REST: 0.9})
        assert result < 0.5, f"Expected suppression < 0.5, got {result}"

    def test_no_signals_returns_near_baseline(self):
        """TF with no matching signals should be near 0.5 baseline."""
        tf = TranscriptionFactor(gene_index=0, sensitivity=0.1)
        random.seed(42)
        result = tf.evaluate({})
        assert 0.4 < result < 0.6, f"Expected near baseline, got {result}"

    def test_clamp_high(self):
        """TF activation should be clamped to 1.0."""
        tf = TranscriptionFactor(
            gene_index=0,
            activators=[SignalType.ENERGY, SignalType.DENSITY, SignalType.ACCENT],
            sensitivity=2.0,
        )
        result = tf.evaluate({
            SignalType.ENERGY: 1.0,
            SignalType.DENSITY: 1.0,
            SignalType.ACCENT: 1.0,
        })
        assert result <= 1.0

    def test_clamp_low(self):
        """TF activation should be clamped to 0.0."""
        tf = TranscriptionFactor(
            gene_index=0,
            suppressors=[SignalType.REST, SignalType.TENSION],
            sensitivity=2.0,
        )
        result = tf.evaluate({
            SignalType.REST: 1.0,
            SignalType.TENSION: 1.0,
        })
        assert result >= 0.0

    def test_invalid_gene_index(self):
        """Gene index out of range should raise ValueError."""
        with pytest.raises(ValueError):
            TranscriptionFactor(gene_index=999)
        with pytest.raises(ValueError):
            TranscriptionFactor(gene_index=-1)

    def test_negative_sensitivity(self):
        """Negative sensitivity should raise ValueError."""
        with pytest.raises(ValueError):
            TranscriptionFactor(gene_index=0, sensitivity=-0.1)

    def test_last_activation_tracking(self):
        """TF should track its last activation value."""
        tf = TranscriptionFactor(gene_index=0, activators=[SignalType.ENERGY], sensitivity=1.0)
        tf.evaluate({SignalType.ENERGY: 0.5})
        assert tf.last_activation == tf.last_activation  # just check it's set
        assert 0.0 <= tf.last_activation <= 1.0

    def test_stochastic_noise(self):
        """Repeated evaluations with same input should vary (stochastic noise)."""
        tf = TranscriptionFactor(gene_index=0, sensitivity=1.0)
        results = set()
        for _ in range(20):
            results.add(tf.evaluate({SignalType.ENERGY: 0.6}))
        # Should have at least a few different values due to noise
        assert len(results) > 1, "Expected stochastic variation in TF evaluation"


# ── ConstraintCompiler Tests ────────────────────────────────────────────────

class TestConstraintCompiler:
    """Test ribosome constraint compilation."""

    def test_compile_returns_dict(self):
        """Compiled constraints should be a dict with expected keys."""
        genome = [0.5] * GENOME_SIZE
        epi = {i: 1.0 for i in range(GENOME_SIZE)}
        cc = ConstraintCompiler(genome, epi)
        result = cc.compile({}, {'key_center': 60})
        assert isinstance(result, dict)
        assert 'pitch_weight' in result
        assert 'velocity_target' in result
        assert 'density' in result

    def test_epigenetic_modulation(self):
        """Silenced genes (epi=0) should produce zero effective values."""
        genome = [1.0] * GENOME_SIZE
        epi = {i: 0.0 for i in range(GENOME_SIZE)}
        cc = ConstraintCompiler(genome, epi)
        result = cc.compile({}, {'key_center': 60})
        # All constraints should be zero when all genes silenced
        assert result['density'] == pytest.approx(0.0)

    def test_tf_activation_modulation(self):
        """TF activations should modulate effective gene values."""
        genome = [1.0] * GENOME_SIZE
        epi = {i: 1.0 for i in range(GENOME_SIZE)}
        cc = ConstraintCompiler(genome, epi)

        no_tf = cc.compile({}, {'key_center': 60})
        with_tf = cc.compile({0: 2.0}, {'key_center': 60})

        # With TF activation > 1.0, values should be larger
        assert with_tf['consensus'] > no_tf['consensus']


# ── DynamicsEngine Tests ─────────────────────────────────────────────────────

class TestDynamicsEngine:
    """Test mitochondria (dynamics engine)."""

    def test_initial_energy(self):
        """Engine should start with specified base energy."""
        engine = DynamicsEngine(base_energy=0.7)
        assert engine.energy == pytest.approx(0.7)

    def test_energy_update(self):
        """Energy should blend toward incoming ensemble energy."""
        engine = DynamicsEngine(base_energy=0.5)
        engine.update(incoming_energy=0.9, autonomy=0.3)
        assert engine.energy > 0.5

    def test_energy_clamp(self):
        """Energy should be clamped to [0, 1]."""
        engine = DynamicsEngine(base_energy=0.99)
        engine.update(1.0, 0.0)
        assert engine.energy <= 1.0

    def test_velocity_range(self):
        """Computed velocity should be in [1, 127]."""
        engine = DynamicsEngine()
        for _ in range(100):
            vel = engine.compute_velocity(80, 30, 0.5, 0.5)
            assert 1 <= vel <= 127

    def test_duration_positive(self):
        """Computed duration should always be positive."""
        engine = DynamicsEngine()
        for _ in range(100):
            dur = engine.compute_duration(500, 0.5, 0.5, 0.5, 4, 16)
            assert dur > 0

    def test_boost_and_decay(self):
        """Boost should increase energy, decay should decrease it."""
        engine = DynamicsEngine(base_energy=0.3)
        engine.boost(0.5)
        assert engine.energy > 0.3
        old = engine.energy
        engine.decay()
        assert engine.energy < old


# ── MusicalCell Tests ────────────────────────────────────────────────────────

class TestMusicalCell:
    """Test MusicalCell receive/express/emit cycle."""

    def test_creation(self):
        """Cell should be created with valid genome."""
        cell = MusicalCell('piano', piano_genome(), channel=0)
        assert cell.name == 'piano'
        assert len(cell.genome) == GENOME_SIZE
        assert len(cell.history) == 0

    def test_invalid_genome_length(self):
        """Wrong genome length should raise ValueError."""
        with pytest.raises(ValueError):
            MusicalCell('bad', [0.5] * 10)

    def test_receive_filters_signals(self):
        """Membrane should filter signals to only receptor types."""
        cell = MusicalCell('piano', piano_genome())
        cell.receptors = [SignalType.ENERGY, SignalType.DENSITY]
        cell.receive({
            SignalType.ENERGY: 0.8,
            SignalType.TENSION: 0.5,
            SignalType.DENSITY: 0.6,
        })
        # Should have only ENERGY and DENSITY
        assert SignalType.ENERGY in cell._filtered_signals
        assert SignalType.DENSITY in cell._filtered_signals
        assert SignalType.TENSION not in cell._filtered_signals

    def test_update_tfs(self):
        """TFs should be updated with signal evaluations."""
        cell = MusicalCell('piano', piano_genome())
        cell.tfs = [
            TranscriptionFactor(0, activators=[SignalType.ENERGY], sensitivity=1.0),
        ]
        cell.update_tfs({SignalType.ENERGY: 0.8})
        assert 0 in cell._tf_activations
        assert cell._tf_activations[0] > 0.5

    def test_express_produces_events(self):
        """Express should produce MidiEvents."""
        cell = MusicalCell('sax', sax_genome(), channel=2, note_range=(54, 84))
        cell.tfs = _wire_sax_tfs()
        events = cell.express({
            'beat': 0, 'bar': 0, 'tempo': 120,
            'key_center': 60,
            'scale': [0, 2, 4, 5, 7, 9, 11],
            'energy': 0.6,
        })
        # May or may not produce events depending on space gene + randomness
        assert isinstance(events, list)

    def test_emit_returns_signals(self):
        """Emit should return a dict of SignalType → float."""
        cell = MusicalCell('piano', piano_genome(), channel=0)
        # Give it some output to emit from
        cell._last_output = [MidiEvent(60, 80, 0.0, 200.0, 0)]
        signals = cell.emit()
        assert isinstance(signals, dict)
        assert SignalType.ENERGY in signals

    def test_emit_empty_returns_rest(self):
        """Emit with no output should signal REST."""
        cell = MusicalCell('piano', piano_genome())
        signals = cell.emit([])
        assert SignalType.REST in signals

    def test_full_cycle(self):
        """Receive → update_tfs → express → emit should complete."""
        cell = MusicalCell('sax', sax_genome(), channel=2)
        cell.tfs = _wire_sax_tfs()

        signals_in = {SignalType.ENERGY: 0.7, SignalType.RHYTHM: 0.5}
        cell.receive(signals_in)
        cell.update_tfs(signals_in)
        events = cell.express({
            'beat': 4, 'bar': 1, 'tempo': 120,
            'key_center': 60,
            'scale': [0, 2, 4, 5, 7, 9, 11],
            'energy': 0.6,
        })
        signals_out = cell.emit(events)

        assert len(cell.history) == 1
        assert isinstance(events, list)
        assert isinstance(signals_out, dict)

    def test_learn_updates_epigenetic(self):
        """Learning should modify epigenetic state."""
        cell = MusicalCell('piano', piano_genome())
        old_epi = dict(cell.epigenetic_state)
        cell.learn({'overall': 0.9, 'rhythmic_fit': 0.8, 'harmonic_fit': 0.7, 'dynamic_fit': 0.8})
        # Something should have changed
        changed = any(
            cell.epigenetic_state[k] != old_epi[k]
            for k in old_epi
        )
        assert changed

    def test_learn_negative_feedback(self):
        """Negative feedback should generally downregulate genes."""
        cell = MusicalCell('piano', piano_genome())
        cell.learn({'overall': 0.1, 'rhythmic_fit': 0.1, 'harmonic_fit': 0.1, 'dynamic_fit': 0.1})
        # Overall low feedback should reduce most epigenetic values below baseline
        below_count = sum(1 for i in range(GENOME_SIZE) if cell.epigenetic_state[i] < 1.0)
        assert below_count > GENOME_SIZE // 2, f"Expected most genes below 1.0, only {below_count} are"

    def test_reset_epigenetic(self):
        """Reset should restore epigenetic state to baseline."""
        cell = MusicalCell('piano', piano_genome())
        cell.learn({'overall': 0.1, 'rhythmic_fit': 0.1, 'harmonic_fit': 0.1, 'dynamic_fit': 0.1})
        cell.reset_epigenetic()
        for i in range(GENOME_SIZE):
            assert cell.epigenetic_state[i] == pytest.approx(1.0)

    def test_history_grows(self):
        """History should accumulate with each express call."""
        cell = MusicalCell('piano', piano_genome())
        for beat in range(5):
            cell.express({'beat': beat, 'bar': beat // 4, 'tempo': 120, 'energy': 0.5})
        assert len(cell.history) == 5


# ── TradingFours Tests ───────────────────────────────────────────────────────

class TestTradingFours:
    """Test trading fours alternation."""

    def test_creation(self):
        """TradingFours should be created with two cells."""
        a = MusicalCell('sax', sax_genome(), channel=2)
        b = MusicalCell('drums', drums_genome(), channel=9)
        tf = TradingFours(a, b, phrase_length=4)
        assert tf.phrase_length == 4

    def test_alternation(self):
        """Should alternate between cell A and cell B."""
        a = MusicalCell('sax', sax_genome(), channel=2)
        b = MusicalCell('drums', drums_genome(), channel=9)
        a.tfs = _wire_sax_tfs()
        b.tfs = _wire_drums_tfs()
        tf = TradingFours(a, b, phrase_length=4)

        # First 16 beats (4 bars): cell A
        # Next 16 beats: cell B
        a_count = 0
        b_count = 0
        for beat in range(32):
            events = tf.round(beat, {'tempo': 120, 'key_center': 60, 'scale': [0, 2, 4, 5, 7, 9, 11], 'energy': 0.5})
            # Check which cell was soloist
            if tf.current_soloist.name == 'sax':
                a_count += 1
            else:
                b_count += 1

        # Should have approximately equal turns
        assert a_count > 0 and b_count > 0

    def test_signal_exchange(self):
        """Each round should exchange signals between cells."""
        a = MusicalCell('sax', sax_genome(), channel=2)
        b = MusicalCell('drums', drums_genome(), channel=9)
        a.tfs = _wire_sax_tfs()
        b.tfs = _wire_drums_tfs()
        tf = TradingFours(a, b, phrase_length=4)

        ctx = {'tempo': 120, 'key_center': 60, 'scale': [0, 2, 4, 5, 7, 9, 11], 'energy': 0.5}
        tf.round(0, ctx)
        tf.round(1, ctx)
        # After a few rounds, signals should have been exchanged
        assert len(tf._last_a_signals) > 0 or len(tf._last_b_signals) > 0


# ── CallAndResponse Tests ────────────────────────────────────────────────────

class TestCallAndResponse:
    """Test call-response signal protocol."""

    def test_call_produces_output(self):
        """Call should produce events and signals."""
        caller = MusicalCell('sax', sax_genome(), channel=2)
        caller.tfs = _wire_sax_tfs()
        responder = MusicalCell('piano', piano_genome(), channel=0)
        responder.tfs = _wire_piano_tfs()

        cr = CallAndResponse(caller, responder, call_length=4, response_length=4)
        events, signals = cr.call({'beat': 0, 'bar': 0, 'tempo': 120, 'energy': 0.5})
        assert isinstance(events, list)
        assert isinstance(signals, dict)

    def test_respond_produces_output(self):
        """Respond should produce events informed by call signals."""
        caller = MusicalCell('sax', sax_genome(), channel=2)
        caller.tfs = _wire_sax_tfs()
        responder = MusicalCell('piano', piano_genome(), channel=0)
        responder.tfs = _wire_piano_tfs()

        cr = CallAndResponse(caller, responder)
        call_events, call_signals = cr.call({'beat': 0, 'bar': 0, 'tempo': 120, 'energy': 0.5})
        response = cr.respond(call_events, call_signals, {'beat': 4, 'bar': 1, 'tempo': 120, 'energy': 0.5})
        assert isinstance(response, list)

    def test_tick_cycles_phases(self):
        """Tick should cycle between call and response phases."""
        caller = MusicalCell('sax', sax_genome(), channel=2)
        caller.tfs = _wire_sax_tfs()
        responder = MusicalCell('piano', piano_genome(), channel=0)
        responder.tfs = _wire_piano_tfs()

        cr = CallAndResponse(caller, responder, call_length=4, response_length=4)
        ctx = {'tempo': 120, 'key_center': 60, 'scale': [0, 2, 4, 5, 7, 9, 11], 'energy': 0.5}

        # First 4 ticks = call phase
        for i in range(4):
            cr.tick(i, ctx)
        assert cr.phase == 'response'

        # Next 4 ticks = response phase
        for i in range(4, 8):
            cr.tick(i, ctx)
        assert cr.phase == 'call'

    def test_phase_starts_as_call(self):
        """Initial phase should be 'call'."""
        caller = MusicalCell('sax', sax_genome(), channel=2)
        responder = MusicalCell('piano', piano_genome(), channel=0)
        cr = CallAndResponse(caller, responder)
        assert cr.phase == 'call'


# ── Vamp Tests ───────────────────────────────────────────────────────────────

class TestVamp:
    """Test vamp pattern and transition."""

    def test_creation(self):
        """Vamp should be created with a pattern."""
        pattern = [MidiEvent(60, 80, 0.0, 200.0, 0)]
        vamp = Vamp(pattern, bars=2)
        assert vamp.waiting is True
        assert vamp.bars == 2

    def test_tick_repeats_pattern(self):
        """Tick should repeat the vamp pattern."""
        pattern = [
            MidiEvent(60, 80, 0.0, 200.0, 0),
            MidiEvent(64, 70, 500.0, 200.0, 0),
        ]
        vamp = Vamp(pattern, bars=2)
        events = vamp.tick(0, tempo=120)
        assert isinstance(events, list)

    def test_transition_on_soloist_signal(self):
        """Vamp should stop waiting when soloist signals."""
        pattern = [MidiEvent(60, 80, 0.0, 200.0, 0)]
        vamp = Vamp(pattern, bars=2)
        assert vamp.waiting is True

        vamp.tick(0, soloist_input={SignalType.SOLO_INDICATOR: 0.9})
        assert vamp.waiting is False
        assert vamp.should_transition is True

    def test_transition_on_high_energy(self):
        """Vamp should transition on high energy signal."""
        pattern = [MidiEvent(60, 80, 0.0, 200.0, 0)]
        vamp = Vamp(pattern, bars=2)
        vamp.tick(0, soloist_input={SignalType.ENERGY: 0.8})
        assert vamp.should_transition

    def test_no_transition_without_signal(self):
        """Vamp should stay waiting without soloist signal."""
        pattern = [MidiEvent(60, 80, 0.0, 200.0, 0)]
        vamp = Vamp(pattern, bars=2)
        vamp.tick(0)
        assert vamp.waiting is True

    def test_reset(self):
        """Reset should restore waiting state."""
        pattern = [MidiEvent(60, 80, 0.0, 200.0, 0)]
        vamp = Vamp(pattern, bars=2)
        vamp.tick(0, soloist_input={SignalType.SOLO_INDICATOR: 0.9})
        assert vamp.should_transition
        vamp.reset()
        assert vamp.waiting is True
        assert vamp.loop_count == 0


# ── JazzSession Tests ────────────────────────────────────────────────────────

class TestJazzSession:
    """Test full session lifecycle."""

    def test_creation(self):
        """Session should be created with correct parameters."""
        session = JazzSession(key='Bb', tempo=140, style='bebop')
        assert session.key == 'Bb'
        assert session.tempo == 140
        assert session.phase == SessionPhase.HEAD
        assert len(session.cells) == 4
        assert 'piano' in session.cells
        assert 'bass' in session.cells
        assert 'drums' in session.cells
        assert 'sax' in session.cells

    def test_tick_produces_events(self):
        """Each tick should produce MIDI events."""
        random.seed(42)
        session = JazzSession(key='C', tempo=120)
        events = session.tick()
        assert isinstance(events, list)
        assert session.beat == 1

    def test_phase_transitions(self):
        """Session should transition through phases."""
        session = JazzSession(key='C', tempo=120, style='bebop')
        phases_seen = {session.phase}

        # Run enough beats to see phase transitions
        for _ in range(300):
            session.tick()
            phases_seen.add(session.phase)
            if session.phase == SessionPhase.ENDED:
                break

        # Should have seen multiple phases
        assert len(phases_seen) >= 3, f"Only saw phases: {phases_seen}"

    def test_perform_returns_arrangement(self):
        """Perform should return a complete Arrangement."""
        random.seed(42)
        session = JazzSession(key='C', tempo=120)
        arrangement = session.perform(bars=16)
        assert arrangement is not None
        assert len(arrangement.tracks) > 0

    def test_session_state(self):
        """get_session_state should return valid state dict."""
        random.seed(42)
        session = JazzSession(key='C', tempo=120)
        session.tick()
        state = session.get_session_state()
        assert 'phase' in state
        assert 'beat' in state
        assert 'energy' in state
        assert 'cells' in state
        assert state['beat'] == 1

    def test_reset(self):
        """Reset should return session to initial state."""
        session = JazzSession(key='C', tempo=120)
        for _ in range(20):
            session.tick()
        session.reset()
        assert session.beat == 0
        assert session.phase == SessionPhase.HEAD

    def test_different_keys(self):
        """Session should work with different key centers."""
        for key in ['C', 'F', 'Bb', 'Eb']:
            session = JazzSession(key=key, tempo=120)
            events = session.tick()
            assert isinstance(events, list)

    def test_different_styles(self):
        """Session should work with different styles."""
        for style in ['bebop', 'cool', 'modal', 'free', 'hard_bop']:
            session = JazzSession(style=style)
            events = session.tick()
            assert isinstance(events, list)

    def test_energy_evolution(self):
        """Session energy should evolve over time."""
        random.seed(42)
        session = JazzSession(key='C', tempo=120)
        energies = []
        for _ in range(20):
            session.tick()
            energies.append(session.shared_context['energy'])
        # Energy should have changed
        assert len(set(f"{e:.4f}" for e in energies)) > 1


# ── NON-PRE-CALCULABILITY Tests ──────────────────────────────────────────────

class TestNonPreCalculability:
    """Verify that outputs cannot be predicted without running.

    The core property of the living constraint system: same initial
    conditions produce different outputs due to stochastic TFs and
    iterative signal exchange.
    """

    def test_same_cell_different_outputs(self):
        """Same cell run twice should produce different events."""
        random.seed(42)
        cell1 = MusicalCell('sax', sax_genome(), channel=2)
        cell1.tfs = _wire_sax_tfs()
        events1 = cell1.express({
            'beat': 0, 'bar': 0, 'tempo': 120,
            'key_center': 60, 'scale': [0, 2, 4, 5, 7, 9, 11], 'energy': 0.5,
        })

        random.seed(99)
        cell2 = MusicalCell('sax', sax_genome(), channel=2)
        cell2.tfs = _wire_sax_tfs()
        events2 = cell2.express({
            'beat': 0, 'bar': 0, 'tempo': 120,
            'key_center': 60, 'scale': [0, 2, 4, 5, 7, 9, 11], 'energy': 0.5,
        })

        # Different seeds → different outputs (at least sometimes)
        # We compare event notes as a simple measure
        notes1 = tuple(e.note for e in events1)
        notes2 = tuple(e.note for e in events2)
        # Allow for occasional equality, but over many runs should differ
        # Actually just check they're not always identical
        all_same = True
        for seed_a in [42, 100, 200]:
            for seed_b in [99, 101, 201]:
                if seed_a == seed_b:
                    continue
                random.seed(seed_a)
                c1 = MusicalCell('sax', sax_genome(), channel=2)
                c1.tfs = _wire_sax_tfs()
                e1 = c1.express({
                    'beat': 0, 'bar': 0, 'tempo': 120,
                    'key_center': 60, 'scale': [0, 2, 4, 5, 7, 9, 11], 'energy': 0.5,
                })

                random.seed(seed_b)
                c2 = MusicalCell('sax', sax_genome(), channel=2)
                c2.tfs = _wire_sax_tfs()
                e2 = c2.express({
                    'beat': 0, 'bar': 0, 'tempo': 120,
                    'key_center': 60, 'scale': [0, 2, 4, 5, 7, 9, 11], 'energy': 0.5,
                })

                n1 = tuple(ev.note for ev in e1)
                n2 = tuple(ev.note for ev in e2)
                if n1 != n2:
                    all_same = False
                    break
            if not all_same:
                break

        assert not all_same, "Same cell with different seeds always produced identical output"

    def test_session_non_deterministic(self):
        """Two sessions without seed should produce different outputs."""
        outputs = []
        for _ in range(2):
            session = JazzSession(key='C', tempo=120)
            all_events = []
            for _ in range(32):
                events = session.tick()
                all_events.extend(events)
            # Summarize as tuple of (note, velocity) pairs
            summary = tuple((e.note, e.velocity) for e in all_events[:50])
            outputs.append(summary)

        # Should differ (probabilistically near-certain with 50 events)
        assert outputs[0] != outputs[1], "Two non-seeded sessions produced identical output"

    def test_session_with_same_seed_reproducible(self):
        """Session with same seed should produce same output."""
        results = []
        for _ in range(2):
            session = JazzSession(key='C', tempo=120, seed=42)
            all_events = []
            for _ in range(32):
                events = session.tick()
                all_events.extend(events)
            summary = tuple((e.note, e.velocity) for e in all_events[:50])
            results.append(summary)

        assert results[0] == results[1], "Seeded session not reproducible"


# ── Genome Preset Tests ──────────────────────────────────────────────────────

class TestGenomePresets:
    """Test genome presets for each instrument."""

    def test_piano_genome(self):
        genome = piano_genome()
        assert len(genome) == GENOME_SIZE
        assert all(0 <= g <= 1 for g in genome)
        # Piano should have high comping
        assert genome[17] > 0.6  # COMPING

    def test_bass_genome(self):
        genome = bass_genome()
        assert len(genome) == GENOME_SIZE
        assert genome[1] > 0.7  # SNAP high
        assert genome[18] > 0.8  # WALKING high

    def test_drums_genome(self):
        genome = drums_genome()
        assert len(genome) == GENOME_SIZE
        assert genome[3] > 0.7  # LAMAN high
        assert genome[4] > 0.8  # TEMPO_CONSISTENCY high

    def test_sax_genome(self):
        genome = sax_genome()
        assert len(genome) == GENOME_SIZE
        assert genome[1] < 0.5  # SNAP low
        assert genome[20] > 0.6  # SYNCOPATION high


# ── TF Wiring Tests ──────────────────────────────────────────────────────────

class TestTFWiring:
    """Test transcription factor wiring for each instrument."""

    def test_piano_tfs(self):
        tfs = _wire_piano_tfs()
        assert len(tfs) > 0
        assert all(isinstance(tf, TranscriptionFactor) for tf in tfs)

    def test_bass_tfs(self):
        tfs = _wire_bass_tfs()
        assert len(tfs) > 0

    def test_drums_tfs(self):
        tfs = _wire_drums_tfs()
        assert len(tfs) > 0

    def test_sax_tfs(self):
        tfs = _wire_sax_tfs()
        assert len(tfs) > 0

    def test_tf_gene_indices_valid(self):
        """All TF gene indices should be valid."""
        for wire_fn in [_wire_piano_tfs, _wire_bass_tfs, _wire_drums_tfs, _wire_sax_tfs]:
            for tf in wire_fn():
                assert 0 <= tf.gene_index < GENOME_SIZE


# ── Convenience Function Tests ───────────────────────────────────────────────

class TestConvenience:
    """Test convenience functions."""

    def test_create_cell_auto(self):
        cell = create_cell('piano')
        assert cell.name == 'piano'
        assert len(cell.genome) == GENOME_SIZE

    def test_create_cell_explicit(self):
        cell = create_cell('custom', genome=[0.5] * GENOME_SIZE)
        assert cell.name == 'custom'

    def test_quick_session(self):
        random.seed(42)
        session, arrangement = quick_session(key='C', tempo=120, bars=8)
        assert isinstance(session, JazzSession)
        assert arrangement is not None
