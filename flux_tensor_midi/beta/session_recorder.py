"""
Session recorder for beta testing.

Records constraint parameters, compositions, playback events,
time spent, and abandon points as structured JSON session logs.
No personal data — purely musical interaction data.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SessionRecorder:
    """Records everything a user does during a beta session.

    Usage::

        rec = SessionRecorder()
        rec.start_session()
        rec.log_action("param_change", {"epsilon": 0.25})
        rec.log_composition("abc123", {"epsilon": 0.25, "constraints": ["harmonic"]})
        rec.log_action("playback", {"midi_hash": "abc123"})
        rec.end_session()
    """

    def __init__(self, output_dir: str | Path = "beta_data/sessions") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._session: dict[str, Any] | None = None
        self._start_ts: float = 0.0

    # ── public API ──────────────────────────────────────────────────────

    def start_session(self, user_id: str | None = None) -> str:
        """Start a new recording session. Returns the session ID."""
        session_id = uuid.uuid4().hex[:12]
        self._start_ts = time.monotonic()
        self._session = {
            "session_id": session_id,
            "user_id": user_id or "anon",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "actions": [],
            "compositions": [],
            "total_duration_s": None,
            "ended_at": None,
            "abandon_point": None,
        }
        return session_id

    def log_action(
        self,
        event_type: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Log a user action.

        Common event_types: param_change, playback, pause, stop, undo, navigate.
        """
        self._require_active()
        self._session["actions"].append({
            "event_type": event_type,
            "params": params or {},
            "elapsed_s": round(time.monotonic() - self._start_ts, 3),
        })

    def log_composition(
        self,
        midi_hash: str,
        params: dict[str, Any],
    ) -> None:
        """Log a composition that was generated."""
        self._require_active()
        self._session["compositions"].append({
            "midi_hash": midi_hash,
            "params": params,
            "elapsed_s": round(time.monotonic() - self._start_ts, 3),
        })

    def end_session(self, abandon_point: str | None = None) -> dict[str, Any]:
        """End the session, persist to disk, and return the session dict.

        Args:
            abandon_point: If the user left mid-flow, describe where
                           (e.g. "before_playback", "during_param_select").
        """
        self._require_active()
        elapsed = round(time.monotonic() - self._start_ts, 3)
        self._session["total_duration_s"] = elapsed
        self._session["ended_at"] = datetime.now(timezone.utc).isoformat()
        self._session["abandon_point"] = abandon_point

        path = self.output_dir / f"{self._session['session_id']}.json"
        path.write_text(json.dumps(self._session, indent=2))

        session = self._session
        self._session = None
        return session

    @property
    def active(self) -> bool:
        return self._session is not None

    @property
    def session_id(self) -> str | None:
        return self._session["session_id"] if self._session else None

    # ── helpers ─────────────────────────────────────────────────────────

    def _require_active(self) -> None:
        if self._session is None:
            raise RuntimeError("No active session. Call start_session() first.")

    # ── class-method utilities ──────────────────────────────────────────

    @classmethod
    def load_session(cls, path: str | Path) -> dict[str, Any]:
        """Load a session log from disk."""
        return json.loads(Path(path).read_text())

    @classmethod
    def load_all_sessions(cls, directory: str | Path = "beta_data/sessions") -> list[dict[str, Any]]:
        """Load every session JSON from a directory."""
        d = Path(directory)
        if not d.exists():
            return []
        sessions = []
        for p in sorted(d.glob("*.json")):
            try:
                sessions.append(json.loads(p.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
        return sessions
