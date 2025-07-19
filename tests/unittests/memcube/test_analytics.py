from __future__ import annotations

import pytest

from contributing.samples.memcube_system.analytics import AnalyticsEngine
from contributing.samples.memcube_system.in_memory_storage import InMemoryMemCubeStorage
from contributing.samples.memcube_system.operator import MemoryOperator


@pytest.mark.asyncio
async def test_usage_metrics() -> None:
  storage = InMemoryMemCubeStorage()
  operator = MemoryOperator(storage)
  analytics = AnalyticsEngine(storage)

  m1 = await operator.create_from_text(
      project_id="p1", label="alpha", content="a", created_by="u1"
  )
  m2 = await operator.create_from_text(
      project_id="p1", label="beta", content="b", created_by="u1"
  )

  await storage._log_event(
      m1.id, "RETRIEVED", "u1", project_id="p1", meta={"tags": ["t1"]}
  )
  await storage._log_event(
      m1.id, "RETRIEVED", "u1", project_id="p1", meta={"tags": ["t1"]}
  )
  await storage._log_event(
      m2.id, "RETRIEVED", "u2", project_id="p1", meta={"tags": ["t2"]}
  )

  await analytics.compute_analytics()
  metrics = await analytics.get_usage("p1", period="7d")

  assert metrics["total_retrievals"][m1.id] == 2
  assert metrics["total_retrievals"][m2.id] == 1
  assert metrics["tag_frequencies"]["t1"] == 2
  assert metrics["tag_frequencies"]["t2"] == 1
  assert metrics["lifecycle_counts"]["NEW"] == 2
  assert metrics["lifecycle_counts"]["ACTIVE"] == 3
