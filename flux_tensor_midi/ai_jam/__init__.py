"""
AI-AI Jam: Two AI musicians jamming through constraint theory.

Agents with distinct personalities take turns improvising over shared
harmony, mediated by a consensus constraint layer.
"""

from flux_tensor_midi.ai_jam.agent import AIAgent, AgentPersonality
from flux_tensor_midi.ai_jam.session import JamSession
from flux_tensor_midi.ai_jam.presets import get_preset, list_presets

__all__ = [
    "AIAgent",
    "AgentPersonality",
    "JamSession",
    "get_preset",
    "list_presets",
]
