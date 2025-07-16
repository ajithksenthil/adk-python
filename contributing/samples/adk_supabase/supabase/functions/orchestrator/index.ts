import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.38.0'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// Validation schemas
const CreateProjectSchema = z.object({
  name: z.string().min(1),
  description: z.string().optional(),
  tenant_id: z.string(),
  budget_total: z.number().positive().optional(),
  agents: z.array(z.string()).optional()
})

const CreateTaskSchema = z.object({
  project_id: z.string().uuid(),
  task_id: z.string().regex(/^[A-Z]+_[0-9]+$/),
  type: z.string(),
  title: z.string(),
  description: z.string().optional(),
  priority: z.number().int().optional(),
  depends_on: z.array(z.string()).optional(),
  estimated_hours: z.number().positive().optional(),
  assigned_to: z.string().optional()
})

const ExecuteToolSchema = z.object({
  agent_id: z.string(),
  project_id: z.string().uuid(),
  tool_name: z.string(),
  parameters: z.record(z.any()),
  task_id: z.string().uuid().optional(),
  requires_approval: z.boolean().optional()
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
      case 'create-project':
        return await createProject(supabase, await req.json())
      
      case 'create-task':
        return await createTask(supabase, await req.json())
      
      case 'assign-task':
        return await assignTask(supabase, await req.json())
      
      case 'get-next-task':
        return await getNextTask(supabase, await req.json())
      
      case 'execute-tool':
        return await executeTool(supabase, await req.json())
      
      case 'complete-task':
        return await completeTask(supabase, await req.json())
      
      case 'agent-heartbeat':
        return await agentHeartbeat(supabase, await req.json())
        
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

async function createProject(supabase: any, params: any) {
  const validated = CreateProjectSchema.parse(params)
  
  // Create project
  const { data: project, error } = await supabase
    .from('projects')
    .insert({
      name: validated.name,
      description: validated.description,
      tenant_id: validated.tenant_id,
      budget_total: validated.budget_total || 0,
      created_by: validated.tenant_id // Could be actual user ID
    })
    .select()
    .single()
  
  if (error) {
    throw new Error(`Failed to create project: ${error.message}`)
  }
  
  // Initialize FSA state for project
  await supabase.functions.invoke('fsa-state/update', {
    body: {
      project_id: project.id,
      fsa_id: `project-${project.id}`,
      state: {
        project: {
          id: project.id,
          name: project.name,
          status: 'active',
          created_at: project.created_at
        },
        tasks: {},
        agents: {},
        metrics: {
          tasks_total: 0,
          tasks_completed: 0,
          budget_spent: 0
        },
        resources: {}
      },
      actor: 'system',
      lineage_id: `project-init-${project.id}`
    }
  })
  
  // Register agents if provided
  if (validated.agents && validated.agents.length > 0) {
    for (const agentId of validated.agents) {
      await registerAgentToProject(supabase, agentId, project.id)
    }
  }
  
  // Emit event
  await supabase
    .from('events')
    .insert({
      type: 'project.created',
      source: 'orchestrator',
      data: { project },
      project_id: project.id
    })
  
  return new Response(
    JSON.stringify({
      project,
      fsa_id: `project-${project.id}`
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function createTask(supabase: any, params: any) {
  const validated = CreateTaskSchema.parse(params)
  
  // Create task
  const { data: task, error } = await supabase
    .from('tasks')
    .insert({
      ...validated,
      created_by: 'orchestrator' // Could track actual creator
    })
    .select()
    .single()
  
  if (error) {
    throw new Error(`Failed to create task: ${error.message}`)
  }
  
  // Update FSA state
  await supabase.functions.invoke('fsa-state/update', {
    body: {
      project_id: validated.project_id,
      fsa_id: `project-${validated.project_id}`,
      delta: [
        {
          op: 'set',
          path: ['tasks', validated.task_id],
          value: {
            id: task.id,
            task_id: validated.task_id,
            type: validated.type,
            title: validated.title,
            status: 'PENDING',
            created_at: task.created_at
          }
        },
        {
          op: 'inc',
          path: ['metrics', 'tasks_total'],
          value: 1
        }
      ],
      actor: 'orchestrator',
      lineage_id: `task-create-${task.id}`
    }
  })
  
  // Emit event
  await supabase
    .from('events')
    .insert({
      type: 'task.created',
      source: 'orchestrator',
      data: { task },
      project_id: validated.project_id
    })
  
  // Try auto-assignment
  if (!validated.assigned_to) {
    await tryAutoAssign(supabase, task)
  }
  
  return new Response(
    JSON.stringify({ task }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function assignTask(supabase: any, params: any) {
  const { task_id, agent_id } = params
  
  // Update task
  const { data: task, error } = await supabase
    .from('tasks')
    .update({
      assigned_to: agent_id,
      assigned_at: new Date().toISOString(),
      status: 'IN_PROGRESS'
    })
    .eq('id', task_id)
    .select()
    .single()
  
  if (error) {
    throw new Error(`Failed to assign task: ${error.message}`)
  }
  
  // Update agent
  await supabase
    .from('agents')
    .update({
      current_task_id: task_id,
      status: 'BUSY'
    })
    .eq('agent_id', agent_id)
  
  // Update FSA state
  await supabase.functions.invoke('fsa-state/update', {
    body: {
      project_id: task.project_id,
      fsa_id: `project-${task.project_id}`,
      delta: [
        {
          op: 'set',
          path: ['tasks', task.task_id, 'status'],
          value: 'IN_PROGRESS'
        },
        {
          op: 'set',
          path: ['tasks', task.task_id, 'assigned_to'],
          value: agent_id
        },
        {
          op: 'set',
          path: ['agents', agent_id, 'current_task'],
          value: task.task_id
        }
      ],
      actor: 'orchestrator',
      lineage_id: `task-assign-${task_id}`
    }
  })
  
  return new Response(
    JSON.stringify({ 
      success: true,
      task_id,
      agent_id 
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function getNextTask(supabase: any, params: any) {
  const { agent_id } = params
  
  // Check if agent exists and is available
  const { data: agent } = await supabase
    .from('agents')
    .select('*')
    .eq('agent_id', agent_id)
    .single()
  
  if (!agent || agent.status !== 'ONLINE') {
    throw new Error('Agent not available')
  }
  
  // Get next task using database function
  const { data: taskId } = await supabase
    .rpc('get_next_task_for_agent', {
      p_agent_id: agent_id
    })
  
  if (!taskId) {
    return new Response(
      JSON.stringify({ 
        task: null,
        message: 'No tasks available' 
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  
  // Get full task details
  const { data: task } = await supabase
    .from('tasks')
    .select('*')
    .eq('id', taskId)
    .single()
  
  return new Response(
    JSON.stringify({ task }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function executeTool(supabase: any, params: any) {
  const validated = ExecuteToolSchema.parse(params)
  
  // Check tool exists and agent has permission
  const { data: hasPermission } = await supabase
    .rpc('check_tool_permission', {
      p_agent_id: validated.agent_id,
      p_tool_name: validated.tool_name
    })
  
  if (!hasPermission) {
    throw new Error('Agent does not have permission to use this tool')
  }
  
  // Get tool details
  const { data: tool } = await supabase
    .from('tools')
    .select('*')
    .eq('name', validated.tool_name)
    .single()
  
  if (!tool) {
    throw new Error('Tool not found')
  }
  
  // Create execution request
  const { data: request, error } = await supabase
    .from('execution_requests')
    .insert({
      agent_id: validated.agent_id,
      project_id: validated.project_id,
      tool_name: validated.tool_name,
      parameters: validated.parameters,
      priority: 50 // Default priority
    })
    .select()
    .single()
  
  if (error) {
    throw new Error(`Failed to create execution request: ${error.message}`)
  }
  
  // If requires approval, wait for it
  if (tool.requires_approval || validated.requires_approval) {
    return new Response(
      JSON.stringify({
        request_id: request.id,
        status: 'pending_approval',
        message: 'Tool execution requires approval'
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  
  // Execute tool immediately
  const result = await executeToolRequest(supabase, request, tool)
  
  return new Response(
    JSON.stringify({
      request_id: request.id,
      status: 'completed',
      result
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function completeTask(supabase: any, params: any) {
  const { task_id, agent_id, result, actual_hours } = params
  
  // Update task
  const { data: task, error } = await supabase
    .from('tasks')
    .update({
      status: 'COMPLETED',
      completed_at: new Date().toISOString(),
      actual_hours
    })
    .eq('id', task_id)
    .eq('assigned_to', agent_id) // Ensure agent owns the task
    .select()
    .single()
  
  if (error) {
    throw new Error(`Failed to complete task: ${error.message}`)
  }
  
  // Update agent
  await supabase
    .from('agents')
    .update({
      current_task_id: null,
      status: 'ONLINE',
      tasks_completed: supabase.rpc('increment', { value: 1 })
    })
    .eq('agent_id', agent_id)
  
  // Update FSA state
  await supabase.functions.invoke('fsa-state/update', {
    body: {
      project_id: task.project_id,
      fsa_id: `project-${task.project_id}`,
      delta: [
        {
          op: 'set',
          path: ['tasks', task.task_id, 'status'],
          value: 'COMPLETED'
        },
        {
          op: 'set',
          path: ['tasks', task.task_id, 'completed_at'],
          value: new Date().toISOString()
        },
        {
          op: 'unset',
          path: ['agents', agent_id, 'current_task']
        },
        {
          op: 'inc',
          path: ['metrics', 'tasks_completed'],
          value: 1
        }
      ],
      actor: agent_id,
      lineage_id: `task-complete-${task_id}`
    }
  })
  
  // Check for unblocked tasks
  await checkUnblockedTasks(supabase, task)
  
  return new Response(
    JSON.stringify({ 
      success: true,
      task_id,
      next_task_available: true // Could check
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function agentHeartbeat(supabase: any, params: any) {
  const { agent_id, project_id, status = 'ONLINE' } = params
  
  // Update agent status
  await supabase
    .from('agents')
    .update({
      status,
      last_heartbeat: new Date().toISOString()
    })
    .eq('agent_id', agent_id)
  
  // Update or create session
  const { data: session } = await supabase
    .from('agent_sessions')
    .select('*')
    .eq('agent_id', agent_id)
    .eq('project_id', project_id)
    .is('ended_at', null)
    .single()
  
  if (session) {
    await supabase
      .from('agent_sessions')
      .update({
        last_activity: new Date().toISOString()
      })
      .eq('id', session.id)
  } else {
    await supabase
      .from('agent_sessions')
      .insert({
        agent_id,
        project_id
      })
  }
  
  // Update FSA state
  await supabase.functions.invoke('fsa-state/update', {
    body: {
      project_id,
      fsa_id: `project-${project_id}`,
      delta: [{
        op: 'set',
        path: ['agents', agent_id, 'last_heartbeat'],
        value: new Date().toISOString()
      }],
      actor: agent_id,
      lineage_id: `heartbeat-${agent_id}`
    }
  })
  
  return new Response(
    JSON.stringify({ 
      success: true,
      agent_id,
      status 
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

// Helper functions

async function registerAgentToProject(supabase: any, agentId: string, projectId: string) {
  // Ensure agent exists
  const { data: agent } = await supabase
    .from('agents')
    .select('*')
    .eq('agent_id', agentId)
    .single()
  
  if (!agent) {
    // Create agent
    await supabase
      .from('agents')
      .insert({
        agent_id: agentId,
        name: agentId,
        type: 'generic'
      })
  }
  
  // Create session
  await supabase
    .from('agent_sessions')
    .insert({
      agent_id: agentId,
      project_id: projectId
    })
}

async function tryAutoAssign(supabase: any, task: any) {
  // Simple auto-assignment based on task type
  const { data: agents } = await supabase
    .from('agents')
    .select('*')
    .eq('status', 'ONLINE')
    .is('current_task_id', null)
    .contains('capabilities', [task.type])
    .limit(1)
  
  if (agents && agents.length > 0) {
    await assignTask(supabase, {
      task_id: task.id,
      agent_id: agents[0].agent_id
    })
  }
}

async function executeToolRequest(supabase: any, request: any, tool: any) {
  // Record execution start
  const { data: execution, error } = await supabase
    .from('tool_executions')
    .insert({
      tool_id: tool.id,
      project_id: request.project_id,
      agent_id: request.agent_id,
      parameters: request.parameters,
      started_at: new Date().toISOString()
    })
    .select()
    .single()
  
  if (error) {
    throw new Error(`Failed to record execution: ${error.message}`)
  }
  
  try {
    // Execute based on tool type
    let result: any
    
    switch (tool.type) {
      case 'code_execution':
        result = await executeCode(tool.name, request.parameters)
        break
        
      case 'api_call':
        result = await makeApiCall(request.parameters)
        break
        
      case 'file_operation':
        result = await performFileOperation(tool.name, request.parameters)
        break
        
      default:
        throw new Error(`Unknown tool type: ${tool.type}`)
    }
    
    // Record success
    await supabase
      .from('tool_executions')
      .update({
        result,
        completed_at: new Date().toISOString(),
        duration_ms: Date.now() - new Date(execution.started_at).getTime()
      })
      .eq('id', execution.id)
    
    // Update usage
    await supabase.rpc('record_tool_usage', {
      p_agent_id: request.agent_id,
      p_tool_id: tool.id
    })
    
    return result
    
  } catch (error) {
    // Record failure
    await supabase
      .from('tool_executions')
      .update({
        error: error.message,
        completed_at: new Date().toISOString()
      })
      .eq('id', execution.id)
    
    throw error
  }
}

async function executeCode(toolName: string, params: any): Promise<any> {
  // In production, this would execute in a sandboxed environment
  switch (toolName) {
    case 'bash':
      return { output: `Executed: ${params.command}`, exit_code: 0 }
      
    case 'python':
      return { output: `Python executed: ${params.code.slice(0, 50)}...`, result: null }
      
    default:
      throw new Error(`Unknown code tool: ${toolName}`)
  }
}

async function makeApiCall(params: any): Promise<any> {
  // In production, would make actual HTTP request
  return {
    status: 200,
    body: { message: 'Mock API response' },
    headers: {}
  }
}

async function performFileOperation(toolName: string, params: any): Promise<any> {
  // In production, would perform actual file operations
  switch (toolName) {
    case 'read_file':
      return { content: 'Mock file content', size: 1024 }
      
    case 'write_file':
      return { success: true, bytes_written: params.content.length }
      
    default:
      throw new Error(`Unknown file tool: ${toolName}`)
  }
}

async function checkUnblockedTasks(supabase: any, completedTask: any) {
  // Find tasks that were blocked by this one
  const { data: blockedTasks } = await supabase
    .from('tasks')
    .select('*')
    .eq('project_id', completedTask.project_id)
    .contains('depends_on', [completedTask.task_id])
  
  for (const task of blockedTasks || []) {
    // Check if all dependencies are now completed
    const { data: incompleteDeps } = await supabase
      .from('tasks')
      .select('task_id')
      .eq('project_id', task.project_id)
      .in('task_id', task.depends_on)
      .neq('status', 'COMPLETED')
    
    if (!incompleteDeps || incompleteDeps.length === 0) {
      // Task is now unblocked, try to assign
      await tryAutoAssign(supabase, task)
    }
  }
}