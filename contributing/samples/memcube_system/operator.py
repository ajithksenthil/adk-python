"""Memory operator and scheduler for intelligent memory management."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
import hashlib
import json
import logging
import re
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

import numpy as np

from .embedding import compute_embedding
from .models import InsightCard
from .models import MemCube
from .models import MemCubeHeader
from .models import MemCubePayload
from .models import MemoryPriority
from .models import MemoryQuery
from .models import MemoryScheduleRequest
from .models import MemoryType
from .storage import MemCubeStorage

logger = logging.getLogger(__name__)

# Simple regex-based PII detector for demonstration
_PII_PATTERNS = [
    re.compile(r"[A-Za-z]+ [A-Za-z]+"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
]


def _contains_pii(text: str) -> bool:
  """Return True if the text appears to contain PII."""
  for pattern in _PII_PATTERNS:
    if pattern.search(text):
      return True
  return False


@dataclass
class MemoryContext:
  """Context for memory operations."""

  agent_id: str
  task_id: str
  project_id: str
  token_budget: int
  current_tokens: int = 0
  included_memories: List[str] = None

  def __post_init__(self):
    if self.included_memories is None:
      self.included_memories = []

  @property
  def remaining_tokens(self) -> int:
    return self.token_budget - self.current_tokens

  def can_fit(self, memory: MemCube) -> bool:
    """Check if memory fits in remaining budget."""
    tokens = memory.payload.token_count or 100  # Default estimate
    return self.current_tokens + tokens <= self.token_budget


class MemorySelector:
  """
  Intelligent memory selection based on relevance and constraints.

  Uses multiple signals:
  - Tag matching
  - Recency (last_used)
  - Frequency (usage_hits)
  - Priority (hot/warm/cold)
  - Vector similarity (if available)
  - Task context
  """

  def __init__(self, storage: MemCubeStorage):
    self.storage = storage

  async def select_memories(
      self, request: MemoryScheduleRequest
  ) -> List[MemCube]:
    """
    Select optimal set of memories for agent request.

    Returns memories that fit within token budget.
    """
    context = MemoryContext(
        agent_id=request.agent_id,
        task_id=request.task_id,
        project_id=request.project_id,
        token_budget=request.token_budget,
    )

    # Get candidate memories
    candidates = await self._get_candidates(request)

    # Score and rank memories
    scored = await self._score_memories(candidates, request)

    # Select optimal subset within budget
    selected = self._optimize_selection(scored, context)

    # Update usage stats
    for memory in selected:
      await self.storage.update_memory_usage(memory.id)

    logger.info(
        f"Selected {len(selected)} memories for agent {request.agent_id}"
    )
    return selected

  async def _get_candidates(
      self, request: MemoryScheduleRequest
  ) -> List[MemCube]:
    """Get candidate memories based on request."""
    # Start with base query
    query = MemoryQuery(
        project_id=request.project_id,
        tags=request.need_tags,
        include_insights=request.include_insights,
        limit=request.top_k,
    )

    if request.query_text:
      query.query_text = request.query_text

    # Add priority filter if preferring hot
    if request.prefer_hot:
      query.priority_filter = MemoryPriority.HOT

    # Query storage
    memories = await self.storage.query_memories(query)

    # If not enough hot memories, get warm ones too
    if len(memories) < 10 and request.prefer_hot:
      query.priority_filter = MemoryPriority.WARM
      warm_memories = await self.storage.query_memories(query)
      memories.extend(warm_memories)

    return memories

  async def _score_memories(
      self, memories: List[MemCube], request: MemoryScheduleRequest
  ) -> List[Tuple[float, MemCube]]:
    """Score memories based on relevance."""
    scored = []

    query_vec: Optional[List[float]] = None
    if request.query_text:
      query_vec = compute_embedding(request.query_text)

    for memory in memories:
      score = 0.0

      # Tag relevance (0-40 points)
      tag_score = self._compute_tag_relevance(memory, request.need_tags)
      score += tag_score * 40

      # Recency (0-20 points)
      if memory.header.last_used:
        age_hours = (
            datetime.utcnow() - memory.header.last_used
        ).total_seconds() / 3600
        recency_score = max(0, 1 - (age_hours / 168))  # Decay over week
        score += recency_score * 20

      # Frequency (0-20 points)
      freq_score = min(1.0, memory.header.usage_hits / 50)
      score += freq_score * 20

      # Priority bonus (0-10 points)
      if memory.header.priority == MemoryPriority.HOT:
        score += 10
      elif memory.header.priority == MemoryPriority.WARM:
        score += 5

      if query_vec and memory.header.embedding_sig:
        sim = self._compute_similarity(query_vec, memory.header.embedding_sig)
        score += sim * 30

      # Task context bonus (0-10 points)
      if await self._is_task_relevant(memory, request.task_id):
        score += 10

      scored.append((score, memory))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored

  def _compute_tag_relevance(
      self, memory: MemCube, need_tags: List[str]
  ) -> float:
    """Compute tag relevance score."""
    if not need_tags:
      return 0.5  # Neutral if no tags specified

    # Check label for tag matches
    label_lower = memory.header.label.lower()
    matches = sum(1 for tag in need_tags if tag.lower() in label_lower)

    return min(1.0, matches / len(need_tags))

  async def _is_task_relevant(self, memory: MemCube, task_id: str) -> bool:
    """Check if memory is linked to task."""
    # Could query memory_task_links table
    # For now, check if task_id in label or origin
    return task_id in memory.header.label or (
        memory.header.origin and task_id in memory.header.origin
    )

  def _compute_similarity(self, vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between vectors."""
    if len(vec1) != len(vec2):
      return 0.0
    v1 = np.array(vec1, dtype="float32")
    v2 = np.array(vec2, dtype="float32")
    denom = np.linalg.norm(v1) * np.linalg.norm(v2)
    if denom == 0:
      return 0.0
    return float(np.dot(v1, v2) / denom)

  def _optimize_selection(
      self, scored: List[Tuple[float, MemCube]], context: MemoryContext
  ) -> List[MemCube]:
    """
    Select optimal subset within token budget.

    Uses greedy algorithm with diversity bonus.
    """
    selected = []
    selected_types = set()

    for score, memory in scored:
      if not context.can_fit(memory):
        continue

      # Diversity bonus - prefer different types
      if memory.header.type not in selected_types:
        score *= 1.2
        selected_types.add(memory.header.type)

      # Add to selection
      selected.append(memory)
      context.included_memories.append(memory.id)
      context.current_tokens += memory.payload.token_count or 100

      # Stop if budget exhausted
      if context.remaining_tokens < 100:
        break

    return selected


