# FSA-Based State Memory Service

This implements a Finite State Automaton (FSA) based memory system that provides a single, authoritative project state for all agents in the AI-native enterprise architecture.

## Overview

The State Memory Service (SMS) addresses a critical challenge in multi-agent systems: maintaining consistent, shared state across all agents while enforcing policies and tracking changes. It's inspired by the SciBORG paper's findings that FSA-based memory significantly improves agent success rates on complex tasks.

## Architecture

```
┌─────────────────────────────────────────┐
│         Orchestrator Kernel             │
│  ┌─────────────┐    ┌────────────────┐ │
│  │ Read State  │    │ Write Deltas   │ │
│  └──────┬──────┘    └───────┬────────┘ │
└─────────┼───────────────────┼──────────┘
          │                   │
          ▼                   ▼
┌─────────────────────────────────────────┐
│      State Memory Service (SMS)         │
│  ┌─────────────┐    ┌────────────────┐ │
│  │   Redis KV  │    │ Policy Valid.  │ │
│  └─────────────┘    └────────────────┘ │
│         ▲                   │           │
│         └───────────────────┘           │
│              Kafka Consumer             │
└─────────────────────────────────────────┘
          ▲
          │ state.delta events
┌─────────┴───────────────────────────────┐
│         Kafka Event Bus                 │
└─────────────────────────────────────────┘
```

## Features

1. **Versioned State Storage**: Every state change creates a new version, enabling rollback and audit trails
2. **CRDT-like Conflict Resolution**: Supports operations like `$inc`, `$push`, `$addToSet` for concurrent updates
3. **Policy Validation**: Enforces business rules and AML (Autonomy Maturity Level) constraints
4. **Kafka Integration**: Asynchronous state updates via event streaming
5. **Token-Limited Summaries**: Provides concise state context for LLM prompts
6. **REST API**: Simple HTTP interface for state operations

## Quick Start

### Prerequisites

- Python 3.8+
- Redis (running on localhost:6379)
- Kafka (optional, for async updates)

### Installation

```bash
# Install dependencies
pip install -r state_memory_service/requirements.txt
```

### Running the Service

```bash
# Start Redis (if not running)
docker run -p 6379:6379 redis:latest

# Start the State Memory Service
python -m uvicorn state_memory_service.service:app --reload
```

The service will be available at `http://localhost:8000`

### API Endpoints

- `GET /health` - Health check
- `GET /state/{tenant_id}/{fsa_id}` - Retrieve current state
- `POST /state/{tenant_id}/{fsa_id}` - Set complete state
- `POST /state/{tenant_id}/{fsa_id}/delta` - Apply state delta
- `POST /validate/delta` - Validate delta without applying

## Integration with Orchestrator Kernel

The Orchestrator Kernel has been enhanced to:

1. **Read State Before Execution**: Fetches current FSA state and includes a summary in agent prompts
2. **Publish State Deltas**: After tool execution, publishes state changes to Kafka
3. **Track State Versions**: Records state version transitions for observability

Example integration in the kernel:

```python
# Configuration
config = KernelConfig(
    enable_state_memory=True,
    state_memory_url="http://localhost:8000"
)

# State is automatically fetched and included in agent context
```

## Running the Demo

### 1. Integration Tests

Run comprehensive tests of all components:

```bash
python test_fsa_integration.py
```

This tests:
- Basic state operations
- Policy validation
- Orchestrator integration
- Concurrent updates

### 2. Demo Scenario

Run a realistic snack supply chain scenario:

```bash
# Terminal 1: Start SMS
python -m uvicorn state_memory_service.service:app

# Terminal 2: Run demo
python fsa_demo_scenario.py
```

The demo shows:
- Multiple agents reading shared state
- State updates with policy enforcement
- AML-based access control
- Coordinated multi-agent workflow

## State Schema Example

```json
{
  "task_status": {
    "TASK-001": "COMPLETED",
    "TASK-002": "IN_PROGRESS"
  },
  "inventory": {
    "item_a": 100,
    "item_b": 250
  },
  "budget_remaining": 50000,
  "metadata": {
    "last_updated": "2024-01-20T10:30:00Z",
    "updated_by": "procurement_agent"
  }
}
```

## Policy Configuration

Policies are defined in `policy_validator.py`:

```python
# Inventory must be non-negative
PolicyRule(
    name="inventory_non_negative",
    field="inventory.*",
    condition=">= 0",
    error_message="Inventory cannot be negative"
)

# AML-based transaction limits
if aml_level <= 3 and amount > 1000:
    return "AML 3 cannot approve transactions > $1000"
```

## Benefits

1. **Consistency**: Single source of truth for project state
2. **Auditability**: Complete history of state changes
3. **Safety**: Policy enforcement prevents invalid states
4. **Scalability**: Async updates via Kafka
5. **Simplicity**: Clean API for agents to read/write state

## Next Steps

- Add Neo4j for state transition graphs
- Implement state compaction for long-running projects
- Add WebSocket subscriptions for real-time updates
- Create specialized state schemas per pillar
- Add state snapshot/restore capabilities