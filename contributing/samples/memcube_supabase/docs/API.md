# MemCube Supabase API Reference

## Overview

MemCube provides a RESTful API through Supabase Edge Functions and PostgREST. All endpoints require authentication via Supabase Auth.

## Authentication

All requests must include an authentication header:

```http
Authorization: Bearer YOUR_SUPABASE_ACCESS_TOKEN
```

Get a token by signing in:

```javascript
const { data: { session } } = await supabase.auth.signInWithPassword({
  email: 'agent@project.com',
  password: 'password'
})
const token = session.access_token
```

## Base URLs

- **Edge Functions**: `https://YOUR_PROJECT.supabase.co/functions/v1/`
- **REST API**: `https://YOUR_PROJECT.supabase.co/rest/v1/`
- **Realtime**: `wss://YOUR_PROJECT.supabase.co/realtime/v1/`

## Edge Function Endpoints

### memories-crud

Memory CRUD operations via Edge Functions.

#### Create Memory

```http
POST /functions/v1/memories-crud
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "action": "create",
  "label": "react-hooks-guide",
  "type": "PLAINTEXT",
  "content": "Complete guide to React hooks...",
  "project_id": "project-123",
  "tags": ["react", "hooks", "frontend"],
  "governance": {
    "read_roles": ["MEMBER", "AGENT"],
    "write_roles": ["AGENT"],
    "ttl_days": 365,
    "shareable": true
  }
}

Response: 200 OK
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "label": "react-hooks-guide",
  "type": "PLAINTEXT",
  "created_at": "2024-01-15T10:00:00Z"
}
```

#### Get Memory

```http
POST /functions/v1/memories-crud
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "action": "get",
  "memory_id": "550e8400-e29b-41d4-a716-446655440000"
}

Response: 200 OK
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "label": "react-hooks-guide",
  "type": "PLAINTEXT",
  "content": "<<MEM:react-hooks-guide>>\nComplete guide to React hooks...\n<<ENDMEM>>",
  "metadata": {
    "version": 1,
    "created_by": "user-123",
    "created_at": "2024-01-15T10:00:00Z",
    "usage_hits": 42,
    "priority": "HOT",
    "token_count": 1250
  }
}
```

#### Update Memory

```http
POST /functions/v1/memories-crud
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "action": "update",
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Updated React hooks guide with new patterns...",
  "increment_version": true
}

Response: 200 OK
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "version": 2,
  "updated_at": "2024-01-15T11:00:00Z"
}
```

#### Archive Memory

```http
POST /functions/v1/memories-crud
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "action": "archive",
  "memory_id": "550e8400-e29b-41d4-a716-446655440000"
}

Response: 200 OK
{
  "status": "archived",
  "memory_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### memories-schedule

Intelligent memory scheduling for agents.

```http
POST /functions/v1/memories-schedule
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "agent_id": "frontend-bot",
  "task_id": "TASK-789",
  "project_id": "project-123",
  "need_tags": ["react", "performance", "hooks"],
  "token_budget": 4000,
  "prefer_hot": true,
  "include_insights": true,
  "embedding": [0.1, 0.2, ...] // Optional: 1536-dim vector
}

Response: 200 OK
{
  "agent_id": "frontend-bot",
  "task_id": "TASK-789",
  "memories": [
    {
      "id": "mem-001",
      "label": "react-optimization",
      "type": "PLAINTEXT",
      "content": "<<MEM:react-optimization>>\nUse React.memo for expensive components...\n<<ENDMEM>>",
      "tokens": 450,
      "relevance_score": 0.92
    },
    {
      "id": "mem-002",
      "label": "hooks-performance",
      "type": "PLAINTEXT",
      "content": "<<MEM:hooks-performance>>\nuseMemo and useCallback patterns...\n<<ENDMEM>>",
      "tokens": 380,
      "relevance_score": 0.88
    }
  ],
  "total_tokens": 1890,
  "count": 5,
  "cache_key": "mem_a1b2c3d4"
}
```

## REST API Endpoints (PostgREST)

### Query Memories

```http
GET /rest/v1/memories?project_id=eq.project-123&type=eq.PLAINTEXT&priority=eq.HOT
Authorization: Bearer TOKEN

Response: 200 OK
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "project_id": "project-123",
    "label": "react-hooks-guide",
    "type": "PLAINTEXT",
    "priority": "HOT",
    "usage_hits": 156,
    "created_at": "2024-01-15T10:00:00Z"
  }
]
```

### Complex Queries

```http
# Get memories with specific tags in label
GET /rest/v1/memories?label=ilike.*react*&project_id=eq.project-123&order=usage_hits.desc&limit=10

# Get memories created in last 7 days
GET /rest/v1/memories?created_at=gte.2024-01-08T00:00:00Z&project_id=eq.project-123

