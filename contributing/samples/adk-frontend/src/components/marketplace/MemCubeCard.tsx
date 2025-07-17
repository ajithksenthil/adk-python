import { Database, Download, Star, Tag, Folder, Eye } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

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

interface MemCubeCardProps {
  memCube: MemCube
  onView: () => void
  onAddToProject: () => void
}

const typeColors = {
  PLAINTEXT: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  SEMANTIC: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  COMMAND: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  TEMPLATE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
}

const typeIcons = {
  PLAINTEXT: '📄',
  SEMANTIC: '🧠',
  COMMAND: '⚡',
  TEMPLATE: '🎨',
}

export default function MemCubeCard({ memCube, onView, onAddToProject }: MemCubeCardProps) {
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const formatDownloads = (count: number) => {
    if (count < 1000) return count.toString()
    return `${(count / 1000).toFixed(1)}k`
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden">
      {/* Header */}
      <div className="p-6">
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center">
            <div className="text-2xl mr-3">{typeIcons[memCube.type]}</div>
            <div className="flex-1">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white line-clamp-1">
                {memCube.label}
              </h3>
              <div className="flex items-center mt-1 space-x-3 text-sm">
                <span className={clsx('px-2 py-1 text-xs font-medium rounded-full', typeColors[memCube.type])}>
                  {memCube.type}
                </span>
                <span className="text-gray-500 dark:text-gray-400">
                  {memCube.category}
                </span>
              </div>
            </div>
          </div>
          {memCube.price > 0 && (
            <div className="text-right">
              <p className="text-lg font-bold text-gray-900 dark:text-white">
                ${memCube.price}
              </p>
            </div>
          )}
        </div>

        {/* Description */}
        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-4">
          {memCube.description}
        </p>

        {/* Tags */}
        <div className="flex flex-wrap gap-1 mb-4">
          {memCube.tags.slice(0, 4).map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
            >
              <Tag className="h-3 w-3 mr-1" />
              {tag}
            </span>
          ))}
          {memCube.tags.length > 4 && (
            <span className="text-xs text-gray-500 dark:text-gray-400 px-2 py-1">
              +{memCube.tags.length - 4} more
            </span>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 py-3 border-t border-gray-200 dark:border-gray-700">
          <div className="text-center">
            <div className="flex items-center justify-center text-gray-400 mb-1">
              <Download className="h-4 w-4" />
            </div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {formatDownloads(memCube.downloads)}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Downloads</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center text-yellow-400 mb-1">
              <Star className="h-4 w-4 fill-current" />
            </div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {memCube.rating.toFixed(1)}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Rating</p>
          </div>
          <div className="text-center">
            <div className="flex items-center justify-center text-gray-400 mb-1">
              <Database className="h-4 w-4" />
            </div>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {formatSize(memCube.size)}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">Size</p>
          </div>
        </div>

        {/* Creator */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center">
            {memCube.creator.avatar ? (
              <img
                src={memCube.creator.avatar}
                alt={memCube.creator.name}
                className="h-6 w-6 rounded-full mr-2"
              />
            ) : (
              <div className="h-6 w-6 rounded-full bg-gray-300 dark:bg-gray-600 mr-2" />
            )}
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {memCube.creator.name}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Updated {formatDistanceToNow(new Date(memCube.updated_at), { addSuffix: true })}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="px-6 py-3 bg-gray-50 dark:bg-gray-900 flex items-center justify-between">
        <button
          onClick={onView}
          className="inline-flex items-center text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
        >
          <Eye className="h-4 w-4 mr-1" />
          View Details
        </button>
        <button
          onClick={onAddToProject}
          className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <Folder className="h-4 w-4 mr-1" />
          Add to Project
        </button>
      </div>
    </div>
  )
}