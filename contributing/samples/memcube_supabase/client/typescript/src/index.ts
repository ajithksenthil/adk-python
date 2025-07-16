import { createClient, SupabaseClient } from '@supabase/supabase-js'
import { RealtimeChannel } from '@supabase/supabase-js'

// Types
export enum MemoryType {
  PLAINTEXT = 'PLAINTEXT',
  ACTIVATION = 'ACTIVATION',
  PARAMETER = 'PARAMETER'
}

export enum MemoryPriority {
  HOT = 'HOT',
  WARM = 'WARM',
  COLD = 'COLD'
}

export interface MemoryGovernance {
  read_roles?: string[]
  write_roles?: string[]
  ttl_days?: number
  shareable?: boolean
  license?: string | null
  pii_tagged?: boolean
}

export interface CreateMemoryRequest {
  label: string
  type: MemoryType
  content: string
  project_id: string
  tags?: string[]
  governance?: MemoryGovernance
}

export interface Memory {
  id: string
  label: string
  type: MemoryType
  priority: MemoryPriority
  content?: string
  metadata?: {
    version: number
    created_by: string
    created_at: string
    usage_hits: number
    token_count?: number
  }
}

export interface MemoryScheduleRequest {
  agent_id: string
  task_id: string
  project_id: string
  need_tags?: string[]
  token_budget?: number
  prefer_hot?: boolean
  include_insights?: boolean
  embedding?: number[]
}

export interface ScheduledMemories {
  agent_id: string
  task_id: string
  memories: Array<{
    id: string
    label: string
    type: string
    content: string
    tokens: number
    relevance_score?: number
  }>
  total_tokens: number
  count: number
}

export interface MemoryQuery {
  project_id: string
  tags?: string[]
  type_filter?: MemoryType
  priority_filter?: MemoryPriority
  limit?: number
  include_insights?: boolean
}

export interface Insight {
  id: string
  project_id: string
  insight: string
  evidence_refs: string[]
  support_count: number
  sentiment: number
  tags: string[]
  memory_id?: string
}

export interface MemoryPack {
  id: string
  title: string
  description: string
  author_id: string
  price_cents: number
  memory_count: number
  rating?: number
}

// Main client class
export class MemCubeClient {
  private supabase: SupabaseClient
  private realtimeChannel?: RealtimeChannel

  constructor(
    supabaseUrl: string,
    supabaseKey: string,
    private options: {
      projectId?: string
      autoRefreshToken?: boolean
    } = {}
  ) {
    this.supabase = createClient(supabaseUrl, supabaseKey, {
      auth: {
        autoRefreshToken: options.autoRefreshToken ?? true,
        persistSession: true
      }
    })
  }

  // Authentication
  async signIn(email: string, password: string) {
    const { data, error } = await this.supabase.auth.signInWithPassword({
      email,
      password
    })
    if (error) throw error
    return data
  }

  async signOut() {
    const { error } = await this.supabase.auth.signOut()
    if (error) throw error
  }

  async getSession() {
    const { data: { session }, error } = await this.supabase.auth.getSession()
    if (error) throw error
    return session
  }

  // Memory CRUD operations
  async createMemory(request: CreateMemoryRequest): Promise<Memory> {
    const { data, error } = await this.supabase.functions.invoke('memories-crud', {
      body: {
        action: 'create',
        ...request,
        project_id: request.project_id || this.options.projectId
      }
    })

    if (error) throw error
    return data
  }

  async getMemory(memoryId: string): Promise<Memory> {
    const { data, error } = await this.supabase.functions.invoke('memories-crud', {
      body: {
        action: 'get',
        memory_id: memoryId
      }
    })

    if (error) throw error
    return data
  }

  async updateMemory(memoryId: string, content: string): Promise<Memory> {
    const { data, error } = await this.supabase.functions.invoke('memories-crud', {
      body: {
        action: 'update',
        memory_id: memoryId,
        content
      }
    })

    if (error) throw error
    return data
  }

  async archiveMemory(memoryId: string): Promise<{ status: string; memory_id: string }> {
    const { data, error } = await this.supabase.functions.invoke('memories-crud', {
      body: {
        action: 'archive',
        memory_id: memoryId
      }
    })

    if (error) throw error
    return data
  }

  // Memory querying
  async queryMemories(query: MemoryQuery): Promise<Memory[]> {
    let q = this.supabase
      .from('memories')
      .select('*, memory_payloads(content, token_count)')
      .eq('project_id', query.project_id || this.options.projectId!)

    if (query.type_filter) {
      q = q.eq('type', query.type_filter)
    }

    if (query.priority_filter) {
      q = q.eq('priority', query.priority_filter)
    }

    if (query.tags && query.tags.length > 0) {
      // Filter by tags in label (simple implementation)
      const tagFilter = query.tags.map(tag => `label.ilike.%${tag}%`).join(',')
      q = q.or(tagFilter)
    }

    if (query.limit) {
      q = q.limit(query.limit)
    }

    const { data, error } = await q

    if (error) throw error
    return data || []
  }

  // Memory scheduling for agents
  async scheduleMemories(request: MemoryScheduleRequest): Promise<ScheduledMemories> {
    const { data, error } = await this.supabase.functions.invoke('memories-schedule', {
      body: {
        ...request,
        project_id: request.project_id || this.options.projectId
      }
    })

    if (error) throw error
    return data
  }