class MemoryScheduler:
  """
  Schedules memory operations across multiple agents.

  Handles:
  - Memory request queuing
  - Priority scheduling
  - Load balancing
  - Caching
  """

  def __init__(
      self,
      storage: MemCubeStorage,
      selector: MemorySelector,
      cache_ttl: int = 300,
  ):
    self.storage = storage
    self.selector = selector
    self.cache_ttl = cache_ttl
    self._cache: Dict[str, Tuple[datetime, List[MemCube]]] = {}
    self._request_queue: asyncio.Queue = asyncio.Queue()
    self._worker_task: Optional[asyncio.Task] = None

  async def start(self):
    """Start the scheduler worker."""
    self._worker_task = asyncio.create_task(self._process_requests())
    logger.info("Memory scheduler started")

  async def stop(self):
    """Stop the scheduler."""
    if self._worker_task:
      self._worker_task.cancel()
      try:
        await self._worker_task
      except asyncio.CancelledError:
        pass

  async def schedule_request(
      self,
      request: MemoryScheduleRequest,
      chain_id: Optional[str] = None,
  ) -> List[MemCube]:
    """
    Schedule a memory request.

    Returns selected memories for the agent.
    """
    if chain_id:
      return await self.storage.get_chain(chain_id)

    # Check cache first
    cache_key = self._get_cache_key(request)
    if cache_key in self._cache:
      cached_time, memories = self._cache[cache_key]
      if datetime.utcnow() - cached_time < timedelta(seconds=self.cache_ttl):
        logger.debug(f"Cache hit for {request.agent_id}")
        return memories

    # Process request
    memories = await self.selector.select_memories(request)

    # Update cache
    self._cache[cache_key] = (datetime.utcnow(), memories)

    # Clean old cache entries periodically
    if len(self._cache) > 1000:
      await self._clean_cache()

    return memories

  def _get_cache_key(self, request: MemoryScheduleRequest) -> str:
    """Generate cache key for request."""
    key_parts = [
        request.project_id,
        request.agent_id,
        str(sorted(request.need_tags)),
        str(request.token_budget),
        str(request.prefer_hot),
    ]
    key_str = "|".join(key_parts)
    return hashlib.md5(key_str.encode()).hexdigest()

  async def _clean_cache(self):
    """Remove expired cache entries."""
    now = datetime.utcnow()
    expired = []

    for key, (cached_time, _) in self._cache.items():
      if now - cached_time > timedelta(seconds=self.cache_ttl):
        expired.append(key)

    for key in expired:
      del self._cache[key]

    logger.debug(f"Cleaned {len(expired)} expired cache entries")

  async def _process_requests(self):
    """Process queued requests."""
    while True:
      try:
        # Process requests with priority
        await asyncio.sleep(0.1)  # Small delay

      except asyncio.CancelledError:
        break
      except Exception as e:
        logger.error(f"Error in scheduler worker: {e}")


