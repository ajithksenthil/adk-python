from __future__ import annotations

from typing import Dict
from typing import List
from typing import Optional

import faiss
import numpy as np

from .embedding import compute_embedding
from .models import MemCube
from .models import MemoryPriority
from .models import MemoryQuery
from .storage import MemCubeStorage


class InMemoryMemCubeStorage(MemCubeStorage):
  """Simple in-memory storage for testing."""

  def __init__(self):
    self.memories: Dict[str, MemCube] = {}

  async def store_memory(self, memory: MemCube) -> str:
    self.memories[memory.id] = memory
    return memory.id

  async def get_memory(self, memory_id: str) -> Optional[MemCube]:
    return self.memories.get(memory_id)

  async def query_memories(self, query: MemoryQuery) -> List[MemCube]:
    mems = [
        m
        for m in self.memories.values()
        if m.header.project_id == query.project_id
    ]
    if query.type_filter:
      mems = [m for m in mems if m.type == query.type_filter]
    if query.priority_filter:
      mems = [m for m in mems if m.header.priority == query.priority_filter]
    if query.tags:
      mems = [m for m in mems if any(t in m.label for t in query.tags)]

    if query.query_text and not query.embedding:
      query.embedding = compute_embedding(query.query_text)

    if query.embedding:
      vecs = []
      mem_list = []
      for m in mems:
        if m.header.embedding_sig:
          vecs.append(np.array(m.header.embedding_sig, dtype='float32'))
          mem_list.append(m)
      if vecs:
        index = faiss.IndexFlatIP(len(query.embedding))
        index.add(np.vstack(vecs))
        scores, idxs = index.search(
            np.array([query.embedding], dtype='float32'),
            min(query.limit, len(vecs)),
        )
        results = []
        for score, idx in zip(scores[0], idxs[0]):
          if score < query.similarity_threshold:
            continue
          results.append(mem_list[idx])
          if len(results) >= query.limit:
            break
        mems = results
      else:
        mems = mem_list[: query.limit]
    return mems[: query.limit]

  async def update_memory_usage(self, memory_id: str) -> None:
    pass

  async def archive_memory(self, memory_id: str) -> bool:
    return self.memories.pop(memory_id, None) is not None
