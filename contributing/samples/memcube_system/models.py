"""Core data models for MemCube memory system."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union
import uuid

from pydantic import BaseModel
from pydantic import Field
from pydantic import validator


class MemoryType(str, Enum):
  """Types of memory cubes matching MemOS taxonomy."""

  PLAINTEXT = "PLAINTEXT"  # Markdown or JSON ≤ 64KB
  ACTIVATION = "ACTIVATION"  # Base64-encoded KV cache ≤ 256KB
  PARAMETER = "PARAMETER"  # LoRA delta patch (compressed)


class MemoryLifecycle(str, Enum):
  """Lifecycle states for memory cubes."""

  NEW = "NEW"
  ACTIVE = "ACTIVE"
  STALE = "STALE"
  ARCHIVED = "ARCHIVED"
  EXPIRED = "EXPIRED"


class MemoryPriority(str, Enum):
  """Priority levels for memory scheduling."""

  HOT = "hot"
  WARM = "warm"
  COLD = "cold"


class StorageMode(str, Enum):
  """Storage modes for memory payloads."""

  INLINE = "inline"
  COMPRESSED = "compressed"
  COLD = "cold"


@dataclass
class MemoryGovernance:
  """Governance settings for memory access and lifecycle."""

  read_roles: List[str] = Field(default_factory=lambda: ["MEMBER"])
  write_roles: List[str] = Field(default_factory=lambda: ["AGENT"])
  ttl_days: int = 365
  shareable: bool = True
  license: Optional[str] = None  # SPDX identifier
  pii_tagged: bool = False


class MemCubeHeader(BaseModel):
  """Header metadata for a memory cube."""

  id: str = Field(default_factory=lambda: str(uuid.uuid4()))
  project_id: str
  label: str
  type: MemoryType
  version: int = 1
  origin: Optional[str] = None  # e.g., "agent_run:xyz"
  created_by: str  # agent_id or member_id
  created_at: datetime = Field(default_factory=datetime.utcnow)
  embedding_sig: Optional[List[float]] = None  # Vector embedding
  governance: MemoryGovernance = Field(default_factory=MemoryGovernance)

  # v0.2 extensions
  usage_hits: int = 0
  last_used: Optional[datetime] = None
  priority: MemoryPriority = MemoryPriority.WARM
  storage_mode: StorageMode = StorageMode.INLINE
  provenance_id: Optional[str] = None  # First ancestor
  kv_hint: bool = False  # True if should be injected via KV cache
  watermark: bool = False

  class Config:
    json_encoders = {datetime: lambda v: v.isoformat()}


class MemCubePayload(BaseModel):
  """Payload content for a memory cube."""

  type: MemoryType
  content: Union[str, bytes, Dict[str, Any]]
  token_count: Optional[int] = None
  size_bytes: int = 0

  @validator("content")
  def validate_content_size(cls, v, values):
    """Validate content size based on type."""
    mem_type = values.get("type")
    if mem_type == MemoryType.PLAINTEXT:
      if isinstance(v, str) and len(v.encode()) > 64 * 1024:
        raise ValueError("PLAINTEXT content exceeds 64KB limit")
    elif mem_type == MemoryType.ACTIVATION:
      if isinstance(v, (str, bytes)) and len(v) > 256 * 1024:
        raise ValueError("ACTIVATION content exceeds 256KB limit")
    return v

  def get_size(self) -> int:
    """Calculate payload size in bytes."""
    if isinstance(self.content, str):
      return len(self.content.encode())
    elif isinstance(self.content, bytes):
      return len(self.content)
    else:
      return len(str(self.content).encode())


class MemCube(BaseModel):
  """Complete memory cube with header and payload."""

  header: MemCubeHeader
  payload: MemCubePayload

  @property
  def id(self) -> str:
    return self.header.id

  @property
  def label(self) -> str:
    return self.header.label

  @property
  def type(self) -> MemoryType:
    return self.header.type

  def to_prompt_text(self) -> str:
    """Convert to text format for agent prompts."""
    if self.type == MemoryType.PLAINTEXT:
      return f"<<MEM:{self.label}>>\n{self.payload.content}\n<<ENDMEM>>"
    else:
      return f"<<MEM:{self.label}>>Binary content ({self.type.value})<<ENDMEM>>"


class MemoryVersion(BaseModel):
  """Version information for a memory cube."""

  id: str = Field(default_factory=lambda: str(uuid.uuid4()))
  memory_id: str
  version: int
  blob_path: Optional[str] = None
  vector_sig: Optional[List[float]] = None
  token_count: int = 0
  created_by: str
  created_at: datetime = Field(default_factory=datetime.utcnow)
  kv_hint: bool = False
  provenance_id: Optional[str] = None


class MemoryEvent(BaseModel):
  """Audit event for memory state transitions."""

  id: Optional[int] = None
  memory_id: str
  event: str  # CREATED, PROMOTED, ARCHIVED, EXPIRED, etc.
  actor: str  # agent or member ID
  ts: datetime = Field(default_factory=datetime.utcnow)
  meta: Dict[str, Any] = Field(default_factory=dict)


class MemoryLink(BaseModel):
  """Link between tasks and memories."""

  task_id: str
  memory_id: str
  role: str = "READ"  # READ or WRITE


class MemoryPack(BaseModel):
  """Collection of memory cubes for distribution."""

  id: str = Field(default_factory=lambda: str(uuid.uuid4()))
  author_id: str
  title: str
  description: str
  cover_img: Optional[str] = None
  price_cents: int = 0
  royalty_pct: int = Field(0, ge=0, le=100)
  watermark: bool = True
  created_at: datetime = Field(default_factory=datetime.utcnow)
  memory_ids: List[str] = Field(default_factory=list)

  @property
  def is_free(self) -> bool:
    return self.price_cents == 0


class InsightCard(BaseModel):
  """User insight card for crowd-sourced feedback."""

  id: str = Field(default_factory=lambda: str(uuid.uuid4()))
  insight: str
  evidence_refs: List[str] = Field(default_factory=list)
  support_count: int = 0
  sentiment: float = Field(0.0, ge=-1.0, le=1.0)
  priority: MemoryPriority = MemoryPriority.WARM
  tags: List[str] = Field(default_factory=list)
  created_at: datetime = Field(default_factory=datetime.utcnow)

  def to_memcube(self, project_id: str, created_by: str) -> MemCube:
    """Convert insight card to a memory cube."""
    header = MemCubeHeader(
        project_id=project_id,
        label=f"insight::{self.id[:8]}",
        type=MemoryType.PLAINTEXT,
        created_by=created_by,
        priority=self.priority,
        governance=MemoryGovernance(
            read_roles=["MEMBER", "AGENT"], write_roles=["SYSTEM"]
        ),
    )

    content = {
        "insight": self.insight,
        "support_count": self.support_count,
        "sentiment": self.sentiment,
        "evidence_refs": self.evidence_refs,
        "tags": self.tags,
    }

    payload = MemCubePayload(
        type=MemoryType.PLAINTEXT,
        content=str(content),
        token_count=len(self.insight.split()),  # Simple approximation
    )

    return MemCube(header=header, payload=payload)


class MemoryQuery(BaseModel):
  """Query parameters for memory search."""

  project_id: str
  tags: List[str] = Field(default_factory=list)
  type_filter: Optional[MemoryType] = None
  query_text: Optional[str] = None
  embedding: Optional[List[float]] = None
  similarity_threshold: float = 0.78
  limit: int = 10
  include_insights: bool = False
  priority_filter: Optional[MemoryPriority] = None


class MemoryScheduleRequest(BaseModel):
  """Request from agent for memory scheduling."""

  agent_id: str
  task_id: str
  project_id: str
  need_tags: List[str] = Field(default_factory=list)
  token_budget: int = 4000
  prefer_hot: bool = True
  include_insights: bool = True
  query_text: Optional[str] = None
  top_k: int = 10


@dataclass
class MemoryChain:
  """Ordered chain of memories."""

  project_id: str
  label: str
  created_by: str
  id: str = Field(default_factory=lambda: str(uuid.uuid4()))
  created_at: datetime = Field(default_factory=datetime.utcnow)
  tags: List[str] = Field(default_factory=list)


@dataclass
class MemoryChainLink:
  """Link between a chain and a memory."""

  chain_id: str
  memory_id: str
  position: int
  added_at: datetime = Field(default_factory=datetime.utcnow)
