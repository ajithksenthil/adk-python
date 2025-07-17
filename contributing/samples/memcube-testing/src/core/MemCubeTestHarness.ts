import { createClient, SupabaseClient } from '@supabase/supabase-js'
import OpenAI from 'openai'
import { z } from 'zod'

// MemCube types
export const MemCubeTypeSchema = z.enum(['PLAINTEXT', 'SEMANTIC', 'COMMAND', 'TEMPLATE'])
export type MemCubeType = z.infer<typeof MemCubeTypeSchema>

export const MemCubeSchema = z.object({
  id: z.string().uuid(),
  project_id: z.string(),
  label: z.string(),
  type: MemCubeTypeSchema,
  content: z.string().optional(),
  content_url: z.string().optional(),
  embedding: z.array(z.number()).optional(),
  metadata: z.record(z.any()).optional(),
  created_at: z.string(),
  updated_at: z.string(),
})

export type MemCube = z.infer<typeof MemCubeSchema>

// Test result types
export interface TestResult {
  testId: string
  memCubeId: string
  operation: 'create' | 'read' | 'update' | 'delete' | 'search'
  success: boolean
  duration: number
  error?: string
  metadata?: Record<string, any>
}

export interface EfficacyMetrics {
  accuracy: number // Semantic search accuracy
  recall: number // Percentage of relevant results retrieved
  precision: number // Percentage of retrieved results that are relevant
  f1Score: number // Harmonic mean of precision and recall
  avgResponseTime: number // Average operation time in ms
  throughput: number // Operations per second
  storageEfficiency: number // Compression ratio
}

export class MemCubeTestHarness {
  private supabase: SupabaseClient
  private openai: OpenAI
  private testResults: TestResult[] = []

  constructor(
    supabaseUrl: string,
    supabaseKey: string,
    openaiKey: string
  ) {
    this.supabase = createClient(supabaseUrl, supabaseKey)
    this.openai = new OpenAI({ apiKey: openaiKey })
  }

