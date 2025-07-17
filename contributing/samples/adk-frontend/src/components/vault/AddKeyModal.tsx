import { Fragment, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { X, Key } from 'lucide-react'

interface AddKeyModalProps {
  open: boolean
  onClose: () => void
  onAdd: (keyData: any) => void
}

export default function AddKeyModal({ open, onClose, onAdd }: AddKeyModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    type: 'openai',
    key: '',
    spend_cap: 0,
    assigned_teams: [] as string[],
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onAdd(formData)
    // Reset form
    setFormData({
      name: '',
      type: 'openai',
      key: '',
      spend_cap: 0,
      assigned_teams: [],
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
                    <Key className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full">
                    <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900 dark:text-white">
                      Add API Key
                    </Dialog.Title>
                    
                    <form onSubmit={handleSubmit} className="mt-4 space-y-4">
                      {/* Name */}
                      <div>
                        <label htmlFor="name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Key Name
                        </label>
                        <input
                          type="text"
                          id="name"
                          required
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                          placeholder="e.g., Production OpenAI Key"
                        />
                      </div>

                      {/* Type */}
                      <div>
                        <label htmlFor="type" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Key Type
                        </label>
                        <select
                          id="type"
                          value={formData.type}
                          onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                        >
                          <option value="openai">OpenAI</option>
                          <option value="anthropic">Anthropic</option>
                          <option value="github">GitHub</option>
                          <option value="custom">Custom</option>
                        </select>
                      </div>

                      {/* API Key */}
                      <div>
                        <label htmlFor="key" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          API Key
                        </label>
                        <input
                          type="password"
                          id="key"
                          required
                          value={formData.key}
                          onChange={(e) => setFormData({ ...formData, key: e.target.value })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white font-mono"
                          placeholder="sk-..."
                        />
                      </div>

                      {/* Spend Cap */}
                      <div>
                        <label htmlFor="spend_cap" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Monthly Spend Cap ($)
                        </label>
                        <input
                          type="number"
                          id="spend_cap"
                          min="0"
                          step="0.01"
                          value={formData.spend_cap}
                          onChange={(e) => setFormData({ ...formData, spend_cap: parseFloat(e.target.value) || 0 })}
                          className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                          placeholder="0 for unlimited"
                        />
                      </div>

                      {/* Assigned Teams */}
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Assign to Teams
                        </label>
                        <div className="mt-2 space-y-2">
                          {['design-bot', 'frontend-dev', 'backend-dev', 'qa-bot'].map((team) => (
                            <label key={team} className="flex items-center">
                              <input
                                type="checkbox"
                                value={team}
                                checked={formData.assigned_teams.includes(team)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setFormData({
                                      ...formData,
                                      assigned_teams: [...formData.assigned_teams, team],
                                    })
                                  } else {
                                    setFormData({
                                      ...formData,
                                      assigned_teams: formData.assigned_teams.filter(t => t !== team),
                                    })
                                  }
                                }}
                                className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                              />
                              <span className="ml-2 text-sm text-gray-700 dark:text-gray-300">
                                {team}
                              </span>
                            </label>
                          ))}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                        <button
                          type="submit"
                          className="inline-flex w-full justify-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 sm:ml-3 sm:w-auto"
                        >
                          Add Key
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