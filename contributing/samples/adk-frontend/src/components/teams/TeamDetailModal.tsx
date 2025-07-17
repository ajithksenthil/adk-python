import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { X, Bot, Activity, Clock, CheckCircle, XCircle, Settings } from 'lucide-react'
import { format } from 'date-fns'

interface AgentTeam {
  id: string
  agent_id: string
  name: string
  type: string
  status: 'ONLINE' | 'BUSY' | 'OFFLINE' | 'ERROR'
  capabilities: string[]
  aml_level: string
  tasks_completed: number
  tasks_failed: number
  avg_completion_time: number
  accept_public_tasks: boolean
  docker_image?: string
  model_endpoint?: string
  last_heartbeat: string
}

interface TeamDetailModalProps {
  team: AgentTeam
  open: boolean
  onClose: () => void
}

export default function TeamDetailModal({ team, open, onClose }: TeamDetailModalProps) {
  const statusColors = {
    ONLINE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    BUSY: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    OFFLINE: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    ERROR: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  }

  const successRate = team.tasks_completed + team.tasks_failed > 0
    ? (team.tasks_completed / (team.tasks_completed + team.tasks_failed)) * 100
    : 0

  return (
    <Transition.Root show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" />
        </Transition.Child>

        <div className="fixed inset-0 z-10 overflow-y-auto">
          <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enterTo="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 translate-y-0 sm:scale-100"
              leaveTo="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-2xl sm:p-6">
                <div className="absolute right-0 top-0 pr-4 pt-4">
                  <button
                    type="button"
                    className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none"
                    onClick={onClose}
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>

                {/* Header */}
                <div className="flex items-start mb-6">
                  <div className="p-3 bg-gray-100 dark:bg-gray-700 rounded-lg mr-4">
                    <Bot className="h-8 w-8 text-gray-600 dark:text-gray-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
                      {team.name}
                    </h3>
                    <div className="flex items-center mt-1 space-x-4">
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        {team.agent_id} • {team.type}
                      </span>
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColors[team.status]}`}>
                        {team.status}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Stats Grid */}
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Tasks Completed</p>
                        <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                          {team.tasks_completed}
                        </p>
                      </div>
                      <CheckCircle className="h-8 w-8 text-green-500" />
                    </div>
                  </div>
                  
                  <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Tasks Failed</p>
                        <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                          {team.tasks_failed}
                        </p>
                      </div>
                      <XCircle className="h-8 w-8 text-red-500" />
                    </div>
                  </div>

                  <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Avg Completion Time</p>
                        <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                          {team.avg_completion_time}h
                        </p>
                      </div>
                      <Clock className="h-8 w-8 text-blue-500" />
                    </div>
                  </div>

                  <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Success Rate</p>
                        <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                          {successRate.toFixed(1)}%
                        </p>
                      </div>
                      <Activity className="h-8 w-8 text-purple-500" />
                    </div>
                  </div>
                </div>

                {/* Capabilities */}
                <div className="mb-6">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Capabilities</h4>
                  <div className="flex flex-wrap gap-2">
                    {team.capabilities.map((capability) => (
                      <span
                        key={capability}
                        className="px-3 py-1 text-sm bg-primary-100 dark:bg-primary-900 text-primary-700 dark:text-primary-300 rounded-full"
                      >
                        {capability}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Configuration */}
                <div className="mb-6">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">Configuration</h4>
                  <div className="space-y-3 text-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500 dark:text-gray-400">AML Level</span>
                      <span className="text-gray-900 dark:text-white font-medium">{team.aml_level}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-gray-500 dark:text-gray-400">Public Tasks</span>
                      <span className="text-gray-900 dark:text-white font-medium">
                        {team.accept_public_tasks ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                    {team.docker_image && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500 dark:text-gray-400">Docker Image</span>
                        <span className="text-gray-900 dark:text-white font-mono text-xs">
                          {team.docker_image}
                        </span>
                      </div>
                    )}
                    {team.model_endpoint && (
                      <div className="flex items-center justify-between">
                        <span className="text-gray-500 dark:text-gray-400">Model Endpoint</span>
                        <span className="text-gray-900 dark:text-white font-mono text-xs truncate max-w-xs">
                          {team.model_endpoint}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Last Heartbeat */}
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Last heartbeat: {format(new Date(team.last_heartbeat), 'PPpp')}
                </div>

                {/* Actions */}
                <div className="mt-6 flex justify-end space-x-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                  >
                    <Settings className="h-4 w-4 mr-2" />
                    Configure
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}