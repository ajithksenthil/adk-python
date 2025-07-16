# Enhanced FSA State Memory System

## Overview

The Enhanced FSA State Memory System provides a comprehensive, shared memory for all agents in an AI-native enterprise. It answers four key questions at any moment:

1. **"What are we doing?"** - Tasks, dependencies, and workflow state
2. **"Where are we?"** - Current sprint, milestone, and project phase  
3. **"What do we have?"** - Resources, artifacts, and inventory
4. **"What rules apply?"** - Policies, AML levels, and voting rules

## Key Features

### 1. Comprehensive State Schema

The state includes everything agents need to coordinate effectively:

```json
{
  "tasks": {
    "TASK-001": {
      "status": "RUNNING",
      "assigned_team": "alice/frontend",
      "depends_on": ["TASK-000"],
      "deadline": "2024-08-01T10:00:00Z"
    }
  },
  "active_state": {
    "current_sprint": "Sprint-31",
    "milestone_id": 7,
    "phase": "MVP Development"
  },
  "resources": {
    "cash_balance_usd": 125435.22,
    "inventory": {"servers": 15, "licenses": 100},
    "team_capacity": {"frontend": 0.8, "backend": 1.0}
  },
  "metrics": {
    "ctr_last_24h": 2.7,
    "conversion_rate": 0.045,
    "daily_active_users": 5420
  },
  "policy_caps": {
    "max_po_per_day": 10000,
    "refund_limit": 100
  },
  "aml_levels": {
    "growth_engine": 3,
    "customer_success": 2
  },
  "timers": {
    "next_sprint_planning": "2024-07-20T09:00:00Z",
    "ssl_cert_expiry": "2024-08-15T00:00:00Z"
  },
  "agents_online": {
    "alice/frontend": "2024-07-15T10:30:00Z",
    "MetricsBot": "2024-07-15T10:32:00Z"
  }
}
```

### 2. Human-Agent Discussion Threads

Every task can have a comment thread where humans and agents collaborate:

```bash
# Human adds comment
POST /tasks/{tenant}/{fsa}/{task_id}/comment
{
  "author": "bob",
  "body": "We should A/B test the hero copy",
  "lineage_id": "trace-123"
}

# Agent responds
POST /tasks/{tenant}/{fsa}/{task_id}/comment
{
  "author": "CopyBot",
  "body": "Analysis complete. Variant B shows 15% better engagement",
  "lineage_id": "agent-trace-456"
}
```

Comments include:
- Author (human or agent)
- Timestamp and state version
- Lineage ID for tracing
- Reactions and blocker flags
- Full markdown support

### 3. Advanced Policy Enforcement

Policies are enforced at write-time based on:

- **Field validation**: Inventory must be non-negative, budgets within limits
- **AML constraints**: Transaction limits based on autonomy level
- **Custom rules**: Domain-specific validations

Example policy check:
```python
# AML 1 agent tries to spend $5000 (limit is $1000)
delta = {"resources.cash_balance_usd": {"$inc": -5000}}

# Response: Policy violation: AML 1 cannot approve transactions > $1000
```

### 4. Real-time Agent Coordination

Agents coordinate through shared state:

1. **MetricsBot** updates performance metrics
2. **OptimizerBot** sees improved CTR and increases budget
3. **SchedulerBot** creates review task for 6 hours later
4. **All agents** see the same consistent state

### 5. Task Dependencies and Voting

Complex workflows with dependencies and governance:

```python
# Task with dependencies
"IMPLEMENT_API": {
  "status": "PENDING",
  "depends_on": ["DESIGN_COMPLETE", "SPEC_APPROVED"]
}

# High-impact task requires voting
"MAJOR_REFACTOR": {
  "status": "VOTING",
  "vote_rules": "3_of_5_core+treasurer"
}
```

## Architecture

### State Evolution Flow

```
1. READ: Agent gets state + <2K token summary
   GET /state/{tenant}/{fsa_id}?summary=true

2. THINK: Agent includes state in prompt
   "Current sprint: Sprint-31, Budget: $125K..."

3. ACT: Agent performs action and creates delta
   {"tasks.TASK-001.status": "COMPLETED"}

4. VALIDATE: Policy engine checks constraints
   ✓ Budget remains positive
   ✓ AML level permits action

5. COMMIT: New version written, events published
   Version 42 → 43

6. NOTIFY: Other agents see updated state
   Live-Board highlights changes
```

### Integration Points

