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
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventPriority(Enum):
  """Event priority levels."""
  LOW = "low"
  NORMAL = "normal"
  HIGH = "high"
  CRITICAL = "critical"


class EventType(Enum):
  """Standard event types across pillars."""
  # Mission & Governance
  POLICY_UPDATE = "policy.update"
  BUDGET_APPROVAL = "budget.approval"
  RISK_ALERT = "risk.alert"
  
  # Product & Experience
  FEATURE_RELEASE = "feature.release"
  CODE_MERGE = "code.merge"
  QA_RESULT = "qa.result"
  
  # Growth Engine
  CAMPAIGN_LAUNCH = "campaign.launch"
  LEAD_GENERATED = "lead.generated"
  DEAL_WON = "deal.won"
  
  # Customer Success
  TICKET_CREATED = "ticket.created"
  REFUND_PROCESSED = "refund.processed"
  CHURN_RISK = "churn.risk"
  
  # Resource & Supply
  INVENTORY_UPDATE = "inventory.update"
  PO_CREATED = "po.created"
  SHIPMENT_TRACKED = "shipment.tracked"
  
  # People & Culture
  CANDIDATE_APPLIED = "candidate.applied"
  EMPLOYEE_ONBOARDED = "employee.onboarded"
  SURVEY_COMPLETED = "survey.completed"
  
  # Intelligence & Improvement
  METRIC_COLLECTED = "metric.collected"
  EXPERIMENT_STARTED = "experiment.started"
  MODEL_DEPLOYED = "model.deployed"
  
  # Platform & Infra
  SERVICE_DEPLOYED = "service.deployed"
  ALERT_TRIGGERED = "alert.triggered"
  SCALING_EVENT = "scaling.event"
  
  # Generic
  CUSTOM = "custom"
  AGENT_ACTION = "agent.action"
  SYSTEM_EVENT = "system.event"


@dataclass
class EventMetadata:
  """Metadata for event tracking and lineage."""
  event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
  trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
  span_id: Optional[str] = None
  parent_span_id: Optional[str] = None
  source_pillar: str = ""
  source_agent: str = ""
  target_pillar: Optional[str] = None
  target_agent: Optional[str] = None
  timestamp: datetime = field(default_factory=datetime.now)
  priority: EventPriority = EventPriority.NORMAL
  correlation_id: Optional[str] = None  # For related events
  causation_id: Optional[str] = None  # Event that caused this one
  tags: Dict[str, str] = field(default_factory=dict)
  
  def to_headers(self) -> Dict[str, str]:
    """Convert metadata to headers for message passing."""
    return {
      "event_id": self.event_id,
      "trace_id": self.trace_id,
      "span_id": self.span_id or "",
      "parent_span_id": self.parent_span_id or "",
      "source_pillar": self.source_pillar,
      "source_agent": self.source_agent,
      "timestamp": self.timestamp.isoformat(),
      "priority": self.priority.value,
      "correlation_id": self.correlation_id or "",
      "causation_id": self.causation_id or "",
    }
  
  @classmethod
  def from_headers(cls, headers: Dict[str, str]) -> EventMetadata:
    """Create metadata from message headers."""
    return cls(
      event_id=headers.get("event_id", str(uuid.uuid4())),
      trace_id=headers.get("trace_id", str(uuid.uuid4())),
      span_id=headers.get("span_id") or None,
      parent_span_id=headers.get("parent_span_id") or None,
      source_pillar=headers.get("source_pillar", ""),
      source_agent=headers.get("source_agent", ""),
      timestamp=datetime.fromisoformat(headers.get("timestamp", datetime.now().isoformat())),
      priority=EventPriority(headers.get("priority", "normal")),
      correlation_id=headers.get("correlation_id") or None,
      causation_id=headers.get("causation_id") or None,
    )


class Event(BaseModel):
  """Base event class for the data mesh."""
  event_type: EventType
  metadata: EventMetadata
  payload: Dict[str, Any]
  schema_version: str = "1.0.0"
  
  class Config:
    arbitrary_types_allowed = True
  
  def to_json(self) -> str:
    """Convert event to JSON string."""
    return json.dumps({
      "event_type": self.event_type.value,
      "metadata": {
        **self.metadata.to_headers(),
        "tags": self.metadata.tags
      },
      "payload": self.payload,
      "schema_version": self.schema_version
    })
  
  @classmethod
  def from_json(cls, json_str: str) -> Event:
    """Create event from JSON string."""
    data = json.loads(json_str)
    metadata_dict = data.get("metadata", {})
    
    # Create metadata with tags
    metadata = EventMetadata.from_headers(metadata_dict)
    metadata.tags = metadata_dict.get("tags", {})
    
    return cls(
      event_type=EventType(data["event_type"]),
      metadata=metadata,
      payload=data["payload"],
      schema_version=data.get("schema_version", "1.0.0")
    )


