# ADK Supabase SDK

Unified SDK for interacting with the ADK Supabase backend, providing seamless integration with FSA State Memory System and MemCube persistent storage.

## Features

- **FSA State Management**: Real-time state coordination for multi-agent systems
- **MemCube Integration**: Persistent memory storage with semantic search
- **Task Orchestration**: Distributed task management and assignment
- **Agent Coordination**: Agent lifecycle and communication management
- **Tool Execution**: Secure tool invocation with approval workflows
- **Real-time Updates**: WebSocket subscriptions for state and task changes
- **Lifecycle Management**: Cleanup, archival, and health monitoring

## Installation

### TypeScript/JavaScript

```bash
npm install @adk/supabase-sdk
```

### Python

```bash
pip install adk-supabase
```

## Quick Start

### TypeScript

```typescript
import { createADKClient } from '@adk/supabase-sdk'

// Initialize client
const adk = createADKClient({
  supabaseUrl: 'https://your-project.supabase.co',
  supabaseKey: 'your-anon-key',
  projectId: 'optional-project-id',
  tenantId: 'your-tenant-id'
})

// Create a project
const projectId = await adk.createProject('My AI Project', 'Description', 10000)

// Update FSA state
await adk.updateState('main-fsa', {
  agents: { agent1: { status: 'online' } },
  tasks: { task1: { status: 'pending' } }
}, 'system')

// Create a memory
const memory = await adk.createMemory(
  'project-context',
  'This project aims to build an AI assistant',
  'PLAINTEXT'
)

// Search memories
const results = await adk.searchMemories('AI assistant', 5)

// Subscribe to state changes
const unsubscribe = adk.subscribeToState('main-fsa', (state) => {
  console.log('State updated:', state)
})
```

### Python

```python
from adk_supabase import create_adk_client
import asyncio

# Initialize client
adk = create_adk_client(
    supabase_url='https://your-project.supabase.co',
    supabase_key='your-anon-key',
    project_id='optional-project-id',
    tenant_id='your-tenant-id'
)

async def main():
    # Create a project
    project_id = await adk.create_project('My AI Project', 'Description', 10000)
    
    # Update FSA state
    await adk.update_state('main-fsa', {
        'agents': {'agent1': {'status': 'online'}},
        'tasks': {'task1': {'status': 'pending'}}
    }, 'system')
    
    # Create a memory
    memory = await adk.create_memory(
        'project-context',
        'This project aims to build an AI assistant',
        MemoryType.PLAINTEXT
    )
    
    # Search memories
    results = await adk.search_memories('AI assistant', 5)
    
    # Create and assign a task
    task = await adk.create_task(
        'DESIGN_001',
        'design',
        'Design the UI mockups'
    )
    await adk.assign_task(task.id, 'agent1')

asyncio.run(main())
```

## Core Concepts

### FSA State Management

The FSA (Finite State Automaton) system provides versioned state management with CRDT-like operations:

```typescript
// Apply delta operations
await adk.applyDelta('project-fsa', [
  { op: 'set', path: ['tasks', 'TASK_001', 'status'], value: 'completed' },
  { op: 'inc', path: ['metrics', 'tasks_completed'], value: 1 }
], 'agent-1')

// Query state slices
const taskSlice = await adk.querySlice('project-fsa', 'tasks:DESIGN_*', 10)
```

### Memory Management

MemCube provides intelligent storage with automatic optimization:

```typescript
// Create different types of memories
await adk.createMemory('code-snippet', '```python\ndef hello():\n    pass\n```', 'CODE')
await adk.createMemory('meeting-notes', '# Meeting Notes\n...', 'MARKDOWN')

// Semantic search across memories
const relevant = await adk.searchMemories('python function', 10, 0.8)
```

### Task Orchestration

Manage complex workflows with dependencies:

```typescript
// Create tasks with dependencies
const designTask = await adk.createTask({
  task_id: 'DESIGN_001',
  type: 'design',
  title: 'Create UI mockups',
  priority: 100
})

const implTask = await adk.createTask({
  task_id: 'IMPL_001',
  type: 'implementation',
  title: 'Implement UI',
  depends_on: ['DESIGN_001']
})

// Agents get next available task
const nextTask = await adk.getNextTask('agent-1')
```

