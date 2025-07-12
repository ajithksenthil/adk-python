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

"""Data/Integration Mesh implementation for ADK with event bus and lineage tracking."""

from .event_bus import (
  Event,
  EventBus,
  EventBusFactory,
  EventHandler,
  EventMetadata,
  EventPriority,
  EventType,
  InMemoryEventBus,
  KafkaEventBus,
  PubSubEventBus,
  Topics,
)

from .schema_registry import (
  CompatibilityMode,
  ConfluentSchemaRegistry,
  LocalSchemaRegistry,
  SchemaEvolutionHelper,
  SchemaFormat,
  SchemaRegistry,
  SchemaSubject,
  SchemaVersion,
  validate_event,
)

from .cdc_connectors import (
  CDCConnector,
  CDCEvent,
  CDCManager,
  CDCOffset,
  CDCOperation,
  CDCConnectorStatus,
  NetSuiteCDCConnector,
  SalesforceCDCConnector,
  StripeCDCConnector,
  ZendeskCDCConnector,
)

from .lineage_service import (
  LineageEdge,
  LineageEdgeType,
  LineageNode,
  LineageNodeType,
  LineageQuery,
  LineageService,
  LineageVisualizer,
)

__all__ = [
  # Event Bus
  "Event",
  "EventBus", 
  "EventBusFactory",
  "EventHandler",
  "EventMetadata",
  "EventPriority",
  "EventType",
  "InMemoryEventBus",
  "KafkaEventBus",
  "PubSubEventBus",
  "Topics",
  
  # Schema Registry
  "CompatibilityMode",
  "ConfluentSchemaRegistry", 
  "LocalSchemaRegistry",
  "SchemaEvolutionHelper",
  "SchemaFormat",
  "SchemaRegistry",
  "SchemaSubject",
  "SchemaVersion",
  "validate_event",
  
  # CDC Connectors
  "CDCConnector",
  "CDCEvent",
  "CDCManager", 
  "CDCOffset",
  "CDCOperation",
  "CDCConnectorStatus",
  "NetSuiteCDCConnector",
  "SalesforceCDCConnector",
  "StripeCDCConnector",
  "ZendeskCDCConnector",
  
  # Lineage Service
  "LineageEdge",
  "LineageEdgeType",
  "LineageNode", 
  "LineageNodeType",
  "LineageQuery",
  "LineageService",
  "LineageVisualizer",
]