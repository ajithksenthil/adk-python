import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { Configuration, OpenAIApi } from 'https://esm.sh/openai@3.1.0'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface EmbeddingRequest {
  memory_ids?: string[]
  batch_size?: number
  model?: string
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

    const { memory_ids, batch_size = 10, model = 'text-embedding-3-small' } = await req.json() as EmbeddingRequest

    // Get memories that need embeddings
    let query = supabaseClient
      .from('memories')
      .select('id, label, type, project_id')
      .is('embedding', null)
      .order('created_at', { ascending: false })
      .limit(batch_size)

    if (memory_ids && memory_ids.length > 0) {
      query = query.in('id', memory_ids)
    }

    const { data: memories, error: fetchError } = await query

    if (fetchError) {
      throw fetchError
    }

    if (!memories || memories.length === 0) {
      return new Response(
        JSON.stringify({ message: 'No memories need embeddings', processed: 0 }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
      )
    }

    // Process memories in batches
    const results = []
    for (const memory of memories) {
      try {
        // Create job entry
        const { data: job } = await supabaseClient
          .from('embedding_jobs')
          .insert({
            memory_id: memory.id,
            status: 'processing',
          })
          .select()
          .single()

        // Get memory content
        const { data: payload } = await supabaseClient
          .from('payloads')
          .select('content')
          .eq('memory_id', memory.id)
          .single()

        if (!payload?.content) {
          throw new Error('No content found for memory')
        }

        // Prepare text for embedding
        let textToEmbed = `${memory.label}\n${memory.type}\n`
        
        // Add content based on type
        if (memory.type === 'PLAINTEXT' || memory.type === 'SEMANTIC') {
          textToEmbed += payload.content
        } else if (memory.type === 'COMMAND' || memory.type === 'TEMPLATE') {
          // For code, include comments and structure
          textToEmbed += `Code: ${payload.content.substring(0, 1000)}` // Limit length
        }

        // Generate embedding
        const embeddingResponse = await openai.createEmbedding({
          model,
          input: textToEmbed,
        })

        const embedding = embeddingResponse.data.data[0].embedding

        // Update memory with embedding
        const { error: updateError } = await supabaseClient
          .from('memories')
          .update({
            embedding: JSON.stringify(embedding),
            embedding_model: model,
            embedding_generated_at: new Date().toISOString(),
          })
          .eq('id', memory.id)

        if (updateError) {
          throw updateError
        }

        // Update job status
        await supabaseClient
          .from('embedding_jobs')
          .update({
            status: 'completed',
            completed_at: new Date().toISOString(),
          })
          .eq('id', job.id)

        results.push({
          memory_id: memory.id,
          status: 'success',
        })
      } catch (error) {
        // Log error and continue
        console.error(`Error processing memory ${memory.id}:`, error)
        
        await supabaseClient
          .from('embedding_jobs')
          .update({
            status: 'failed',
            error: error.message,
            completed_at: new Date().toISOString(),
          })
          .eq('memory_id', memory.id)

        results.push({
          memory_id: memory.id,
          status: 'error',
          error: error.message,
        })
      }
    }

    return new Response(
      JSON.stringify({
        message: 'Embedding generation complete',
        processed: results.length,
        results,
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