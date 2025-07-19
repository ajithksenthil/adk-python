"""MemCube API Service - REST endpoints for memory management."""

from contextlib import asynccontextmanager
from datetime import datetime
import logging
import os
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from fastapi import Body
from fastapi import Depends
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic import Field
import uvicorn

from .marketplace import MarketplaceService
from .models import InsightCard
from .models import MemCube
from .models import MemoryPriority
from .models import MemoryQuery
from .models import MemoryScheduleRequest
from .models import MemoryType
from .operator import MemoryOperator
from .operator import MemoryScheduler
from .operator import MemorySelector
from .storage import MemoryLifecycleManager
from .storage import SupabaseMemCubeStorage
from .recommendation import RecommendationEngine
from .analytics import AnalyticsEngine

logger = logging.getLogger(__name__)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "http://localhost:54321")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-supabase-key")
BLOB_STORAGE_URL = os.getenv("BLOB_STORAGE_URL", "")
MARKETPLACE_API = os.getenv("MARKETPLACE_API", "http://localhost:8001")

# Global instances
storage: Optional[SupabaseMemCubeStorage] = None
operator: Optional[MemoryOperator] = None
scheduler: Optional[MemoryScheduler] = None
marketplace: Optional[MarketplaceService] = None
lifecycle_manager: Optional[MemoryLifecycleManager] = None
recommender: Optional[RecommendationEngine] = None
analytics: Optional[AnalyticsEngine] = None


# Request/Response models
class MemoryCreateRequest(BaseModel):
  """Request to create a new memory."""

  project_id: str
  label: str
  content: str
  type: MemoryType = MemoryType.PLAINTEXT
  created_by: str
  tags: List[str] = Field(default_factory=list)
  priority: MemoryPriority = MemoryPriority.WARM
  governance: Optional[Dict[str, Any]] = None


class MemoryUpdateRequest(BaseModel):
  """Request to update memory content."""

  content: str
  updated_by: str


class MemoryQueryRequest(BaseModel):
  """Request for querying memories."""

  project_id: str
  query_text: Optional[str] = None
  tags: List[str] = Field(default_factory=list)
  type_filter: Optional[MemoryType] = None
  priority_filter: Optional[MemoryPriority] = None
  top_k: int = 10
  similarity_threshold: float = 0.78


class PackCreateRequest(BaseModel):
  """Request to create a memory pack."""

  title: str
  description: str
  tags: List[str] = Field(default_factory=list)
  max_memories: int = 50
  price_cents: int = 0
  royalty_pct: int = 10
  cover_img: Optional[str] = None


class InsightCreateRequest(BaseModel):
  """Request to create an insight."""

  insight: str
  evidence_refs: List[str] = Field(default_factory=list)
  tags: List[str] = Field(default_factory=list)
  sentiment: float = Field(0.0, ge=-1.0, le=1.0)


class ChainCreateRequest(BaseModel):
  """Request to create a memory chain."""

  project_id: str
  label: str
  created_by: str
  tags: List[str] = Field(default_factory=list)


# Lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
  """Manage app lifecycle."""
  global storage, operator, scheduler, marketplace, lifecycle_manager, recommender, analytics

  # Startup
  logger.info("Starting MemCube service...")

  # Initialize storage
  storage = SupabaseMemCubeStorage(SUPABASE_URL, SUPABASE_KEY, BLOB_STORAGE_URL)

  # Initialize components
  operator = MemoryOperator(storage)
  selector = MemorySelector(storage)
  scheduler = MemoryScheduler(storage, selector)
  marketplace = MarketplaceService(storage, operator, MARKETPLACE_API)
  lifecycle_manager = MemoryLifecycleManager(storage)
  recommender = RecommendationEngine(storage)
  analytics = AnalyticsEngine(storage)

  # Start scheduler
  await scheduler.start()
  await recommender.start()
  await analytics.start()

  logger.info("MemCube service started successfully")

  yield

  # Shutdown
  logger.info("Shutting down MemCube service...")

  if scheduler:
    await scheduler.stop()
  if recommender:
    await recommender.stop()
  if analytics:
    await analytics.stop()

  logger.info("MemCube service stopped")


