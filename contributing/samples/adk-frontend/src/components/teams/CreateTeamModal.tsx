import { Fragment, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { X, Bot, Plus } from 'lucide-react'

interface CreateTeamModalProps {
  open: boolean
  onClose: () => void
  onCreate: (teamData: any) => void
}

export default function CreateTeamModal({ open, onClose, onCreate }: CreateTeamModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    agent_id: '',
    type: 'developer',
    capabilities: '',
    aml_level: 'AML1',
    accept_public_tasks: false,
    docker_image: '',
    model_endpoint: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const capabilities = formData.capabilities
      .split(',')
      .map(c => c.trim())
      .filter(c => c.length > 0)
    
    onCreate({
      ...formData,
      capabilities,
    })
    
    // Reset form
    setFormData({
      name: '',
      agent_id: '',
      type: 'developer',
      capabilities: '',
      aml_level: 'AML1',
      accept_public_tasks: false,
      docker_image: '',
      model_endpoint: '',
    })
  }

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
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 px-4 pb-4 pt-5 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg sm:p-6">
                <div className="absolute right-0 top-0 pr-4 pt-4">
                  <button
                    type="button"
                    className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none"
                    onClick={onClose}
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>

                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900 sm:mx-0 sm:h-10 sm:w-10">
                    <Bot className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full">
                    <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900 dark:text-white">
                      Create Agent Team
                    </Dialog.Title>
                    
                    <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                      {/* Name */}
                      <div>
                        <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Team Name
                        </label>
                        <input
                          type="text"
                          id="name"
                          required
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                          placeholder="e.g., Frontend Developer"
                        />
                      </div>

                      {/* Agent ID */}
                      <div>
                        <label htmlFor="agent_id" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Agent ID
                        </label>
                        <input
                          type="text"
                          id="agent_id"
                          required
                          value={formData.agent_id}
                          onChange={(e) => setFormData({ ...formData, agent_id: e.target.value })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                          placeholder="e.g., frontend-dev-1"
                        />
                      </div>

                      {/* Type */}
                      <div>
                        <label htmlFor="type" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Agent Type
                        </label>
                        <select
                          id="type"
                          value={formData.type}
                          onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                        >
                          <option value="developer">Developer</option>
                          <option value="designer">Designer</option>
                          <option value="tester">Tester</option>
                          <option value="analyst">Analyst</option>
                          <option value="manager">Manager</option>
                        </select>
                      </div>

                      {/* Capabilities */}
                      <div>
                        <label htmlFor="capabilities" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Capabilities (comma-separated)
                        </label>
                        <textarea
                          id="capabilities"
                          rows={3}
                          required
                          value={formData.capabilities}
                          onChange={(e) => setFormData({ ...formData, capabilities: e.target.value })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                          placeholder="e.g., react, typescript, css, testing"
                        />
                      </div>

                      {/* AML Level */}
                      <div>
                        <label htmlFor="aml_level" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          AML Level
                        </label>
                        <select
                          id="aml_level"
                          value={formData.aml_level}
                          onChange={(e) => setFormData({ ...formData, aml_level: e.target.value })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                        >
                          <option value="AML1">AML1 - Basic</option>
                          <option value="AML2">AML2 - Intermediate</option>
                          <option value="AML3">AML3 - Advanced</option>
                          <option value="AML4">AML4 - Expert</option>
                        </select>
                      </div>

                      {/* Docker Image */}
                      <div>
                        <label htmlFor="docker_image" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Docker Image (optional)
                        </label>
                        <input
                          type="text"
                          id="docker_image"
                          value={formData.docker_image}
                          onChange={(e) => setFormData({ ...formData, docker_image: e.target.value })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                          placeholder="e.g., adk/frontend-agent:latest"
                        />
                      </div>

                      {/* Model Endpoint */}
                      <div>
                        <label htmlFor="model_endpoint" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Model Endpoint (optional)
                        </label>
                        <input
                          type="url"
                          id="model_endpoint"
                          value={formData.model_endpoint}
                          onChange={(e) => setFormData({ ...formData, model_endpoint: e.target.value })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                          placeholder="e.g., https://api.openai.com/v1/chat/completions"
                        />
                      </div>

                      {/* Public Tasks */}
                      <div className="flex items-center">
                        <input
                          type="checkbox"
                          id="accept_public_tasks"
                          checked={formData.accept_public_tasks}
                          onChange={(e) => setFormData({ ...formData, accept_public_tasks: e.target.checked })}
                          className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                        />
                        <label htmlFor="accept_public_tasks" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                          Accept public tasks
                        </label>
                      </div>

                      {/* Actions */}
                      <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                        <button
                          type="submit"
                          className="inline-flex w-full justify-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 sm:ml-3 sm:w-auto"
                        >
                          <Plus className="h-4 w-4 mr-2" />
                          Create Team
                        </button>
                        <button
                          type="button"
                          onClick={onClose}
                          className="mt-3 inline-flex w-full justify-center rounded-md bg-white dark:bg-gray-700 px-3 py-2 text-sm font-semibold text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 sm:mt-0 sm:w-auto"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  </div>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition.Root>
  )
}