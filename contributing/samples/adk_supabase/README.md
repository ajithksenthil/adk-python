# ADK Supabase Backend

A complete Supabase implementation of the Agent Development Kit (ADK) combining FSA State Memory System and MemCube persistent storage into a unified, serverless backend.

## 🚀 Features

- **FSA State Management**: Real-time, versioned state coordination for multi-agent systems
- **MemCube Storage**: Intelligent memory management with semantic search capabilities
- **Task Orchestration**: Distributed task assignment and execution tracking
- **Agent Coordination**: Lifecycle management and communication infrastructure
- **Tool Execution**: Secure, rate-limited tool invocation with approval workflows
- **Real-time Updates**: WebSocket-based state and event propagation
- **Lifecycle Management**: Automated cleanup, archival, and health monitoring

## 📋 Prerequisites

- [Supabase CLI](https://supabase.com/docs/guides/cli) installed
- Supabase project created at [app.supabase.com](https://app.supabase.com)
- Node.js 18+ (for Edge Functions)
- Python 3.8+ (for Python SDK)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd adk_supabase
```

### 2. Link to Supabase Project

```bash
supabase link --project-ref <your-project-ref>
```

### 3. Configure Environment

Create `.env` file:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
OPENAI_API_KEY=your-openai-key  # For embeddings
```

### 4. Deploy Database Schema

```bash
# Deploy all migrations
supabase db push

# Or deploy individually
supabase db push supabase/migrations/00001_fsa_schema.sql
supabase db push supabase/migrations/00002_memcube_schema.sql
supabase db push supabase/migrations/00003_orchestrator.sql
```

### 5. Deploy Edge Functions

```bash
# Deploy all functions
supabase functions deploy

# Or deploy individually
supabase functions deploy fsa-state
supabase functions deploy fsa-query
supabase functions deploy memories-crud
supabase functions deploy memories-search
supabase functions deploy memories-pack
supabase functions deploy orchestrator
supabase functions deploy agent-execute
supabase functions deploy lifecycle
```

## 📦 SDK Installation

### TypeScript/JavaScript

```bash
cd sdk/typescript
npm install
npm run build
```

### Python

```bash
cd sdk/python
pip install -e .
```

## 🔧 Usage Examples

### TypeScript

```typescript
import { createADKClient } from '@adk/supabase-sdk'

const adk = createADKClient({
  supabaseUrl: process.env.SUPABASE_URL,
  supabaseKey: process.env.SUPABASE_ANON_KEY
})

// Create a project
const projectId = await adk.createProject('AI Assistant', 'Multi-agent project')

// Update FSA state
await adk.updateState('main-fsa', {
  agents: { agent1: { status: 'online' } },
  tasks: { task1: { status: 'pending' } }
}, 'system')

// Create and search memories
const memory = await adk.createMemory('context', 'Project requirements...')
const results = await adk.searchMemories('requirements', 5)
```

### Python

```python
from adk_supabase import create_adk_client
import asyncio

adk = create_adk_client(
    supabase_url=os.getenv('SUPABASE_URL'),
    supabase_key=os.getenv('SUPABASE_ANON_KEY')
)

async def main():
    # Create project
    project_id = await adk.create_project('AI Assistant', 'Multi-agent project')
    
    # Create task
    task = await adk.create_task(
        'DESIGN_001',
        'design',
        'Create system architecture'
    )
    
    # Assign to agent
    await adk.assign_task(task.id, 'designer-agent')

asyncio.run(main())
```

## 📁 Project Structure

```
adk_supabase/
├── supabase/
│   ├── migrations/          # Database schema
│   │   ├── 00001_fsa_schema.sql
│   │   ├── 00002_memcube_schema.sql
│   │   └── 00003_orchestrator.sql
│   │
│   └── functions/          # Edge Functions
│       ├── fsa-state/      # State management
│       ├── fsa-query/      # State queries
│       ├── memories-crud/  # Memory CRUD
│       ├── memories-search/# Semantic search
│       ├── memories-pack/  # Pack management
│       ├── orchestrator/   # Task & project management
│       ├── agent-execute/  # Agent operations
│       └── lifecycle/      # Maintenance
│
├── sdk/
│   ├── typescript/         # TypeScript SDK
│   │   ├── src/
│   │   ├── package.json
│   │   └── tsconfig.json
│   │
│   └── python/            # Python SDK
│       ├── adk_supabase/
│       ├── setup.py
│       └── requirements.txt
│
├── examples/              # Usage examples
├── tests/                # Test suites
└── docs/                 # Additional documentation
```

## 🔑 Key Concepts

### FSA State Management

The FSA system provides versioned state storage with CRDT-like operations:

- **Versioning**: Every update creates a new version
- **Delta Operations**: `set`, `inc`, `push`, `unset`
- **Conflict Resolution**: Multiple merge strategies
- **Slice Queries**: Extract specific patterns efficiently

### MemCube Storage

Intelligent memory management with automatic optimization:

- **Storage Modes**: INLINE, COMPRESSED, COLD
- **Semantic Search**: Vector embeddings with pgvector
- **Memory Packs**: Organized collections
- **Auto-optimization**: Based on content size

### Task Orchestration

Distributed task management with dependency tracking:

- **Task States**: PENDING → IN_PROGRESS → COMPLETED/FAILED
- **Dependencies**: DAG-based execution order
- **Auto-assignment**: Based on agent capabilities
- **Progress Tracking**: Real-time updates

## 🧪 Testing

### Unit Tests

```bash
# TypeScript
cd sdk/typescript
npm test

# Python
cd sdk/python
pytest
```

### Integration Tests

```bash
# Run Supabase locally
supabase start

# Run integration tests
npm run test:integration
```

## 📊 Monitoring

### Health Check

```typescript
const health = await adk.healthCheck()
console.log('System status:', health.status)
console.log('Checks:', health.checks)
```

### Metrics

Monitor via Supabase Dashboard:
- Function invocations
- Database performance
- Storage usage
- Realtime connections

## 🔒 Security

### Row Level Security (RLS)
- Project-based isolation
- Tenant separation
- Agent permissions

### API Security
- API key authentication
- JWT validation
- Rate limiting

### Best Practices
- Use service role key only server-side
- Implement proper error handling
- Regular security audits

## 🚦 Performance

### Optimizations
- Indexed queries
- Cached state slices
- Batch operations
- Connection pooling

### Scaling
- Horizontal: Add read replicas
- Vertical: Upgrade compute resources
- Caching: Redis for hot data
- CDN: Static content delivery

## 🛠️ Maintenance

### Cleanup Operations

```typescript
// Clean expired cache
await adk.cleanup('cache', 24)

// Archive old projects
await adk.archiveProject(true, true)

// Run maintenance tasks
await adk.runMaintenance(['cleanup_expired', 'optimize_storage'])
```

### Backup Strategy
- Automated daily backups
- Point-in-time recovery
- Cross-region replication

## 📚 Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [API Reference](./docs/API.md)
- [Migration Guide](./docs/MIGRATION.md)
- [SDK Documentation](./sdk/README.md)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- Supabase team for the excellent platform
- OpenAI for embedding capabilities
- ADK community for feedback and contributions

## 📞 Support

- [GitHub Issues](https://github.com/your-org/adk-supabase/issues)
- [Discord Community](https://discord.gg/adk)
- [Documentation](https://docs.adk.dev)

---

Built with ❤️ by the ADK Team