### Agent Management

Handle agent lifecycle and task execution:

```typescript
// Agent executes task
await adk.executeTask('agent-1', taskId, 'start')

// Update progress
await adk.updateProgress('agent-1', taskId, 50, 'Halfway done')

// Request tool execution
const result = await adk.requestTool(
  'agent-1',
  taskId,
  'code_execution',
  { language: 'python', code: 'print("Hello")' },
  true // wait for result
)

// Complete task
await adk.executeTask('agent-1', taskId, 'complete', { output: 'Done!' })
```

### Real-time Subscriptions

Subscribe to live updates:

```typescript
// Subscribe to FSA state changes
const unsubState = adk.subscribeToState('main-fsa', (state) => {
  console.log('New state version:', state.version)
})

// Subscribe to task updates
const unsubTasks = adk.subscribeToTasks((task) => {
  console.log('Task updated:', task.task_id, task.status)
})

// Cleanup
unsubState()
unsubTasks()
```

## Advanced Features

### Lifecycle Management

```typescript
// Cleanup old data
await adk.cleanup('cache', 24) // older than 24 hours
await adk.cleanup('events', 48)

// Archive project
const archiveId = await adk.archiveProject(true, true) // include memories, compress

// Health check
const health = await adk.healthCheck()
console.log('System health:', health.status)
```

### Error Handling

The SDK provides typed errors for better error handling:

```typescript
import { ProjectNotFoundError, TaskNotFoundError } from '@adk/supabase-sdk'

try {
  await adk.getTask('invalid-id')
} catch (error) {
  if (error instanceof TaskNotFoundError) {
    console.log('Task not found:', error.details.task_id)
  }
}
```

## API Reference

### Client Methods

#### Project Management
- `createProject(name, description?, budget?, agents?)` - Create new project
- `setProject(projectId)` - Set active project

#### FSA State
- `getState(fsaId, version?)` - Get state at specific version
- `updateState(fsaId, state, actor)` - Replace entire state
- `applyDelta(fsaId, delta[], actor)` - Apply incremental updates
- `querySlice(fsaId, pattern, k?)` - Query state slice by pattern

#### Memory Management
- `createMemory(label, content, type?, metadata?)` - Create memory
- `searchMemories(query, limit?, threshold?)` - Semantic search
- `getMemory(memoryId)` - Get specific memory
- `updateMemory(memoryId, updates)` - Update memory
- `deleteMemory(memoryId)` - Delete memory

#### Task Management
- `createTask(taskId, type, title, ...)` - Create task
- `assignTask(taskId, agentId)` - Assign to agent
- `getNextTask(agentId)` - Get next available task
- `completeTask(taskId, agentId, result?)` - Complete task

#### Agent Operations
- `executeTask(agentId, taskId, action, ...)` - Execute task action
- `updateProgress(agentId, taskId, progress, ...)` - Update progress
- `requestTool(agentId, taskId, toolName, params)` - Request tool
- `heartbeat(agentId, status?)` - Send heartbeat

## Best Practices

1. **State Management**: Use delta operations for incremental updates instead of replacing entire state
2. **Memory Storage**: Let the system automatically choose storage modes based on content size
3. **Task Dependencies**: Define clear dependencies to enable parallel execution
4. **Error Recovery**: Implement retry logic with exponential backoff for transient failures
5. **Resource Cleanup**: Regularly run cleanup operations to manage storage costs
6. **Real-time Updates**: Unsubscribe from channels when no longer needed to prevent memory leaks

## Migration Guide

If migrating from separate FSA/MemCube implementations:

1. Update connection strings to use Supabase URL and anon key
2. Replace direct database calls with SDK methods
3. Update real-time subscriptions to use SDK subscribe methods
4. Migrate state management to use FSA delta operations
5. Update memory operations to use MemCube CRUD methods

## Support

- [Documentation](https://docs.adk.dev/supabase)
- [GitHub Issues](https://github.com/adk/adk-supabase/issues)
- [Discord Community](https://discord.gg/adk)

## License

MIT License - see LICENSE file for details