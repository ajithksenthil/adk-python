import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface AnalyticsRequest {
  action: 'dashboard' | 'memory_metrics' | 'tag_popularity' | 'lifecycle' | 'export' | 'schedule'
  project_id?: string
  memory_id?: string
  time_range?: string // 1h, 24h, 7d, 30d, 90d
  metric_type?: string
  export_format?: 'json' | 'csv'
  schedule_config?: {
    job_type: string
    enabled: boolean
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

    const request = await req.json() as AnalyticsRequest

    switch (request.action) {
      case 'dashboard': {
        if (!request.project_id) {
          throw new Error('project_id is required')
        }

        // Verify user has access to project
        const { data: member } = await supabaseClient
          .from('project_members')
          .select('role')
          .eq('project_id', request.project_id)
          .eq('user_id', user.id)
          .single()

        if (!member) {
          throw new Error('Access denied')
        }

        // Get dashboard data
        const { data, error } = await supabaseClient
          .rpc('get_analytics_dashboard', {
            p_project_id: request.project_id,
            p_time_range: request.time_range || '7d',
          })

        if (error) throw error

        // Enrich with recommendations if available
        const { data: recommendations } = await supabaseClient
          .from('memory_recommendations')
          .select('memory_id, score, reason')
          .eq('project_id', request.project_id)
          .gt('expires_at', new Date().toISOString())
          .order('score', { ascending: false })
          .limit(5)

        return new Response(
          JSON.stringify({ 
            dashboard: data,
            recommendations,
            generated_at: new Date().toISOString(),
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'memory_metrics': {
        if (!request.memory_id) {
          throw new Error('memory_id is required')
        }

        // Get memory details
        const { data: memory } = await supabaseClient
          .from('memories')
          .select('project_id')
          .eq('id', request.memory_id)
          .single()

        if (!memory) {
          throw new Error('Memory not found')
        }

        // Verify access
        const { data: member } = await supabaseClient
          .from('project_members')
          .select('role')
          .eq('project_id', memory.project_id)
          .eq('user_id', user.id)
          .single()

        if (!member) {
          throw new Error('Access denied')
        }

        // Get or compute metrics
        const timeWindow = request.time_range === '30d' ? '30 days' : 
                          request.time_range === '90d' ? '90 days' : '7 days'

        // Check if recent metrics exist
        const { data: existingMetrics } = await supabaseClient
          .from('memory_analytics_metrics')
          .select('*')
          .eq('memory_id', request.memory_id)
          .gte('computed_at', new Date(Date.now() - 3600000).toISOString()) // 1 hour old
          .order('computed_at', { ascending: false })

        let metrics
        if (existingMetrics && existingMetrics.length > 0) {
          metrics = existingMetrics[0]
        } else {
          // Compute fresh metrics
          const { data: usageMetrics } = await supabaseClient
            .rpc('compute_memory_usage_metrics', {
              p_memory_id: request.memory_id,
              p_time_window: timeWindow,
            })

          const { data: temporalPatterns } = await supabaseClient
            .rpc('compute_temporal_patterns', {
              p_memory_id: request.memory_id,
              p_time_window: timeWindow,
            })

          // Store computed metrics
          await supabaseClient
            .from('memory_analytics_metrics')
            .insert([
              {
                memory_id: request.memory_id,
                project_id: memory.project_id,
                metric_type: 'usage',
                metric_value: usageMetrics,
              },
              {
                memory_id: request.memory_id,
                project_id: memory.project_id,
                metric_type: 'temporal',
                metric_value: temporalPatterns,
              },
            ])

          metrics = {
            usage: usageMetrics,
            temporal: temporalPatterns,
          }
        }

        return new Response(
          JSON.stringify({ 
            memory_id: request.memory_id,
            metrics,
            computed_at: new Date().toISOString(),
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'tag_popularity': {
        const timeWindow = request.time_range === '30d' ? '30 days' : 
                          request.time_range === '90d' ? '90 days' : '7 days'

        const { data, error } = await supabaseClient
          .rpc('analyze_tag_popularity', {
            p_project_id: request.project_id,
            p_time_window: timeWindow,
          })

        if (error) throw error

        return new Response(
          JSON.stringify({ 
            tags: data,
            project_id: request.project_id,
            time_window: timeWindow,
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'lifecycle': {
        if (!request.project_id) {
          throw new Error('project_id is required')
        }

        const { data, error } = await supabaseClient
          .rpc('compute_lifecycle_metrics', {
            p_project_id: request.project_id,
            p_time_window: '90 days',
          })

        if (error) throw error

        return new Response(
          JSON.stringify({ 
            project_id: request.project_id,
            lifecycle_metrics: data,
            computed_at: new Date().toISOString(),
          }),
          { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
        )
      }

      case 'export': {
        if (!request.project_id) {
          throw new Error('project_id is required')
        }

        const format = request.export_format || 'json'
        const timeRange = request.time_range || '30d'

        // Get aggregated data for export
        const { data: aggregates } = await supabaseClient
          .from('memory_analytics_aggregates')
          .select('*')
          .eq('project_id', request.project_id)
          .gte('period_start', new Date(Date.now() - 
            (timeRange === '7d' ? 7 * 24 * 60 * 60 * 1000 :
             timeRange === '30d' ? 30 * 24 * 60 * 60 * 1000 :
             90 * 24 * 60 * 60 * 1000)).toISOString())
          .order('period_start', { ascending: false })

        if (format === 'csv') {
          // Convert to CSV format
          const headers = ['period_start', 'period_end', 'time_period', 'aggregate_type', 'value']
          const rows = aggregates.map(row => [
            row.period_start,
            row.period_end,
            row.time_period,
            row.aggregate_type,
            JSON.stringify(row.aggregate_value),
          ])
          
          const csv = [
            headers.join(','),
            ...rows.map(row => row.map(cell => `"${cell}"`).join(',')),
          ].join('\n')

          return new Response(csv, {
            headers: {
              ...corsHeaders,
              'Content-Type': 'text/csv',
              'Content-Disposition': `attachment; filename="analytics_export_${request.project_id}_${timeRange}.csv"`,
            },
            status: 200,
          })
        } else {
          // Return as JSON
          return new Response(
            JSON.stringify({
              project_id: request.project_id,
              time_range: timeRange,
              export_date: new Date().toISOString(),
              data: aggregates,
            }),
            { 
              headers: { 
                ...corsHeaders, 
                'Content-Type': 'application/json',
                'Content-Disposition': `attachment; filename="analytics_export_${request.project_id}_${timeRange}.json"`,
              }, 
              status: 200 
            }
          )
        }
      }

      case 'schedule': {
        // Only project owners can manage schedules
        const { data: member } = await supabaseClient
          .from('project_members')
          .select('role')
          .eq('user_id', user.id)
          .eq('role', 'OWNER')
          .single()

        if (!member) {
          throw new Error('Only project owners can manage analytics schedules')
        }

        if (!request.schedule_config) {
          // Get current schedules
          const { data: schedules } = await supabaseClient
            .from('memory_analytics_schedules')
            .select('*')
            .order('job_name')

          return new Response(
            JSON.stringify({ schedules }),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
          )
        } else {
          // Update schedule
          const { error } = await supabaseClient
            .from('memory_analytics_schedules')
            .update({ is_active: request.schedule_config.enabled })
            .eq('job_type', request.schedule_config.job_type)

          if (error) throw error

          return new Response(
            JSON.stringify({ 
              success: true,
              job_type: request.schedule_config.job_type,
              enabled: request.schedule_config.enabled,
            }),
            { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
          )
        }
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