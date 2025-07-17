import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Search, Database } from 'lucide-react'
import toast from 'react-hot-toast'
import MemCubeCard from '../components/marketplace/MemCubeCard'
import MemCubeDetailModal from '../components/marketplace/MemCubeDetailModal'
import AddToProjectModal from '../components/marketplace/AddToProjectModal'

interface MemCube {
  id: string
  label: string
  description: string
  type: 'PLAINTEXT' | 'SEMANTIC' | 'COMMAND' | 'TEMPLATE'
  category: string
  tags: string[]
  size: number
  downloads: number
  rating: number
  price: number
  creator: {
    id: string
    name: string
    avatar?: string
  }
  preview_content?: string
  created_at: string
  updated_at: string
}

export default function DataMarketplace() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [sortBy, setSortBy] = useState('popular')
  const [selectedMemCube, setSelectedMemCube] = useState<MemCube | null>(null)
  const [memCubeToAdd, setMemCubeToAdd] = useState<MemCube | null>(null)

  // Fetch available MemCubes
  const { data: memCubes, isLoading } = useQuery({
    queryKey: ['marketplace-memcubes', searchQuery, selectedCategory, selectedType, sortBy],
    queryFn: async () => {
      // Mock data - replace with real API call
      const mockMemCubes: MemCube[] = [
        {
          id: '1',
          label: 'React Component Library',
          description: 'A comprehensive collection of reusable React components with TypeScript support, including forms, modals, and data visualization components.',
          type: 'TEMPLATE',
          category: 'Frontend',
          tags: ['react', 'typescript', 'components', 'ui'],
          size: 2048000, // 2MB
          downloads: 1250,
          rating: 4.8,
          price: 0,
          creator: {
            id: 'creator1',
            name: 'React Team',
            avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=react',
          },
          preview_content: 'export const Button = ({ children, onClick, variant = "primary" }) => {...}',
          created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '2',
          label: 'Python Data Science Toolkit',
          description: 'Essential data science functions and utilities for Python, including data preprocessing, visualization, and machine learning helpers.',
          type: 'COMMAND',
          category: 'Data Science',
          tags: ['python', 'data-science', 'ml', 'pandas', 'numpy'],
          size: 5120000, // 5MB
          downloads: 3420,
          rating: 4.9,
          price: 15,
          creator: {
            id: 'creator2',
            name: 'DataSci Pro',
            avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=datasci',
          },
          preview_content: 'def preprocess_data(df, missing_strategy="mean", scale=True):...',
          created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '3',
          label: 'API Documentation Templates',
          description: 'Professional API documentation templates with OpenAPI/Swagger support, including examples for REST, GraphQL, and WebSocket APIs.',
          type: 'PLAINTEXT',
          category: 'Documentation',
          tags: ['api', 'documentation', 'openapi', 'swagger', 'rest'],
          size: 1024000, // 1MB
          downloads: 890,
          rating: 4.6,
          price: 0,
          creator: {
            id: 'creator3',
            name: 'API Docs Team',
            avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=apidocs',
          },
          preview_content: '# API Documentation\n\n## Endpoints\n\n### GET /api/v1/users...',
          created_at: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '4',
          label: 'AWS Infrastructure Templates',
          description: 'Production-ready AWS CloudFormation and Terraform templates for common infrastructure patterns including VPC, ECS, Lambda, and more.',
          type: 'TEMPLATE',
          category: 'DevOps',
          tags: ['aws', 'infrastructure', 'terraform', 'cloudformation', 'devops'],
          size: 3072000, // 3MB
          downloads: 2100,
          rating: 4.7,
          price: 25,
          creator: {
            id: 'creator4',
            name: 'Cloud Architects',
            avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=cloud',
          },
          preview_content: 'resource "aws_vpc" "main" {\n  cidr_block = var.vpc_cidr...',
          created_at: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '5',
          label: 'Marketing Copy Generator',
          description: 'AI-powered marketing copy templates and prompts for various channels including social media, email campaigns, and landing pages.',
          type: 'SEMANTIC',
          category: 'Marketing',
          tags: ['marketing', 'copywriting', 'ai', 'prompts', 'content'],
          size: 512000, // 512KB
          downloads: 1560,
          rating: 4.5,
          price: 10,
          creator: {
            id: 'creator5',
            name: 'MarketingAI',
            avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=marketing',
          },
          preview_content: 'Generate compelling product descriptions that highlight...',
          created_at: new Date(Date.now() - 20 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '6',
          label: 'Smart Contract Library',
          description: 'Audited and optimized Solidity smart contracts for DeFi, NFTs, and DAOs with comprehensive test suites and deployment scripts.',
          type: 'TEMPLATE',
          category: 'Blockchain',
          tags: ['solidity', 'ethereum', 'smart-contracts', 'defi', 'web3'],
          size: 4096000, // 4MB
          downloads: 720,
          rating: 4.9,
          price: 50,
          creator: {
            id: 'creator6',
            name: 'Web3 Builders',
            avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=web3',
          },
          preview_content: 'pragma solidity ^0.8.0;\n\ncontract ERC20Token {...',
          created_at: new Date(Date.now() - 75 * 24 * 60 * 60 * 1000).toISOString(),
          updated_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ]

      // Apply filters
      let filtered = mockMemCubes

      // Search filter
      if (searchQuery) {
        filtered = filtered.filter(mc => 
          mc.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
          mc.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
          mc.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
        )
      }

      // Category filter
      if (selectedCategory !== 'all') {
        filtered = filtered.filter(mc => mc.category === selectedCategory)
      }

      // Type filter
      if (selectedType !== 'all') {
        filtered = filtered.filter(mc => mc.type === selectedType)
      }

      // Sorting
      switch (sortBy) {
        case 'popular':
          filtered.sort((a, b) => b.downloads - a.downloads)
          break
        case 'rating':
          filtered.sort((a, b) => b.rating - a.rating)
          break
        case 'newest':
          filtered.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
          break
        case 'price-low':
          filtered.sort((a, b) => a.price - b.price)
          break
        case 'price-high':
          filtered.sort((a, b) => b.price - a.price)
          break
      }

      return filtered
    },
  })

  // Add MemCube to project mutation
  const addToProjectMutation = useMutation({
    mutationFn: async ({ memCubeId, targetProjectId }: { memCubeId: string; targetProjectId: string }) => {
      // Implement add to project logic
      console.log('Adding MemCube to project:', memCubeId, targetProjectId)
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1500))
    },
    onSuccess: () => {
      toast.success('MemCube added to project successfully')
      setMemCubeToAdd(null)
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to add MemCube to project')
    },
  })

  const categories = [
    { value: 'all', label: 'All Categories', icon: Database },
    { value: 'Frontend', label: 'Frontend', icon: Database },
    { value: 'Backend', label: 'Backend', icon: Database },
    { value: 'Data Science', label: 'Data Science', icon: Database },
    { value: 'DevOps', label: 'DevOps', icon: Database },
    { value: 'Documentation', label: 'Documentation', icon: Database },
    { value: 'Marketing', label: 'Marketing', icon: Database },
    { value: 'Blockchain', label: 'Blockchain', icon: Database },
  ]

  const types = [
    { value: 'all', label: 'All Types' },
    { value: 'PLAINTEXT', label: 'Plain Text' },
    { value: 'SEMANTIC', label: 'Semantic' },
    { value: 'COMMAND', label: 'Command' },
    { value: 'TEMPLATE', label: 'Template' },
  ]

  const sortOptions = [
    { value: 'popular', label: 'Most Popular' },
    { value: 'rating', label: 'Highest Rated' },
    { value: 'newest', label: 'Newest' },
    { value: 'price-low', label: 'Price: Low to High' },
    { value: 'price-high', label: 'Price: High to Low' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Data Marketplace</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Discover and integrate MemCubes to enhance your AI agent teams
        </p>
      </div>

      {/* Search and Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
        <div className="space-y-4">
          {/* Search Bar */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search MemCubes by name, description, or tags..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
            />
          </div>

          {/* Filters Row */}
          <div className="flex flex-wrap gap-4">
            {/* Category Filter */}
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Category
              </label>
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              >
                {categories.map((cat) => (
                  <option key={cat.value} value={cat.value}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Type Filter */}
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Type
              </label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              >
                {types.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Sort By */}
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
              >
                {sortOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : memCubes && memCubes.length > 0 ? (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Found {memCubes.length} MemCube{memCubes.length !== 1 ? 's' : ''}
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {memCubes.map((memCube) => (
              <MemCubeCard
                key={memCube.id}
                memCube={memCube}
                onView={() => setSelectedMemCube(memCube)}
                onAddToProject={() => setMemCubeToAdd(memCube)}
              />
            ))}
          </div>
        </div>
      ) : (
        <div className="text-center py-12">
          <Database className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">
            No MemCubes found
          </h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Try adjusting your search or filters
          </p>
        </div>
      )}

      {/* MemCube Detail Modal */}
      {selectedMemCube && (
        <MemCubeDetailModal
          memCube={selectedMemCube}
          open={!!selectedMemCube}
          onClose={() => setSelectedMemCube(null)}
          onAddToProject={() => {
            setMemCubeToAdd(selectedMemCube)
            setSelectedMemCube(null)
          }}
        />
      )}

      {/* Add to Project Modal */}
      {memCubeToAdd && (
        <AddToProjectModal
          memCube={memCubeToAdd}
          open={!!memCubeToAdd}
          onClose={() => setMemCubeToAdd(null)}
          onConfirm={(targetProjectId) => {
            addToProjectMutation.mutate({
              memCubeId: memCubeToAdd.id,
              targetProjectId,
            })
          }}
          isLoading={addToProjectMutation.isPending}
        />
      )}
    </div>
  )
}