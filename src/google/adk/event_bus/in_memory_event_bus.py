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

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .base_event_bus import (
    BaseEventBus,
    EventMessage,
    EventPriority,
    EventSubscription,
)

logger = logging.getLogger(__name__)


class InMemoryEventBus(BaseEventBus):
  """In-memory event bus implementation for development and testing."""
  
  def __init__(self, max_history: int = 1000):
    """Initialize in-memory event bus.
    
    Args:
        max_history: Maximum number of events to keep in history
    """
    self.max_history = max_history
    self._event_history: List[EventMessage] = []
    self._subscriptions: Dict[str, EventSubscription] = {}
    self._topic_subscriptions: Dict[str, Set[str]] = defaultdict(set)
    self._waiting_futures: List[tuple] = []  # (future, filters)
  
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
    """Publish an event."""
    event = EventMessage(
        topic=topic,
        event_type=event_type,
        source=source,
        payload=payload,
        priority=priority,
        correlation_id=correlation_id,
        reply_to=reply_to,
    )
    
    # Add to history
    self._event_history.append(event)
    
    # Trim history if needed
    if len(self._event_history) > self.max_history:
      self._event_history = self._event_history[-self.max_history :]
    
    # Notify subscribers
    await self._notify_subscribers(event)
    
    # Check waiting futures
    await self._check_waiting_futures(event)
    
    logger.debug(f"Published event: {event.event_type} to {topic}")
    
    return event
  
  async def subscribe(
      self,
      subscriber_id: str,
      topics: List[str],
      handler: Callable[[EventMessage], None],
      event_types: Optional[List[str]] = None,
      priority_filter: Optional[List[EventPriority]] = None,
  ) -> EventSubscription:
    """Subscribe to events."""
    subscription = EventSubscription(
        subscriber_id=subscriber_id,
        topics=topics,
        event_types=event_types,
        priority_filter=priority_filter,
        handler=handler,
    )
    
    # Store subscription
    self._subscriptions[subscription.id] = subscription
    
    # Update topic index
    for topic in topics:
      self._topic_subscriptions[topic].add(subscription.id)
    
    logger.debug(
        f"Subscriber {subscriber_id} subscribed to: {', '.join(topics)}"
    )
    
    return subscription
  
  async def unsubscribe(self, subscription_id: str) -> bool:
    """Unsubscribe from events."""
    if subscription_id not in self._subscriptions:
      return False
    
    subscription = self._subscriptions[subscription_id]
    
    # Remove from topic index
    for topic in subscription.topics:
      self._topic_subscriptions[topic].discard(subscription_id)
      if not self._topic_subscriptions[topic]:
        del self._topic_subscriptions[topic]
    
    # Remove subscription
    del self._subscriptions[subscription_id]
    
    logger.debug(f"Unsubscribed: {subscription_id}")
    return True
  
  async def get_event_history(
      self,
      topic: Optional[str] = None,
      event_type: Optional[str] = None,
      source: Optional[str] = None,
      start_time: Optional[datetime] = None,
      end_time: Optional[datetime] = None,
      limit: int = 100,
  ) -> List[EventMessage]:
    """Get historical events."""
    filtered_events = []
    
    for event in reversed(self._event_history):
      # Apply filters
      if topic and event.topic != topic:
        continue
      if event_type and event.event_type != event_type:
        continue
      if source and event.source != source:
        continue
      if start_time and event.timestamp < start_time:
        continue
      if end_time and event.timestamp > end_time:
        continue
      
      filtered_events.append(event)
      
      if len(filtered_events) >= limit:
        break
    
    return filtered_events
  
  async def wait_for_event(
      self,
      topic: str,
      event_type: Optional[str] = None,
      correlation_id: Optional[str] = None,
      timeout: Optional[float] = None,
  ) -> Optional[EventMessage]:
    """Wait for a specific event."""
    # Check history first
    for event in reversed(self._event_history):
      if event.topic == topic:
        if event_type and event.event_type != event_type:
          continue
        if correlation_id and event.correlation_id != correlation_id:
          continue
        return event
    
    # Create future to wait on
    future = asyncio.Future()
    filters = {
        "topic": topic,
        "event_type": event_type,
        "correlation_id": correlation_id,
    }
    
    self._waiting_futures.append((future, filters))
    
    try:
      # Wait with timeout
      event = await asyncio.wait_for(future, timeout=timeout)
      return event
    except asyncio.TimeoutError:
      return None
    finally:
      # Clean up
      self._waiting_futures = [
          (f, filt)
          for f, filt in self._waiting_futures
          if f != future
      ]
  
  async def _notify_subscribers(self, event: EventMessage):
    """Notify all relevant subscribers of an event."""
    # Get subscription IDs for this topic
    subscription_ids = self._topic_subscriptions.get(event.topic, set())
    
    for sub_id in subscription_ids:
      subscription = self._subscriptions.get(sub_id)
      if not subscription or not subscription.handler:
        continue
      
      # Check filters
      if (
          subscription.event_types
          and event.event_type not in subscription.event_types
      ):
        continue
      
      if (
          subscription.priority_filter
          and event.priority not in subscription.priority_filter
      ):
        continue
      
      # Call handler
      try:
        if asyncio.iscoroutinefunction(subscription.handler):
          await subscription.handler(event)
        else:
          subscription.handler(event)
      except Exception as e:
        logger.error(
            f"Error in handler for {subscription.subscriber_id}: {e}"
        )
  
  async def _check_waiting_futures(self, event: EventMessage):
    """Check if any waiting futures match this event."""
    completed_futures = []
    
    for future, filters in self._waiting_futures:
      if future.done():
        completed_futures.append((future, filters))
        continue
      
      # Check filters
      if filters.get("topic") and event.topic != filters["topic"]:
        continue
      
      if (
          filters.get("event_type")
          and event.event_type != filters["event_type"]
      ):
        continue
      
      if (
          filters.get("correlation_id")
          and event.correlation_id != filters["correlation_id"]
      ):
        continue
      
      # Match found
      future.set_result(event)
      completed_futures.append((future, filters))
    
    # Remove completed futures
    for completed in completed_futures:
      if completed in self._waiting_futures:
        self._waiting_futures.remove(completed)
  
  def clear(self):
    """Clear all data (for testing)."""
    self._event_history.clear()
    self._subscriptions.clear()
    self._topic_subscriptions.clear()
    self._waiting_futures.clear()
  
  def get_metrics(self) -> Dict[str, Any]:
    """Get event bus metrics."""
    return {
        "total_events": len(self._event_history),
        "active_subscriptions": len(self._subscriptions),
        "monitored_topics": len(self._topic_subscriptions),
        "waiting_futures": len(self._waiting_futures),
        "topics": list(self._topic_subscriptions.keys()),
    }