# ADK Supabase Architecture

## Overview

The ADK Supabase implementation provides a complete serverless backend for the Agent Development Kit, unifying the FSA State Memory System and MemCube persistent storage into a cohesive platform. This architecture leverages Supabase's PostgreSQL database, Edge Functions, Realtime subscriptions, and Storage capabilities.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Applications                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ TypeScript  │  │   Python    │  │   Agent     │            │
│  │    SDK      │  │    SDK      │  │  Runtimes   │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Supabase Edge Functions                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ FSA State    │  │  MemCube     │  │ Orchestrator │         │
│  │ Management   │  │   CRUD       │  │   Kernel     │         │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤         │
│  │ • Update     │  │ • Create     │  │ • Projects   │         │
│  │ • Query      │  │ • Search     │  │ • Tasks      │         │
│  │ • Merge      │  │ • Pack       │  │ • Tools      │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                           │
│  │ Agent        │  │  Lifecycle   │                           │
│  │ Execute      │  │  Management  │                           │
│  ├──────────────┤  ├──────────────┤                           │
│  │ • Tasks      │  │ • Cleanup    │                           │
│  │ • Progress   │  │ • Archive    │                           │
│  │ • Tools      │  │ • Health     │                           │
│  └──────────────┘  └──────────────┘                           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    FSA State Tables                       │  │
│  │  • fsa_states (versioned state storage)                  │  │
│  │  • fsa_deltas (incremental updates)                      │  │
│  │  • fsa_slice_cache (query optimization)                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   MemCube Tables                          │  │
│  │  • memories (content + embeddings)                        │  │
│  │  • memory_payloads (large content)                       │  │
│  │  • memory_packs (collections)                            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 Orchestrator Tables                       │  │
│  │  • projects, tasks, agents                               │  │
│  │  • tools, tool_executions                                │  │
│  │  • workflows, events                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    ▼                    ▼
        ┌──────────────────┐   ┌──────────────────┐
        │    Realtime      │   │  Object Storage  │
        │  Subscriptions   │   │   (Archives)     │
        └──────────────────┘   └──────────────────┘
```

## Core Components

### 1. FSA State Memory System

The FSA system provides real-time state coordination for multi-agent systems with:

#### State Management
- **Versioned Storage**: Every state change creates a new version
- **Delta Operations**: Incremental updates using CRDT-like operations
- **Conflict Resolution**: Multiple merge strategies (last-write-wins, union, CRDT)
- **Lineage Tracking**: Full causality chain for debugging

#### Query Optimization
- **Slice Queries**: Extract specific patterns from large states
- **Caching Layer**: Automatic caching of frequently accessed slices
- **Token Counting**: Efficient context window management
- **Batch Operations**: Multi-slice queries in single request

#### Schema Design
```sql
-- Core state storage
fsa_states (
  id, project_id, fsa_id, version, 
  parent_version, state (JSONB), 
  actor, lineage_id, created_at
)

-- Incremental updates
fsa_deltas (
  id, state_id, operations (JSONB),
  actor, lineage_id, applied_at
)

-- Query cache
fsa_slice_cache (
  id, state_id, pattern, k_limit,
  slice_data, summary, token_count,
  expires_at
)
```

### 2. MemCube Persistent Storage

MemCube provides intelligent memory management with:

#### Storage Modes
- **INLINE**: Small content (<10KB) stored directly
- **COMPRESSED**: Medium content (10KB-1MB) with compression
- **COLD**: Large content (>1MB) in object storage

#### Features
- **Semantic Search**: Vector embeddings with pgvector
- **Memory Packs**: Organized collections of memories
- **Automatic Optimization**: Dynamic storage mode selection
- **Content Types**: PLAINTEXT, JSON, MARKDOWN, CODE, BINARY

#### Schema Design
```sql
-- Core memory storage
memories (
  id, project_id, label, type,
  storage_mode, content_size,
  embedding (vector), metadata (JSONB)
)

-- Large content storage
memory_payloads (
  id, memory_id, content,
  compressed, encryption_key
)

