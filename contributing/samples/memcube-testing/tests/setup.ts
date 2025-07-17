import { vi } from 'vitest'
import { config } from 'dotenv'

// Load test environment variables
config({ path: '.env.test' })

// Mock Supabase client
vi.mock('@supabase/supabase-js', () => ({
  createClient: vi.fn(() => ({
    from: vi.fn(() => ({
      select: vi.fn().mockReturnThis(),
      insert: vi.fn().mockReturnThis(),
      update: vi.fn().mockReturnThis(),
      delete: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      single: vi.fn(),
    })),
    rpc: vi.fn(),
    storage: {
      from: vi.fn(() => ({
        upload: vi.fn(),
        download: vi.fn(),
        remove: vi.fn(),
      })),
    },
  })),
}))

// Global test utilities
global.testUtils = {
  generateMemCube: (overrides = {}) => ({
    id: crypto.randomUUID(),
    label: 'Test MemCube',
    type: 'PLAINTEXT',
    content: 'Test content',
    embedding: Array(1536).fill(0).map(() => Math.random()),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  }),
  
  generateProject: (overrides = {}) => ({
    id: crypto.randomUUID(),
    name: 'Test Project',
    description: 'Test project description',
    created_at: new Date().toISOString(),
    ...overrides,
  }),
}