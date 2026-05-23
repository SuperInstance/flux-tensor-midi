"""Tests for the DawDreamer bridge module.

Uses MockRenderer exclusively — no dawdreamer install required.
"""

import os
import tempfile
import wave

import pytest

from flux_tensor_midi.audio import (
    MockRenderer,
    create_renderer,
    find_soundfonts,
)
from flux_tensor_midi.audio.dawdreamer_bridge import (
    HAS_DAWDREAMER,
    _events_to_midi_bytes,
    _silence_wav,
)
from flux_tensor_midi.midi.events import MidiEvent


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def renderer():
    """Create a MockRenderer for testing."""
    return MockRenderer(sample_rate=44100, buffer_size=512)


@pytest.fixture
def tmp_output(tmp_path):
    """Provide a temporary output path."""
    return str(tmp_path / "output.wav")


@pytest.fixture
def sample_events():
    """Create a list of sample MidiEvent objects."""
    return [
        MidiEvent(note=60, velocity=100, start_ms=0, duration_ms=500, channel=0),
        MidiEvent(note=64, velocity=80, start_ms=500, duration_ms=500, channel=0),
        MidiEvent(note=67, velocity=90, start_ms=1000, duration_ms=1000, channel=0),
        MidiEvent(note=72, velocity=70, start_ms=0, duration_ms=2000, channel=1),
    ]


# ──────────────────────────────────────────────────────────────────────────────
# MockRenderer basic tests
# ──────────────────────────────────────────────────────────────────────────────

class TestMockRenderer:
    def test_init_defaults(self, renderer):
        assert renderer.sample_rate == 44100
        assert renderer.buffer_size == 512
        assert renderer.render_log == []
        assert renderer.loaded_patches == {}

    def test_init_custom_params(self):
        r = MockRenderer(sample_rate=48000, buffer_size=1024)
        assert r.sample_rate == 48000
        assert r.buffer_size == 1024

    def test_load_patch(self, renderer):
        renderer.load_patch(0, "/path/to/piano.sf2")
        assert renderer.loaded_patches[0] == "/path/to/piano.sf2"

        renderer.load_patch(1, "/path/to/synth.vst3")
        assert renderer.loaded_patches[1] == "/path/to/synth.vst3"

    def test_load_patch_multiple_channels(self, renderer):
        renderer.load_patch(0, "piano.sf2")
        renderer.load_patch(1, "bass.sf2")
        renderer.load_patch(9, "drums.sf2")
        assert len(renderer.loaded_patches) == 3

    def test_render_midi_string_path(self, renderer, tmp_output):
        result = renderer.render_midi("/tmp/test.mid", 2.0, tmp_output)
        assert result == tmp_output
        assert os.path.isfile(tmp_output)

        # Verify it's a valid WAV
        with wave.open(tmp_output, "rb") as wf:
            assert wf.getnchannels() == 2
            assert wf.getframerate() == 44100
            assert wf.getsampwidth() == 2

    def test_render_midi_bytes(self, renderer, tmp_output):
        midi_bytes = b"MThd\x00\x00\x00\x06\x00\x01\x00\x01\x00\x78"
        result = renderer.render_midi(midi_bytes, 3.0, tmp_output)
        assert result == tmp_output
        assert os.path.isfile(tmp_output)

    def test_render_midi_duration_matches(self, renderer, tmp_output):
        duration = 5.0
        renderer.render_midi("test.mid", duration, tmp_output)

        with wave.open(tmp_output, "rb") as wf:
            actual_duration = wf.getnframes() / wf.getframerate()
            assert abs(actual_duration - duration) < 0.01

    def test_render_midi_creates_dirs(self, renderer, tmp_path):
        nested = str(tmp_path / "deep" / "nested" / "output.wav")
        renderer.render_midi("test.mid", 1.0, nested)
        assert os.path.isfile(nested)

    def test_render_midi_log(self, renderer, tmp_output):
        renderer.render_midi("test.mid", 2.0, tmp_output)
        assert len(renderer.render_log) == 1
        entry = renderer.render_log[0]
        assert entry["type"] == "midi"
        assert entry["source"] == "test.mid"
        assert entry["duration"] == 2.0
        assert entry["output"] == tmp_output

    def test_render_arrangement_with_events(self, renderer, sample_events, tmp_output):
        result = renderer.render_arrangement(sample_events, tmp_output)
        assert result == tmp_output
        assert os.path.isfile(tmp_output)

        log_entry = renderer.render_log[0]
        assert log_entry["type"] == "arrangement"
        assert log_entry["num_events"] == 4

    def test_render_arrangement_with_score(self, renderer, tmp_output):
        """Test rendering with a Score-like object."""
        from flux_tensor_midi.core.flux import FluxVector

        class FakeScore:
            def all_events(self):
                return [
                    ("piano", 0.0, FluxVector([0.9, 0.0, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])),
                    ("piano", 1.0, FluxVector([0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])),
                    ("bass", 0.5, FluxVector([0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])),
                ]

        score = FakeScore()
        result = renderer.render_arrangement(score, tmp_output)
        assert result == tmp_output
        assert os.path.isfile(tmp_output)

    def test_render_arrangement_invalid_type(self, renderer, tmp_output):
        with pytest.raises(TypeError, match="arrangement must be"):
            renderer.render_arrangement("not_valid", tmp_output)

    def test_render_arrangement_empty_events(self, renderer, tmp_output):
        result = renderer.render_arrangement([], tmp_output)
        assert result == tmp_output
        assert os.path.isfile(tmp_output)

        # Duration should be the minimum (1.0s)
        with wave.open(tmp_output, "rb") as wf:
            actual_duration = wf.getnframes() / wf.getframerate()
            assert actual_duration >= 1.0


