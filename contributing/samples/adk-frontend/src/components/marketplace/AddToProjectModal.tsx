import { Fragment, useState } from 'react'
import { Dialog, Transition } from '@headlessui/react'
import { X, Folder, Plus, Search, Check } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../contexts/AuthContext'

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

interface Project {
  id: string
  name: string
  description: string
  team_count: number
  memcube_count: number
  created_at: string
}

interface AddToProjectModalProps {
  memCube: MemCube
  open: boolean
  onClose: () => void
  onConfirm: (projectId: string) => void
  isLoading?: boolean
}

export default function AddToProjectModal({ memCube, open, onClose, onConfirm, isLoading }: AddToProjectModalProps) {
  const { user } = useAuth()
  const [selectedProjectId, setSelectedProjectId] = useState<string>('')
  const [searchQuery, setSearchQuery] = useState('')
  const [showNewProjectForm, setShowNewProjectForm] = useState(false)
  const [newProjectName, setNewProjectName] = useState('')
  const [newProjectDescription, setNewProjectDescription] = useState('')

  // Fetch user's projects
  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ['user-projects', user?.id],
    queryFn: async () => {
      // Mock data - replace with real API call
      const mockProjects: Project[] = [
        {
          id: 'project1',
          name: 'E-commerce Platform',
          description: 'Full-stack e-commerce application with AI-powered recommendations',
          team_count: 4,
          memcube_count: 12,
          created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: 'project2',
          name: 'Data Analytics Dashboard',
          description: 'Real-time analytics dashboard for business intelligence',
          team_count: 3,
          memcube_count: 8,
          created_at: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString(),
        },
        {
          id: 'project3',
          name: 'Mobile App Backend',
          description: 'Scalable backend API for mobile applications',
          team_count: 2,
          memcube_count: 5,
          created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ]
      return mockProjects
    },
    enabled: open && !!user,
  })

  const filteredProjects = projects?.filter(project => 
    project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    project.description.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  const handleConfirm = () => {
    if (showNewProjectForm) {
      // Create new project first, then add MemCube
      console.log('Creating new project:', newProjectName, newProjectDescription)
      // In real implementation, create project and get its ID
      const newProjectId = 'new-project-' + Date.now()
      onConfirm(newProjectId)
    } else if (selectedProjectId) {
      onConfirm(selectedProjectId)
    }
  }

  const handleClose = () => {
    setSelectedProjectId('')
    setSearchQuery('')
    setShowNewProjectForm(false)
    setNewProjectName('')
    setNewProjectDescription('')
    onClose()
  }

  return (
    <Transition.Root show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={handleClose}>
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
                    onClick={handleClose}
                  >
                    <X className="h-6 w-6" />
                  </button>
                </div>

                <div className="sm:flex sm:items-start">
                  <div className="mx-auto flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-full bg-primary-100 dark:bg-primary-900 sm:mx-0 sm:h-10 sm:w-10">
                    <Folder className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div className="mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full">
                    <Dialog.Title as="h3" className="text-lg font-semibold leading-6 text-gray-900 dark:text-white">
                      Add MemCube to Project
                    </Dialog.Title>
                    
                    <div className="mt-4">
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                        Select a project to add <span className="font-medium">{memCube.label}</span> to:
                      </p>

                      {!showNewProjectForm ? (
                        <>
                          {/* Search Projects */}
                          <div className="mb-4">
                            <div className="relative">
                              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                              <input
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search projects..."
                                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-gray-700 dark:text-white text-sm"
                              />
                            </div>
                          </div>

                          {/* Projects List */}
                          {projectsLoading ? (
                            <div className="flex items-center justify-center py-8">
                              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
                            </div>
                          ) : filteredProjects.length > 0 ? (
                            <div className="space-y-2 max-h-60 overflow-y-auto">
                              {filteredProjects.map((project) => (
                                <label
                                  key={project.id}
                                  className={`flex items-start p-3 border rounded-lg cursor-pointer transition-colors ${
                                    selectedProjectId === project.id
                                      ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                                      : 'border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
                                  }`}
                                >
                                  <input
                                    type="radio"
                                    name="project"
                                    value={project.id}
                                    checked={selectedProjectId === project.id}
                                    onChange={(e) => setSelectedProjectId(e.target.value)}
                                    className="h-4 w-4 mt-0.5 text-primary-600 focus:ring-primary-500 border-gray-300"
                                  />
                                  <div className="ml-3 flex-1">
                                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                                      {project.name}
                                    </p>
                                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                                      {project.description}
                                    </p>
                                    <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500 dark:text-gray-400">
                                      <span>{project.team_count} teams</span>
                                      <span>•</span>
                                      <span>{project.memcube_count} MemCubes</span>
                                    </div>
                                  </div>
                                </label>
                              ))}
                            </div>
                          ) : (
                            <p className="text-center py-8 text-sm text-gray-500 dark:text-gray-400">
                              No projects found
                            </p>
                          )}

                          {/* Create New Project Option */}
                          <button
                            type="button"
                            onClick={() => setShowNewProjectForm(true)}
                            className="mt-4 w-full inline-flex items-center justify-center px-4 py-2 border border-dashed border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                          >
                            <Plus className="h-4 w-4 mr-2" />
                            Create New Project
                          </button>
                        </>
                      ) : (
                        /* New Project Form */
                        <div className="space-y-4">
                          <div>
                            <label htmlFor="project-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                              Project Name
                            </label>
                            <input
                              type="text"
                              id="project-name"
                              value={newProjectName}
                              onChange={(e) => setNewProjectName(e.target.value)}
                              className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                              placeholder="My Awesome Project"
                            />
                          </div>
                          <div>
                            <label htmlFor="project-description" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                              Description
                            </label>
                            <textarea
                              id="project-description"
                              rows={3}
                              value={newProjectDescription}
                              onChange={(e) => setNewProjectDescription(e.target.value)}
                              className="mt-1 block w-full rounded-md border-gray-300 dark:border-gray-600 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                              placeholder="Brief description of your project..."
                            />
                          </div>
                          <button
                            type="button"
                            onClick={() => setShowNewProjectForm(false)}
                            className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                          >
                            ← Back to project list
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="mt-5 sm:mt-4 sm:flex sm:flex-row-reverse">
                      <button
                        type="button"
                        onClick={handleConfirm}
                        disabled={isLoading || (!selectedProjectId && !showNewProjectForm) || (showNewProjectForm && !newProjectName)}
                        className="inline-flex w-full justify-center rounded-md bg-primary-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-primary-500 sm:ml-3 sm:w-auto disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isLoading ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                            Adding...
                          </>
                        ) : (
                          <>
                            <Check className="h-4 w-4 mr-2" />
                            {showNewProjectForm ? 'Create & Add' : 'Add to Project'}
                          </>
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={handleClose}
                        disabled={isLoading}
                        className="mt-3 inline-flex w-full justify-center rounded-md bg-white dark:bg-gray-700 px-3 py-2 text-sm font-semibold text-gray-900 dark:text-white shadow-sm ring-1 ring-inset ring-gray-300 dark:ring-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 sm:mt-0 sm:w-auto disabled:opacity-50"
                      >
                        Cancel
                      </button>
                    </div>
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