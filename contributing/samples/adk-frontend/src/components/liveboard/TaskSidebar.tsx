import { X, Clock, User, Tag, CheckCircle, MessageSquare } from 'lucide-react'
import { Task as BaseTask } from '@adk/supabase-sdk'

interface ExtendedTask extends BaseTask {
  task_id: string;
  type: string;
  assigned_to?: string;
  estimated_hours?: number;
  depends_on?: string[];
}
import { format } from 'date-fns'
import clsx from 'clsx'
import { useState } from 'react'

interface TaskSidebarProps {
  task: ExtendedTask | null
  onClose: () => void
  onApprove: (taskId: string) => void
  onReject: (taskId: string) => void
}

export default function TaskSidebar({ task, onClose, onApprove, onReject }: TaskSidebarProps) {
  const [comment, setComment] = useState('')

  if (!task) return null

  const statusColors = {
    PENDING: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    IN_PROGRESS: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    COMPLETED: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    FAILED: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    BLOCKED: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  }

  const handleAddComment = () => {
    // TODO: Implement comment addition
    console.log('Adding comment:', comment)
    setComment('')
  }

  return (
    <div className="w-96 bg-white dark:bg-gray-800 shadow-xl border-l border-gray-200 dark:border-gray-700 flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              {task.task_id}
            </h2>
            <span className={clsx(
              'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mt-1',
              statusColors[task.status]
            )}>
              {task.status.replace('_', ' ')}
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="px-6 py-4 space-y-6">
          {/* Description */}
          <div>
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
              Description
            </h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {task.description || 'No description provided'}
            </p>
          </div>

          {/* Details */}
          <div className="space-y-3">
            <div className="flex items-center text-sm">
              <Tag className="h-4 w-4 text-gray-400 mr-2" />
              <span className="text-gray-500 dark:text-gray-400">Type:</span>
              <span className="ml-2 text-gray-900 dark:text-white capitalize">{task.type}</span>
            </div>
            
            {task.assigned_to && (
              <div className="flex items-center text-sm">
                <User className="h-4 w-4 text-gray-400 mr-2" />
                <span className="text-gray-500 dark:text-gray-400">Assigned to:</span>
                <span className="ml-2 text-gray-900 dark:text-white">{task.assigned_to}</span>
              </div>
            )}

            <div className="flex items-center text-sm">
              <Clock className="h-4 w-4 text-gray-400 mr-2" />
              <span className="text-gray-500 dark:text-gray-400">Created:</span>
              <span className="ml-2 text-gray-900 dark:text-white">
                {format(new Date(task.created_at), 'MMM d, yyyy h:mm a')}
              </span>
            </div>

            {task.estimated_hours && (
              <div className="flex items-center text-sm">
                <Clock className="h-4 w-4 text-gray-400 mr-2" />
                <span className="text-gray-500 dark:text-gray-400">Estimated:</span>
                <span className="ml-2 text-gray-900 dark:text-white">{task.estimated_hours} hours</span>
              </div>
            )}
          </div>

          {/* Dependencies */}
          {task.depends_on && task.depends_on.length > 0 && (
            <div>
              <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                Dependencies
              </h3>
              <div className="space-y-1">
                {task.depends_on.map((dep: string) => (
                  <div key={dep} className="text-sm text-gray-600 dark:text-gray-400">
                    • {dep}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Comments */}
          <div>
            <h3 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
              Comments
            </h3>
            <div className="space-y-3">
              {/* Mock comments - replace with real data */}
              <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
                <div className="flex items-start space-x-2">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-full bg-primary-500 flex items-center justify-center">
                      <span className="text-white text-xs font-medium">AI</span>
                    </div>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      Design Agent
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      Started working on the UI mockups. Will have initial designs ready in 2 hours.
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                      2 hours ago
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Add comment */}
            <div className="mt-4">
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Add a comment..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 text-sm dark:bg-gray-700 dark:text-white"
                rows={3}
              />
              <button
                onClick={handleAddComment}
                disabled={!comment.trim()}
                className="mt-2 inline-flex items-center px-3 py-1.5 border border-transparent text-xs font-medium rounded shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <MessageSquare className="h-3 w-3 mr-1" />
                Comment
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Actions */}
      {task.status === 'PENDING' && (
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex space-x-3">
          <button
            onClick={() => onReject(task.id)}
            className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-gray-300 dark:border-gray-600 shadow-sm text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            <X className="h-4 w-4 mr-2" />
            Reject
          </button>
          <button
            onClick={() => onApprove(task.id)}
            className="flex-1 inline-flex justify-center items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            <CheckCircle className="h-4 w-4 mr-2" />
            Approve
          </button>
        </div>
      )}
    </div>
  )
}