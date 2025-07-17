import { useQuery } from '@tanstack/react-query'
import { useSupabase } from '../contexts/SupabaseContext'
import { useAuth } from '../contexts/AuthContext'
import { 
  DollarSign, 
  CheckCircle, 
  Clock, 
  Users
} from 'lucide-react'
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'
import KPICard from '../components/dashboard/KPICard'
import TeamCard from '../components/dashboard/TeamCard'
import AlertCard from '../components/dashboard/AlertCard'

export default function Dashboard() {
  const { adk } = useSupabase()
  const { projectId } = useAuth()

  // Fetch project metrics
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['dashboard-metrics', projectId],
    queryFn: async () => {
      if (!projectId) return null
      
      const state = await adk.querySlice(`project-${projectId}`, 'metrics:*')
      return state.slice.metrics || {}
    },
    enabled: !!projectId,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch active agents
  const { data: agents, isLoading: agentsLoading } = useQuery({
    queryKey: ['active-agents', projectId],
    queryFn: async () => {
      if (!projectId) return []
      
      const state = await adk.querySlice(`project-${projectId}`, 'agents:*', 10)
      return Object.values(state.slice || {})
    },
    enabled: !!projectId,
  })

  // Fetch pending tasks
  const { data: pendingTasks, isLoading: tasksLoading } = useQuery({
    queryKey: ['pending-tasks', projectId],
    queryFn: async () => {
      if (!projectId) return []
      
      const state = await adk.querySlice(`project-${projectId}`, 'tasks:*', 20)
      const tasks = Object.values(state.slice || {})
      return tasks.filter((task: any) => task.status === 'PENDING' || task.status === 'BLOCKED')
    },
    enabled: !!projectId,
  })

  // Mock data for charts (replace with real data)
  const taskCompletionData = [
    { date: '2024-01-01', completed: 12, failed: 2 },
    { date: '2024-01-02', completed: 15, failed: 1 },
    { date: '2024-01-03', completed: 18, failed: 3 },
    { date: '2024-01-04', completed: 22, failed: 0 },
    { date: '2024-01-05', completed: 25, failed: 2 },
    { date: '2024-01-06', completed: 30, failed: 1 },
    { date: '2024-01-07', completed: 28, failed: 4 },
  ]

  const budgetData = [
    { name: 'Allocated', value: metrics?.budget_total || 10000 },
    { name: 'Spent', value: metrics?.budget_spent || 3500 },
    { name: 'Remaining', value: (metrics?.budget_total || 10000) - (metrics?.budget_spent || 3500) },
  ]

  const loading = metricsLoading || agentsLoading || tasksLoading

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Real-time overview of your multi-agent system
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Budget"
          value={`$${(metrics?.budget_total || 0).toLocaleString()}`}
          icon={DollarSign}
          trend={+12.5}
          color="green"
        />
        <KPICard
          title="Tasks Completed"
          value={metrics?.tasks_completed || 0}
          icon={CheckCircle}
          trend={+8.2}
          color="blue"
        />
        <KPICard
          title="Active Agents"
          value={agents?.filter((a: any) => a.status === 'ONLINE').length || 0}
          icon={Users}
          subtitle={`${agents?.length || 0} total`}
          color="purple"
        />
        <KPICard
          title="Avg Completion Time"
          value="2.4h"
          icon={Clock}
          trend={-15.3}
          color="yellow"
        />
      </div>

      {/* Alerts Section */}
      {pendingTasks && pendingTasks.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">Requires Attention</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <AlertCard
              type="warning"
              title="Pending Approvals"
              message={`${pendingTasks.filter((t: any) => t.status === 'PENDING').length} tasks awaiting approval`}
              action={{
                label: 'Review Tasks',
                href: '/live-board'
              }}
            />
            <AlertCard
              type="error"
              title="Blocked Tasks"
              message={`${pendingTasks.filter((t: any) => t.status === 'BLOCKED').length} tasks are blocked`}
              action={{
                label: 'View Details',
                href: '/live-board'
              }}
            />
          </div>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Task Completion Chart */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Task Completion Trend
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={taskCompletionData}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis 
                dataKey="date" 
                tickFormatter={(value) => format(new Date(value), 'MMM d')}
                className="text-xs"
              />
              <YAxis className="text-xs" />
              <Tooltip />
              <Area 
                type="monotone" 
                dataKey="completed" 
                stackId="1"
                stroke="#10b981" 
                fill="#10b981" 
                fillOpacity={0.8}
                name="Completed"
              />
              <Area 
                type="monotone" 
                dataKey="failed" 
                stackId="1"
                stroke="#ef4444" 
                fill="#ef4444" 
                fillOpacity={0.8}
                name="Failed"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Budget Utilization */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Budget Utilization
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={budgetData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis type="number" className="text-xs" />
              <YAxis dataKey="name" type="category" className="text-xs" />
              <Tooltip formatter={(value) => `$${value.toLocaleString()}`} />
              <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Teams Section */}
      <div>
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Active Teams</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents?.map((agent: any) => (
            <TeamCard
              key={agent.agent_id}
              name={agent.name}
              type={agent.type}
              status={agent.status}
              capabilities={agent.capabilities}
              currentTask={agent.current_task}
              tasksCompleted={agent.tasks_completed}
              uptime="99.8%"
            />
          ))}
        </div>
      </div>
    </div>
  )
}