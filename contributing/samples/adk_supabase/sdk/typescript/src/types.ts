// Extended type definitions for ADK Supabase SDK

export interface Project {
  id: string
  name: string
  description?: string
  tenant_id: string
  budget_total: number
  budget_spent: number
  created_by: string
  created_at: string
  updated_at: string
  archived: boolean
}

export interface FSAStateVersion {
  id: string
  project_id: string
  fsa_id: string
  version: number
  parent_version?: number
  state: Record<string, any>
  actor: string
  lineage_id?: string
  created_at: string
}

export interface FSASliceResult {
  project_id: string
  fsa_id: string
  version: number
  slice: Record<string, any>
  summary: string
  pattern: string
  cached: boolean
}

export interface MemoryPack {
  id: string
  name: string
  description?: string
  created_by: string
  created_at: string
  updated_at: string
}

export interface MemorySearchResult {
  memory: Memory
  similarity: number
  highlights?: string[]
}

export interface TaskProgress {
  id: string
  task_id: string
  agent_id: string
  progress: number
  message?: string
  data?: any
  created_at: string
}

export interface TaskResult {
  id: string
  task_id: string
  agent_id: string
  result: any
  artifacts: Record<string, any>
  created_at: string
}

export interface Tool {
  id: string
  name: string
  type: 'code_execution' | 'api_call' | 'file_operation' | string
  description?: string
  parameters: Record<string, any>
  required_aml_level: 'AML0' | 'AML1' | 'AML2' | 'AML3' | 'AML4'
  requires_approval: boolean
  enabled: boolean
}

export interface ToolExecution {
  id: string
  tool_id: string
  project_id: string
  task_id?: string
  agent_id: string
  parameters: Record<string, any>
  result?: any
  error?: string
  started_at: string
  completed_at?: string
  duration_ms?: number
}

export interface Workflow {
  id: string
  project_id: string
  name: string
  description?: string
  steps: WorkflowStep[]
  trigger_type?: 'manual' | 'schedule' | 'event'
  trigger_config?: any
  enabled: boolean
}

export interface WorkflowStep {
  type: 'tool' | 'condition' | 'parallel' | 'sequence'
  name: string
  config: any
  next?: string | string[]
}

export interface AgentSession {
  id: string
  agent_id: string
  project_id: string
  started_at: string
  last_activity: string
  ended_at?: string
  tasks_worked: number
  tokens_used: number
  errors_count: number
}

export interface Event {
  id: string
  type: string
  source: string
  data: any
  project_id?: string
  target_agent?: string
  processed: boolean
  processed_at?: string
  processed_by?: string
  created_at: string
  expires_at: string
}

export interface Metric {
  id: string
  project_id: string
  name: string
  type: 'counter' | 'gauge' | 'histogram'
  value: number
  labels: Record<string, any>
  timestamp: string
}

export interface Resource {
  id: string
  project_id: string
  name: string
  type: string
  unit: string
  quota_amount?: number
  used_amount: number
  cost_per_unit?: number
}

export interface PolicyRule {
  id: string
  project_id: string
  name: string
  type: 'budget' | 'resource' | 'aml' | 'custom'
  condition: any
  action: any
  enabled: boolean
  last_triggered?: string
  trigger_count: number
}

export interface HealthCheck {
  status: 'healthy' | 'degraded' | 'unhealthy'
  checks: Record<string, {
    status: 'ok' | 'warning' | 'error'
    [key: string]: any
  }>
  timestamp: string
  error?: string
}

// Error types
export class ADKError extends Error {
  constructor(
    message: string,
    public code: string,
    public details?: any
  ) {
    super(message)
    this.name = 'ADKError'
  }
}

export class ProjectNotFoundError extends ADKError {
  constructor(projectId: string) {
    super(`Project ${projectId} not found`, 'PROJECT_NOT_FOUND', { projectId })
  }
}

export class TaskNotFoundError extends ADKError {
  constructor(taskId: string) {
    super(`Task ${taskId} not found`, 'TASK_NOT_FOUND', { taskId })
  }
}

export class AgentNotAuthorizedError extends ADKError {
  constructor(agentId: string, resource: string) {
    super(`Agent ${agentId} not authorized for ${resource}`, 'AGENT_NOT_AUTHORIZED', { agentId, resource })
  }
}

export class MemoryNotFoundError extends ADKError {
  constructor(memoryId: string) {
    super(`Memory ${memoryId} not found`, 'MEMORY_NOT_FOUND', { memoryId })
  }
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

export type AsyncCallback<T> = (data: T) => void | Promise<void>

export interface PaginationParams {
  limit?: number
  offset?: number
  order_by?: string
  order?: 'asc' | 'desc'
}

export interface BatchOperation<T> {
  operation: 'create' | 'update' | 'delete'
  data: T
}

// Re-export base types from index
export type { 
  ADKConfig,
  FSAState,
  FSADelta,
  Memory,
  Task,
  Agent,
  ToolExecution as ToolExecutionRequest
} from './index'