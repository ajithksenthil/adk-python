import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useSupabase } from '../contexts/SupabaseContext'
import { useAuth } from '../contexts/AuthContext'
import { Users, Plus, Bot, Zap } from 'lucide-react'
import toast from 'react-hot-toast'
import TeamDetailModal from '../components/teams/TeamDetailModal'
import CreateTeamModal from '../components/teams/CreateTeamModal'

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

export default function TeamsSkills() {
  const { } = useSupabase()
  const { projectId } = useAuth()
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [selectedTeam, setSelectedTeam] = useState<AgentTeam | null>(null)

  // Fetch teams
  const { data: teams, isLoading, refetch } = useQuery({
    queryKey: ['teams', projectId],
    queryFn: async () => {
      if (!projectId) return []
      
      // Mock data - replace with real API call
      const mockTeams: AgentTeam[] = [
        {
          id: '1',
          agent_id: 'design-bot',
          name: 'Design Bot',
          type: 'designer',
          status: 'ONLINE',
          capabilities: ['ui-design', 'ux-research', 'prototyping', 'design-systems'],
          aml_level: 'AML2',
          tasks_completed: 142,
          tasks_failed: 3,
          avg_completion_time: 2.4,
          accept_public_tasks: true,
          docker_image: 'adk/design-agent:latest',
          last_heartbeat: new Date().toISOString(),
        },
        {
          id: '2',
          agent_id: 'frontend-dev',
          name: 'Frontend Developer',
          type: 'developer',
          status: 'BUSY',
          capabilities: ['react', 'typescript', 'css', 'testing'],
          aml_level: 'AML3',
          tasks_completed: 89,
          tasks_failed: 7,
          avg_completion_time: 3.1,
          accept_public_tasks: false,
          model_endpoint: 'https://api.openai.com/v1/chat/completions',
          last_heartbeat: new Date().toISOString(),
        },
        {
          id: '3',
          agent_id: 'backend-dev',
          name: 'Backend Developer',
          type: 'developer',
          status: 'ONLINE',
          capabilities: ['python', 'nodejs', 'database', 'api-design'],
          aml_level: 'AML3',
          tasks_completed: 156,
          tasks_failed: 12,
          avg_completion_time: 4.2,
          accept_public_tasks: true,
          docker_image: 'adk/backend-agent:latest',
          last_heartbeat: new Date().toISOString(),
        },
        {
          id: '4',
          agent_id: 'qa-bot',
          name: 'QA Bot',
          type: 'tester',
          status: 'OFFLINE',
          capabilities: ['testing', 'automation', 'bug-reporting', 'performance'],
          aml_level: 'AML1',
          tasks_completed: 203,
          tasks_failed: 0,
          avg_completion_time: 1.8,
          accept_public_tasks: false,
          docker_image: 'adk/qa-agent:latest',
          last_heartbeat: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
        },
      ]
      
      return mockTeams
    },
    enabled: !!projectId,
  })

  // Toggle public tasks mutation
  const togglePublicTasksMutation = useMutation({
    mutationFn: async ({ teamId, value }: { teamId: string; value: boolean }) => {
      // Implement toggle logic
      console.log('Toggling public tasks:', teamId, value)
    },
    onSuccess: () => {
      toast.success('Team settings updated')
      refetch()
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update team')
    },
  })

  const handleCreateTeam = async (teamData: any) => {
    // Implement create team logic
    console.log('Creating team:', teamData)
    toast.success('Team created successfully')
    setShowCreateModal(false)
    refetch()
  }

  const statusColors = {
    ONLINE: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    BUSY: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
    OFFLINE: 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200',
    ERROR: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Teams & Skills</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage your agent teams and their capabilities
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <Plus className="h-4 w-4 mr-2" />
          Create Team
        </button>
      </div>

      {/* Teams Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      ) : teams && teams.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {teams.map((team) => (
            <div
              key={team.id}
              className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => setSelectedTeam(team)}
            >
              <div className="p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center">
                    <div className="p-2 bg-gray-100 dark:bg-gray-700 rounded-lg mr-3">
                      <Bot className="h-6 w-6 text-gray-600 dark:text-gray-400" />
                    </div>
                    <div>
                      <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                        {team.name}
                      </h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        {team.agent_id} • {team.type}
                      </p>
                    </div>
                  </div>
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusColors[team.status]}`}>
                    {team.status}
                  </span>
                </div>

                {/* Skills */}
                <div className="mb-4">
                  <div className="flex flex-wrap gap-1">
                    {team.capabilities.slice(0, 4).map((skill) => (
                      <span
                        key={skill}
                        className="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded"
                      >
                        {skill}
                      </span>
                    ))}
                    {team.capabilities.length > 4 && (
                      <span className="px-2 py-1 text-xs text-gray-500 dark:text-gray-400">
                        +{team.capabilities.length - 4} more
                      </span>
                    )}
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Completed</p>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {team.tasks_completed}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Failed</p>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {team.tasks_failed}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-gray-400">Avg Time</p>
                    <p className="text-lg font-semibold text-gray-900 dark:text-white">
                      {team.avg_completion_time}h
                    </p>
                  </div>
                </div>

                {/* Settings */}
                <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700">
                  <div className="flex items-center text-sm">
                    <Zap className="h-4 w-4 text-gray-400 mr-1" />
                    <span className="text-gray-500 dark:text-gray-400">
                      AML Level: {team.aml_level}
                    </span>
                  </div>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={team.accept_public_tasks}
                      onChange={(e) => {
                        e.stopPropagation()
                        togglePublicTasksMutation.mutate({
                          teamId: team.id,
                          value: e.target.checked,
                        })
                      }}
                      className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                    />
                    <span className="ml-2 text-sm text-gray-600 dark:text-gray-400">
                      Public tasks
                    </span>
                  </label>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Users className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900 dark:text-white">No teams</h3>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Get started by creating your first agent team.
          </p>
          <div className="mt-6">
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Team
            </button>
          </div>
        </div>
      )}

      {/* Create Team Modal */}
      <CreateTeamModal
        open={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onCreate={handleCreateTeam}
      />

      {/* Team Detail Modal */}
      {selectedTeam && (
        <TeamDetailModal
          team={selectedTeam}
          open={!!selectedTeam}
          onClose={() => setSelectedTeam(null)}
        />
      )}
    </div>
  )
}