import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'
import { Configuration, OpenAIApi } from 'https://esm.sh/openai@3.1.0'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface ChainRequest {
  action: 'create' | 'add_memory' | 'remove_memory' | 'reorder' | 'summarize' | 'get'
  chain_id?: string
  project_id?: string
  title?: string
  description?: string
  memory_id?: string
  position?: number
  transition_text?: string
  new_order?: number[]
}

serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const authHeader = req.headers.get('Authorization')!
    const token = authHeader.replace('Bearer ', '')
    
    const supabaseClient = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_ANON_KEY') ?? '',
      {
        global: {
          headers: {
            Authorization: authHeader,
          },
        },
        auth: {
          autoRefreshToken: false,
          persistSession: false,
        },
      }
    )

    const { data: { user }, error: authError } = await supabaseClient.auth.getUser(token)
    if (authError || !user) {
      throw new Error('Unauthorized')
    }

    const request = await req.json() as ChainRequest

    switch (request.action) {
      case 'create': {
        if (!request.project_id || !request.title) {
          throw new Error('project_id and title are required')
        }

        const { data, error } = await supabaseClient
          .from('memory_chains')
          .insert({
            project_id: request.project_id,
            title: request.title,
            description: request.description,
            created_by: user.id,
          })
          .select()
          .single()

        if (error) throw error
        
        return new Response(
          JSON.stringify({ chain: data }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 201 }
        )
      }

      case 'add_memory': {
        if (!request.chain_id || !request.memory_id) {
          throw new Error('chain_id and memory_id are required')
        }

        const { data, error } = await supabaseClient
          .rpc('add_memory_to_chain', {
            p_chain_id: request.chain_id,
            p_memory_id: request.memory_id,
            p_position: request.position,
            p_transition_text: request.transition_text,
            p_user_id: user.id,
          })

        if (error) throw error
        
        return new Response(
          JSON.stringify({ link: data }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'remove_memory': {
        if (!request.chain_id || !request.memory_id) {
          throw new Error('chain_id and memory_id are required')
        }

        const { data, error } = await supabaseClient
          .rpc('remove_memory_from_chain', {
            p_chain_id: request.chain_id,
            p_memory_id: request.memory_id,
          })

        if (error) throw error
        
        return new Response(
          JSON.stringify({ success: data }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'reorder': {
        if (!request.chain_id || !request.new_order) {
          throw new Error('chain_id and new_order are required')
        }

        // Get current links
        const { data: links, error: fetchError } = await supabaseClient
          .from('memory_chain_links')
          .select('id, memory_id')
          .eq('chain_id', request.chain_id)
          .order('order_index')

        if (fetchError) throw fetchError

        // Validate new order
        if (links.length !== request.new_order.length) {
          throw new Error('Invalid new order: length mismatch')
        }

        // Update order indexes
        const updates = request.new_order.map((memory_id, index) => {
          const link = links.find(l => l.memory_id === memory_id)
          if (!link) throw new Error(`Memory ${memory_id} not found in chain`)
          return {
            id: link.id,
            order_index: index,
          }
        })

        const { error: updateError } = await supabaseClient
          .from('memory_chain_links')
          .upsert(updates)

        if (updateError) throw updateError
        
        return new Response(
          JSON.stringify({ success: true }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'summarize': {
        if (!request.chain_id) {
          throw new Error('chain_id is required')
        }

        // Get chain data
        const { data: chainData, error: chainError } = await supabaseClient
          .rpc('get_memory_chain', {
            p_chain_id: request.chain_id,
            p_include_content: true,
          })

        if (chainError) throw chainError
        if (!chainData || chainData.length === 0) {
          throw new Error('Chain not found or empty')
        }

        // Calculate tokens
        const { data: tokenCount } = await supabaseClient
          .rpc('calculate_chain_tokens', {
            p_chain_id: request.chain_id,
          })

        // Get chain config
        const { data: chain } = await supabaseClient
          .from('memory_chains')
          .select('auto_summarize, summary_threshold')
          .eq('id', request.chain_id)
          .single()

        if (!chain.auto_summarize || tokenCount < chain.summary_threshold) {
          return new Response(
            JSON.stringify({ 
              summary: null, 
              reason: 'Summary not needed',
              token_count: tokenCount 
            }),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
          )
        }

        // Build narrative from chain
        let narrative = `Chain: ${chainData[0].chain_title}\n\n`
        if (chainData[0].chain_description) {
          narrative += `${chainData[0].chain_description}\n\n`
        }

        chainData.forEach((item, index) => {
          narrative += `${index + 1}. ${item.memory_label}\n`
          if (item.transition_text) {
            narrative += `   Transition: ${item.transition_text}\n`
          }
          if (item.content) {
            narrative += `   Content: ${item.content.substring(0, 500)}...\n`
          }
          narrative += '\n'
        })

        // Generate summary using OpenAI
        const openaiConfig = new Configuration({
          apiKey: Deno.env.get('OPENAI_API_KEY'),
        })
        const openai = new OpenAIApi(openaiConfig)

        const completion = await openai.createChatCompletion({
          model: 'gpt-3.5-turbo',
          messages: [
            {
              role: 'system',
              content: 'You are a helpful assistant that creates concise summaries of memory chains. Focus on the key insights and maintain narrative flow.',
            },
            {
              role: 'user',
              content: `Please summarize this memory chain into a coherent narrative:\n\n${narrative}`,
            },
          ],
          max_tokens: 500,
          temperature: 0.7,
        })

        const summary = completion.data.choices[0].message?.content

        // Store summary
        const { error: summaryError } = await supabaseClient
          .from('memory_chain_summaries')
          .upsert({
            chain_id: request.chain_id,
            summary,
            token_count: tokenCount,
            model_used: 'gpt-3.5-turbo',
          })

        if (summaryError) throw summaryError

        return new Response(
          JSON.stringify({ 
            summary,
            token_count: tokenCount,
            original_length: narrative.length,
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'get': {
        if (!request.chain_id) {
          throw new Error('chain_id is required')
        }

        // Get chain details
        const { data: chain, error: chainError } = await supabaseClient
          .from('memory_chains')
          .select('*')
          .eq('id', request.chain_id)
          .single()

        if (chainError) throw chainError

        // Get chain memories
        const { data: memories } = await supabaseClient
          .rpc('get_memory_chain', {
            p_chain_id: request.chain_id,
            p_include_content: true,
          })

        // Get summary if exists
        const { data: summary } = await supabaseClient
          .from('memory_chain_summaries')
          .select('*')
          .eq('chain_id', request.chain_id)
          .single()

        return new Response(
          JSON.stringify({ 
            chain,
            memories,
            summary,
            token_count: await supabaseClient.rpc('calculate_chain_tokens', {
              p_chain_id: request.chain_id,
            }).then(r => r.data),
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      default:
        throw new Error(`Unknown action: ${request.action}`)
    }
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 400 }
    )
  }
})