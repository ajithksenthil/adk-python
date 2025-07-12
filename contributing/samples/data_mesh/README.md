# Data/Integration Mesh

This sample demonstrates a comprehensive Data/Integration Mesh implementation for ADK agents, providing event-driven architecture, schema validation, change data capture, and lineage tracking as outlined in the enterprise reference architecture.

## Overview

The Data/Integration Mesh provides:

1. **Event Bus** - Pub/sub messaging with multiple backends (Memory, Kafka, Pub/Sub)
2. **Schema Registry** - Event schema validation and evolution
3. **CDC Connectors** - Real-time data capture from SaaS systems
4. **Lineage Service** - Data flow tracking and impact analysis

## Architecture Components

### 1. Event Bus (`event_bus.py`)

The event bus enables decoupled communication between agents and systems:

- **Multi-Backend Support**: In-memory, Kafka, Google Pub/Sub
- **Event Metadata**: Trace IDs, lineage tracking, priority handling
- **Handler Filtering**: Event type, pillar, and priority filters
- **Standard Topics**: Pillar-based and system topics

#### Key Classes:
- `Event` - Base event with metadata and payload
- `EventBus` - Abstract interface for all implementations
- `EventHandler` - Configurable event processing
- `EventBusFactory` - Factory for creating bus instances

### 2. Schema Registry (`schema_registry.py`)

Validates and manages event schemas:

- **JSON Schema Support** - Full JSON Schema Draft 7 support
- **Schema Evolution** - Backward/forward compatibility checking
- **Version Management** - Multiple schema versions per subject
- **Validation** - Runtime event validation against schemas

#### Key Classes:
- `SchemaRegistry` - Abstract registry interface
- `LocalSchemaRegistry` - In-memory registry for development
- `ConfluentSchemaRegistry` - Integration with Confluent Schema Registry
- `SchemaEvolutionHelper` - Tools for schema evolution

### 3. CDC Connectors (`cdc_connectors.py`)

Real-time data capture from SaaS systems:

- **Multiple Sources**: Salesforce, Stripe, NetSuite, Zendesk
- **Operation Types**: Insert, Update, Delete, Snapshot
- **Offset Management** - Reliable change tracking
- **Error Handling** - Retry logic and error recovery

#### Key Classes:
- `CDCConnector` - Abstract base for all connectors
- `CDCManager` - Manages multiple connectors
- `SalesforceCDCConnector` - Salesforce integration
- `StripeCDCConnector` - Stripe events integration

### 4. Lineage Service (`lineage_service.py`)

Tracks data flow and dependencies:

- **Graph Structure** - NetworkX-based lineage graph
- **Node Types** - Agents, tools, data sources, decisions
- **Edge Types** - Reads, writes, triggers, dependencies
- **Query Interface** - Flexible lineage queries
- **Impact Analysis** - Change impact assessment

#### Key Classes:
- `LineageService` - Core lineage tracking service
- `LineageNode` - Graph nodes (agents, tools, data)
- `LineageEdge` - Graph edges (relationships)
- `LineageQuery` - Query parameters for lineage search

## Usage

### Basic Event Bus Setup

```python
from contributing.samples.data_mesh import (
    EventBusFactory,
    Event,
    EventHandler,
    EventMetadata,
    EventType,
    Topics
)

# Create event bus
event_bus = EventBusFactory.create("memory")

# Create handler
async def handle_growth_events(event: Event):
    print(f"Processing: {event.event_type.value}")

handler = EventHandler(
    handler_func=handle_growth_events,
    event_types=[EventType.CAMPAIGN_LAUNCH]
)

# Subscribe and publish
await event_bus.subscribe(Topics.GROWTH, handler)

event = Event(
    event_type=EventType.CAMPAIGN_LAUNCH,
    metadata=EventMetadata(
        source_pillar="Growth Engine",
        source_agent="marketing_agent"
    ),
    payload={"campaign_id": "camp_001"}
)

await event_bus.publish(Topics.GROWTH, event)
```

### Schema Registry Usage

```python
from contributing.samples.data_mesh import (
    LocalSchemaRegistry,
    SchemaFormat
)

registry = LocalSchemaRegistry()

# Register schema
lead_schema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "lead_id": {"type": "string"},
        "email": {"type": "string", "format": "email"},
        "score": {"type": "integer", "minimum": 0, "maximum": 100}
    },
    "required": ["lead_id", "email"]
}

version = await registry.register_schema(
    "event.lead.generated",
    lead_schema,
    SchemaFormat.JSON_SCHEMA
)

# Validate data
data = {"lead_id": "123", "email": "user@example.com", "score": 85}
is_valid = await registry.validate("event.lead.generated", data)
```

### CDC Connector Setup

