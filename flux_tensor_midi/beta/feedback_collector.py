"""
Feedback collector for beta testing.

Lightweight after-composition feedback: star ratings, free text,
NPS-style "would you use this again?".
Supports headless mode that just logs interaction metrics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class FeedbackCollector:
    """Collects user feedback on compositions.

    Usage::

        fc = FeedbackCollector()
        fc.ask_rating("abc123", 4)
        fc.ask_text("abc123", "Loved the harmonic constraint")
        fc.ask_nps("abc123", 8)
        fc.export_feedback()
    """

    def __init__(
        self,
        output_dir: str | Path = "beta_data/feedback",
        headless: bool = False,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self._records: list[dict[str, Any]] = []

    # ── public API ──────────────────────────────────────────────────────

    def ask_rating(self, composition_id: str, stars: int) -> dict[str, Any]:
        """Record a 1-5 star rating for a composition.

        Args:
            composition_id: Hash or ID of the composition.
            stars: Rating from 1 to 5.

        Returns:
            The feedback record dict.
        """
        if not 1 <= stars <= 5:
            raise ValueError(f"Rating must be 1-5, got {stars}")
        record = self._make_record(composition_id, "rating", {"stars": stars})
        self._records.append(record)
        return record

    def ask_text(self, composition_id: str, text: str) -> dict[str, Any]:
        """Record free-text feedback for a composition."""
        record = self._make_record(composition_id, "text", {"text": text})
        self._records.append(record)
        return record

    def ask_nps(self, composition_id: str, score: int) -> dict[str, Any]:
        """Record an NPS-style score (0-10): "How likely to use again?"

        0-6 = detractor, 7-8 = passive, 9-10 = promoter.
        """
        if not 0 <= score <= 10:
            raise ValueError(f"NPS score must be 0-10, got {score}")
        category = "detractor" if score <= 6 else ("passive" if score <= 8 else "promoter")
        record = self._make_record(
            composition_id, "nps",
            {"score": score, "category": category},
        )
        self._records.append(record)
        return record

    def export_feedback(self) -> list[dict[str, Any]]:
        """Persist all collected feedback to disk and return it."""
        path = self.output_dir / f"feedback_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        path.write_text(json.dumps(self._records, indent=2))
        return list(self._records)

    @property
    def record_count(self) -> int:
        return len(self._records)

    # ── class-method utilities ──────────────────────────────────────────

    @classmethod
    def load_all_feedback(cls, directory: str | Path = "beta_data/feedback") -> list[dict[str, Any]]:
        """Load every feedback JSON from a directory."""
        d = Path(directory)
        if not d.exists():
            return []
        all_records: list[dict[str, Any]] = []
        for p in sorted(d.glob("*.json")):
            try:
                data = json.loads(p.read_text())
                if isinstance(data, list):
                    all_records.extend(data)
            except (json.JSONDecodeError, OSError):
                continue
        return all_records

    # ── helpers ─────────────────────────────────────────────────────────

    def _make_record(
        self, composition_id: str, kind: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "composition_id": composition_id,
            "kind": kind,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "headless": self.headless,
        }
