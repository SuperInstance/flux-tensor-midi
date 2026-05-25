"""Spreader-Tool content-addressed storage — file-backed MVP."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Union

from spreader.types import (
    FCWStatus,
    FrozenContextWindow,
    KPIMetrics,
    RoomType,
    Seed,
    SeedState,
    TriggerType,
)

Item = Union[FrozenContextWindow, Seed]


class SpreaderStore:
    """Content-addressed file store for FCWs and Seeds.

    Layout::

        base_dir/
          fcws/{hash}.json
          seeds/{hash}.json
          index.json   # {"room_id → hash"} mappings
    """

    def __init__(self, base_dir: str = ".spreader_store") -> None:
        self._base = base_dir
        self._fcw_dir = os.path.join(base_dir, "fcws")
        self._seed_dir = os.path.join(base_dir, "seeds")
        self._index_path = os.path.join(base_dir, "index.json")

    # ── helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def content_hash(data: bytes) -> str:
        """SHA-256 hex digest."""
        return hashlib.sha256(data).hexdigest()

    def _ensure_dirs(self) -> None:
        """Create storage directories if they don't exist."""
        os.makedirs(self._fcw_dir, exist_ok=True)
        os.makedirs(self._seed_dir, exist_ok=True)

    def _load_index(self) -> Dict[str, Any]:
        """Load the room→hash index from disk."""
        if os.path.exists(self._index_path):
            with open(self._index_path, "r") as f:
                return json.load(f)
        return {"fcws": {}, "seeds": {}}

    def _save_index(self, idx: Dict[str, Any]) -> None:
        """Persist the room→hash index to disk."""
        self._ensure_dirs()
        with open(self._index_path, "w") as f:
            json.dump(idx, f, indent=2)

    @staticmethod
    def _serialize(item: Item) -> str:
        """Dataclass → JSON string (handles enums & optionals)."""
        d = asdict(item)
        return json.dumps(d, default=str, sort_keys=True)

    @staticmethod
    def _deserialize_fcw(raw: str) -> FrozenContextWindow:
        """Deserialize a JSON string into a FrozenContextWindow."""
        d = json.loads(raw)
        d["room_type"] = RoomType(d["room_type"])
        d["status"] = FCWStatus(d["status"])
        d["kpi_snapshot"] = KPIMetrics(**d["kpi_snapshot"])
        d["trigger"] = TriggerType(d["trigger"])
        # Remove fields not in __init__ if added by asdict of frozen dataclass
        _clean = {k: v for k, v in d.items() if k in FrozenContextWindow.__dataclass_fields__}
        return FrozenContextWindow(**_clean)

    @staticmethod
    def _deserialize_seed(raw: str) -> Seed:
        """Deserialize a JSON string into a Seed."""
        d = json.loads(raw)
        d["state"] = SeedState(d["state"])
        if d.get("locked_kpis") and isinstance(d["locked_kpis"], dict):
            d["locked_kpis"] = KPIMetrics(**d["locked_kpis"])
        _clean = {k: v for k, v in d.items() if k in Seed.__dataclass_fields__}
        return Seed(**_clean)

    # ── public API ───────────────────────────────────────────────────────

    def put(self, item: Item) -> str:
        """Store an FCW or Seed. Returns its content hash."""
        self._ensure_dirs()
        serialized = self._serialize(item)
        h = self.content_hash(serialized.encode())

        if isinstance(item, FrozenContextWindow):
            path = os.path.join(self._fcw_dir, f"{h}.json")
            kind = "fcws"
        else:
            path = os.path.join(self._seed_dir, f"{h}.json")
            kind = "seeds"

        with open(path, "w") as f:
            f.write(serialized)

        # Update index: room_id → list of hashes
        idx = self._load_index()
        room_id = item.room_id
        bucket = idx.setdefault(kind, {})
        entries = bucket.setdefault(room_id, [])
        if h not in entries:
            entries.append(h)
        self._save_index(idx)
        return h

    def get(self, content_hash: str) -> Optional[Item]:
        """Retrieve an FCW or Seed by content hash, or None."""
        # Try FCW first, then Seed
        for directory, deserializer in [
            (self._fcw_dir, self._deserialize_fcw),
            (self._seed_dir, self._deserialize_seed),
        ]:
            path = os.path.join(directory, f"{content_hash}.json")
            if os.path.exists(path):
                with open(path, "r") as f:
                    return deserializer(f.read())
        return None

    def delete(self, content_hash: str) -> bool:
        """Delete an item. Returns True if anything was removed."""
        removed = False
        for directory in (self._fcw_dir, self._seed_dir):
            path = os.path.join(directory, f"{content_hash}.json")
            if os.path.exists(path):
                os.remove(path)
                removed = True

        # Clean index
        idx = self._load_index()
        for kind in ("fcws", "seeds"):
            bucket = idx.get(kind, {})
            for room_id, hashes in list(bucket.items()):
                if content_hash in hashes:
                    hashes.remove(content_hash)
                    if not hashes:
                        del bucket[room_id]
        if removed:
            self._save_index(idx)
        return removed

    def _list_items(
        self,
        kind: str,
        room_id: Optional[str],
        status_filter: Optional[object],
        status_attr: str,
        deserialize_fn,
        expected_type: type,
    ) -> list:
        """Shared listing logic for FCWs and Seeds."""
        idx = self._load_index()
        results: list = []
        bucket = idx.get(kind, {})
        hash_lists = (
            [bucket[room_id]]
            if room_id and room_id in bucket
            else (list(bucket.values()) if not room_id else [])
        )
        for hashes in hash_lists:
            for h in hashes:
                item = self.get(h)
                if item is None:
                    continue
                assert isinstance(item, expected_type)
                if status_filter and getattr(item, status_attr) != status_filter:
                    continue
                results.append(item)
        return results

    def list_fcws(
        self,
        room_id: Optional[str] = None,
        status: Optional[FCWStatus] = None,
    ) -> List[FrozenContextWindow]:
        """List stored FCWs, optionally filtered by room_id and/or status."""
        return self._list_items(
            kind="fcws",
            room_id=room_id,
            status_filter=status,
            status_attr="status",
            deserialize_fn=None,
            expected_type=FrozenContextWindow,
        )

    def list_seeds(
        self,
        room_id: Optional[str] = None,
        state: Optional[SeedState] = None,
    ) -> List[Seed]:
        """List stored Seeds, optionally filtered by room_id and/or state."""
        return self._list_items(
            kind="seeds",
            room_id=room_id,
            status_filter=state,
            status_attr="state",
            deserialize_fn=None,
            expected_type=Seed,
        )

    def destroy(self) -> None:
        """Remove the entire store directory (for test cleanup)."""
        if os.path.exists(self._base):
            shutil.rmtree(self._base)
