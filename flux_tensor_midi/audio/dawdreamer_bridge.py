"""
DawDreamer bridge — render flux-tensor-midi MIDI to audio via DawDreamer.

Bridges constraint-theory composition → actual audio output.

Requires DawDreamer + a VST plugin or SoundFont for audio rendering.
If dawdreamer is not installed, a MockRenderer is provided for testing.

Install:
    pip install flux-tensor-midi[audio]

DawDreamer setup:
    pip install dawdreamer
    # Optionally install fluidsynth for SoundFont support:
    #   macOS:  brew install fluidsynth
    #   Ubuntu: sudo apt install fluidsynth
    #   Windows: download from https://www.fluidsynth.org/
"""

from __future__ import annotations

import io
import os
import struct
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

try:
    import dawdreamer as dd
    HAS_DAWDREAMER = True
except ImportError:
    HAS_DAWDREAMER = False

try:
    import mido
    HAS_MIDO = True
except ImportError:
    HAS_MIDO = False

# Reuse the existing daw_bridge MIDI builder for file generation
from flux_tensor_midi.adapters.daw_bridge import (
    MidiExportConfig,
    TrackConfig,
    build_midi_file,
)
from flux_tensor_midi.midi.events import MidiEvent


# ──────────────────────────────────────────────────────────────────────────────
# MIDI utilities
# ──────────────────────────────────────────────────────────────────────────────

def _events_to_midi_bytes(
    events: Sequence[MidiEvent],
    bpm: float = 120.0,
    ppqn: int = 480,
) -> bytes:
    """Convert a list of MidiEvent objects to raw Standard MIDI File bytes."""
    channel_events: Dict[int, List[MidiEvent]] = {}
    for ev in events:
        channel_events.setdefault(ev.channel, []).append(ev)

    config = MidiExportConfig(tempo_bpm=bpm, ppqn=ppqn)

    for ch, ch_events in sorted(channel_events.items()):
        track = TrackConfig(
            name=f"Channel {ch + 1}",
            channel=ch,
        )
        for ev in ch_events:
            start_tick = int(ev.start_ms / 1000.0 * (bpm / 60.0) * ppqn)
            dur_ticks = int(ev.duration_ms / 1000.0 * (bpm / 60.0) * ppqn)
            track.notes.append((start_tick, max(1, dur_ticks), ev.note, ev.velocity))
        config.tracks.append(track)

    return build_midi_file(config)


def _silence_wav(duration_seconds: float, sample_rate: int = 44100,
                 num_channels: int = 2) -> bytes:
    """Generate a silent WAV file in memory."""
    buf = io.BytesIO()
    num_frames = int(duration_seconds * sample_rate)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames * num_channels)
    return buf.getvalue()


def _detect_sf2_paths() -> List[str]:
    """Search common locations for SoundFont (.sf2) files."""
    candidates = []
    search_dirs = [
        "/usr/share/sounds/sf2",
        "/usr/share/soundfonts",
        "/usr/local/share/sounds/sf2",
        "/usr/local/share/soundfonts",
        os.path.expanduser("~/SoundFonts"),
        os.path.expanduser("~/soundfonts"),
        os.path.expanduser("~/.local/share/soundfonts"),
    ]

    if os.name == "nt":
        search_dirs.append(os.path.join(
            os.environ.get("PROGRAMFILES", r"C:\Program Files"), "SoundFonts"
        ))
    elif hasattr(os, "uname") and os.uname().sysname == "Darwin":
        search_dirs.append("/Library/Audio/Sounds/Banks")

    for d in search_dirs:
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.lower().endswith(".sf2"):
                    candidates.append(os.path.join(d, f))

    return candidates


# ──────────────────────────────────────────────────────────────────────────────
# MockRenderer — testing without DawDreamer
# ──────────────────────────────────────────────────────────────────────────────

