import { createClient, SupabaseClient } from '@supabase/supabase-js'
import { RealtimeChannel } from '@supabase/realtime-js'

// Types
export interface ADKConfig {
  supabaseUrl: string
  supabaseKey: string
  projectId?: string
  tenantId?: string
}

export interface FSAState {
  [key: string]: any
}

export interface FSADelta {
  op: 'set' | 'inc' | 'push' | 'unset'
  path: string[]
  value?: any
}

export interface Memory {
  id: string
  label: string
  content: string
  type: 'PLAINTEXT' | 'JSON' | 'MARKDOWN' | 'CODE' | 'BINARY'
  embedding?: number[]
  metadata?: Record<string, any>
  created_at: string
}

export interface Task {
  id: string
  task_id: string
  type: string
  title: string
  description?: string
  status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'BLOCKED'
  assigned_to?: string
  depends_on?: string[]
}

export interface Agent {
  agent_id: string
  name: string
  type: string
  status: 'ONLINE' | 'BUSY' | 'OFFLINE' | 'ERROR'
  capabilities: string[]
  current_task_id?: string
}

export interface ToolExecution {
  tool_name: string
  parameters: Record<string, any>
  requires_approval?: boolean
}

// Main ADK Client
export class ADKClient {
  private supabase: SupabaseClient
  private projectId?: string
  private tenantId?: string
  private realtimeChannels: Map<string, RealtimeChannel> = new Map()

  constructor(config: ADKConfig) {
    this.supabase = createClient(config.supabaseUrl, config.supabaseKey)
    this.projectId = config.projectId
    this.tenantId = config.tenantId
  }

  // Project Management
  async createProject(name: string, description?: string, budget?: number): Promise<string> {
    const { data, error } = await this.supabase.functions.invoke('orchestrator/create-project', {
      body: {
        name,
        description,
        tenant_id: this.tenantId || 'default',
        budget_total: budget
      }
    })

    if (error) throw error
    this.projectId = data.project.id
    return data.project.id
  }

  async setProject(projectId: string) {
    this.projectId = projectId
  }

  // FSA State Management
  async getState(fsaId: string, version?: number): Promise<FSAState> {
    const { data, error } = await this.supabase.functions.invoke('fsa-state/get', {
      body: {
        project_id: this.ensureProjectId(),
        fsa_id: fsaId,
        version
      }
    })

    if (error) throw error
    return data.state
  }

  async updateState(fsaId: string, state: FSAState, actor: string): Promise<number> {
    const { data, error } = await this.supabase.functions.invoke('fsa-state/update', {
      body: {
        project_id: this.ensureProjectId(),
        fsa_id: fsaId,
        state,
        actor,
        lineage_id: `update-${Date.now()}`
      }
    })

    if (error) throw error
    return data.version
  }

  async applyDelta(fsaId: string, delta: FSADelta[], actor: string): Promise<number> {
    const { data, error } = await this.supabase.functions.invoke('fsa-state/update', {
      body: {
        project_id: this.ensureProjectId(),
        fsa_id: fsaId,
        delta,
        actor,
        lineage_id: `delta-${Date.now()}`
      }
    })

    if (error) throw error
    return data.version
  }

  async querySlice(fsaId: string, pattern: string, k?: number): Promise<any> {
    const { data, error } = await this.supabase.functions.invoke('fsa-query/slice', {
      body: {
        project_id: this.ensureProjectId(),
        fsa_id: fsaId,
        pattern,
        k,
        use_cache: true
      }
    })

    if (error) throw error
    return data
  }

  // Memory Management (MemCube)
  async createMemory(
    label: string,
    content: string,
    type: Memory['type'] = 'PLAINTEXT',
    metadata?: Record<string, any>
  ): Promise<Memory> {
    const { data, error } = await this.supabase.functions.invoke('memories-crud/create', {
      body: {
        project_id: this.ensureProjectId(),
        label,
        content,
        type,
        metadata
      }
    })

    if (error) throw error
    return data.memory
  }

  async searchMemories(query: string, limit: number = 10, threshold: number = 0.7): Promise<Memory[]> {
    const { data, error } = await this.supabase.functions.invoke('memories-search/semantic', {
      body: {
        project_id: this.ensureProjectId(),
        query,
        limit,
        threshold
      }
    })

    if (error) throw error
    return data.results
  }

  async getMemory(memoryId: string): Promise<Memory> {
    const { data, error } = await this.supabase.functions.invoke('memories-crud/get', {
      body: {
        memory_id: memoryId
      }
    })

    if (error) throw error
    return data.memory
  }

  async updateMemory(memoryId: string, updates: Partial<Memory>): Promise<Memory> {
    const { data, error } = await this.supabase.functions.invoke('memories-crud/update', {
      body: {
        memory_id: memoryId,
        ...updates
      }
    })

    if (error) throw error
    return data.memory
  }

  async deleteMemory(memoryId: string): Promise<void> {
    const { data, error } = await this.supabase.functions.invoke('memories-crud/delete', {
      body: {
        memory_id: memoryId
      }
    })

    if (error) throw error
  }

  // Task Management
  async createTask(task: Omit<Task, 'id'>): Promise<Task> {
    const { data, error } = await this.supabase.functions.invoke('orchestrator/create-task', {
      body: {
        project_id: this.ensureProjectId(),
        ...task
      }
    })

    if (error) throw error
    return data.task
  }

  async assignTask(taskId: string, agentId: string): Promise<void> {
    const { data, error } = await this.supabase.functions.invoke('orchestrator/assign-task', {
      body: {
        task_id: taskId,
        agent_id: agentId
      }
    })

    if (error) throw error
  }

