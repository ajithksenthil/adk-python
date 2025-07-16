import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.38.0'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// Cache for scheduled memories (5 minute TTL)
const memoryCache = new Map<string, { data: any, timestamp: number }>()
const CACHE_TTL = 5 * 60 * 1000 // 5 minutes

const ScheduleRequestSchema = z.object({
  agent_id: z.string(),
  task_id: z.string(),
  project_id: z.string(),
  need_tags: z.array(z.string()).default([]),
  token_budget: z.number().int().positive().default(4000),
  prefer_hot: z.boolean().default(true),
  include_insights: z.boolean().default(false),
  embedding: z.array(z.number()).optional() // For similarity search
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

    // Validate auth
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
      throw new Error('No authorization header')
    }

    const params = await req.json()
    const validated = ScheduleRequestSchema.parse(params)
    
    // Generate cache key
    const cacheKey = generateCacheKey(validated)
    
    // Check cache
    const cached = memoryCache.get(cacheKey)
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      console.log('Cache hit for', cacheKey)
      return new Response(
        JSON.stringify(cached.data),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      )
    }

    // Get memories using the database function
    const { data: memories, error } = await supabase.rpc('schedule_memories_for_agent', {
      agent_id_param: validated.agent_id,
      task_id_param: validated.task_id,
      project_id_param: validated.project_id,
      need_tags: validated.need_tags,
      token_budget: validated.token_budget,
      prefer_hot: validated.prefer_hot
    })

    if (error) {
      throw new Error(`Failed to schedule memories: ${error.message}`)
    }

    // If embedding provided, also do similarity search
    let similarMemories: any[] = []
    if (validated.embedding) {
      const { data: similar } = await supabase.rpc('search_similar_memories', {
        query_embedding: validated.embedding,
        project_id_param: validated.project_id,
        similarity_threshold: 0.78,
        limit_count: 10
      })
      
      if (similar) {
        similarMemories = similar
      }
    }

    // Include insights if requested
    let insights: any[] = []
    if (validated.include_insights) {
      const { data: insightData } = await supabase
        .from('insights')
        .select('*')
        .eq('project_id', validated.project_id)
        .order('support_count', { ascending: false })
        .limit(5)

      if (insightData) {
        insights = insightData
      }
    }

    // Combine and deduplicate memories
    const allMemories = combineMemories(memories || [], similarMemories, insights, validated.token_budget)

    // Format response
    const response = {
      agent_id: validated.agent_id,
      task_id: validated.task_id,
      memories: allMemories.map(formatMemory),
      total_tokens: allMemories.reduce((sum, m) => sum + (m.token_count || 100), 0),
      count: allMemories.length,
      cache_key: cacheKey.slice(0, 8) // For debugging
    }

    // Update cache
    memoryCache.set(cacheKey, {
      data: response,
      timestamp: Date.now()
    })

    // Clean old cache entries periodically
    if (memoryCache.size > 1000) {
      cleanCache()
    }

    // Log memory access for each returned memory
    const memoryIds = allMemories
      .filter(m => m.memory_id)
      .map(m => m.memory_id)
    
    if (memoryIds.length > 0) {
      await logMemoryAccess(supabase, memoryIds, validated.agent_id, validated.task_id)
    }

    return new Response(
      JSON.stringify(response),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )

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

function generateCacheKey(params: any): string {
  const key = [
    params.project_id,
    params.agent_id,
    params.task_id,
    params.need_tags.sort().join(','),
    params.token_budget,
    params.prefer_hot,
    params.include_insights
  ].join('|')
  
  // Simple hash
  let hash = 0
  for (let i = 0; i < key.length; i++) {
    const char = key.charCodeAt(i)
    hash = ((hash << 5) - hash) + char
    hash = hash & hash
  }
  
  return `mem_${Math.abs(hash).toString(16)}`
}

function combineMemories(
  scheduled: any[],
  similar: any[],
  insights: any[],
  tokenBudget: number
): any[] {
  const combined = new Map<string, any>()
  let totalTokens = 0
  
  // Add scheduled memories first (highest priority)
  for (const mem of scheduled) {
    if (totalTokens + (mem.token_count || 100) > tokenBudget) break
    combined.set(mem.memory_id || mem.id, mem)
    totalTokens += mem.token_count || 100
  }
  
  // Add similar memories if space
  for (const mem of similar) {
    if (combined.has(mem.id)) continue
    if (totalTokens + (mem.token_count || 100) > tokenBudget) break
    combined.set(mem.id, mem)
    totalTokens += mem.token_count || 100
  }
  
  // Convert insights to memory format and add if space
  for (const insight of insights) {
    if (totalTokens + 50 > tokenBudget) break
    
    const insightMemory = {
      id: `insight_${insight.id}`,
      label: `insight::${insight.id.slice(0, 8)}`,
      type: 'PLAINTEXT',
      content: formatInsight(insight),
      token_count: 50,
      priority: insight.priority,
      relevance_score: 0.5
    }
    
    combined.set(insightMemory.id, insightMemory)
    totalTokens += 50
  }
  
  return Array.from(combined.values())
}

function formatMemory(memory: any): any {
  return {
    id: memory.memory_id || memory.id,
    label: memory.label,
    type: memory.type,
    content: memory.content ? formatMemoryContent(memory.label, memory.content) : '',
    tokens: memory.token_count || 100,
    relevance_score: memory.relevance_score || memory.similarity || 0
  }
}

function formatMemoryContent(label: string, content: string): string {
  return `<<MEM:${label}>>\n${content}\n<<ENDMEM>>`
}

function formatInsight(insight: any): string {
  return `Insight: ${insight.insight}\nSupport: ${insight.support_count} users\nSentiment: ${insight.sentiment}`
}

async function logMemoryAccess(
  supabase: any,
  memoryIds: string[],
  agentId: string,
  taskId: string
) {
  try {
    // Batch update usage stats
    for (const memoryId of memoryIds) {
      await supabase.rpc('increment_memory_usage', { memory_uuid: memoryId })
    }
    
    // Log access events
    const events = memoryIds.map(memoryId => ({
      memory_id: memoryId,
      event: 'ACCESSED',
      actor: agentId,
      meta: { task_id: taskId, context: 'scheduled' }
    }))
    
    await supabase.from('memory_events').insert(events)
  } catch (error) {
    console.error('Failed to log memory access:', error)
    // Non-critical, don't throw
  }
}

function cleanCache() {
  const now = Date.now()
  const entries = Array.from(memoryCache.entries())
  
  // Remove expired entries
  for (const [key, value] of entries) {
    if (now - value.timestamp > CACHE_TTL) {
      memoryCache.delete(key)
    }
  }
  
  // If still too many, remove oldest
  if (memoryCache.size > 500) {
    const sorted = entries
      .sort((a, b) => a[1].timestamp - b[1].timestamp)
      .slice(0, memoryCache.size - 500)
    
    for (const [key] of sorted) {
      memoryCache.delete(key)
    }
  }
}