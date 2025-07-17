declare module '@adk/supabase-sdk' {
  export interface Task {
    id: string
    project_id: string
    description: string
    cost_estimate: number
    creator_id: string
    assigned_agent?: string
    status: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED' | 'BLOCKED'
    dependencies: string[]
    created_at: string
    updated_at: string
  }

  export interface FSAState {
    current_state: string
    transitions: Record<string, string>
    state_data: any
  }

  export interface Memory {
    id: string
    project_id: string
    label: string
    type: 'PLAINTEXT' | 'SEMANTIC' | 'COMMAND' | 'TEMPLATE'
    content?: string
    content_url?: string
    embedding?: number[]
    created_at: string
  }

  export class ADKClient {
    constructor(supabase: any)
    
    // FSA methods
    async getState(fsaId: string, slice?: string[]): Promise<FSAState>
    async updateState(fsaId: string, state: FSAState, actor: string): Promise<number>
    async applyDelta(fsaId: string, operations: any[], actor: string): Promise<FSAState>
    subscribeToState(fsaId: string, callback: (state: FSAState) => void): () => void
    
    // Task methods
    async createTask(task: Partial<Task>): Promise<Task>
    async getTask(taskId: string): Promise<Task>
    async updateTask(taskId: string, updates: Partial<Task>): Promise<Task>
    async getTasks(status?: Task['status']): Promise<Task[]>
    subscribeToTasks(callback: (task: Task) => void): () => void
    
    // Memory methods
    async createMemory(label: string, content: string, type?: Memory['type']): Promise<Memory>
    async searchMemories(query: string, projectId: string, limit?: number): Promise<Memory[]>
    async getMemory(memoryId: string): Promise<Memory>
  }
}