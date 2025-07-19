"""Analytics jobs for MemCube usage metrics."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from .in_memory_storage import InMemoryMemCubeStorage
from .storage import SupabaseMemCubeStorage


class AnalyticsEngine:
  """Periodically aggregate memory usage analytics."""

  def __init__(
      self,
      storage: InMemoryMemCubeStorage | SupabaseMemCubeStorage,
      interval_seconds: int = 3600,
  ) -> None:
    self.storage = storage
    self.interval_seconds = interval_seconds
    self._task: Optional[asyncio.Task] = None
    self.analytics: Dict[str, Dict[str, Any]] = {}

  async def start(self) -> None:
    if not self._task:
      self._task = asyncio.create_task(self._run())

  async def stop(self) -> None:
    if self._task:
      self._task.cancel()
      try:
        await self._task
      except asyncio.CancelledError:
        pass

  async def _run(self) -> None:
    while True:
      await self.compute_analytics()
      await asyncio.sleep(self.interval_seconds)

  async def compute_analytics(self) -> None:
    events = await self._fetch_events()
    self.analytics = self._aggregate(events)

  async def _fetch_events(self) -> List[Dict[str, Any]]:
    if isinstance(self.storage, InMemoryMemCubeStorage):
      return list(self.storage.events)
    result = self.storage.client.table("memory_events").select("*").execute()
    return result.data or []

  def _aggregate(
      self, events: List[Dict[str, Any]]
  ) -> Dict[str, Dict[str, Any]]:
    metrics: Dict[str, Dict[str, Any]] = {}
    for event in events:
      project_id = event.get("project_id")
      if not project_id:
        continue
      mem_id = event["memory_id"]
      event_type = event["event"]
      ts_raw = event.get("ts")
      ts = (
          datetime.fromisoformat(ts_raw)
          if isinstance(ts_raw, str)
          else ts_raw or datetime.utcnow()
      )
      day = ts.date().isoformat()
      meta = event.get("meta") or {}
      tags = meta.get("tags", []) if isinstance(meta, dict) else []

      proj = metrics.setdefault(
          project_id,
          {
              "total_retrievals": defaultdict(int),
              "tag_frequencies": defaultdict(int),
              "lifecycle": defaultdict(int),
              "temporal": defaultdict(int),
          },
      )
      if event_type in {"RETRIEVED", "ACCESSED"}:
        proj["total_retrievals"][mem_id] += 1
        proj["temporal"][day] += 1
        proj["lifecycle"]["ACTIVE"] += 1
      elif event_type == "CREATED":
        proj["lifecycle"]["NEW"] += 1
      elif event_type == "ARCHIVED":
        proj["lifecycle"]["ARCHIVED"] += 1

      for tag in tags:
        proj["tag_frequencies"][tag] += 1

    return metrics

  async def get_usage(
      self, project_id: str, period: str = "7d"
  ) -> Dict[str, Any]:
    if project_id not in self.analytics:
      await self.compute_analytics()

    data = self.analytics.get(
        project_id,
        {
            "total_retrievals": {},
            "tag_frequencies": {},
            "lifecycle": {},
            "temporal": {},
        },
    )
    days = 7
    if period.endswith("d") and period[:-1].isdigit():
      days = int(period[:-1])
    cutoff = datetime.utcnow().date() - timedelta(days=days - 1)
    temporal = {
        d: c
        for d, c in data["temporal"].items()
        if datetime.fromisoformat(d).date() >= cutoff
    }
    return {
        "project_id": project_id,
        "total_retrievals": dict(data["total_retrievals"]),
        "tag_frequencies": dict(data["tag_frequencies"]),
        "lifecycle_counts": dict(data["lifecycle"]),
        "temporal_usage": temporal,
    }


async def main() -> None:
  """Run a single analytics update and print results."""
  storage = InMemoryMemCubeStorage()
  engine = AnalyticsEngine(storage)
  await engine.compute_analytics()
  print(engine.analytics)


if __name__ == "__main__":
  asyncio.run(main())
