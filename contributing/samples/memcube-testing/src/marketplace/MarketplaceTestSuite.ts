import { MemCubeTestHarness, MemCube, MemCubeType } from '../core/MemCubeTestHarness'
import { SupabaseClient } from '@supabase/supabase-js'

export interface MarketplaceMemCube extends MemCube {
  description: string
  category: string
  tags: string[]
  downloads: number
  rating: number
  price: number
  creator_id: string
  published_at: string
}

export interface PublishOptions {
  description: string
  category: string
  tags: string[]
  price: number
}

export interface SearchOptions {
  category?: string
  type?: MemCubeType
  minPrice?: number
  maxPrice?: number
  sortBy?: 'downloads' | 'rating' | 'newest' | 'price'
  limit?: number
}

export interface MarketplaceResult {
  success: boolean
  error?: string
  data?: any
}

export interface SearchResult extends MarketplaceResult {
  results: MarketplaceMemCube[]
}

export class MarketplaceTestSuite {
  private harness: MemCubeTestHarness
  private supabase: SupabaseClient

  constructor(harness: MemCubeTestHarness) {
    this.harness = harness
    // Access the supabase client from harness (would need to expose it)
    this.supabase = (harness as any).supabase
  }

  async createTestProject(project: { name: string; description: string }): Promise<string> {
    const { data, error } = await this.supabase
      .from('projects')
      .insert({
        id: crypto.randomUUID(),
        name: project.name,
        description: project.description,
        created_at: new Date().toISOString(),
      })
      .select()
      .single()

    if (error) throw new Error(`Failed to create project: ${error.message}`)
    return data.id
  }

  async deleteTestProject(projectId: string): Promise<void> {
    const { error } = await this.supabase
      .from('projects')
      .delete()
      .eq('id', projectId)

    if (error) throw new Error(`Failed to delete project: ${error.message}`)
  }

  async publishMemCube(
    memCubeId: string,
    options: PublishOptions
  ): Promise<MarketplaceResult> {
    try {
      // Check if already published
      const { data: existing } = await this.supabase
        .from('marketplace_memcubes')
        .select('id')
        .eq('id', memCubeId)
        .single()

      if (existing) {
        return {
          success: false,
          error: 'MemCube is already published',
        }
      }

      // Publish to marketplace
      const { data, error } = await this.supabase
        .from('marketplace_memcubes')
        .insert({
          id: memCubeId,
          description: options.description,
          category: options.category,
          tags: options.tags,
          price: options.price,
          downloads: 0,
          rating: 0,
          creator_id: 'test-user-id', // In real scenario, get from auth
          published_at: new Date().toISOString(),
        })
        .select()
        .single()

      return {
        success: !error,
        error: error?.message,
        data,
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  async unpublishMemCube(memCubeId: string): Promise<MarketplaceResult> {
    try {
      const { error } = await this.supabase
        .from('marketplace_memcubes')
        .delete()
        .eq('id', memCubeId)

      return {
        success: !error,
        error: error?.message,
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  async searchMarketplace(
    query: string = '',
    options: SearchOptions = {}
  ): Promise<SearchResult> {
    try {
      let queryBuilder = this.supabase
        .from('marketplace_memcubes')
        .select(`
          *,
          memories!inner(*)
        `)

      // Text search
      if (query) {
        queryBuilder = queryBuilder.or(
          `memories.label.ilike.%${query}%,description.ilike.%${query}%`
        )
      }

      // Category filter
      if (options.category) {
        queryBuilder = queryBuilder.eq('category', options.category)
      }

      // Type filter
      if (options.type) {
        queryBuilder = queryBuilder.eq('memories.type', options.type)
      }

      // Price range
      if (options.minPrice !== undefined) {
        queryBuilder = queryBuilder.gte('price', options.minPrice)
      }
      if (options.maxPrice !== undefined) {
        queryBuilder = queryBuilder.lte('price', options.maxPrice)
      }

      // Sorting
      switch (options.sortBy) {
        case 'downloads':
          queryBuilder = queryBuilder.order('downloads', { ascending: false })
          break
        case 'rating':
          queryBuilder = queryBuilder.order('rating', { ascending: false })
          break
        case 'newest':
          queryBuilder = queryBuilder.order('published_at', { ascending: false })
          break
        case 'price':
          queryBuilder = queryBuilder.order('price', { ascending: true })
          break
      }

      // Limit
      if (options.limit) {
        queryBuilder = queryBuilder.limit(options.limit)
      }

      const { data, error } = await queryBuilder

      // Transform results
      const results: MarketplaceMemCube[] = data?.map(item => ({
        ...item.memories,
        description: item.description,
        category: item.category,
        tags: item.tags,
        downloads: item.downloads,
        rating: item.rating,
        price: item.price,
        creator_id: item.creator_id,
        published_at: item.published_at,
      })) || []

      return {
        success: !error,
        error: error?.message,
        results,
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        results: [],
      }
    }
  }

  async addMemCubeToProject(
    memCubeId: string,
    projectId: string
  ): Promise<MarketplaceResult> {
    try {
      // Add to project_memcubes junction table
      const { data, error } = await this.supabase
        .from('project_memcubes')
        .insert({
          project_id: projectId,
          memcube_id: memCubeId,
          added_at: new Date().toISOString(),
          added_by: 'test-user-id',
        })
        .select()
        .single()

      if (!error) {
        // Increment download count
        await this.supabase.rpc('increment_downloads', {
          memcube_id: memCubeId,
        })
      }

      return {
        success: !error,
        error: error?.message,
        data,
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  async getProjectMemCubes(projectId: string): Promise<MemCube[]> {
    try {
      // Get MemCubes directly owned by project
      const { data: owned } = await this.supabase
        .from('memories')
        .select('*')
        .eq('project_id', projectId)

      // Get MemCubes added from marketplace
      const { data: added } = await this.supabase
        .from('project_memcubes')
        .select(`
          memories!inner(*)
        `)
        .eq('project_id', projectId)

      const ownedMemCubes = owned || []
      const addedMemCubes = added?.map(item => item.memories) || []

      return [...ownedMemCubes, ...addedMemCubes]
    } catch (error) {
      return []
    }
  }

  async simulateUserRating(
    memCubeId: string,
    rating: number
  ): Promise<MarketplaceResult> {
    try {
      const { data, error } = await this.supabase
        .from('memcube_ratings')
        .insert({
          memcube_id: memCubeId,
          user_id: 'test-user-id',
          rating,
          created_at: new Date().toISOString(),
        })
        .select()
        .single()

      if (!error) {
        // Update average rating
        await this.updateAverageRating(memCubeId)
      }

      return {
        success: !error,
        error: error?.message,
        data,
      }
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      }
    }
  }

  private async updateAverageRating(memCubeId: string): Promise<void> {
    const { data: ratings } = await this.supabase
      .from('memcube_ratings')
      .select('rating')
      .eq('memcube_id', memCubeId)

    if (ratings && ratings.length > 0) {
      const avgRating = ratings.reduce((sum, r) => sum + r.rating, 0) / ratings.length
      
      await this.supabase
        .from('marketplace_memcubes')
        .update({ rating: avgRating })
        .eq('id', memCubeId)
    }
  }
}