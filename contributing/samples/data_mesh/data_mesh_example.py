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

"""Example demonstrating the complete Data/Integration Mesh functionality."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List

from .cdc_connectors import (
  CDCManager,
  SalesforceCDCConnector,
  StripeCDCConnector,
  ZendeskCDCConnector,
)
from .event_bus import Event, EventBusFactory, EventHandler, EventMetadata, EventPriority, EventType, Topics
from .lineage_service import LineageQuery, LineageService, LineageVisualizer
from .schema_registry import LocalSchemaRegistry, SchemaFormat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def demonstrate_event_bus():
  """Demonstrate event bus functionality."""
  print("=== Event Bus Demo ===\n")
  
  # Create event bus
  event_bus = EventBusFactory.create("memory")
  
  # Create handlers for different pillars
  growth_events = []
  customer_events = []
  
  async def handle_growth(event: Event):
    growth_events.append(event)
    print(f"Growth Engine received: {event.event_type.value}")
  
  async def handle_customer(event: Event):
    customer_events.append(event)
    print(f"Customer Success received: {event.event_type.value}")
  
  # Subscribe to topics
  growth_handler = EventHandler(
    handler_func=handle_growth,
    event_types=[EventType.CAMPAIGN_LAUNCH, EventType.LEAD_GENERATED]
  )
  
  customer_handler = EventHandler(
    handler_func=handle_customer,
    event_types=[EventType.TICKET_CREATED, EventType.CHURN_RISK]
  )
  
  await event_bus.subscribe(Topics.GROWTH, growth_handler)
  await event_bus.subscribe(Topics.CUSTOMER, customer_handler)
  
  # Publish events
  campaign_event = Event(
    event_type=EventType.CAMPAIGN_LAUNCH,
    metadata=EventMetadata(
      source_pillar="Growth Engine",
      source_agent="marketing_agent",
      priority=EventPriority.HIGH
    ),
    payload={
      "campaign_id": "camp_001",
      "channel": "email",
      "budget": 5000.0,
      "target_audience": "enterprise_prospects"
    }
  )
  
  ticket_event = Event(
    event_type=EventType.TICKET_CREATED,
    metadata=EventMetadata(
      source_pillar="Customer Success",
      source_agent="support_agent",
      priority=EventPriority.NORMAL
    ),
    payload={
      "ticket_id": "TIK-123",
      "customer_id": "cust_456",
      "issue_type": "billing",
      "severity": "medium"
    }
  )
  
  await event_bus.publish(Topics.GROWTH, campaign_event)
  await event_bus.publish(Topics.CUSTOMER, ticket_event)
  
  # Wait for async handlers
  await asyncio.sleep(0.1)
  
  print(f"\nEvents processed:")
  print(f"  Growth Engine: {len(growth_events)} events")
  print(f"  Customer Success: {len(customer_events)} events\n")
  
  await event_bus.close()
  return event_bus


async def demonstrate_schema_registry():
  """Demonstrate schema registry functionality."""
  print("=== Schema Registry Demo ===\n")
  
  registry = LocalSchemaRegistry()
  
  # Register a custom schema
  lead_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "lead_id": {"type": "string"},
      "email": {"type": "string", "format": "email"},
      "company": {"type": "string"},
      "score": {"type": "integer", "minimum": 0, "maximum": 100},
      "source": {"type": "string", "enum": ["website", "referral", "event", "advertising"]}
    },
    "required": ["lead_id", "email", "score"]
  }
  
  version = await registry.register_schema(
    "event.lead.generated",
    lead_schema,
    SchemaFormat.JSON_SCHEMA
  )
  
  print(f"Registered lead schema version {version}")
  
  # Test validation
  valid_data = {
    "lead_id": "lead_789",
    "email": "prospect@example.com",
    "company": "Tech Corp",
    "score": 85,
    "source": "website"
  }
  
  invalid_data = {
    "lead_id": "lead_790",
    "email": "invalid-email",  # Invalid format
    "score": 150  # Out of range
  }
  
  valid = await registry.validate("event.lead.generated", valid_data)
  invalid = await registry.validate("event.lead.generated", invalid_data)
  
  print(f"Valid data passed: {valid}")
  print(f"Invalid data passed: {invalid}")
  
  # List all schemas
  subjects = await registry.list_subjects()
  print(f"\nRegistered schemas: {len(subjects)}")
  for subject in subjects:
    info = registry.get_subject_info(subject)
    print(f"  {subject}: {info['latest_version']} versions")
  
  print()
  return registry


async def demonstrate_cdc_connectors():
  """Demonstrate CDC connectors."""
  print("=== CDC Connectors Demo ===\n")
  
  # Create event bus for CDC events
  event_bus = EventBusFactory.create("memory")
  cdc_manager = CDCManager(event_bus)
  
  # Track CDC events
  cdc_events = []
  
  async def track_cdc_event(event: Event):
    cdc_events.append(event)
    source = event.payload.get("source_system")
    operation = event.payload.get("operation")
    obj = event.payload.get("object")
    print(f"CDC Event: {source} - {operation} on {obj}")
  
  cdc_handler = EventHandler(handler_func=track_cdc_event)
  await event_bus.subscribe("cdc.salesforce", cdc_handler)
  await event_bus.subscribe("cdc.stripe", cdc_handler)
  await event_bus.subscribe("cdc.zendesk", cdc_handler)
  
  # Register connectors
  salesforce_connector = SalesforceCDCConnector(
    connector_id="sf_001",
    event_bus=event_bus,
    pillar="Customer Success",
    instance_url="https://mycompany.salesforce.com",
    access_token="mock_token"
  )
  
  stripe_connector = StripeCDCConnector(
    connector_id="stripe_001",
    event_bus=event_bus,
    pillar="Growth Engine",
    api_key="sk_test_mock"
  )
  
  zendesk_connector = ZendeskCDCConnector(
    connector_id="zendesk_001",
    event_bus=event_bus,
    pillar="Customer Success",
    subdomain="mycompany",
    email="admin@mycompany.com",
    api_token="mock_token"
  )
  
  cdc_manager.register_connector(salesforce_connector)
  cdc_manager.register_connector(stripe_connector)
  cdc_manager.register_connector(zendesk_connector)
  
  # Start connectors
  await cdc_manager.start_connector("sf_001", ["Contact", "Opportunity"])
  await cdc_manager.start_connector("stripe_001", ["payment_intent"])
  await cdc_manager.start_connector("zendesk_001", ["ticket"])
  
  # Let connectors run for a bit
  await asyncio.sleep(2)
  
  # Check status
  status = cdc_manager.get_status()
  print(f"\nConnector Status:")
  for connector_id, info in status.items():
    print(f"  {connector_id}: {info['status']} (errors: {info['error_count']})")
  
  print(f"\nCDC Events captured: {len(cdc_events)}")
  
  # Stop connectors
  await cdc_manager.stop_all()
  await event_bus.close()
  
  print()
  return cdc_events


async def demonstrate_lineage_tracking():
  """Demonstrate lineage tracking."""
  print("=== Lineage Tracking Demo ===\n")
  
  lineage_service = LineageService()
  
  # Create event bus with lineage tracking
  event_bus = EventBusFactory.create("memory")
  lineage_handler = lineage_service.create_event_handler()
  await event_bus.subscribe("system.audit", lineage_handler)
  
  # Simulate agent workflow
  trace_id = "trace_001"
  
  # Step 1: Lead generation agent processes data
  await lineage_service.add_node(
    node_id="agent:lead_generation",
    node_type=lineage_service.LineageNodeType.AGENT,
    name="Lead Generation Agent",
    pillar="Growth Engine"
  )
  
  await lineage_service.add_node(
    node_id="data:website_forms",
    node_type=lineage_service.LineageNodeType.DATA_SOURCE,
    name="Website Forms"
  )
  
  await lineage_service.track_data_flow(
    source_id="data:website_forms",
    sink_id="agent:lead_generation",
    trace_id=trace_id,
    record_count=5
  )
  
  # Step 2: Lead scoring tool
  await lineage_service.track_tool_invocation(
    agent_id="agent:lead_generation",
    tool_name="lead_scorer",
    trace_id=trace_id,
    inputs={"leads": 5},
    outputs={"qualified_leads": 3},
    pillar="Growth Engine"
  )
  
  # Step 3: Decision to route high-score leads
  await lineage_service.track_decision(
    agent_id="agent:lead_generation",
    decision_id="route_leads",
    trace_id=trace_id,
    decision_type="lead_routing",
    result="sales_qualified",
    factors=["score > 80", "company_size > 100"]
  )
  
  # Step 4: Sales agent takes over
  await lineage_service.add_node(
    node_id="agent:sales_outreach",
    node_type=lineage_service.LineageNodeType.AGENT,
    name="Sales Outreach Agent",
    pillar="Growth Engine"
  )
  
  await lineage_service.add_edge(
    source_id="agent:lead_generation",
    target_id="agent:sales_outreach",
    edge_type=lineage_service.LineageEdgeType.TRIGGERS,
    trace_id=trace_id
  )
  
  # Query lineage
  query = LineageQuery(
    trace_id=trace_id,
    direction="both",
    include_metadata=True
  )
  
  lineage_data = await lineage_service.query_lineage(query)
  
  print(f"Lineage Analysis:")
  print(f"  Nodes: {lineage_data['stats']['total_nodes']}")
  print(f"  Edges: {lineage_data['stats']['total_edges']}")
  print(f"  Node Types: {lineage_data['stats']['node_types']}")
  print(f"  Pillars: {lineage_data['stats']['pillars_involved']}")
  
  # Get trace timeline
  timeline = await lineage_service.get_trace_timeline(trace_id)
  print(f"\nTrace Timeline:")
  for step in timeline:
    print(f"  {step['timestamp']}: {step['source']['name']} -> {step['action']} -> {step['target']['name']}")
  
  # Impact analysis
  impact = await lineage_service.find_impact("agent:lead_generation")
  print(f"\nImpact Analysis for Lead Generation Agent:")
  print(f"  Affected Nodes: {len(impact['affected_nodes'])}")
  print(f"  Risk Level: {impact['risk_level']}")
  print(f"  Affected Pillars: {impact['affected_pillars']}")
  
  await event_bus.close()
  
  print()
  return lineage_data


async def demonstrate_end_to_end_flow():
  """Demonstrate complete end-to-end data mesh flow."""
  print("=== End-to-End Data Mesh Flow ===\n")
  
  # Initialize components
  event_bus = EventBusFactory.create("memory")
  schema_registry = LocalSchemaRegistry()
  lineage_service = LineageService()
  cdc_manager = CDCManager(event_bus)
  
  # Set up lineage tracking
  lineage_handler = lineage_service.create_event_handler()
  await event_bus.subscribe(Topics.AUDIT, lineage_handler)
  
  # Register schemas for the flow
  customer_update_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "customer_id": {"type": "string"},
      "account_status": {"type": "string"},
      "last_activity": {"type": "string", "format": "date-time"},
      "health_score": {"type": "integer", "minimum": 0, "maximum": 100}
    },
    "required": ["customer_id", "account_status"]
  }
  
  await schema_registry.register_schema(
    "event.customer.update",
    customer_update_schema
  )
  
  # Set up CDC connector
  salesforce_connector = SalesforceCDCConnector(
    connector_id="sf_main",
    event_bus=event_bus,
    pillar="Customer Success",
    instance_url="https://company.salesforce.com",
    access_token="token"
  )
  cdc_manager.register_connector(salesforce_connector)
  
  # Event tracking
  processed_events = []
  
  async def process_customer_event(event: Event):
    # Validate event against schema
    is_valid = await schema_registry.validate("event.customer.update", event.payload)
    
    if is_valid:
      processed_events.append(event)
      print(f"✓ Processed valid customer event: {event.payload.get('customer_id')}")
      
      # Simulate downstream processing
      if event.payload.get("health_score", 100) < 50:
        # Trigger churn prevention workflow
        churn_event = Event(
          event_type=EventType.CHURN_RISK,
          metadata=EventMetadata(
            source_pillar="Customer Success",
            source_agent="churn_detection_agent",
            target_pillar="Customer Success",
            target_agent="retention_agent",
            trace_id=event.metadata.trace_id,
            causation_id=event.metadata.event_id
          ),
          payload={
            "customer_id": event.payload["customer_id"],
            "risk_level": "high",
            "recommended_actions": ["personal_outreach", "discount_offer"]
          }
        )
        await event_bus.publish(Topics.CUSTOMER, churn_event)
    else:
      print(f"✗ Invalid customer event rejected")
  
  # Subscribe to customer events
  customer_handler = EventHandler(
    handler_func=process_customer_event,
    event_types=[EventType.CUSTOM],
    pillars=["Customer Success"]
  )
  await event_bus.subscribe("cdc.salesforce", customer_handler)
  
  # Start CDC
  await cdc_manager.start_connector("sf_main", ["Account"])
  
  # Simulate customer data changes
  print("Simulating customer data changes...\n")
  
  # Mock customer updates
  customer_updates = [
    {
      "customer_id": "cust_001",
      "account_status": "active",
      "last_activity": datetime.now().isoformat(),
      "health_score": 85
    },
    {
      "customer_id": "cust_002", 
      "account_status": "at_risk",
      "last_activity": (datetime.now() - timedelta(days=30)).isoformat(),
      "health_score": 35  # Low score - will trigger churn prevention
    },
    {
      "customer_id": "cust_003",
      "account_status": "churned",
      "last_activity": (datetime.now() - timedelta(days=60)).isoformat(),
      "health_score": 10
    }
  ]
  
  for update in customer_updates:
    event = Event(
      event_type=EventType.CUSTOM,
      metadata=EventMetadata(
        source_pillar="Customer Success",
        source_agent="cdc_salesforce"
      ),
      payload=update
    )
    await event_bus.publish("cdc.salesforce", event)
  
  # Wait for processing
  await asyncio.sleep(0.5)
  
  # Query lineage for the flow
  lineage_query = LineageQuery(
    pillar="Customer Success",
    direction="both",
    max_depth=5
  )
  
  lineage_data = await lineage_service.query_lineage(lineage_query)
  
  # Results
  print(f"Flow Results:")
  print(f"  Events Processed: {len(processed_events)}")
  print(f"  Schema Validations: {len(customer_updates)} total")
  print(f"  Lineage Nodes: {lineage_data['stats']['total_nodes']}")
  print(f"  Lineage Edges: {lineage_data['stats']['total_edges']}")
  
  # Generate visualization
  mermaid_diagram = LineageVisualizer.generate_mermaid(lineage_data)
  print(f"\nMermaid Diagram Preview:")
  print(mermaid_diagram[:200] + "..." if len(mermaid_diagram) > 200 else mermaid_diagram)
  
  # Cleanup
  await cdc_manager.stop_all()
  await event_bus.close()
  
  print("\n=== Data Mesh Demo Complete ===")


async def main():
  """Run all demonstrations."""
  print("🚀 ADK Data/Integration Mesh Demonstration\n")
  print("This demo shows the complete data mesh implementation including:")
  print("- Event bus with multiple backends")
  print("- Schema registry with validation")  
  print("- CDC connectors for SaaS integration")
  print("- Lineage tracking and impact analysis")
  print("- End-to-end data flow\n")
  
  try:
    await demonstrate_event_bus()
    await demonstrate_schema_registry()
    await demonstrate_cdc_connectors()
    await demonstrate_lineage_tracking()
    await demonstrate_end_to_end_flow()
    
    print("\n✅ All demonstrations completed successfully!")
    
  except Exception as e:
    logger.error(f"Demo failed: {e}")
    raise


if __name__ == "__main__":
  asyncio.run(main())