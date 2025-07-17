import { useState } from 'react'
import { RefreshCw, Trash2, Eye, EyeOff, Edit, Activity } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

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

interface KeyCardProps {
  apiKey: ApiKey
  onRotate: () => void
  onDelete: () => void
  onEdit: () => void
}

const typeIcons = {
  openai: '🤖',
  anthropic: '🧠',
  github: '🐙',
  custom: '🔧',
}

export default function KeyCard({ apiKey, onRotate, onDelete, onEdit }: KeyCardProps) {
  const [showKey, setShowKey] = useState(false)
  const spendPercentage = apiKey.spend_cap > 0 
    ? (apiKey.current_spend / apiKey.spend_cap) * 100 
    : 0

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center">
          <div className="text-2xl mr-3">{typeIcons[apiKey.type]}</div>
          <div>
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">
              {apiKey.name}
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 capitalize">
              {apiKey.type} API Key
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={onEdit}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <Edit className="h-4 w-4" />
          </button>
          <button
            onClick={onRotate}
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-1 text-red-400 hover:text-red-600"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Key Display */}
      <div className="mb-4">
        <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-900 rounded-md">
          <code className="text-sm text-gray-600 dark:text-gray-400 font-mono">
            {showKey ? apiKey.key : apiKey.masked_key}
          </code>
          <button
            onClick={() => setShowKey(!showKey)}
            className="ml-2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Spend Cap */}
      {apiKey.spend_cap > 0 && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-sm mb-1">
            <span className="text-gray-500 dark:text-gray-400">Spend Cap</span>
            <span className="text-gray-900 dark:text-white font-medium">
              ${apiKey.current_spend.toFixed(2)} / ${apiKey.spend_cap}
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
            <div
              className={clsx(
                'h-2 rounded-full transition-all',
                spendPercentage > 80 ? 'bg-red-600' : 
                spendPercentage > 60 ? 'bg-yellow-600' : 'bg-green-600'
              )}
              style={{ width: `${Math.min(spendPercentage, 100)}%` }}
            />
          </div>
        </div>
      )}

      {/* Assigned Teams */}
      <div className="mb-4">
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">Assigned to:</p>
        <div className="flex flex-wrap gap-1">
          {apiKey.assigned_teams.map((team) => (
            <span
              key={team}
              className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
            >
              {team}
            </span>
          ))}
          {apiKey.assigned_teams.length === 0 && (
            <span className="text-xs text-gray-500 dark:text-gray-400 italic">
              Not assigned to any teams
            </span>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center">
          <Activity className="h-3 w-3 mr-1" />
          {apiKey.last_used ? (
            <span>
              Last used {formatDistanceToNow(new Date(apiKey.last_used), { addSuffix: true })}
            </span>
          ) : (
            <span>Never used</span>
          )}
        </div>
        <span>
          Created {formatDistanceToNow(new Date(apiKey.created_at), { addSuffix: true })}
        </span>
      </div>
    </div>
  )
}