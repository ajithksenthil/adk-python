# MemCube System Architecture & Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [Directory Structure](#directory-structure)
4. [Component Details](#component-details)
5. [API Endpoints Reference](#api-endpoints-reference)
6. [Data Flow](#data-flow)
7. [Integration with FSA](#integration-with-fsa)
8. [Deployment Architecture](#deployment-architecture)

## System Overview

MemCube is a structured, lifecycle-aware memory system for AI agents that provides:
- **Persistent Knowledge Storage**: Long-term memory across agent sessions
- **Intelligent Retrieval**: Context-aware memory selection within token budgets
- **Memory Marketplace**: Share and monetize knowledge packs
- **Lifecycle Management**: Automatic promotion/demotion based on usage

### Key Differentiators
- **Complements FSA**: FSA handles live state, MemCube handles persistent knowledge
- **Three Memory Types**: PLAINTEXT (readable), ACTIVATION (KV cache), PARAMETER (LoRA)
- **Governance Built-in**: Role-based access, TTL, licensing
- **Efficiency First**: Slice-based queries, smart caching, storage optimization

## Architecture Design

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Agent Applications                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │   Design    │  │  Frontend   │  │   Backend   │  │    QA     │ │
│  │    Agent    │  │    Agent    │  │    Agent    │  │   Agent   │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘ │
│         │                 │                 │                │       │
└─────────┼─────────────────┼─────────────────┼────────────────┼──────┘
          │                 │                 │                │
┌─────────┴─────────────────┴─────────────────┴────────────────┴──────┐
│                        Agent SDK Layer                               │
│  ┌────────────────┐  ┌─────────────────┐  ┌────────────────────┐   │
│  │ MemCubeClient  │  │ MemoryInjector  │  │ AgentMemoryExtension│  │
│  │                │  │                 │  │                    │   │
│  │ - get_memories │  │ - inject_xml    │  │ - enhance_prompt   │   │
│  │ - store_exp    │  │ - inject_md     │  │ - capture_exp      │   │
│  │ - submit_insight│ │ - inject_default│  │ - generate_insight │   │
│  └────────┬───────┘  └────────┬────────┘  └──────────┬─────────┘   │
│           │                   │                       │             │
└───────────┼───────────────────┼───────────────────────┼─────────────┘
            │                   │                       │
            └───────────────────┴───────────────────────┘
                                │
                                │ HTTP/REST
                                │
┌───────────────────────────────┴──────────────────────────────────────┐
│                      MemCube API Service                             │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │   REST API      │  │ Memory Scheduler  │  │   Marketplace    │   │
│  │                 │  │                   │  │                  │   │
│  │ /memories       │  │ - Token budgeting │  │ - Pack creation  │   │
│  │ /insights       │  │ - Relevance score │  │ - Distribution   │   │
│  │ /marketplace    │  │ - Cache management│  │ - Monetization   │   │
│  └────────┬────────┘  └─────────┬────────┘  └────────┬─────────┘   │
│           │                     │                     │             │
├───────────┼─────────────────────┼─────────────────────┼─────────────┤
│           │                     │                     │             │
│  ┌────────┴──────────┐  ┌──────┴────────┐  ┌────────┴─────────┐   │
│  │ Memory Operator   │  │Memory Selector │  │ Lifecycle Manager│   │
│  │                   │  │                │  │                  │   │
│  │ - Create/Update   │  │ - Tag matching │  │ - TTL expiration │   │
│  │ - Synthesize      │  │ - Scoring      │  │ - Priority decay │   │
│  │ - Batch ops       │  │ - Optimization │  │ - Cleanup tasks  │   │
│  └────────┬──────────┘  └───────┬────────┘  └────────┬─────────┘   │
│           │                     │                     │             │
└───────────┼─────────────────────┼─────────────────────┼─────────────┘
            │                     │                     │
            └─────────────────────┴─────────────────────┘
                                │
┌───────────────────────────────┴──────────────────────────────────────┐
│                        Storage Layer                                 │
│  ┌─────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │    Supabase     │  │   Blob Storage   │  │    Vector DB     │   │
│  │                 │  │                  │  │                  │   │
│  │ - Metadata      │  │ - Large payloads │  │ - Embeddings     │   │
│  │ - Inline data   │  │ - Compressed data│  │ - Similarity     │   │
│  │ - Audit logs    │  │ - Cold storage   │  │ - Search index   │   │
│  └─────────────────┘  └──────────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### Component Interaction Diagram

```
┌─────────────┐     1. Request memories      ┌──────────────┐
│    Agent    │ ─────────────────────────────▶│  MemCube     │
│             │                                │   Client     │
│             │◀───────────────────────────────│              │
└─────────────┘     6. Enhanced prompt         └──────┬───────┘
                                                      │
                                                      │ 2. Schedule request
                                                      ▼
┌─────────────┐     3. Query memories         ┌──────────────┐
│   Storage   │◀───────────────────────────────│  Scheduler   │
│  (Supabase) │                                │              │
│             │─────────────────────────────────▶              │
└─────────────┘     4. Return candidates       └──────┬───────┘
                                                      │
                                                      │ 5. Select & format
                                                      ▼
                                               ┌──────────────┐
                                               │   Selector   │
                                               │   & Cache    │
                                               └──────────────┘
```

## Directory Structure

```
memcube_system/
│
├── __init__.py                 # Package initialization, exports all public APIs
│
├── models.py                   # Core data models
│   ├── MemoryType             # Enum: PLAINTEXT, ACTIVATION, PARAMETER
│   ├── MemoryLifecycle        # States: NEW, ACTIVE, STALE, ARCHIVED, EXPIRED
│   ├── MemoryPriority         # HOT, WARM, COLD
│   ├── MemoryGovernance       # Access control and policies
│   ├── MemCubeHeader          # Metadata (id, version, governance, etc.)
│   ├── MemCubePayload         # Content with size validation
│   ├── MemCube                # Complete memory unit
│   ├── MemoryPack             # Marketplace distribution unit
│   ├── InsightCard            # User-generated insights
│   └── Query/Request models   # API request/response schemas
│
├── storage.py                  # Storage layer implementation
│   ├── MemCubeStorage         # Abstract base class
│   ├── SupabaseMemCubeStorage # Supabase implementation
│   │   ├── store_memory()     # Create/update with versioning
│   │   ├── get_memory()       # Retrieve with usage tracking
│   │   ├── query_memories()   # Search with filters
│   │   └── archive_memory()   # Lifecycle transitions
│   └── MemoryLifecycleManager # Automated maintenance
│       ├── expire_old_memories()
│       ├── decay_unused_memories()
│       └── cleanup_orphaned_payloads()
│
├── operator.py                 # High-level memory operations
│   ├── MemoryOperator         # CRUD and synthesis operations
│   │   ├── create_from_text()
│   │   ├── create_from_activation()
│   │   ├── synthesize_memories()
│   │   └── get_memory_lineage()
│   ├── MemorySelector         # Intelligent selection logic
│   │   ├── select_memories()  # Main selection algorithm
│   │   ├── _score_memories()  # Multi-signal scoring
│   │   └── _optimize_selection()
│   └── MemoryScheduler        # Request handling & caching
│       ├── schedule_request()
│       └── _process_requests()
│
├── marketplace.py              # Data marketplace integration
│   ├── MemPackPublisher       # Create and publish packs
│   │   ├── create_pack()
│   │   ├── publish_pack()
│   │   └── _watermark_memories()
│   ├── MemPackImporter        # Import from marketplace
│   │   ├── search_packs()
│   │   ├── import_pack()
│   │   └── _process_payment()
│   └── MarketplaceService     # Coordination layer
│
├── service.py                  # FastAPI REST service
│   ├── Lifecycle management   # App startup/shutdown
│   ├── Memory endpoints       # CRUD operations
│   ├── Query endpoints        # Search and retrieval
│   ├── Insight endpoints      # User feedback
│   ├── Marketplace endpoints  # Pack operations
│   └── Admin endpoints        # Maintenance tasks
│
├── agent_sdk.py               # Agent integration tools
│   ├── MemCubeClient         # Simple API client
│   │   ├── get_memories_for_task()
│   │   ├── store_experience()
│   │   └── submit_insight()
│   ├── MemoryInjector        # Prompt enhancement
│   │   ├── inject_memories()
│   │   ├── _format_xml()
│   │   ├── _format_markdown()
│   │   └── _format_default()
│   ├── AgentMemoryExtension  # Full lifecycle integration
│   │   ├── enhance_prompt()
│   │   ├── capture_experience()
│   │   └── generate_insight()
│   └── MemoryHooks           # Framework integration
│       ├── pre_task_hook()
│       ├── post_task_hook()
│       └── error_hook()
│
├── README.md                  # User documentation
├── ARCHITECTURE.md           # This file - detailed architecture
├── test_memcube_integration.py    # Integration tests
└── memcube_fsa_integration_demo.py # FSA integration example
```

## Component Details

### 1. Models Layer (`models.py`)
- **Purpose**: Define all data structures and validation rules
- **Key Classes**:
  - `MemCube`: Core memory unit with header + payload
  - `MemoryGovernance`: Access control (read_roles, write_roles, TTL)
  - `InsightCard`: User feedback that converts to memories
- **Validation**: Pydantic models with size limits (64KB for PLAINTEXT, 256KB for ACTIVATION)

### 2. Storage Layer (`storage.py`)
- **Purpose**: Abstract persistence with intelligent storage modes
- **Storage Modes**:
  - `INLINE`: <4KB stored directly in database
  - `COMPRESSED`: <64KB compressed in database
  - `COLD`: >64KB in external blob storage
- **Features**:
  - Automatic versioning
  - Audit trail via events table
  - Vector similarity search support
  - TTL and lifecycle management

### 3. Operator Layer (`operator.py`)
- **Purpose**: Business logic for memory management
- **Key Components**:
  - `MemoryOperator`: High-level operations (create, update, synthesize)
  - `MemorySelector`: Scoring algorithm for relevance
  - `MemoryScheduler`: Request queuing and caching
- **Selection Algorithm**:
  ```
  Score = 0.4 * tag_relevance 
        + 0.2 * recency 
        + 0.2 * frequency 
        + 0.1 * priority 
        + 0.1 * task_context
  ```

### 4. API Service (`service.py`)
- **Purpose**: REST API exposing all functionality
- **Framework**: FastAPI with async support
- **Features**:
  - OpenAPI documentation
  - CORS support
  - Request validation
  - Error handling
  - Lifecycle hooks

### 5. Agent SDK (`agent_sdk.py`)
- **Purpose**: Easy integration for AI agents
- **Integration Patterns**:
  - Direct client usage
  - Decorator pattern
  - Hook-based integration
  - Factory pattern for enhanced agents

## API Endpoints Reference

### Memory Management

#### Create Memory
```http
POST /memories
Content-Type: application/json

{
  "project_id": "project-123",
  "label": "react-best-practices",
  "content": "Always use functional components...",
  "type": "PLAINTEXT",
  "created_by": "agent-001",
  "tags": ["react", "frontend"],
  "priority": "WARM",
  "governance": {
    "read_roles": ["MEMBER", "AGENT"],
    "write_roles": ["AGENT"],
    "ttl_days": 365
  }
}

Response: 200 OK
{
  "id": "mem-uuid",
  "label": "react-best-practices",
  "type": "PLAINTEXT",
  "created_at": "2024-01-15T10:00:00Z"
}
```

#### Get Memory
```http
GET /memories/{memory_id}

Response: 200 OK
{
  "id": "mem-uuid",
  "label": "react-best-practices",
  "type": "PLAINTEXT",
  "content": "<<MEM:react-best-practices>>\nAlways use functional components...\n<<ENDMEM>>",
  "metadata": {
    "version": 1,
    "created_by": "agent-001",
    "created_at": "2024-01-15T10:00:00Z",
    "usage_hits": 42,
    "priority": "HOT"
  }
}
```

#### Update Memory
```http
PUT /memories/{memory_id}
Content-Type: application/json

{
  "content": "Updated content with new learnings...",
  "updated_by": "agent-002"
}

Response: 200 OK
{
  "id": "mem-uuid-v2",
  "version": 2,
  "updated_at": "2024-01-15T11:00:00Z"
}
```

#### Archive Memory
```http
DELETE /memories/{memory_id}

Response: 200 OK
{
  "status": "archived",
  "memory_id": "mem-uuid"
}
```

### Memory Querying

#### Query Memories
```http
POST /memories/query
Content-Type: application/json

{
  "project_id": "project-123",
  "tags": ["react", "hooks"],
  "type_filter": "PLAINTEXT",
  "priority_filter": "HOT",
  "embedding": [0.1, 0.2, ...],  // Optional: for similarity search
  "similarity_threshold": 0.78,
  "limit": 10,
  "include_insights": true
}

Response: 200 OK
{
  "memories": [
    {
      "id": "mem-001",
      "label": "react-hooks-patterns",
      "type": "PLAINTEXT",
      "priority": "HOT",
      "usage_hits": 156,
      "preview": "Essential patterns for React hooks including..."
    }
  ],
  "count": 3
}
```

#### Schedule Memories for Agent
```http
POST /memories/schedule
Content-Type: application/json

{
  "agent_id": "frontend-bot",
  "task_id": "TASK-789",
  "project_id": "project-123",
  "need_tags": ["react", "performance"],
  "token_budget": 4000,
  "prefer_hot": true,
  "include_insights": true
}

Response: 200 OK
{
  "agent_id": "frontend-bot",
  "memories": [
    {
      "id": "mem-001",
      "label": "react-optimization",
      "content": "<<MEM:react-optimization>>\nMemoization techniques...\n<<ENDMEM>>",
      "tokens": 450
    }
  ],
  "total_tokens": 1890,
  "count": 5
}
```

### Task Integration

#### Link Memory to Task
```http
POST /memories/{memory_id}/link
Content-Type: application/json

{
  "task_id": "TASK-789",
  "role": "READ"  // or "WRITE"
}

Response: 200 OK
{
  "status": "linked",
  "memory_id": "mem-001",
  "task_id": "TASK-789"
}
```

#### Get Task Memories
```http
GET /tasks/{task_id}/memories

Response: 200 OK
{
  "task_id": "TASK-789",
  "memories": [
    {
      "id": "mem-001",
      "label": "related-pattern",
      "type": "PLAINTEXT",
      "content": "<<MEM:related-pattern>>\nContent...\n<<ENDMEM>>"
    }
  ],
  "count": 3
}
```

### Insights Management

#### Create Insight
```http
POST /insights?project_id=project-123&created_by=agent-001
Content-Type: application/json

{
  "insight": "Users prefer dark mode in evening hours",
  "evidence_refs": ["analytics-001", "survey-042"],
  "tags": ["ui", "preferences"],
  "sentiment": 0.85
}

Response: 200 OK
{
  "insight_id": "ins-uuid",
  "memory_id": "mem-uuid",
  "created_at": "2024-01-15T10:00:00Z"
}
```

### Marketplace Operations

#### Create Memory Pack
```http
POST /marketplace/packs?author_id=user-123&project_id=project-123
Content-Type: application/json

{
  "title": "React Performance Pack",
  "description": "Curated memories for React optimization",
  "tags": ["react", "performance"],
  "max_memories": 50,
  "price_cents": 999,
  "royalty_pct": 15,
  "cover_img": "https://example.com/cover.png"
}

Response: 200 OK
{
  "listing_id": "pack-uuid",
  "status": "published",
  "title": "React Performance Pack"
}
```

#### Search Marketplace
```http
GET /marketplace/search?query=react+patterns&max_price_cents=1000

Response: 200 OK
{
  "packs": [
    {
      "id": "pack-001",
      "title": "React Best Practices",
      "description": "Comprehensive React patterns",
      "author": "expert-dev",
      "price_cents": 500,
      "memory_count": 25,
      "rating": 4.8
    }
  ],
  "count": 12
}
```

#### Import Memory Pack
```http
POST /marketplace/import/{pack_id}?project_id=project-123&buyer_id=user-456

Response: 200 OK
{
  "pack_id": "pack-001",
  "imported_memories": ["mem-101", "mem-102", "mem-103"],
  "count": 3
}
```

### Memory Synthesis

#### Synthesize Memories
```http
POST /memories/synthesize?project_id=project-123&created_by=agent-001
Content-Type: application/json

{
  "memory_ids": ["mem-001", "mem-002", "mem-003"],
  "prompt": "Create a comprehensive guide combining these patterns"
}

Response: 200 OK
{
  "id": "mem-synth-001",
  "label": "synthesis::20240115_1000",
  "source_count": 3,
  "content_preview": "Synthesis of 3 memories:\nCreate a comprehensive guide..."
}
```

### Administrative Operations

#### Run Lifecycle Tasks
```http
POST /admin/lifecycle

Response: 200 OK
{
  "status": "completed",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

#### Prune Cold Memories
```http
POST /admin/prune/{project_id}?keep_count=100

Response: 200 OK
{
  "project_id": "project-123",
  "archived_count": 45,
  "keep_count": 100
}
```

### Health Check
```http
GET /health

Response: 200 OK
{
  "status": "healthy",
  "service": "memcube",
  "version": "0.2.0",
  "timestamp": "2024-01-15T10:00:00Z"
}
```

## Data Flow

### Memory Creation Flow
```
1. Agent captures experience
   └─> 2. SDK buffers or sends immediately
       └─> 3. API validates request
           └─> 4. Storage determines mode (inline/compressed/cold)
               └─> 5. Header saved to Supabase
                   └─> 6. Payload stored based on mode
                       └─> 7. Version record created
                           └─> 8. Event logged
                               └─> 9. Memory ID returned
```

### Memory Retrieval Flow
```
1. Agent requests memories for task
   └─> 2. Scheduler checks cache
       ├─> [Cache Hit] Return cached memories
       └─> [Cache Miss] 3. Selector queries storage
           └─> 4. Score and rank candidates
               └─> 5. Optimize within token budget
                   └─> 6. Update usage stats
                       └─> 7. Cache results
                           └─> 8. Return formatted memories
```

### Marketplace Flow
```
1. Author selects memories for pack
   └─> 2. Publisher validates and watermarks
       └─> 3. Pack metadata stored
           └─> 4. Listed on marketplace
               └─> 5. Buyer discovers pack
                   └─> 6. Payment processed
                       └─> 7. Memories imported to project
                           └─> 8. Royalties tracked
```

## Integration with FSA

### Complementary Systems
```
┌─────────────────────────┐     ┌─────────────────────────┐
│         FSA             │     │       MemCube           │
├─────────────────────────┤     ├─────────────────────────┤
│ • Live state            │     │ • Persistent knowledge  │
│ • Task coordination     │     │ • Long-term memory      │
│ • Real-time metrics     │     │ • Experience capture    │
│ • Agent synchronization │     │ • Insight generation    │
│ • Ephemeral data        │     │ • Knowledge marketplace │
└─────────────────────────┘     └─────────────────────────┘
         │                               │
         └───────────────┬───────────────┘
                         │
                    Used Together
                         │
                         ▼
              ┌──────────────────┐
              │  Intelligent     │
              │  Agent Behavior  │
              └──────────────────┘
```

### Typical Agent Workflow
```python
# 1. Read current state from FSA
state = await fsa_client.get_slice(tenant_id, fsa_id, "task:*")

# 2. Get relevant memories from MemCube
memories = await memcube_client.get_memories_for_task(
    agent_id, task_id, project_id, tags=["react"]
)

# 3. Enhance prompt with both
prompt = f"""
Current State: {state.summary}
{inject_memories(base_prompt, memories)}
"""

# 4. Execute task
result = await llm.complete(prompt)

# 5. Update FSA state
await fsa_client.apply_delta(tenant_id, fsa_id, {
    "tasks.TASK-001.status": "COMPLETED"
})

# 6. Store experience in MemCube
await memcube_client.store_experience(
    agent_id, project_id, "task-learning", result.learning
)
```

## Deployment Architecture

### Production Setup
```
┌─────────────────┐
│   Load Balancer │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│ API-1 │ │ API-2 │  (Horizontal scaling)
└───┬───┘ └──┬────┘
    │        │
    └───┬────┘
        │
┌───────▼────────┐
│     Redis      │  (Cache layer)
└───────┬────────┘
        │
┌───────▼────────────────────────┐
│          Supabase              │
│  ┌──────────┐  ┌────────────┐ │
│  │PostgreSQL│  │  Storage   │ │
│  └──────────┘  └────────────┘ │
└────────────────────────────────┘
        │
┌───────▼────────┐
│  Blob Storage  │  (S3/GCS for large payloads)
└────────────────┘
```

### Environment Variables
```bash
# Core Service
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-service-key
BLOB_STORAGE_URL=s3://your-bucket
MARKETPLACE_API=https://marketplace.api.com

# Performance Tuning
CACHE_TTL=300  # 5 minutes
MAX_CACHE_SIZE=10000
WORKER_POOL_SIZE=10

# Storage Thresholds
INLINE_SIZE_LIMIT=4096
COMPRESSED_SIZE_LIMIT=65536
```

### Scaling Considerations

1. **API Layer**: Stateless, scale horizontally
2. **Cache Layer**: Redis cluster for high availability
3. **Storage Layer**: 
   - Supabase handles metadata scaling
   - Blob storage for large payloads
   - Consider read replicas for heavy query loads
4. **Memory Scheduling**: 
   - Implement queue-based processing for large batches
   - Consider separate scheduler service at scale

### Monitoring & Observability

Key metrics to track:
- Memory creation rate
- Query latency (p50, p95, p99)
- Cache hit rate
- Storage distribution (inline vs compressed vs cold)
- Token budget utilization
- Marketplace activity

### Security Considerations

1. **Authentication**: API key or JWT tokens
2. **Authorization**: Role-based access per memory governance
3. **Data Privacy**: PII tagging and handling
4. **Marketplace**: Payment security and watermarking
5. **Rate Limiting**: Per agent/project quotas