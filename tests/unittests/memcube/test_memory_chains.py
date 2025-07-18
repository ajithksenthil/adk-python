from __future__ import annotations

import pytest

from contributing.samples.memcube_system.in_memory_storage import InMemoryMemCubeStorage
from contributing.samples.memcube_system.operator import MemoryOperator


@pytest.mark.asyncio
async def test_memory_chain_ordered_retrieval() -> None:
  storage = InMemoryMemCubeStorage()
  operator = MemoryOperator(storage)

  m1 = await operator.create_from_text(
      project_id="p1", label="m1", content="one", created_by="user", tags=[]
  )
  m2 = await operator.create_from_text(
      project_id="p1", label="m2", content="two", created_by="user", tags=[]
  )

  chain_id = await storage.create_chain("p1", "chain", "user")
  await storage.append_to_chain(chain_id, m1.id)
  await storage.append_to_chain(chain_id, m2.id)

  memories = await storage.get_chain(chain_id)

  assert [m.id for m in memories] == [m1.id, m2.id]
