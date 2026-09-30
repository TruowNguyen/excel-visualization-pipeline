from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from threading import RLock
from typing import Any


class AnalysisSnapshotRepository:
    """Bounded in-memory storage; never persists provider prompts or raw responses."""

    def __init__(self, limit: int = 100):
        self.limit = limit
        self._items: OrderedDict[str, tuple[int, dict[str, Any]]] = OrderedDict()
        self._lock = RLock()

    def put(self, analysis_id: str, source_run_id: int, payload: dict[str, Any]) -> None:
        with self._lock:
            self._items[analysis_id] = (source_run_id, deepcopy(payload))
            self._items.move_to_end(analysis_id)
            while len(self._items) > self.limit:
                self._items.popitem(last=False)

    def get(self, analysis_id: str) -> tuple[int, dict[str, Any]] | None:
        with self._lock:
            item = self._items.get(analysis_id)
            if item is None:
                return None
            self._items.move_to_end(analysis_id)
            return item[0], deepcopy(item[1])
