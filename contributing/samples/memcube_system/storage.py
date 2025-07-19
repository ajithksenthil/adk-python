"""Storage layer for MemCube memory system using Supabase."""

import asyncio
import base64
from datetime import datetime
from datetime import timedelta
import json
import logging
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
import uuid
import secrets

import aiohttp
import faiss
import numpy as np
from pydantic import BaseModel
from supabase import Client
from supabase import create_client

from .embedding import compute_embedding
from .models import MemCube
from .models import MemCubeHeader
from .models import MemCubePayload
from .models import MemoryEvent
from .models import MemoryLifecycle
from .models import MemoryLink
from .models import MemoryPriority
from .models import MemoryQuery
from .models import MemoryType
from .models import MemoryVersion
from .models import StorageMode

logger = logging.getLogger(__name__)


class SimpleKeyService:
  """Placeholder key management service."""

  _keys: Dict[str, bytes] = {}

  @classmethod
  def generate_key(cls, memory_id: str) -> bytes:
    key = secrets.token_bytes(16)
    cls._keys[memory_id] = key
    return key

  @classmethod
  def get_key(cls, memory_id: str) -> Optional[bytes]:
    return cls._keys.get(memory_id)


def _xor(data: bytes, key: bytes) -> bytes:
  """Simple XOR encryption/decryption."""
  return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))




class MemCubeStorage:
  """Abstract base class for MemCube storage backends."""

  async def store_memory(self, memory: MemCube) -> str:
    """Store a memory cube and return its ID."""
    raise NotImplementedError

  async def get_memory(self, memory_id: str) -> Optional[MemCube]:
    """Retrieve a memory cube by ID."""
    raise NotImplementedError

  async def query_memories(self, query: MemoryQuery) -> List[MemCube]:
    """Query memories based on criteria."""
    raise NotImplementedError

  async def update_memory_usage(self, memory_id: str) -> None:
    """Update usage statistics for a memory."""
    raise NotImplementedError

  async def archive_memory(self, memory_id: str) -> bool:
    """Archive a memory cube."""
    raise NotImplementedError

  async def list_pii_memories(self, project_id: str) -> List[MemCube]:
    """List memories tagged as containing PII."""
    raise NotImplementedError

  async def get_access_logs(self, project_id: str) -> List[Dict[str, Any]]:
    """Return access log events for a project."""
    raise NotImplementedError

  async def create_chain(
      self,
      project_id: str,
      label: str,
      created_by: str,
      tags: Optional[List[str]] = None,
  ) -> str:
    """Create a memory chain."""
    raise NotImplementedError

  async def append_to_chain(self, chain_id: str, memory_id: str) -> bool:
    """Append memory to chain."""
    raise NotImplementedError

  async def remove_from_chain(self, chain_id: str, memory_id: str) -> bool:
    """Remove memory from chain."""
    raise NotImplementedError

  async def get_chain(self, chain_id: str) -> List[MemCube]:
    """Retrieve ordered memories from chain."""
    raise NotImplementedError