# ──────────────────────────────────────────────────────────────────────────────
# Utility function tests
# ──────────────────────────────────────────────────────────────────────────────

class TestUtilities:
    def test_silence_wav_valid(self):
        wav_data = _silence_wav(1.0, 44100, 2)
        assert len(wav_data) > 44  # At least a WAV header

        import io
        buf = io.BytesIO(wav_data)
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 2
            assert wf.getframerate() == 44100
            assert wf.getsampwidth() == 2
            frames = wf.getnframes()
            assert frames == 44100

    def test_silence_wav_mono(self):
        wav_data = _silence_wav(0.5, 22050, 1)
        import io
        buf = io.BytesIO(wav_data)
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getnframes() == 11025

    def test_events_to_midi_bytes_basic(self, sample_events):
        midi_bytes = _events_to_midi_bytes(sample_events, bpm=120.0)
        # Should be a valid MIDI file header
        assert midi_bytes[:4] == b"MThd"

    def test_events_to_midi_bytes_empty(self):
        midi_bytes = _events_to_midi_bytes([], bpm=120.0)
        assert midi_bytes[:4] == b"MThd"

    def test_events_to_midi_bytes_multi_channel(self, sample_events):
        """Events on channels 0 and 1 should produce 2 data tracks + 1 conductor."""
        midi_bytes = _events_to_midi_bytes(sample_events, bpm=120.0)
        assert len(midi_bytes) > 14  # More than just a header


# ──────────────────────────────────────────────────────────────────────────────
# Factory tests
# ──────────────────────────────────────────────────────────────────────────────

class TestFactory:
    def test_create_renderer_mock(self):
        r = create_renderer(mock=True)
        assert isinstance(r, MockRenderer)

    def test_create_renderer_auto_fallback(self):
        """Without dawdreamer, should get MockRenderer."""
        r = create_renderer(mock=False)
        if HAS_DAWDREAMER:
            from flux_tensor_midi.audio.dawdreamer_bridge import DawDreamerRenderer
            assert isinstance(r, DawDreamerRenderer)
        else:
            assert isinstance(r, MockRenderer)

    def test_create_renderer_custom_params(self):
        r = create_renderer(sample_rate=48000, buffer_size=1024, mock=True)
        assert r.sample_rate == 48000
        assert r.buffer_size == 1024


# ──────────────────────────────────────────────────────────────────────────────
# SoundFont detection tests
# ──────────────────────────────────────────────────────────────────────────────

class TestSoundFontDetection:
    def test_find_soundfonts_returns_list(self):
        result = find_soundfonts()
        assert isinstance(result, list)

    def test_find_soundfonts_no_crash(self):
        """Should not raise even if no soundfonts exist."""
        find_soundfonts()


# ──────────────────────────────────────────────────────────────────────────────
# Integration-style: full pipeline with MockRenderer
# ──────────────────────────────────────────────────────────────────────────────

class TestPipeline:
    def test_full_pipeline_events_to_wav(self, tmp_path):
        """End-to-end: create events → render → get WAV."""
        renderer = MockRenderer()
        output = str(tmp_path / "full_render.wav")

        events = [
            MidiEvent(note=60, velocity=100, start_ms=0, duration_ms=1000, channel=0),
            MidiEvent(note=64, velocity=90, start_ms=250, duration_ms=750, channel=0),
            MidiEvent(note=67, velocity=80, start_ms=500, duration_ms=500, channel=0),
        ]

        result = renderer.render_arrangement(events, output)

        assert result == output
        assert os.path.isfile(output)
        assert os.path.getsize(output) > 44

        with wave.open(output, "rb") as wf:
            assert wf.getnchannels() == 2
            assert wf.getframerate() == 44100

    def test_full_pipeline_with_patches(self, tmp_path):
        """Load patches then render."""
        renderer = MockRenderer()
        renderer.load_patch(0, "piano.sf2")
        renderer.load_patch(1, "strings.sf2")

        output = str(tmp_path / "patched.wav")
        events = [
            MidiEvent(note=60, velocity=100, start_ms=0, duration_ms=500, channel=0),
            MidiEvent(note=72, velocity=80, start_ms=0, duration_ms=500, channel=1),
        ]

        renderer.render_arrangement(events, output)
        assert os.path.isfile(output)

    def test_multiple_renders(self, tmp_path):
        """Render multiple times — each should be independent."""
        renderer = MockRenderer()

        for i in range(3):
            output = str(tmp_path / f"render_{i}.wav")
            events = [MidiEvent(note=60 + i * 4, velocity=80, start_ms=0, duration_ms=500)]
            renderer.render_arrangement(events, output)
            assert os.path.isfile(output)

        assert len(renderer.render_log) == 3

    def test_midi_file_render(self, tmp_path):
        """Render from a MIDI file path."""
        renderer = MockRenderer()

        # First create a MIDI file
        events = [
            MidiEvent(note=60, velocity=100, start_ms=0, duration_ms=1000),
            MidiEvent(note=64, velocity=80, start_ms=500, duration_ms=500),
        ]
        midi_bytes = _events_to_midi_bytes(events)

        midi_path = str(tmp_path / "test.mid")
        with open(midi_path, "wb") as f:
            f.write(midi_bytes)

        output = str(tmp_path / "from_midi.wav")
        renderer.render_midi(midi_path, 2.0, output)
        assert os.path.isfile(output)
        assert os.path.getsize(output) > 44
