import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.38.0'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// Validation schemas
const ExecuteTaskSchema = z.object({
  agent_id: z.string(),
  task_id: z.string().uuid(),
  project_id: z.string().uuid(),
  action: z.enum(['start', 'pause', 'resume', 'complete', 'fail']),
  result: z.any().optional(),
  error: z.string().optional(),
  progress: z.number().min(0).max(100).optional()
})

const UpdateProgressSchema = z.object({
  agent_id: z.string(),
  task_id: z.string().uuid(),
  progress: z.number().min(0).max(100),
  status_message: z.string().optional(),
  intermediate_results: z.any().optional()
})

const RequestToolSchema = z.object({
  agent_id: z.string(),
  task_id: z.string().uuid(),
  tool_name: z.string(),
  parameters: z.record(z.any()),
  wait_for_result: z.boolean().default(false)
})

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient(supabaseUrl, supabaseServiceKey, {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
      }
    })

    const { pathname } = new URL(req.url)
    const pathParts = pathname.split('/').filter(Boolean)
    const action = pathParts[pathParts.length - 1]

    switch (action) {
      case 'execute-task':
        return await executeTask(supabase, await req.json())
      
      case 'update-progress':
        return await updateProgress(supabase, await req.json())
      
      case 'request-tool':
        return await requestTool(supabase, await req.json())
      
      case 'submit-result':
        return await submitResult(supabase, await req.json())
      
      case 'get-context':
        return await getExecutionContext(supabase, await req.json())
      
      case 'report-error':
        return await reportError(supabase, await req.json())
        
      default:
        throw new Error(`Unknown action: ${action}`)
    }

  } catch (error) {
    console.error('Error:', error)
    return new Response(
      JSON.stringify({ error: error.message }),
      { 
        status: 400,
        headers: { ...corsHeaders, 'Content-Type': 'application/json' }
      }
    )
  }
})

