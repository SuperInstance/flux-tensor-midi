"""
Beta testing and feedback harness for the constraint music ecosystem.

Modules:
    session_recorder  — Records user interaction sessions
    feedback_collector — Lightweight rating/text feedback
    experiment_runner  — A/B testing with statistical analysis
    discovery_engine   — Automatic pattern discovery from session data
    cli                — CLI entry point for beta commands
"""

from __future__ import annotations

__all__ = [
    "SessionRecorder",
    "FeedbackCollector",
    "ExperimentRunner",
    "DiscoveryEngine",
]