class MockRenderer:
    """Drop-in replacement for DawDreamerRenderer when dawdreamer is not installed.

    Generates silent WAV files and records render calls for test assertions.
    """

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 512):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self._patches: Dict[int, str] = {}
        self._render_log: List[Dict[str, Any]] = []

    def load_patch(self, midi_channel: int, patch_path: str) -> None:
        """Record a patch load (no-op for mock)."""
        self._patches[midi_channel] = patch_path

    def render_midi(
        self,
        midi_path_or_bytes: Union[str, bytes],
        duration: float,
        output_path: str,
    ) -> str:
        """Render a silent WAV of the specified duration."""
        midi_info = (
            os.path.basename(midi_path_or_bytes)
            if isinstance(midi_path_or_bytes, str)
            else f"<bytes, {len(midi_path_or_bytes)} bytes>"
        )
        self._render_log.append({
            "type": "midi",
            "source": midi_info,
            "duration": duration,
            "output": output_path,
        })

        wav_data = _silence_wav(duration, self.sample_rate)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(wav_data)

        return output_path

    def render_arrangement(
        self,
        arrangement: Any,
        output_path: str,
    ) -> str:
        """Render an arrangement to a silent WAV.

        Accepts a Score-like object with ``all_events()``, or a list of
        MidiEvent objects.
        """
        events: List[MidiEvent] = []
        duration_ms = 0.0

        if isinstance(arrangement, list):
            events = arrangement
            if events:
                duration_ms = max(ev.start_ms + ev.duration_ms for ev in events)
        elif hasattr(arrangement, "all_events"):
            all_evts = arrangement.all_events()
            for musician, timestamp, vector in all_evts:
                vec_tuple = (
                    vector.to_tuple()
                    if hasattr(vector, "to_tuple")
                    else tuple(vector)
                )
                midi_evts = MidiEvent.from_flux(
                    vec_tuple,
                    start_ms=timestamp * 1000.0,
                    duration_ms=250.0,
                )
                events.extend(midi_evts)
                end = timestamp * 1000.0 + 250.0
                if end > duration_ms:
                    duration_ms = end
        else:
            raise TypeError(
                f"arrangement must be a list of MidiEvent, a Score, or have "
                f"all_events(); got {type(arrangement).__name__}"
            )

        duration = max(1.0, duration_ms / 1000.0 + 0.5)

        midi_bytes = _events_to_midi_bytes(events)
        self._render_log.append({
            "type": "arrangement",
            "num_events": len(events),
            "duration": duration,
            "output": output_path,
        })

        wav_data = _silence_wav(duration, self.sample_rate)
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(wav_data)

        return output_path

    @property
    def render_log(self) -> List[Dict[str, Any]]:
        """Access the render call log for test assertions."""
        return self._render_log

    @property
    def loaded_patches(self) -> Dict[int, str]:
        """Access loaded patch mappings."""
        return dict(self._patches)


# ──────────────────────────────────────────────────────────────────────────────
# DawDreamerRenderer — real audio rendering
# ──────────────────────────────────────────────────────────────────────────────