```python
from contributing.samples.data_mesh import (
    CDCManager,
    SalesforceCDCConnector
)

# Create CDC manager
event_bus = EventBusFactory.create("memory")
cdc_manager = CDCManager(event_bus)

# Register Salesforce connector
connector = SalesforceCDCConnector(
    connector_id="sf_main",
    event_bus=event_bus,
    pillar="Customer Success",
    instance_url="https://company.salesforce.com",
    access_token="your_token"
)

cdc_manager.register_connector(connector)

# Start syncing
await cdc_manager.start_connector("sf_main", ["Contact", "Account"])
```

### Lineage Tracking

```python
from contributing.samples.data_mesh import (
    LineageService,
    LineageQuery,
    LineageNodeType
)

lineage = LineageService()

# Track agent actions
await lineage.add_node(
    node_id="agent:marketing",
    node_type=LineageNodeType.AGENT,
    name="Marketing Agent",
    pillar="Growth Engine"
)

await lineage.track_tool_invocation(
    agent_id="agent:marketing",
    tool_name="email_sender",
    trace_id="trace_001",
    inputs={"recipients": 100},
    outputs={"sent": 95},
    pillar="Growth Engine"
)

# Query lineage
query = LineageQuery(
    node_id="agent:marketing",
    direction="downstream",
    max_depth=5
)

results = await lineage.query_lineage(query)
```

## Production Deployments

### Kafka Event Bus

```python
# Production Kafka setup
event_bus = EventBusFactory.create(
    "kafka",
    bootstrap_servers="kafka1:9092,kafka2:9092",
    consumer_group="adk-agents"
)
```

### Confluent Schema Registry

```python
# Production schema registry
from contributing.samples.data_mesh import ConfluentSchemaRegistry

registry = ConfluentSchemaRegistry("http://schema-registry:8081")
```

### CDC with Real APIs

```python
# Real Salesforce CDC
connector = SalesforceCDCConnector(
    connector_id="sf_prod",
    event_bus=event_bus,
    pillar="Customer Success",
    instance_url="https://yourcompany.salesforce.com",
    access_token=os.getenv("SALESFORCE_TOKEN")
)

# Real Stripe CDC
stripe_connector = StripeCDCConnector(
    connector_id="stripe_prod",
    event_bus=event_bus,
    pillar="Growth Engine",
    api_key=os.getenv("STRIPE_API_KEY")
)
```

## Event Types by Pillar

### Mission & Governance
- `POLICY_UPDATE` - Policy changes
- `BUDGET_APPROVAL` - Budget approvals
- `RISK_ALERT` - Risk notifications

### Product & Experience
- `FEATURE_RELEASE` - Feature deployments
- `CODE_MERGE` - Code merges
- `QA_RESULT` - Test results

### Growth Engine
- `CAMPAIGN_LAUNCH` - Marketing campaigns
- `LEAD_GENERATED` - New leads
- `DEAL_WON` - Sales wins

### Customer Success
- `TICKET_CREATED` - Support tickets
- `REFUND_PROCESSED` - Refunds
- `CHURN_RISK` - Churn alerts

### Resource & Supply
- `INVENTORY_UPDATE` - Inventory changes
- `PO_CREATED` - Purchase orders
- `SHIPMENT_TRACKED` - Shipping updates

### People & Culture
- `CANDIDATE_APPLIED` - Job applications
- `EMPLOYEE_ONBOARDED` - New hires
- `SURVEY_COMPLETED` - Surveys

### Intelligence & Improvement
- `METRIC_COLLECTED` - Analytics
- `EXPERIMENT_STARTED` - A/B tests
- `MODEL_DEPLOYED` - ML models

### Platform & Infra
- `SERVICE_DEPLOYED` - Service deployments
- `ALERT_TRIGGERED` - System alerts
- `SCALING_EVENT` - Auto-scaling

## Topic Naming Conventions

```python
# Pillar topics
Topics.MISSION      # pillar.mission
Topics.PRODUCT      # pillar.product
Topics.GROWTH       # pillar.growth
Topics.CUSTOMER     # pillar.customer

# System topics
Topics.ALERTS       # system.alerts
Topics.METRICS      # system.metrics
Topics.AUDIT        # system.audit

# CDC topics
Topics.CDC_SALESFORCE  # cdc.salesforce
Topics.CDC_STRIPE      # cdc.stripe
Topics.CDC_ZENDESK     # cdc.zendesk
```

## Schema Evolution Examples

### Adding Optional Field (Backward Compatible)

```python
from contributing.samples.data_mesh import SchemaEvolutionHelper

# Original schema
old_schema = {
    "properties": {
        "name": {"type": "string"},
        "email": {"type": "string"}
    },
    "required": ["name", "email"]
}

# Add optional field
new_schema = SchemaEvolutionHelper.add_optional_field(
    old_schema,
    "phone",
    {"type": "string"}
)
```

