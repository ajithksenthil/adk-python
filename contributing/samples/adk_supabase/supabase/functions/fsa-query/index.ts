import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.38.0'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// Schema validation
const SliceQuerySchema = z.object({
  project_id: z.string().uuid(),
  fsa_id: z.string(),
  pattern: z.string(), // e.g., "task:DESIGN_*", "metrics.*"
  k: z.number().int().positive().optional(),
  use_cache: z.boolean().default(true)
})

const MultiSliceQuerySchema = z.object({
  project_id: z.string().uuid(),
  fsa_id: z.string(),
  slices: z.array(z.object({
    pattern: z.string(),
    k: z.number().int().positive().optional()
  }))
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
      case 'slice':
        return await querySlice(supabase, await req.json())
      
      case 'multi-slice':
        return await queryMultiSlice(supabase, await req.json())
      
      case 'aggregate':
        return await queryAggregate(supabase, await req.json())
      
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

async function querySlice(supabase: any, params: any) {
  const validated = SliceQuerySchema.parse(params)
  
  // Check cache first
  if (validated.use_cache) {
    const cached = await getFromCache(
      supabase, 
      validated.project_id, 
      validated.fsa_id, 
      validated.pattern,
      validated.k
    )
    
    if (cached) {
      return new Response(
        JSON.stringify(cached),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }
  }
  
  // Get latest state
  const { data: stateData } = await supabase
    .from('fsa_states')
    .select('*')
    .eq('project_id', validated.project_id)
    .eq('fsa_id', validated.fsa_id)
    .order('version', { ascending: false })
    .limit(1)
    .single()
  
  if (!stateData) {
    return new Response(
      JSON.stringify({
        project_id: validated.project_id,
        fsa_id: validated.fsa_id,
        version: 0,
        slice: {},
        summary: 'No state found',
        pattern: validated.pattern
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  
  // Extract slice using database function
  const { data: sliceData } = await supabase
    .rpc('extract_state_slice', {
      state: stateData.state,
      pattern: validated.pattern,
      k_limit: validated.k
    })
  
  // Generate summary
  const { data: summary } = await supabase
    .rpc('generate_slice_summary', {
      slice_data: sliceData,
      pattern: validated.pattern
    })
  
  const result = {
    project_id: validated.project_id,
    fsa_id: validated.fsa_id,
    version: stateData.version,
    slice: sliceData || {},
    summary: summary || generateLocalSummary(sliceData, validated.pattern),
    pattern: validated.pattern,
    cached: false
  }
  
  // Cache result
  if (validated.use_cache) {
    await cacheSlice(supabase, stateData.id, validated.pattern, validated.k, result)
  }
  
  return new Response(
    JSON.stringify(result),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function queryMultiSlice(supabase: any, params: any) {
  const validated = MultiSliceQuerySchema.parse(params)
  
  // Get latest state once
  const { data: stateData } = await supabase
    .from('fsa_states')
    .select('*')
    .eq('project_id', validated.project_id)
    .eq('fsa_id', validated.fsa_id)
    .order('version', { ascending: false })
    .limit(1)
    .single()
  
  if (!stateData) {
    return new Response(
      JSON.stringify({
        project_id: validated.project_id,
        fsa_id: validated.fsa_id,
        version: 0,
        slices: validated.slices.map(s => ({
          pattern: s.pattern,
          slice: {},
          summary: 'No state found'
        }))
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  
  // Process each slice
  const results = await Promise.all(
    validated.slices.map(async (sliceQuery) => {
      // Check cache
      const cached = await getFromCache(
        supabase,
        validated.project_id,
        validated.fsa_id,
        sliceQuery.pattern,
        sliceQuery.k
      )
      
      if (cached) {
        return {
          pattern: sliceQuery.pattern,
          slice: cached.slice,
          summary: cached.summary,
          cached: true
        }
      }
      
      // Extract slice
      const { data: sliceData } = await supabase
        .rpc('extract_state_slice', {
          state: stateData.state,
          pattern: sliceQuery.pattern,
          k_limit: sliceQuery.k
        })
      
      const summary = generateLocalSummary(sliceData, sliceQuery.pattern)
      
      // Cache for next time
      await cacheSlice(
        supabase,
        stateData.id,
        sliceQuery.pattern,
        sliceQuery.k,
        { slice: sliceData, summary }
      )
      
      return {
        pattern: sliceQuery.pattern,
        slice: sliceData || {},
        summary,
        cached: false
      }
    })
  )
  
  return new Response(
    JSON.stringify({
      project_id: validated.project_id,
      fsa_id: validated.fsa_id,
      version: stateData.version,
      slices: results
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function queryAggregate(supabase: any, params: any) {
  const { project_id, fsa_id, aggregations } = params
  
  // Get latest state
  const { data: stateData } = await supabase
    .from('fsa_states')
    .select('*')
    .eq('project_id', project_id)
    .eq('fsa_id', fsa_id)
    .order('version', { ascending: false })
    .limit(1)
    .single()
  
  if (!stateData) {
    return new Response(
      JSON.stringify({ error: 'State not found' }),
      { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  
  const results: any = {}
  
  for (const agg of aggregations) {
    switch (agg.type) {
      case 'count':
        results[agg.name] = countMatches(stateData.state, agg.pattern)
        break
        
      case 'sum':
        results[agg.name] = sumValues(stateData.state, agg.pattern, agg.field)
        break
        
      case 'avg':
        results[agg.name] = avgValues(stateData.state, agg.pattern, agg.field)
        break
        
      case 'filter':
        results[agg.name] = filterByCondition(stateData.state, agg.pattern, agg.condition)
        break
    }
  }
  
  return new Response(
    JSON.stringify({
      project_id,
      fsa_id,
      version: stateData.version,
      aggregations: results
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

// Helper functions

async function getFromCache(
  supabase: any,
  projectId: string,
  fsaId: string,
  pattern: string,
  k?: number
): Promise<any | null> {
  // Get latest state version
  const { data: stateData } = await supabase
    .from('fsa_states')
    .select('id, version')
    .eq('project_id', projectId)
    .eq('fsa_id', fsaId)
    .order('version', { ascending: false })
    .limit(1)
    .single()
  
  if (!stateData) return null
  
  // Check cache
  const { data: cacheData } = await supabase
    .from('fsa_slice_cache')
    .select('*')
    .eq('state_id', stateData.id)
    .eq('pattern', pattern)
    .eq('k_limit', k || null)
    .gt('expires_at', new Date().toISOString())
    .single()
  
  if (cacheData) {
    // Update access stats
    await supabase
      .from('fsa_slice_cache')
      .update({
        accessed_at: new Date().toISOString(),
        access_count: cacheData.access_count + 1
      })
      .eq('id', cacheData.id)
    
    return {
      ...cacheData,
      version: stateData.version,
      cached: true
    }
  }
  
  return null
}

async function cacheSlice(
  supabase: any,
  stateId: string,
  pattern: string,
  k: number | undefined,
  data: any
) {
  try {
    await supabase
      .from('fsa_slice_cache')
      .upsert({
        state_id: stateId,
        pattern,
        k_limit: k || null,
        slice_data: data.slice,
        summary: data.summary,
        token_count: estimateTokens(data.slice),
        expires_at: new Date(Date.now() + 5 * 60 * 1000).toISOString() // 5 min TTL
      })
  } catch (error) {
    console.error('Cache write failed:', error)
    // Non-critical, continue
  }
}

function generateLocalSummary(slice: any, pattern: string): string {
  if (!slice || Object.keys(slice).length === 0) {
    return `No items matching pattern "${pattern}"`
  }
  
  const count = Object.keys(slice).length
  const sampleKeys = Object.keys(slice).slice(0, 3)
  
  if (pattern.startsWith('task:')) {
    const statuses = Object.values(slice).map((t: any) => t.status)
    const statusCounts = statuses.reduce((acc: any, s: string) => {
      acc[s] = (acc[s] || 0) + 1
      return acc
    }, {})
    
    return `${count} tasks: ${Object.entries(statusCounts)
      .map(([s, c]) => `${c} ${s}`)
      .join(', ')}`
  } else if (pattern.startsWith('agent:')) {
    return `${count} agents online`
  } else if (pattern.startsWith('metric:')) {
    return `${count} metrics tracked`
  } else {
    return `${count} items: ${sampleKeys.join(', ')}${count > 3 ? '...' : ''}`
  }
}

function estimateTokens(data: any): number {
  // Rough estimate: 1 token per 4 characters
  const jsonStr = JSON.stringify(data)
  return Math.ceil(jsonStr.length / 4)
}

function countMatches(state: any, pattern: string): number {
  const regex = new RegExp('^' + pattern.replace('*', '.*'))
  return Object.keys(state).filter(k => regex.test(k)).length
}

function sumValues(state: any, pattern: string, field: string): number {
  const regex = new RegExp('^' + pattern.replace('*', '.*'))
  let sum = 0
  
  for (const [key, value] of Object.entries(state)) {
    if (regex.test(key) && typeof value === 'object' && value !== null) {
      const fieldValue = (value as any)[field]
      if (typeof fieldValue === 'number') {
        sum += fieldValue
      }
    }
  }
  
  return sum
}

function avgValues(state: any, pattern: string, field: string): number {
  const regex = new RegExp('^' + pattern.replace('*', '.*'))
  let sum = 0
  let count = 0
  
  for (const [key, value] of Object.entries(state)) {
    if (regex.test(key) && typeof value === 'object' && value !== null) {
      const fieldValue = (value as any)[field]
      if (typeof fieldValue === 'number') {
        sum += fieldValue
        count++
      }
    }
  }
  
  return count > 0 ? sum / count : 0
}

function filterByCondition(state: any, pattern: string, condition: any): any[] {
  const regex = new RegExp('^' + pattern.replace('*', '.*'))
  const results = []
  
  for (const [key, value] of Object.entries(state)) {
    if (regex.test(key) && matchesCondition(value, condition)) {
      results.push({ key, value })
    }
  }
  
  return results
}

function matchesCondition(value: any, condition: any): boolean {
  // Simple condition matching
  for (const [field, expected] of Object.entries(condition)) {
    if (value[field] !== expected) {
      return false
    }
  }
  return true
}