class DawDreamerRenderer:
    """Renders MIDI to audio through DawDreamer with VST/SF2 instruments.

    Parameters
    ----------
    sample_rate : int
        Audio sample rate (default 44100).
    buffer_size : int
        Buffer size in frames (default 512).

    Raises
    ------
    ImportError
        If dawdreamer is not installed.
    """

    def __init__(self, sample_rate: int = 44100, buffer_size: int = 512):
        if not HAS_DAWDREAMER:
            raise ImportError(
                "dawdreamer is required for DawDreamerRenderer.\n"
                "\n"
                "Install it with:\n"
                "  pip install dawdreamer\n"
                "\n"
                "Or use the audio extra:\n"
                "  pip install flux-tensor-midi[audio]\n"
                "\n"
                "For testing without dawdreamer, use MockRenderer:\n"
                "  from flux_tensor_midi.audio import MockRenderer\n"
                "  renderer = MockRenderer()"
            )

        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self._engine: Optional[Any] = None
        self._graph: Optional[Any] = None
        self._plugins: Dict[int, Any] = {}
        self._patch_paths: Dict[int, str] = {}

    def _ensure_engine(self) -> None:
        """Lazily create the DawDreamer engine."""
        if self._engine is None:
            self._engine = dd.Engine(
                sample_rate=self.sample_rate,
                block_size=self.buffer_size,
            )
            self._graph = self._engine.make_graph()

    def load_patch(self, midi_channel: int, patch_path: str) -> None:
        """Load a VST plugin or SoundFont for a MIDI channel.

        Parameters
        ----------
        midi_channel : int
            MIDI channel (0–15).
        patch_path : str
            Path to a VST (.dll/.vst3/.so) or SoundFont (.sf2) file.
        """
        self._ensure_engine()

        if not os.path.isfile(patch_path):
            raise FileNotFoundError(f"Patch file not found: {patch_path}")

        ext = os.path.splitext(patch_path)[1].lower()

        if ext == ".sf2":
            self._load_soundfont(midi_channel, patch_path)
        elif ext in (".dll", ".so", ".vst3", ".component"):
            self._load_vst(midi_channel, patch_path)
        else:
            raise ValueError(
                f"Unsupported patch format: {ext}. "
                f"Expected .sf2, .dll, .so, .vst3, or .component"
            )

        self._patch_paths[midi_channel] = patch_path

    def _load_soundfont(self, midi_channel: int, sf2_path: str) -> None:
        """Load a SoundFont via the built-in sampler or fluidsynth."""
        self._ensure_engine()

        try:
            sampler = self._graph.add_plugin("sampler")
            sampler.load(sf2_path)
            self._plugins[midi_channel] = sampler
        except Exception:
            try:
                plugin = self._graph.add_plugin(dd.PatchProcessor, sf2_path)
                self._plugins[midi_channel] = plugin
            except Exception as e:
                raise RuntimeError(
                    f"Could not load SoundFont {sf2_path}. "
                    f"Ensure fluidsynth is installed or use a VST sampler.\n"
                    f"Error: {e}"
                ) from e

    def _load_vst(self, midi_channel: int, vst_path: str) -> None:
        """Load a VST plugin for a MIDI channel."""
        self._ensure_engine()
        plugin = self._graph.add_plugin(dd.PatchProcessor, vst_path)
        self._plugins[midi_channel] = plugin

    def render_midi(
        self,
        midi_path_or_bytes: Union[str, bytes],
        duration: float,
        output_path: str,
        bpm: float = 120.0,
    ) -> str:
        """Render a MIDI file to WAV audio.

        Parameters
        ----------
        midi_path_or_bytes : str | bytes
            Path to a .mid file, or raw MIDI bytes.
        duration : float
            Render duration in seconds.
        output_path : str
            Path to write the output WAV file.
        bpm : float
            Tempo for byte-to-tick conversion (default 120).

        Returns
        -------
        str
            Path to the written WAV file.
        """
        self._ensure_engine()

        # Write MIDI bytes to a temp file if needed
        if isinstance(midi_path_or_bytes, bytes):
            tmp = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
            tmp.write(midi_path_or_bytes)
            tmp.close()
            midi_path = tmp.name
            cleanup = True
        else:
            midi_path = midi_path_or_bytes
            cleanup = False

        try:
            midi_player = self._graph.add_midi_player(midi_path)

            # Auto-detect SoundFont if no patches loaded
            if not self._plugins:
                sf2_paths = _detect_sf2_paths()
                if sf2_paths:
                    self.load_patch(0, sf2_paths[0])

            self._engine.render(duration)
            audio = self._engine.get_audio()

            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            self._write_wav(audio, output_path)

        finally:
            if cleanup:
                os.unlink(midi_path)

        return output_path

    def render_arrangement(
        self,
        arrangement: Any,
        output_path: str,
        bpm: float = 120.0,
    ) -> str:
        """Render a flux-tensor-midi arrangement to WAV audio.

        Accepts:
        - A list of MidiEvent objects
        - A Score object (with ``all_events()``)
        - A MidiExportConfig object

        Parameters
        ----------
        arrangement
            The arrangement to render.
        output_path : str
            Path to write the output WAV.
        bpm : float
            Tempo (default 120).

        Returns
        -------
        str
            Path to the written WAV file.
        """
        if isinstance(arrangement, MidiExportConfig):
            midi_bytes = build_midi_file(arrangement)
            max_tick = 0
            for track in arrangement.tracks:
                for start_tick, dur_ticks, _, _ in track.notes:
                    end = start_tick + dur_ticks
                    if end > max_tick:
                        max_tick = end
            duration = max(
                1.0,
                (max_tick / arrangement.ppqn) * (60.0 / arrangement.tempo_bpm) + 0.5,
            )
            return self.render_midi(
                midi_bytes, duration, output_path, bpm=arrangement.tempo_bpm,
            )

        events: List[MidiEvent] = []
        duration_ms = 0.0

        if isinstance(arrangement, list):
            events = arrangement
            if events:
                duration_ms = max(ev.start_ms + ev.duration_ms for ev in events)
        elif hasattr(arrangement, "all_events"):
            all_evts = arrangement.all_events()
            for musician, timestamp, vector in all_evts:
                vec_tuple = (
                    vector.to_tuple()
                    if hasattr(vector, "to_tuple")
                    else tuple(vector)
                )
                midi_evts = MidiEvent.from_flux(
                    vec_tuple,
                    start_ms=timestamp * 1000.0,
                    duration_ms=250.0,
                )
                events.extend(midi_evts)
                end = timestamp * 1000.0 + 250.0
                if end > duration_ms:
                    duration_ms = end
        else:
            raise TypeError(
                f"arrangement must be a list of MidiEvent, a Score, "
                f"a MidiExportConfig, or have all_events(); "
                f"got {type(arrangement).__name__}"
            )

        duration = max(1.0, duration_ms / 1000.0 + 0.5)
        midi_bytes = _events_to_midi_bytes(events, bpm=bpm)
        return self.render_midi(midi_bytes, duration, output_path, bpm=bpm)

    @staticmethod
    def _write_wav(audio_data: Any, output_path: str) -> None:
        """Write audio data to a WAV file."""
        import numpy as np

        if isinstance(audio_data, np.ndarray):
            if audio_data.ndim == 1:
                audio_data = audio_data.reshape(1, -1)

            num_channels = audio_data.shape[0]

            # Convert to 16-bit PCM
            pcm = np.clip(audio_data * 32767, -32768, 32767).astype(np.int16)

            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(num_channels)
                wf.setsampwidth(2)
                wf.setframerate(44100)
                interleaved = pcm.T.flatten()
                wf.writeframes(interleaved.tobytes())
        else:
            with open(output_path, "wb") as f:
                f.write(audio_data)


# ──────────────────────────────────────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────────────────────────────────────

def create_renderer(
    sample_rate: int = 44100,
    buffer_size: int = 512,
    mock: bool = False,
) -> Union[DawDreamerRenderer, MockRenderer]:
    """Create a renderer instance.

    Parameters
    ----------
    sample_rate : int
        Audio sample rate.
    buffer_size : int
        Buffer size in frames.
    mock : bool
        If True, always return MockRenderer.
        If False, return DawDreamerRenderer if available, else MockRenderer.

    Returns
    -------
    DawDreamerRenderer | MockRenderer
    """
    if mock:
        return MockRenderer(sample_rate=sample_rate, buffer_size=buffer_size)

    if HAS_DAWDREAMER:
        return DawDreamerRenderer(sample_rate=sample_rate, buffer_size=buffer_size)

    return MockRenderer(sample_rate=sample_rate, buffer_size=buffer_size)


# ──────────────────────────────────────────────────────────────────────────────
# Convenience
# ──────────────────────────────────────────────────────────────────────────────

def find_soundfonts() -> List[str]:
    """Find SoundFont (.sf2) files in standard locations."""
    return _detect_sf2_paths()
