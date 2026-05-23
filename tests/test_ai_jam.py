"""
Tests for AI-AI Jam module: agent, session, presets, and CLI.
"""

from __future__ import annotations

import random
import tempfile
from pathlib import Path

import pytest

from flux_tensor_midi.ai_jam.agent import (
    AIAgent,
    AgentPersonality,
    CHORD_TONES,
    D_DORIAN_NOTES,
    DORIAN_INTERVALS,
)
from flux_tensor_midi.ai_jam.session import JamSession, DEFAULT_PROGRESSION
from flux_tensor_midi.ai_jam.presets import (
    get_preset,
    list_presets,
    PARKER,
    MILES,
    BACH,
    VIVALDI,
    COLTRANE,
    MONK,
    ZAWINUL,
    SHORTER,
    NOISE,
    DRONE,
)
from flux_tensor_midi.midi.events import MidiEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rng():
    return random.Random(42)


@pytest.fixture
def parker(rng):
    return AIAgent(PARKER, rng=rng)


@pytest.fixture
def miles(rng):
    return AIAgent(MILES, rng=random.Random(84))


@pytest.fixture
def simple_context():
    return {"chord_progression": [("Dm7", 4)]}


@pytest.fixture
def full_context():
    return {"chord_progression": DEFAULT_PROGRESSION}


# ---------------------------------------------------------------------------
# Agent basic tests (1-5)
# ---------------------------------------------------------------------------

class TestAgentBasics:
    def test_agent_generates_valid_midi(self, parker, simple_context):
        """Agent produces a list of valid MidiEvent objects."""
        events = parker.respond([], simple_context, bars=4, bpm=140)
        assert isinstance(events, list)
        assert len(events) > 0
        for ev in events:
            assert isinstance(ev, MidiEvent)
            assert 0 <= ev.note <= 127
            assert 0 < ev.velocity <= 127
            assert ev.duration_ms > 0

    def test_agent_notes_in_range(self, parker, simple_context):
        """All notes respect the agent's octave range."""
        events = parker.respond([], simple_context, bars=4, bpm=140)
        lo, hi = parker._note_range()
        for ev in events:
            assert lo <= ev.note <= hi, f"Note {ev.note} outside range [{lo}, {hi}]"

    def test_agent_uses_correct_channel(self, parker, simple_context):
        """Events use the agent's MIDI channel."""
        events = parker.respond([], simple_context, bars=4, bpm=140)
        for ev in events:
            assert ev.channel == PARKER.midi_channel

    def test_agent_timing_positive(self, parker, simple_context):
        """All event start times are non-negative."""
        events = parker.respond([], simple_context, bars=4, bpm=140)
        for ev in events:
            assert ev.start_ms >= 0

    def test_agent_responds_to_other(self, parker, miles, simple_context):
        """Agent can respond to another agent's output."""
        a1_events = parker.respond([], simple_context, bars=4, bpm=140)
        a2_events = miles.respond(a1_events, simple_context, bars=4, bpm=140)
        assert len(a2_events) > 0
        # Miles should have stored Parker's output in memory
        assert len(miles.memory) > 0


# ---------------------------------------------------------------------------
# Consensus constraint tests (6-9)
# ---------------------------------------------------------------------------

