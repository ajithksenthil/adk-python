# FSA State Memory System - Quick Reference

## 🚀 Quick Start

```bash
# Run enhanced demo (recommended)
./run_enhanced_demo.sh

# Or run basic demo
./run_fsa_system.sh
```

## 📁 File Structure

```
state_memory_service/
├── service.py           # Basic SMS (v1)
├── service_v2.py        # Enhanced SMS with comments
├── models.py            # Basic data models
├── models_v2.py         # Comprehensive state models
├── conflict_resolver.py # CRDT-like operations
├── policy_validator.py  # Policy enforcement
├── agent_sdk.py         # Agent helper utilities
└── README.md           # Documentation

orchestrator_kernel/
├── kernel.py            # Updated with SMS integration
├── state_client.py      # Basic state client
└── state_client_v2.py   # Enhanced state client

tests/
├── test_fsa_integration.py  # Basic integration tests
├── test_enhanced_fsa.py     # Comprehensive feature tests
└── fsa_demo_scenario.py     # Snack supply chain demo
```

## 🔑 Key API Endpoints

### State Management
```bash
# Get state with summary
curl 'http://localhost:8000/state/{tenant}/{fsa}?summary=true'

# Apply delta with validation
curl -X POST http://localhost:8000/state/{tenant}/{fsa}/delta \
  -H "Content-Type: application/json" \
  -d '{"tasks.TASK-001.status": "COMPLETED"}' \
  --data-urlencode "pillar=product" \
  --data-urlencode "aml_level=3"
```

### Comments
```bash
# Add comment to task
curl -X POST http://localhost:8000/tasks/{tenant}/{fsa}/{task_id}/comment \
  --data-urlencode "author=alice" \
  --data-urlencode "body=Need to review API design" \
  --data-urlencode "lineage_id=trace-123"

# Get task comments
curl http://localhost:8000/tasks/{tenant}/{fsa}/{task_id}/comments?limit=10
```

### Agent Ops
```bash
# Update heartbeat
curl -X POST http://localhost:8000/agents/{tenant}/{fsa}/{agent_name}/heartbeat
```

## 📊 State Schema Reference

```python
{
    # Core workflow
    "tasks": {},           # Task graph with status, dependencies
    "active_state": {},    # Sprint, milestone, phase
    
    # Resources
    "resources": {},       # Budget, inventory, capacity
    "artefacts": {},      # URLs, documents, assets
    
    # Performance
    "metrics": {},        # KPIs, rates, scores
    "timers": {},         # Deadlines, renewals
    
    # Governance
    "policy_caps": {},    # Limits and thresholds
    "aml_levels": {},     # Autonomy per pillar
    "vote_rules": {},     # Voting requirements
    
    # Operations
    "agents_online": {},  # Heartbeat tracking
    "lineage_version": 0  # Auto-incrementing
}
```

## 🛠 Common Operations

### For Agents

```python
# Read state in agent
state = await state_client.get_state(tenant_id, fsa_id)
print(f"Current sprint: {state.current_sprint}")
print(f"My tasks: {state.active_tasks}")

# Update task status
delta = {
    "tasks.TASK-001.status": "COMPLETED",
    "metrics.tasks_completed": {"$inc": 1}
}
await state_client.apply_delta(tenant_id, fsa_id, delta, 
                              actor="MyAgent", lineage_id=span_id)

# Add comment
await state_client.add_comment(tenant_id, fsa_id, task_id,
                              author="MyAgent", 
                              body="Analysis complete",
                              lineage_id=span_id)
```

### For Humans

```python
# Check project status
GET /state/{tenant}/{fsa}?summary=true

# Comment on task
POST /tasks/{tenant}/{fsa}/{task}/comment
  author=bob
  body=Please prioritize mobile experience

# View agent availability  
GET /state/{tenant}/{fsa} 
  -> check agents_online timestamps
```

## 🔧 Configuration

### Policy Rules
Edit `policy_validator.py` to add custom rules:
```python
self.add_rule("your_pillar", PolicyRule(
    name="custom_check",
    field="metrics.error_rate",
    condition="< 0.05",
    error_message="Error rate too high"
))
```

### AML Levels
Set in state:
```python
"aml_levels": {
    "growth_engine": 3,      # Medium autonomy
    "customer_success": 2,   # Low autonomy  
    "platform_infra": 5      # Full autonomy
}
```

## 🚨 Troubleshooting

### Redis Connection
```bash
# Check Redis
redis-cli ping

# Start Redis
docker run -p 6379:6379 redis:latest
```

### View Logs
```bash
# SMS logs
tail -f sms.log

# Check state
redis-cli GET "state:v2:tenant:fsa"
```

### API Documentation
```
http://localhost:8000/docs
```

## 📚 More Information

- Basic README: `state_memory_service/README.md`
- Enhanced README: `state_memory_service/ENHANCED_README.md`
- Implementation Summary: `FSA_IMPLEMENTATION_SUMMARY.md`
- Architecture Docs: `contributing/adk_project_overview_and_architecture.md`