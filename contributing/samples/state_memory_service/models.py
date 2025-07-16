"""Data models for State Memory Service."""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class StateVersion(BaseModel):
    """Represents a versioned state snapshot."""
    tenant_id: str
    fsa_id: str
    version: int
    state: Dict[str, Any]
    lineage_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StateDelta(BaseModel):
    """Represents a state change delta."""
    tenant: str
    fsa_id: str
    actor: str
    delta: Dict[str, Any]
    lineage_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StateUpdateResponse(BaseModel):
    """Response for state update operations."""
    success: bool
    version: int
    message: Optional[str] = None
    conflicts: Optional[Dict[str, Any]] = None