async function executeTask(supabase: any, params: any) {
  const validated = ExecuteTaskSchema.parse(params)
  
  // Verify agent owns the task
  const { data: task } = await supabase
    .from('tasks')
    .select('*')
    .eq('id', validated.task_id)
    .eq('assigned_to', validated.agent_id)
    .single()
  
  if (!task) {
    throw new Error('Task not found or not assigned to agent')
  }
  
  let newStatus: string
  let updateData: any = {
    updated_at: new Date().toISOString()
  }
  
  switch (validated.action) {
    case 'start':
      if (task.status !== 'PENDING' && task.status !== 'IN_PROGRESS') {
        throw new Error('Task cannot be started in current status')
      }
      newStatus = 'IN_PROGRESS'
      updateData.started_at = new Date().toISOString()
      break
      
    case 'pause':
      if (task.status !== 'IN_PROGRESS') {
        throw new Error('Only in-progress tasks can be paused')
      }
      newStatus = 'PENDING'
      updateData.paused_at = new Date().toISOString()
      break
      
    case 'resume':
      if (task.status !== 'PENDING' || !task.started_at) {
        throw new Error('Task cannot be resumed')
      }
      newStatus = 'IN_PROGRESS'
      updateData.resumed_at = new Date().toISOString()
      break
      
    case 'complete':
      if (task.status !== 'IN_PROGRESS') {
        throw new Error('Only in-progress tasks can be completed')
      }
      newStatus = 'COMPLETED'
      updateData.completed_at = new Date().toISOString()
      updateData.result = validated.result
      break
      
    case 'fail':
      newStatus = 'FAILED'
      updateData.failed_at = new Date().toISOString()
      updateData.error = validated.error
      break
      
    default:
      throw new Error('Invalid action')
  }
  
  // Update task
  const { data: updatedTask, error: updateError } = await supabase
    .from('tasks')
    .update({
      ...updateData,
      status: newStatus
    })
    .eq('id', validated.task_id)
    .select()
    .single()
  
  if (updateError) {
    throw new Error(`Failed to update task: ${updateError.message}`)
  }
  
  // Update FSA state
  await supabase.functions.invoke('fsa-state/update', {
    body: {
      project_id: validated.project_id,
      fsa_id: `project-${validated.project_id}`,
      delta: [
        {
          op: 'set',
          path: ['tasks', task.task_id, 'status'],
          value: newStatus
        },
        {
          op: 'set',
          path: ['tasks', task.task_id, 'last_action'],
          value: validated.action
        },
        {
          op: 'set',
          path: ['tasks', task.task_id, 'last_update'],
          value: new Date().toISOString()
        }
      ],
      actor: validated.agent_id,
      lineage_id: `task-${validated.action}-${validated.task_id}`
    }
  })
  
  // Update agent state if needed
  if (validated.action === 'complete' || validated.action === 'fail') {
    await supabase
      .from('agents')
      .update({
        current_task_id: null,
        status: 'ONLINE',
        tasks_completed: validated.action === 'complete' 
          ? supabase.rpc('increment', { value: 1 })
          : undefined,
        tasks_failed: validated.action === 'fail'
          ? supabase.rpc('increment', { value: 1 })
          : undefined
      })
      .eq('agent_id', validated.agent_id)
  }
  
  // Emit event
  await supabase
    .from('events')
    .insert({
      type: `task.${validated.action}`,
      source: validated.agent_id,
      data: {
        task_id: validated.task_id,
        action: validated.action,
        result: validated.result,
        error: validated.error
      },
      project_id: validated.project_id
    })
  
  return new Response(
    JSON.stringify({
      success: true,
      task: updatedTask,
      next_action: validated.action === 'complete' ? 'get_next_task' : null
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function updateProgress(supabase: any, params: any) {
  const validated = UpdateProgressSchema.parse(params)
  
  // Verify agent owns the task
  const { data: task } = await supabase
    .from('tasks')
    .select('*')
    .eq('id', validated.task_id)
    .eq('assigned_to', validated.agent_id)
    .eq('status', 'IN_PROGRESS')
    .single()
  
  if (!task) {
    throw new Error('Task not found, not assigned to agent, or not in progress')
  }
  
  // Create progress update
  const { error: progressError } = await supabase
    .from('task_progress')
    .insert({
      task_id: validated.task_id,
      agent_id: validated.agent_id,
      progress: validated.progress,
      message: validated.status_message,
      data: validated.intermediate_results
    })
  
  if (progressError) {
    throw new Error(`Failed to record progress: ${progressError.message}`)
  }
  
  // Update FSA state with progress
  await supabase.functions.invoke('fsa-state/update', {
    body: {
      project_id: task.project_id,
      fsa_id: `project-${task.project_id}`,
      delta: [
        {
          op: 'set',
          path: ['tasks', task.task_id, 'progress'],
          value: validated.progress
        },
        {
          op: 'set',
          path: ['tasks', task.task_id, 'last_progress_update'],
          value: new Date().toISOString()
        }
      ],
      actor: validated.agent_id,
      lineage_id: `progress-${validated.task_id}`
    }
  })
  
  // Emit progress event if significant milestone
  if (validated.progress % 25 === 0) {
    await supabase
      .from('events')
      .insert({
        type: 'task.progress',
        source: validated.agent_id,
        data: {
          task_id: validated.task_id,
          progress: validated.progress,
          message: validated.status_message
        },
        project_id: task.project_id
      })
  }
  
  return new Response(
    JSON.stringify({
      success: true,
      progress: validated.progress
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function requestTool(supabase: any, params: any) {
  const validated = RequestToolSchema.parse(params)
  
  // Verify agent is working on task
  const { data: task } = await supabase
    .from('tasks')
    .select('project_id')
    .eq('id', validated.task_id)
    .eq('assigned_to', validated.agent_id)
    .single()
  
  if (!task) {
    throw new Error('Task not found or not assigned to agent')
  }
  
  // Create execution request
  const { data: request, error } = await supabase
    .from('execution_requests')
    .insert({
      agent_id: validated.agent_id,
      project_id: task.project_id,
      tool_name: validated.tool_name,
      parameters: validated.parameters,
      task_id: validated.task_id,
      priority: 75 // Higher priority for active task execution
    })
    .select()
    .single()
  
  if (error) {
    throw new Error(`Failed to create tool request: ${error.message}`)
  }
  
  // If wait_for_result, poll for completion
  if (validated.wait_for_result) {
    const result = await waitForToolResult(supabase, request.id)
    
    return new Response(
      JSON.stringify({
        request_id: request.id,
        status: 'completed',
        result
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  
  return new Response(
    JSON.stringify({
      request_id: request.id,
      status: 'queued',
      message: 'Tool execution queued'
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function submitResult(supabase: any, params: any) {
  const { agent_id, task_id, result, artifacts = {} } = params
  
  // Verify task ownership
  const { data: task } = await supabase
    .from('tasks')
    .select('*')
    .eq('id', task_id)
    .eq('assigned_to', agent_id)
    .eq('status', 'IN_PROGRESS')
    .single()
  
  if (!task) {
    throw new Error('Task not found, not assigned to agent, or not in progress')
  }
  
  // Store result
  const { data: resultData, error } = await supabase
    .from('task_results')
    .insert({
      task_id,
      agent_id,
      result,
      artifacts
    })
    .select()
    .single()
  
  if (error) {
    throw new Error(`Failed to store result: ${error.message}`)
  }
  
  // Store artifacts in MemCube
  if (Object.keys(artifacts).length > 0) {
    for (const [key, value] of Object.entries(artifacts)) {
      await supabase.functions.invoke('memories-crud/create', {
        body: {
          project_id: task.project_id,
          label: `task-${task.task_id}-${key}`,
          content: JSON.stringify(value),
          type: 'JSON',
          metadata: {
            task_id: task.task_id,
            artifact_key: key,
            agent_id
          }
        }
      })
    }
  }
  
  // Update task with result reference
  await supabase
    .from('tasks')
    .update({
      result_id: resultData.id,
      has_artifacts: Object.keys(artifacts).length > 0
    })
    .eq('id', task_id)
  
  return new Response(
    JSON.stringify({
      success: true,
      result_id: resultData.id,
      artifacts_stored: Object.keys(artifacts).length
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function getExecutionContext(supabase: any, params: any) {
  const { agent_id, task_id } = params
  
  // Get task details
  const { data: task } = await supabase
    .from('tasks')
    .select('*')
    .eq('id', task_id)
    .eq('assigned_to', agent_id)
    .single()
  
  if (!task) {
    throw new Error('Task not found or not assigned to agent')
  }
  
  // Get project context from FSA
  const { data: fsaState } = await supabase.functions.invoke('fsa-query/slice', {
    body: {
      project_id: task.project_id,
      fsa_id: `project-${task.project_id}`,
      pattern: `context:*`,
      use_cache: true
    }
  })
  
  const projectContext = await fsaState.json()
  
  // Get related memories
  const { data: memories } = await supabase.functions.invoke('memories-search/semantic', {
    body: {
      project_id: task.project_id,
      query: `${task.type} ${task.title}`,
      limit: 5,
      threshold: 0.7
    }
  })
  
  const relatedMemories = await memories.json()
  
  // Get dependency status
  let dependencies = []
  if (task.depends_on && task.depends_on.length > 0) {
    const { data: depTasks } = await supabase
      .from('tasks')
      .select('task_id, status, completed_at')
      .eq('project_id', task.project_id)
      .in('task_id', task.depends_on)
    
    dependencies = depTasks || []
  }
  
  // Get agent's recent tool usage
  const { data: recentTools } = await supabase
    .from('tool_executions')
    .select('tool_id, tools!inner(name, type), result')
    .eq('agent_id', agent_id)
    .eq('project_id', task.project_id)
    .order('started_at', { ascending: false })
    .limit(10)
  
  return new Response(
    JSON.stringify({
      task,
      project_context: projectContext.slice || {},
      related_memories: relatedMemories.results || [],
      dependencies,
      recent_tools: recentTools || [],
      agent_capabilities: await getAgentCapabilities(supabase, agent_id)
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function reportError(supabase: any, params: any) {
  const { agent_id, task_id, error, severity = 'error', context = {} } = params
  
  // Log error
  const { error: logError } = await supabase
    .from('agent_errors')
    .insert({
      agent_id,
      task_id,
      error_message: error,
      severity,
      context,
      occurred_at: new Date().toISOString()
    })
  
  if (logError) {
    console.error('Failed to log error:', logError)
  }
  
  // Update agent error count
  await supabase
    .from('agent_sessions')
    .update({
      errors_count: supabase.rpc('increment', { value: 1 })
    })
    .eq('agent_id', agent_id)
    .is('ended_at', null)
  
  // Emit error event for monitoring
  await supabase
    .from('events')
    .insert({
      type: 'agent.error',
      source: agent_id,
      data: {
        task_id,
        error,
        severity,
        context
      },
      project_id: context.project_id
    })
  
  // Determine if task should be reassigned
  if (severity === 'critical') {
    // Mark task as failed and trigger reassignment
    await supabase
      .from('tasks')
      .update({
        status: 'FAILED',
        error_message: error,
        needs_reassignment: true
      })
      .eq('id', task_id)
    
    return new Response(
      JSON.stringify({
        success: true,
        action: 'task_failed',
        reassignment_requested: true
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  
  return new Response(
    JSON.stringify({
      success: true,
      logged: true
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

// Helper functions

async function waitForToolResult(supabase: any, requestId: string, maxWaitMs: number = 30000): Promise<any> {
  const startTime = Date.now()
  const pollIntervalMs = 500
  
  while (Date.now() - startTime < maxWaitMs) {
    const { data: request } = await supabase
      .from('execution_requests')
      .select('status, result, error')
      .eq('id', requestId)
      .single()
    
    if (!request) {
      throw new Error('Request not found')
    }
    
    if (request.status === 'completed') {
      return request.result
    }
    
    if (request.status === 'failed') {
      throw new Error(`Tool execution failed: ${request.error}`)
    }
    
    // Wait before next poll
    await new Promise(resolve => setTimeout(resolve, pollIntervalMs))
  }
  
  throw new Error('Tool execution timeout')
}

async function getAgentCapabilities(supabase: any, agentId: string): Promise<any> {
  const { data: capabilities } = await supabase
    .from('agent_capabilities')
    .select('capability, proficiency_level')
    .eq('agent_id', agentId)
    .eq('verified', true)
  
  const { data: agent } = await supabase
    .from('agents')
    .select('capabilities, aml_level')
    .eq('agent_id', agentId)
    .single()
  
  return {
    verified_capabilities: capabilities || [],
    declared_capabilities: agent?.capabilities || [],
    aml_level: agent?.aml_level || 'AML1'
  }
}

// Additional tables needed for this function

/*
CREATE TABLE task_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    progress INTEGER NOT NULL CHECK (progress >= 0 AND progress <= 100),
    message TEXT,
    data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE task_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    result JSONB NOT NULL,
    artifacts JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE agent_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    task_id UUID REFERENCES tasks(id),
    error_message TEXT NOT NULL,
    severity TEXT NOT NULL, -- 'warning', 'error', 'critical'
    context JSONB DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL
);

-- Add to tasks table
ALTER TABLE tasks ADD COLUMN result_id UUID REFERENCES task_results(id);
ALTER TABLE tasks ADD COLUMN has_artifacts BOOLEAN DEFAULT false;
ALTER TABLE tasks ADD COLUMN error_message TEXT;
ALTER TABLE tasks ADD COLUMN needs_reassignment BOOLEAN DEFAULT false;
*/