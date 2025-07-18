import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface PrivacyRequest {
  action: 'check_access' | 'update_privacy' | 'scan_pii' | 'create_token' | 'redeem_token' | 'encrypt' | 'audit_log'
  memory_id?: string
  user_id?: string
  project_id?: string
  access_type?: string
  privacy_settings?: {
    visibility?: string
    license_id?: string
    requires_attribution?: boolean
    allow_derivatives?: boolean
    allow_commercial_use?: boolean
    expires_at?: string
    custom_terms?: string
  }
  token?: string
  token_settings?: {
    expires_in_hours?: number
    max_uses?: number
    allowed_operations?: string[]
    recipient_email?: string
  }
  audit_filters?: {
    start_date?: string
    end_date?: string
    user_id?: string
    access_type?: string
    limit?: number
  }
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

    const request = await req.json() as PrivacyRequest

    switch (request.action) {
      case 'check_access': {
        if (!request.memory_id) {
          throw new Error('memory_id is required')
        }

        const { data, error } = await supabaseClient
          .rpc('check_memory_access', {
            p_memory_id: request.memory_id,
            p_user_id: request.user_id || user.id,
            p_access_type: request.access_type || 'READ',
            p_project_id: request.project_id,
          })

        if (error) throw error

        const result = data[0]
        
        // Get additional memory info if access is allowed
        let memoryInfo = null
        if (result.allowed) {
          const { data: memory } = await supabaseClient
            .from('memories')
            .select(`
              id,
              label,
              type,
              created_at,
              created_by,
              memory_privacy_settings!inner(
                visibility,
                requires_attribution,
                allow_derivatives,
                allow_commercial_use,
                encryption_enabled,
                pii_detected,
                expires_at
              )
            `)
            .eq('id', request.memory_id)
            .single()

          memoryInfo = memory
        }

        return new Response(
          JSON.stringify({
            allowed: result.allowed,
            reason: result.reason,
            requires_attribution: result.requires_attribution,
            license_info: result.license_info,
            memory_info: memoryInfo,
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'update_privacy': {
        if (!request.memory_id || !request.privacy_settings) {
          throw new Error('memory_id and privacy_settings are required')
        }

        // Check if user owns the memory
        const { data: memory } = await supabaseClient
          .from('memories')
          .select('created_by')
          .eq('id', request.memory_id)
          .single()

        if (!memory || memory.created_by !== user.id) {
          throw new Error('Only memory owner can update privacy settings')
        }

        // Update privacy settings
        const { error: updateError } = await supabaseClient
          .from('memory_privacy_settings')
          .upsert({
            memory_id: request.memory_id,
            ...request.privacy_settings,
          })

        if (updateError) throw updateError

        // If visibility changed to private and PII not scanned, trigger scan
        if (request.privacy_settings.visibility === 'PUBLIC') {
          const { data: privacy } = await supabaseClient
            .from('memory_privacy_settings')
            .select('pii_scan_date')
            .eq('memory_id', request.memory_id)
            .single()

          if (!privacy?.pii_scan_date) {
            // Trigger PII scan
            await scanMemoryForPII(supabaseClient, request.memory_id)
          }
        }

        return new Response(
          JSON.stringify({ 
            success: true,
            memory_id: request.memory_id,
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'scan_pii': {
        if (!request.memory_id) {
          throw new Error('memory_id is required')
        }

        // Check access
        const { data: accessCheck } = await supabaseClient
          .rpc('check_memory_access', {
            p_memory_id: request.memory_id,
            p_user_id: user.id,
            p_access_type: 'READ',
          })

        if (!accessCheck[0].allowed) {
          throw new Error('Access denied')
        }

        const result = await scanMemoryForPII(supabaseClient, request.memory_id)

        return new Response(
          JSON.stringify(result),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'create_token': {
        if (!request.memory_id) {
          throw new Error('memory_id is required')
        }

        const settings = request.token_settings || {}
        const expiresIn = `${settings.expires_in_hours || 168} hours` // Default 7 days

        const { data, error } = await supabaseClient
          .rpc('create_sharing_token', {
            p_memory_id: request.memory_id,
            p_user_id: user.id,
            p_expires_in: expiresIn,
            p_max_uses: settings.max_uses || 1,
            p_allowed_operations: settings.allowed_operations || ['READ'],
            p_recipient_email: settings.recipient_email,
          })

        if (error) throw error

        // Get full token details
        const { data: tokenDetails } = await supabaseClient
          .from('memory_sharing_tokens')
          .select('*')
          .eq('token', data)
          .single()

        return new Response(
          JSON.stringify({
            token: data,
            details: tokenDetails,
            share_url: `${Deno.env.get('APP_URL')}/share/${data}`,
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'redeem_token': {
        if (!request.token) {
          throw new Error('token is required')
        }

        const { data, error } = await supabaseClient
          .rpc('redeem_sharing_token', {
            p_token: request.token,
            p_operation: request.access_type || 'READ',
          })

        if (error) throw error

        const result = data[0]

        // If successful, get memory content
        let memoryContent = null
        if (result.success && result.memory_id) {
          const { data: memory } = await supabaseClient
            .from('memories')
            .select(`
              id,
              label,
              type,
              tags,
              payloads!inner(content),
              memory_privacy_settings!inner(
                requires_attribution,
                license_id,
                encryption_enabled
              )
            `)
            .eq('id', result.memory_id)
            .single()

          // Check if content is encrypted
          if (memory?.memory_privacy_settings?.encryption_enabled) {
            memory.payloads[0].content = '[ENCRYPTED CONTENT]'
          }

          memoryContent = memory
        }

        return new Response(
          JSON.stringify({
            success: result.success,
            reason: result.reason,
            memory: memoryContent,
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'encrypt': {
        if (!request.memory_id) {
          throw new Error('memory_id is required')
        }

        // Check if user owns the memory
        const { data: memory } = await supabaseClient
          .from('memories')
          .select('created_by')
          .eq('id', request.memory_id)
          .single()

        if (!memory || memory.created_by !== user.id) {
          throw new Error('Only memory owner can encrypt content')
        }

        // Generate encryption key ID (in production, this would use KMS)
        const keyId = `key_${Date.now()}_${user.id}`

        const { data, error } = await supabaseClient
          .rpc('encrypt_memory_content', {
            p_memory_id: request.memory_id,
            p_key_id: keyId,
          })

        if (error) throw error

        return new Response(
          JSON.stringify({
            success: data,
            memory_id: request.memory_id,
            key_id: keyId,
            message: data ? 'Memory encrypted successfully' : 'Encryption failed',
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'audit_log': {
        const filters = request.audit_filters || {}
        
        let query = supabaseClient
          .from('memory_access_logs')
          .select(`
            *,
            memories!inner(label, type),
            auth.users!accessed_by(raw_user_meta_data)
          `)
          .order('created_at', { ascending: false })
          .limit(filters.limit || 100)

        // Apply filters
        if (request.memory_id) {
          query = query.eq('memory_id', request.memory_id)
        }

        if (request.project_id) {
          query = query.eq('project_id', request.project_id)
        }

        if (filters.user_id) {
          query = query.eq('accessed_by', filters.user_id)
        }

        if (filters.access_type) {
          query = query.eq('access_type', filters.access_type)
        }

        if (filters.start_date) {
          query = query.gte('created_at', filters.start_date)
        }

        if (filters.end_date) {
          query = query.lte('created_at', filters.end_date)
        }

        const { data, error } = await query

        if (error) throw error

        // Summary statistics
        const stats = {
          total_accesses: data.length,
          granted: data.filter(log => log.access_granted).length,
          denied: data.filter(log => !log.access_granted).length,
          unique_users: new Set(data.map(log => log.accessed_by)).size,
          access_types: data.reduce((acc, log) => {
            acc[log.access_type] = (acc[log.access_type] || 0) + 1
            return acc
          }, {} as Record<string, number>),
        }

        return new Response(
          JSON.stringify({
            logs: data,
            stats,
            query_params: filters,
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

// Helper function to scan memory for PII
async function scanMemoryForPII(supabaseClient: any, memoryId: string) {
  // Get memory content
  const { data: payload } = await supabaseClient
    .from('payloads')
    .select('content')
    .eq('memory_id', memoryId)
    .single()

  if (!payload?.content) {
    return { has_pii: false, message: 'No content to scan' }
  }

  // Run PII detection
  const { data: piiResult, error } = await supabaseClient
    .rpc('detect_pii', {
      p_content: payload.content,
    })

  if (error) throw error

  const result = piiResult[0]

  // Update privacy settings with scan results
  await supabaseClient
    .from('memory_privacy_settings')
    .update({
      pii_detected: result.has_pii,
      pii_scan_date: new Date().toISOString(),
    })
    .eq('memory_id', memoryId)

  // If high severity PII detected, automatically restrict and encrypt
  if (result.has_pii && result.severity in ['HIGH', 'CRITICAL']) {
    await supabaseClient
      .from('memory_privacy_settings')
      .update({
        visibility: 'PRIVATE',
        encryption_enabled: true,
      })
      .eq('memory_id', memoryId)

    // Log the automatic action
    await supabaseClient
      .from('memory_events')
      .insert({
        event_type: 'auto_restricted',
        memory_id: memoryId,
        metadata: {
          reason: 'High severity PII detected',
          pii_types: result.pii_types,
          severity: result.severity,
        },
      })
  }

  return {
    memory_id: memoryId,
    has_pii: result.has_pii,
    pii_types: result.pii_types,
    severity: result.severity,
    details: result.details,
    actions_taken: result.has_pii && result.severity in ['HIGH', 'CRITICAL'] ? 
      ['Visibility set to PRIVATE', 'Encryption enabled'] : [],
  }
}