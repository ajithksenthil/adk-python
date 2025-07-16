# MemCube System Overview

## Quick Navigation

1. [What is MemCube?](#what-is-memcube)
2. [How It Works](#how-it-works)
3. [Integration with FSA](#integration-with-fsa)
4. [Key Concepts](#key-concepts)
5. [Getting Started](#getting-started)

## What is MemCube?

MemCube is a **persistent memory system** for AI agents that stores knowledge, experiences, and insights across sessions. Think of it as the "long-term memory" that complements FSA's "working memory".

### FSA vs MemCube

| Aspect | FSA (State Memory) | MemCube (Knowledge Memory) |
|--------|-------------------|---------------------------|
| **Purpose** | Live coordination | Persistent knowledge |
| **Lifespan** | Per-project session | Permanent |
| **Content** | Tasks, metrics, state | Experiences, patterns, insights |
| **Access** | Real-time, slice-based | Query-based, scheduled |
| **Size** | ~100KB per project | Unlimited (with governance) |

## How It Works

### 1. Memory Flow for Agents

```
┌─────────────────────────────────────────────────────────┐
│                     Agent Workflow                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Agent starts task                                  │
│     ↓                                                  │
│  2. Read FSA state (current context)                   │
│     ↓                                                  │
│  3. Query MemCube (relevant knowledge) ←───────┐       │
│     ↓                                          │       │
│  4. Enhance prompt with memories               │       │
│     ↓                                          │       │
│  5. Execute task with LLM                      │       │
│     ↓                                          │       │
│  6. Update FSA state (coordination)            │       │
│     ↓                                          │       │
│  7. Store new experiences in MemCube ──────────┘       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2. Memory Types

```
┌────────────────┬────────────────┬─────────────────┐
│   PLAINTEXT    │   ACTIVATION   │   PARAMETER     │
├────────────────┼────────────────┼─────────────────┤
│ • Readable     │ • KV Cache     │ • Model Weights │
│ • ≤ 64KB       │ • ≤ 256KB      │ • LoRA Deltas   │
│ • Markdown/JSON│ • Base64       │ • Compressed    │
│ • Most Common  │ • Fast Context │ • Fine-tuning   │
└────────────────┴────────────────┴─────────────────┘
```

### 3. Memory Lifecycle

```
     NEW → ACTIVE → STALE → ARCHIVED → EXPIRED
      ↓       ↓        ↓         ↓         ↓
   Created  Used    Unused   Compressed  Deleted
            Often   30 days   After TTL   Auto
```

## Integration with FSA

### Combined Architecture

```
┌──────────────────────────────────────────────────────┐
│                  AI Agent System                      │
├────────────────────┬─────────────────────────────────┤
│                    │                                  │
│   FSA (Live)       │        MemCube (Persistent)     │
│                    │                                  │
│ • Current Tasks    │     • Past Experiences          │
│ • Active Metrics   │     • Learned Patterns          │
│ • Online Agents    │     • Domain Knowledge          │
│ • Resource State   │     • User Insights             │
│                    │                                  │
│ "What's happening" │     "What we've learned"        │
│                    │                                  │
└────────────────────┴─────────────────────────────────┘
                    ↓
            Intelligent Agents
```

### Example: Design Agent Workflow

```python
# 1. Agent reads current design task from FSA
fsa_state = await fsa_client.get_slice(
    tenant_id="acme", 
    fsa_id="project-x",
    slice_pattern="task:DESIGN_*"
)
# Returns: Current design tasks, status, deadlines

# 2. Agent gets relevant design knowledge from MemCube
memories = await memcube.get_memories_for_task(
    agent_id="design-bot",
    task_id="DESIGN_001", 
    tags=["figma", "components", "design-system"]
)
# Returns: Past design patterns, user preferences, lessons

# 3. Agent works with combined context
result = await agent.design_component(
    task=fsa_state.tasks["DESIGN_001"],
    knowledge=memories
)

# 4. Update both systems
# FSA: Task completed
await fsa_client.apply_delta({
    "tasks.DESIGN_001.status": "DONE"
})

# MemCube: New learning
await memcube.store_experience(
    "design-pattern",
    "Card components need 16px padding for mobile"
)
```

## Key Concepts

### 1. Memory Governance

Each memory has rules about who can access it:

```yaml
governance:
  read_roles: ["MEMBER", "AGENT"]     # Who can read
  write_roles: ["AGENT"]              # Who can modify
  ttl_days: 365                       # When to expire
  shareable: true                     # Can be shared in marketplace
  license: "MIT"                      # Usage license
  pii_tagged: false                   # Contains personal data
```

### 2. Memory Selection Algorithm

When an agent requests memories, the system scores each one:

```
Score = 40% × Tag Match
      + 20% × Recency (when last used)
      + 20% × Frequency (how often used)
      + 10% × Priority (HOT/WARM/COLD)
      + 10% × Task Relevance
```

### 3. Storage Optimization

MemCube automatically chooses the best storage method:

```
if size < 4KB:
    → Store inline in database (fastest)
elif size < 64KB:
    → Compress and store in database
else:
    → Store in blob storage (S3/GCS)
```

### 4. Token Budget Management

Agents specify how many tokens they can use for memories:

```python
memories = await scheduler.schedule_memories(
    agent_id="my-agent",
    task_id="TASK-123",
    token_budget=2000,  # Max tokens for memories
    prefer_hot=True     # Prioritize frequently used
)
# Returns memories that fit within 2000 tokens
```

## Getting Started

### For Agent Developers

1. **Basic Integration**
```python
from memcube_system.agent_sdk import AgentMemoryExtension

async with AgentMemoryExtension(
    agent_id="my-agent",
    project_id="my-project"
) as memory:
    # Automatically enhance prompts
    enhanced = await memory.enhance_prompt(
        "Build a React component",
        task_id="TASK-123"
    )
    
    # Store learnings
    memory.capture_experience(
        "react-tip",
        "Always memoize expensive computations"
    )
```

2. **Advanced Integration**
```python
from memcube_system.agent_sdk import create_memory_agent

# Create memory-enhanced agent class
MemoryAgent = create_memory_agent(
    YourBaseAgent,
    project_id="my-project"
)

# Use it normally - memory is automatic
agent = MemoryAgent()
await agent.run_task("Build feature")
```

### For System Administrators

1. **Start MemCube Service**
```bash
# Configure
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-key"

# Run
python -m uvicorn memcube_system.service:app --port 8002
```

2. **Monitor Health**
```bash
# Check service
curl http://localhost:8002/health

# Run maintenance
curl -X POST http://localhost:8002/admin/lifecycle
```

### For Data Scientists

**Create Memory Packs**
```python
# Bundle domain knowledge
pack = await marketplace.create_pack(
    title="React Best Practices 2024",
    memories=["mem-001", "mem-002", ...],
    price_cents=999
)

# Agents can import and use immediately
await marketplace.import_pack(pack.id)
```

## Common Use Cases

### 1. Design System Memory
```python
# Store design decisions
await memory.store_experience(
    "color-palette",
    "Primary blue: #0066CC, works well with dark mode"
)

# Retrieve for new designs
memories = await memory.get_memories(tags=["colors", "design-system"])
```

### 2. Error Pattern Learning
```python
# Capture error patterns
memory.capture_experience(
    "error-pattern",
    "TypeError in React: usually missing null check in map()",
    tags=["errors", "react", "debugging"]
)
```

### 3. Performance Insights
```python
# Store performance learnings
await memory.generate_insight(
    "Database queries slow down after 1M records without index",
    evidence=["perf-test-001"],
    sentiment=-0.5  # Negative finding
)
```

### 4. Team Knowledge Sharing
```python
# Create knowledge pack
pack = await publisher.create_pack(
    title="Our Team's React Patterns",
    description="Curated patterns from 6 months of development",
    memory_ids=team_memory_ids,
    price_cents=0  # Free for team
)
```

## Best Practices

### DO ✅
- Store learnings immediately after tasks
- Tag memories descriptively for better retrieval
- Set appropriate governance rules
- Use memory packs for knowledge sharing
- Monitor usage patterns to optimize

### DON'T ❌
- Store sensitive data without PII tagging
- Create memories larger than necessary
- Ignore TTL settings (memories accumulate)
- Store duplicate knowledge
- Use ACTIVATION type unless caching KV

## Troubleshooting

### Memory Not Retrieved?
1. Check tags match
2. Verify token budget
3. Ensure memory not archived
4. Check governance permissions

### Storage Issues?
1. Verify Supabase connection
2. Check blob storage config for large files
3. Ensure proper permissions
4. Monitor storage quotas

### Performance Slow?
1. Use slice queries (not full retrieval)
2. Enable caching (5min default)
3. Optimize memory selection criteria
4. Consider HOT priority for frequent memories

## Next Steps

- 📖 Read the [Architecture Guide](./ARCHITECTURE.md) for deep dive
- 🚀 Try the [Integration Demo](./test_memcube_integration.py)
- 🔗 See [FSA Integration Example](./memcube_fsa_integration_demo.py)
- 📚 Browse [API Reference](./ARCHITECTURE.md#api-endpoints-reference)