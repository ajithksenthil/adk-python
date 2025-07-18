import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { Configuration, OpenAIApi } from 'https://esm.sh/openai@3.1.0'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface SearchRequest {
  query: string
  project_id?: string
  top_k?: number
  threshold?: number
  use_hybrid?: boolean
  weights?: {
    semantic?: number
    tags?: number
    recency?: number
  }
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? '',
      {
        auth: {
          autoRefreshToken: false,
          persistSession: false,
        },
      }
    )

    const openaiConfig = new Configuration({
      apiKey: Deno.env.get('OPENAI_API_KEY'),
    })
    const openai = new OpenAIApi(openaiConfig)

    const { 
      query, 
      project_id, 
      top_k = 10, 
      threshold = 0.7,
      use_hybrid = true,
      weights = { semantic: 0.5, tags: 0.3, recency: 0.2 }
    } = await req.json() as SearchRequest

    // Generate embedding for query
    const embeddingResponse = await openai.createEmbedding({
      model: 'text-embedding-3-small',
      input: query,
    })

    const queryEmbedding = embeddingResponse.data.data[0].embedding

    let results

    if (use_hybrid) {
      // Use hybrid search combining semantic, tags, and recency
      const { data, error } = await supabaseClient
        .rpc('search_memories_hybrid', {
          query_text: query,
          query_embedding: JSON.stringify(queryEmbedding),
          semantic_weight: weights.semantic || 0.5,
          tag_weight: weights.tags || 0.3,
          recency_weight: weights.recency || 0.2,
          match_count: top_k,
          filter_project_id: project_id,
        })

      if (error) throw error
      
      // Fetch full memory details
      const memoryIds = data.map(d => d.id)
      const { data: memories, error: memError } = await supabaseClient
        .from('memories')
        .select(`
          *,
          payloads!inner(content)
        `)
        .in('id', memoryIds)

      if (memError) throw memError

      // Combine scores with memory data
      results = memories.map(memory => {
        const scoreData = data.find(d => d.id === memory.id)
        return {
          ...memory,
          score: scoreData?.score || 0,
          semantic_similarity: scoreData?.semantic_similarity || 0,
          tag_relevance: scoreData?.tag_relevance || 0,
          recency_score: scoreData?.recency_score || 0,
          content: memory.payloads?.[0]?.content,
        }
      }).sort((a, b) => b.score - a.score)
    } else {
      // Pure semantic search
      const { data, error } = await supabaseClient
        .rpc('search_memories_semantic', {
          query_embedding: JSON.stringify(queryEmbedding),
          match_threshold: threshold,
          match_count: top_k,
          filter_project_id: project_id,
        })

      if (error) throw error
      results = data
    }

    // Log search event for analytics
    await supabaseClient
      .from('memory_events')
      .insert({
        event_type: 'search',
        memory_id: null,
        project_id,
        metadata: {
          query,
          result_count: results.length,
          search_type: use_hybrid ? 'hybrid' : 'semantic',
        },
      })

    return new Response(
      JSON.stringify({
        query,
        results,
        total: results.length,
        search_type: use_hybrid ? 'hybrid' : 'semantic',
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
    )
  }
})