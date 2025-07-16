"""
Type definitions for ADK Supabase SDK
"""

from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field


# Enums

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class AgentStatus(str, Enum):
    ONLINE = "ONLINE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"


class MemoryType(str, Enum):
    PLAINTEXT = "PLAINTEXT"
    JSON = "JSON"
    MARKDOWN = "MARKDOWN"
    CODE = "CODE"
    BINARY = "BINARY"


class AMLLevel(str, Enum):
    AML0 = "AML0"
    AML1 = "AML1"
    AML2 = "AML2"
    AML3 = "AML3"
    AML4 = "AML4"


class StorageMode(str, Enum):
    INLINE = "INLINE"
    COMPRESSED = "COMPRESSED"
    COLD = "COLD"


# Core Types

@dataclass
class Project:
    id: str
    name: str
    tenant_id: str
    description: Optional[str] = None
    budget_total: float = 0
    budget_spent: float = 0
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    archived: bool = False


@dataclass
class FSAState:
    state: Dict[str, Any]
    version: int = 0
    project_id: str = ""
    fsa_id: str = ""
    lineage_version: int = 0
    actor: Optional[str] = None
    lineage_id: Optional[str] = None
    created_at: Optional[datetime] = None
    deltas: Optional[List[Dict[str, Any]]] = None


@dataclass
class FSADelta:
    op: str  # 'set', 'inc', 'push', 'unset'
    path: List[str]
    value: Optional[Any] = None


@dataclass
class FSASliceResult:
    project_id: str
    fsa_id: str
    version: int
    slice: Dict[str, Any]
    summary: str
    pattern: str
    cached: bool = False


@dataclass
class Memory:
    id: str
    label: str
    content: str
    type: MemoryType = MemoryType.PLAINTEXT
    project_id: Optional[str] = None
    embedding: Optional[List[float]] = None
    metadata: Optional[Dict[str, Any]] = None
    pack_id: Optional[str] = None
    storage_mode: StorageMode = StorageMode.INLINE
    content_size: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class MemorySearchResult:
    memory: Memory
    similarity: float
    highlights: Optional[List[str]] = None


@dataclass
class Task:
    id: str
    project_id: str
    task_id: str
    type: str
    title: str
    status: TaskStatus = TaskStatus.PENDING
    description: Optional[str] = None
    priority: int = 0
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    depends_on: Optional[List[str]] = None
    blocks: Optional[List[str]] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class Agent:
    id: str
    agent_id: str
    name: str
    type: str
    status: AgentStatus = AgentStatus.OFFLINE
    capabilities: List[str] = field(default_factory=list)
    aml_level: AMLLevel = AMLLevel.AML1
    max_tokens_per_task: int = 100000
    last_heartbeat: Optional[datetime] = None
    current_task_id: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_completion_time_hours: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskProgress:
    id: str
    task_id: str
    agent_id: str
    progress: int
    message: Optional[str] = None
    data: Optional[Any] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Tool:
    id: str
    name: str
    type: str
    description: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_aml_level: AMLLevel = AMLLevel.AML1
    requires_approval: bool = False
    enabled: bool = True


@dataclass
class ToolExecution:
    tool_name: str
    parameters: Dict[str, Any]
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    requires_approval: bool = False


@dataclass
class Event:
    id: str
    type: str
    source: str
    data: Any
    project_id: Optional[str] = None
    target_agent: Optional[str] = None
    processed: bool = False
    processed_at: Optional[datetime] = None
    processed_by: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class HealthCheck:
    status: str  # 'healthy', 'degraded', 'unhealthy'
    checks: Dict[str, Dict[str, Any]]
    timestamp: datetime
    error: Optional[str] = None


# Error Types

class ADKError(Exception):
    """Base exception for ADK SDK"""
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.details = details


class ProjectNotFoundError(ADKError):
    """Raised when a project is not found"""
    def __init__(self, project_id: str):
        super().__init__(
            f"Project {project_id} not found",
            code="PROJECT_NOT_FOUND",
            details={"project_id": project_id}
        )


class TaskNotFoundError(ADKError):
    """Raised when a task is not found"""
    def __init__(self, task_id: str):
        super().__init__(
            f"Task {task_id} not found",
            code="TASK_NOT_FOUND",
            details={"task_id": task_id}
        )


class AgentNotAuthorizedError(ADKError):
    """Raised when an agent is not authorized for a resource"""
    def __init__(self, agent_id: str, resource: str):
        super().__init__(
            f"Agent {agent_id} not authorized for {resource}",
            code="AGENT_NOT_AUTHORIZED",
            details={"agent_id": agent_id, "resource": resource}
        )


class MemoryNotFoundError(ADKError):
    """Raised when a memory is not found"""
    def __init__(self, memory_id: str):
        super().__init__(
            f"Memory {memory_id} not found",
            code="MEMORY_NOT_FOUND",
            details={"memory_id": memory_id}
        )


# Utility Types

AsyncCallback = Callable[[Any], Union[None, Awaitable[None]]]

@dataclass
class PaginationParams:
    limit: int = 10
    offset: int = 0
    order_by: Optional[str] = None
    order: str = "asc"  # 'asc' or 'desc'


@dataclass
class BatchOperation:
    operation: str  # 'create', 'update', 'delete'
    data: Any