-- Memory collections
memory_packs (
  id, project_id, name,
  description, memory_count
)
```

### 3. Orchestrator Kernel

The orchestrator manages task distribution and agent coordination:

#### Task Management
- **DAG Support**: Dependencies and blocking relationships
- **Priority Queuing**: Automatic task assignment by priority
- **Status Tracking**: PENDING → IN_PROGRESS → COMPLETED/FAILED
- **Progress Monitoring**: Real-time progress updates

#### Agent Coordination
- **Capability Matching**: Assign tasks based on agent skills
- **Session Management**: Track online/offline status
- **Heartbeat Monitoring**: Automatic failure detection
- **Load Balancing**: Distribute work evenly

#### Tool Execution
- **Registry System**: Centralized tool management
- **Permission Control**: AML-based access control
- **Rate Limiting**: Per-agent and per-tool limits
- **Approval Workflows**: Human-in-the-loop for sensitive operations

### 4. Edge Functions

Deno-based serverless functions provide the API layer:

#### FSA Functions
- `fsa-state`: State CRUD operations
- `fsa-query`: Slice queries and aggregations

#### MemCube Functions
- `memories-crud`: Memory management
- `memories-search`: Semantic search
- `memories-pack`: Pack operations

#### Orchestrator Functions
- `orchestrator`: Project and task management
- `agent-execute`: Task execution and progress
- `lifecycle`: Maintenance and cleanup

## Data Flow Patterns

### 1. State Update Flow
```
Agent → Edge Function → Validate → Apply Delta → 
Update State → Emit Event → Realtime Broadcast
```

### 2. Memory Search Flow
```
Query → Generate Embedding → Vector Search → 
Rank Results → Apply Filters → Return Memories
```

### 3. Task Execution Flow
```
Create Task → Check Dependencies → Assign Agent → 
Execute → Update Progress → Complete → Trigger Next
```

## Security Model

### Row Level Security (RLS)
- Project-based isolation
- Tenant-level separation
- Agent-specific permissions

### Access Control
- API Key authentication
- JWT token validation
- AML level enforcement

### Data Protection
- Encryption at rest
- Secure key management
- Audit logging

## Performance Optimizations

### Database
- Composite indexes on frequently queried columns
- Partial indexes for filtered queries
- JSONB GIN indexes for state queries
- Vector indexes for similarity search

### Caching
- 5-minute TTL for state slices
- LRU eviction for memory cache
- CDN caching for static content

### Query Optimization
- Batch operations to reduce round trips
- Pagination for large result sets
- Selective field loading
- Connection pooling

## Scaling Considerations

### Horizontal Scaling
- Stateless Edge Functions
- Read replicas for queries
- Partitioned tables for large datasets

### Vertical Scaling
- Larger compute for Edge Functions
- More memory for caching
- Dedicated pgvector instances

### Cost Optimization
- Automatic data archival
- Cold storage for old memories
- Cleanup of expired data
- Resource quotas per project

## Monitoring and Observability

### Metrics
- Task completion rates
- Agent utilization
- Memory usage patterns
- API latency percentiles

### Logging
- Structured logs from Edge Functions
- Database query logs
- Error tracking with context

### Health Checks
- Database connectivity
- Storage availability
- Queue depth monitoring
- Agent heartbeat tracking

## Development Workflow

### Local Development
```bash
# Start Supabase locally
supabase start

# Run migrations
supabase db push

# Deploy functions
supabase functions deploy

# Test with SDK
npm test
```

### Deployment
```bash
# Deploy to Supabase project
supabase link --project-ref your-project-ref
supabase db push
supabase functions deploy --no-verify-jwt
```

## Best Practices

### State Management
1. Use delta operations for incremental updates
2. Implement proper versioning strategies
3. Clean up old versions periodically
4. Cache frequently accessed slices

### Memory Storage
1. Let system choose storage mode automatically
2. Use appropriate content types
3. Implement retention policies
4. Regular cleanup of unused memories

### Task Orchestration
1. Define clear task dependencies
2. Set reasonable timeouts
3. Implement retry mechanisms
4. Monitor task queue depth

### Agent Development
1. Send regular heartbeats
2. Report progress incrementally
3. Handle errors gracefully
4. Request only necessary tools

## Migration Path

### From Standalone Systems
1. Export existing FSA states
2. Migrate memories with embeddings
3. Import task definitions
4. Update agent configurations
5. Switch to Supabase SDK

### Database Migration
```sql
-- Example migration from separate systems
INSERT INTO memories (label, content, type, embedding)
SELECT name, data, 'PLAINTEXT', embedding
FROM legacy_memory_table;

INSERT INTO fsa_states (project_id, fsa_id, state, version)
SELECT project_id, 'imported-fsa', state_data, 1
FROM legacy_state_table;
```

## Future Enhancements

### Planned Features
- GraphQL API layer
- Advanced CRDT implementations
- Multi-region replication
- Enhanced security features
- AI-powered query optimization

### Research Areas
- Distributed state consensus
- Quantum-resistant encryption
- Neuromorphic memory models
- Self-optimizing indexes
- Autonomous agent orchestration

## Conclusion

The ADK Supabase architecture provides a robust, scalable foundation for multi-agent AI systems. By leveraging Supabase's managed infrastructure and combining it with sophisticated state management and memory systems, developers can focus on building intelligent agents rather than infrastructure management.