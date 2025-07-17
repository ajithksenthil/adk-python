import { describe, it, expect, beforeAll, afterAll } from 'vitest'
import { MemCubeTestHarness } from '../../src/core/MemCubeTestHarness'
import { MarketplaceTestSuite } from '../../src/marketplace/MarketplaceTestSuite'

describe('Marketplace Integration Tests', () => {
  let harness: MemCubeTestHarness
  let marketplace: MarketplaceTestSuite
  let testProjectId: string
  let publishedMemCubes: string[] = []

  beforeAll(async () => {
    harness = new MemCubeTestHarness(
      process.env.SUPABASE_URL!,
      process.env.SUPABASE_ANON_KEY!,
      process.env.OPENAI_API_KEY!
    )
    
    marketplace = new MarketplaceTestSuite(harness)
    
    // Create a test project
    testProjectId = await marketplace.createTestProject({
      name: 'Integration Test Project',
      description: 'Project for marketplace integration tests',
    })
  })

  afterAll(async () => {
    // Cleanup published MemCubes
    for (const memCubeId of publishedMemCubes) {
      await marketplace.unpublishMemCube(memCubeId)
    }
    
    // Delete test project
    await marketplace.deleteTestProject(testProjectId)
  })

  describe('Publishing MemCubes', () => {
    it('should publish a MemCube to marketplace', async () => {
      // Create a MemCube
      const createResult = await harness.createMemCube({
        project_id: testProjectId,
        label: 'React Component Library',
        type: 'TEMPLATE',
        content: 'export const Button = ({ children, onClick }) => <button onClick={onClick}>{children}</button>',
        metadata: {
          category: 'Frontend',
          tags: ['react', 'components', 'ui'],
          price: 0,
        },
      })

      expect(createResult.success).toBe(true)
      const memCubeId = createResult.memCubeId

      // Publish to marketplace
      const publishResult = await marketplace.publishMemCube(memCubeId, {
        description: 'A collection of reusable React components',
        category: 'Frontend',
        tags: ['react', 'components', 'ui'],
        price: 0,
      })

      expect(publishResult.success).toBe(true)
      publishedMemCubes.push(memCubeId)

      // Verify it appears in marketplace
      const searchResult = await marketplace.searchMarketplace('React Component')
      expect(searchResult.results.some(mc => mc.id === memCubeId)).toBe(true)
    })

    it('should handle duplicate publishing', async () => {
      const createResult = await harness.createMemCube({
        project_id: testProjectId,
        label: 'Test MemCube',
        type: 'PLAINTEXT',
        content: 'Test content',
      })

      const memCubeId = createResult.memCubeId

      // First publish
      await marketplace.publishMemCube(memCubeId, {
        description: 'Test',
        category: 'Documentation',
        tags: ['test'],
        price: 0,
      })

      // Attempt duplicate publish
      const duplicateResult = await marketplace.publishMemCube(memCubeId, {
        description: 'Test',
        category: 'Documentation',
        tags: ['test'],
        price: 0,
      })

      expect(duplicateResult.success).toBe(false)
      expect(duplicateResult.error).toContain('already published')
      
      publishedMemCubes.push(memCubeId)
    })
  })

  describe('Marketplace Search', () => {
    beforeAll(async () => {
      // Create and publish test MemCubes
      const testData = [
        {
          label: 'Python Data Science Toolkit',
          type: 'COMMAND' as const,
          content: 'import pandas as pd\nimport numpy as np',
          category: 'Data Science',
          tags: ['python', 'data-science', 'pandas'],
          price: 15,
        },
        {
          label: 'AWS CloudFormation Templates',
          type: 'TEMPLATE' as const,
          content: 'AWSTemplateFormatVersion: 2010-09-09',
          category: 'DevOps',
          tags: ['aws', 'infrastructure', 'cloudformation'],
          price: 25,
        },
        {
          label: 'Marketing Copy Generator',
          type: 'SEMANTIC' as const,
          content: 'Generate engaging marketing copy for products',
          category: 'Marketing',
          tags: ['marketing', 'copywriting', 'ai'],
          price: 10,
        },
      ]

      for (const data of testData) {
        const result = await harness.createMemCube({
          project_id: testProjectId,
          label: data.label,
          type: data.type,
          content: data.content,
        })

        if (result.success) {
          await marketplace.publishMemCube(result.memCubeId, {
            description: `${data.label} description`,
            category: data.category,
            tags: data.tags,
            price: data.price,
          })
          publishedMemCubes.push(result.memCubeId)
        }
      }
    })

    it('should search by keyword', async () => {
      const result = await marketplace.searchMarketplace('Python')
      
      expect(result.success).toBe(true)
      expect(result.results.length).toBeGreaterThan(0)
      expect(result.results[0].label).toContain('Python')
    })

    it('should filter by category', async () => {
      const result = await marketplace.searchMarketplace('', {
        category: 'DevOps',
      })

      expect(result.success).toBe(true)
      result.results.forEach(mc => {
        expect(mc.category).toBe('DevOps')
      })
    })

    it('should filter by type', async () => {
      const result = await marketplace.searchMarketplace('', {
        type: 'TEMPLATE',
      })

      expect(result.success).toBe(true)
      result.results.forEach(mc => {
        expect(mc.type).toBe('TEMPLATE')
      })
    })

    it('should filter by price range', async () => {
      const result = await marketplace.searchMarketplace('', {
        minPrice: 10,
        maxPrice: 20,
      })

      expect(result.success).toBe(true)
      result.results.forEach(mc => {
        expect(mc.price).toBeGreaterThanOrEqual(10)
        expect(mc.price).toBeLessThanOrEqual(20)
      })
    })

    it('should sort by popularity', async () => {
      const result = await marketplace.searchMarketplace('', {
        sortBy: 'downloads',
      })

      expect(result.success).toBe(true)
      for (let i = 1; i < result.results.length; i++) {
        expect(result.results[i - 1].downloads).toBeGreaterThanOrEqual(result.results[i].downloads)
      }
    })
  })

  describe('Project Integration', () => {
    it('should add MemCube from marketplace to project', async () => {
      // Search for a MemCube
      const searchResult = await marketplace.searchMarketplace('Python')
      expect(searchResult.results.length).toBeGreaterThan(0)
      
      const memCubeToAdd = searchResult.results[0]
      
      // Create a new project
      const newProjectId = await marketplace.createTestProject({
        name: 'Consumer Project',
        description: 'Project that consumes marketplace MemCubes',
      })

      // Add MemCube to project
      const addResult = await marketplace.addMemCubeToProject(
        memCubeToAdd.id,
        newProjectId
      )

      expect(addResult.success).toBe(true)

      // Verify MemCube is accessible in project
      const projectMemCubes = await marketplace.getProjectMemCubes(newProjectId)
      expect(projectMemCubes.some(mc => mc.id === memCubeToAdd.id)).toBe(true)

      // Cleanup
      await marketplace.deleteTestProject(newProjectId)
    })

    it('should track download statistics', async () => {
      const searchResult = await marketplace.searchMarketplace('', { limit: 1 })
      const memCube = searchResult.results[0]
      const initialDownloads = memCube.downloads

      // Add to project (counts as download)
      const newProjectId = await marketplace.createTestProject({
        name: 'Download Test Project',
        description: 'Test download tracking',
      })

      await marketplace.addMemCubeToProject(memCube.id, newProjectId)

      // Check updated download count
      const updatedSearch = await marketplace.searchMarketplace(memCube.label)
      const updatedMemCube = updatedSearch.results.find(mc => mc.id === memCube.id)
      
      expect(updatedMemCube!.downloads).toBe(initialDownloads + 1)

      // Cleanup
      await marketplace.deleteTestProject(newProjectId)
    })
  })

  describe('Access Control', () => {
    it('should respect project isolation', async () => {
      // Create two projects
      const project1 = await marketplace.createTestProject({
        name: 'Project 1',
        description: 'First project',
      })

      const project2 = await marketplace.createTestProject({
        name: 'Project 2',
        description: 'Second project',
      })

      // Create MemCube in project1
      const result = await harness.createMemCube({
        project_id: project1,
        label: 'Private MemCube',
        type: 'PLAINTEXT',
        content: 'This should only be accessible in project1',
      })

      // Try to access from project2 context
      const project2MemCubes = await marketplace.getProjectMemCubes(project2)
      expect(project2MemCubes.some(mc => mc.id === result.memCubeId)).toBe(false)

      // Verify accessible from project1
      const project1MemCubes = await marketplace.getProjectMemCubes(project1)
      expect(project1MemCubes.some(mc => mc.id === result.memCubeId)).toBe(true)

      // Cleanup
      await marketplace.deleteTestProject(project1)
      await marketplace.deleteTestProject(project2)
    })

    it('should handle unauthorized access attempts', async () => {
      // Attempt to publish without proper authorization
      const result = await marketplace.publishMemCube('invalid-id', {
        description: 'Test',
        category: 'Test',
        tags: ['test'],
        price: 0,
      })

      expect(result.success).toBe(false)
      expect(result.error).toBeDefined()
    })
  })
})