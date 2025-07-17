import { describe, it, expect, beforeEach, vi } from 'vitest'
import { MemCubeTestHarness } from '../../src/core/MemCubeTestHarness'

describe('MemCube CRUD Operations', () => {
  let harness: MemCubeTestHarness
  
  beforeEach(() => {
    harness = new MemCubeTestHarness(
      process.env.SUPABASE_URL || 'http://localhost:54321',
      process.env.SUPABASE_ANON_KEY || 'test-key',
      process.env.OPENAI_API_KEY || 'test-key'
    )
    harness.clearTestResults()
  })

  describe('Create Operations', () => {
    it('should create a PLAINTEXT MemCube', async () => {
      const memCube = {
        project_id: 'test-project',
        label: 'Test Documentation',
        type: 'PLAINTEXT' as const,
        content: 'This is test documentation content',
      }

      const result = await harness.createMemCube(memCube)

      expect(result.success).toBe(true)
      expect(result.operation).toBe('create')
      expect(result.duration).toBeGreaterThan(0)
      expect(result.metadata?.size).toBe(memCube.content.length)
    })

    it('should create a SEMANTIC MemCube with embeddings', async () => {
      const memCube = {
        project_id: 'test-project',
        label: 'Semantic Knowledge',
        type: 'SEMANTIC' as const,
        content: 'This content will be embedded for semantic search',
      }

      const result = await harness.createMemCube(memCube)

      expect(result.success).toBe(true)
      expect(result.operation).toBe('create')
      expect(result.duration).toBeGreaterThan(0)
    })

    it('should create a COMMAND MemCube', async () => {
      const memCube = {
        project_id: 'test-project',
        label: 'Python Script',
        type: 'COMMAND' as const,
        content: 'def hello_world():\n    print("Hello, World!")',
      }

      const result = await harness.createMemCube(memCube)

      expect(result.success).toBe(true)
      expect(result.operation).toBe('create')
    })

    it('should create a TEMPLATE MemCube', async () => {
      const memCube = {
        project_id: 'test-project',
        label: 'React Component Template',
        type: 'TEMPLATE' as const,
        content: 'export const Component = ({ children }) => <div>{children}</div>',
      }

      const result = await harness.createMemCube(memCube)

      expect(result.success).toBe(true)
      expect(result.operation).toBe('create')
    })
  })

  describe('Read Operations', () => {
    it('should read an existing MemCube', async () => {
      // First create a MemCube
      const createResult = await harness.createMemCube({
        project_id: 'test-project',
        label: 'Test MemCube',
        type: 'PLAINTEXT',
        content: 'Test content',
      })

      expect(createResult.success).toBe(true)
      const memCubeId = createResult.memCubeId

      // Then read it
      const readResult = await harness.readMemCube(memCubeId)

      expect(readResult.success).toBe(true)
      expect(readResult.operation).toBe('read')
      expect(readResult.memCubeId).toBe(memCubeId)
      expect(readResult.metadata?.found).toBe(true)
    })

    it('should handle reading non-existent MemCube', async () => {
      const result = await harness.readMemCube('non-existent-id')

      expect(result.success).toBe(false)
      expect(result.operation).toBe('read')
      expect(result.metadata?.found).toBe(false)
    })
  })

  describe('Search Operations', () => {
    beforeEach(async () => {
      // Create test data
      const testMemCubes = [
        {
          project_id: 'test-project',
          label: 'React Hooks Guide',
          type: 'PLAINTEXT' as const,
          content: 'Complete guide to React hooks including useState, useEffect, and custom hooks',
        },
        {
          project_id: 'test-project',
          label: 'Python Data Analysis',
          type: 'COMMAND' as const,
          content: 'import pandas as pd\nimport numpy as np\n# Data analysis scripts',
        },
        {
          project_id: 'test-project',
          label: 'Machine Learning Basics',
          type: 'SEMANTIC' as const,
          content: 'Introduction to machine learning concepts including supervised and unsupervised learning',
        },
      ]

      for (const memCube of testMemCubes) {
        await harness.createMemCube(memCube)
      }
    })

    it('should perform text search', async () => {
      const result = await harness.searchMemCubes('React', undefined, 10)

      expect(result.success).toBe(true)
      expect(result.operation).toBe('search')
      expect(result.metadata?.searchType).toBe('text')
      expect(result.results).toBeDefined()
      expect(result.results!.length).toBeGreaterThan(0)
    })

    it('should perform semantic search', async () => {
      const result = await harness.searchMemCubes(
        'How to build user interfaces with components',
        'SEMANTIC',
        5
      )

      expect(result.success).toBe(true)
      expect(result.operation).toBe('search')
      expect(result.metadata?.searchType).toBe('semantic')
      expect(result.results).toBeDefined()
    })

    it('should filter search by type', async () => {
      const result = await harness.searchMemCubes('data', 'COMMAND', 10)

      expect(result.success).toBe(true)
      expect(result.operation).toBe('search')
      expect(result.results).toBeDefined()
      // All results should be COMMAND type
      result.results?.forEach(memCube => {
        expect(memCube.type).toBe('COMMAND')
      })
    })
  })

  describe('Performance Metrics', () => {
    it('should track operation duration', async () => {
      const operations = [
        () => harness.createMemCube({
          project_id: 'test-project',
          label: 'Test 1',
          type: 'PLAINTEXT' as const,
          content: 'Content 1',
        }),
        () => harness.createMemCube({
          project_id: 'test-project',
          label: 'Test 2',
          type: 'PLAINTEXT' as const,
          content: 'Content 2',
        }),
      ]

      const results = await harness.runBatchTest(operations, 2)

      expect(results).toHaveLength(2)
      results.forEach(result => {
        expect(result.duration).toBeGreaterThan(0)
        expect(result.duration).toBeLessThan(5000) // Should complete within 5 seconds
      })
    })

    it('should calculate efficacy metrics', () => {
      const relevantResults = new Set(['id1', 'id2', 'id3', 'id4', 'id5'])
      const retrievedResults = ['id1', 'id2', 'id3', 'id6', 'id7']

      const metrics = harness.calculateEfficacyMetrics(relevantResults, retrievedResults)

      expect(metrics.precision).toBe(0.6) // 3/5 retrieved are relevant
      expect(metrics.recall).toBe(0.6) // 3/5 relevant were retrieved
      expect(metrics.f1Score).toBeCloseTo(0.6)
      expect(metrics.accuracy).toBe(metrics.f1Score)
    })
  })

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      // Create harness with invalid URL
      const errorHarness = new MemCubeTestHarness(
        'http://invalid-url',
        'invalid-key',
        'invalid-key'
      )

      const result = await errorHarness.createMemCube({
        project_id: 'test-project',
        label: 'Test',
        type: 'PLAINTEXT' as const,
        content: 'Test',
      })

      expect(result.success).toBe(false)
      expect(result.error).toBeDefined()
    })

    it('should handle validation errors', async () => {
      const result = await harness.createMemCube({
        project_id: 'test-project',
        label: '', // Invalid: empty label
        type: 'PLAINTEXT' as const,
        content: 'Test',
      })

      expect(result.success).toBe(false)
      expect(result.error).toBeDefined()
    })
  })
})