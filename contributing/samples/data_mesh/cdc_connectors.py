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

"""Change Data Capture (CDC) connectors for SaaS integration."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .event_bus import Event, EventBus, EventMetadata, EventPriority, EventType

logger = logging.getLogger(__name__)


class CDCOperation(Enum):
  """CDC operation types."""
  INSERT = "insert"
  UPDATE = "update"
  DELETE = "delete"
  SNAPSHOT = "snapshot"


class CDCConnectorStatus(Enum):
  """Connector status."""
  DISCONNECTED = "disconnected"
  CONNECTING = "connecting"
  CONNECTED = "connected"
  SYNCING = "syncing"
  ERROR = "error"
  PAUSED = "paused"


@dataclass
class CDCOffset:
  """CDC offset for tracking sync position."""
  connector_id: str
  source_system: str
  table_or_object: str
  offset_value: str  # System-specific (timestamp, ID, etc.)
  updated_at: datetime = field(default_factory=datetime.now)
  metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CDCEvent:
  """Change data capture event."""
  operation: CDCOperation
  source_system: str
  table_or_object: str
  primary_key: Dict[str, Any]
  before: Optional[Dict[str, Any]]  # Previous state
  after: Optional[Dict[str, Any]]  # New state
  timestamp: datetime
  sequence: Optional[str] = None
  metadata: Dict[str, Any] = field(default_factory=dict)
  
  def to_event(self, pillar: str) -> Event:
    """Convert to standard event."""
    return Event(
      event_type=EventType.CUSTOM,
      metadata=EventMetadata(
        source_pillar=pillar,
        source_agent=f"cdc_{self.source_system}",
        priority=EventPriority.NORMAL,
        tags={
          "cdc_operation": self.operation.value,
          "source_system": self.source_system,
          "object_type": self.table_or_object
        }
      ),
      payload={
        "operation": self.operation.value,
        "source_system": self.source_system,
        "object": self.table_or_object,
        "primary_key": self.primary_key,
        "before": self.before,
        "after": self.after,
        "timestamp": self.timestamp.isoformat(),
        "sequence": self.sequence
      }
    )


class CDCConnector(ABC):
  """Abstract base class for CDC connectors."""
  
  def __init__(
    self,
    connector_id: str,
    source_system: str,
    event_bus: EventBus,
    pillar: str
  ):
    self.connector_id = connector_id
    self.source_system = source_system
    self.event_bus = event_bus
    self.pillar = pillar
    self.status = CDCConnectorStatus.DISCONNECTED
    self._running = False
    self._tasks: List[asyncio.Task] = []
    self._offsets: Dict[str, CDCOffset] = {}
    self._error_count = 0
    self._last_error: Optional[str] = None
  
  @abstractmethod
  async def connect(self) -> bool:
    """Connect to the source system."""
    pass
  
  @abstractmethod
  async def disconnect(self):
    """Disconnect from the source system."""
    pass
  
  @abstractmethod
  async def get_changes(
    self,
    table_or_object: str,
    since: Optional[datetime] = None
  ) -> List[CDCEvent]:
    """Get changes for a specific table/object."""
    pass
  
  @abstractmethod
  async def get_snapshot(
    self,
    table_or_object: str
  ) -> List[CDCEvent]:
    """Get full snapshot of a table/object."""
    pass
  
  async def start(self, tables_or_objects: List[str]):
    """Start CDC for specified tables/objects."""
    self._running = True
    self.status = CDCConnectorStatus.CONNECTING
    
    # Connect to source
    connected = await self.connect()
    if not connected:
      self.status = CDCConnectorStatus.ERROR
      return
    
    self.status = CDCConnectorStatus.CONNECTED
    
    # Start sync tasks
    for obj in tables_or_objects:
      task = asyncio.create_task(self._sync_loop(obj))
      self._tasks.append(task)
  
  async def stop(self):
    """Stop CDC connector."""
    self._running = False
    
    # Cancel tasks
    for task in self._tasks:
      task.cancel()
    
    if self._tasks:
      await asyncio.gather(*self._tasks, return_exceptions=True)
    
    self._tasks.clear()
    
    # Disconnect
    await self.disconnect()
    self.status = CDCConnectorStatus.DISCONNECTED
  
  async def _sync_loop(self, table_or_object: str):
    """Sync loop for a specific table/object."""
    logger.info(f"Starting CDC sync for {self.source_system}:{table_or_object}")
    
    # Initial snapshot if no offset
    offset_key = f"{self.source_system}:{table_or_object}"
    if offset_key not in self._offsets:
      await self._perform_snapshot(table_or_object)
    
    # Continuous sync
    while self._running:
      try:
        self.status = CDCConnectorStatus.SYNCING
        
        # Get offset
        since = None
        if offset_key in self._offsets:
          # Parse offset based on system
          since = datetime.fromisoformat(self._offsets[offset_key].offset_value)
        
        # Get changes
        changes = await self.get_changes(table_or_object, since)
        
        # Process changes
        for change in changes:
          event = change.to_event(self.pillar)
          topic = f"cdc.{self.source_system.lower()}"
          
          success = await self.event_bus.publish(topic, event)
          if success:
            # Update offset
            self._offsets[offset_key] = CDCOffset(
              connector_id=self.connector_id,
              source_system=self.source_system,
              table_or_object=table_or_object,
              offset_value=change.timestamp.isoformat()
            )
        
        self.status = CDCConnectorStatus.CONNECTED
        self._error_count = 0
        
        # Sleep before next poll
        await asyncio.sleep(5)  # Configurable
        
      except Exception as e:
        logger.error(f"CDC sync error for {table_or_object}: {e}")
        self._error_count += 1
        self._last_error = str(e)
        self.status = CDCConnectorStatus.ERROR
        
        # Exponential backoff
        await asyncio.sleep(min(60, 2 ** self._error_count))
  
  async def _perform_snapshot(self, table_or_object: str):
    """Perform initial snapshot."""
    logger.info(f"Performing snapshot for {self.source_system}:{table_or_object}")
    
    try:
      snapshot_events = await self.get_snapshot(table_or_object)
      
      for event in snapshot_events:
        topic = f"cdc.{self.source_system.lower()}"
        await self.event_bus.publish(topic, event.to_event(self.pillar))
      
      # Set initial offset
      if snapshot_events:
        offset_key = f"{self.source_system}:{table_or_object}"
        self._offsets[offset_key] = CDCOffset(
          connector_id=self.connector_id,
          source_system=self.source_system,
          table_or_object=table_or_object,
          offset_value=datetime.now().isoformat()
        )
      
      logger.info(f"Snapshot complete: {len(snapshot_events)} records")
      
    except Exception as e:
      logger.error(f"Snapshot failed for {table_or_object}: {e}")
      raise
  
  def get_status(self) -> Dict[str, Any]:
    """Get connector status."""
    return {
      "connector_id": self.connector_id,
      "source_system": self.source_system,
      "status": self.status.value,
      "error_count": self._error_count,
      "last_error": self._last_error,
      "offsets": {
        k: {
          "table": v.table_or_object,
          "offset": v.offset_value,
          "updated": v.updated_at.isoformat()
        }
        for k, v in self._offsets.items()
      }
    }


class SalesforceCDCConnector(CDCConnector):
  """CDC connector for Salesforce."""
  
  def __init__(
    self,
    connector_id: str,
    event_bus: EventBus,
    pillar: str,
    instance_url: str,
    access_token: str
  ):
    super().__init__(connector_id, "salesforce", event_bus, pillar)
    self.instance_url = instance_url
    self.access_token = access_token
    self._client = None
  
  async def connect(self) -> bool:
    """Connect to Salesforce."""
    try:
      # In production, would use simple_salesforce or similar
      # self._client = Salesforce(
      #   instance_url=self.instance_url,
      #   session_id=self.access_token
      # )
      logger.info(f"Connected to Salesforce: {self.instance_url}")
      return True
    except Exception as e:
      logger.error(f"Failed to connect to Salesforce: {e}")
      return False
  
  async def disconnect(self):
    """Disconnect from Salesforce."""
    self._client = None
  
  async def get_changes(
    self,
    table_or_object: str,
    since: Optional[datetime] = None
  ) -> List[CDCEvent]:
    """Get changes using Salesforce CDC API."""
    changes = []
    
    # In production, would use Salesforce CDC/Streaming API
    # Example: Platform Events, Change Data Capture, or PushTopic
    
    # Mock implementation
    if since is None:
      since = datetime.now() - timedelta(minutes=5)
    
    # Simulate some changes
    mock_changes = [
      {
        "Id": "003XX000001234",
        "Name": "John Doe",
        "Email": "john@example.com",
        "LastModifiedDate": datetime.now().isoformat()
      }
    ]
    
    for record in mock_changes:
      changes.append(CDCEvent(
        operation=CDCOperation.UPDATE,
        source_system=self.source_system,
        table_or_object=table_or_object,
        primary_key={"Id": record["Id"]},
        before=None,  # Salesforce CDC doesn't provide before state
        after=record,
        timestamp=datetime.fromisoformat(record["LastModifiedDate"])
      ))
    
    return changes
  
  async def get_snapshot(
    self,
    table_or_object: str
  ) -> List[CDCEvent]:
    """Get snapshot using SOQL query."""
    snapshot = []
    
    # In production:
    # query = f"SELECT Id, Name, Email FROM {table_or_object}"
    # records = self._client.query_all(query)
    
    # Mock implementation
    mock_records = [
      {
        "Id": f"003XX00000{i}",
        "Name": f"Contact {i}",
        "Email": f"contact{i}@example.com"
      }
      for i in range(5)
    ]
    
    for record in mock_records:
      snapshot.append(CDCEvent(
        operation=CDCOperation.SNAPSHOT,
        source_system=self.source_system,
        table_or_object=table_or_object,
        primary_key={"Id": record["Id"]},
        before=None,
        after=record,
        timestamp=datetime.now()
      ))
    
    return snapshot


class StripeCDCConnector(CDCConnector):
  """CDC connector for Stripe events."""
  
  def __init__(
    self,
    connector_id: str,
    event_bus: EventBus,
    pillar: str,
    api_key: str
  ):
    super().__init__(connector_id, "stripe", event_bus, pillar)
    self.api_key = api_key
    self._last_event_id = None
  
  async def connect(self) -> bool:
    """Connect to Stripe."""
    try:
      # In production: stripe.api_key = self.api_key
      logger.info("Connected to Stripe API")
      return True
    except Exception as e:
      logger.error(f"Failed to connect to Stripe: {e}")
      return False
  
  async def disconnect(self):
    """Disconnect from Stripe."""
    pass
  
  async def get_changes(
    self,
    table_or_object: str,
    since: Optional[datetime] = None
  ) -> List[CDCEvent]:
    """Get changes from Stripe events API."""
    changes = []
    
    # In production, would use Stripe Events API
    # events = stripe.Event.list(
    #   type=table_or_object,
    #   created={"gte": int(since.timestamp())} if since else None
    # )
    
    # Mock implementation for payment events
    if table_or_object == "payment_intent":
      mock_events = [
        {
          "id": "evt_1234",
          "type": "payment_intent.succeeded",
          "data": {
            "object": {
              "id": "pi_1234",
              "amount": 10000,
              "currency": "usd",
              "status": "succeeded"
            }
          },
          "created": int(datetime.now().timestamp())
        }
      ]
      
      for event in mock_events:
        changes.append(CDCEvent(
          operation=CDCOperation.INSERT,
          source_system=self.source_system,
          table_or_object=table_or_object,
          primary_key={"id": event["data"]["object"]["id"]},
          before=None,
          after=event["data"]["object"],
          timestamp=datetime.fromtimestamp(event["created"]),
          sequence=event["id"]
        ))
    
    return changes
  
  async def get_snapshot(
    self,
    table_or_object: str
  ) -> List[CDCEvent]:
    """Get snapshot of Stripe objects."""
    snapshot = []
    
    # In production, would list objects
    # E.g., stripe.Customer.list() for customers
    
    return snapshot


class NetSuiteCDCConnector(CDCConnector):
  """CDC connector for NetSuite."""
  
  def __init__(
    self,
    connector_id: str,
    event_bus: EventBus,
    pillar: str,
    account_id: str,
    consumer_key: str,
    consumer_secret: str,
    token_id: str,
    token_secret: str
  ):
    super().__init__(connector_id, "netsuite", event_bus, pillar)
    self.account_id = account_id
    self.consumer_key = consumer_key
    self.consumer_secret = consumer_secret
    self.token_id = token_id
    self.token_secret = token_secret
  
  async def connect(self) -> bool:
    """Connect to NetSuite."""
    try:
      # In production, would use NetSuite REST/SOAP API
      logger.info(f"Connected to NetSuite account: {self.account_id}")
      return True
    except Exception as e:
      logger.error(f"Failed to connect to NetSuite: {e}")
      return False
  
  async def disconnect(self):
    """Disconnect from NetSuite."""
    pass
  
  async def get_changes(
    self,
    table_or_object: str,
    since: Optional[datetime] = None
  ) -> List[CDCEvent]:
    """Get changes using NetSuite saved search."""
    changes = []
    
    # In production, would use SuiteQL or saved searches
    # to find modified records
    
    # Mock implementation for transactions
    if table_or_object == "transaction":
      mock_transactions = [
        {
          "id": "12345",
          "type": "salesorder",
          "tranid": "SO-2024-001",
          "entity": "Customer ABC",
          "total": 5000.00,
          "lastmodifieddate": datetime.now().isoformat()
        }
      ]
      
      for txn in mock_transactions:
        changes.append(CDCEvent(
          operation=CDCOperation.UPDATE,
          source_system=self.source_system,
          table_or_object=table_or_object,
          primary_key={"id": txn["id"]},
          before=None,
          after=txn,
          timestamp=datetime.fromisoformat(txn["lastmodifieddate"])
        ))
    
    return changes
  
  async def get_snapshot(
    self,
    table_or_object: str
  ) -> List[CDCEvent]:
    """Get snapshot using NetSuite search."""
    # Would implement full table scan
    return []


class ZendeskCDCConnector(CDCConnector):
  """CDC connector for Zendesk."""
  
  def __init__(
    self,
    connector_id: str,
    event_bus: EventBus,
    pillar: str,
    subdomain: str,
    email: str,
    api_token: str
  ):
    super().__init__(connector_id, "zendesk", event_bus, pillar)
    self.subdomain = subdomain
    self.email = email
    self.api_token = api_token
  
  async def connect(self) -> bool:
    """Connect to Zendesk."""
    try:
      # In production, would use Zendesk API client
      logger.info(f"Connected to Zendesk: {self.subdomain}")
      return True
    except Exception as e:
      logger.error(f"Failed to connect to Zendesk: {e}")
      return False
  
  async def disconnect(self):
    """Disconnect from Zendesk."""
    pass
  
  async def get_changes(
    self,
    table_or_object: str,
    since: Optional[datetime] = None
  ) -> List[CDCEvent]:
    """Get changes using Zendesk incremental export."""
    changes = []
    
    # In production, would use Incremental Exports API
    # /api/v2/incremental/tickets.json?start_time=...
    
    # Mock implementation for tickets
    if table_or_object == "ticket":
      mock_tickets = [
        {
          "id": 98765,
          "subject": "Product issue",
          "status": "open",
          "priority": "high",
          "updated_at": datetime.now().isoformat()
        }
      ]
      
      for ticket in mock_tickets:
        changes.append(CDCEvent(
          operation=CDCOperation.UPDATE,
          source_system=self.source_system,
          table_or_object=table_or_object,
          primary_key={"id": ticket["id"]},
          before=None,
          after=ticket,
          timestamp=datetime.fromisoformat(ticket["updated_at"])
        ))
    
    return changes
  
  async def get_snapshot(
    self,
    table_or_object: str
  ) -> List[CDCEvent]:
    """Get snapshot of Zendesk objects."""
    # Would implement using list endpoints
    return []


class CDCManager:
  """Manager for CDC connectors."""
  
  def __init__(self, event_bus: EventBus):
    self.event_bus = event_bus
    self._connectors: Dict[str, CDCConnector] = {}
  
  def register_connector(self, connector: CDCConnector):
    """Register a CDC connector."""
    self._connectors[connector.connector_id] = connector
    logger.info(f"Registered CDC connector: {connector.connector_id}")
  
  async def start_connector(
    self,
    connector_id: str,
    tables_or_objects: List[str]
  ):
    """Start a specific connector."""
    if connector_id not in self._connectors:
      raise ValueError(f"Unknown connector: {connector_id}")
    
    connector = self._connectors[connector_id]
    await connector.start(tables_or_objects)
  
  async def stop_connector(self, connector_id: str):
    """Stop a specific connector."""
    if connector_id in self._connectors:
      await self._connectors[connector_id].stop()
  
  async def stop_all(self):
    """Stop all connectors."""
    for connector in self._connectors.values():
      await connector.stop()
  
  def get_status(self) -> Dict[str, Any]:
    """Get status of all connectors."""
    return {
      connector_id: connector.get_status()
      for connector_id, connector in self._connectors.items()
    }
  
  def get_connector(self, connector_id: str) -> Optional[CDCConnector]:
    """Get a specific connector."""
    return self._connectors.get(connector_id)