  // Core CRUD operations with timing
  async createMemCube(memCube: Omit<MemCube, 'id' | 'created_at' | 'updated_at'>): Promise<TestResult> {
    const testId = crypto.randomUUID()
    const startTime = performance.now()
    
    try {
      // Generate embedding if semantic type
      if (memCube.type === 'SEMANTIC' && memCube.content) {
        const embedding = await this.generateEmbedding(memCube.content)
        memCube.embedding = embedding
      }

      const { data, error } = await this.supabase
        .from('memories')
        .insert({
          ...memCube,
          id: crypto.randomUUID(),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        .select()
        .single()

      const duration = performance.now() - startTime
      const result: TestResult = {
        testId,
        memCubeId: data?.id || '',
        operation: 'create',
        success: !error,
        duration,
        error: error?.message,
        metadata: { size: memCube.content?.length || 0 },
      }

      this.testResults.push(result)
      return result
    } catch (error) {
      const duration = performance.now() - startTime
      const result: TestResult = {
        testId,
        memCubeId: '',
        operation: 'create',
        success: false,
        duration,
        error: error instanceof Error ? error.message : 'Unknown error',
      }
      this.testResults.push(result)
      return result
    }
  }

  async readMemCube(memCubeId: string): Promise<TestResult> {
    const testId = crypto.randomUUID()
    const startTime = performance.now()

    try {
      const { data, error } = await this.supabase
        .from('memories')
        .select('*')
        .eq('id', memCubeId)
        .single()

      const duration = performance.now() - startTime
      const result: TestResult = {
        testId,
        memCubeId,
        operation: 'read',
        success: !error,
        duration,
        error: error?.message,
        metadata: { found: !!data },
      }

      this.testResults.push(result)
      return result
    } catch (error) {
      const duration = performance.now() - startTime
      const result: TestResult = {
        testId,
        memCubeId,
        operation: 'read',
        success: false,
        duration,
        error: error instanceof Error ? error.message : 'Unknown error',
      }
      this.testResults.push(result)
      return result
    }
  }

  async searchMemCubes(
    query: string,
    type?: MemCubeType,
    limit: number = 10
  ): Promise<TestResult & { results?: MemCube[] }> {
    const testId = crypto.randomUUID()
    const startTime = performance.now()

    try {
      // For semantic search, generate query embedding
      if (type === 'SEMANTIC') {
        const queryEmbedding = await this.generateEmbedding(query)
        
        const { data, error } = await this.supabase.rpc('search_memories', {
          query_embedding: queryEmbedding,
          match_threshold: 0.7,
          match_count: limit,
        })

        const duration = performance.now() - startTime
        const result = {
          testId,
          memCubeId: '',
          operation: 'search' as const,
          success: !error,
          duration,
          error: error?.message,
          metadata: { 
            resultCount: data?.length || 0,
            searchType: 'semantic',
          },
          results: data || [],
        }

        this.testResults.push(result)
        return result
      } else {
        // Text search
        let query = this.supabase
          .from('memories')
          .select('*')
          .textSearch('label', query)

        if (type) {
          query = query.eq('type', type)
        }

        const { data, error } = await query.limit(limit)

        const duration = performance.now() - startTime
        const result = {
          testId,
          memCubeId: '',
          operation: 'search' as const,
          success: !error,
          duration,
          error: error?.message,
          metadata: { 
            resultCount: data?.length || 0,
            searchType: 'text',
          },
          results: data || [],
        }

        this.testResults.push(result)
        return result
      }
    } catch (error) {
      const duration = performance.now() - startTime
      const result = {
        testId,
        memCubeId: '',
        operation: 'search' as const,
        success: false,
        duration,
        error: error instanceof Error ? error.message : 'Unknown error',
        results: [],
      }
      this.testResults.push(result)
      return result
    }
  }

  // Generate embeddings using OpenAI
  private async generateEmbedding(text: string): Promise<number[]> {
    const response = await this.openai.embeddings.create({
      model: 'text-embedding-ada-002',
      input: text,
    })
    return response.data[0].embedding
  }

  // Calculate efficacy metrics
  calculateEfficacyMetrics(relevantResults: Set<string>, retrievedResults: string[]): EfficacyMetrics {
    const retrievedSet = new Set(retrievedResults)
    const correctlyRetrieved = retrievedResults.filter(id => relevantResults.has(id)).length
    
    const precision = retrievedResults.length > 0 ? correctlyRetrieved / retrievedResults.length : 0
    const recall = relevantResults.size > 0 ? correctlyRetrieved / relevantResults.size : 0
    const f1Score = precision + recall > 0 ? 2 * (precision * recall) / (precision + recall) : 0
    
    const successfulOps = this.testResults.filter(r => r.success)
    const avgResponseTime = successfulOps.length > 0
      ? successfulOps.reduce((sum, r) => sum + r.duration, 0) / successfulOps.length
      : 0
    
    const totalTime = this.testResults.reduce((sum, r) => sum + r.duration, 0)
    const throughput = totalTime > 0 ? (this.testResults.length / totalTime) * 1000 : 0
    
    // Calculate storage efficiency (mock for now)
    const storageEfficiency = 0.75 // Assume 25% compression
    
    return {
      accuracy: f1Score, // Using F1 as overall accuracy
      recall,
      precision,
      f1Score,
      avgResponseTime,
      throughput,
      storageEfficiency,
    }
  }

  // Batch testing utilities
  async runBatchTest(operations: Array<() => Promise<TestResult>>, concurrency: number = 5): Promise<TestResult[]> {
    const results: TestResult[] = []
    const batches = []
    
    for (let i = 0; i < operations.length; i += concurrency) {
      batches.push(operations.slice(i, i + concurrency))
    }
    
    for (const batch of batches) {
      const batchResults = await Promise.all(batch.map(op => op()))
      results.push(...batchResults)
    }
    
    return results
  }

  // Get all test results
  getTestResults(): TestResult[] {
    return this.testResults
  }

  // Clear test results
  clearTestResults(): void {
    this.testResults = []
  }

  // Export results for analysis
  exportResults(): string {
    return JSON.stringify({
      timestamp: new Date().toISOString(),
      totalTests: this.testResults.length,
      successRate: this.testResults.filter(r => r.success).length / this.testResults.length,
      results: this.testResults,
    }, null, 2)
  }
}