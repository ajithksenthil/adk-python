import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.38.0'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// Validation schemas
const CleanupSchema = z.object({
  type: z.enum(['cache', 'sessions', 'events', 'states']),
  project_id: z.string().uuid().optional(),
  older_than_hours: z.number().positive().default(24)
})

const ArchiveSchema = z.object({
  project_id: z.string().uuid(),
  include_memories: z.boolean().default(false),
  compress: z.boolean().default(true)
})

const MaintenanceSchema = z.object({
  tasks: z.array(z.enum([
    'vacuum_analyze',
    'update_statistics',
    'rebuild_indexes',
    'cleanup_expired',
    'optimize_storage'
  ])).default(['cleanup_expired'])
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
      case 'cleanup':
        return await performCleanup(supabase, await req.json())
      
      case 'archive-project':
        return await archiveProject(supabase, await req.json())
      
      case 'maintenance':
        return await runMaintenance(supabase, await req.json())
      
      case 'health-check':
        return await performHealthCheck(supabase)
      
      case 'migrate-storage':
        return await migrateStorage(supabase, await req.json())
      
      case 'compact-states':
        return await compactStates(supabase, await req.json())
        
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

async function performCleanup(supabase: any, params: any) {
  const validated = CleanupSchema.parse(params)
  const cutoffTime = new Date(Date.now() - validated.older_than_hours * 60 * 60 * 1000).toISOString()
  
  let results: any = {}
  
  switch (validated.type) {
    case 'cache':
      // Clean expired FSA slice cache
      const { count: cacheCount } = await supabase
        .from('fsa_slice_cache')
        .delete()
        .lt('expires_at', new Date().toISOString())
        .select('id', { count: 'exact', head: true })
      
      results.fsa_cache_cleaned = cacheCount || 0
      
      // Clean expired memory cache
      const { count: memCacheCount } = await supabase
        .from('memory_cache')
        .delete()
        .lt('expires_at', new Date().toISOString())
        .select('id', { count: 'exact', head: true })
      
      results.memory_cache_cleaned = memCacheCount || 0
      break
      
    case 'sessions':
      // End stale agent sessions
      const { data: staleSessions } = await supabase
        .from('agent_sessions')
        .select('id, agent_id')
        .is('ended_at', null)
        .lt('last_activity', cutoffTime)
      
      if (staleSessions && staleSessions.length > 0) {
        // Mark agents as offline
        const agentIds = [...new Set(staleSessions.map(s => s.agent_id))]
        await supabase
          .from('agents')
          .update({ status: 'OFFLINE' })
          .in('agent_id', agentIds)
        
        // End sessions
        await supabase
          .from('agent_sessions')
          .update({ ended_at: new Date().toISOString() })
          .in('id', staleSessions.map(s => s.id))
        
        results.sessions_ended = staleSessions.length
        results.agents_marked_offline = agentIds.length
      }
      break
      
    case 'events':
      // Remove expired events
      const { count: eventCount } = await supabase
        .from('events')
        .delete()
        .lt('expires_at', new Date().toISOString())
        .select('id', { count: 'exact', head: true })
      
      results.events_cleaned = eventCount || 0
      break
      
    case 'states':
      // Archive old state versions
      if (!validated.project_id) {
        throw new Error('project_id required for state cleanup')
      }
      
      // Keep only last N versions per FSA
      const { data: fsaIds } = await supabase
        .from('fsa_states')
        .select('fsa_id')
        .eq('project_id', validated.project_id)
        .distinct()
      
      for (const { fsa_id } of fsaIds || []) {
        // Get versions to keep (last 10)
        const { data: keepVersions } = await supabase
          .from('fsa_states')
          .select('version')
          .eq('project_id', validated.project_id)
          .eq('fsa_id', fsa_id)
          .order('version', { ascending: false })
          .limit(10)
        
        if (keepVersions && keepVersions.length > 0) {
          const minKeepVersion = Math.min(...keepVersions.map(v => v.version))
          
          // Archive older versions
          const { count } = await supabase
            .from('fsa_states')
            .update({ archived: true })
            .eq('project_id', validated.project_id)
            .eq('fsa_id', fsa_id)
            .lt('version', minKeepVersion)
            .select('id', { count: 'exact', head: true })
          
          results[`${fsa_id}_archived`] = count || 0
        }
      }
      break
  }
  
  // Log cleanup action
  await supabase
    .from('lifecycle_logs')
    .insert({
      action: 'cleanup',
      type: validated.type,
      results,
      project_id: validated.project_id
    })
  
  return new Response(
    JSON.stringify({
      success: true,
      type: validated.type,
      results
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function archiveProject(supabase: any, params: any) {
  const validated = ArchiveSchema.parse(params)
  
  // Check project exists
  const { data: project } = await supabase
    .from('projects')
    .select('*')
    .eq('id', validated.project_id)
    .single()
  
  if (!project) {
    throw new Error('Project not found')
  }
  
  if (project.archived) {
    throw new Error('Project already archived')
  }
  
  // Create archive record
  const { data: archive, error: archiveError } = await supabase
    .from('project_archives')
    .insert({
      project_id: validated.project_id,
      project_data: project,
      include_memories: validated.include_memories
    })
    .select()
    .single()
  
  if (archiveError) {
    throw new Error(`Failed to create archive: ${archiveError.message}`)
  }
  
  // Archive FSA states
  const { data: states } = await supabase
    .from('fsa_states')
    .select('*')
    .eq('project_id', validated.project_id)
    .order('version', { ascending: false })
    .limit(50) // Keep last 50 versions
  
  if (states && states.length > 0) {
    const stateArchive = validated.compress 
      ? await compressData(states)
      : states
    
    await supabase.storage
      .from('archives')
      .upload(
        `projects/${validated.project_id}/fsa-states.json${validated.compress ? '.gz' : ''}`,
        stateArchive
      )
  }
  
  // Archive memories if requested
  if (validated.include_memories) {
    const { data: memories } = await supabase
      .from('memories')
      .select('*')
      .eq('project_id', validated.project_id)
    
    if (memories && memories.length > 0) {
      const memoryArchive = validated.compress
        ? await compressData(memories)
        : memories
      
      await supabase.storage
        .from('archives')
        .upload(
          `projects/${validated.project_id}/memories.json${validated.compress ? '.gz' : ''}`,
          memoryArchive
        )
    }
  }
  
  // Mark project as archived
  await supabase
    .from('projects')
    .update({ archived: true, archived_at: new Date().toISOString() })
    .eq('id', validated.project_id)
  
  // Clean up active data (optional - could be done later)
  // This is a soft delete - data remains but is marked archived
  
  return new Response(
    JSON.stringify({
      success: true,
      archive_id: archive.id,
      project_id: validated.project_id,
      archived_at: new Date().toISOString()
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function runMaintenance(supabase: any, params: any) {
  const validated = MaintenanceSchema.parse(params)
  const results: any = {}
  
  for (const task of validated.tasks) {
    try {
      switch (task) {
        case 'vacuum_analyze':
          // Run VACUUM ANALYZE on main tables
          await supabase.rpc('run_vacuum_analyze')
          results[task] = { status: 'completed' }
          break
          
        case 'update_statistics':
          // Update table statistics
          await supabase.rpc('update_table_statistics')
          results[task] = { status: 'completed' }
          break
          
        case 'rebuild_indexes':
          // Rebuild indexes
          await supabase.rpc('rebuild_indexes')
          results[task] = { status: 'completed' }
          break
          
        case 'cleanup_expired':
          // Clean all expired data
          const cleanupTypes = ['cache', 'events'] as const
          for (const type of cleanupTypes) {
            const cleanup = await performCleanup(supabase, { type, older_than_hours: 24 })
            const cleanupResult = await cleanup.json()
            results[`${task}_${type}`] = cleanupResult.results
          }
          break
          
        case 'optimize_storage':
          // Optimize storage modes
          const { data: optimized } = await supabase.rpc('optimize_memory_storage')
          results[task] = { optimized_count: optimized || 0 }
          break
      }
    } catch (error) {
      results[task] = { status: 'failed', error: error.message }
    }
  }
  
  // Log maintenance
  await supabase
    .from('lifecycle_logs')
    .insert({
      action: 'maintenance',
      type: 'scheduled',
      results
    })
  
  return new Response(
    JSON.stringify({
      success: true,
      tasks: validated.tasks,
      results
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function performHealthCheck(supabase: any) {
  const health: any = {
    status: 'healthy',
    checks: {},
    timestamp: new Date().toISOString()
  }
  
  try {
    // Check database connectivity
    const { count: projectCount } = await supabase
      .from('projects')
      .select('id', { count: 'exact', head: true })
    
    health.checks.database = {
      status: 'ok',
      project_count: projectCount
    }
    
    // Check agent status
    const { data: agentStats } = await supabase
      .from('agents')
      .select('status')
      .select('status, count', { count: 'exact' })
      .group('status')
    
    health.checks.agents = {
      status: 'ok',
      stats: agentStats || []
    }
    
    // Check storage
    const { data: storageStats } = await supabase.storage
      .from('memories')
      .list('', { limit: 1 })
    
    health.checks.storage = {
      status: storageStats ? 'ok' : 'degraded'
    }
    
    // Check event processing
    const { count: unprocessedEvents } = await supabase
      .from('events')
      .select('id', { count: 'exact', head: true })
      .eq('processed', false)
      .lt('created_at', new Date(Date.now() - 5 * 60 * 1000).toISOString())
    
    if (unprocessedEvents && unprocessedEvents > 100) {
      health.checks.events = {
        status: 'warning',
        unprocessed_count: unprocessedEvents
      }
      health.status = 'degraded'
    } else {
      health.checks.events = {
        status: 'ok',
        unprocessed_count: unprocessedEvents || 0
      }
    }
    
    // Check FSA state size
    const { data: largeStates } = await supabase
      .rpc('get_large_fsa_states', { size_threshold_mb: 10 })
    
    if (largeStates && largeStates.length > 0) {
      health.checks.fsa_states = {
        status: 'warning',
        large_states: largeStates.length
      }
    } else {
      health.checks.fsa_states = { status: 'ok' }
    }
    
  } catch (error) {
    health.status = 'unhealthy'
    health.error = error.message
  }
  
  return new Response(
    JSON.stringify(health),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function migrateStorage(supabase: any, params: any) {
  const { project_id, from_mode, to_mode } = params
  
  // Migrate memory storage modes
  const { data: memories } = await supabase
    .from('memories')
    .select('*')
    .eq('project_id', project_id)
    .eq('storage_mode', from_mode)
  
  let migrated = 0
  
  for (const memory of memories || []) {
    try {
      // Re-evaluate storage mode
      await supabase.functions.invoke('memories-crud/update', {
        body: {
          memory_id: memory.id,
          storage_mode: to_mode
        }
      })
      
      migrated++
    } catch (error) {
      console.error(`Failed to migrate memory ${memory.id}:`, error)
    }
  }
  
  return new Response(
    JSON.stringify({
      success: true,
      migrated_count: migrated,
      total_count: memories?.length || 0
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

async function compactStates(supabase: any, params: any) {
  const { project_id, fsa_id, keep_versions = 10 } = params
  
  // Get all versions
  const { data: states } = await supabase
    .from('fsa_states')
    .select('*')
    .eq('project_id', project_id)
    .eq('fsa_id', fsa_id)
    .order('version', { ascending: false })
  
  if (!states || states.length <= keep_versions) {
    return new Response(
      JSON.stringify({
        success: true,
        message: 'No compaction needed',
        current_versions: states?.length || 0
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
    )
  }
  
  // Keep recent versions
  const versionsToKeep = states.slice(0, keep_versions)
  const versionsToCompact = states.slice(keep_versions)
  
  // Create compacted state
  const oldestKeptVersion = versionsToKeep[versionsToKeep.length - 1]
  const compactedState = {
    ...oldestKeptVersion,
    id: undefined,
    version: 0,
    compacted: true,
    compacted_versions: versionsToCompact.map(v => v.version),
    compacted_at: new Date().toISOString()
  }
  
  // Store compacted state
  await supabase
    .from('fsa_states_archive')
    .insert(compactedState)
  
  // Delete old versions
  const versionsToDelete = versionsToCompact.map(v => v.id)
  await supabase
    .from('fsa_states')
    .delete()
    .in('id', versionsToDelete)
  
  // Clean up related deltas
  await supabase
    .from('fsa_deltas')
    .delete()
    .in('state_id', versionsToDelete)
  
  return new Response(
    JSON.stringify({
      success: true,
      versions_kept: keep_versions,
      versions_compacted: versionsToCompact.length,
      space_saved_estimate: `${(versionsToCompact.length * 0.1).toFixed(2)} MB`
    }),
    { headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
  )
}

// Helper functions

async function compressData(data: any): Promise<Uint8Array> {
  const jsonStr = JSON.stringify(data)
  const encoder = new TextEncoder()
  const data_uint8 = encoder.encode(jsonStr)
  
  // Use CompressionStream API (available in Deno)
  const cs = new CompressionStream('gzip')
  const writer = cs.writable.getWriter()
  writer.write(data_uint8)
  writer.close()
  
  const compressed = []
  const reader = cs.readable.getReader()
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    compressed.push(...value)
  }
  
  return new Uint8Array(compressed)
}

// Additional tables needed

/*
CREATE TABLE lifecycle_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT NOT NULL,
    type TEXT NOT NULL,
    results JSONB,
    project_id UUID REFERENCES projects(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE project_archives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    project_data JSONB NOT NULL,
    include_memories BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE fsa_states_archive (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    fsa_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    state JSONB NOT NULL,
    compacted BOOLEAN DEFAULT false,
    compacted_versions INTEGER[],
    compacted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL
);

-- Add to existing tables
ALTER TABLE fsa_states ADD COLUMN archived BOOLEAN DEFAULT false;
ALTER TABLE projects ADD COLUMN archived_at TIMESTAMPTZ;

-- Helper functions
CREATE OR REPLACE FUNCTION get_large_fsa_states(size_threshold_mb INTEGER)
RETURNS TABLE(project_id UUID, fsa_id TEXT, size_mb DECIMAL) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        fs.project_id,
        fs.fsa_id,
        ROUND(pg_column_size(fs.state)::decimal / 1048576, 2) as size_mb
    FROM fsa_states fs
    WHERE pg_column_size(fs.state) > size_threshold_mb * 1048576
    ORDER BY pg_column_size(fs.state) DESC;
END;
$$ LANGUAGE plpgsql;
*/