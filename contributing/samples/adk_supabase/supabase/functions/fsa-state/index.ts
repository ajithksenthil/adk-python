import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.38.0'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// Input validation schemas
const StateUpdateSchema = z.object({
  project_id: z.string().uuid(),
  fsa_id: z.string(),
  state: z.record(z.any()).optional(),
  delta: z.array(z.object({
    op: z.enum(['set', 'inc', 'push', 'unset']),
    path: z.array(z.string()),
    value: z.any().optional()
  })).optional(),
  actor: z.string(),
  lineage_id: z.string().optional()
})

const StateQuerySchema = z.object({
  project_id: z.string().uuid(),
  fsa_id: z.string(),
  version: z.number().int().positive().optional(),
  include_delta_history: z.boolean().optional()
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
      case 'get':
        return await getState(supabase, await req.json())
      
      case 'update':
        return await updateState(supabase, await req.json())
      
      case 'merge':
        return await mergeStates(supabase, await req.json())
      
      case 'history':
        return await getStateHistory(supabase, await req.json())
      
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

async function getState(supabase: any, params: any) {
  const validated = StateQuerySchema.parse(params)
  
  // Get latest state or specific version
  let query = supabase
    .from('fsa_states')
    .select('*')
    .eq('project_id', validated.project_id)
    .eq('fsa_id', validated.fsa_id)
    
  if (validated.version) {
    query = query.eq('version', validated.version)
  } else {
    query = query.order('version', { ascending: false }).limit(1)
  }
  
  const { data, error } = await query.single()
  
  if (error || !data) {
    // Return empty state for new FSA
    return new Response(
      JSON.stringify({
        project_id: validated.project_id,
        fsa_id: validated.fsa_id,
        version: 0,
        state: {},
        lineage_version: 0
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  
  // Include delta history if requested
  let deltas = []
  if (validated.include_delta_history) {
    const { data: deltaData } = await supabase
      .from('fsa_deltas')
      .select('*')
      .eq('state_id', data.id)
      .order('applied_at', { ascending: true })
    
    deltas = deltaData || []
  }
  
  return new Response(
    JSON.stringify({
      ...data,
      lineage_version: data.version,
      deltas: deltas
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function updateState(supabase: any, params: any) {
  const validated = StateUpdateSchema.parse(params)
  
  // Get current version
  const currentVersion = await getCurrentVersion(supabase, validated.project_id, validated.fsa_id)
  const newVersion = currentVersion + 1
  
  // Get current state if applying delta
  let newState = validated.state || {}
  
  if (validated.delta && validated.delta.length > 0) {
    // Fetch current state
    const { data: currentStateData } = await supabase
      .from('fsa_states')
      .select('state')
      .eq('project_id', validated.project_id)
      .eq('fsa_id', validated.fsa_id)
      .eq('version', currentVersion)
      .single()
    
    const currentState = currentStateData?.state || {}
    
    // Apply delta operations
    newState = await applyDeltaOperations(currentState, validated.delta)
  }
  
  // Create new state version
  const { data: stateData, error: stateError } = await supabase
    .from('fsa_states')
    .insert({
      project_id: validated.project_id,
      fsa_id: validated.fsa_id,
      version: newVersion,
      parent_version: currentVersion > 0 ? currentVersion : null,
      state: newState,
      actor: validated.actor,
      lineage_id: validated.lineage_id
    })
    .select()
    .single()
  
  if (stateError) {
    throw new Error(`Failed to create state: ${stateError.message}`)
  }
  
  // Store delta if provided
  if (validated.delta && validated.delta.length > 0) {
    await supabase
      .from('fsa_deltas')
      .insert({
        state_id: stateData.id,
        operations: validated.delta,
        actor: validated.actor,
        lineage_id: validated.lineage_id
      })
  }
  
  // Notify via realtime
  await supabase
    .from('events')
    .insert({
      type: 'fsa.state.updated',
      source: 'fsa-state-function',
      data: {
        project_id: validated.project_id,
        fsa_id: validated.fsa_id,
        version: newVersion,
        actor: validated.actor
      },
      project_id: validated.project_id
    })
  
  return new Response(
    JSON.stringify({
      success: true,
      version: newVersion,
      state_id: stateData.id,
      lineage_version: newVersion
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function mergeStates(supabase: any, params: any) {
  // Merge multiple state branches (for conflict resolution)
  const { project_id, fsa_id, versions, strategy = 'last-write-wins', actor } = params
  
  if (!versions || versions.length < 2) {
    throw new Error('At least 2 versions required for merge')
  }
  
  // Fetch all versions
  const { data: states } = await supabase
    .from('fsa_states')
    .select('*')
    .eq('project_id', project_id)
    .eq('fsa_id', fsa_id)
    .in('version', versions)
  
  if (!states || states.length !== versions.length) {
    throw new Error('Some versions not found')
  }
  
  // Apply merge strategy
  let mergedState = {}
  
  switch (strategy) {
    case 'last-write-wins':
      // Take the state with highest version
      mergedState = states.sort((a, b) => b.version - a.version)[0].state
      break
      
    case 'union':
      // Merge all keys, last write wins per key
      for (const state of states) {
        mergedState = { ...mergedState, ...state.state }
      }
      break
      
    case 'crdt':
      // Use CRDT semantics for specific fields
      mergedState = await applyCRDTMerge(states.map(s => s.state))
      break
      
    default:
      throw new Error(`Unknown merge strategy: ${strategy}`)
  }
  
  // Create merged version
  const currentVersion = await getCurrentVersion(supabase, project_id, fsa_id)
  const mergedVersion = currentVersion + 1
  
  const { data: mergedData, error } = await supabase
    .from('fsa_states')
    .insert({
      project_id,
      fsa_id,
      version: mergedVersion,
      parent_version: Math.max(...versions),
      state: mergedState,
      actor,
      lineage_id: `merge-${versions.join('-')}`
    })
    .select()
    .single()
  
  if (error) {
    throw new Error(`Failed to create merged state: ${error.message}`)
  }
  
  return new Response(
    JSON.stringify({
      success: true,
      version: mergedVersion,
      merged_versions: versions,
      strategy: strategy
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function getStateHistory(supabase: any, params: any) {
  const { project_id, fsa_id, limit = 10, offset = 0 } = params
  
  const { data, error, count } = await supabase
    .from('fsa_states')
    .select('*', { count: 'exact' })
    .eq('project_id', project_id)
    .eq('fsa_id', fsa_id)
    .order('version', { ascending: false })
    .range(offset, offset + limit - 1)
  
  if (error) {
    throw new Error(`Failed to get history: ${error.message}`)
  }
  
  return new Response(
    JSON.stringify({
      history: data || [],
      total: count || 0,
      limit,
      offset
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

// Helper functions

async function getCurrentVersion(supabase: any, projectId: string, fsaId: string): Promise<number> {
  const { data } = await supabase
    .rpc('get_latest_state_version', {
      p_project_id: projectId,
      p_fsa_id: fsaId
    })
  
  return data || 0
}

async function applyDeltaOperations(state: any, operations: any[]): Promise<any> {
  let result = { ...state }
  
  for (const op of operations) {
    const path = op.path
    const value = op.value
    
    switch (op.op) {
      case 'set':
        result = setValueAtPath(result, path, value)
        break
        
      case 'inc':
        result = incrementValueAtPath(result, path, value)
        break
        
      case 'push':
        result = pushValueAtPath(result, path, value)
        break
        
      case 'unset':
        result = unsetValueAtPath(result, path)
        break
    }
  }
  
  return result
}

function setValueAtPath(obj: any, path: string[], value: any): any {
  const result = { ...obj }
  let current = result
  
  for (let i = 0; i < path.length - 1; i++) {
    if (!current[path[i]]) {
      current[path[i]] = {}
    }
    current = current[path[i]]
  }
  
  current[path[path.length - 1]] = value
  return result
}

function incrementValueAtPath(obj: any, path: string[], delta: number): any {
  const result = { ...obj }
  let current = result
  
  for (let i = 0; i < path.length - 1; i++) {
    if (!current[path[i]]) {
      current[path[i]] = {}
    }
    current = current[path[i]]
  }
  
  const key = path[path.length - 1]
  current[key] = (current[key] || 0) + delta
  return result
}

function pushValueAtPath(obj: any, path: string[], value: any): any {
  const result = { ...obj }
  let current = result
  
  for (let i = 0; i < path.length - 1; i++) {
    if (!current[path[i]]) {
      current[path[i]] = {}
    }
    current = current[path[i]]
  }
  
  const key = path[path.length - 1]
  if (!Array.isArray(current[key])) {
    current[key] = []
  }
  current[key].push(value)
  return result
}

function unsetValueAtPath(obj: any, path: string[]): any {
  const result = { ...obj }
  let current = result
  
  for (let i = 0; i < path.length - 1; i++) {
    if (!current[path[i]]) {
      return result
    }
    current = current[path[i]]
  }
  
  delete current[path[path.length - 1]]
  return result
}

async function applyCRDTMerge(states: any[]): Promise<any> {
  // Simplified CRDT merge - in production would use proper CRDT library
  const merged: any = {}
  
  for (const state of states) {
    for (const [key, value] of Object.entries(state)) {
      if (typeof value === 'number') {
        // Numbers: take max (grow-only counter)
        merged[key] = Math.max(merged[key] || 0, value as number)
      } else if (Array.isArray(value)) {
        // Arrays: union (grow-only set)
        merged[key] = [...new Set([...(merged[key] || []), ...value])]
      } else if (typeof value === 'object' && value !== null) {
        // Objects: recursive merge
        merged[key] = await applyCRDTMerge([merged[key] || {}, value])
      } else {
        // Other types: last write wins
        merged[key] = value
      }
    }
  }
  
  return merged
}