import { Fragment } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { X, Database, Download, Star, Tag, Folder, Code, Clock } from 'lucide-react'
import { format } from 'date-fns'
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

interface MemCubeDetailModalProps {
  memCube: MemCube
  open: boolean
  onClose: () => void
  onAddToProject: () => void
}

const typeColors = {
  PLAINTEXT: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
  SEMANTIC: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  COMMAND: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  TEMPLATE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
}

const typeDescriptions = {
  PLAINTEXT: 'Plain text content for documentation, notes, and reference material',
  SEMANTIC: 'AI-optimized content with semantic understanding and embeddings',
  COMMAND: 'Executable commands and scripts for automation',
  TEMPLATE: 'Reusable templates and boilerplate code',
}

export default function MemCubeDetailModal({ memCube, open, onClose, onAddToProject }: MemCubeDetailModalProps) {
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
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
              <Dialog.Panel className="relative transform overflow-hidden rounded-lg bg-white dark:bg-gray-800 text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-3xl">
                <div className="absolute right-0 top-0 pr-4 pt-4">
                  <button
                    type="button"
                    className="rounded-md text-gray-400 hover:text-gray-500 focus:outline-none"
                    onClick={onClose}
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>

                <div className="px-6 pt-6 pb-4">
                  {/* Header */}
                  <div className="mb-6">
                    <div className="flex items-start">
                      <div className="flex-1">
                        <h3 className="text-2xl font-semibold text-gray-900 dark:text-white">
                          {memCube.label}
                        </h3>
                        <div className="flex items-center mt-2 space-x-4">
                          <span className={clsx('px-3 py-1 text-sm font-medium rounded-full', typeColors[memCube.type])}>
                            {memCube.type}
                          </span>
                          <span className="text-sm text-gray-500 dark:text-gray-400">
                            {memCube.category}
                          </span>
                          {memCube.price > 0 ? (
                            <span className="text-lg font-bold text-gray-900 dark:text-white">
                              ${memCube.price}
                            </span>
                          ) : (
                            <span className="text-sm font-medium text-green-600 dark:text-green-400">
                              Free
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Description */}
                  <div className="mb-6">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Description</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {memCube.description}
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-500 mt-2 italic">
                      {typeDescriptions[memCube.type]}
                    </p>
                  </div>

                  {/* Stats Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg text-center">
                      <Download className="h-5 w-5 text-gray-400 mx-auto mb-2" />
                      <p className="text-xl font-semibold text-gray-900 dark:text-white">
                        {memCube.downloads.toLocaleString()}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Downloads</p>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg text-center">
                      <Star className="h-5 w-5 text-yellow-400 mx-auto mb-2" />
                      <p className="text-xl font-semibold text-gray-900 dark:text-white">
                        {memCube.rating.toFixed(1)}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Rating</p>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg text-center">
                      <Database className="h-5 w-5 text-gray-400 mx-auto mb-2" />
                      <p className="text-xl font-semibold text-gray-900 dark:text-white">
                        {formatSize(memCube.size)}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Size</p>
                    </div>
                    <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded-lg text-center">
                      <Clock className="h-5 w-5 text-gray-400 mx-auto mb-2" />
                      <p className="text-xl font-semibold text-gray-900 dark:text-white">
                        {format(new Date(memCube.updated_at), 'MMM d')}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">Updated</p>
                    </div>
                  </div>

                  {/* Tags */}
                  <div className="mb-6">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Tags</h4>
                    <div className="flex flex-wrap gap-2">
                      {memCube.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center px-3 py-1 text-sm bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full"
                        >
                          <Tag className="h-3 w-3 mr-1" />
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Preview */}
                  {memCube.preview_content && (
                    <div className="mb-6">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2 flex items-center">
                        <Code className="h-4 w-4 mr-1" />
                        Preview
                      </h4>
                      <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4 overflow-x-auto">
                        <pre className="text-sm text-gray-800 dark:text-gray-200 font-mono">
                          <code>{memCube.preview_content}</code>
                        </pre>
                      </div>
                    </div>
                  )}

                  {/* Creator Info */}
                  <div className="mb-6">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">Creator</h4>
                    <div className="flex items-center">
                      {memCube.creator.avatar ? (
                        <img
                          src={memCube.creator.avatar}
                          alt={memCube.creator.name}
                          className="h-10 w-10 rounded-full mr-3"
                        />
                      ) : (
                        <div className="h-10 w-10 rounded-full bg-gray-300 dark:bg-gray-600 mr-3" />
                      )}
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {memCube.creator.name}
                        </p>
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Created {format(new Date(memCube.created_at), 'MMMM d, yyyy')}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Features/Capabilities */}
                  <div className="mb-6">
                    <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">What you get</h4>
                    <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">✓</span>
                        Full access to all content and templates
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">✓</span>
                        Integration with your AI agent teams
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">✓</span>
                        Automatic updates and improvements
                      </li>
                      <li className="flex items-start">
                        <span className="text-green-500 mr-2">✓</span>
                        Commercial usage rights
                      </li>
                    </ul>
                  </div>
                </div>

                {/* Actions */}
                <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 flex items-center justify-end space-x-3">
                  <button
                    type="button"
                    onClick={onClose}
                    className="inline-flex items-center px-4 py-2 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    onClick={onAddToProject}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                  >
                    <Folder className="h-4 w-4 mr-2" />
                    Add to Project
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