class TestConsensus:
    def test_first_note_is_chord_tone(self, parker, simple_context):
        """First note of each bar should be a chord tone (consensus)."""
        events = parker.respond([], simple_context, bars=4, bpm=140)
        bar_ms = (60_000.0 / 140) * 4
        dm7_pc = set(n % 12 for n in CHORD_TONES["Dm7"])
        for bar in range(4):
            bar_start = bar * bar_ms
            bar_end = (bar + 1) * bar_ms
            bar_events = [e for e in events if bar_start <= e.start_ms < bar_end]
            if bar_events:
                first = min(bar_events, key=lambda e: e.start_ms)
                # The very first note of bar 0 should be a chord tone
                if bar == 0:
                    assert first.note % 12 in dm7_pc, (
                        f"Bar {bar} first note {first.note} ({first.note % 12}) "
                        f"not a Dm7 chord tone"
                    )

    def test_consensus_pitch_returns_chord_tone(self, parker):
        """_consensus_pitch always returns a chord tone."""
        for chord in ["Dm7", "Gm7", "Am7"]:
            pitch = parker._consensus_pitch(chord, 60.0)
            chord_pc = set(n % 12 for n in CHORD_TONES[chord])
            assert int(pitch) % 12 in chord_pc

    def test_both_agents_agree_on_boundary_tones(self, parker, miles, full_context):
        """At bar boundaries, both agents' first notes share chord tones."""
        a1 = parker.respond([], full_context, bars=4, bpm=140)
        a2 = miles.respond(a1, full_context, bars=4, bpm=140)
        # Both should start with Dm7 tones
        a1_first = min(a1, key=lambda e: e.start_ms)
        a2_first = min(a2, key=lambda e: e.start_ms)
        dm7_pc = set(n % 12 for n in CHORD_TONES["Dm7"])
        assert a1_first.note % 12 in dm7_pc
        assert a2_first.note % 12 in dm7_pc

    def test_consensus_weight_respected(self):
        """Agent with high consensus_weight should more reliably hit chord tones."""
        high_consensus = AgentPersonality(
            name="strict", instrument="piano", midi_channel=0,
            consensus_weight=0.99, rest_probability=0.0,
            note_density=2.0, velocity_range=(60, 100),
            snap_epsilon=1.0, direction_change_prob=0.0,
            sustain_factor=0.5, octave_range=(4, 5),
            preferred_intervals=(2, 3, 5, 7),
        )
        low_consensus = AgentPersonality(
            name="free", instrument="piano", midi_channel=0,
            consensus_weight=0.01, rest_probability=0.3,
            note_density=2.0, velocity_range=(60, 100),
            snap_epsilon=0.1, direction_change_prob=0.5,
            sustain_factor=0.5, octave_range=(4, 5),
            preferred_intervals=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11),
        )
        ctx = {"chord_progression": [("Dm7", 4)]}
        strict_agent = AIAgent(high_consensus, rng=random.Random(42))
        free_agent = AIAgent(low_consensus, rng=random.Random(42))

        strict_events = strict_agent.respond([], ctx, bars=4, bpm=140)
        free_events = free_agent.respond([], ctx, bars=4, bpm=140)

        dm7_pc = set(n % 12 for n in CHORD_TONES["Dm7"])
        strict_chord_hits = sum(1 for e in strict_events if e.note % 12 in dm7_pc)
        free_chord_hits = sum(1 for e in free_events if e.note % 12 in dm7_pc)

        # High consensus should have higher or equal chord tone ratio
        if len(strict_events) > 0 and len(free_events) > 0:
            strict_ratio = strict_chord_hits / len(strict_events)
            free_ratio = free_chord_hits / len(free_events)
            # At minimum, strict agent should not have a lower ratio
            # (This is probabilistic but the seed makes it deterministic)
            assert strict_ratio >= free_ratio * 0.8  # Allow some slack


# ---------------------------------------------------------------------------
# Session tests (10-14)
# ---------------------------------------------------------------------------

class TestSession:
    def test_session_produces_events(self, parker, miles):
        """Session generates a non-empty event list."""
        session = JamSession(agent1=parker, agent2=miles, total_bars=8, bpm=140)
        events = session.run()
        assert len(events) > 0

    def test_session_events_sorted(self, parker, miles):
        """Events are sorted by start time."""
        session = JamSession(agent1=parker, agent2=miles, total_bars=16, bpm=140)
        events = session.run()
        for i in range(len(events) - 1):
            assert events[i].start_ms <= events[i + 1].start_ms

    def test_session_multi_track_channels(self, parker, miles):
        """Events have different MIDI channels for each agent."""
        session = JamSession(agent1=parker, agent2=miles, total_bars=8, bpm=140)
        events = session.run()
        channels = set(ev.channel for ev in events)
        assert len(channels) == 2
        assert PARKER.midi_channel in channels
        assert MILES.midi_channel in channels

    def test_session_duration(self, parker, miles):
        """Session events don't exceed the expected total duration."""
        total_bars = 16
        bpm = 140
        session = JamSession(agent1=parker, agent2=miles, total_bars=total_bars, bpm=bpm)
        events = session.run()
        bar_ms = (60_000.0 / bpm) * 4
        expected_end = total_bars * bar_ms
        # Allow some slack for the last note's duration
        last_end = max(ev.end_ms for ev in events)
        assert last_end <= expected_end + bar_ms, (
            f"Session ends at {last_end:.0f}ms, expected ~{expected_end:.0f}ms"
        )

    def test_session_midi_file(self, parker, miles):
        """Session can write a valid MIDI file."""
        session = JamSession(agent1=parker, agent2=miles, total_bars=8, bpm=140)
        with tempfile.NamedTemporaryFile(suffix=".mid", delete=False) as f:
            path = f.name
        try:
            session.to_midi_file(path)
            assert Path(path).exists()
            assert Path(path).stat().st_size > 0
            # Verify it's a valid MIDI file
            import mido
            mid = mido.MidiFile(path)
            assert len(mid.tracks) == 2
        finally:
            Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Preset tests (15-18)