class EventHandler:
  """Handler for processing events."""
  
  def __init__(
    self,
    handler_func: Callable[[Event], None],
    event_types: Optional[List[EventType]] = None,
    pillars: Optional[List[str]] = None,
    priority_filter: Optional[List[EventPriority]] = None
  ):
    self.handler_func = handler_func
    self.event_types = event_types or []
    self.pillars = pillars or []
    self.priority_filter = priority_filter or []
  
  def should_handle(self, event: Event) -> bool:
    """Check if this handler should process the event."""
    # Check event type filter
    if self.event_types and event.event_type not in self.event_types:
      return False
    
    # Check pillar filter
    if self.pillars and event.metadata.source_pillar not in self.pillars:
      return False
    
    # Check priority filter
    if self.priority_filter and event.metadata.priority not in self.priority_filter:
      return False
    
    return True
  
  async def handle(self, event: Event):
    """Handle the event."""
    if asyncio.iscoroutinefunction(self.handler_func):
      await self.handler_func(event)
    else:
      self.handler_func(event)


class EventBus(ABC):
  """Abstract base class for event bus implementations."""
  
  @abstractmethod
  async def publish(self, topic: str, event: Event) -> bool:
    """Publish an event to a topic."""
    pass
  
  @abstractmethod
  async def subscribe(
    self,
    topic: str,
    handler: EventHandler,
    subscription_id: Optional[str] = None
  ) -> str:
    """Subscribe to a topic with a handler."""
    pass
  
  @abstractmethod
  async def unsubscribe(self, subscription_id: str) -> bool:
    """Unsubscribe from a topic."""
    pass
  
  @abstractmethod
  async def close(self):
    """Close the event bus connection."""
    pass


class InMemoryEventBus(EventBus):
  """In-memory event bus for development and testing."""
  
  def __init__(self):
    self._topics: Dict[str, List[Event]] = {}
    self._subscriptions: Dict[str, Dict[str, EventHandler]] = {}
    self._running = True
    self._tasks: List[asyncio.Task] = []
  
  async def publish(self, topic: str, event: Event) -> bool:
    """Publish an event to a topic."""
    if not self._running:
      return False
    
    # Store event
    if topic not in self._topics:
      self._topics[topic] = []
    self._topics[topic].append(event)
    
    # Notify subscribers
    if topic in self._subscriptions:
      for handler in self._subscriptions[topic].values():
        if handler.should_handle(event):
          task = asyncio.create_task(handler.handle(event))
          self._tasks.append(task)
    
    logger.info(f"Published event {event.event_type.value} to topic {topic}")
    return True
  
  async def subscribe(
    self,
    topic: str,
    handler: EventHandler,
    subscription_id: Optional[str] = None
  ) -> str:
    """Subscribe to a topic with a handler."""
    if not subscription_id:
      subscription_id = f"{topic}_{uuid.uuid4().hex[:8]}"
    
    if topic not in self._subscriptions:
      self._subscriptions[topic] = {}
    
    self._subscriptions[topic][subscription_id] = handler
    logger.info(f"Subscribed to topic {topic} with ID {subscription_id}")
    
    return subscription_id
  
  async def unsubscribe(self, subscription_id: str) -> bool:
    """Unsubscribe from a topic."""
    for topic, subscriptions in self._subscriptions.items():
      if subscription_id in subscriptions:
        del subscriptions[subscription_id]
        logger.info(f"Unsubscribed {subscription_id} from topic {topic}")
        return True
    return False
  
  async def close(self):
    """Close the event bus."""
    self._running = False
    # Wait for pending tasks
    if self._tasks:
      await asyncio.gather(*self._tasks, return_exceptions=True)
    self._tasks.clear()
  
  def get_events(self, topic: str) -> List[Event]:
    """Get all events for a topic (for testing)."""
    return self._topics.get(topic, [])


class KafkaEventBus(EventBus):
  """Kafka-based event bus for production use."""
  
  def __init__(
    self,
    bootstrap_servers: str = "localhost:9092",
    consumer_group: str = "adk-agents"
  ):
    self.bootstrap_servers = bootstrap_servers
    self.consumer_group = consumer_group
    self._producers: Dict[str, Any] = {}
    self._consumers: Dict[str, Any] = {}
    self._running = True
    logger.info(f"Kafka event bus initialized with servers: {bootstrap_servers}")
  
  async def publish(self, topic: str, event: Event) -> bool:
    """Publish an event to Kafka topic."""
    try:
      # In production, would use aiokafka
      # from aiokafka import AIOKafkaProducer
      # producer = self._get_producer()
      # await producer.send(
      #   topic,
      #   value=event.to_json().encode(),
      #   headers=event.metadata.to_headers()
      # )
      
      logger.info(f"Published event {event.event_type.value} to Kafka topic {topic}")
      return True
    except Exception as e:
      logger.error(f"Failed to publish to Kafka: {e}")
      return False
  
  async def subscribe(
    self,
    topic: str,
    handler: EventHandler,
    subscription_id: Optional[str] = None
  ) -> str:
    """Subscribe to Kafka topic."""
    if not subscription_id:
      subscription_id = f"{self.consumer_group}_{topic}_{uuid.uuid4().hex[:8]}"
    
    # In production, would create Kafka consumer
    # consumer = AIOKafkaConsumer(
    #   topic,
    #   bootstrap_servers=self.bootstrap_servers,
    #   group_id=self.consumer_group
    # )
    # await consumer.start()
    # asyncio.create_task(self._consume_loop(consumer, handler))
    
    logger.info(f"Subscribed to Kafka topic {topic} with ID {subscription_id}")
    return subscription_id
  
  async def unsubscribe(self, subscription_id: str) -> bool:
    """Unsubscribe from Kafka topic."""
    # In production, would stop consumer
    logger.info(f"Unsubscribed {subscription_id} from Kafka")
    return True
  
  async def close(self):
    """Close Kafka connections."""
    self._running = False
    # In production, would close all producers and consumers


