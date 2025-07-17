import { Activity, CheckCircle, Cpu } from 'lucide-react'
import clsx from 'clsx'

interface TeamCardProps {
  name: string
  type: string
  status: 'ONLINE' | 'BUSY' | 'OFFLINE' | 'ERROR'
  capabilities: string[]
  currentTask?: string
  tasksCompleted: number
  uptime: string
}

const statusColors = {
  ONLINE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  BUSY: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  OFFLINE: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  ERROR: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
}

const statusIcons = {
  ONLINE: <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse" />,
  BUSY: <div className="h-2 w-2 bg-yellow-500 rounded-full animate-pulse" />,
  OFFLINE: <div className="h-2 w-2 bg-gray-500 rounded-full" />,
  ERROR: <div className="h-2 w-2 bg-red-500 rounded-full animate-pulse" />,
}

export default function TeamCard({
  name,
  type,
  status,
  capabilities,
  currentTask,
  tasksCompleted,
  uptime,
}: TeamCardProps) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-medium text-gray-900 dark:text-white">{name}</h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 capitalize">{type} Agent</p>
        </div>
        <div className="flex items-center space-x-2">
          {statusIcons[status]}
          <span className={clsx(
            'px-2 py-1 text-xs font-medium rounded-full',
            statusColors[status]
          )}>
            {status}
          </span>
        </div>
      </div>

      <div className="space-y-3">
        {/* Capabilities */}
        <div>
          <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Skills</p>
          <div className="flex flex-wrap gap-1">
            {capabilities.slice(0, 3).map((skill) => (
              <span
                key={skill}
                className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
              >
                {skill}
              </span>
            ))}
            {capabilities.length > 3 && (
              <span className="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">
                +{capabilities.length - 3} more
              </span>
            )}
          </div>
        </div>

        {/* Current Task */}
        {currentTask && (
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Current Task</p>
            <p className="text-sm text-gray-900 dark:text-white truncate">{currentTask}</p>
          </div>
        )}

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2 pt-3 border-t border-gray-200 dark:border-gray-700">
          <div className="text-center">
            <CheckCircle className="h-4 w-4 text-gray-400 mx-auto mb-1" />
            <p className="text-xs text-gray-500 dark:text-gray-400">Completed</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{tasksCompleted}</p>
          </div>
          <div className="text-center">
            <Activity className="h-4 w-4 text-gray-400 mx-auto mb-1" />
            <p className="text-xs text-gray-500 dark:text-gray-400">Uptime</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white">{uptime}</p>
          </div>
          <div className="text-center">
            <Cpu className="h-4 w-4 text-gray-400 mx-auto mb-1" />
            <p className="text-xs text-gray-500 dark:text-gray-400">CPU</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white">23%</p>
          </div>
        </div>
      </div>
    </div>
  )
}