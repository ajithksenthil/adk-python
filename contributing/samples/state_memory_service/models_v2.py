"""Enhanced data models for comprehensive FSA State Memory."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Task lifecycle states."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VOTING = "VOTING"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Task(BaseModel):
    """Individual task in the task graph."""
    task_id: str
    status: TaskStatus
    assigned_team: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    
class Comment(BaseModel):
    """Discussion thread comment."""
    comment_id: str
    author: str
    ts: datetime = Field(default_factory=datetime.utcnow)
    lineage_id: str
    state_ver: int
    body_md: str
    reactions: Dict[str, int] = Field(default_factory=dict)
    is_blocker: bool = False
    

class ProjectState(BaseModel):
    """Comprehensive project-wide FSA state."""
    
    # What are we doing?
    tasks: Dict[str, Task] = Field(default_factory=dict)
    active_state: Dict[str, Any] = Field(default_factory=dict)
    
    # What do we have?
    artefacts: Dict[str, Any] = Field(default_factory=dict)
    resources: Dict[str, Any] = Field(default_factory=dict)
    
    # How are we doing?
    metrics: Dict[str, Any] = Field(default_factory=dict)
    
    # What rules apply?
    policy_caps: Dict[str, Any] = Field(default_factory=dict)
    aml_levels: Dict[str, int] = Field(default_factory=dict)
    vote_rules: Dict[str, str] = Field(default_factory=dict)
    
    # When do things happen?
    timers: Dict[str, datetime] = Field(default_factory=dict)
    
    # Who is available?
    agents_online: Dict[str, datetime] = Field(default_factory=dict)
    
    # Versioning
    lineage_version: int = 0
    
    # Metadata
    _metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        
    def to_summary(self, max_chars: int = 2000) -> str:
        """Generate a concise summary for LLM context."""
        summary_parts = []
        
        # Active state
        if self.active_state:
            summary_parts.append(f"=== Current State ===")
            summary_parts.append(f"Sprint: {self.active_state.get('current_sprint', 'N/A')}")
            summary_parts.append(f"Milestone: {self.active_state.get('milestone_id', 'N/A')}")
        
        # Tasks overview
        task_counts = {}
        for task in self.tasks.values():
            status = task.status if isinstance(task, Task) else task.get('status', 'UNKNOWN')
            task_counts[status] = task_counts.get(status, 0) + 1
        
        if task_counts:
            summary_parts.append(f"\n=== Tasks ===")
            for status, count in task_counts.items():
                summary_parts.append(f"{status}: {count}")
        
        # Resources
        if self.resources:
            summary_parts.append(f"\n=== Resources ===")
            if 'cash_balance_usd' in self.resources:
                summary_parts.append(f"Cash: ${self.resources['cash_balance_usd']:,.2f}")
            if 'inventory' in self.resources:
                summary_parts.append(f"Inventory: {len(self.resources['inventory'])} items")
        
        # Metrics
        if self.metrics:
            summary_parts.append(f"\n=== Key Metrics ===")
            for key, value in list(self.metrics.items())[:5]:  # Top 5 metrics
                if isinstance(value, (int, float)):
                    summary_parts.append(f"{key}: {value}")
        
        # Policy caps
        if self.policy_caps:
            summary_parts.append(f"\n=== Policy Limits ===")
            for key, value in list(self.policy_caps.items())[:3]:
                summary_parts.append(f"{key}: {value}")
        
        # AML levels
        if self.aml_levels:
            summary_parts.append(f"\n=== Autonomy Levels ===")
            for pillar, level in self.aml_levels.items():
                summary_parts.append(f"{pillar}: AML {level}")
        
        # Active agents
        active_agents = [name for name, heartbeat in self.agents_online.items() 
                        if (datetime.utcnow() - heartbeat).total_seconds() < 300]
        if active_agents:
            summary_parts.append(f"\n=== Active Agents ({len(active_agents)}) ===")
            summary_parts.extend(active_agents[:5])  # Show first 5
        
        summary = "\n".join(summary_parts)
        
        # Truncate if needed
        if len(summary) > max_chars:
            summary = summary[:max_chars-3] + "..."
            
        return summary


class CommentEvent(BaseModel):
    """Event for adding a comment to a task."""
    task_id: str
    comment: Comment
    event_type: str = "task.comment.created"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    

class StateTransition(BaseModel):
    """Represents a state transition with before/after versions."""
    from_version: int
    to_version: int
    delta: Dict[str, Any]
    actor: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    lineage_id: str
    policy_check_passed: bool = True
    violations: Optional[List[str]] = None