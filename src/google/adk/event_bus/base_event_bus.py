# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class EventPriority(str, Enum):
  """Priority levels for events."""
  
  LOW = "low"
  NORMAL = "normal"
  HIGH = "high"
  CRITICAL = "critical"


class EventMessage(BaseModel):
  """Message sent through the event bus."""
  
  id: str = Field(default_factory=lambda: str(uuid4()), description="Unique event ID")
  topic: str = Field(description="Topic/channel for the event")
  event_type: str = Field(description="Type of event")
  source: str = Field(description="Source agent or component")
  timestamp: datetime = Field(
      default_factory=datetime.now, description="Event timestamp"
  )
  priority: EventPriority = Field(
      default=EventPriority.NORMAL, description="Event priority"
  )
  payload: Dict[str, Any] = Field(
      default_factory=dict, description="Event payload data"
  )
  metadata: Dict[str, Any] = Field(
      default_factory=dict, description="Additional metadata"
  )
  correlation_id: Optional[str] = Field(
      default=None, description="ID for correlating related events"
  )
  reply_to: Optional[str] = Field(
      default=None, description="Topic for replies if applicable"
  )
  
  def to_dict(self) -> Dict[str, Any]:
    """Convert to dictionary for serialization."""
    data = self.model_dump()
    data["timestamp"] = self.timestamp.isoformat()
    return data
  
  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> EventMessage:
    """Create from dictionary."""
    if isinstance(data.get("timestamp"), str):
      data["timestamp"] = datetime.fromisoformat(data["timestamp"])
    return cls(**data)


class EventSubscription(BaseModel):
  """Subscription to event topics."""
  
  id: str = Field(
      default_factory=lambda: str(uuid4()), description="Subscription ID"
  )
  subscriber_id: str = Field(description="ID of the subscriber")
  topics: List[str] = Field(description="Topics to subscribe to")
  event_types: Optional[List[str]] = Field(
      default=None, description="Filter by event types"
  )
  priority_filter: Optional[List[EventPriority]] = Field(
      default=None, description="Filter by priority levels"
  )
  handler: Optional[Callable[[EventMessage], None]] = Field(
      default=None, description="Handler function for events", exclude=True
  )
  
  class Config:
    arbitrary_types_allowed = True


class BaseEventBus(ABC):
  """Abstract base class for event bus implementations."""
  
  @abstractmethod
  async def publish(
      self,
      topic: str,
      event_type: str,
      source: str,
      payload: Dict[str, Any],
      priority: EventPriority = EventPriority.NORMAL,
      correlation_id: Optional[str] = None,
      reply_to: Optional[str] = None,
  ) -> EventMessage:
    """Publish an event to the bus.
    
    Args:
        topic: Topic/channel for the event
        event_type: Type of event
        source: Source agent or component
        payload: Event data
        priority: Event priority
        correlation_id: ID for correlating related events
        reply_to: Topic for replies
        
    Returns:
        The published EventMessage
    """
    pass
  
  @abstractmethod
  async def subscribe(
      self,
      subscriber_id: str,
      topics: List[str],
      handler: Callable[[EventMessage], None],
      event_types: Optional[List[str]] = None,
      priority_filter: Optional[List[EventPriority]] = None,
  ) -> EventSubscription:
    """Subscribe to events.
    
    Args:
        subscriber_id: ID of the subscriber
        topics: Topics to subscribe to
        handler: Function to handle received events
        event_types: Optional filter by event types
        priority_filter: Optional filter by priority
        
    Returns:
        EventSubscription object
    """
    pass
  
  @abstractmethod
  async def unsubscribe(self, subscription_id: str) -> bool:
    """Unsubscribe from events.
    
    Args:
        subscription_id: ID of the subscription to remove
        
    Returns:
        True if unsubscribed successfully
    """
    pass
  
  @abstractmethod
  async def get_event_history(
      self,
      topic: Optional[str] = None,
      event_type: Optional[str] = None,
      source: Optional[str] = None,
      start_time: Optional[datetime] = None,
      end_time: Optional[datetime] = None,
      limit: int = 100,
  ) -> List[EventMessage]:
    """Get historical events.
    
    Args:
        topic: Filter by topic
        event_type: Filter by event type
        source: Filter by source
        start_time: Filter by start time
        end_time: Filter by end time
        limit: Maximum number of events to return
        
    Returns:
        List of matching events
    """
    pass
  
  @abstractmethod
  async def wait_for_event(
      self,
      topic: str,
      event_type: Optional[str] = None,
      correlation_id: Optional[str] = None,
      timeout: Optional[float] = None,
  ) -> Optional[EventMessage]:
    """Wait for a specific event.
    
    Args:
        topic: Topic to monitor
        event_type: Optional event type filter
        correlation_id: Optional correlation ID filter
        timeout: Timeout in seconds
        
    Returns:
        The matching event or None if timeout
    """
    pass
  
  async def request_reply(
      self,
      topic: str,
      event_type: str,
      source: str,
      payload: Dict[str, Any],
      reply_timeout: float = 30.0,
  ) -> Optional[EventMessage]:
    """Send an event and wait for a reply.
    
    Args:
        topic: Topic to publish to
        event_type: Type of event
        source: Source of the request
        payload: Request payload
        reply_timeout: Timeout for reply in seconds
        
    Returns:
        Reply event or None if timeout
    """
    # Generate correlation ID and reply topic
    correlation_id = str(uuid4())
    reply_topic = f"reply.{source}.{correlation_id}"
    
    # Publish request
    await self.publish(
        topic=topic,
        event_type=event_type,
        source=source,
        payload=payload,
        correlation_id=correlation_id,
        reply_to=reply_topic,
    )
    
    # Wait for reply
    return await self.wait_for_event(
        topic=reply_topic,
        correlation_id=correlation_id,
        timeout=reply_timeout,
    )