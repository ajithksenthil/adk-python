import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { X, Bell, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useSupabase } from '../../contexts/SupabaseContext'
import { useAuth } from '../../contexts/AuthContext'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

interface NotificationPanelProps {
  open: boolean
  onClose: () => void
}

interface Notification {
  id: string
  type: 'vote' | 'task' | 'agent' | 'system'
  title: string
  message: string
  timestamp: string
  read: boolean
  severity: 'info' | 'warning' | 'error' | 'success'
  metadata?: any
}

const notificationIcons = {
  info: Info,
  warning: AlertTriangle,
  error: AlertCircle,
  success: CheckCircle,
}

const notificationColors = {
  info: 'bg-blue-50 text-blue-600 dark:bg-blue-900 dark:text-blue-400',
  warning: 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900 dark:text-yellow-400',
  error: 'bg-red-50 text-red-600 dark:bg-red-900 dark:text-red-400',
  success: 'bg-green-50 text-green-600 dark:bg-green-900 dark:text-green-400',
}

export default function NotificationPanel({ open, onClose }: NotificationPanelProps) {
  const { } = useSupabase()
  const { projectId } = useAuth()

  // Fetch notifications
  const { data: notifications, isLoading } = useQuery({
    queryKey: ['notifications', projectId],
    queryFn: async () => {
      if (!projectId) return []
      
      // Mock notifications - replace with real data
      const mockNotifications: Notification[] = [
        {
          id: '1',
          type: 'vote',
          title: 'Vote Required',
          message: 'Task DESIGN_001 requires your approval',
          timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
          read: false,
          severity: 'warning',
        },
        {
          id: '2',
          type: 'task',
          title: 'Task Completed',
          message: 'Frontend development task completed by frontend-dev agent',
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          read: false,
          severity: 'success',
        },
        {
          id: '3',
          type: 'agent',
          title: 'Agent Offline',
          message: 'QA Bot has gone offline unexpectedly',
          timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
          read: true,
          severity: 'error',
        },
        {
          id: '4',
          type: 'system',
          title: 'Budget Alert',
          message: 'Project budget is 80% utilized',
          timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
          read: true,
          severity: 'warning',
        },
      ]
      
      return mockNotifications
    },
    enabled: !!projectId,
  })

  const unreadCount = notifications?.filter(n => !n.read).length || 0

  return (
    <Transition.Root show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-in-out duration-500"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in-out duration-500"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-hidden">
          <div className="absolute inset-0 overflow-hidden">
            <div className="pointer-events-none fixed inset-y-0 right-0 flex max-w-full pl-10">
              <Transition.Child
                as={Fragment}
                enter="transform transition ease-in-out duration-500 sm:duration-700"
                enterFrom="translate-x-full"
                enterTo="translate-x-0"
                leave="transform transition ease-in-out duration-500 sm:duration-700"
                leaveFrom="translate-x-0"
                leaveTo="translate-x-full"
              >
                <Dialog.Panel className="pointer-events-auto w-screen max-w-md">
                  <div className="flex h-full flex-col overflow-y-scroll bg-white dark:bg-gray-800 shadow-xl">
                    {/* Header */}
                    <div className="bg-primary-600 px-4 py-6 sm:px-6">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center">
                          <Bell className="h-6 w-6 text-white" />
                          <Dialog.Title className="ml-3 text-lg font-medium text-white">
                            Notifications
                          </Dialog.Title>
                          {unreadCount > 0 && (
                            <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-white text-primary-600">
                              {unreadCount} new
                            </span>
                          )}
                        </div>
                        <button
                          type="button"
                          className="rounded-md text-white hover:text-gray-200 focus:outline-none"
                          onClick={onClose}
                        >
                          <X className="h-6 w-6" />
                        </button>
                      </div>
                    </div>

                    {/* Notifications list */}
                    <div className="flex-1 overflow-y-auto">
                      {isLoading ? (
                        <div className="flex items-center justify-center p-8">
                          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                        </div>
                      ) : notifications && notifications.length > 0 ? (
                        <div className="divide-y divide-gray-200 dark:divide-gray-700">
                          {notifications.map((notification) => {
                            const Icon = notificationIcons[notification.severity]
                            return (
                              <div
                                key={notification.id}
                                className={clsx(
                                  'p-4 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer transition-colors',
                                  !notification.read && 'bg-blue-50 dark:bg-blue-900/20'
                                )}
                              >
                                <div className="flex space-x-3">
                                  <div className={clsx(
                                    'flex-shrink-0 p-2 rounded-full',
                                    notificationColors[notification.severity]
                                  )}>
                                    <Icon className="h-5 w-5" />
                                  </div>
                                  <div className="flex-1 min-w-0">
                                    <p className={clsx(
                                      'text-sm font-medium text-gray-900 dark:text-white',
                                      !notification.read && 'font-semibold'
                                    )}>
                                      {notification.title}
                                    </p>
                                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                                      {notification.message}
                                    </p>
                                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                                      {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true })}
                                    </p>
                                  </div>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      ) : (
                        <div className="p-8 text-center">
                          <Bell className="mx-auto h-12 w-12 text-gray-400" />
                          <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                            No notifications yet
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Footer */}
                    {notifications && notifications.length > 0 && (
                      <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-3">
                        <button className="w-full text-center text-sm text-primary-600 hover:text-primary-500 font-medium">
                          Mark all as read
                        </button>
                      </div>
                    )}
                  </div>
                </Dialog.Panel>
              </Transition.Child>
            </div>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}