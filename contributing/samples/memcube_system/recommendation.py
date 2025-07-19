from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from .in_memory_storage import InMemoryMemCubeStorage


class RecommendationEngine:
  """Compute project memory recommendations based on usage."""

  def __init__(self, storage: InMemoryMemCubeStorage, interval_seconds: int = 3600):
    self.storage = storage
    self.interval_seconds = interval_seconds
    self._task: Optional[asyncio.Task] = None

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
      await self.update_all_projects()
      await asyncio.sleep(self.interval_seconds)

  async def update_all_projects(self) -> None:
    projects = {e["project_id"] for e in self.storage.events if e.get("project_id")}
    for pid in projects:
      self.update_project(pid)

  def update_project(self, project_id: str, top_n: int = 10) -> None:
    events = [e for e in self.storage.events if e.get("project_id")]
    memory_projects: Dict[str, set[str]] = defaultdict(set)
    for e in events:
      if e["event"] == "RETRIEVED":
        memory_projects[e["memory_id"]].add(e["project_id"])

    project_memories = {
        e["memory_id"]
        for e in events
        if e.get("project_id") == project_id and e["event"] == "RETRIEVED"
    }

    scores: Dict[str, float] = {}
    for mem, projects in memory_projects.items():
      if mem in project_memories:
        continue
      best = 0.0
      for pmem in project_memories:
        union = projects | memory_projects[pmem]
        inter = projects & memory_projects[pmem]
        if union:
          sim = len(inter) / len(union)
          if sim > best:
            best = sim
      if best > 0:
        scores[mem] = best

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    self.storage.recommendations[project_id] = ranked

  def get_recommendations(self, project_id: str, limit: int = 10) -> List[Dict[str, float]]:
    recs = self.storage.recommendations.get(project_id, [])[:limit]
    return [{"memory_id": mid, "score": score} for mid, score in recs]