### Adding Required Field with Default

```python
new_schema = SchemaEvolutionHelper.add_required_field_with_default(
    old_schema,
    "created_at",
    {"type": "string", "format": "date-time"},
    datetime.now().isoformat()
)
```

## Running the Example

1. **Run the complete demonstration**:
   ```bash
   cd contributing/samples/data_mesh
   python data_mesh_example.py
   ```

2. **Individual components**:
   ```bash
   # Event bus only
   python -c "
   import asyncio
   from data_mesh_example import demonstrate_event_bus
   asyncio.run(demonstrate_event_bus())
   "
   
   # Schema registry only
   python -c "
   import asyncio
   from data_mesh_example import demonstrate_schema_registry
   asyncio.run(demonstrate_schema_registry())
   "
   ```

## Integration with Control Plane

The Data/Integration Mesh integrates with the Control Plane:

```python
from contributing.samples.control_plane import ControlPlaneAgent
from contributing.samples.data_mesh import LineageService

# Create lineage-aware agent
lineage = LineageService()
controlled_agent = ControlPlaneAgent(
    wrapped_agent=base_agent,
    pillar="Growth Engine",
    lineage_service=lineage  # Track agent actions
)
```

## Monitoring and Observability

### Event Metrics

```python
# Track event processing metrics
async def metrics_handler(event: Event):
    metrics.increment("events.processed", tags={
        "pillar": event.metadata.source_pillar,
        "type": event.event_type.value
    })

handler = EventHandler(handler_func=metrics_handler)
await event_bus.subscribe("system.metrics", handler)
```

### Lineage Analytics

```python
# Analyze lineage patterns
stats = {}
for pillar in ["Growth Engine", "Customer Success"]:
    query = LineageQuery(pillar=pillar, direction="both")
    results = await lineage.query_lineage(query)
    stats[pillar] = results["stats"]

print(f"Cross-pillar dependencies: {stats}")
```

## Best Practices

### Event Design
1. **Immutable Events** - Events should be immutable records
2. **Rich Metadata** - Include trace IDs and lineage information
3. **Schema First** - Define schemas before publishing events
4. **Idempotent Handling** - Handlers should be idempotent

### Schema Management
1. **Backward Compatibility** - Maintain compatibility when possible
2. **Version Strategy** - Use semantic versioning for schemas
3. **Documentation** - Document schema changes and impacts
4. **Testing** - Test schema changes with real data

### CDC Operations
1. **Incremental Sync** - Use incremental sync to minimize load
2. **Error Handling** - Implement robust error handling and retries
3. **Monitoring** - Monitor CDC lag and error rates
4. **Rate Limiting** - Respect API rate limits

### Lineage Tracking
1. **Comprehensive Coverage** - Track all data transformations
2. **Performance** - Avoid impacting system performance
3. **Retention** - Implement data retention policies
4. **Privacy** - Be mindful of sensitive data in lineage

## Troubleshooting

### Event Bus Issues

**Events not being received:**
- Check subscription filters (event types, pillars)
- Verify handler registration
- Check event bus connectivity

**High memory usage:**
- Use production backends (Kafka/Pub/Sub) instead of memory
- Implement message cleanup policies
- Monitor handler processing speed

### Schema Validation Failures

**Compatibility errors:**
- Review schema evolution guidelines
- Use SchemaEvolutionHelper for safe changes
- Test schema changes in development

**Validation errors:**
- Check event payload format
- Verify required fields are present
- Review field type constraints

### CDC Connector Issues

**Connector not syncing:**
- Check source system connectivity
- Verify authentication credentials
- Review CDC connector logs
- Check offset management

**Missing changes:**
- Verify offset positioning
- Check source system change logs
- Review filter criteria

### Lineage Performance

**Slow queries:**
- Add indexes for commonly queried fields
- Limit query depth and scope
- Implement result caching
- Use graph database for large datasets

## Related Documentation

- [Control Plane Implementation](../control_plane/README.md)
- [Reference Architecture](../react_supabase/ARCHITECTURE.md)
- [Kafka Documentation](https://kafka.apache.org/documentation/)
- [JSON Schema Specification](https://json-schema.org/)
- [NetworkX Documentation](https://networkx.org/)

## Security Considerations

1. **Event Encryption** - Encrypt sensitive event payloads
2. **Access Control** - Implement topic-level permissions
3. **Audit Trail** - Log all data access and modifications
4. **Data Privacy** - Follow data protection regulations
5. **Network Security** - Use TLS for all connections

## Performance Optimization

1. **Batching** - Batch events for better throughput
2. **Compression** - Use message compression for large payloads
3. **Partitioning** - Partition topics by pillar or tenant
4. **Caching** - Cache frequently accessed schemas and lineage
5. **Connection Pooling** - Reuse connections to external systems