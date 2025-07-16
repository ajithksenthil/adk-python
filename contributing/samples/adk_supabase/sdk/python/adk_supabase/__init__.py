"""
ADK Supabase SDK - Unified Python SDK for FSA and MemCube
"""

from .client import ADKClient, create_adk_client
from .types import (
    # Core types
    FSAState,
    FSADelta,
    Memory,
    Task,
    Agent,
    Project,
    
    # Status enums
    TaskStatus,
    AgentStatus,
    MemoryType,
    AMLLevel,
    
    # Errors
    ADKError,
    ProjectNotFoundError,
    TaskNotFoundError,
    AgentNotAuthorizedError,
    MemoryNotFoundError,
)

__version__ = "1.0.0"
__all__ = [
    "ADKClient",
    "create_adk_client",
    "FSAState",
    "FSADelta",
    "Memory",
    "Task",
    "Agent",
    "Project",
    "TaskStatus",
    "AgentStatus", 
    "MemoryType",
    "AMLLevel",
    "ADKError",
    "ProjectNotFoundError",
    "TaskNotFoundError",
    "AgentNotAuthorizedError",
    "MemoryNotFoundError",
]