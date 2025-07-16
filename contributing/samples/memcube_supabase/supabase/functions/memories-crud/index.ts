import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.38.0'
import { z } from 'https://deno.land/x/zod@v3.22.4/mod.ts'

// Environment variables
const supabaseUrl = Deno.env.get('SUPABASE_URL')!
const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!

// Input validation schemas
const CreateMemorySchema = z.object({
  label: z.string().min(1),
  type: z.enum(['PLAINTEXT', 'ACTIVATION', 'PARAMETER']),
  content: z.string(),
  project_id: z.string(),
  tags: z.array(z.string()).optional(),
  governance: z.object({
    read_roles: z.array(z.string()).default(['MEMBER', 'AGENT']),
    write_roles: z.array(z.string()).default(['AGENT']),
    ttl_days: z.number().int().positive().default(365),
    shareable: z.boolean().default(true),
    license: z.string().nullable().optional(),
    pii_tagged: z.boolean().default(false)
  }).optional()
})

const UpdateMemorySchema = z.object({
  memory_id: z.string().uuid(),
  content: z.string(),
  increment_version: z.boolean().default(true)
})

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS
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

    // Get auth token and user context
    const authHeader = req.headers.get('Authorization')
    if (!authHeader) {
      throw new Error('No authorization header')
    }

    const token = authHeader.replace('Bearer ', '')
    const { data: { user }, error: authError } = await supabase.auth.getUser(token)
    
    if (authError || !user) {
      throw new Error('Invalid authentication')
    }

    const { action, ...params } = await req.json()

    switch (action) {
      case 'create':
        return await createMemory(supabase, user.id, params)
      
      case 'get':
        return await getMemory(supabase, params.memory_id)
      
      case 'update':
        return await updateMemory(supabase, user.id, params)
      
      case 'archive':
        return await archiveMemory(supabase, params.memory_id)
      
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

async function createMemory(supabase: any, userId: string, params: any) {
  // Validate input
  const validated = CreateMemorySchema.parse(params)
  
  // Calculate content size and storage mode
  const contentBytes = new TextEncoder().encode(validated.content).length
  const storageMode = getStorageMode(contentBytes)
  
  // Start transaction
  const { data: memory, error: memoryError } = await supabase
    .from('memories')
    .insert({
      project_id: validated.project_id,
      label: validated.label,
      type: validated.type,
      governance: validated.governance || {},
      created_by: userId,
      // Set initial priority based on type
      priority: validated.type === 'ACTIVATION' ? 'HOT' : 'WARM'
    })
    .select()
    .single()

  if (memoryError) {
    throw new Error(`Failed to create memory: ${memoryError.message}`)
  }

  // Store payload based on storage mode
  let payloadData: any = {
    memory_id: memory.id,
    storage_mode: storageMode,
    size_bytes: contentBytes,
    token_count: estimateTokenCount(validated.content)
  }

  if (storageMode === 'INLINE') {
    payloadData.content = validated.content
  } else if (storageMode === 'COMPRESSED') {
    // Compress content
    const compressed = await compressContent(validated.content)
    payloadData.content_binary = compressed
  } else {
    // Store in blob storage
    const blobUrl = await uploadToStorage(supabase, memory.id, validated.content)
    payloadData.content_url = blobUrl
  }

  const { error: payloadError } = await supabase
    .from('memory_payloads')
    .insert(payloadData)

  if (payloadError) {
    // Rollback by deleting memory
    await supabase.from('memories').delete().eq('id', memory.id)
    throw new Error(`Failed to store payload: ${payloadError.message}`)
  }

  // Create initial version record
  await supabase
    .from('memory_versions')
    .insert({
      memory_id: memory.id,
      version: 1,
      created_by: userId,
      changes: { action: 'created' }
    })

  // Log event
  await supabase
    .from('memory_events')
    .insert({
      memory_id: memory.id,
      event: 'CREATED',
      actor: userId,
      meta: { type: validated.type, storage_mode: storageMode }
    })

  // Generate embedding if configured
  if (validated.type === 'PLAINTEXT' && Deno.env.get('OPENAI_API_KEY')) {
    // Fire and forget - don't wait for embedding
    generateEmbedding(supabase, memory.id, validated.content)
  }

  return new Response(
    JSON.stringify({
      id: memory.id,
      label: memory.label,
      type: memory.type,
      created_at: memory.created_at
    }),
    { 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function getMemory(supabase: any, memoryId: string) {
  // Get memory with payload
  const { data: memory, error } = await supabase
    .from('memories')
    .select(`
      *,
      memory_payloads (
        content,
        content_url,
        storage_mode,
        token_count
      )
    `)
    .eq('id', memoryId)
    .single()

  if (error || !memory) {
    throw new Error('Memory not found')
  }

  // Increment usage stats
  await supabase.rpc('increment_memory_usage', { memory_uuid: memoryId })

  // Retrieve content based on storage mode
  let content = ''
  const payload = memory.memory_payloads[0]
  
  if (payload.storage_mode === 'INLINE') {
    content = payload.content
  } else if (payload.storage_mode === 'COMPRESSED') {
    // Decompress
    content = await decompressContent(payload.content_binary)
  } else if (payload.content_url) {
    // Fetch from storage
    content = await fetchFromStorage(supabase, payload.content_url)
  }

  return new Response(
    JSON.stringify({
      id: memory.id,
      label: memory.label,
      type: memory.type,
      content: formatMemoryContent(memory.label, content),
      metadata: {
        version: memory.version,
        created_by: memory.created_by,
        created_at: memory.created_at,
        usage_hits: memory.usage_hits,
        priority: memory.priority,
        token_count: payload.token_count
      }
    }),
    { 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function updateMemory(supabase: any, userId: string, params: any) {
  const validated = UpdateMemorySchema.parse(params)
  
  // Get current memory
  const { data: current, error: fetchError } = await supabase
    .from('memories')
    .select('*, memory_payloads(*)')
    .eq('id', validated.memory_id)
    .single()

  if (fetchError || !current) {
    throw new Error('Memory not found')
  }

  // Check write access
  if (!hasWriteAccess(current.governance, userId)) {
    throw new Error('No write access')
  }

  const newVersion = validated.increment_version ? current.version + 1 : current.version
  const contentBytes = new TextEncoder().encode(validated.content).length
  const storageMode = getStorageMode(contentBytes)

  // Update memory version
  const { error: updateError } = await supabase
    .from('memories')
    .update({
      version: newVersion,
      updated_at: new Date().toISOString()
    })
    .eq('id', validated.memory_id)

  if (updateError) {
    throw new Error(`Update failed: ${updateError.message}`)
  }

  // Update payload
  await supabase
    .from('memory_payloads')
    .update({
      content: storageMode === 'INLINE' ? validated.content : null,
      storage_mode: storageMode,
      size_bytes: contentBytes,
      token_count: estimateTokenCount(validated.content)
    })
    .eq('memory_id', validated.memory_id)

  // Create version record
  if (validated.increment_version) {
    await supabase
      .from('memory_versions')
      .insert({
        memory_id: validated.memory_id,
        version: newVersion,
        created_by: userId,
        changes: { 
          action: 'updated',
          previous_version: current.version,
          size_change: contentBytes - current.memory_payloads[0].size_bytes
        }
      })
  }

  // Log event
  await supabase
    .from('memory_events')
    .insert({
      memory_id: validated.memory_id,
      event: 'UPDATED',
      actor: userId,
      meta: { version: newVersion }
    })

  return new Response(
    JSON.stringify({
      id: validated.memory_id,
      version: newVersion,
      updated_at: new Date().toISOString()
    }),
    { 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

async function archiveMemory(supabase: any, memoryId: string) {
  const { error } = await supabase
    .from('memories')
    .update({
      lifecycle: 'ARCHIVED',
      priority: 'COLD',
      updated_at: new Date().toISOString()
    })
    .eq('id', memoryId)

  if (error) {
    throw new Error(`Archive failed: ${error.message}`)
  }

  // Log event
  await supabase
    .from('memory_events')
    .insert({
      memory_id: memoryId,
      event: 'ARCHIVED',
      actor: 'system'
    })

  return new Response(
    JSON.stringify({ 
      status: 'archived',
      memory_id: memoryId 
    }),
    { 
      headers: { ...corsHeaders, 'Content-Type': 'application/json' }
    }
  )
}

// Helper functions
function getStorageMode(sizeBytes: number): string {
  if (sizeBytes < 4096) return 'INLINE'
  if (sizeBytes < 65536) return 'COMPRESSED'
  return 'COLD'
}

function estimateTokenCount(text: string): number {
  // Rough estimate: 1 token ≈ 4 characters
  return Math.ceil(text.length / 4)
}

function formatMemoryContent(label: string, content: string): string {
  return `<<MEM:${label}>>\n${content}\n<<ENDMEM>>`
}

function hasWriteAccess(governance: any, userId: string): boolean {
  const writeRoles = governance?.write_roles || ['AGENT']
  // In production, check actual user roles
  return true // Simplified for demo
}

async function compressContent(content: string): Promise<Uint8Array> {
  const encoder = new TextEncoder()
  const data = encoder.encode(content)
  const cs = new CompressionStream('gzip')
  const writer = cs.writable.getWriter()
  writer.write(data)
  writer.close()
  
  const chunks: Uint8Array[] = []
  const reader = cs.readable.getReader()
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
  }
  
  const compressed = new Uint8Array(chunks.reduce((acc, chunk) => acc + chunk.length, 0))
  let offset = 0
  for (const chunk of chunks) {
    compressed.set(chunk, offset)
    offset += chunk.length
  }
  
  return compressed
}

async function decompressContent(compressed: Uint8Array): Promise<string> {
  const ds = new DecompressionStream('gzip')
  const writer = ds.writable.getWriter()
  writer.write(compressed)
  writer.close()
  
  const chunks: Uint8Array[] = []
  const reader = ds.readable.getReader()
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    chunks.push(value)
  }
  
  const decompressed = new Uint8Array(chunks.reduce((acc, chunk) => acc + chunk.length, 0))
  let offset = 0
  for (const chunk of chunks) {
    decompressed.set(chunk, offset)
    offset += chunk.length
  }
  
  return new TextDecoder().decode(decompressed)
}

async function uploadToStorage(supabase: any, memoryId: string, content: string): Promise<string> {
  const { data, error } = await supabase.storage
    .from('memory-payloads')
    .upload(`${memoryId}.txt`, content, {
      contentType: 'text/plain',
      upsert: true
    })

  if (error) {
    throw new Error(`Storage upload failed: ${error.message}`)
  }

  return data.path
}

async function fetchFromStorage(supabase: any, path: string): Promise<string> {
  const { data, error } = await supabase.storage
    .from('memory-payloads')
    .download(path)

  if (error) {
    throw new Error(`Storage fetch failed: ${error.message}`)
  }

  return await data.text()
}

async function generateEmbedding(supabase: any, memoryId: string, content: string) {
  try {
    const response = await fetch('https://api.openai.com/v1/embeddings', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${Deno.env.get('OPENAI_API_KEY')}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'text-embedding-ada-002',
        input: content.slice(0, 8000) // Limit input size
      })
    })

    const result = await response.json()
    
    if (result.data?.[0]?.embedding) {
      await supabase
        .from('memories')
        .update({ embedding: result.data[0].embedding })
        .eq('id', memoryId)
    }
  } catch (error) {
    console.error('Embedding generation failed:', error)
    // Non-critical, don't throw
  }
}