  // Insights
  async createInsight(
    insight: string,
    evidence_refs: string[] = [],
    tags: string[] = [],
    sentiment: number = 0
  ): Promise<{ insight_id: string; memory_id: string }> {
    const projectId = this.options.projectId
    if (!projectId) throw new Error('Project ID required')

    const { data: user } = await this.supabase.auth.getUser()
    if (!user.user) throw new Error('Not authenticated')

    const { data, error } = await this.supabase
      .from('insights')
      .insert({
        project_id: projectId,
        insight,
        evidence_refs,
        tags,
        sentiment,
        created_by: user.user.id
      })
      .select()
      .single()

    if (error) throw error

    // Convert to memory
    const memory = await this.createMemory({
      label: `insight::${data.id.slice(0, 8)}`,
      type: MemoryType.PLAINTEXT,
      content: `Insight: ${insight}\nSupport: ${data.support_count}\nSentiment: ${sentiment}`,
      project_id: projectId,
      tags: ['insight', ...tags]
    })

    return {
      insight_id: data.id,
      memory_id: memory.id
    }
  }

  // Task-memory linking
  async linkMemoryToTask(memoryId: string, taskId: string, role: 'READ' | 'WRITE' = 'READ') {
    const { error } = await this.supabase
      .from('memory_task_links')
      .insert({
        memory_id: memoryId,
        task_id: taskId,
        role
      })

    if (error) throw error
  }

  async getTaskMemories(taskId: string): Promise<Memory[]> {
    const { data, error } = await this.supabase
      .from('memory_task_links')
      .select(`
        memories (
          *,
          memory_payloads(content, token_count)
        )
      `)
      .eq('task_id', taskId)

    if (error) throw error
    return data?.map(item => item.memories) || []
  }

  // Real-time subscriptions
  subscribeToMemoryChanges(
    projectId: string,
    callback: (payload: any) => void
  ): RealtimeChannel {
    this.realtimeChannel = this.supabase
      .channel('memory-changes')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'memories',
          filter: `project_id=eq.${projectId}`
        },
        callback
      )
      .subscribe()

    return this.realtimeChannel
  }

  unsubscribe() {
    if (this.realtimeChannel) {
      this.supabase.removeChannel(this.realtimeChannel)
    }
  }

  // Marketplace
  async searchMemoryPacks(query: string, maxPriceCents?: number): Promise<MemoryPack[]> {
    let q = this.supabase
      .from('memory_packs')
      .select('*, pack_memories(count)')
      .eq('published', true)
      .ilike('title', `%${query}%`)

    if (maxPriceCents !== undefined) {
      q = q.lte('price_cents', maxPriceCents)
    }

    const { data, error } = await q.limit(20)

    if (error) throw error
    return data || []
  }

  async importMemoryPack(packId: string): Promise<string[]> {
    const projectId = this.options.projectId
    if (!projectId) throw new Error('Project ID required')

    // Get pack memories
    const { data: packData, error: packError } = await this.supabase
      .from('pack_memories')
      .select('memories(*)')
      .eq('pack_id', packId)

    if (packError) throw packError

    // Import each memory
    const importedIds: string[] = []
    
    for (const item of packData || []) {
      const memory = item.memories
      try {
        const imported = await this.createMemory({
          label: `imported::${memory.label}`,
          type: memory.type,
          content: '', // Content would be fetched separately
          project_id: projectId,
          tags: ['imported', packId]
        })
        importedIds.push(imported.id)
      } catch (err) {
        console.error('Failed to import memory:', err)
      }
    }

    return importedIds
  }

  // Utility methods
  async getMemoryStats(projectId?: string): Promise<any> {
    const pid = projectId || this.options.projectId
    if (!pid) throw new Error('Project ID required')

    const { data, error } = await this.supabase
      .from('memory_stats')
      .select('*')
      .eq('project_id', pid)

    if (error) throw error
    return data
  }

  // Agent helper methods
  async enhancePrompt(
    prompt: string,
    taskId: string,
    agentId: string,
    tags?: string[],
    tokenBudget: number = 2000
  ): Promise<string> {
    const projectId = this.options.projectId
    if (!projectId) throw new Error('Project ID required')

    const scheduled = await this.scheduleMemories({
      agent_id: agentId,
      task_id: taskId,
      project_id: projectId,
      need_tags: tags,
      token_budget: tokenBudget
    })

    if (scheduled.memories.length === 0) {
      return prompt
    }

    // Inject memories into prompt
    const memorySection = scheduled.memories
      .map(m => m.content)
      .join('\n\n')

    if (prompt.includes('<MEMORIES>')) {
      return prompt.replace('<MEMORIES>', memorySection)
    } else {
      return `${memorySection}\n\n${prompt}`
    }
  }

  async captureExperience(
    label: string,
    content: string,
    tags?: string[]
  ): Promise<Memory> {
    const projectId = this.options.projectId
    if (!projectId) throw new Error('Project ID required')

    return this.createMemory({
      label,
      type: MemoryType.PLAINTEXT,
      content,
      project_id: projectId,
      tags: tags || []
    })
  }
}

// Export convenience function
export function createMemCubeClient(
  supabaseUrl: string,
  supabaseKey: string,
  projectId?: string
): MemCubeClient {
  return new MemCubeClient(supabaseUrl, supabaseKey, { projectId })
}