from __future__ import annotations

import pytest

from contributing.samples.memcube_system.in_memory_storage import InMemoryMemCubeStorage
from contributing.samples.memcube_system.operator import MemoryOperator
from contributing.samples.memcube_system.recommendation import RecommendationEngine


@pytest.mark.asyncio
async def test_project_recommendations() -> None:
  storage = InMemoryMemCubeStorage()
  operator = MemoryOperator(storage)
  recommender = RecommendationEngine(storage)

  m1 = await operator.create_from_text(
      project_id="p1", label="A", content="alpha", created_by="u1", tags=[]
  )
  m2 = await operator.create_from_text(
      project_id="p1", label="B", content="beta", created_by="u1", tags=[]
  )
  m3 = await operator.create_from_text(
      project_id="p2", label="C", content="gamma", created_by="u2", tags=[]
  )

  # Simulate retrieval events
  await storage._log_event(m1.id, "RETRIEVED", "u1", project_id="p1")
  await storage._log_event(m2.id, "RETRIEVED", "u1", project_id="p1")
  await storage._log_event(m2.id, "RETRIEVED", "u2", project_id="p2")
  await storage._log_event(m3.id, "RETRIEVED", "u2", project_id="p2")

  recommender.update_project("p2", top_n=2)
  recs = recommender.get_recommendations("p2")

  assert recs
  assert recs[0]["memory_id"] == m1.id