  async getNextTask(agentId: string): Promise<Task | null> {
    const { data, error } = await this.supabase.functions.invoke('orchestrator/get-next-task', {
      body: {
        agent_id: agentId
      }
    })

    if (error) throw error
    return data.task
  }

  async completeTask(taskId: string, agentId: string, result?: any): Promise<void> {
    const { data, error } = await this.supabase.functions.invoke('orchestrator/complete-task', {
      body: {
        task_id: taskId,
        agent_id: agentId,
        result
      }
    })

    if (error) throw error
  }

  // Agent Management
  async executeTask(
    agentId: string,
    taskId: string,
    action: 'start' | 'pause' | 'resume' | 'complete' | 'fail',
    result?: any,
    error?: string
  ): Promise<any> {
    const { data, error: err } = await this.supabase.functions.invoke('agent-execute/execute-task', {
      body: {
        agent_id: agentId,
        task_id: taskId,
        project_id: this.ensureProjectId(),
        action,
        result,
        error
      }
    })

    if (err) throw err
    return data
  }

  async updateProgress(
    agentId: string,
    taskId: string,
    progress: number,
    statusMessage?: string
  ): Promise<void> {
    const { data, error } = await this.supabase.functions.invoke('agent-execute/update-progress', {
      body: {
        agent_id: agentId,
        task_id: taskId,
        progress,
        status_message: statusMessage
      }
    })

    if (error) throw error
  }

  async requestTool(
    agentId: string,
    taskId: string,
    toolName: string,
    parameters: Record<string, any>,
    waitForResult: boolean = false
  ): Promise<any> {
    const { data, error } = await this.supabase.functions.invoke('agent-execute/request-tool', {
      body: {
        agent_id: agentId,
        task_id: taskId,
        tool_name: toolName,
        parameters,
        wait_for_result: waitForResult
      }
    })

    if (error) throw error
    return data
  }

  async heartbeat(agentId: string, status: Agent['status'] = 'ONLINE'): Promise<void> {
    const { data, error } = await this.supabase.functions.invoke('orchestrator/agent-heartbeat', {
      body: {
        agent_id: agentId,
        project_id: this.ensureProjectId(),
        status
      }
    })

    if (error) throw error
  }

  // Tool Execution
  async executeTool(execution: ToolExecution & { agent_id: string }): Promise<any> {
    const { data, error } = await this.supabase.functions.invoke('orchestrator/execute-tool', {
      body: {
        project_id: this.ensureProjectId(),
        ...execution
      }
    })

    if (error) throw error
    return data
  }

  // Real-time Subscriptions
  subscribeToState(fsaId: string, callback: (state: FSAState) => void): () => void {
    const channelName = `fsa-${this.projectId}-${fsaId}`
    
    if (this.realtimeChannels.has(channelName)) {
      this.realtimeChannels.get(channelName)!.unsubscribe()
    }

    const channel = this.supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'events',
          filter: `type=eq.fsa.state.updated&data->>project_id=eq.${this.projectId}&data->>fsa_id=eq.${fsaId}`
        },
        async (payload) => {
          // Fetch the latest state
          const state = await this.getState(fsaId)
          callback(state)
        }
      )
      .subscribe()

    this.realtimeChannels.set(channelName, channel)

    return () => {
      channel.unsubscribe()
      this.realtimeChannels.delete(channelName)
    }
  }

  subscribeToTasks(callback: (task: Task) => void): () => void {
    const channelName = `tasks-${this.projectId}`
    
    if (this.realtimeChannels.has(channelName)) {
      this.realtimeChannels.get(channelName)!.unsubscribe()
    }

    const channel = this.supabase
      .channel(channelName)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'tasks',
          filter: `project_id=eq.${this.projectId}`
        },
        (payload) => {
          callback(payload.new as Task)
        }
      )
      .subscribe()

    this.realtimeChannels.set(channelName, channel)

    return () => {
      channel.unsubscribe()
      this.realtimeChannels.delete(channelName)
    }
  }

  // Lifecycle Management
  async cleanup(type: 'cache' | 'sessions' | 'events' | 'states', olderThanHours: number = 24): Promise<any> {
    const { data, error } = await this.supabase.functions.invoke('lifecycle/cleanup', {
      body: {
        type,
        project_id: type === 'states' ? this.ensureProjectId() : undefined,
        older_than_hours: olderThanHours
      }
    })

    if (error) throw error
    return data.results
  }

  async archiveProject(includeMemories: boolean = false, compress: boolean = true): Promise<string> {
    const { data, error } = await this.supabase.functions.invoke('lifecycle/archive-project', {
      body: {
        project_id: this.ensureProjectId(),
        include_memories: includeMemories,
        compress
      }
    })

    if (error) throw error
    return data.archive_id
  }

  async healthCheck(): Promise<any> {
    const { data, error } = await this.supabase.functions.invoke('lifecycle/health-check', {
      body: {}
    })

    if (error) throw error
    return data
  }

  // Utility Methods
  private ensureProjectId(): string {
    if (!this.projectId) {
      throw new Error('Project ID not set. Call setProject() or createProject() first.')
    }
    return this.projectId
  }

  async disconnect(): Promise<void> {
    // Unsubscribe from all channels
    for (const channel of this.realtimeChannels.values()) {
      channel.unsubscribe()
    }
    this.realtimeChannels.clear()
  }
}

// Factory function
export function createADKClient(config: ADKConfig): ADKClient {
  return new ADKClient(config)
}

// Re-export types
export * from './types'