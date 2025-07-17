import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useSupabase } from '../contexts/SupabaseContext'
import { useAuth } from '../contexts/AuthContext'
import { Key, Plus, Shield } from 'lucide-react'
import toast from 'react-hot-toast'
import AddKeyModal from '../components/vault/AddKeyModal'
import KeyCard from '../components/vault/KeyCard'

interface ApiKey {
  id: string
  name: string
  key: string
  masked_key: string
  type: 'openai' | 'anthropic' | 'github' | 'custom'
  spend_cap: number
  current_spend: number
  assigned_teams: string[]
  last_used: string | null
  created_at: string
}

export default function VaultKeys() {
  const { } = useSupabase()
  const { projectId } = useAuth()
  const [showAddModal, setShowAddModal] = useState(false)

  // Fetch API keys
  const { data: keys, isLoading, refetch } = useQuery({
    queryKey: ['api-keys', projectId],
    queryFn: async () => {
      if (!projectId) return []
      
      // Mock data - replace with real API call
      const mockKeys: ApiKey[] = [
        {
          id: '1',
          name: 'OpenAI Production',
          key: 'sk-...hidden',
          masked_key: 'sk-...aBcD',
          type: 'openai',
          spend_cap: 500,
          current_spend: 234.56,
          assigned_teams: ['design-bot', 'frontend-dev'],
          last_used: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: '2',
          name: 'GitHub Actions',
          key: 'ghp_...hidden',
          masked_key: 'ghp_...XyZ',
          type: 'github',
          spend_cap: 0,
          current_spend: 0,
          assigned_teams: ['backend-dev'],
          last_used: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          created_at: new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ]
      
      return mockKeys
    },
    enabled: !!projectId,
  })

  // Delete key mutation
  const deleteMutation = useMutation({
    mutationFn: async (keyId: string) => {
      // Implement delete logic
      console.log('Deleting key:', keyId)
    },
    onSuccess: () => {
      toast.success('API key deleted')
      refetch()
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete key')
    },
  })

  // Rotate key mutation
  const rotateMutation = useMutation({
    mutationFn: async (keyId: string) => {
      // Implement rotate logic
      console.log('Rotating key:', keyId)
    },
    onSuccess: () => {
      toast.success('API key rotated')
      refetch()
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to rotate key')
    },
  })

  const handleAddKey = async (keyData: any) => {
    // Implement add key logic
    console.log('Adding key:', keyData)
    toast.success('API key added')
    setShowAddModal(false)
    refetch()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Vault & Keys</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage API keys and access credentials
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add Key
        </button>
      </div>

      {/* Security Notice */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
        <div className="flex">
          <Shield className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800 dark:text-blue-300">
              Security Best Practices
            </h3>
            <p className="mt-1 text-sm text-blue-700 dark:text-blue-400">
              Rotate your API keys regularly and set appropriate spend caps. Never share keys outside your organization.
            </p>
          </div>
        </div>
      </div>

      {/* Keys Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : keys && keys.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {keys.map((key) => (
            <KeyCard
              key={key.id}
              apiKey={key}
              onRotate={() => rotateMutation.mutate(key.id)}
              onDelete={() => deleteMutation.mutate(key.id)}
              onEdit={() => {}}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Key className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">No API keys</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Get started by adding your first API key.
          </p>
          <div className="mt-6">
            <button
              onClick={() => setShowAddModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Key
            </button>
          </div>
        </div>
      )}

      {/* Add Key Modal */}
      <AddKeyModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddKey}
      />
    </div>
  )
}