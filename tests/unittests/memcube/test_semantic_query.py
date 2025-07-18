from __future__ import annotations

import pytest

from contributing.samples.memcube_system.in_memory_storage import InMemoryMemCubeStorage
from contributing.samples.memcube_system.models import MemoryQuery
from contributing.samples.memcube_system.operator import MemoryOperator


@pytest.mark.asyncio
async def test_query_text_returns_relevant_memory() -> None:
  storage = InMemoryMemCubeStorage()
  operator = MemoryOperator(storage)

  m1 = await operator.create_from_text(
      project_id="p1",
      label="apple",
      content="An apple a day keeps the doctor away",
      created_by="user1",
      tags=["fruit"],
  )
  m2 = await operator.create_from_text(
      project_id="p1",
      label="banana",
      content="Bananas are yellow and sweet",
      created_by="user1",
      tags=["fruit"],
  )

  query = MemoryQuery(
      project_id="p1", query_text="apple", limit=1, similarity_threshold=0.0
  )
  results = await storage.query_memories(query)

  assert len(results) == 1
  assert results[0].id == m1.id
