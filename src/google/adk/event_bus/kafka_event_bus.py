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
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

from .base_event_bus import (
    BaseEventBus,
    EventMessage,
    EventPriority,
    EventSubscription,
)

logger = logging.getLogger(__name__)

# Note: In a real implementation, you would import and use actual Kafka libraries
# like aiokafka. This is a simplified implementation for demonstration.


class KafkaEventBus(BaseEventBus):
  """Kafka-based event bus implementation.
  
  This is a simplified implementation that demonstrates the pattern.
  In production, you would use actual Kafka client libraries like aiokafka.
  """
  
  def __init__(
      self,
      bootstrap_servers: str = "localhost:9092",
      client_id: str = "adk-event-bus",
      group_id: str = "adk-agents",
  ):
    """Initialize Kafka event bus.
    
    Args:
        bootstrap_servers: Kafka bootstrap servers
        client_id: Client ID for Kafka
        group_id: Consumer group ID
    """
    self.bootstrap_servers = bootstrap_servers
    self.client_id = client_id
    self.group_id = group_id
    
    # In production, initialize Kafka producer and consumer here
    self._producer = None  # Would be aiokafka.AIOKafkaProducer
    self._consumers: Dict[str, Any] = {}  # Topic -> Consumer mapping
    self._subscriptions: Dict[str, EventSubscription] = {}
    self._running = False
    self._consumer_tasks: List[asyncio.Task] = []
    
    # For demo purposes, we'll use in-memory storage
    self._event_store: List[EventMessage] = []
    self._topic_handlers: Dict[str, Set[EventSubscription]] = {}
  
  async def start(self):
    """Start the event bus."""
    if self._running:
      return
    
    self._running = True
    logger.info(f"Starting Kafka event bus: {self.bootstrap_servers}")
    
    # In production:
    # - Initialize Kafka producer
    # - Start consumer tasks
    # - Connect to Kafka cluster
  
  async def stop(self):
    """Stop the event bus."""
    self._running = False
    
    # Cancel consumer tasks
    for task in self._consumer_tasks:
      task.cancel()
    
    # Wait for tasks to complete
    if self._consumer_tasks:
      await asyncio.gather(*self._consumer_tasks, return_exceptions=True)
    
    # In production:
    # - Close Kafka connections
    # - Clean up resources
    
    logger.info("Kafka event bus stopped")
  
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
    """Publish an event to Kafka."""
    # Create event message
    event = EventMessage(
        topic=topic,
        event_type=event_type,
        source=source,
        payload=payload,
        priority=priority,
        correlation_id=correlation_id,
        reply_to=reply_to,
    )
    
    # In production, serialize and send to Kafka
    # await self._producer.send(topic, value=event.to_dict())
    
    # For demo, store in memory and notify handlers
    self._event_store.append(event)
    await self._notify_handlers(event)
    
    logger.info(
        f"Published event: {event.event_type} to {topic} "
        f"(priority: {priority.value})"
    )
    
    return event
  
  async def subscribe(
      self,
      subscriber_id: str,
      topics: List[str],
      handler: Callable[[EventMessage], None],
      event_types: Optional[List[str]] = None,
      priority_filter: Optional[List[EventPriority]] = None,
  ) -> EventSubscription:
    """Subscribe to Kafka topics."""
    subscription = EventSubscription(
        subscriber_id=subscriber_id,
        topics=topics,
        event_types=event_types,
        priority_filter=priority_filter,
        handler=handler,
    )
    
    # Store subscription
    self._subscriptions[subscription.id] = subscription
    
    # Register with topics
    for topic in topics:
      if topic not in self._topic_handlers:
        self._topic_handlers[topic] = set()
        # In production, create Kafka consumer for this topic
        await self._create_consumer(topic)
      
      self._topic_handlers[topic].add(subscription)
    
    logger.info(
        f"Subscriber {subscriber_id} subscribed to topics: {', '.join(topics)}"
    )
    
    return subscription
  
  async def unsubscribe(self, subscription_id: str) -> bool:
    """Unsubscribe from topics."""
    if subscription_id not in self._subscriptions:
      return False
    
    subscription = self._subscriptions[subscription_id]
    
    # Remove from topic handlers
    for topic in subscription.topics:
      if topic in self._topic_handlers:
        self._topic_handlers[topic].discard(subscription)
        
        # If no more subscribers, stop consumer
        if not self._topic_handlers[topic]:
          await self._stop_consumer(topic)
          del self._topic_handlers[topic]
    
    # Remove subscription
    del self._subscriptions[subscription_id]
    
    logger.info(f"Unsubscribed: {subscription_id}")
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
    """Get historical events from Kafka."""
    # In production, this would query Kafka or a separate event store
    
    # Filter events
    filtered_events = []
    for event in reversed(self._event_store):  # Most recent first
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
    # Create a future to wait on
    future = asyncio.Future()
    
    # Create temporary subscription
    async def event_handler(event: EventMessage):
      # Check if this is the event we're waiting for
      if event_type and event.event_type != event_type:
        return
      if correlation_id and event.correlation_id != correlation_id:
        return
      
      # Found the event
      if not future.done():
        future.set_result(event)
    
    # Subscribe
    subscription = await self.subscribe(
        subscriber_id=f"wait_{topic}_{correlation_id}",
        topics=[topic],
        handler=event_handler,
    )
    
    try:
      # Wait for event with timeout
      event = await asyncio.wait_for(future, timeout=timeout)
      return event
    except asyncio.TimeoutError:
      logger.debug(f"Timeout waiting for event on {topic}")
      return None
    finally:
      # Clean up subscription
      await self.unsubscribe(subscription.id)
  
  async def _create_consumer(self, topic: str):
    """Create a Kafka consumer for a topic."""
    # In production:
    # consumer = aiokafka.AIOKafkaConsumer(
    #     topic,
    #     bootstrap_servers=self.bootstrap_servers,
    #     group_id=self.group_id,
    #     client_id=f"{self.client_id}-{topic}",
    # )
    # await consumer.start()
    # self._consumers[topic] = consumer
    #
    # # Start consumer task
    # task = asyncio.create_task(self._consume_messages(topic, consumer))
    # self._consumer_tasks.append(task)
    
    logger.info(f"Created consumer for topic: {topic}")
  
  async def _stop_consumer(self, topic: str):
    """Stop a Kafka consumer."""
    # In production:
    # if topic in self._consumers:
    #     consumer = self._consumers[topic]
    #     await consumer.stop()
    #     del self._consumers[topic]
    
    logger.info(f"Stopped consumer for topic: {topic}")
  
  async def _consume_messages(self, topic: str, consumer):
    """Consume messages from Kafka (production implementation)."""
    # In production:
    # try:
    #     async for msg in consumer:
    #         # Deserialize message
    #         event_data = json.loads(msg.value.decode())
    #         event = EventMessage.from_dict(event_data)
    #         
    #         # Notify handlers
    #         await self._notify_handlers(event)
    # except Exception as e:
    #     logger.error(f"Error consuming from {topic}: {e}")
    pass
  
  async def _notify_handlers(self, event: EventMessage):
    """Notify subscribed handlers of an event."""
    if event.topic not in self._topic_handlers:
      return
    
    # Get relevant subscriptions
    subscriptions = self._topic_handlers[event.topic]
    
    for subscription in subscriptions:
      # Check filters
      if subscription.event_types and event.event_type not in subscription.event_types:
        continue
      if subscription.priority_filter and event.priority not in subscription.priority_filter:
        continue
      
      # Call handler
      if subscription.handler:
        try:
          # Run handler in background to avoid blocking
          asyncio.create_task(self._run_handler(subscription.handler, event))
        except Exception as e:
          logger.error(
              f"Error calling handler for {subscription.subscriber_id}: {e}"
          )
  
  async def _run_handler(self, handler: Callable, event: EventMessage):
    """Run an event handler safely."""
    try:
      if asyncio.iscoroutinefunction(handler):
        await handler(event)
      else:
        handler(event)
    except Exception as e:
      logger.error(f"Handler error for event {event.id}: {e}")
  
  def get_metrics(self) -> Dict[str, Any]:
    """Get event bus metrics."""
    return {
        "total_events": len(self._event_store),
        "active_subscriptions": len(self._subscriptions),
        "monitored_topics": len(self._topic_handlers),
        "topics": list(self._topic_handlers.keys()),
        "subscriber_count": len(
            set(sub.subscriber_id for sub in self._subscriptions.values())
        ),
    }