class PubSubEventBus(EventBus):
  """Google Cloud Pub/Sub event bus."""
  
  def __init__(self, project_id: str):
    self.project_id = project_id
    self._subscriptions: Dict[str, Any] = {}
    logger.info(f"Pub/Sub event bus initialized for project: {project_id}")
  
  async def publish(self, topic: str, event: Event) -> bool:
    """Publish event to Pub/Sub topic."""
    try:
      # In production, would use google-cloud-pubsub
      # from google.cloud import pubsub_v1
      # publisher = pubsub_v1.PublisherClient()
      # topic_path = publisher.topic_path(self.project_id, topic)
      # future = publisher.publish(
      #   topic_path,
      #   event.to_json().encode(),
      #   **event.metadata.to_headers()
      # )
      
      logger.info(f"Published event {event.event_type.value} to Pub/Sub topic {topic}")
      return True
    except Exception as e:
      logger.error(f"Failed to publish to Pub/Sub: {e}")
      return False
  
  async def subscribe(
    self,
    topic: str,
    handler: EventHandler,
    subscription_id: Optional[str] = None
  ) -> str:
    """Subscribe to Pub/Sub topic."""
    if not subscription_id:
      subscription_id = f"{topic}-sub-{uuid.uuid4().hex[:8]}"
    
    # In production, would create Pub/Sub subscription
    logger.info(f"Subscribed to Pub/Sub topic {topic} with ID {subscription_id}")
    return subscription_id
  
  async def unsubscribe(self, subscription_id: str) -> bool:
    """Unsubscribe from Pub/Sub topic."""
    logger.info(f"Unsubscribed {subscription_id} from Pub/Sub")
    return True
  
  async def close(self):
    """Close Pub/Sub connections."""
    pass


class EventBusFactory:
  """Factory for creating event bus instances."""
  
  @staticmethod
  def create(
    bus_type: str = "memory",
    **kwargs
  ) -> EventBus:
    """Create an event bus instance."""
    if bus_type == "memory":
      return InMemoryEventBus()
    elif bus_type == "kafka":
      return KafkaEventBus(
        bootstrap_servers=kwargs.get("bootstrap_servers", "localhost:9092"),
        consumer_group=kwargs.get("consumer_group", "adk-agents")
      )
    elif bus_type == "pubsub":
      return PubSubEventBus(
        project_id=kwargs.get("project_id", "")
      )
    else:
      raise ValueError(f"Unknown event bus type: {bus_type}")


# Topic naming conventions
class Topics:
  """Standard topic names for each pillar."""
  
  # Pillar-specific topics
  MISSION = "pillar.mission"
  PRODUCT = "pillar.product"
  GROWTH = "pillar.growth"
  CUSTOMER = "pillar.customer"
  SUPPLY = "pillar.supply"
  PEOPLE = "pillar.people"
  INTEL = "pillar.intel"
  PLATFORM = "pillar.platform"
  
  # Cross-cutting topics
  ALERTS = "system.alerts"
  METRICS = "system.metrics"
  AUDIT = "system.audit"
  POLICY = "system.policy"
  
  # CDC topics
  CDC_SALESFORCE = "cdc.salesforce"
  CDC_NETSUITE = "cdc.netsuite"
  CDC_STRIPE = "cdc.stripe"
  CDC_ZENDESK = "cdc.zendesk"
  
  @classmethod
  def for_pillar(cls, pillar: str) -> str:
    """Get topic name for a pillar."""
    pillar_map = {
      "Mission & Governance": cls.MISSION,
      "Product & Experience": cls.PRODUCT,
      "Growth Engine": cls.GROWTH,
      "Customer Success": cls.CUSTOMER,
      "Resource & Supply": cls.SUPPLY,
      "People & Culture": cls.PEOPLE,
      "Intelligence & Improvement": cls.INTEL,
      "Platform & Infra": cls.PLATFORM,
    }
    return pillar_map.get(pillar, f"pillar.{pillar.lower().replace(' ', '_')}")