# Get memories with pagination
GET /rest/v1/memories?project_id=eq.project-123&offset=20&limit=10
```

### Create Insight

```http
POST /rest/v1/insights
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "project_id": "project-123",
  "insight": "Users strongly prefer dark mode in evening hours",
  "evidence_refs": ["analytics-001", "survey-042"],
  "tags": ["ui", "preferences", "dark-mode"],
  "sentiment": 0.85,
  "created_by": "user-123"
}

Response: 201 Created
{
  "id": "insight-uuid",
  "project_id": "project-123",
  "insight": "Users strongly prefer dark mode in evening hours",
  "support_count": 0,
  "created_at": "2024-01-15T10:00:00Z"
}
```

### Task-Memory Links

```http
# Create link
POST /rest/v1/memory_task_links
Content-Type: application/json
Authorization: Bearer TOKEN

{
  "memory_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": "TASK-789",
  "role": "READ"
}

# Get memories for task
GET /rest/v1/memory_task_links?task_id=eq.TASK-789&select=memories(*)
```

## Real-time Subscriptions

### Subscribe to Memory Changes

```javascript
const channel = supabase
  .channel('memory-changes')
  .on(
    'postgres_changes',
    {
      event: '*', // INSERT, UPDATE, DELETE
      schema: 'public',
      table: 'memories',
      filter: 'project_id=eq.project-123'
    },
    (payload) => {
      console.log('Memory changed:', payload)
      // payload.eventType: 'INSERT' | 'UPDATE' | 'DELETE'
      // payload.new: new record (INSERT/UPDATE)
      // payload.old: old record (UPDATE/DELETE)
    }
  )
  .subscribe()
```

### Subscribe to Task Memory Updates

```javascript
const channel = supabase
  .channel('task-memories')
  .on(
    'postgres_changes',
    {
      event: '*',
      schema: 'public',
      table: 'memory_task_links',
      filter: 'task_id=eq.TASK-789'
    },
    (payload) => {
      console.log('Task memory link changed:', payload)
    }
  )
  .subscribe()
```

## Storage API

### Upload Large Payload

```javascript
// For payloads > 64KB
const { data, error } = await supabase.storage
  .from('memory-payloads')
  .upload('memories/550e8400-e29b-41d4-a716-446655440000.txt', largeContent, {
    contentType: 'text/plain',
    upsert: true
  })

// Get signed URL for access
const { data: { signedUrl } } = await supabase.storage
  .from('memory-payloads')
  .createSignedUrl('memories/550e8400-e29b-41d4-a716-446655440000.txt', 3600)
```

## RPC Functions

### Search Similar Memories

```javascript
const { data, error } = await supabase.rpc('search_similar_memories', {
  query_embedding: [0.1, 0.2, ...], // 1536-dim vector
  project_id_param: 'project-123',
  similarity_threshold: 0.78,
  limit_count: 10
})
```

### Get Memory Stats

```javascript
const { data, error } = await supabase
  .from('memory_stats')
  .select('*')
  .eq('project_id', 'project-123')
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "Error message",
  "code": "error_code",
  "details": "Additional details"
}
```

Common status codes:
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limits

- **Edge Functions**: 1000 requests/minute per project
- **REST API**: 1000 requests/minute per IP
- **Realtime**: 100 concurrent connections per project

## Best Practices

1. **Use Batch Operations**: When creating multiple memories, batch them in transactions
2. **Cache Responses**: Memory schedule responses are cached for 5 minutes
3. **Subscribe Selectively**: Use filters in realtime subscriptions to reduce bandwidth
4. **Compress Large Content**: For ACTIVATION type, compress before storing
5. **Use Appropriate Indexes**: Query by indexed fields for better performance

## SDK Usage Examples

### TypeScript

```typescript
import { createMemCubeClient } from '@memcube/supabase'

const client = createMemCubeClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_ANON_KEY!,
  'project-123'
)

// Create memory
const memory = await client.createMemory({
  label: 'typescript-tips',
  type: MemoryType.PLAINTEXT,
  content: 'Use strict types',
  project_id: 'project-123'
})

// Schedule for agent
const scheduled = await client.scheduleMemories({
  agent_id: 'bot-001',
  task_id: 'TASK-123',
  project_id: 'project-123',
  need_tags: ['typescript'],
  token_budget: 2000
})
```

### Python

```python
from memcube_supabase import create_memcube_client

client = create_memcube_client(
    supabase_url=os.environ['SUPABASE_URL'],
    supabase_key=os.environ['SUPABASE_ANON_KEY'],
    project_id='project-123'
)

async with client:
    # Create memory
    memory = await client.create_memory(
        label='python-tips',
        content='Use type hints',
        type=MemoryType.PLAINTEXT
    )
    
    # Schedule for agent
    scheduled = await client.schedule_memories(
        agent_id='bot-001',
        task_id='TASK-123',
        tags=['python'],
        token_budget=2000
    )
```