# Create FastAPI app
app = FastAPI(
    title="MemCube Memory Service",
    description=(
        "Structured memory system for AI agents with marketplace integration"
    ),
    version="0.2.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
  """Health check endpoint."""
  return {
      "status": "healthy",
      "service": "memcube",
      "version": "0.2.0",
      "timestamp": datetime.utcnow().isoformat(),
  }


# Memory CRUD operations
@app.post("/memories", response_model=Dict[str, Any])
async def create_memory(request: MemoryCreateRequest):
  """Create a new memory."""
  try:
    if request.type == MemoryType.PLAINTEXT:
      memory = await operator.create_from_text(
          project_id=request.project_id,
          label=request.label,
          content=request.content,
          created_by=request.created_by,
          tags=request.tags,
      )
    else:
      raise HTTPException(400, "Only PLAINTEXT memories supported via API")

    # Set custom governance if provided
    if request.governance:
      # Update governance settings
      memory.header.governance.read_roles = request.governance.get(
          "read_roles", ["MEMBER"]
      )
      memory.header.governance.write_roles = request.governance.get(
          "write_roles", ["AGENT"]
      )

    # Set priority
    memory.header.priority = request.priority

    # Store memory
    memory_id = await storage.store_memory(memory)

    return {
        "id": memory_id,
        "label": memory.label,
        "type": memory.type.value,
        "created_at": memory.header.created_at.isoformat(),
    }

  except Exception as e:
    logger.error(f"Failed to create memory: {e}")
    raise HTTPException(500, str(e))


@app.get("/memories/{memory_id}")
async def get_memory(memory_id: str, role: str = Query("MEMBER")):
  """Get a specific memory."""
  memory = await storage.get_memory(memory_id)
  if not memory:
    raise HTTPException(404, f"Memory {memory_id} not found")

  if memory.header.governance.pii_tagged and role not in memory.header.governance.read_roles:
    raise HTTPException(403, "Forbidden")

  # Update usage stats
  await storage.update_memory_usage(memory_id)

  return {
      "id": memory.id,
      "label": memory.label,
      "type": memory.type.value,
      "content": memory.to_prompt_text(),
      "metadata": {
          "version": memory.header.version,
          "created_by": memory.header.created_by,
          "created_at": memory.header.created_at.isoformat(),
          "usage_hits": memory.header.usage_hits,
          "priority": memory.header.priority.value,
      },
  }


@app.put("/memories/{memory_id}")
async def update_memory(memory_id: str, request: MemoryUpdateRequest):
  """Update memory content (creates new version)."""
  updated = await operator.update_memory_content(
      memory_id=memory_id,
      new_content=request.content,
      updated_by=request.updated_by,
  )

  if not updated:
    raise HTTPException(404, f"Memory {memory_id} not found")

  return {
      "id": updated.id,
      "version": updated.header.version,
      "updated_at": updated.header.created_at.isoformat(),
  }


@app.delete("/memories/{memory_id}")
async def archive_memory(memory_id: str):
  """Archive a memory."""
  success = await storage.archive_memory(memory_id)
  if not success:
    raise HTTPException(404, f"Memory {memory_id} not found")

  return {"status": "archived", "memory_id": memory_id}


# Memory querying
@app.post("/memories/query")
async def query_memories(request: MemoryQueryRequest, role: str = Query("MEMBER")):
  """Query memories based on criteria."""
  query = MemoryQuery(
      project_id=request.project_id,
      tags=request.tags,
      type_filter=request.type_filter,
      priority_filter=request.priority_filter,
      limit=request.top_k,
      similarity_threshold=request.similarity_threshold,
      query_text=request.query_text,
  )
  memories = await storage.query_memories(query)
  if role not in {"ADMIN"}:
    memories = [
        m
        for m in memories
        if not m.header.governance.pii_tagged
        or role in m.header.governance.read_roles
    ]

  return {
      "memories": [
          {
              "id": m.id,
              "label": m.label,
              "type": m.type.value,
              "priority": m.header.priority.value,
              "usage_hits": m.header.usage_hits,
              "preview": (
                  m.to_prompt_text()[:200] + "..."
                  if len(m.to_prompt_text()) > 200
                  else m.to_prompt_text()
              ),
          }
          for m in memories
      ],
      "count": len(memories),
  }


# Memory scheduling for agents
@app.post("/memories/schedule")
async def schedule_memories(request: MemoryScheduleRequest):
  """Schedule memories for an agent."""
  memories = await scheduler.schedule_request(request)

  # Format for agent consumption
  formatted = []
  total_tokens = 0

  for memory in memories:
    formatted.append({
        "id": memory.id,
        "label": memory.label,
        "content": memory.to_prompt_text(),
        "tokens": memory.payload.token_count or 100,
    })
    total_tokens += memory.payload.token_count or 100

  return {
      "agent_id": request.agent_id,
      "memories": formatted,
      "total_tokens": total_tokens,
      "count": len(memories),
  }


# Recommendations
@app.get("/memories/recommendations")
async def get_recommendations_endpoint(
    project_id: str = Query(...), limit: int = Query(10)
):
  """Get recommended memories for a project."""
  if not recommender:
    raise HTTPException(503, "Recommendation engine not initialized")
  recs = recommender.get_recommendations(project_id, limit)
  return {"project_id": project_id, "recommendations": recs, "count": len(recs)}


# Analytics
@app.get("/analytics/usage")
async def get_usage_analytics(
    project_id: str = Query(...), period: str = Query("7d")
):
  """Return aggregated usage analytics for a project."""
  if not analytics:
    raise HTTPException(503, "Analytics engine not initialized")
  metrics = await analytics.get_usage(project_id, period)
  return metrics


# Task-memory linking
@app.post("/memories/{memory_id}/link")
async def link_memory_to_task(
    memory_id: str, task_id: str = Body(...), role: str = Body("READ")
):
  """Link a memory to a task."""
  success = await storage.link_memory_to_task(memory_id, task_id, role)
  if not success:
    raise HTTPException(400, "Failed to link memory to task")

  return {"status": "linked", "memory_id": memory_id, "task_id": task_id}


@app.get("/tasks/{task_id}/memories")
async def get_task_memories(task_id: str):
  """Get memories linked to a task."""
  memories = await storage.get_memories_for_task(task_id)

  return {
      "task_id": task_id,
      "memories": [
          {
              "id": m.id,
              "label": m.label,
              "type": m.type.value,
              "content": m.to_prompt_text(),
          }
          for m in memories
      ],
      "count": len(memories),
  }


# Memory chains
@app.post("/chains", response_model=Dict[str, Any])
async def create_chain(request: ChainCreateRequest):
  chain_id = await storage.create_chain(
      project_id=request.project_id,
      label=request.label,
      created_by=request.created_by,
      tags=request.tags,
  )
  return {"id": chain_id, "label": request.label}


@app.post("/chains/{chain_id}/memories")
async def add_memory_to_chain(chain_id: str, memory_id: str = Body(...)):
  success = await storage.append_to_chain(chain_id, memory_id)
  if not success:
    raise HTTPException(400, "Failed to append memory to chain")
  return {"status": "added", "chain_id": chain_id, "memory_id": memory_id}


@app.delete("/chains/{chain_id}/memories/{memory_id}")
async def remove_memory_from_chain(chain_id: str, memory_id: str):
  success = await storage.remove_from_chain(chain_id, memory_id)
  if not success:
    raise HTTPException(400, "Failed to remove memory from chain")
  return {"status": "removed", "chain_id": chain_id, "memory_id": memory_id}


@app.get("/chains/{chain_id}")
async def get_chain(chain_id: str):
  memories = await storage.get_chain(chain_id)
  return {
      "chain_id": chain_id,
      "memories": [
          {
              "id": m.id,
              "label": m.label,
              "type": m.type.value,
              "content": m.to_prompt_text(),
          }
          for m in memories
      ],
      "count": len(memories),
  }


# Insight management
@app.post("/insights")
async def create_insight(
    project_id: str = Query(...),
    created_by: str = Query(...),
    request: InsightCreateRequest = Body(...),
):
  """Create an insight and convert to memory."""
  # Create insight card
  insight = InsightCard(
      insight=request.insight,
      evidence_refs=request.evidence_refs,
      tags=request.tags,
      sentiment=request.sentiment,
  )

  # Convert to memory
  memory = await operator.create_from_insight(
      project_id=project_id, insight_card=insight, created_by=created_by
  )

  return {
      "insight_id": insight.id,
      "memory_id": memory.id,
      "created_at": datetime.utcnow().isoformat(),
  }


# Marketplace operations
@app.post("/marketplace/packs")
async def create_memory_pack(
    author_id: str = Query(...),
    project_id: str = Query(...),
    request: PackCreateRequest = Body(...),
):
  """Create and publish a memory pack."""
  try:
    listing_id = await marketplace.create_and_publish_pack(
        author_id=author_id, project_id=project_id, pack_config=request.dict()
    )

    return {
        "listing_id": listing_id,
        "status": "published",
        "title": request.title,
    }

  except Exception as e:
    logger.error(f"Failed to create pack: {e}")
    raise HTTPException(500, str(e))


@app.get("/marketplace/search")
async def search_marketplace(
    query: str = Query(...), max_price_cents: Optional[int] = Query(None)
):
  """Search marketplace for memory packs."""
  packs = await marketplace.importer.search_packs(query, max_price_cents)
  return {"packs": packs, "count": len(packs)}


@app.post("/marketplace/import/{pack_id}")
async def import_memory_pack(
    pack_id: str, project_id: str = Query(...), buyer_id: str = Query(...)
):
  """Import a memory pack into project."""
  try:
    memory_ids = await marketplace.importer.import_pack(
        pack_id=pack_id, project_id=project_id, buyer_id=buyer_id
    )

    return {
        "pack_id": pack_id,
        "imported_memories": memory_ids,
        "count": len(memory_ids),
    }

  except Exception as e:
    logger.error(f"Failed to import pack: {e}")
    raise HTTPException(500, str(e))


# Memory synthesis
@app.post("/memories/synthesize")
async def synthesize_memories(
    project_id: str = Query(...),
    created_by: str = Query(...),
    memory_ids: List[str] = Body(...),
    prompt: str = Body(...),
):
  """Synthesize multiple memories into a new one."""
  # Get source memories
  source_memories = []
  for mid in memory_ids:
    memory = await storage.get_memory(mid)
    if memory:
      source_memories.append(memory)

  if not source_memories:
    raise HTTPException(400, "No valid source memories found")

  # Synthesize
  synthesized = await operator.synthesize_memories(
      project_id=project_id,
      source_memories=source_memories,
      synthesis_prompt=prompt,
      created_by=created_by,
  )

  return {
      "id": synthesized.id,
      "label": synthesized.label,
      "source_count": len(source_memories),
      "content_preview": synthesized.to_prompt_text()[:500],
  }


# Admin operations
@app.post("/admin/lifecycle")
async def run_lifecycle_tasks():
  """Run memory lifecycle management tasks."""
  if not lifecycle_manager:
    raise HTTPException(503, "Lifecycle manager not initialized")

  await lifecycle_manager.run_lifecycle_tasks()
  return {"status": "completed", "timestamp": datetime.utcnow().isoformat()}


@app.post("/admin/prune/{project_id}")
async def prune_cold_memories(
    project_id: str, keep_count: int = Query(100, ge=10, le=1000)
):
  """Prune cold memories for a project."""
  archived = await operator.prune_cold_memories(project_id, keep_count)
  return {
      "project_id": project_id,
      "archived_count": archived,
      "keep_count": keep_count,
  }


@app.get("/admin/audit/{project_id}")
async def audit_project(project_id: str, role: str = Query("ADMIN")):
  """List PII-tagged memories and access logs."""
  if role != "ADMIN":
    raise HTTPException(403, "Forbidden")
  pii_mems = await storage.list_pii_memories(project_id)
  logs = await storage.get_access_logs(project_id)
  return {
      "pii_memories": [m.id for m in pii_mems],
      "access_logs": logs,
  }


# Main entry point
if __name__ == "__main__":
  uvicorn.run(
      "memcube_system.service:app", host="0.0.0.0", port=8002, reload=True
  )