class MemoryOperator:
  """
  High-level memory operations and management.

  Provides:
  - Memory creation helpers
  - Batch operations
  - Memory synthesis
  - Insight processing
  """

  def __init__(self, storage: MemCubeStorage):
    self.storage = storage

  async def create_from_text(
      self,
      project_id: str,
      label: str,
      content: str,
      created_by: str,
      tags: Optional[List[str]] = None,
  ) -> MemCube:
    """Create a plaintext memory from text content."""
    # Create header
    header = MemCubeHeader(
        project_id=project_id,
        label=label,
        type=MemoryType.PLAINTEXT,
        created_by=created_by,
        priority=MemoryPriority.WARM,
        embedding_sig=compute_embedding(content),
    )

    if _contains_pii(content):
      header.governance.pii_tagged = True

    # Create payload
    payload = MemCubePayload(
        type=MemoryType.PLAINTEXT,
        content=content,
        token_count=len(content.split()),  # Simple estimate
    )

    # Create and store
    memory = MemCube(header=header, payload=payload)
    await self.storage.store_memory(memory)

    return memory

  async def create_from_activation(
      self,
      project_id: str,
      label: str,
      kv_cache: bytes,
      created_by: str,
      model_hint: str = "",
  ) -> MemCube:
    """Create an activation memory from KV cache."""
    # Create header with KV hint
    header = MemCubeHeader(
        project_id=project_id,
        label=f"{label}::{model_hint}",
        type=MemoryType.ACTIVATION,
        created_by=created_by,
        kv_hint=True,
        priority=MemoryPriority.HOT,  # Activations usually hot
    )

    # Create payload
    payload = MemCubePayload(
        type=MemoryType.ACTIVATION, content=kv_cache, size_bytes=len(kv_cache)
    )

    # Create and store
    memory = MemCube(header=header, payload=payload)
    await self.storage.store_memory(memory)

    return memory

  async def create_from_insight(
      self, project_id: str, insight_card: InsightCard, created_by: str
  ) -> MemCube:
    """Convert insight card to memory."""
    memory = insight_card.to_memcube(project_id, created_by)
    if _contains_pii(memory.payload.content):
      memory.header.governance.pii_tagged = True
    await self.storage.store_memory(memory)
    return memory

  async def synthesize_memories(
      self,
      project_id: str,
      source_memories: List[MemCube],
      synthesis_prompt: str,
      created_by: str,
  ) -> MemCube:
    """
    Synthesize multiple memories into a new one.

    This would typically call an LLM to create a summary.
    """
    # Combine source content
    source_texts = []
    for mem in source_memories:
      if mem.type == MemoryType.PLAINTEXT:
        source_texts.append(mem.to_prompt_text())

    combined = "\n\n".join(source_texts)

    # TODO: Call LLM for synthesis
    synthesized_content = (
        "Synthesis of"
        f" {len(source_memories)} memories:\n{synthesis_prompt}\n\n{combined[:500]}..."
    )

    # Create synthesized memory
    header = MemCubeHeader(
        project_id=project_id,
        label=f"synthesis::{datetime.utcnow().strftime('%Y%m%d_%H%M')}",
        type=MemoryType.PLAINTEXT,
        created_by=created_by,
        origin=f"synthesis_from_{len(source_memories)}_memories",
    )

    payload = MemCubePayload(
        type=MemoryType.PLAINTEXT,
        content=synthesized_content,
        token_count=len(synthesized_content.split()),
    )

    if _contains_pii(synthesized_content):
      header.governance.pii_tagged = True

    memory = MemCube(header=header, payload=payload)
    await self.storage.store_memory(memory)

    # Link to source memories via provenance
    if source_memories:
      memory.header.provenance_id = source_memories[0].id

    return memory

  async def batch_create(self, memories: List[MemCube]) -> List[str]:
    """Batch create multiple memories."""
    memory_ids = []

    for memory in memories:
      try:
        memory_id = await self.storage.store_memory(memory)
        memory_ids.append(memory_id)
      except Exception as e:
        logger.error(f"Failed to create memory {memory.label}: {e}")

    return memory_ids

  async def update_memory_content(
      self, memory_id: str, new_content: str, updated_by: str
  ) -> Optional[MemCube]:
    """Update memory content (creates new version)."""
    # Get existing memory
    existing = await self.storage.get_memory(memory_id)
    if not existing:
      return None

    # Create new version
    existing.header.version += 1
    existing.header.created_by = updated_by
    existing.header.created_at = datetime.utcnow()
    existing.header.provenance_id = memory_id  # Link to original

    # Update payload
    existing.payload.content = new_content
    existing.payload.token_count = len(new_content.split())
    existing.header.embedding_sig = compute_embedding(new_content)

    # Store as new memory (versioned)
    new_id = await self.storage.store_memory(existing)
    existing.header.id = new_id

    return existing

  async def get_memory_lineage(
      self, memory_id: str, max_depth: int = 5
  ) -> List[MemCube]:
    """Get memory lineage (provenance chain)."""
    lineage = []
    current_id = memory_id
    depth = 0

    while current_id and depth < max_depth:
      memory = await self.storage.get_memory(current_id)
      if not memory:
        break

      lineage.append(memory)
      current_id = memory.header.provenance_id
      depth += 1

    return lineage

  async def prune_cold_memories(
      self, project_id: str, keep_count: int = 100
  ) -> int:
    """Prune cold memories beyond retention limit."""
    # Query cold memories
    query = MemoryQuery(
        project_id=project_id, priority_filter=MemoryPriority.COLD, limit=1000
    )

    cold_memories = await self.storage.query_memories(query)

    # Sort by last_used (oldest first)
    cold_memories.sort(key=lambda m: m.header.last_used or datetime.min)

    # Archive oldest beyond keep_count
    archived = 0
    if len(cold_memories) > keep_count:
      for memory in cold_memories[keep_count:]:
        if await self.storage.archive_memory(memory.id):
          archived += 1

    logger.info(f"Archived {archived} cold memories from project {project_id}")
    return archived