class SupabaseMemCubeStorage(MemCubeStorage):
  """
  Supabase-backed storage for MemCube system.

  Expected Supabase schema:
  - memories: Core memory table with header data
  - memory_payloads: Payload storage (can be external)
  - memory_versions: Version history
  - memory_events: Audit trail
  - memory_task_links: Task associations
  """

  def __init__(
      self,
      supabase_url: str,
      supabase_key: str,
      blob_storage_url: Optional[str] = None,
  ):
    self.client: Client = create_client(supabase_url, supabase_key)
    self.blob_storage_url = blob_storage_url
    self._session: Optional[aiohttp.ClientSession] = None

  async def __aenter__(self):
    self._session = aiohttp.ClientSession()
    return self

  async def __aexit__(self, exc_type, exc_val, exc_tb):
    if self._session:
      await self._session.close()

  async def store_memory(self, memory: MemCube) -> str:
    """
    Store a memory cube in Supabase.

    Splits header and payload for efficient storage.
    Large payloads go to blob storage.
    """
    try:
      # Determine storage mode based on size
      payload_size = memory.payload.get_size()
      storage_mode = self._determine_storage_mode(payload_size)

      # Store payload
      payload_ref = await self._store_payload(
          memory.id,
          memory.payload,
          storage_mode,
          encrypt=memory.header.governance.pii_tagged,
      )

      # Prepare header data for DB
      header_data = {
          "id": memory.header.id,
          "project_id": memory.header.project_id,
          "label": memory.header.label,
          "type": memory.header.type.value,
          "version": memory.header.version,
          "origin": memory.header.origin,
          "created_by": memory.header.created_by,
          "created_at": memory.header.created_at.isoformat(),
          "embedding_sig": memory.header.embedding_sig,
          "governance": json.dumps({
              "read_roles": memory.header.governance.read_roles,
              "write_roles": memory.header.governance.write_roles,
              "ttl_days": memory.header.governance.ttl_days,
              "shareable": memory.header.governance.shareable,
              "license": memory.header.governance.license,
              "pii_tagged": memory.header.governance.pii_tagged,
          }),
          "usage_hits": memory.header.usage_hits,
          "last_used": (
              memory.header.last_used.isoformat()
              if memory.header.last_used
              else None
          ),
          "priority": memory.header.priority.value,
          "storage_mode": storage_mode.value,
          "provenance_id": memory.header.provenance_id,
          "kv_hint": memory.header.kv_hint,
          "watermark": memory.header.watermark,
          "payload_ref": payload_ref,
          "size_bytes": payload_size,
          "token_count": memory.payload.token_count,
      }

      # Insert into memories table
      result = self.client.table("memories").insert(header_data).execute()

      # Create version record
      version_data = {
          "memory_id": memory.id,
          "version": memory.header.version,
          "blob_path": (
              payload_ref if storage_mode != StorageMode.INLINE else None
          ),
          "vector_sig": memory.header.embedding_sig,
          "token_count": memory.payload.token_count or 0,
          "created_by": memory.header.created_by,
          "created_at": memory.header.created_at.isoformat(),
          "kv_hint": memory.header.kv_hint,
          "provenance_id": memory.header.provenance_id,
      }
      self.client.table("memory_versions").insert(version_data).execute()

      # Log creation event
      await self._log_event(
          memory.id,
          "CREATED",
          memory.header.created_by,
          project_id=memory.header.project_id,
      )

      logger.info(f"Stored memory {memory.id} with {storage_mode.value} mode")
      return memory.id

    except Exception as e:
      logger.error(f"Failed to store memory: {e}")
      raise

  async def get_memory(self, memory_id: str) -> Optional[MemCube]:
    """Retrieve a memory cube by ID."""
    try:
      # Get header from memories table
      result = (
          self.client.table("memories")
          .select("*")
          .eq("id", memory_id)
          .execute()
      )

      if not result.data:
        return None

      header_data = result.data[0]

      # Reconstruct governance
      governance_data = json.loads(header_data["governance"])
      from dataclasses import dataclass

      from .models import MemoryGovernance

      governance = MemoryGovernance(
          read_roles=governance_data.get("read_roles", ["MEMBER"]),
          write_roles=governance_data.get("write_roles", ["AGENT"]),
          ttl_days=governance_data.get("ttl_days", 365),
          shareable=governance_data.get("shareable", True),
          license=governance_data.get("license", []),
          pii_tagged=governance_data.get("pii_tagged", False),
      )

      # Reconstruct header
      header = MemCubeHeader(
          id=header_data["id"],
          project_id=header_data["project_id"],
          label=header_data["label"],
          type=MemoryType(header_data["type"]),
          version=header_data["version"],
          origin=header_data["origin"],
          created_by=header_data["created_by"],
          created_at=datetime.fromisoformat(header_data["created_at"]),
          embedding_sig=header_data["embedding_sig"],
          governance=governance,
          usage_hits=header_data["usage_hits"],
          last_used=datetime.fromisoformat(header_data["last_used"])
          if header_data["last_used"]
          else None,
          priority=MemoryPriority(header_data["priority"]),
          storage_mode=StorageMode(header_data["storage_mode"]),
          provenance_id=header_data["provenance_id"],
          kv_hint=header_data["kv_hint"],
          watermark=header_data["watermark"],
      )

      # Retrieve payload
      payload = await self._retrieve_payload(
          memory_id,
          header_data["payload_ref"],
          StorageMode(header_data["storage_mode"]),
          MemoryType(header_data["type"]),
          encrypted=governance.pii_tagged,
      )

      if not payload:
        logger.warning(f"Failed to retrieve payload for memory {memory_id}")
        return None

      memory = MemCube(header=header, payload=payload)
      await self._log_event(
          memory.id,
          "RETRIEVED",
          "system",
          project_id=memory.header.project_id,
      )
      return memory

    except Exception as e:
      logger.error(f"Failed to get memory {memory_id}: {e}")
      return None

  async def query_memories(self, query: MemoryQuery) -> List[MemCube]:
    """
    Query memories based on criteria.

    Supports filtering by:
    - Project ID
    - Tags (via JSON search)
    - Memory type
    - Priority
    - Vector similarity (if embeddings available)
    """
    try:
      # Compute query embedding if query text provided
      if query.query_text and not query.embedding:
        query.embedding = compute_embedding(query.query_text)

      # Start with base query
      q = (
          self.client.table("memories")
          .select("*")
          .eq("project_id", query.project_id)
      )

      # Add type filter
      if query.type_filter:
        q = q.eq("type", query.type_filter.value)

      # Add priority filter
      if query.priority_filter:
        q = q.eq("priority", query.priority_filter.value)

      # Execute query
      result = q.execute()

      candidate_rows = []
      vectors = []
      for row in result.data:
        if query.tags and not self._matches_tags(row, query.tags):
          continue
        if row.get("embedding_sig"):
          vectors.append(np.array(row["embedding_sig"], dtype="float32"))
          candidate_rows.append(row)

      ranked_ids: List[str] = []
      if query.embedding and vectors:
        index = faiss.IndexFlatIP(len(query.embedding))
        index.add(np.vstack(vectors))
        scores, idxs = index.search(
            np.array([query.embedding], dtype="float32"),
            min(query.limit * 2, len(vectors)),
        )
        for score, idx in zip(scores[0], idxs[0]):
          if score < query.similarity_threshold:
            continue
          ranked_ids.append(candidate_rows[idx]["id"])
          if len(ranked_ids) >= query.limit:
            break
      else:
        ranked_ids = [row["id"] for row in candidate_rows[: query.limit]]

      memories = []
      for mid in ranked_ids:
        memory = await self.get_memory(mid)
        if memory:
          memories.append(memory)

      # Include insights if requested
      if query.include_insights and len(memories) < query.limit:
        insights = await self._get_insight_memories(
            query.project_id, query.limit - len(memories)
        )
        memories.extend(insights)

      return memories

    except Exception as e:
      logger.error(f"Failed to query memories: {e}")
      return []

  async def update_memory_usage(self, memory_id: str) -> None:
    """Update usage statistics for a memory."""
    try:
      # Increment usage counter and update last_used
      now = datetime.utcnow()

      result = (
          self.client.table("memories")
          .update({
              "usage_hits": self.client.rpc("increment", {"value": 1}),
              "last_used": now.isoformat(),
          })
          .eq("id", memory_id)
          .execute()
      )

      # Log access event
      await self._log_event(memory_id, "ACCESSED", "system", project_id=None)

      # Check if should promote to HOT
      if result.data and result.data[0]["usage_hits"] > 10:
        await self._update_priority(memory_id, MemoryPriority.HOT)

    except Exception as e:
      logger.error(f"Failed to update usage for {memory_id}: {e}")

  async def archive_memory(self, memory_id: str) -> bool:
    """Archive a memory cube."""
    try:
      # Update lifecycle state
      result = (
          self.client.table("memories")
          .update({
              "lifecycle": MemoryLifecycle.ARCHIVED.value,
              "priority": MemoryPriority.COLD.value,
          })
          .eq("id", memory_id)
          .execute()
      )

      if result.data:
        await self._log_event(memory_id, "ARCHIVED", "system", project_id=None)
        return True

      return False

    except Exception as e:
      logger.error(f"Failed to archive memory {memory_id}: {e}")
      return False

  async def list_pii_memories(self, project_id: str) -> List[MemCube]:
    query = MemoryQuery(project_id=project_id)
    mems = await self.query_memories(query)
    return [m for m in mems if m.header.governance.pii_tagged]

  async def get_access_logs(self, project_id: str) -> List[Dict[str, Any]]:
    try:
      result = (
          self.client.table("memory_events")
          .select("*")
          .eq("project_id", project_id)
          .execute()
      )
      return result.data or []
    except Exception as e:
      logger.error(f"Failed to fetch access logs: {e}")
      return []

  async def link_memory_to_task(
      self, memory_id: str, task_id: str, role: str = "READ"
  ) -> bool:
    """Create a link between memory and task."""
    try:
      link_data = {"memory_id": memory_id, "task_id": task_id, "role": role}

      self.client.table("memory_task_links").insert(link_data).execute()
      return True

    except Exception as e:
      logger.error(f"Failed to link memory {memory_id} to task {task_id}: {e}")
      return False

  async def get_memories_for_task(self, task_id: str) -> List[MemCube]:
    """Get all memories linked to a task."""
    try:
      # Get memory IDs linked to task
      result = (
          self.client.table("memory_task_links")
          .select("memory_id")
          .eq("task_id", task_id)
          .execute()
      )

      memories = []
      for link in result.data:
        memory = await self.get_memory(link["memory_id"])
        if memory:
          memories.append(memory)

      return memories

    except Exception as e:
      logger.error(f"Failed to get memories for task {task_id}: {e}")
      return []

  async def create_chain(
      self,
      project_id: str,
      label: str,
      created_by: str,
      tags: Optional[List[str]] = None,
  ) -> str:
    chain_id = str(uuid.uuid4())
    try:
      data = {
          "id": chain_id,
          "project_id": project_id,
          "label": label,
          "created_by": created_by,
          "created_at": datetime.utcnow().isoformat(),
          "tags": json.dumps(tags or []),
      }
      self.client.table("memory_chains").insert(data).execute()
      return chain_id
    except Exception as e:
      logger.error(f"Failed to create chain: {e}")
      return chain_id

  async def append_to_chain(self, chain_id: str, memory_id: str) -> bool:
    try:
      result = (
          self.client.table("memory_chain_links")
          .select("position")
          .eq("chain_id", chain_id)
          .order("position", desc=True)
          .limit(1)
          .execute()
      )
      pos = result.data[0]["position"] + 1 if result.data else 1
      link = {
          "chain_id": chain_id,
          "memory_id": memory_id,
          "position": pos,
          "added_at": datetime.utcnow().isoformat(),
      }
      self.client.table("memory_chain_links").insert(link).execute()
      return True
    except Exception as e:
      logger.error(f"Failed to append {memory_id} to chain {chain_id}: {e}")
      return False

  async def remove_from_chain(self, chain_id: str, memory_id: str) -> bool:
    try:
      self.client.table("memory_chain_links").delete().eq(
          "chain_id", chain_id
      ).eq("memory_id", memory_id).execute()
      return True
    except Exception as e:
      logger.error(f"Failed to remove {memory_id} from chain {chain_id}: {e}")
      return False

  async def get_chain(self, chain_id: str) -> List[MemCube]:
    try:
      result = (
          self.client.table("memory_chain_links")
          .select("memory_id, position")
          .eq("chain_id", chain_id)
          .order("position")
          .execute()
      )
      ordered = []
      for row in result.data:
        mem = await self.get_memory(row["memory_id"])
        if mem:
          ordered.append(mem)
      return ordered
    except Exception as e:
      logger.error(f"Failed to get chain {chain_id}: {e}")
      return []

  # Private helper methods

  def _determine_storage_mode(self, size_bytes: int) -> StorageMode:
    """Determine storage mode based on payload size."""
    if size_bytes < 4 * 1024:  # < 4KB
      return StorageMode.INLINE
    elif size_bytes < 64 * 1024:  # < 64KB
      return StorageMode.COMPRESSED
    else:
      return StorageMode.COLD

  async def _store_payload(
      self,
      memory_id: str,
      payload: MemCubePayload,
      mode: StorageMode,
      *,
      encrypt: bool = False,
  ) -> str:
    """Store payload based on storage mode."""
    content_bytes = self._serialize_payload(payload)

    if mode == StorageMode.COMPRESSED:
      import gzip
      content_bytes = gzip.compress(content_bytes)

    if encrypt:
      key = SimpleKeyService.generate_key(memory_id)
      content_bytes = _xor(content_bytes, key)
      return base64.b64encode(content_bytes).decode()

    if mode == StorageMode.INLINE:
      if isinstance(payload.content, str) and not encrypt:
        return payload.content
      return base64.b64encode(content_bytes).decode()

    else:  # COLD storage
      if encrypt:
        key = SimpleKeyService.generate_key(memory_id)
        encrypted_bytes = _xor(content_bytes, key)
        return base64.b64encode(encrypted_bytes).decode()
      if self.blob_storage_url:
        return await self._store_to_blob(memory_id, payload)
      return await self._store_payload(
          memory_id, payload, StorageMode.COMPRESSED
      )

  async def _retrieve_payload(
      self,
      memory_id: str,
      payload_ref: str,
      mode: StorageMode,
      mem_type: MemoryType,
      *,
      encrypted: bool = False,
  ) -> Optional[MemCubePayload]:
    """Retrieve payload based on storage mode."""
    try:
      if encrypted:
        data = base64.b64decode(payload_ref)
        key = SimpleKeyService.get_key(memory_id)
        if not key:
          raise ValueError("missing key")
        data = _xor(data, key)
        if mode == StorageMode.COMPRESSED:
          import gzip
          data = gzip.decompress(data)
        content = self._deserialize_payload(data, mem_type)

      elif mode == StorageMode.INLINE:
        if mem_type == MemoryType.PLAINTEXT:
          content = payload_ref
        elif mem_type == MemoryType.ACTIVATION:
          content = base64.b64decode(payload_ref)
        else:
          content = json.loads(payload_ref)

      elif mode == StorageMode.COMPRESSED:
        import gzip
        compressed = base64.b64decode(payload_ref)
        content_bytes = gzip.decompress(compressed)
        content = self._deserialize_payload(content_bytes, mem_type)

      else:  # COLD storage
        # Retrieve from blob
        if self.blob_storage_url:
          content = await self._retrieve_from_blob(memory_id)
        else:
          # Try as compressed
          return await self._retrieve_payload(
              memory_id,
              payload_ref,
              StorageMode.COMPRESSED,
              mem_type,
              encrypted=encrypted,
          )

      return MemCubePayload(
          type=mem_type, content=content, size_bytes=len(str(content).encode())
      )

    except Exception as e:
      logger.error(f"Failed to retrieve payload: {e}")
      return None

  def _serialize_payload(self, payload: MemCubePayload) -> bytes:
    """Serialize payload to bytes."""
    if isinstance(payload.content, bytes):
      return payload.content
    elif isinstance(payload.content, str):
      return payload.content.encode()
    else:
      return json.dumps(payload.content).encode()

  def _deserialize_payload(self, data: bytes, mem_type: MemoryType) -> Any:
    """Deserialize payload from bytes."""
    if mem_type == MemoryType.ACTIVATION:
      return data
    elif mem_type == MemoryType.PLAINTEXT:
      return data.decode()
    else:
      return json.loads(data.decode())

  async def _store_to_blob(
      self, memory_id: str, payload: MemCubePayload
  ) -> str:
    """Store payload to external blob storage."""
    # Implementation depends on blob storage provider
    # Return blob path/URL
    blob_path = f"memories/{memory_id}/v{datetime.utcnow().timestamp()}"
    # TODO: Actual blob storage implementation
    return blob_path

  async def _retrieve_from_blob(self, memory_id: str) -> Any:
    """Retrieve payload from blob storage."""
    # TODO: Actual blob retrieval
    return None

  def _matches_tags(self, row: Dict[str, Any], tags: List[str]) -> bool:
    """Check if memory matches required tags."""
    # Simple implementation - could be enhanced
    label = row.get("label", "").lower()
    return any(tag.lower() in label for tag in tags)

  def _compute_similarity(self, vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between vectors."""
    if len(vec1) != len(vec2):
      return 0.0

    v1 = np.array(vec1)
    v2 = np.array(vec2)

    dot_product = np.dot(v1, v2)
    norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)

    if norm_product == 0:
      return 0.0

    return dot_product / norm_product

  async def _update_priority(
      self, memory_id: str, priority: MemoryPriority
  ) -> None:
    """Update memory priority."""
    try:
      self.client.table("memories").update({"priority": priority.value}).eq(
          "id", memory_id
      ).execute()

      await self._log_event(
          memory_id,
          f"PRIORITY_CHANGED_{priority.value}",
          "system",
          project_id=None,
      )

    except Exception as e:
      logger.error(f"Failed to update priority: {e}")

  async def _log_event(
      self,
      memory_id: str,
      event: str,
      actor: str,
      meta: Optional[Dict[str, Any]] = None,
      project_id: Optional[str] = None,
  ) -> None:
    """Log a memory event."""
    try:
      event_data = {
          "memory_id": memory_id,
          "event": event,
          "actor": actor,
          "ts": datetime.utcnow().isoformat(),
          "meta": json.dumps(meta or {}),
      }
      if project_id:
        event_data["project_id"] = project_id

      self.client.table("memory_events").insert(event_data).execute()

    except Exception as e:
      logger.error(f"Failed to log event: {e}")

  async def _get_insight_memories(
      self, project_id: str, limit: int
  ) -> List[MemCube]:
    """Get insight-based memories."""
    # TODO: Query insights table and convert to memories
    return []


class MemoryLifecycleManager:
  """
  Manages memory lifecycle transitions and cleanup.

  Handles:
  - TTL expiration
  - Priority decay
  - Archive policies
  - Cleanup tasks
  """

  def __init__(self, storage: SupabaseMemCubeStorage):
    self.storage = storage

  async def run_lifecycle_tasks(self) -> None:
    """Run periodic lifecycle management tasks."""
    await asyncio.gather(
        self._expire_old_memories(),
        self._decay_unused_memories(),
        self._cleanup_orphaned_payloads(),
    )

  async def _expire_old_memories(self) -> None:
    """Expire memories past their TTL."""
    try:
      # Query memories with governance data
      result = (
          self.storage.client.table("memories")
          .select("id, created_at, governance")
          .execute()
      )

      now = datetime.utcnow()

      for row in result.data:
        created_at = datetime.fromisoformat(row["created_at"])
        governance = json.loads(row["governance"])
        ttl_days = governance.get("ttl_days", 365)

        if now - created_at > timedelta(days=ttl_days):
          await self.storage.archive_memory(row["id"])
          logger.info(f"Expired memory {row['id']} after {ttl_days} days")

    except Exception as e:
      logger.error(f"Failed to expire memories: {e}")

  async def _decay_unused_memories(self) -> None:
    """Decay priority of unused memories."""
    try:
      # Find memories not used in 30 days
      cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()

      result = (
          self.storage.client.table("memories")
          .select("id, priority")
          .lt("last_used", cutoff)
          .execute()
      )

      for row in result.data:
        current_priority = MemoryPriority(row["priority"])

        # Decay priority
        if current_priority == MemoryPriority.HOT:
          new_priority = MemoryPriority.WARM
        elif current_priority == MemoryPriority.WARM:
          new_priority = MemoryPriority.COLD
        else:
          continue

        await self.storage._update_priority(row["id"], new_priority)

    except Exception as e:
      logger.error(f"Failed to decay memories: {e}")

  async def _cleanup_orphaned_payloads(self) -> None:
    """Clean up payloads without headers."""
    # TODO: Implement blob storage cleanup
    pass
