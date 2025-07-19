# MemCube Memory System

A structured, lifecycle-aware memory system for AI agents that complements the FSA state tracking system. MemCube provides persistent knowledge storage, memory marketplace integration, and intelligent memory scheduling.

## 📚 Documentation

- **[Detailed Architecture Guide](./ARCHITECTURE.md)** - Complete system design, components, and data flows
- **[API Reference](./ARCHITECTURE.md#api-endpoints-reference)** - All REST endpoints with examples
- **[Directory Structure](./ARCHITECTURE.md#directory-structure)** - Project organization and file purposes

## Overview

MemCube implements a hierarchical memory architecture inspired by MemOS, with three types of memory:

1. **PLAINTEXT**: Human-readable markdown/JSON memories (≤64KB)
2. **ACTIVATION**: Base64-encoded KV cache memories (≤256KB)  
3. **PARAMETER**: LoRA delta patches for model adaptation

## Architecture Summary

For the complete architecture documentation, see [ARCHITECTURE.md](./ARCHITECTURE.md).

```
Agent Apps → Agent SDK → MemCube API → Storage Layer
                ↓              ↓             ↓
         [MemCubeClient] [Scheduler]  [Supabase/Blob]
         [MemoryInjector][Marketplace][Vector Search]
         [Hooks/Extension][Lifecycle] [Audit Trail]
```

## Key Features

### 1. Memory Lifecycle Management
- **Priority Tiers**: HOT → WARM → COLD → ARCHIVED
- **TTL-based expiration**: Configurable per memory
- **Usage tracking**: Automatic promotion/demotion
- **Governance controls**: Role-based access

### 2. Intelligent Memory Scheduling
- **Token budget aware**: Fits memories within context limits
- **Multi-signal scoring**: Recency, frequency, relevance
- **Diversity optimization**: Prefers varied memory types
- **Caching**: Fast repeated access

### 3. Memory Marketplace
- **Pack creation**: Bundle and distribute memories
- **Monetization**: Pricing and royalty support
- **Watermarking**: Protect paid content
- **Discovery**: Search and import relevant packs

### 4. Agent Integration
- **Automatic injection**: Enhance prompts with memories
- **Experience capture**: Store learnings automatically
- **Insight generation**: Convert observations to memories
- **Hook system**: Integrate with agent lifecycle

## Quick Start

### 1. Start the MemCube Service

```bash
# Set environment variables
export SUPABASE_URL="http://localhost:54321"
export SUPABASE_KEY="your-key"

# Run the service
python -m uvicorn memcube_system.service:app --port 8002
```

### 2. Basic Agent Integration

```python
from memcube_system.agent_sdk import AgentMemoryExtension

# Initialize memory extension
async with AgentMemoryExtension(
    agent_id="my-agent",
    project_id="my-project"
) as memory:
    
    # Enhance prompt with memories
    enhanced_prompt = await memory.enhance_prompt(
        prompt="Implement a React component",
        task_id="TASK-123",
        tags=["react", "frontend"]
    )
    
    # Capture experience
    memory.capture_experience(
        label="react-pattern",
        content="Use hooks for state management",
        tags=["react", "best-practice"]
    )
    
    # Generate insight
    await memory.generate_insight(
        observation="Users prefer dark mode",
        evidence=["analytics-001", "survey-002"],
        sentiment=0.8
    )
```

### 3. Memory-Enhanced Agent Class

```python
from memcube_system.agent_sdk import create_memory_agent

# Create enhanced agent class
MemoryAgent = create_memory_agent(
    BaseAgent,
    project_id="my-project",
    auto_store=True
)

# Use the agent
async with MemoryAgent() as agent:
    result = await agent.execute_task("Build feature X")
    # Memories are automatically managed
```

### 4. Running Analytics Jobs

Analytics jobs aggregate memory events into the `memory_analytics` table. The
service starts the scheduler automatically, but jobs can also be run manually:

```bash
python -m memcube_system.analytics
```

Metrics are accessible via the API:

```bash
curl "http://localhost:8002/analytics/usage?project_id=my-project&period=7d"
```

## API Quick Reference

For complete API documentation with request/response examples, see [API Reference](./ARCHITECTURE.md#api-endpoints-reference).

### Core Endpoints
- **Memory CRUD**: `/memories` (POST, GET, PUT, DELETE)
- **Query & Search**: `/memories/query`, `/memories/schedule`
- **Task Integration**: `/memories/{id}/link`, `/tasks/{task_id}/memories`
- **Insights**: `/insights`
- **Marketplace**: `/marketplace/packs`, `/marketplace/search`, `/marketplace/import/{pack_id}`
- **Admin**: `/admin/lifecycle`, `/admin/prune/{project_id}`

## Memory Governance

Each memory has governance settings controlling:

```python
governance = MemoryGovernance(
    read_roles=["MEMBER", "AGENT"],  # Who can read
    write_roles=["AGENT"],           # Who can write
    ttl_days=365,                    # Time to live
    shareable=True,                  # Can be shared
    license="MIT",                   # SPDX identifier
    pii_tagged=False                 # Contains PII
)
```

## Storage Modes

MemCube automatically selects storage mode based on size:

- **INLINE**: < 4KB - Stored directly in database
- **COMPRESSED**: < 64KB - Compressed in database
- **COLD**: > 64KB - External blob storage

## Memory Selection Algorithm

The scheduler scores memories based on:

1. **Tag Relevance** (40%): Match with requested tags
2. **Recency** (20%): Time since last use
3. **Frequency** (20%): Total usage count
4. **Priority** (10%): HOT/WARM/COLD status
5. **Task Context** (10%): Linked to current task

## Integration with FSA

MemCube complements the FSA system:

- **FSA**: Live state, tasks, metrics (ephemeral)
- **MemCube**: Knowledge, experiences, insights (persistent)

Agents typically:
1. Read FSA state for current context
2. Query MemCube for relevant knowledge
3. Execute task
4. Update FSA state
5. Store new experiences in MemCube

## Supabase Schema

Required tables:

```sql
-- Core memories table
CREATE TABLE memories (
    id UUID PRIMARY KEY,
    project_id TEXT NOT NULL,
    label TEXT NOT NULL,
    type TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    governance JSONB,
    usage_hits INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    priority TEXT DEFAULT 'WARM',
    storage_mode TEXT,
    payload_ref TEXT,
    size_bytes INTEGER,
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Memory versions
CREATE TABLE memory_versions (
    id UUID PRIMARY KEY,
    memory_id UUID REFERENCES memories(id),
    version INTEGER,
    blob_path TEXT,
    vector_sig FLOAT[],
    created_at TIMESTAMP DEFAULT NOW()
);

-- Audit events
CREATE TABLE memory_events (
    id SERIAL PRIMARY KEY,
    memory_id UUID REFERENCES memories(id),
    event TEXT,
    actor TEXT,
    ts TIMESTAMP DEFAULT NOW(),
    meta JSONB
);

-- Task links
CREATE TABLE memory_task_links (
    memory_id UUID REFERENCES memories(id),
    task_id TEXT,
    role TEXT DEFAULT 'READ',
    PRIMARY KEY (memory_id, task_id)
);
```

## Configuration

Environment variables:

- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_KEY`: Supabase anon/service key
- `BLOB_STORAGE_URL`: External blob storage (optional)
- `MARKETPLACE_API`: Marketplace service URL

## Performance Considerations

1. **Memory Scheduling**: Use appropriate token budgets
2. **Caching**: Leverage built-in cache (5min TTL)
3. **Batch Operations**: Use batch create/update when possible
4. **Cold Storage**: Archive unused memories regularly

## Future Enhancements

1. **Vector Search**: Semantic memory retrieval
2. **Memory Chains**: Linked memory sequences
3. **Collaborative Filtering**: Team-based memory recommendations
4. **Memory Analytics**: Usage patterns and insights
5. **Privacy Controls**: Enhanced PII handling

## Contributing

See the main project contributing guidelines. Key areas:

- Storage backends (S3, GCS, etc.)
- Memory synthesis algorithms
- Marketplace features
- Agent framework integrations