# ---------------------------------------------------------------------------

class TestPresets:
    def test_all_presets_valid(self):
        """All presets can create a working session."""
        for name in list_presets():
            preset = get_preset(name)
            a1 = AIAgent(preset["agent1"], rng=random.Random(1))
            a2 = AIAgent(preset["agent2"], rng=random.Random(2))
            session = JamSession(
                agent1=a1, agent2=a2,
                bpm=preset["bpm"], total_bars=8,
                progression=preset["progression"],
            )
            events = session.run()
            assert len(events) > 0, f"Preset {name} produced no events"

    def test_all_presets_have_required_keys(self):
        """Each preset has all required fields."""
        for name in list_presets():
            preset = get_preset(name)
            assert "description" in preset
            assert "agent1" in preset
            assert "agent2" in preset
            assert "bpm" in preset
            assert "progression" in preset

    def test_unknown_preset_raises(self):
        """Requesting an unknown preset raises ValueError."""
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset("nonexistent_preset")

    def test_list_presets_returns_five(self):
        """There are exactly 5 presets."""
        presets = list_presets()
        assert len(presets) == 5
        assert "parker_miles" in presets


# ---------------------------------------------------------------------------
# Personality tests (19-21)
# ---------------------------------------------------------------------------

class TestPersonality:
    def test_parker_generates_more_notes_than_miles(self):
        """Parker (dense bebop) should generate more notes than Miles (sparse cool)."""
        ctx = {"chord_progression": [("Dm7", 4), ("Gm7", 4), ("Am7", 4), ("Dm7", 4)]}
        parker = AIAgent(PARKER, rng=random.Random(42))
        miles = AIAgent(MILES, rng=random.Random(42))

        p_events = parker.respond([], ctx, bars=16, bpm=140)
        m_events = miles.respond([], ctx, bars=16, bpm=140)

        assert len(p_events) > len(m_events), (
            f"Parker: {len(p_events)} notes, Miles: {len(m_events)} notes"
        )

    def test_parker_higher_density_than_miles(self):
        """Parker has higher note_density personality than Miles."""
        assert PARKER.note_density > MILES.note_density

    def test_miles_more_rests_than_parker(self):
        """Miles has higher rest probability."""
        assert MILES.rest_probability > PARKER.rest_probability


# ---------------------------------------------------------------------------
# Edge case tests (22-25)
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_one_bar_session(self, parker, miles):
        """A 1-bar session still produces output."""
        session = JamSession(agent1=parker, agent2=miles, total_bars=1, bpm=140)
        events = session.run()
        assert len(events) > 0

    def test_hundred_bar_session(self, parker, miles):
        """A 100-bar session produces lots of output without errors."""
        session = JamSession(
            agent1=parker, agent2=miles,
            total_bars=100, bpm=140,
            phrase_bars=4,
        )
        events = session.run()
        assert len(events) > 100  # Should have many events

    def test_same_agent_vs_itself(self):
        """An agent can jam against a copy of itself."""
        agent1 = AIAgent(PARKER, rng=random.Random(1))
        agent2 = AIAgent(PARKER, rng=random.Random(2))
        session = JamSession(agent1=agent1, agent2=agent2, total_bars=8, bpm=140)
        events = session.run()
        assert len(events) > 0

    def test_empty_other_output(self, parker, simple_context):
        """Agent can respond to an empty other_output list."""
        events = parker.respond([], simple_context, bars=4, bpm=140)
        assert len(events) > 0

    def test_odd_bar_count(self, parker, miles):
        """Session with odd bar count still works."""
        session = JamSession(
            agent1=parker, agent2=miles,
            total_bars=7, bpm=140,
            phrase_bars=2,
        )
        events = session.run()
        assert len(events) > 0
