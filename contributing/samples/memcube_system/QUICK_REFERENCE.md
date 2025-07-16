# MemCube Quick Reference Card

## 🚀 Quick Start

```python
# 1. Basic Usage
from memcube_system.agent_sdk import AgentMemoryExtension

async with AgentMemoryExtension("my-agent", "project-123") as memory:
    # Get memories for your task
    enhanced_prompt = await memory.enhance_prompt(
        "Build a feature", 
        task_id="TASK-001"
    )
    
    # Store what you learned
    memory.capture_experience(
        "feature-tip",
        "Always validate inputs"
    )
```

## 📝 Common Operations

### Store a Memory
```python
memory_id = await client.store_experience(
    agent_id="bot-001",
    project_id="proj-123",
    label="react-pattern",
    content="Use hooks for state",
    tags=["react", "frontend"]
)
```

### Query Memories
```python
memories = await client.get_memories_for_task(
    agent_id="bot-001",
    task_id="TASK-456",
    project_id="proj-123",
    tags=["react"],
    token_budget=2000  # Stay within context limit
)
```

### Submit Insight
```python
await client.submit_insight(
    agent_id="bot-001",
    project_id="proj-123",
    insight="Users prefer dark mode at night",
    evidence=["analytics-001"],
    sentiment=0.8  # Positive
)
```

## 🔧 REST API Endpoints

### Memory Operations
```bash
# Create
POST /memories
{
  "project_id": "proj-123",
  "label": "my-memory",
  "content": "Knowledge here",
  "type": "PLAINTEXT",
  "created_by": "agent-001"
}

# Read
GET /memories/{memory_id}

# Update (creates new version)
PUT /memories/{memory_id}
{
  "content": "Updated knowledge",
  "updated_by": "agent-001"
}

# Archive
DELETE /memories/{memory_id}
```

### Query & Schedule
```bash
# Query memories
POST /memories/query
{
  "project_id": "proj-123",
  "tags": ["react", "hooks"],
  "type_filter": "PLAINTEXT",
  "limit": 10
}

# Schedule for agent (with token budget)
POST /memories/schedule
{
  "agent_id": "bot-001",
  "task_id": "TASK-789",
  "project_id": "proj-123",
  "need_tags": ["react"],
  "token_budget": 4000
}
```

### Insights
```bash
POST /insights?project_id=proj-123&created_by=agent-001
{
  "insight": "Pattern discovered",
  "evidence_refs": ["task-001", "task-002"],
  "sentiment": 0.5
}
```

## 🏗️ Memory Structure

```python
MemCube = {
    # Header (metadata)
    "header": {
        "id": "uuid",
        "project_id": "proj-123",
        "label": "descriptive-name",
        "type": "PLAINTEXT|ACTIVATION|PARAMETER",
        "created_by": "agent-001",
        "priority": "HOT|WARM|COLD",
        "governance": {
            "read_roles": ["MEMBER", "AGENT"],
            "write_roles": ["AGENT"],
            "ttl_days": 365,
            "shareable": true
        }
    },
    # Payload (content)
    "payload": {
        "type": "PLAINTEXT",
        "content": "The actual memory content",
        "token_count": 42
    }
}
```

## 🎯 Memory Types

| Type | Size Limit | Use Case | Format |
|------|------------|----------|---------|
| PLAINTEXT | ≤64KB | Knowledge, patterns | Markdown/JSON |
| ACTIVATION | ≤256KB | KV cache | Base64 |
| PARAMETER | Varies | Model weights | Compressed |

## 🔄 Memory Lifecycle

```
NEW (just created)
 ↓
ACTIVE (being used) 
 ↓
STALE (not used 30d)
 ↓
ARCHIVED (compressed)
 ↓
EXPIRED (deleted after TTL)
```

## 📊 Selection Algorithm

```python
score = (0.4 * tag_relevance +
         0.2 * recency +
         0.2 * frequency +
         0.1 * priority +
         0.1 * task_context)
```

## 🏪 Marketplace

```python
# Create pack
pack = await marketplace.create_pack(
    author_id="user-123",
    title="React Patterns",
    memory_ids=["mem-1", "mem-2"],
    price_cents=500
)

# Search packs
packs = await marketplace.search_packs(
    query="react performance",
    max_price_cents=1000
)

# Import pack
memories = await marketplace.import_pack(
    pack_id="pack-001",
    project_id="proj-123"
)
```

## 🔗 Integration Patterns

### 1. Simple Enhancement
```python
# Just enhance prompts
enhanced = await memory.enhance_prompt(prompt, task_id)
```

### 2. Full Integration
```python
# Create enhanced agent class
MemAgent = create_memory_agent(BaseAgent, project_id="proj-123")

async with MemAgent() as agent:
    await agent.process_task()  # Memory automatic
```

### 3. Hook-Based
```python
hooks = MemoryHooks(memory_extension)
agent.add_hook("pre_task", hooks.pre_task_hook)
agent.add_hook("post_task", hooks.post_task_hook)
```

## 🚨 Common Issues

### Not Getting Memories?
- Check token budget (too low?)
- Verify tags match
- Ensure memories not archived
- Check governance permissions

### Slow Performance?
- Use specific tags (not wildcards)
- Reduce token budget if too high
- Enable caching (default 5min)
- Check memory priorities

### Storage Errors?
- Verify size limits (64KB for PLAINTEXT)
- Check Supabase connection
- Ensure proper governance settings

## 🛠️ Environment Variables

```bash
# Required
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-key

# Optional
BLOB_STORAGE_URL=s3://bucket
MARKETPLACE_API=https://api.market.com
CACHE_TTL=300  # seconds
```

## 📈 Best Practices

1. **Tag Thoughtfully**: Use hierarchical tags like `frontend/react/hooks`
2. **Set Token Budgets**: Start with 2000-4000 tokens
3. **Capture Immediately**: Store learnings right after tasks
4. **Use Governance**: Set appropriate read/write roles
5. **Monitor Usage**: Track which memories are HOT vs COLD
6. **Share Knowledge**: Create packs for team learning

## 🔍 Debugging

```python
# Check memory details
memory = await storage.get_memory("mem-123")
print(f"Priority: {memory.header.priority}")
print(f"Usage: {memory.header.usage_hits}")
print(f"Last used: {memory.header.last_used}")

# Test selection
memories = await scheduler.schedule_request(
    MemoryScheduleRequest(
        agent_id="test",
        task_id="debug",
        project_id="proj-123",
        need_tags=["test"],
        token_budget=1000
    )
)
```

## 📞 Support

- Docs: [README.md](./README.md)
- Architecture: [ARCHITECTURE.md](./ARCHITECTURE.md)
- Examples: [test_memcube_integration.py](./test_memcube_integration.py)
- FSA Integration: [memcube_fsa_integration_demo.py](./memcube_fsa_integration_demo.py)