```
┌─────────────────────────────────────┐
│      Orchestrator Kernel            │
│  • Reads state before execution     │
│  • Includes summary in prompts      │
│  • Publishes deltas after tools     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    Enhanced State Memory Service    │
│  • Versioned state storage          │
│  • Policy validation                │
│  • Comment threads                  │
│  • Heartbeat tracking               │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Kafka Event Bus             │
│  • state.delta events               │
│  • comment.append events            │
│  • state.updated notifications      │
└─────────────────────────────────────┘
```

## Running the Enhanced System

### Prerequisites

- Python 3.8+
- Redis running on localhost:6379
- Kafka (optional) for async updates

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis
docker run -p 6379:6379 redis:latest

# Start Enhanced SMS
python -m uvicorn state_memory_service.service_v2:app --port 8000

# Run tests
python test_enhanced_fsa.py
```

### Testing the Features

The test suite demonstrates all features:

1. **Comprehensive State**: Full project state with all fields
2. **Task Management**: Status updates, dependencies
3. **Resource Management**: Budget updates with policy checks
4. **Comment System**: Human-agent discussion threads
5. **Agent Coordination**: Multiple agents working together
6. **Voting Workflows**: Governance with comments
7. **Heartbeat Monitoring**: Agent availability tracking

## API Reference

### State Operations

- `GET /state/{tenant_id}/{fsa_id}` - Get full state
- `GET /state/{tenant_id}/{fsa_id}?summary=true` - Get summary only
- `POST /state/{tenant_id}/{fsa_id}` - Set complete state
- `POST /state/{tenant_id}/{fsa_id}/delta` - Apply delta with validation

### Comment Operations

- `POST /tasks/{tenant_id}/{fsa_id}/{task_id}/comment` - Add comment
- `GET /tasks/{tenant_id}/{fsa_id}/{task_id}/comments` - Get comments

### Agent Operations

- `POST /agents/{tenant_id}/{fsa_id}/{agent_name}/heartbeat` - Update heartbeat

## Best Practices

### 1. State Design

- Keep state flat where possible
- Use dot notation for nested updates: `"tasks.TASK-001.status"`
- Include timestamps for audit trails
- Set reasonable size limits (target <100KB)

### 2. Comment Integration

- Agents should check comments before acting on tasks
- Use `@blocker` in comments for critical issues
- Include lineage IDs for full traceability
- Keep comments concise and actionable

### 3. Policy Configuration

- Define clear AML levels per pillar
- Set reasonable caps that prevent accidents
- Use validation rules that fail fast
- Log all policy violations for review

### 4. Performance Optimization

- Use state summaries in prompts (<2K tokens)
- Batch related updates in single deltas
- Cache state locally during request processing
- Monitor state size and prune completed tasks

## Extending the System

### Adding Custom Fields

```python
# In your state schema
"custom_fields": {
    "ml_models": {
        "churn_predictor_v5": {
            "accuracy": 0.87,
            "last_trained": "2024-07-01"
        }
    },
    "compliance_flags": {
        "gdpr_compliant": true,
        "hipaa_audit_date": "2024-06-15"
    }
}
```

### Custom Validation Rules

```python
# In policy_validator.py
self.add_rule("ml_platform", PolicyRule(
    name="model_accuracy_threshold",
    field="ml_models.*.accuracy",
    condition=">= 0.80",
    error_message="Model accuracy must be >= 80%"
))
```

### Integration with External Systems

```python
# Slack bridge for comments
@app.post("/webhook/slack")
async def slack_webhook(payload: dict):
    # Map Slack thread to task_id
    task_id = map_thread_to_task(payload["thread_ts"])
    
    # Add as comment
    await sms.add_comment(
        tenant_id, fsa_id, task_id,
        Comment(
            author=f"slack/{payload['user']}",
            body_md=payload["text"],
            lineage_id=f"slack-{payload['ts']}"
        )
    )
```

## Benefits

1. **Single Source of Truth**: All agents see consistent state
2. **Complete Context**: Everything needed for decisions in one place
3. **Human-AI Collaboration**: Seamless discussion threads
4. **Governance Built-in**: Policies and voting workflows
5. **Full Auditability**: Version history and lineage tracking
6. **Real-time Coordination**: Agents react to state changes immediately

## Conclusion

The Enhanced FSA State Memory System provides the "shared consciousness" that enables truly autonomous AI agent teams. By maintaining comprehensive state with human discussion threads, it ensures that agents never lose context, always respect policies, and can collaborate effectively with both humans and other agents.

This is the foundation for building AI-native enterprises where agent teams can handle complex, long-running projects with minimal human oversight while maintaining full governance and auditability.